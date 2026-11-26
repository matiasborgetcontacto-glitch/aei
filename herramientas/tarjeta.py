# Tarjeta con foto de jugador para los clips: foto grande, borde blanco, nombre en banda roja.
# Uso: python3 tarjeta.py FOTO.jpg 'NOMBRE' OUT.png [--y0 0.0 parte de arriba de la foto (fracción)]
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__))
src, name, out = sys.argv[1:4]; y0 = float(sys.argv[sys.argv.index('--y0')+1]) if '--y0' in sys.argv else 0.0
W, Hf = 520, 600
im = Image.open(src).convert('RGB'); r = W/Hf
cw = min(im.width, int(im.height*r)); ch = int(cw/r)
x = (im.width-cw)//2; y = int(y0*im.height); y = min(y, im.height-ch)
im = im.crop((x, y, x+cw, y+ch)).resize((W, Hf), Image.LANCZOS)
B = 10; f = ImageFont.truetype(os.path.join(H, 'fonts/Anton-Regular.woff'), 64)
d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); tw = d0.textlength(name.upper(), font=f)
LH = 96; card = Image.new('RGBA', (W+2*B+40, Hf+2*B+LH//2+40), (0, 0, 0, 0))
m = Image.new('L', (W+2*B, Hf+2*B), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, W+2*B-1, Hf+2*B-1), 28, fill=255)
sh = Image.new('L', card.size, 0); sh.paste(m, (26, 26)); card.paste((0, 0, 0, 150), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
card.paste((255, 255, 255, 255), (20, 20), m)
mi = Image.new('L', (W, Hf), 0); ImageDraw.Draw(mi).rounded_rectangle((0, 0, W-1, Hf-1), 20, fill=255)
card.paste(im, (20+B, 20+B), mi)
d = ImageDraw.Draw(card); lw = max(tw+60, 300); lx = (card.width-lw)/2; ly = 20+Hf+2*B-LH//2-10
d.rounded_rectangle((lx, ly, lx+lw, ly+LH), 16, fill=(225, 20, 30, 255), outline=(255, 255, 255, 255), width=5)
d.text((card.width/2, ly+LH/2), name.upper(), font=f, fill=(255, 255, 255), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0))
card.save(out); print('ok', out, card.size)
