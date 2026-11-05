# TSC Neural - caracteristiques par pixel, IDENTIQUES a celles du HLSL (fonction neural_ldr de tsc-graphics.hlsl).
# Entree : image du jeu en sRGB 0-1 (fichier jeu8 = etage apres tone mapping, sans effet TSC), tenseur (N,3,H,W).
# Pour chaque pixel : couleur du pixel, puis moyenne de 4 points en diagonale a 2, 6 et 16 px (voisinage proche, moyen, large),
# puis la hauteur dans l'ecran. Le reseau ne voit que ce voisinage : il ne peut PAS inventer d'objet, seulement changer la lumiere,
# les couleurs et le contraste local, et le meme pixel donne toujours la meme sortie (pas de scintillement ajoute).
import numpy as np
import torch
import torch.nn.functional as F

RAYONS = (2, 6, 16)
N_ENTREES = 3 + 3 * len(RAYONS) + 1
# v0.7 (plugin 0.18) : TSC Neural guide par le jeu. 6 canaux de plus par pixel, IDENTIQUES a neural_ldr du HLSL :
# albedo du G-buffer encode sRGB (3), distance log2(1+m)/10 bornee 0-1 (ciel 1, cabine 0), masque ciel, masque cabine.
N_GUIDE = 6
# v0.9 : coeur commun / adaptateur par jeu. Les constantes de profondeur viennent du profil du jeu (neural/profils/<jeu>.json,
# memes cles que l'ini du plugin). Profil par defaut : ets2 ; autre jeu : variable d'environnement TSC_PROFIL.
import json
import os

DOSSIER_PROFILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profils")


def charger_profil(nom=None):
    nom = nom or os.environ.get("TSC_PROFIL", "ets2")
    with open(os.path.join(DOSSIER_PROFILS, nom + ".json"), encoding="utf-8") as f:
        return json.load(f)


PROFIL = charger_profil()
_P = PROFIL.get("profondeur") or {"proche": 0.2, "plage_min": 0.01, "plage_max": 0.9, "decalage_z": 0.0}
PROCHE, PLAGE_MIN, PLAGE_MAX, DECALAGE_Z = _P["proche"], _P["plage_min"], _P["plage_max"], _P["decalage_z"]


def srgb_enc(x):
    x = x.clamp(0, 1)
    return torch.where(x <= 0.0031308, 12.92 * x, 1.055 * x.clamp_min(1e-8) ** (1 / 2.4) - 0.055)


def guide_depuis(prof, albedo):
    """prof : (H,W) profondeur du jeu (Z inverse), albedo : (H,W,>=3) lineaire ou None -> tenseur (6,H,W)."""
    d = torch.as_tensor(prof, dtype=torch.float32)
    ciel = (d <= 1e-7).float(); cab = (d > PLAGE_MAX).float()
    ndc = (d - PLAGE_MIN) / max(PLAGE_MAX - PLAGE_MIN, 1e-6) - DECALAGE_Z
    dist = PROCHE / ndc.clamp_min(1e-7)
    df = (torch.log2(1 + dist) / 10).clamp(0, 1)
    df = torch.where(ciel > 0, torch.ones_like(df), torch.where(cab > 0, torch.zeros_like(df), df))
    if albedo is not None:
        a = srgb_enc(torch.as_tensor(np.asarray(albedo)[..., :3], dtype=torch.float32)).permute(2, 0, 1)
    else:
        a = torch.zeros(3, *d.shape)
    return torch.cat([a, df[None], ciel[None], cab[None]], 0)


def decale(x, dx, dy):
    """Lecture du pixel (x+dx, y+dy) avec bord replique (= adresse CLAMP de l'echantillonneur point du plugin)."""
    p = max(abs(dx), abs(dy))
    xp = F.pad(x, (p, p, p, p), mode="replicate")
    h, w = x.shape[-2:]
    return xp[..., p + dy:p + dy + h, p + dx:p + dx + w]


def flou3(e):
    """v0.6 : moyenne 3x3 (bord replique), comme la boucle 3x3 de ps_ldr 0.17."""
    return F.avg_pool2d(F.pad(e, (1, 1, 1, 1), mode="replicate"), 3, 1)


def caracteristiques(e, centre=None, guide=None):
    """e : (N,3,H,W) sRGB 0-1 -> (N,N_ENTREES(+N_GUIDE),H,W). centre : couleur vue au pixel (v0.6 : image adoucie 3x3), sinon e.
    guide : (N,6,H,W) canaux du jeu (v0.7), ajoutes a la fin."""
    f = [e if centre is None else centre]
    for r in RAYONS:
        m = (decale(e, r, r) + decale(e, -r, r) + decale(e, r, -r) + decale(e, -r, -r)) * 0.25
        f.append(m)
    n, _, h, w = e.shape
    y = (torch.arange(h, device=e.device, dtype=e.dtype) + 0.5) / h
    f.append(y.view(1, 1, h, 1).expand(n, 1, h, w))
    if guide is not None:
        f.append(guide)
    return torch.cat(f, 1)
