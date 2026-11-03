# TSC Textures IA - donnees d'apprentissage : vraies matieres (photos CC0 haute definition) + images de conduite reelles de Mendy.
# Rien n'est publie : les donnees restent sur le PC.
import os
import numpy as np
import torch
from PIL import Image

EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def lister(dossier):
    r = []
    for base, _, fichiers in os.walk(dossier):
        for f in fichiers:
            if f.lower().endswith(EXT):
                r.append(os.path.join(base, f))
    return sorted(r)


def ouvrir(chemin, cote_max=4096):
    im = Image.open(chemin).convert("RGB")
    if max(im.size) > cote_max:
        k = cote_max / max(im.size)
        im = im.resize((max(16, int(im.width * k)), max(16, int(im.height * k))), Image.LANCZOS)
    return im


class Source:
    """Un dossier d'images, avec son poids et sa facon d'etre lu.
    video = True : images de conduite (compression YouTube) -> reduites de moitie pour ne pas apprendre les blocs de la video,
    et morceaux tires surtout dans la moitie basse (route, bas-cote, murs proches)."""
    def __init__(self, dossier, poids=1.0, video=False):
        self.fichiers = lister(dossier)
        self.poids, self.video, self.dossier = poids, video, dossier
        self.cache = {}

    def image(self, i):
        f = self.fichiers[i]
        if f not in self.cache:
            im = ouvrir(f)
            if self.video:
                im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
            a = np.asarray(im, dtype=np.float32) / 255.0
            if len(self.cache) > 300:
                self.cache.pop(next(iter(self.cache)))
            self.cache[f] = a
        return self.cache[f]


class Tirage:
    """Tire des morceaux HR de taille t (multiple de 16) ; rejette les morceaux plats (ciel, aplats) qui n'apprennent rien."""
    def __init__(self, sources, t=192, graine=None):
        self.sources = [s for s in sources if s.fichiers]
        if not self.sources:
            raise SystemExit("aucune image d'apprentissage trouvee")
        p = np.array([s.poids for s in self.sources], dtype=np.float64)
        self.p = p / p.sum()
        self.t = t
        self.rng = np.random.default_rng(graine)

    def morceau(self):
        for _ in range(20):
            s = self.sources[self.rng.choice(len(self.sources), p=self.p)]
            a = s.image(int(self.rng.integers(len(s.fichiers))))
            h, w = a.shape[:2]
            t = self.t
            if h < t or w < t:
                continue
            y0 = int(self.rng.integers(h // 2 if s.video and h >= 2 * t else 0, h - t + 1))
            x0 = int(self.rng.integers(0, w - t + 1))
            m = a[y0:y0 + t, x0:x0 + t]
            if m.std() < 0.02:
                continue
            k = int(self.rng.integers(4))
            m = np.rot90(m, k) if not s.video else m   # les videos gardent le haut et le bas (lumiere du ciel)
            if self.rng.uniform() < 0.5:
                m = m[:, ::-1]
            return np.ascontiguousarray(m)
        return np.ascontiguousarray(m)

    def lot(self, n):
        x = np.stack([self.morceau() for _ in range(n)])
        return torch.from_numpy(x).permute(0, 3, 1, 2).contiguous()
