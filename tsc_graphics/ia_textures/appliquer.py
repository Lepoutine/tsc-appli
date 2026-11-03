# TSC Textures IA - applique le modele champion a des textures du jeu (PNG, RGB ou RGBA) -> versions x4 fideles au reel.
#   python appliquer.py --modele modeles\champion.pt --entree textures_png --sortie textures_hd_png
# Garde-fous par texture : couleur et luminance du jeu conservees ; si l'IA invente (detail peu lie au jeu, motif regulier),
# son detail est reduit ou retire. L'alpha (decoupe du feuillage, speculaire) est agrandi a part.
import argparse, csv, os
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from modele import charger
from degradation import flou_gauss
import mesures


@torch.no_grad()
def agrandir(m, x, appareil, tuile=192, marge=16):
    """Par tuiles avec recouvrement : memoire constante quelle que soit la taille de la texture."""
    n, c, h, w = x.shape
    out = torch.zeros(n, c, h * 4, w * 4)
    poids = torch.zeros(1, 1, h * 4, w * 4)
    for y in range(0, h, tuile):
        for x0 in range(0, w, tuile):
            ya, xa = max(y - marge, 0), max(x0 - marge, 0)
            yb, xb = min(y + tuile + marge, h), min(x0 + tuile + marge, w)
            t = x[:, :, ya:yb, xa:xb].to(appareil)
            with torch.autocast(appareil, enabled=appareil == "cuda"):
                r = m(t).float().cpu()
            out[:, :, ya * 4:yb * 4, xa * 4:xb * 4] += r
            poids[:, :, ya * 4:yb * 4, xa * 4:xb * 4] += 1
    return out / poids


def caler_couleur(sr, base):
    """Garde les couleurs et la lumiere du jeu (basses frequences de la base), ne prend de l'IA que le detail."""
    return flou_gauss(base, 3.0) + (sr - flou_gauss(sr, 3.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modele", required=True)
    ap.add_argument("--entree", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--seuil_bas", type=float, default=0.35)
    ap.add_argument("--seuil_haut", type=float, default=0.5)
    a = ap.parse_args()
    appareil = "cuda" if torch.cuda.is_available() else "cpu"
    m, info = charger(a.modele, appareil)
    os.makedirs(a.sortie, exist_ok=True)
    rap = csv.writer(open(os.path.join(a.sortie, "rapport_ia.csv"), "w", newline="", encoding="utf-8"), delimiter=";")
    rap.writerow(["texture", "largeur", "hauteur", "correlation", "cellules_ia", "cellules_base", "poids_detail_ia"])
    fichiers = sorted(f for f in os.listdir(a.entree) if f.lower().endswith(".png"))
    for k, f in enumerate(fichiers):
        sortie = os.path.join(a.sortie, f)
        if os.path.exists(sortie):
            continue   # reprise : ce qui est fait n'est pas refait
        im = Image.open(os.path.join(a.entree, f))
        rgba = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
        x = torch.from_numpy(rgba[..., :3]).permute(2, 0, 1)[None].contiguous()
        base = F.interpolate(x, scale_factor=4, mode="bicubic", align_corners=False).clamp(0, 1)
        sr = caler_couleur(agrandir(m, x, appareil), base).clamp(0, 1)
        cor = mesures.correlation_detail(sr, base)
        ce_ia, ce_base = mesures.cellules(sr), mesures.cellules(base)
        w = 1.0 if cor >= a.seuil_haut else (0.5 if cor >= a.seuil_bas else 0.0)
        if ce_ia > 1.5 * ce_base + 5:
            w = min(w, 0.3)   # motif regulier invente : detail fortement reduit
        sr = (base + w * (sr - base)).clamp(0, 1)
        o = (sr[0].permute(1, 2, 0).numpy() * 255 + 0.5).astype(np.uint8)
        if im.mode in ("RGBA", "LA") or "transparency" in im.info:
            al = torch.from_numpy(rgba[..., 3])[None, None]
            al4 = F.interpolate(al, scale_factor=4, mode="bicubic", align_corners=False).clamp(0, 1)[0, 0].numpy()
            v = rgba[..., 3]
            if ((v < 0.05) | (v > 0.95)).mean() > 0.9:   # decoupe (feuillage, grillage) : bord net, meme seuil que le jeu
                al4 = (al4 > 0.5).astype(np.float32)
            o = np.dstack([o, (al4 * 255 + 0.5).astype(np.uint8)])
        Image.fromarray(o).save(sortie)
        rap.writerow([f, o.shape[1], o.shape[0], f"{cor:.3f}", f"{ce_ia:.1f}", f"{ce_base:.1f}", w])
        if k % 25 == 0:
            print(f"{k + 1}/{len(fichiers)} {f} correlation {cor:.2f} poids {w}", flush=True)
    print("TERMINE", flush=True)


if __name__ == "__main__":
    main()
