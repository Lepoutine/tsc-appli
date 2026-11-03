#!/usr/bin/env python3
"""TSC Textures HD (0.13) : fabrique plugins\\tsc_textures_hd\\<empreinte>.dds a partir d'une image HD.
Usage : python hd_dds.py image.png empreinte16hex format_jeu dossier_sortie
format_jeu = format DXGI de la texture du jeu (colonne format du csv) : 78/72/75 (BC sRGB) -> RGBA8 sRGB (29),
77/71/74 -> RGBA8 (28), 80 (BC4) -> R8 (61), 83 (BC5) -> R8G8 (49). Tous les niveaux (mips) sont generes.
L'image doit avoir les memes proportions que la texture du jeu et etre plus grande ou egale."""
import sys, os, struct
import numpy as np
from PIL import Image
CIBLE = {78: 29, 72: 29, 75: 29, 91: 29, 29: 29, 77: 28, 71: 28, 74: 28, 87: 28, 28: 28, 80: 61, 83: 49}
def s2l(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
def l2s(x): return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)
def main():
    src, h, fj, out = sys.argv[1], sys.argv[2].lower(), int(sys.argv[3]), sys.argv[4]
    fmt = CIBLE[fj]; srgb = fmt == 29
    im = np.asarray(Image.open(src).convert('RGBA'), np.float32) / 255
    if fmt == 61: im = im[..., :1]
    elif fmt == 49: im = im[..., :2]
    lin = s2l(im) if srgb else im
    if srgb and lin.shape[-1] == 4: lin[..., 3] = im[..., 3]
    niveaux = []; cur = lin
    while True:
        o = l2s(cur) if srgb else cur
        if srgb and cur.shape[-1] == 4: o[..., 3] = cur[..., 3]
        niveaux.append((np.clip(o, 0, 1) * 255 + 0.5).astype(np.uint8))
        hh, ww = cur.shape[:2]
        if hh == 1 and ww == 1: break
        nh, nw = max(hh // 2, 1), max(ww // 2, 1)
        cur = cur[:nh * 2 if hh > 1 else 1, :nw * 2 if ww > 1 else 1]
        cur = cur.reshape(nh, cur.shape[0] // nh, nw, cur.shape[1] // nw, -1).mean((1, 3))
    H, W = lin.shape[:2]
    hdr = [0] * 37
    hdr[0] = 0x20534444; hdr[1] = 124; hdr[2] = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000; hdr[3] = H; hdr[4] = W; hdr[7] = len(niveaux)
    hdr[19] = 32; hdr[20] = 0x4; hdr[21] = 0x30315844; hdr[27] = 0x1000 | 0x400000 | 0x8
    hdr[32] = fmt; hdr[33] = 3; hdr[35] = 1
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, h + '.dds'), 'wb') as f:
        f.write(struct.pack('<37I', *hdr))
        for n in niveaux: f.write(np.ascontiguousarray(n).tobytes())
    print(h + '.dds', W, 'x', H, len(niveaux), 'niveaux, format', fmt)
if __name__ == '__main__': main()
