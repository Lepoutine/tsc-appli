"""TSC Neural Graphics : banc d'essai HORS JEU du shader « route mouillee v1 » (tsc-graphics.hlsl 0.3).

Rejoue, sur une image VIDEE du jeu (cible HDR + profondeur reelles d'ETS2, ecrites par le socle TSCF), exactement le calcul
du pixel shader ps_principal, en numpy. Sert a mettre au point la methode sans relancer le jeu. Ce n'est pas une preuve du
rendu en jeu : le cout GPU, la stabilite dans le temps et le mouvement ne se mesurent qu'en jeu.

Format des vidages (FORMAT.md, deduit des octets) : en-tete 20 octets = 'TSCF', largeur, hauteur, format DXGI, octets/pixel
(uint32), puis les pixels sans pitch. HDR = format 10 (RGBA16F, 8 o/px) ; profondeur = D32S8 (format 20, 8 o/px : float32 + 8 bits).

Usage : python3 -I banc_route_mouillee.py <hdr.bin> <profondeur.bin> <sortie.png> [humidite] [cle=valeur ...]
"""
import struct, sys
import numpy as np
import cv2

DEFAUT = dict(fov_v=43, proche=0.2, plage_min=0.01, plage_max=0.9, decalage_z=-0.000194, intensite=1, rugosite=0.12, flou=0.25, trainees=1.5,
              etirement=0.8, pas=0.12, epaisseur=0.5, f0=0.04, assombrir=0.35, peinture=0.6)
NMIPS = 6


def lire_vidage(chemin):
    b = open(chemin, 'rb').read()
    magie, w, h, fmt, opp = struct.unpack_from('<4sIIII', b, 0)
    if magie != b'TSCF':
        raise ValueError(f'{chemin} : en-tete inconnu {magie!r}')
    px = b[20:20 + w * h * opp]
    if fmt == 10:
        return np.frombuffer(px, np.float16).reshape(h, w, 4).astype(np.float32)
    if fmt in (20, 19) and opp == 8:   # D32_FLOAT_S8X24 : 4 octets de profondeur, puis stencil + bourrage
        return np.frombuffer(px, np.float32).reshape(h, w, 2)[..., 0].copy()
    if fmt in (40, 41) and opp == 4:
        return np.frombuffer(px, np.float32).reshape(h, w).copy()
    raise ValueError(f'{chemin} : format {fmt} ({opp} o/px) non gere')


