# Video de mejores momentos (horizontal 1920x1080). Ver GUIA_CLIPS.md, sección 412.
# Uso: python3 compilado.py plan.json OUT.mp4
# plan.json: {"intro": {"src": "w.mp4", "a": 1.0, "b": 7.0, "texto": "FRASE"}, "partes": [["w.mp4", a, b], ...]}
import json, sys, subprocess, os
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__))
plan = json.load(open(sys.argv[1])); out = sys.argv[2]; tmp = out + '_tmp'; os.makedirs(tmp, exist_ok=True)
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-threads', '2', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000']
def parte(src, a, b, f, extra=None):
    vf = '[0:v]fps=30,scale=1920:1080,setsar=1' + (',' + extra if extra else '') + '[v]'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-to', str(b), '-i', src] + (['-i', plan['_bar']] if extra and 'ovl' in extra else []) +
                   ['-filter_complex', vf.replace('ovl', ''), '-map', '[v]', '-map', '0:a', '-af', 'afade=t=in:d=0.04,afade=t=out:st=%.3f:d=0.04' % (b-a-0.04)] + ENC + [f], check=True)
fs = []
if 'intro' in plan:
    it = plan['intro']
    # barra negra con la frase (como Bombillo): blanco, mayúsculas, bold
    bar = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(bar)
    f = ImageFont.truetype(os.path.join(H, 'fonts/Anton-Regular.woff'), 54)
    t = it['texto'].upper(); tw = d.textlength(t, font=f); bw = max(tw + 160, 1100)
    x0 = (1920 - bw) / 2; d.rectangle((x0, 950, x0 + bw, 1035), fill=(18, 18, 18, 235))
    d.text((960, 992), t, font=f, fill=(255, 255, 255), anchor='mm')
    plan['_bar'] = os.path.join(tmp, 'bar.png'); bar.save(plan['_bar'])
    fi = os.path.join(tmp, 'intro.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(it['a']), '-to', str(it['b']), '-i', it['src'], '-i', plan['_bar'],
                    '-filter_complex', '[0:v]fps=30,scale=1920:1080,setsar=1,hue=s=0,eq=contrast=1.15[g];[g][1:v]overlay=0:0[v]', '-map', '[v]', '-map', '0:a',
                    '-af', 'afade=t=out:st=%.3f:d=0.15' % (it['b']-it['a']-0.15)] + ENC + [fi], check=True)
    fs.append(fi)
for i, (src, a, b) in enumerate(plan['partes']):
    f = os.path.join(tmp, 'p%03d.mp4' % i); parte(src, a, b, f); fs.append(f)
open(os.path.join(tmp, 'l.txt'), 'w').write(''.join("file '%s'\n" % os.path.abspath(x) for x in fs))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(tmp, 'l.txt'), '-c', 'copy', '-movflags', '+faststart', out], check=True)
print('ok', out)
