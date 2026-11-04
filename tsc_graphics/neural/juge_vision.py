# TSC Neural v0.8 - JUGE VISION : le juge d'entrainement s'appuie sur une IA de vision deja entrainee sur 142 millions d'images
# reelles (DINOv2 ViT-S/14 de Meta, poids sous licence Apache 2.0, usage commercial autorise). Le petit juge PatchGAN ne voyait
# que nos quelques centaines d'images : il apprenait mal ce qu'est une photo. Ici le "savoir du reel" vient de DINOv2 (gele,
# jamais modifie) et seules de petites tetes TSC sont entrainees au-dessus de 4 de ses couches.
# Methode publiee : Kumari et al., "Ensembling Off-the-shelf Models for GAN Training" (CVPR 2022, juge "vision-aided") et
# Richter et al., "Enhancing Photorealism Enhancement" (Intel, 2021 : G-buffer + juge sur caracteristiques pre-entrainees).
# IMPORTANT : DINOv2 ne sert QU'A l'entrainement, il ne va jamais dans le jeu (le jeu garde notre petit reseau TSC Neural).
# Il ne doit pas non plus servir a MESURER le resultat (le juge de mesure reste independant : sinon on se note soi-meme).
# Poids : fichier model.safetensors du depot Hugging Face timm/vit_small_patch14_dinov2.lvd142m (~88 Mo), donne par --juge_vision.
import torch
import torch.nn as nn
import torch.nn.functional as F

COUCHES = (2, 5, 8, 11)
MOY = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
ECT = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def creer_dino(fichier=None):
    import timm
    kw = dict(dynamic_img_size=True, num_classes=0)
    if fichier:
        m = timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=True, pretrained_cfg_overlay=dict(file=fichier), **kw)
    else:   # tests uniquement : poids aleatoires
        m = timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=False, **kw)
    return m.eval()


def augmente(x, gen=None):
    """DiffAugment (translation + decoupe) applique pareil au reel et au jeu : le juge ne peut pas apprendre par coeur."""
    n, _, h, w = x.shape
    dx, dy = int(w * 0.125), int(h * 0.125)
    tx = torch.randint(-dx, dx + 1, (1,), generator=gen).item(); ty = torch.randint(-dy, dy + 1, (1,), generator=gen).item()
    x = torch.roll(F.pad(x, (dx, dx, dy, dy), mode="reflect"), (ty, tx), (2, 3))[..., dy:dy + h, dx:dx + w]
    cy, cx = torch.randint(0, h // 2, (1,), generator=gen).item(), torch.randint(0, w // 2, (1,), generator=gen).item()
    masque = torch.ones_like(x[:, :1]); masque[..., cy:cy + h // 4, cx:cx + w // 4] = 0
    return x * masque


class JugeVision(nn.Module):
    def __init__(self, fichier=None, taille=224, largeur=256):
        super().__init__()
        self.dino = creer_dino(fichier)
        for q in self.dino.parameters():
            q.requires_grad_(False)
        self.taille = taille
        d = self.dino.embed_dim
        sn = nn.utils.spectral_norm
        self.tetes = nn.ModuleList([nn.Sequential(sn(nn.Conv2d(d, largeur, 1)), nn.LeakyReLU(0.2, True), sn(nn.Conv2d(largeur, 1, 1)))
                                    for _ in COUCHES])

    def train(self, mode=True):
        super().train(mode); self.dino.eval(); return self   # DINOv2 reste toujours en mode evaluation

    def caracteristiques(self, x):
        x = F.interpolate(x, size=(self.taille, self.taille), mode="bilinear", align_corners=False, antialias=True)
        x = (x - MOY.to(x)) / ECT.to(x)
        m = self.dino
        t = m.patch_embed(x)
        t = m._pos_embed(t)
        t = m.norm_pre(t)
        g = self.taille // 14
        sorties = []
        for i, b in enumerate(m.blocks):
            t = b(t)
            if i in COUCHES:
                p = t[:, m.num_prefix_tokens:]
                sorties.append(p.transpose(1, 2).reshape(p.shape[0], -1, g, g))
            if i >= COUCHES[-1]:
                break
        return sorties

    def forward(self, x, gen=None):
        """x : (N,3,H,W) sRGB 0-1 -> liste de cartes de notes (une par couche), reel = 1, jeu transforme = 0."""
        f = self.caracteristiques(augmente(x, gen))
        return [h(c) for h, c in zip(self.tetes, f)]


def perte_juge(J, reel, faux):
    return sum(((a - 1) ** 2).mean() + (b ** 2).mean() for a, b in zip(J(reel), J(faux))) / len(COUCHES)


def perte_generateur(J, faux):
    return sum(((a - 1) ** 2).mean() for a in J(faux)) / len(COUCHES)
