#!/usr/bin/env python3
"""TSC Graphics 0.9.2 : apprend une table de couleurs 3D (tsc-graphics-lut.bin) qui amene la distribution de couleurs
des captures du jeu (sortie TSC avec ldr_lut = 0) vers celle des images reelles de meme ambiance.

Methode (pas de paires de pixels, les scenes different) : transfert lineaire Monge-Kantorovich (moyenne + covariance)
puis ajustement des histogrammes par canal (courbes 1D) ; le tout est cuit dans une grille 32x32x32. Une table ne
deforme rien et ne scintille pas : elle remplace une couleur par une autre, partout pareil.

Usage : python lut_apprendre.py --jeu dossier_captures_jeu --reel dossier_images_reelles --sortie tsc-graphics-lut.bin
        [--force 0.8] [--zone 0.22,0.08,0.78,0.55] [--apercu apercu.png]
Format de sortie : 32x32x32 texels RGBA 16 bits non signes (little endian), r le plus rapide, puis g, puis b ; sRGB.
"""
import argparse, glob, os, struct, sys
import numpy as np
from PIL import Image

N = 32

def charger(dossier, zone, max_px=400000):
    fichiers = sorted(glob.glob(os.path.join(dossier, '*.png')) + glob.glob(os.path.join(dossier, '*.jpg')) + glob.glob(os.path.join(dossier, '*.bmp')))
    if not fichiers: sys.exit('aucune image dans ' + dossier)
    px = []
    for f in fichiers:
        im = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32) / 255.0
        h, w, _ = im.shape
        x0, y0, x1, y1 = zone
        im = im[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].reshape(-1, 3)
        px.append(im)
    px = np.concatenate(px)
    l = px.max(1)
    px = px[(l > 0.02) & (l < 0.995)]          # sans noirs bouches ni blancs brules
    if len(px) > max_px: px = px[np.random.default_rng(1).choice(len(px), max_px, replace=False)]
    return px, len(fichiers)

def mkl(a, b):
    ca, cb = np.cov(a.T) + np.eye(3) * 1e-6, np.cov(b.T) + np.eye(3) * 1e-6
    wa, va = np.linalg.eigh(ca); ra = va @ np.diag(np.sqrt(np.maximum(wa, 1e-9))) @ va.T
    ira = va @ np.diag(1 / np.sqrt(np.maximum(wa, 1e-9))) @ va.T
    m = ra @ cb @ ra; wm, vm = np.linalg.eigh(m); rm = vm @ np.diag(np.sqrt(np.maximum(wm, 0))) @ vm.T
    return ira @ rm @ ira

def courbes(a, b, n=256):
    q = np.linspace(0, 1, n)
    return [(np.quantile(a[:, k], q), np.quantile(b[:, k], q)) for k in range(3)]

def appliquer(x, ma, mb, t, cs):
    y = (x - ma) @ t + mb
    y = np.stack([np.interp(y[:, k], cs[k][0], cs[k][1]) for k in range(3)], 1)
    return np.clip(y, 0, 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jeu', required=True); ap.add_argument('--reel', required=True); ap.add_argument('--sortie', required=True)
    ap.add_argument('--force', type=float, default=0.8); ap.add_argument('--zone', default='0.22,0.08,0.78,0.55'); ap.add_argument('--apercu')
    o = ap.parse_args()
    zone = [float(v) for v in o.zone.split(',')]
    a, na = charger(o.jeu, zone); b, nb = charger(o.reel, zone)
    ma, mb = a.mean(0), b.mean(0); t = mkl(a, b)
    cs = courbes((a - ma) @ t + mb, b)
    g = np.linspace(0, 1, N)
    bb, gg, rr = np.meshgrid(g, g, g, indexing='ij')                     # b le plus lent, r le plus rapide
    grille = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], 1)
    y = appliquer(grille, ma, mb, t, cs)
    y = grille + (y - grille) * o.force
    # lissage leger de la table (evite les marches) : moyenne 3x3x3 ponderee
    v = y.reshape(N, N, N, 3); p = np.pad(v, ((1, 1), (1, 1), (1, 1), (0, 0)), mode='edge')
    acc = np.zeros_like(v); wsum = 0
    for dz in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                w = 4.0 if (dx, dy, dz) == (0, 0, 0) else 1.0 / (abs(dx) + abs(dy) + abs(dz))
                acc += w * p[1 + dz:N + 1 + dz, 1 + dy:N + 1 + dy, 1 + dx:N + 1 + dx]; wsum += w
    y = np.clip(acc / wsum, 0, 1).reshape(-1, 3)
    q = np.round(y * 65535).astype('<u2')
    out = np.concatenate([q, np.full((len(q), 1), 65535, '<u2')], 1)
    open(o.sortie, 'wb').write(out.tobytes())
    print(f'table ecrite : {o.sortie} ({out.nbytes} octets), {na} images jeu, {nb} images reelles')
    print('moyenne jeu', np.round(ma * 255, 1), '-> reel', np.round(mb * 255, 1))
    if o.apercu:
        f = sorted(glob.glob(os.path.join(o.jeu, '*.png')) + glob.glob(os.path.join(o.jeu, '*.jpg')))[0]
        im = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32) / 255.0
        lut = y.reshape(N, N, N, 3)
        idx = np.clip(np.round(im * (N - 1)).astype(int), 0, N - 1)
        res = lut[idx[..., 2], idx[..., 1], idx[..., 0]]
        Image.fromarray(np.concatenate([im, res], 1).__mul__(255).astype(np.uint8)).save(o.apercu)
        print('apercu :', o.apercu)

if __name__ == '__main__':
    main()
