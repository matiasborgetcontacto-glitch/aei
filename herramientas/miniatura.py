# Miniatura YouTube 1280x720 estilo "mejores momentos" (ver GUIA_CLIPS.md).
# Personas recortadas (sin fondo) grandes sobre el fondo del stream, borde blanco,
# texto opcional en cursiva gruesa: linea 1 blanca sobre banda roja, linea 2 amarilla.
# Uso:
#   python3 miniatura.py OUT.jpg --fondo FRAME.jpg --p FOTO1.jpg[:x0-x1] [--p FOTO2.jpg[:x0-x1]] [--t1 'EL UNITED SE VA'] [--t2 'Y DAVO LO SABE']
#   x0-x1[-yb] (opcional): franja horizontal de la foto donde está la persona (en fracción, ej. 0.3-0.7).
#   --bg verde: fondo verde con humo y brillo (estilo MaxClips); --atras FOTO:x0-x1[,FOTO2...]: gente chica y oscura atrás.
#   --lados F1:x:y:w,F2:x:y:w: cada uno en su cámara (mitad y mitad).
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

if 'lados' in o:
    # modo "dos cámaras": cada uno en su propio fondo del stream, mitad y mitad con línea diagonal
    canvas = Image.new('RGBA', (W, Hh))
    specs = o['lados'].split(',')
    for j, sp in enumerate(specs):
        path, x, y, w = sp.split(':'); x, y, w = int(x), int(y), int(w)
        im = Image.open(path).convert('RGB'); h = int(w*Hh/(W/2+60))
        im = pop(im.crop((x, y, x+w, y+h)).resize((W//2+60, Hh), Image.LANCZOS))
        im = im.filter(ImageFilter.UnsharpMask(2, 80, 2))
        m = Image.new('L', (W, Hh), 0); dm = ImageDraw.Draw(m)
        if j == 0: dm.polygon([(0, 0), (W/2+40, 0), (W/2-40, Hh), (0, Hh)], fill=255); canvas.paste(im, (0, 0), m.crop((0, 0, W//2+60, Hh)))
        else:
            dm.polygon([(W/2+40, 0), (W, 0), (W, Hh), (W/2-40, Hh)], fill=255); canvas.paste(im, (W//2-60, 0), m.crop((W//2-60, 0, W, Hh)))
    d = ImageDraw.Draw(canvas); d.line([(W/2+40, -5), (W/2-40, Hh+5)], fill=(255, 255, 255), width=12)
    o['p'] = []
# fondo
if o.get('bg') == 'verde':
    import random; random.seed(4)
    canvas = Image.new('RGBA', (W, Hh), (4, 10, 6, 255))
    lay = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for _ in range(70):
        x = random.choice([random.uniform(-100, 300), random.uniform(W-300, W+100), random.uniform(0, W)]); y = random.uniform(Hh*0.2, Hh+80)
        r = random.uniform(60, 220); g = random.randint(150, 255)
        dl.ellipse((x-r, y-r, x+r, y+r), fill=(30, g, 40, random.randint(40, 110)))
    lay = lay.filter(ImageFilter.GaussianBlur(45)); canvas.alpha_composite(lay)
    c = Image.new('L', (W, Hh), 0); ImageDraw.Draw(c).ellipse((W*0.2, Hh*0.05, W*0.8, Hh*1.2), fill=120)
    c = c.filter(ImageFilter.GaussianBlur(120))
    canvas.alpha_composite(Image.merge('RGBA', (Image.new('L', (W, Hh), 120), Image.new('L', (W, Hh), 255), Image.new('L', (W, Hh), 140), c)))
    o['_glow'] = (60, 255, 80)
elif 'lados' not in o:
    fondo = Image.open(o.get('fondo', o['p'][0].split(':')[0])).convert('RGB')
    bg = pop(cover(fondo, W, Hh)).filter(ImageFilter.GaussianBlur(10))
    bg = ImageEnhance.Color(bg).enhance(1.4)
    canvas = bg.convert('RGBA')
    # luz detrás de la(s) persona(s) + viñeta
    gl = Image.new('L', (W, Hh), 0); dg = ImageDraw.Draw(gl)
    cxs = [0.5] if len(o['p']) == 1 and 't1' not in o else ([0.72] if len(o['p']) == 1 else [0.27, 0.73])
    for c in cxs: dg.ellipse((W*c-330, 40, W*c+330, 760), fill=150)
    gl = gl.filter(ImageFilter.GaussianBlur(90))
    canvas.alpha_composite(Image.merge('RGBA', (Image.new('L',(W,Hh),255),)*3 + (gl,)))
    vg = Image.new('L', (W, Hh), 0); ImageDraw.Draw(vg).ellipse((-200, -150, W+200, Hh+150), fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(120)).point(lambda v: int((255-v)*0.75))
    canvas.alpha_composite(Image.merge('RGBA', (Image.new('L',(W,Hh),0),)*3 + (vg,)))

from rembg import remove, new_session
ses = new_session('u2net_human_seg')
n = len(o['p'])
def persona(spec, th0, maxw):
    path, _, rng = spec.partition(':')
    if path.endswith('.png'):  # recorte ya hecho con mejorar.py
        cut = Image.open(path).convert('RGBA'); s = th0/cut.height if th0 <= Hh else max(th0, Hh+20)/cut.height
        cut = cut.resize((int(cut.width*s), int(cut.height*s)), Image.LANCZOS)
        if cut.width > maxw: cut = cut.crop(((cut.width-maxw)//2, 0, (cut.width-maxw)//2+maxw, cut.height))
        return cut
    im = Image.open(path).convert('RGB'); yb = 1.0
    if rng:
        v = [float(x) for x in rng.split('-')]; yb = v[2] if len(v) > 2 else 1.0
        im = im.crop((int(v[0]*im.width), 0, int(v[1]*im.width), int(yb*im.height)))
    cut = remove(pop(im), session=ses)
    cut = cut.crop(cut.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
    th = max(int(th0*yb), Hh+20) if th0 > Hh else int(th0*yb); s = th/cut.height
    cut = cut.resize((int(cut.width*s), th), Image.LANCZOS)
    if cut.width > maxw: cut = cut.crop(((cut.width-maxw)//2, 0, (cut.width-maxw)//2+maxw, cut.height))
    return cut

def borde(cut, glow=None, grueso=13):
    A = cut.getchannel('A'); pad = 40
    L = Image.new('RGBA', (cut.width+2*pad, cut.height+2*pad), (0, 0, 0, 0))
    Ab = Image.new('L', L.size, 0); Ab.paste(A, (pad, pad))
    if glow:
        g = Ab.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(22))
        L.paste(glow + (255,), (0, 0), g)
    else:
        sh = Ab.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v*0.7)); L.paste((0, 0, 0, 255), (12, 8), sh)
    L.paste((255, 255, 255, 255), (0, 0), Ab.filter(ImageFilter.MaxFilter(grueso)))
    L.alpha_composite(cut, (pad, pad)); return L, pad

glow = o.get('_glow')
# gente de atrás (más chica y oscura)
if 'atras' in o:
    sp = o['atras'].split(','); pos = [0.88] if len(sp) == 1 else [0.13, 0.87, 0.5][:len(sp)]
    for spec, cx in zip(sp, pos):
        cut = persona(spec, Hh*0.95, int(W*0.33))
        if 'siluetas' in o:
            cut = Image.merge('RGBA', [Image.new('L', cut.size, 8)]*3 + [cut.getchannel('A')])
        else:
            cut = Image.merge('RGBA', [ch.point(lambda v: int(v*0.35)) for ch in cut.split()[:3]] + [cut.getchannel('A')])
        L, pad = borde(cut, glow, 7)
        if 'siluetas' in o:
            fq = ImageFont.truetype(os.path.join(H, 'fonts/Anton-Regular.woff'), int(L.width*0.32))
            dq = ImageDraw.Draw(L); A = L.getchannel('A'); bb = A.getbbox(); hy = bb[1] + int(L.width*0.12)
            dq.text((L.width/2, hy), '?', font=fq, fill=(255, 255, 255), anchor='mt', stroke_width=6, stroke_fill=(0, 0, 0))
        canvas.alpha_composite(L, (int(W*cx - L.width/2), Hh - L.height + pad))
for j, spec in enumerate(o['p']):
    cut = persona(spec, Hh*(1.12 if glow else 1.25), int(W*(0.62 if n == 1 else (0.5 if glow else 0.55))))
    L, pad = borde(cut, glow, 11 if glow else 13)
    if n == 1: x = int(W*0.98 - L.width) if 't1' in o else (W-L.width)//2
    elif glow: x = int(W*0.31 - L.width/2) if j == 0 else int(W*0.69 - L.width/2)
    else: x = int(W*0.27 - L.width/2) if j == 0 else int(W*0.73 - L.width/2)
    canvas.alpha_composite(L, (x, (95 if glow else 30) - pad))
    if n == 2 and j == 0 and not glow:
        d = ImageDraw.Draw(canvas)
        d.polygon([(W*0.5+40, 0), (W*0.5+52, 0), (W*0.5-28, Hh), (W*0.5-40, Hh)], fill=(255, 255, 255, 255))

# texto
def skew(img, k=0.22):
    return img.transform((img.width+int(img.height*k), img.height), Image.AFFINE, (1, k, -img.height*k, 0, 1, 0), Image.BICUBIC)

def line(txt, size, fill, band=None):
    f = ImageFont.truetype(os.path.join(H, 'fonts/Anton-Regular.woff'), size)
    d0 = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    l, t, r, b = d0.textbbox((0, 0), txt, font=f, stroke_width=11)
    img = Image.new('RGBA', (r-l+40, b-t+30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if band: d.rectangle((0, 6, img.width, img.height-6), fill=band)
    d.text((28-l, 23-t), txt, font=f, fill=(0, 0, 0), stroke_width=11, stroke_fill=(0, 0, 0))
    d.text((20-l, 15-t), txt, font=f, fill=fill, stroke_width=9, stroke_fill=(0, 0, 0))
    return skew(img)

if 't1' in o:
    ls = [line(o['t1'].upper(), 150, (255, 255, 255), band=(220, 20, 30))]
    if 't2' in o: ls.append(line(o['t2'].upper(), 120, (255, 222, 0)))
    blk = Image.new('RGBA', (max(x.width for x in ls), sum(x.height for x in ls)), (0, 0, 0, 0)); y = 0
    for k, x in enumerate(ls): blk.alpha_composite(x, (0 if k == 0 else 40, y)); y += x.height - 8
    blk = blk.rotate(4, expand=True, resample=Image.BICUBIC)
    if blk.width > W*0.5: blk = blk.resize((int(W*0.5), int(blk.height*W*0.5/blk.width)), Image.LANCZOS)
    canvas.alpha_composite(blk, (20, Hh - blk.height - 25))

canvas.convert('RGB').save(out, quality=93); print('ok', out)
