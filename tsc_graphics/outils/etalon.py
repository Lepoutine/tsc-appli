"""TSC Graphics - etalonnage cale sur des videos de conduite reelle.

Mesure les images reelles et les images du jeu par ambiance, en deduit une transformation couleur (3D LUT)
et les reglages des passes spatiales (voile optique, douceur), puis fabrique les apercus avant / apres.
Les images reelles ne servent qu'a la mesure : elles ne sont jamais incluses dans ce que livre TSC.

  python3 -I etalon.py mesurer  <dossier_images> <index.csv|-> <sortie.json> [zone]
  python3 -I etalon.py ajuster  <reel.json> <jeu.json> <sortie_dir>
  python3 -I etalon.py appliquer <reglages_dir> <ambiance> <image> <sortie.jpg>
"""
import csv
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

N_LUT = 33
BANDES = [(0.0, 0.15), (0.15, 0.6), (0.6, 1.01)]   # ombres, tons moyens, hautes lumieres (luminance lineaire)
LUMA = np.array([0.2126, 0.7152, 0.0722])

# zones de mesure (fractions x0, y0, x1, y1) : la route vue par le pare-brise, sans capot ni tableau de bord
ZONES = {
    'video': (0.10, 0.12, 0.90, 0.62),
    'cabine': (0.25, 0.25, 0.65, 0.58),
    'plein': (0.0, 0.0, 1.0, 1.0),
}


def srgb_vers_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_vers_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def charger(path, zone, largeur=640):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    x0, y0, x1, y1 = ZONES[zone]
    im = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    im.thumbnail((largeur, largeur))
    return srgb_vers_lin(np.asarray(im, dtype=np.float32) / 255.0)


def chroma(lin):
    """Saturation simple : (max - min) / max, sur l'image lineaire."""
    mx = lin.max(axis=-1)
    mn = lin.min(axis=-1)
    return np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0.0)


def masque_vegetation(lin):
    r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    return (g > r * 1.05) & (g > b * 1.15) & (g > 0.02)


