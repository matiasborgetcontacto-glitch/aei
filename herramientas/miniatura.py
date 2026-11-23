# Miniatura YouTube 1280x720 para videos de mejores momentos.
# Uso: python3 miniatura.py FOTO.jpg 'TEXTO *ROJO*' OUT.jpg [--x 0.5 centro del recorte] [--zoom 1.0]
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
H = os.path.dirname(os.path.abspath(__file__))
src, txt, out = sys.argv[1:4]
a = sys.argv[4:]; o = dict(zip(a[::2], a[1::2]))
cx = float(o.get('--x', 0.5)); zoom = float(o.get('--zoom', 1.0))
W, Hh = 1280, 720
im = Image.open(src).convert('RGB')
s = max(W/im.width, Hh/im.height)*zoom
im = im.resize((int(im.width*s), int(im.height*s)), Image.LANCZOS)
x0 = int(min(max(cx*im.width - W/2, 0), im.width-W)); y0 = int((im.height-Hh)*0.35)
im = im.crop((x0, y0, x0+W, y0+Hh))
im = ImageEnhance.Color(im).enhance(1.35); im = ImageEnhance.Contrast(im).enhance(1.15); im = ImageEnhance.Sharpness(im).enhance(1.5)
# degradé oscuro abajo
g = Image.new('L', (1, Hh)); [g.putpixel((0, y), int(230*max(0, (y-Hh*0.45)/(Hh*0.55))**1.3)) for y in range(Hh)]
im.paste(Image.new('RGB', (W, Hh), (0, 0, 0)), (0, 0), g.resize((W, Hh)))
d = ImageDraw.Draw(im)
f = ImageFont.truetype(os.path.join(H, 'fonts/Montserrat-ExtraBold.ttf'), 110)
# palabras con color (*rojo*)
words = []; red = False
for w in txt.split():
    st = w.startswith('*'); en = w.endswith('*')
    if st: red = True
    words.append((w.strip('*').upper(), red))
    if en: red = False
lines = []; cur = []
for w in words:
    t = ' '.join(x for x, _ in cur+[w])
    if cur and d.textlength(t, font=f) > W-80: lines.append(cur); cur = [w]
    else: cur.append(w)
lines.append(cur)
y = Hh - 40 - 118*len(lines)
for ln in lines:
    tw = d.textlength(' '.join(x for x, _ in ln), font=f); x = (W-tw)/2
    for wd, r in ln:
        d.text((x, y), wd, font=f, fill=(255, 40, 40) if r else (255, 230, 0), stroke_width=9, stroke_fill=(0, 0, 0))
        x += d.textlength(wd+' ', font=f)
    y += 118
im.save(out, quality=92); print('ok', out)
