# Pipeline local de clips (sin Higgsfield). Ver GUIA_CLIPS.md.
# Uso:
#   python3 clip.py words SRC.mp4 OUT.json            -> transcribe (palabras con tiempos)
#   python3 clip.py cut SRC.mp4 SRC.json NAME '[[a,b],...]'   -> NAME.mp4 + NAME.json
#   python3 clip.py fx NAME 'TITULO *ROJO*' OUT.mp4 [--crop W:H:X:Y] [--split TOPCROP BOTCROP] [--ty 1074] [--card img --card-at 4.3] [--nozoom]
import json, sys, subprocess, os, math
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__))
FPS = 30000/1001

def words(src, out):
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    wav = out + '.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-ac','1','-ar','16000',wav], check=True)
    seg,_ = m.transcribe(wav, language='es', word_timestamps=True)
    w = [[x.start, x.end, x.word] for s in seg for x in s.words]
    json.dump(w, open(out,'w')); os.remove(wav); print(out, len(w))

def cut(src, srcjson, name, segs):
    w = json.load(open(srcjson)); out=[]; off=0; fc=''; n=len(segs)
    for i,(a,b) in enumerate(segs):
        fc += "[0:v]trim=%s:%s,setpts=PTS-STARTPTS,fps=30[v%d];[0:a]atrim=%s:%s,asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st=%.3f:d=0.03[a%d];"%(a,b,i,a,b,b-a-0.03,i)
        out += [[s-a+off,e-a+off,t] for s,e,t in w if a<=s<b]; off += b-a
    fc += ''.join('[v%d][a%d]'%(i,i) for i in range(n))+'concat=n=%d:v=1:a=1[v][a]'%n
    subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-filter_complex',fc,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','14','-c:a','aac','-b:a','192k',name+'.mp4'], check=True)
    json.dump(out, open(name+'.json','w')); print(name, round(off,2))

def fx(name, title, outp, opts):
    D = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',name+'.mp4'],capture_output=True,text=True).stdout)-0.05
    w = json.load(open(name+'.json')) if os.path.exists(name+'.json') else []
    ty = int(opts.get('ty',1074))
    # titulo
    tpng = name+'_title.png'
    subprocess.run(['python3',os.path.join(H,'titulo_gancho.py'),title,tpng],check=True)
    T = Image.open(tpng).convert('RGBA'); W,Hh = T.size
    d = name+'_tf'; os.makedirs(d, exist_ok=True)
    TOUT=3.8; n=int((TOUT+0.5)*FPS)+1
    for i in range(n):
        t=i/FPS; f=Image.new('RGBA',(W,Hh),(0,0,0,0))
        if t<0.25:
            p=t/0.25; s=0.85+0.15*(1-(1-p)**3)
            im=T.resize((int(W*s),int(Hh*s)),Image.LANCZOS)
            im.putalpha(im.getchannel('A').point(lambda v:int(v*p)))
            f.alpha_composite(im,((W-im.size[0])//2,(Hh-im.size[1])//2))
        elif t<TOUT: f=T
        else:
            p=min((t-TOUT)/0.5,1); A=60*p
            for y in range(Hh):
                dx=int(A*math.sin(y/6.0+t*40)*(1 if (y//8)%2 else -1))
                row=T.crop((0,y,W,y+1)); r=row.copy(); r.putalpha(row.getchannel('A').point(lambda v:int(v*(1-p))))
                if dx>=0:
                    if dx<W: f.alpha_composite(r,(dx,y))
                else: f.alpha_composite(r.crop((-dx,0,W,1)),(0,y))
        f.save('%s/%04d.png'%(d,i))
    # zoom
    if 'nozoom' in opts or 'split' in opts:
        ex='1'
    else:
        pts=[0.6]; last=0.6
        for s,e,t in w:
            t=t.strip()
            if t and t[-1] in '.,?!' and e-last>=3.5 and D-e>2.0: last=e; pts.append(round(e,2))
        lv=[1.12 if i%2==0 else 1.24 for i in range(len(pts))]
        sm=lambda x:"(%s)*(%s)*(3-2*(%s))"%(x,x,x)
        ex="(1+0.12*%s)"%sm("min(it/0.6,1)")
        for i in range(1,len(pts)):
            x="min((it-%.2f)/0.35,1)"%pts[i]
            ex="if(lt(it,%.2f),%s,%s)"%(pts[i],ex,"(%.3f+(%.3f)*%s)"%(lv[i-1],lv[i]-lv[i-1],sm(x)))
        ex="(%s)*(1+0.03*it/%.1f)"%(ex,D)
    if 'split' in opts:
        top,bot = opts['split']
        base="[0:v]split[sa][sb];[sa]crop=%s,scale=1080:1300[st];[sb]crop=%s,scale=1080:620[su];[st][su]vstack,drawbox=x=0:y=1296:w=1080:h=8:color=white:t=fill,setsar=1,fps=30000/1001[b]"%(top,bot)
    else:
        base="[0:v]crop=%s,scale=1080:1920:flags=lanczos,setsar=1,zoompan=z='%s':x='iw/2-(iw/zoom/2)':y='ih*0.30-(ih/zoom*0.30)':d=1:s=1080x1920:fps=30000/1001[b]"%(opts.get('crop','608:1080:656:0'),ex)
    fc=base+";[b][1:v]overlay=0:%d:eof_action=pass[b1]"%ty
    inp=['-i',name+'.mp4','-framerate','30000/1001','-i',d+'/%04d.png']
    last='b1'; k=2
    if 'card' in opts:
        at=float(opts.get('card-at',4.3))
        inp+=['-loop','1','-i',opts['card']]
        fc+=";[%d:v]format=rgba,fade=in:st=%.2f:d=0.2:alpha=1[c];[b1][c]overlay=(W-w)/2:1185:shortest=1:enable='gte(t,%.2f)'[b2]"%(k,at,at); last='b2'; k+=1
    inp+=['-loop','1','-i',os.path.join(H,'kick_logo.png'),'-i',os.path.join(H,'click.mp3')]
    fc+=";[%s][%d:v]overlay=(W-w)/2:35:shortest=1,format=yuv420p[v];[0:a]afade=t=out:st=%.2f:d=0.25[a0];[%d:a]volume=0.9[ck];[a0][ck]amix=inputs=2:duration=first:normalize=0[au]"%(last,k,D-0.25,k+1)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y']+inp+['-filter_complex',fc,'-map','[v]','-map','[au]','-t','%.2f'%D,'-c:v','libx264','-preset','medium','-crf','18','-c:a','aac','-b:a','192k','-movflags','+faststart',outp],check=True)
    print('ok',outp)

if __name__=='__main__':
    c=sys.argv[1]
    if c=='words': words(sys.argv[2],sys.argv[3])
    elif c=='cut': cut(sys.argv[2],sys.argv[3],sys.argv[4],json.loads(sys.argv[5]))
    elif c=='fx':
        a=sys.argv[5:]; o={}; i=0
        while i<len(a):
            k=a[i][2:]
            if k=='nozoom': o[k]=1; i+=1
            elif k=='split': o[k]=(a[i+1],a[i+2]); i+=3
            else: o[k]=a[i+1]; i+=2
        fx(sys.argv[2],sys.argv[3],sys.argv[4],o)
