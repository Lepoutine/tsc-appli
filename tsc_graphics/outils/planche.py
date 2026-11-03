import sys, numpy as np
sys.path.insert(0,'/home/claude/tsc-appli/tsc_graphics/outils')
import etalon
from PIL import Image, ImageDraw
R='/mnt/project-files/tsc_graphics/references_videos/'; G='/mnt/project-files/tsc_graphics/captures_jeu_classees/'
choix={'jour':('videoplayback__2_/videoplayback__2__00995s.jpg','jour/ets2_20261016_210531_00.png'),
 'gris':(None,'gris/ets2_20261021_031421_00.png'),
 'pluie':(None,'pluie/fil_737ac766.png'),
 'crepuscule':(None,'crepuscule/ets2_20261013_085045_00.png'),
 'nuit':(None,'nuit/ets2_20261021_031432_00.png'),
 'nuit_pluie':('PLUIE_SOMBRE','nuit/ets2_20261021_031432_00.png')}
import csv
rows=list(csv.reader(open(R+'index.csv',encoding='utf-8-sig'),delimiter=';'))[1:]
amb=sys.argv[2:] or list(choix)
out=[]
W=1600
for a in amb:
    reel,jeu=choix[a]
    if reel is None:
        c=sorted([r for r in rows if r[3]==a and r[4]!='arret'],key=lambda r:float(r[5].replace(',','.')))
        reel=c[len(c)//2][2].replace(chr(92),'/').replace(chr(92),'/')
    if reel=='PLUIE_SOMBRE':
        reel=sorted([r for r in rows if r[3]=='pluie'],key=lambda r:float(r[5].replace(',','.')))[0][2]
    reel=reel.replace(chr(92),'/')
    im=Image.open(R+reel).convert('RGB')
    g=Image.open(G+jeu).convert('RGB')
    if g.width/g.height>2.5:
        cw=int(g.height*16/9); x0=(g.width-cw)//2; g=g.crop((x0,0,x0+cw,g.height))
    H=540; gw=int(g.width*H/g.height)
    src=np.asarray(g.resize((gw,H)),dtype=np.float32)/255
    after=Image.fromarray((etalon.rendu_photo(src,etalon.LOOKS[a])*255).astype(np.uint8))
    rw=int(im.width*H/im.height)
    canvas=Image.new('RGB',(rw+2*gw+16,H+8),(20,20,20))
    canvas.paste(im.resize((rw,H)),(0,0)); canvas.paste(g.resize((gw,H)),(rw+8,0)); canvas.paste(after,(rw+gw+16,0))
    d=ImageDraw.Draw(canvas)
    for t,xy in ((a.upper()+' : video reelle',(10,8)),('jeu avant',(rw+18,8)),('jeu apres TSC Graphics',(rw+gw+26,8))):
        d.rectangle([xy[0]-5,xy[1]-4,xy[0]+len(t)*6+6,xy[1]+13],fill=(0,0,0)); d.text(xy,t,fill=(255,255,255))
    out.append(canvas)
w=max(c.width for c in out); H=sum(c.height for c in out)
o=Image.new('RGB',(w,H),(20,20,20)); y=0
for c in out: o.paste(c,(0,y)); y+=c.height
o.save(sys.argv[1],quality=88); print(o.size)
