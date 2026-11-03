# TSC Textures IA - reseau d'agrandissement x4 specialise textures de decor ETS2 -> rendu reel.
# Code TSC (Truck So Clean France). Reseau compact : rapide a entrainer sur une carte, rapide a appliquer sur des milliers de textures.
import torch
import torch.nn as nn
import torch.nn.functional as F


class Bloc(nn.Module):
    """Bloc residuel : 2 convolutions 3x3, activation douce, mise a l'echelle 0,2 pour un apprentissage stable."""
    def __init__(self, c):
        super().__init__()
        self.a = nn.Conv2d(c, c, 3, padding=1)
        self.b = nn.Conv2d(c, c, 3, padding=1)
        self.act = nn.PReLU(c)

    def forward(self, x):
        return x + 0.2 * self.b(self.act(self.a(x)))


class TSCTex(nn.Module):
    """Agrandit x4 une texture du jeu. Le reseau predit le DETAIL au-dessus d'un agrandissement bicubique :
    les couleurs et la forme du jeu restent, l'IA ajoute la matiere (grain, fissures, fibres) apprise sur le reel."""
    def __init__(self, canaux=64, blocs=16, echelle=4):
        super().__init__()
        self.echelle = echelle
        self.entree = nn.Conv2d(3, canaux, 3, padding=1)
        self.corps = nn.Sequential(*[Bloc(canaux) for _ in range(blocs)])
        self.fin_corps = nn.Conv2d(canaux, canaux, 3, padding=1)
        self.haut = nn.Sequential(
            nn.Conv2d(canaux, canaux * 4, 3, padding=1), nn.PixelShuffle(2), nn.PReLU(canaux),
            nn.Conv2d(canaux, canaux * 4, 3, padding=1), nn.PixelShuffle(2), nn.PReLU(canaux),
        )
        self.sortie = nn.Conv2d(canaux, 3, 3, padding=1)
        nn.init.zeros_(self.sortie.weight)   # depart = bicubique pur : jamais pire que l'agrandissement simple au debut
        nn.init.zeros_(self.sortie.bias)

    def forward(self, x):
        base = F.interpolate(x, scale_factor=self.echelle, mode="bicubic", align_corners=False)
        f = self.entree(x)
        f = f + self.fin_corps(self.corps(f))
        return base + self.sortie(self.haut(f))


def sn(m):
    return nn.utils.spectral_norm(m)


class Juge(nn.Module):
    """Discriminateur par morceaux : juge si chaque zone de ~70 px ressemble a une vraie matiere photographiee."""
    def __init__(self, c=64):
        super().__init__()
        self.r = nn.Sequential(
            sn(nn.Conv2d(3, c, 4, 2, 1)), nn.LeakyReLU(0.2, True),
            sn(nn.Conv2d(c, c * 2, 4, 2, 1)), nn.LeakyReLU(0.2, True),
            sn(nn.Conv2d(c * 2, c * 4, 4, 2, 1)), nn.LeakyReLU(0.2, True),
            sn(nn.Conv2d(c * 4, c * 4, 3, 1, 1)), nn.LeakyReLU(0.2, True),
            sn(nn.Conv2d(c * 4, 1, 3, 1, 1)),
        )

    def forward(self, x):
        return self.r(x)


def charger(chemin, appareil="cpu"):
    e = torch.load(chemin, map_location=appareil, weights_only=True)
    m = TSCTex(**e.get("config", {}))
    m.load_state_dict(e["poids"])
    return m.to(appareil).eval(), e