class Tex:
    """Texture avec mips, lue comme SampleLevel (bilineaire, bord colle, interpolation entre niveaux)."""
    def __init__(self, img, nmips=1):
        self.m = [img.astype(np.float32)]
        for _ in range(nmips - 1):
            self.m.append(cv2.resize(self.m[-1], (max(1, self.m[-1].shape[1] // 2), max(1, self.m[-1].shape[0] // 2)), interpolation=cv2.INTER_AREA))

    def _niv(self, k, u, v, lin):
        t = self.m[k]; h, w = t.shape[:2]
        x = (u * w - 0.5).astype(np.float32); y = (v * h - 0.5).astype(np.float32)
        if not lin:
            xi = np.clip(np.floor(u * w), 0, w - 1).astype(np.int32); yi = np.clip(np.floor(v * h), 0, h - 1).astype(np.int32)
            return t[yi, xi]
        n = x.size; L = 2048; nn = -(-n // L) * L
        xp = np.zeros(nn, np.float32); yp = np.zeros(nn, np.float32); xp[:n] = x.ravel(); yp[:n] = y.ravel()
        r = cv2.remap(t, xp.reshape(-1, L), yp.reshape(-1, L), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        r = r.reshape((nn,) + t.shape[2:])[:n]
        return r.reshape(u.shape + t.shape[2:])

    def lire(self, u, v, lod=0.0, lin=True):
        if u.size == 0:
            return np.zeros(u.shape + self.m[0].shape[2:], np.float32)
        lod = np.broadcast_to(np.asarray(lod, np.float32), u.shape)
        if len(self.m) == 1 or not lin or np.all(lod == 0):
            return self._niv(0, u, v, lin)
        l0 = np.clip(np.floor(lod), 0, len(self.m) - 1).astype(int); f = lod - l0
        out = None
        for k in np.unique(l0):
            s = l0 == k
            a = self._niv(k, u[s], v[s], True); b = self._niv(min(k + 1, len(self.m) - 1), u[s], v[s], True)
            ff = f[s].reshape((-1,) + (1,) * (a.ndim - 1))
            r = a * (1 - ff) + b * ff
            if out is None: out = np.zeros(u.shape + r.shape[1:], np.float32)
            out[s] = r
        return out


def rendu(hdr, prof, humidite=0.7, **kw):
    R = dict(DEFAUT); R.update(kw)
    H, W = prof.shape
    tanv = np.tan(np.radians(R['fov_v']) / 2); asp = W / H
    col_t = Tex(hdr[..., :3], NMIPS); prof_t = Tex(prof[..., None], 1)
    def lineaire(d):
        ndc = (d - R['plage_min']) / max(R['plage_max'] - R['plage_min'], 1e-6) - R['decalage_z']
        return R['proche'] / np.maximum(ndc, 1e-7)
    def lirep(u, v): return prof_t.lire(u, v, lin=False)[..., 0]
    def posvue(u, v):
        z = lineaire(lirep(u, v)); nx = u * 2 - 1; ny = 1 - v * 2
        return np.stack([nx * tanv * asp * z, ny * tanv * z, z], -1)
    def versuv(p):
        return (p[..., 0] / (p[..., 2] * tanv * asp)) * 0.5 + 0.5, (p[..., 1] / (p[..., 2] * tanv)) * -0.5 + 0.5
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xs + 0.5) / W; v = (ys + 0.5) / H
    src = hdr[..., :3].astype(np.float32); d = prof
    ciel = d <= 1e-7; cab = d > R['plage_max']
    actif = ~(ciel | cab)
    P = posvue(u, v)
    tx, ty = 1 / W, 1 / H
    r_, l_ = posvue(u + tx, v), posvue(u - tx, v); up, bo = posvue(u, v - ty), posvue(u, v + ty)
    dx = np.where((np.abs(r_[..., 2] - P[..., 2]) < np.abs(P[..., 2] - l_[..., 2]))[..., None], r_ - P, P - l_)
    dy = np.where((np.abs(bo[..., 2] - P[..., 2]) < np.abs(P[..., 2] - up[..., 2]))[..., None], bo - P, P - up)
    N = np.cross(dx, dy); N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-12)
    haut = np.clip((N[..., 1] - 0.82) * 6, 0, 1)
    mouille = haut * humidite * actif
    m = mouille >= 0.01
    out = src.copy()
    # pixels mouilles seulement (comme la sortie anticipee du shader)
    iy, ix = np.nonzero(m)
    Pm, Nm, um, vm = P[m], N[m], u[m], v[m]
    V = Pm / np.linalg.norm(Pm, axis=-1, keepdims=True)
    pxx, pxy = xs[m] + 0.5, ys[m] + 0.5
    def bruit(a, b): return np.modf(52.9829189 * np.modf(a * 0.06711056 + b * 0.00583715)[0])[0]
    h1 = bruit(pxx, pxy); h2 = bruit(pxx + 37, pxy + 11)
    Nr = Nm + np.stack([(h1 - 0.5) * R['rugosite'] * 0.15, 0 * h1, (h2 - 0.5) * R['rugosite'] * R['trainees'] * 0.3], -1)
    Nr /= np.linalg.norm(Nr, axis=-1, keepdims=True)
    Rr = V - 2 * np.sum(V * Nr, -1, keepdims=True) * Nr
    pos = Pm + Nm * 0.03
    pas = R['pas'] * (0.5 + h1)
    n = len(um)
    refl = np.zeros((n, 3), np.float32); poids = np.zeros(n, np.float32)
    vivant = np.ones(n, bool)
    libre_u = np.full(n, -1.0, np.float32); libre_v = np.full(n, -1.0, np.float32)
    for k in range(64):
        if not vivant.any(): break
        idx = np.nonzero(vivant)[0]
        pos[idx] += Rr[idx] * pas[idx, None]; pas[idx] *= 1.06
        p = pos[idx]
        stop = p[:, 2] < R['proche']
        uu, vv = versuv(p)
        stop |= (uu < 0) | (uu > 1) | (vv < 0) | (vv > 1)
        vivant[idx[stop]] = False
        ok = ~stop
        idx, p, uu, vv = idx[ok], p[ok], uu[ok], vv[ok]
        ds = lirep(uu, vv)
        nc = ~(ds > R['plage_max'])
        idx, p, ds, uu, vv = idx[nc], p[nc], ds[nc], uu[nc], vv[nc]
        zs = np.where(ds <= 1e-7, 1e9, lineaire(ds))
        dz = p[:, 2] - zs
        dev = dz <= 0                                        # point du rayon encore devant la scene : visible
        libre_u[idx[dev]] = uu[dev]; libre_v[idx[dev]] = vv[dev]
        tou = (dz > 0) & (dz < R['epaisseur'] + pas[idx] * 2)
        if not tou.any(): continue
        j = idx[tou]
        a = pos[j] - Rr[j] * pas[j, None]; b = pos[j].copy()
        for _ in range(6):
            mm = (a + b) * 0.5; mu, mv = versuv(mm); dm = lirep(np.clip(mu, 0, 1), np.clip(mv, 0, 1))
            dedans = (mm[:, 2] - np.where(dm <= 1e-7, 1e9, lineaire(dm))) > 0
            b = np.where(dedans[:, None], mm, b); a = np.where(dedans[:, None], a, mm)
        hu, hv = versuv(b)
        l = np.linalg.norm(b - Pm[j], axis=-1)
        pxm = H / (2 * tanv * np.maximum(b[:, 2], R['proche']))
        lobe = np.maximum(1, R['flou'] * R['rugosite'] * l * pxm)
        lod = np.clip(np.log2(lobe), 0, NMIPS - 1)
        cosv0 = np.clip(np.sum(-V[j] * Nm[j], -1), 0, 1)
        ext = np.minimum(R['etirement'] * lobe / H / (cosv0 + 0.15), 0.06)
        acc = np.zeros((len(j), 3), np.float32); wt = np.zeros(len(j), np.float32)
        zh = b[:, 2]
        for t in range(-3, 4):
            o = t / 3.0
            tv_ = np.clip(hv + o * ext, 0, 1)
            dt_ = lirep(np.clip(hu, 0, 1), tv_)
            zt = np.where(dt_ <= 1e-7, 1e9, lineaire(dt_))
            w = np.exp(-o * o * 2) * np.exp(-np.abs(zt - zh) / (0.03 * zh))   # pas de fuite a travers les silhouettes
            acc += col_t.lire(np.clip(hu, 0, 1), tv_, lod) * w[:, None]; wt += w
        refl[j] = acc / np.maximum(wt, 1e-6)[:, None]
        e = np.maximum(np.abs(hu - 0.5) * 2, np.abs(hv - 0.5) * 2)
        poids[j] = np.clip(1 - e ** 6, 0, 1) * np.clip(1.2 - k / 64.0, 0, 1)
        vivant[j] = False
    # rayon sorti de l'image sans impact : dernier point encore visible, poids 0,35 (jamais un point cache)
    q = (poids == 0) & (libre_u >= 0)
    refl[q] = col_t.lire(libre_u[q], libre_v[q], NMIPS - 2); poids[q] = 0.35
    # voile du ciel
    sansref = (poids == 0) & (Rr[:, 1] > 0)
    for s in range(1, 17):
        q = np.nonzero(sansref)[0]
        if not len(q): break
        u2, v2 = um[q], vm[q] * (1 - s / 16.0)
        c = lirep(u2, v2) <= 1e-7
        qq = q[c]
        refl[qq] = col_t.lire(u2[c], v2[c], NMIPS - 1); poids[qq] = 0.6; sansref[qq] = False
    cosv = np.clip(np.sum(-V * Nm, -1), 0, 1)
    F = R['f0'] + (1 - R['f0']) * (1 - cosv) ** 5
    col = src[m]
    lw = np.array([0.2126, 0.7152, 0.0722], np.float32)
    lc = col @ lw
    lm = col_t.lire(um, vm, min(3, NMIPS - 1)) @ lw
    peint = np.clip((lc / np.maximum(lm, 1e-4) - 1.3) * 2.5, 0, 1)
    mo = mouille[m]
    loin = np.clip(1 - (Pm[:, 2] - 150) / 150, 0, 1)          # fondu de 150 a 300 m
    spec = mo * (1 - R['peinture'] * peint) * loin
    base = col * (1 - R['assombrir'] * mo * (1 - 0.6 * peint))[:, None]
    gris = lc * (1 - R['assombrir'] * mo)
    base = np.maximum(0, gris[:, None] + (base - gris[:, None]) * (1 + 0.15 * mo)[:, None])
    out[m] = base + refl * (poids * F * spec * R['intensite'])[:, None]
    return out, dict(pixels_mouilles=float(m.mean()), reflets_touches=float((poids > 0).mean()) if n else 0.0)


def ecran(hdr, expo=None):
    """Affichage approximatif (le vrai tone mapping du jeu n'est pas reproduit) : exposition par la mediane + Reinhard + sRGB."""
    l = hdr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    if expo is None: expo = 0.18 / max(float(np.median(l[l > 0])) if (l > 0).any() else 1, 1e-4)
    x = hdr * expo; x = x / (1 + x)
    x = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055)
    return (np.clip(x, 0, 1) * 255).astype(np.uint8), expo


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 3: print(__doc__); sys.exit(1)
    hum = float(a[3]) if len(a) > 3 else 0.7
    kw = {k: float(v) for k, v in (x.split('=') for x in a[4:])}
    hdr = lire_vidage(a[0]); prof = lire_vidage(a[1])
    if prof.ndim == 3: prof = prof[..., 0]
    out, st = rendu(hdr[..., :3], prof, hum, **kw)
    g, e = ecran(hdr[..., :3]); dte, _ = ecran(out, e)
    for img, t in ((g, 'ETS2 (vidage reel, effet coupe)'), (dte, 'route mouillee v1 - banc HORS JEU, meme calcul que le shader')):
        cv2.putText(img, t, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(img, t, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(a[2], cv2.cvtColor(np.concatenate([g, dte], 1), cv2.COLOR_RGB2BGR))
    print(st)
