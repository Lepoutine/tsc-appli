# TSC Neural - caracteristiques par pixel, IDENTIQUES a celles du HLSL (fonction neural_ldr de tsc-graphics.hlsl).
# Entree : image du jeu en sRGB 0-1 (fichier jeu8 = etage apres tone mapping, sans effet TSC), tenseur (N,3,H,W).
# Pour chaque pixel : couleur du pixel, puis moyenne de 4 points en diagonale a 2, 6 et 16 px (voisinage proche, moyen, large),
# puis la hauteur dans l'ecran. Le reseau ne voit que ce voisinage : il ne peut PAS inventer d'objet, seulement changer la lumiere,
# les couleurs et le contraste local, et le meme pixel donne toujours la meme sortie (pas de scintillement ajoute).
import torch
import torch.nn.functional as F

RAYONS = (2, 6, 16)
N_ENTREES = 3 + 3 * len(RAYONS) + 1


def decale(x, dx, dy):
    """Lecture du pixel (x+dx, y+dy) avec bord replique (= adresse CLAMP de l'echantillonneur point du plugin)."""
    p = max(abs(dx), abs(dy))
    xp = F.pad(x, (p, p, p, p), mode="replicate")
    h, w = x.shape[-2:]
    return xp[..., p + dy:p + dy + h, p + dx:p + dx + w]


def caracteristiques(e):
    """e : (N,3,H,W) sRGB 0-1 -> (N,N_ENTREES,H,W)."""
    f = [e]
    for r in RAYONS:
        m = (decale(e, r, r) + decale(e, -r, r) + decale(e, r, -r) + decale(e, -r, -r)) * 0.25
        f.append(m)
    n, _, h, w = e.shape
    y = (torch.arange(h, device=e.device, dtype=e.dtype) + 0.5) / h
    f.append(y.view(1, 1, h, 1).expand(n, 1, h, w))
    return torch.cat(f, 1)
