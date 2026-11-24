# Cambia la cara de una persona en una miniatura generada por la cara real (sacada del stream).
# Uso: python3 cambiar_cara.py MINIATURA.jpg OUT.jpg CARA_REAL1.jpg [CARA_REAL2.jpg ...] [--cual derecha|izquierda|centro]
import sys, numpy as np, cv2, insightface, torch, spandrel
from insightface.app import FaceAnalysis
from PIL import Image, ImageFilter
a = [x for x in sys.argv[1:] if not x.startswith('--')]; cual = sys.argv[sys.argv.index('--cual')+1] if '--cual' in sys.argv else 'derecha'
a = [x for x in a if x not in ('derecha', 'izquierda', 'centro')]
dst, out, srcs = a[0], a[1], a[2:]
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); app.prepare(ctx_id=-1, det_size=(640, 640))
sw = insightface.model_zoo.get_model('/home/user/work/models/inswapper_128.onnx', providers=['CPUExecutionProvider'])
# cara fuente: promedio de las caras reales
fs = []
for s in srcs:
    f = app.get(cv2.imread(s)); f = max(f, key=lambda z: (z.bbox[2]-z.bbox[0])*(z.bbox[3]-z.bbox[1])); fs.append(f)
src = fs[0]; e = np.mean([f.normed_embedding for f in fs], axis=0); src.embedding = e / np.linalg.norm(e) * np.linalg.norm(src.embedding)
img = cv2.imread(dst); faces = app.get(img)
faces.sort(key=lambda z: z.bbox[0]); t = faces[-1] if cual == 'derecha' else faces[0] if cual == 'izquierda' else faces[len(faces)//2]
res = sw.get(img, t, src, paste_back=True)
# nitidez de la cara con GFPGAN
x1, y1, x2, y2 = [int(v) for v in t.bbox]; cx, cy = (x1+x2)/2, (y1+y2)/2; S = int(max(x2-x1, y2-y1)*1.8)
bx = (int(cx-S/2), int(cy-S/2), int(cx+S/2), int(cy+S/2))
pil = Image.fromarray(cv2.cvtColor(res, cv2.COLOR_BGR2RGB)); fa = pil.crop(bx).resize((512, 512), Image.LANCZOS)
gf = spandrel.ModelLoader().load_from_file('/home/user/work/models/GFPGANv1.4.pth').model.eval()
tt = (torch.from_numpy(np.asarray(fa).astype(np.float32)/255).permute(2, 0, 1)[None]-0.5)/0.5
with torch.no_grad(): r = gf(tt)
r = r[0] if isinstance(r, (tuple, list)) else r
r = ((r[0].clamp(-1, 1)+1)/2).permute(1, 2, 0).numpy()
fr = Image.fromarray((r*255).round().astype(np.uint8)).resize((bx[2]-bx[0], bx[3]-bx[1]), Image.LANCZOS)
m = Image.new('L', fr.size, 0); m.paste(255, (int(S*0.15), int(S*0.15), int(S*0.85), int(S*0.85)))
pil.paste(fr, bx[:2], m.filter(ImageFilter.GaussianBlur(S*0.06))); pil.save(out, quality=95); print('ok', out)
