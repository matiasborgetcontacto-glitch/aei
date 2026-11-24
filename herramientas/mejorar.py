# Mejora un recorte de persona del stream: IA de nitidez (Real-ESRGAN x4) + IA de cara (GFPGAN 1.4)
# y lo recorta sin fondo. Uso: python3 mejorar.py FRAME.jpg X0-X1-YB OUT.png
# Modelos en /home/user/work/models (ver GUIA_CLIPS.md para bajarlos).
import sys, numpy as np, torch, spandrel, cv2
from PIL import Image, ImageFilter
M = '/home/user/work/models/'
src, rng, out = sys.argv[1:4]
im = Image.open(src).convert('RGB'); v = [float(x) for x in rng.split('-')]
im = im.crop((int(v[0]*im.width), 0, int(v[1]*im.width), int(v[2]*im.height)))
torch.set_num_threads(4)
def run(model, img):
    t = torch.from_numpy(np.asarray(img).astype(np.float32)/255).permute(2, 0, 1)[None]
    with torch.no_grad(): r = model(t)[0].clamp(0, 1).permute(1, 2, 0).numpy()
    return Image.fromarray((r*255).round().astype(np.uint8))
# 1) agrandar con IA y volver a 2x
up = spandrel.ModelLoader().load_from_file(M+'RealESRGAN_x4plus.pth').model.eval()
big = run(up, im).resize((im.width*2, im.height*2), Image.LANCZOS)
# 2) cara: detectar y restaurar con GFPGAN
g = np.asarray(big.convert('L'))
cc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
f = cc.detectMultiScale(g, 1.1, 5, minSize=(150, 150))
if len(f):
    x, y, w, h = max(f, key=lambda r: r[2]*r[3]); cx, cy = x+w/2, y+h/2; S = int(max(w, h)*1.9)
    box = (int(cx-S/2), int(cy-S/2), int(cx+S/2), int(cy+S/2))
    fa = big.crop(box).resize((512, 512), Image.LANCZOS)
    gf = spandrel.ModelLoader().load_from_file(M+'GFPGANv1.4.pth').model.eval()
    t = (torch.from_numpy(np.asarray(fa).astype(np.float32)/255).permute(2, 0, 1)[None]-0.5)/0.5
    with torch.no_grad(): r = gf(t)
    r = r[0] if isinstance(r, (tuple, list)) else r
    r = ((r[0].clamp(-1, 1)+1)/2).permute(1, 2, 0).numpy()
    fr = Image.fromarray((r*255).round().astype(np.uint8)).resize((box[2]-box[0], box[3]-box[1]), Image.LANCZOS)
    m = Image.new('L', fr.size, 0); m.paste(255, (int(S*0.12), int(S*0.12), int(S*0.88), int(S*0.88)))
    big.paste(fr, box[:2], m.filter(ImageFilter.GaussianBlur(S*0.06)))
    print('cara', x, y, w, h)
else: print('sin cara detectada')
# 3) recorte sin fondo
from rembg import remove, new_session
cut = remove(big, session=new_session(sys.argv[4] if len(sys.argv) > 4 else 'birefnet-portrait'))
cut.crop(cut.getchannel('A').point(lambda a: 255 if a > 40 else 0).getbbox()).save(out); print('ok', out)
