# Cartel del gancho (igual al de los clips de stream): Montserrat ExtraBold 67, tracking -2,
# caja blanca redondeada (radio 22), margen 29 lateral / 19 arriba y abajo, interlineado 82,
# ancho max de linea 690. Texto entre *asteriscos* va en rojo. Se ubica con TY=1074 (caja en y=1104).
import sys,re
from PIL import Image,ImageDraw,ImageFont
txt,out=sys.argv[1],sys.argv[2]
F=ImageFont.truetype('/usr/share/fonts/truetype/higgsfield/Montserrat-ExtraBold.ttf',67)
TR=-2
def wl(w): return sum(F.getlength(c)+TR for c in w)-TR
toks=[];red=False
for part in re.split(r'(\*)',txt):
    if part=='*': red=not red; continue
    for w in part.split(): toks.append((w,red))
MAXW=690;sp=F.getlength(' ')+TR
lines=[];cur=[];cw=0
for w,r in toks:
    l=wl(w)
    if cur and cw+sp+l>MAXW: lines.append(cur);cur=[];cw=0
    cw=cw+(sp if cur else 0)+l;cur.append((w,r,l))
lines.append(cur)
LH=82;padx=29;padt=19;padb=19
cap=F.getbbox('H');capTop,capH=cap[1],cap[3]-cap[1]
widths=[sum(l for _,_,l in L)+sp*(len(L)-1) for L in lines]
bw=int(max(widths))+2*padx;bh=padt+capH+LH*(len(lines)-1)+padb
im=Image.new('RGBA',(1080,bh+40),(0,0,0,0));d=ImageDraw.Draw(im)
x0=(1080-bw)//2;top=30
d.rounded_rectangle([x0,top,x0+bw,top+bh],radius=22,fill=(255,255,255,255))
y=top+padt-capTop
for L,wd in zip(lines,widths):
    x=(1080-wd)/2
    for w,r,l in L:
        for ch in w:
            d.text((x,y),ch,font=F,fill=(226,20,30) if r else (10,10,10));x+=F.getlength(ch)+TR
        x+=sp
    y+=LH
im.save(out)
