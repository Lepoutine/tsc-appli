#!/usr/bin/env python3
"""TSC Neural : lit les fichiers .raw enregistres par le plugin (cle enregistre) et les convertit en PNG / npy.
Usage : python neural_lire.py dossier_tsc_neural dossier_sortie"""
import os, sys, glob, struct
import numpy as np
from PIL import Image
BPP = {10: 8, 2: 16, 28: 4, 29: 4, 87: 4, 91: 4, 19: 8, 20: 8, 41: 4, 39: 4, 40: 4}
def lire(f):
    b = open(f, 'rb').read(); magic, w, h, fmt, rp = struct.unpack('<5I', b[:20]); assert magic == 0x4E435354
    d = np.frombuffer(b, np.uint8, rp * h, 32).reshape(h, rp)[:, :w * BPP.get(fmt, 4)]
    if fmt == 10: return np.frombuffer(d.tobytes(), np.float16).reshape(h, w, 4).astype(np.float32)
    if fmt in (19, 20): return np.frombuffer(d.tobytes(), np.float32).reshape(h, w, 2)[..., 0]
    if fmt in (39, 40, 41): return np.frombuffer(d.tobytes(), np.float32).reshape(h, w)
    if fmt in (28, 29): return d.reshape(h, w, 4)
    if fmt in (87, 91): return d.reshape(h, w, 4)[..., [2, 1, 0, 3]]
    raise SystemExit(f'format {fmt} inconnu ({f})')
# 0.9.3 : le jeu rend les vues HDR dans l'ordre gauche, droite, centre mais les tonemappe gauche, centre, droite.
# Les fichiers hdr/prof/albedo et jeu8 d'un meme indice v ne sont donc PAS le meme ecran : on renomme par ecran.
ECRAN = {'hdr': ['gauche', 'droite', 'centre'], 'prof': ['gauche', 'droite', 'centre'], 'albedo': ['gauche', 'droite', 'centre'], 'jeu8': ['gauche', 'centre', 'droite']}
def nom_ecran(n):
    try:
        img, v, quoi = n.split('_'); e = ECRAN[quoi][int(v[1:])]; return f'{img}_{e}_{quoi}'
    except Exception: return n
def main():
    src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, '*.raw'))):
        a = lire(f); base = os.path.join(dst, nom_ecran(os.path.basename(f)[:-4]))
        np.save(base + '.npy', a)
        if a.ndim == 3 and a.dtype == np.uint8: Image.fromarray(a[..., :3]).save(base + '.png')
        elif a.ndim == 3: Image.fromarray(np.clip((a[..., :3] / (1 + a[..., :3])) ** (1 / 2.2) * 255, 0, 255).astype(np.uint8)).save(base + '.png')
        else: Image.fromarray(np.clip(a / max(a.max(), 1e-6) * 255, 0, 255).astype(np.uint8)).save(base + '.png')
        print(os.path.basename(f), a.shape, a.dtype)
if __name__ == '__main__': main()
