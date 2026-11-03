import sys, numpy as np, onnxruntime as ort
from PIL import Image
import os
M=os.environ.get('TSC_MIDAS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modele', 'midas_small.onnx'))
_s=None
def disparite(img_srgb):
    """Disparite relative (grand = proche), normalisee 0..1, a la taille de l'image."""
    global _s
    if _s is None: _s=ort.InferenceSession(M,providers=['CPUExecutionProvider'])
    h,w=img_srgb.shape[:2]
    x=np.asarray(Image.fromarray((img_srgb*255).astype(np.uint8)).resize((256,256),Image.BICUBIC),dtype=np.float32)/255
    x=(x-[0.485,0.456,0.406])/[0.229,0.224,0.225]
    x=x.transpose(2,0,1)[None].astype(np.float32)
    o=_s.run(None,{_s.get_inputs()[0].name:x})[0][0]
    o=(o-o.min())/(o.max()-o.min()+1e-6)
    return np.asarray(Image.fromarray(o.astype(np.float32),mode='F').resize((w,h),Image.BICUBIC))
if __name__=='__main__':
    im=Image.open(sys.argv[1]).convert('RGB')
    if im.width/im.height>2.5:
        cw=int(im.height*16/9); x0=(im.width-cw)//2; im=im.crop((x0,0,x0+cw,im.height))
    im=im.resize((960,540))
    d=disparite(np.asarray(im,dtype=np.float32)/255)
    o=Image.new('RGB',(1920,540)); o.paste(im,(0,0)); o.paste(Image.fromarray((d*255).astype(np.uint8)).convert('RGB'),(960,0)); o.save(sys.argv[2])
