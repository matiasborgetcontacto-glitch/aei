import json,sys,subprocess,os,math
from PIL import Image
k,a,b,c=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]
card=os.environ.get('CARD');TY=int(os.environ.get('TY','1180'))
D=b-a;FPS=30000/1001
w=[(s-a,e-a,t.strip()) for s,e,t in json.load(open(c+'.json')) if a-0.05<=s<b-0.05 and t.strip()]
# ---- zoom curve: ease-in at start, smooth changes at phrase ends
pts=[0.6];last=0.6
for s,e,t in w:
    if t[-1] in '.,?!' and e-last>=3.5 and D-e>2.0:
        last=e;pts.append(round(e,2))
lv=[1.12 if i%2==0 else 1.24 for i in range(len(pts))]
def sm(x): return "(%s)*(%s)*(3-2*(%s))"%(x,x,x)
ex="(1+0.12*%s)"%sm("min(it/0.6,1)")
for i in range(1,len(pts)):
    x="min((it-%.2f)/0.35,1)"%pts[i]
    seg="(%.3f+(%.3f)*%s)"%(lv[i-1],lv[i]-lv[i-1],sm(x))
    ex="if(lt(it,%.2f),%s,%s)"%(pts[i],ex,seg)
ex="(%s)*(1+0.03*it/%.1f)"%(ex,D)
# ---- title frames: pop in, hold, wave-glitch out
T=Image.open('fin/%s.png'%k).convert('RGBA');W,H=T.size
d='tf_'+k;os.makedirs(d,exist_ok=True)
TOUT=3.8;n=int((TOUT+0.5)*FPS)+1
src=T.load()
for i in range(n):
    t=i/FPS;f=Image.new('RGBA',(W,H),(0,0,0,0))
    if t<0.25:
        p=t/0.25;s=0.85+0.15*(1-(1-p)**3)
        im=T.resize((int(W*s),int(H*s)),Image.LANCZOS)
        im.putalpha(im.getchannel('A').point(lambda v:int(v*p)))
        f.alpha_composite(im,((W-im.size[0])//2,(H-im.size[1])//2))
    elif t<TOUT:
        f=T
    else:
        p=min((t-TOUT)/0.5,1);A=60*p
        for y in range(H):
            dx=int(A*math.sin(y/6.0+t*40)*(1 if (y//8)%2 else -1))
            row=T.crop((0,y,W,y+1))
            r=row.copy();r.putalpha(row.getchannel('A').point(lambda v:int(v*(1-p))))
            f.alpha_composite(r,(dx,y)) if 0<=dx else f.alpha_composite(r.crop((-dx,0,W,1)),(0,y))
    f.save('%s/%04d.png'%(d,i))
# ---- captions (ASS), 2 words, current word yellow
def ts(x):
    x=max(0,x);return "%d:%02d:%05.2f"%(x//3600,(x%3600)//60,x%60)
cy1,cy2=1600,1100
hdr="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: C,Montserrat ExtraBold,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3,2,5,40,40,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
groups=[];cur=[]
for x in w:
    cur.append(x)
    if len(cur)==2 or x[2][-1] in '.,?!' or len(x[2])>9:
        groups.append(cur);cur=[]
if cur: groups.append(cur)
ev=[]
for gi,gr in enumerate(groups):
    gend=groups[gi+1][0][0] if gi+1<len(groups) else D
    for j,(s,e,t) in enumerate(gr):
        en=gr[j+1][0] if j+1<len(gr) else gend
        if card and s<4.3<en: en=4.3
        y=cy2 if (card and s>=4.3) else cy1
        parts=[]
        for q,z in enumerate(gr):
            wd=z[2].upper().strip('.,?!¿¡"')
            parts.append('{\\c&H00E6FF&}%s{\\c&HFFFFFF&}'%wd if q==j else wd)
        ev.append("Dialogue: 0,%s,%s,C,,0,0,0,,{\\pos(540,%d)}%s"%(ts(s),ts(min(en,D)),y,' '.join(parts)))
open('%s.ass'%k,'w').write(hdr+'\n'.join(ev)+'\n')
# ---- render
fc=("[0:v]crop=405:720:448:0,scale=1080:1920:flags=lanczos,setsar=1,"
    "zoompan=z='%s':x='iw/2-(iw/zoom/2)':y='ih*0.30-(ih/zoom*0.30)':d=1:s=1080x1920:fps=30000/1001[b];"
    "[b][1:v]overlay=0:%d:eof_action=pass[b1]")%(ex,TY)
inp=['-ss',str(a),'-to',str(b),'-i','v.mp4','-framerate','30000/1001','-i',d+'/%04d.png']
last='b1'
if card:
    inp+=['-loop','1','-i',card]
    fc+=";[2:v]format=rgba,fade=in:st=4.3:d=0.2:alpha=1[c];[b1][c]overlay=(W-w)/2:1185:shortest=1:enable='gte(t,4.3)'[b2]"
    last='b2'
fc+=";[%s]ass=%s.ass:fontsdir=/usr/share/fonts/truetype/higgsfield,format=yuv420p[v];[0:a]afade=t=out:st=%.2f:d=0.25[au]"%(last,k,D-0.25)
subprocess.run(['ffmpeg','-nostdin','-v','error','-y']+inp+['-filter_complex',fc,'-map','[v]','-map','[au]','-t','%.2f'%D,'-c:v','libx264','-preset','medium','-crf','18','-c:a','aac','-b:a','192k','-movflags','+faststart','fx/%s.mp4'%k],check=True)
print('ok',k,pts)
