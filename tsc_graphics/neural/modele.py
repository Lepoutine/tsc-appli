# TSC Neural - reseaux. Generateur = petit perceptron par pixel (convolutions 1x1 sur les caracteristiques), assez leger pour
# tourner dans l'etage LDR du plugin en ~1 ms sur 3 ecrans. Juge d'entrainement = discriminateur par zones (PatchGAN) qui apprend
# a reconnaitre le reel ; il ne sert qu'a l'entrainement et ne va jamais dans le jeu.
import torch
import torch.nn as nn
from caracteristiques import N_ENTREES, caracteristiques, flou3

CACHE = 24
DELTA_MAX = 0.35   # le reseau corrige au plus de 0,35 en sRGB par canal : il retouche, il ne repeint pas


class TSCNeural(nn.Module):
    def __init__(self, cache=CACHE):
        super().__init__()
        self.c1 = nn.Conv2d(N_ENTREES, cache, 1)
        self.c2 = nn.Conv2d(cache, cache, 1)
        self.c3 = nn.Conv2d(cache, 3, 1)
        nn.init.zeros_(self.c3.weight); nn.init.zeros_(self.c3.bias)   # depart = image du jeu inchangee

    detail_garde = True   # v0.6 / plugin 0.17 : le reseau voit l'image adoucie 3x3, le detail fin du jeu passe tel quel

    def forward(self, e):
        eb = flou3(e) if self.detail_garde else None
        f = caracteristiques(e, eb)
        h = torch.relu(self.c1(f))
        h = torch.relu(self.c2(h))
        d = torch.tanh(self.c3(h)) * DELTA_MAX
        if eb is not None:   # = ps_ldr 0.17 : saturate(enc(saturate(eb + d)) + (e - eb))
            return ((eb + d).clamp(0, 1) + (e - eb)).clamp(0, 1)
        return (e + d).clamp(0, 1)


class Discriminateur(nn.Module):
    def __init__(self, c=48):
        super().__init__()
        sn = nn.utils.spectral_norm   # v0.4 : juge bride (run2 : le juge gagnait apres 12 000 et le reseau derivait)
        def bloc(i, o, s):
            return [sn(nn.Conv2d(i, o, 4, s, 1)), nn.LeakyReLU(0.2, True)]
        self.m = nn.Sequential(*bloc(3, c, 2), *bloc(c, 2 * c, 2), *bloc(2 * c, 4 * c, 2), *bloc(4 * c, 4 * c, 1),
                               sn(nn.Conv2d(4 * c, 1, 4, 1, 1)))

    def forward(self, x):
        return self.m(x * 2 - 1)
