# Miniatura YouTube 1280x720 estilo "mejores momentos" (ver GUIA_CLIPS.md).
# Personas recortadas (sin fondo) grandes sobre el fondo del stream, borde blanco,
# texto opcional en cursiva gruesa: linea 1 blanca sobre banda roja, linea 2 amarilla.
# Uso:
#   python3 miniatura.py OUT.jpg --fondo FRAME.jpg --p FOTO1.jpg[:x0-x1] [--p FOTO2.jpg[:x0-x1]] [--t1 'EL UNITED SE VA'] [--t2 'Y DAVO LO SABE']
#   x0-x1 (opcional): franja horizontal de la foto donde está la persona (en fracción, ej. 0.3-0.7).
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops
H = os.path.dirname(os.path.abspath(__file__))
W, Hh = 1280, 720
args = sys.argv[1:]; out = args[0]; o = {'p': []}; i = 1
while i < len(args):
    k = args[i][2:]
    if k == 'p': o['p'].append(args[i+1])
    else: o[k] = args[i+1]
    i += 2

def cover(im, w, h):
    s = max(w/im.width, h/im.height); im = im.resize((int(im.width*s)+1, int(im.height*s)+1), Image.LANCZOS)
    x = (im.width-w)//2; y = (im.height-h)//2; return im.crop((x, y, x+w, y+h))

def pop(im):
    im = ImageEnhance.Color(im).enhance(1.35); im = ImageEnhance.Contrast(im).enhance(1.12)
    return ImageEnhance.Sharpness(im).enhance(1.6)

# fondo
fondo = Image.open(o.get('fondo', o['p'][0].split(':')[0])).convert('RGB')
bg = pop(cover(fondo, W, Hh)).filter(ImageFilter.GaussianBlur(3))
bg = ImageEnhance.Brightness(bg).enhance(0.85)
canvas = bg.convert('RGBA')

from rembg import remove, new_session
ses = new_session('u2net_human_seg')
n = len(o['p'])
for j, spec in enumerate(o['p']):
    path, _, rng = spec.partition(':')
    im = Image.open(path).convert('RGB')
    if rng:
        a, b = [float(v) for v in rng.split('-')]; im = im.crop((int(a*im.width), 0, int(b*im.width), im.height))
    cut = remove(pop(im), session=ses)
    cut = cut.crop(cut.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
    th = int(Hh*(1.05 if n == 1 else 1.0)); s = th/cut.height
    cut = cut.resize((int(cut.width*s), th), Image.LANCZOS)
    maxw = int(W*(0.62 if n == 1 else 0.55))
    if cut.width > maxw: cut = cut.crop(((cut.width-maxw)//2, 0, (cut.width-maxw)//2+maxw, cut.height))
    # borde blanco + sombra
    A = cut.getchannel('A')
    pad = 20; L = Image.new('RGBA', (cut.width+2*pad, cut.height+2*pad), (0, 0, 0, 0))
    Ab = Image.new('L', L.size, 0); Ab.paste(A, (pad, pad))
    sh = Ab.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v*0.7))
    st = Ab.filter(ImageFilter.MaxFilter(13))
    L.paste((0, 0, 0, 255), (12, 8), sh); L.paste((255, 255, 255, 255), (0, 0), st)
    L.alpha_composite(cut, (pad, pad))
    if n == 1: x = int(W*0.98 - L.width) if 't1' in o else (W-L.width)//2
    else: x = int(W*0.27 - L.width/2) if j == 0 else int(W*0.73 - L.width/2)
    canvas.alpha_composite(L, (x, Hh - L.height + pad))
    if n == 2 and j == 0:
        d = ImageDraw.Draw(canvas)
        d.polygon([(W*0.5+40, 0), (W*0.5+52, 0), (W*0.5-28, Hh), (W*0.5-40, Hh)], fill=(255, 255, 255, 255))

# texto
def skew(img, k=0.22):
    return img.transform((img.width+int(img.height*k), img.height), Image.AFFINE, (1, k, -img.height*k, 0, 1, 0), Image.BICUBIC)

def line(txt, size, fill, band=None):
    f = ImageFont.truetype(os.path.join(H, 'fonts/Anton-Regular.woff'), size)
    d0 = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    l, t, r, b = d0.textbbox((0, 0), txt, font=f, stroke_width=8)
    img = Image.new('RGBA', (r-l+40, b-t+30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if band: d.rectangle((0, 6, img.width, img.height-6), fill=band)
    d.text((20-l, 15-t), txt, font=f, fill=fill, stroke_width=8, stroke_fill=(0, 0, 0))
    return skew(img)

if 't1' in o:
    ls = [line(o['t1'].upper(), 118, (255, 255, 255), band=(220, 20, 30))]
    if 't2' in o: ls.append(line(o['t2'].upper(), 92, (255, 222, 0)))
    blk = Image.new('RGBA', (max(x.width for x in ls), sum(x.height for x in ls)), (0, 0, 0, 0)); y = 0
    for k, x in enumerate(ls): blk.alpha_composite(x, (0 if k == 0 else 40, y)); y += x.height - 8
    blk = blk.rotate(4, expand=True, resample=Image.BICUBIC)
    if blk.width > W*0.62: blk = blk.resize((int(W*0.62), int(blk.height*W*0.62/blk.width)), Image.LANCZOS)
    canvas.alpha_composite(blk, (20, Hh - blk.height - 25))

canvas.convert('RGB').save(out, quality=93); print('ok', out)