def masque_ciel(lin):
    h = lin.shape[0]
    haut = np.zeros(lin.shape[:2], bool)
    haut[: h // 3] = True
    y = lin @ LUMA
    return haut & (y > np.percentile(y, 70)) & (chroma(lin) < 0.45)


def mesurer_images(paths, zone):
    lum, sat_bandes, veg, ciel = [], [[] for _ in BANDES], [], []
    for p in paths:
        lin = charger(p, zone)
        y = lin @ LUMA
        s = chroma(lin)
        lum.append(y.ravel())
        for i, (a, b) in enumerate(BANDES):
            m = (y >= a) & (y < b)
            if m.any():
                sat_bandes[i].append(s[m])
        mv = masque_vegetation(lin)
        if mv.sum() > 50:
            veg.append(lin[mv])
        mc = masque_ciel(lin)
        if mc.sum() > 50:
            ciel.append(lin[mc])
    lum = np.concatenate(lum)
    return {
        'images': len(paths),
        'percentiles': np.percentile(lum, np.arange(101)).tolist(),
        'saturation_bandes': [float(np.mean(np.concatenate(v))) if v else None for v in sat_bandes],
        'vegetation': np.concatenate(veg).mean(axis=0).tolist() if veg else None,
        'ciel': np.concatenate(ciel).mean(axis=0).tolist() if ciel else None,
        'contraste_local': float(np.mean([contraste_local(charger(p, zone)) for p in paths[:40]])),
    }


def contraste_local(lin):
    y = lin_vers_srgb(lin @ LUMA)
    im = Image.fromarray((y * 255).astype(np.uint8))
    flou = np.asarray(im.filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255.0
    return float(np.mean(np.abs(y - flou)))


def cmd_mesurer(dossier, index, sortie, zone='video'):
    groupes = {}
    if index != '-':
        with open(index, newline='', encoding='utf-8-sig') as f:
            texte = f.read()
        delim = ';' if texte.split('\n', 1)[0].count(';') > texte.split('\n', 1)[0].count(',') else ','
        if True:
            for r in csv.DictReader(texte.splitlines(), delimiter=delim):
                amb = (r.get('ambiance') or '').strip().lower()
                ctx = (r.get('contexte') or '').strip().lower()
                if not amb or amb.startswith('jeu') or ctx in ('arret', 'arrêt', 'hors route'):
                    continue
                p = os.path.join(dossier, r['fichier'].replace('\\', '/'))
                if os.path.exists(p):
                    groupes.setdefault(amb, []).append(p)
    else:
        for amb in sorted(os.listdir(dossier)):
            d = os.path.join(dossier, amb)
            if os.path.isdir(d):
                groupes[amb] = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    res = {amb: mesurer_images(ps, zone) for amb, ps in groupes.items() if ps}
    with open(sortie, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    for amb, m in res.items():
        p = m['percentiles']
        print(f"{amb:12s} {m['images']:4d} images  lum p5/50/95/99 {p[5]:.3f}/{p[50]:.3f}/{p[95]:.3f}/{p[99]:.3f}  "
              f"sat {[round(x, 3) if x else None for x in m['saturation_bandes']]}  contraste {m['contraste_local']:.3f}")


# ---------------------------------------------------------------- ajustement

def courbe_tons(p_jeu, p_reel, pente_max=3.0):
    """Courbe monotone luminance jeu -> luminance reelle, par correspondance de percentiles, lissee et bornee."""
    x = np.asarray(p_jeu, float)
    y = np.asarray(p_reel, float)
    x = np.maximum.accumulate(x + np.arange(len(x)) * 1e-6)
    y = np.maximum.accumulate(y)
    xs = np.linspace(0, 1, 256)
    ys = np.interp(xs, np.concatenate([[0], x, [1]]), np.concatenate([[0], y, [max(y[-1], 1.0)]]))
    # lissage + pente bornee (pas de cassure visible, pas d'ecrasement)
    k = np.ones(9) / 9
    ys = np.convolve(np.pad(ys, 4, mode='edge'), k, mode='valid')
    d = np.clip(np.diff(ys), 1.0 / (pente_max * 255), pente_max / 255)
    ys = np.concatenate([[ys[0]], ys[0] + np.cumsum(d)])
    ys = (ys - ys[0]) / max(ys[-1] - ys[0], 1e-6) * (min(y[-1] * 1.02, 1.0) - y[0]) + y[0]
    return xs, np.clip(ys, 0, 1)


def ajuster_ambiance(reel, jeu):
    xs, ys = courbe_tons(jeu['percentiles'], reel['percentiles'])
    sat = []
    for sr, sj in zip(reel['saturation_bandes'], jeu['saturation_bandes']):
        sat.append(1.0 if not sr or not sj else float(np.clip(sr / sj, 0.6, 1.8)))
    veg = None
    if reel.get('vegetation') and jeu.get('vegetation'):
        vr = np.asarray(reel['vegetation']); vj = np.asarray(jeu['vegetation'])
        veg = ((vr / vr.sum()) / (vj / vj.sum())).tolist()   # rapport de teinte normalise (pas de luminosite)
    ciel = None
    if reel.get('ciel') and jeu.get('ciel'):
        cr = np.asarray(reel['ciel']); cj = np.asarray(jeu['ciel'])
        ciel = ((cr / cr.sum()) / (cj / cj.sum())).tolist()
    # douceur : rapprocher le contraste local du jeu de celui du reel (fraction du detail retiree)
    douceur = float(np.clip(1 - reel['contraste_local'] / max(jeu['contraste_local'], 1e-4), 0.0, 0.5))
    # voile optique : remonte les noirs comme la diffusion d'une vraie optique / d'un pare-brise
    voile = float(np.clip(reel['percentiles'][2] - jeu['percentiles'][2], 0.0, 0.06))
    return {'courbe_x': xs.tolist(), 'courbe_y': ys.tolist(), 'saturation': sat, 'vegetation': veg, 'ciel': ciel,
            'douceur': douceur, 'voile': voile}


def lut_depuis_reglages(r, n=N_LUT):
    g = np.linspace(0, 1, n)
    b, gg, rr = np.meshgrid(g, g, g, indexing='ij')
    c = srgb_vers_lin(np.stack([rr, gg, b], -1))   # entree : couleur sRGB de l'image du jeu
    y = c @ LUMA
    y2 = np.interp(y, r['courbe_x'], r['courbe_y'])
    out = c * (y2 / np.maximum(y, 1e-5))[..., None]
    # saturation par bande de luminance (transitions douces)
    w = np.stack([1 - smooth(y2, 0.08, 0.22), smooth(y2, 0.08, 0.22) * (1 - smooth(y2, 0.45, 0.75)), smooth(y2, 0.45, 0.75)], -1)
    s = (w * np.asarray(r['saturation'])).sum(-1)
    yo = out @ LUMA
    out = yo[..., None] + (out - yo[..., None]) * s[..., None]
    if r.get('vegetation'):
        m = np.clip(((c[..., 1] - np.maximum(c[..., 0], c[..., 2])) / np.maximum(c[..., 1], 1e-4)) * 4, 0, 1)
        t = np.asarray(r['vegetation']); t = t / (t @ LUMA)
        out = out * (1 - m[..., None]) + out * t * m[..., None]
    out = np.clip(out, 0, 1)
    return lin_vers_srgb(out)   # sortie sRGB


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def ecrire_cube(lut, path, titre):
    n = lut.shape[0]
    with open(path, 'w') as f:
        f.write(f'TITLE "{titre}"\nLUT_3D_SIZE {n}\n')
        for bi in range(n):
            for gi in range(n):
                for ri in range(n):
                    v = lut[bi, gi, ri]
                    f.write(f'{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')


def cmd_ajuster(reel_json, jeu_json, sortie):
    reel = json.load(open(reel_json)); jeu = json.load(open(jeu_json))
    os.makedirs(sortie, exist_ok=True)
    tout = {}
    for amb in reel:
        j = jeu.get(amb) or jeu.get('jour') or next(iter(jeu.values()))
        r = ajuster_ambiance(reel[amb], j)
        tout[amb] = r
        ecrire_cube(lut_depuis_reglages(r), os.path.join(sortie, f'tsc_{amb}.cube'), f'TSC Graphics {amb}')
        print(f"{amb:12s} sat {[round(x, 2) for x in r['saturation']]} douceur {r['douceur']:.2f} voile {r['voile']:.3f}")
    with open(os.path.join(sortie, 'reglages.json'), 'w') as f:
        json.dump(tout, f, indent=1)


# ---------------------------------------------------------------- application (apercus, meme calcul que le shader)

def appliquer_lut(img_srgb, lut):
    n = lut.shape[0]
    p = img_srgb * (n - 1)
    i0 = np.clip(np.floor(p).astype(int), 0, n - 2)
    f = p - i0
    out = 0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[..., 0] if dr else 1 - f[..., 0]) * (f[..., 1] if dg else 1 - f[..., 1]) * (f[..., 2] if db else 1 - f[..., 2])
                out = out + w[..., None] * lut[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    return out


def flou(img, rayon):
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(rayon)), dtype=np.float32) / 255.0


def rendu_tsc(img_srgb, r, lut):
    """Passes dans l'ordre du plugin : LUT, douceur (detail fin attenue), voile optique (diffusion des lumieres)."""
    out = appliquer_lut(img_srgb, lut)
    if r['douceur'] > 0:
        out = out - r['douceur'] * (out - flou(out, 1.2))
    if r['voile'] > 0:
        lin = srgb_vers_lin(out)
        diff = srgb_vers_lin(flou(out, max(out.shape[:2]) / 40))
        lin = lin * (1 - r['voile'] * 4) + diff * r['voile'] * 4 + r['voile'] * 0.25
        out = lin_vers_srgb(lin)
    return np.clip(out, 0, 1)


def cmd_appliquer(reglages_dir, amb, image, sortie):
    tout = json.load(open(os.path.join(reglages_dir, 'reglages.json')))
    r = tout[amb]
    lut = lut_depuis_reglages(r)
    img = np.asarray(Image.open(image).convert('RGB'), dtype=np.float32) / 255.0
    out = rendu_tsc(img, r, lut)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(sortie, quality=92)


# ---------------------------------------------------------------- rendu photo TSC (v2) : exposition comme une vraie camera

def boite(a, r):
    """Moyenne sur une fenetre (2r+1)^2 par sommes cumulees (bords reflechis)."""
    p = np.pad(a, ((r + 1, r), (r + 1, r)) + ((0, 0),) * (a.ndim - 2), mode='reflect')
    c = p.cumsum(0).cumsum(1)
    s = c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]
    return s / float((2 * r + 1) ** 2)


def filtre_guide(i, p, r, eps):
    """Filtre guide (He et al.) : flou qui respecte les contours (pas de halo autour des vitres)."""
    mi, mp = boite(i, r), boite(p, r)
    a = (boite(i * p, r) - mi * mp) / (boite(i * i, r) - mi * mi + eps)
    b = mp - a * mi
    return boite(a, r) * i + boite(b, r)


def rendu_photo(img_srgb, p):
    """Passes du shader TSC Graphics, dans le meme ordre :
    1. luminance log, decomposee en grandes zones (filtre guide) et detail fin ;
    2. grandes zones : ecart dehors / dedans agrandi (macro), exposition visee ;
    3. detail fin attenue (douceur d'une vraie optique) ;
    4. courbe film (epaule douce, noirs releves par le voile) ;
    5. couleur : balance des blancs, saturation par tranche, vegetation ;
    6. diffusion des lumieres (bloom large, pare-brise) ;
    """
    lin = srgb_vers_lin(img_srgb)
    y = np.maximum(lin @ LUMA, 1e-4)
    ly = np.log2(y)
    h, w = ly.shape
    r = max(4, int(min(h, w) / 30))
    small = ly[::4, ::4]
    base_s = filtre_guide(small, small, max(2, r // 4), 0.4)
    base = np.asarray(Image.fromarray(base_s.astype(np.float32), mode='F').resize((w, h), Image.BILINEAR))
    detail = ly - base
    moy = np.percentile(base, 60)
    nb = moy + (base - moy) * p['macro'] + p['expo']
    # les grandes zones tres claires (ciel, vitres) sont compressees en log : pas de ciel blanc brule
    hi = p.get('haut', 0.0)
    nb = np.where(nb > hi, hi + (nb - hi) * p.get('haut_pente', 0.35), nb)
    ny = nb + detail * p['micro']
    y2 = 2.0 ** ny
    out = lin * (y2 / y)[..., None]
    # courbe film : epaule douce (pas d'ecretage dur), voile = noirs releves
    # courbe film (Reinhard etendu) : epaule douce, blanc atteint seulement a 'blanc' (pas d'ecretage dur)
    W = p.get('blanc', 4.0)
    out = out * p['epaule']
    out = out * (1 + out / (W * W)) / (1 + out)
    out = out * (1 - p['voile']) + p['voile'] * 0.06
    # couleur
    out = out * np.asarray(p['balance'])[None, None, :]
    yo = out @ LUMA
    w3 = np.stack([1 - smooth(yo, 0.03, 0.12), smooth(yo, 0.03, 0.12) * (1 - smooth(yo, 0.3, 0.7)), smooth(yo, 0.3, 0.7)], -1)
    s = (w3 * np.asarray(p['sat'])).sum(-1)
    out = yo[..., None] + (out - yo[..., None]) * s[..., None]
    if p.get('vegetation'):
        c = lin
        m = np.clip(((c[..., 1] - np.maximum(c[..., 0], c[..., 2])) / np.maximum(c[..., 1], 1e-4)) * 3, 0, 1)
        t = np.asarray(p['vegetation']); t = t / (t @ LUMA)
        out = out * (1 - m[..., None] * p['veg_force']) + out * t * (m[..., None] * p['veg_force'])
    # diffusion : les zones claires (vitres, ciel) debordent un peu, comme un vrai pare-brise / objectif
    if p['diffusion'] > 0:
        clair = np.clip(out - 0.6, 0, None)
        dif = srgb_vers_lin(flou(lin_vers_srgb(clair), max(h, w) / 60))
        out = out + dif * p['diffusion']
    return np.clip(lin_vers_srgb(np.clip(out, 0, 1)), 0, 1)


LOOKS = {
    # jour : dehors lumineux et laiteux comme une camera, cabine dans l'ombre mais lisible
    'jour': dict(macro=1.3, expo=0.9, haut=-0.6, haut_pente=0.3, micro=0.80, epaule=1.0, blanc=3.0, voile=0.035,
                 balance=[1.0, 1.0, 1.0], sat=[1.0, 0.97, 0.95], vegetation=[0.95, 1.0, 0.85], veg_force=0.5, diffusion=0.35),
    # gris : ciel blanc couvert, peu de contraste, couleurs eteintes, leger bleu
    'gris': dict(macro=1.15, expo=1.15, haut=-0.7, haut_pente=0.3, micro=0.65, epaule=1.0, blanc=3.0, voile=0.05,
                 balance=[0.97, 1.0, 1.04], sat=[0.85, 0.80, 0.70], vegetation=[0.92, 1.0, 0.9], veg_force=0.4, diffusion=0.25),
    # pluie : comme gris, plus sombre, brume (voile fort), detail adouci par l'eau sur le pare-brise
    'pluie': dict(macro=1.1, expo=0.6, haut=-0.8, haut_pente=0.3, micro=0.55, epaule=1.0, blanc=3.0, voile=0.07,
                  balance=[0.96, 1.0, 1.05], sat=[0.80, 0.78, 0.70], vegetation=[0.92, 1.0, 0.92], veg_force=0.4, diffusion=0.3),
    # crepuscule : chaud, contre-jour, halo marque autour du soleil
    'crepuscule': dict(macro=1.3, expo=0.6, haut=-0.4, haut_pente=0.35, micro=0.75, epaule=1.0, blanc=3.0, voile=0.03,
                       balance=[1.06, 1.0, 0.92], sat=[0.95, 1.0, 1.05], vegetation=[1.0, 1.0, 0.85], veg_force=0.3, diffusion=0.5),
    # nuit : noirs profonds, lumieres franches qui bavent (eblouissement), pas de voile
    'nuit': dict(macro=1.4, expo=0.0, haut=0.5, haut_pente=0.5, micro=0.85, epaule=1.0, blanc=2.0, voile=0.01,
                 balance=[1.0, 0.98, 1.0], sat=[0.9, 1.0, 1.05], vegetation=None, veg_force=0.0, diffusion=0.6),
}


def cmd_photo(amb, image, sortie, look_json=None):
    p = dict(LOOKS[amb])
    if look_json:
        p.update(json.load(open(look_json)))
    img = np.asarray(Image.open(image).convert('RGB'), dtype=np.float32) / 255.0
    out = rendu_photo(img, p)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(sortie, quality=92)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'mesurer':
        cmd_mesurer(*sys.argv[2:])
    elif c == 'ajuster':
        cmd_ajuster(*sys.argv[2:5])
    elif c == 'appliquer':
        cmd_appliquer(*sys.argv[2:6])
    elif c == 'photo':
        cmd_photo(*sys.argv[2:])
    else:
        print(__doc__)
