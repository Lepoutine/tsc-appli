# TSC Neural v0.8 - JUGE VISION : le juge d'entrainement s'appuie sur une IA de vision deja entrainee sur 142 millions d'images
# reelles (DINOv2 ViT-S/14 de Meta, poids sous licence Apache 2.0, usage commercial autorise). Le petit juge PatchGAN ne voyait
# que nos quelques centaines d'images : il apprenait mal ce qu'est une photo. Ici le "savoir du reel" vient de DINOv2 (gele,
# jamais modifie) et seules de petites tetes TSC sont entrainees au-dessus de 4 de ses couches.
# Methode publiee : Kumari et al., "Ensembling Off-the-shelf Models for GAN Training" (CVPR 2022, juge "vision-aided") et
# Richter et al., "Enhancing Photorealism Enhancement" (Intel, 2021 : G-buffer + juge sur caracteristiques pre-entrainees).
# IMPORTANT : DINOv2 ne sert QU'A l'entrainement, il ne va jamais dans le jeu (le jeu garde notre petit reseau TSC Neural).
# Il ne doit pas non plus servir a MESURER le resultat (le juge de mesure reste independant : sinon on se note soi-meme).
# Poids : fichier model.safetensors du depot Hugging Face timm/vit_small_patch14_dinov2.lvd142m (~88 Mo), donne par --juge_vision.
# v0.8.1 : architecture et lecteur safetensors ecrits ici (aucun paquet a installer : timm/pyyaml ne s'installent pas en Python 3.15).
import torch
import torch.nn as nn
import torch.nn.functional as F

COUCHES = (2, 5, 8, 11)
MOY = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
ECT = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def lire_safetensors(fichier):
    """Lecteur safetensors sans dependance (format public : 8 octets = taille de l'en-tete JSON, en-tete, puis donnees brutes)."""
    import json, struct
    types = {"F32": torch.float32, "F16": torch.float16, "BF16": torch.bfloat16}
    with open(fichier, "rb") as fo:
        n = struct.unpack("<Q", fo.read(8))[0]
        tete = json.loads(fo.read(n))
        brut = fo.read()
    sd = {}
    for k, v in tete.items():
        if k == "__metadata__":
            continue
        a, b = v["data_offsets"]
        t = torch.frombuffer(bytearray(brut[a:b]), dtype=types[v["dtype"]]).reshape(v["shape"])
        sd[k] = t.float()
    return sd


class _Bloc(nn.Module):
    def __init__(self, d, tetes):
        super().__init__()
        self.tetes = tetes
        self.norm1 = nn.LayerNorm(d, eps=1e-6); self.norm2 = nn.LayerNorm(d, eps=1e-6)
        self.attn = nn.Module(); self.attn.qkv = nn.Linear(d, 3 * d); self.attn.proj = nn.Linear(d, d)
        self.ls1 = nn.Module(); self.ls1.gamma = nn.Parameter(torch.ones(d))
        self.ls2 = nn.Module(); self.ls2.gamma = nn.Parameter(torch.ones(d))
        self.mlp = nn.Module(); self.mlp.fc1 = nn.Linear(d, 4 * d); self.mlp.fc2 = nn.Linear(4 * d, d)

    def forward(self, x):
        B, N, C = x.shape
        q, k, v = self.attn.qkv(self.norm1(x)).reshape(B, N, 3, self.tetes, C // self.tetes).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v).transpose(1, 2).reshape(B, N, C)
        x = x + self.ls1.gamma * self.attn.proj(a)
        return x + self.ls2.gamma * self.mlp.fc2(F.gelu(self.mlp.fc1(self.norm2(x))))


class DinoS14(nn.Module):
    """ViT-S/14 DINOv2, memes noms de poids que timm (vit_small_patch14_dinov2.lvd142m) : aucun paquet a installer."""
    num_prefix_tokens = 1

    def __init__(self, d=384, profondeur=12, tetes=6, grille=37):
        super().__init__()
        self.embed_dim, self.grille = d, grille
        self.patch_embed = nn.Module(); self.patch_embed.proj = nn.Conv2d(3, d, 14, 14)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d))
        self.pos_embed = nn.Parameter(torch.zeros(1, 1 + grille * grille, d))
        self.blocks = nn.ModuleList([_Bloc(d, tetes) for _ in range(profondeur)])
        self.norm = nn.LayerNorm(d, eps=1e-6)

    def jetons(self, x):
        t = self.patch_embed.proj(x)
        B, C, H, W = t.shape
        t = t.flatten(2).transpose(1, 2)
        pe = self.pos_embed
        if (H, W) != (self.grille, self.grille):   # = resample_abs_pos_embed de timm (bicubique, antialias)
            g = pe[:, 1:].reshape(1, self.grille, self.grille, C).permute(0, 3, 1, 2)
            g = F.interpolate(g, size=(H, W), mode="bicubic", antialias=True).permute(0, 2, 3, 1).reshape(1, H * W, C)
            pe = torch.cat([pe[:, :1], g], 1)
        return torch.cat([self.cls_token.expand(B, -1, -1), t], 1) + pe


def creer_dino(fichier=None):
    m = DinoS14()
    if fichier:
        sd = lire_safetensors(fichier)
        manque, inattendu = m.load_state_dict(sd, strict=False)
        inattendu = [k for k in inattendu if not k.startswith("head")]
        if manque or inattendu:
            raise SystemExit(f"poids DINOv2 incompatibles : manque {manque[:5]}, inattendu {inattendu[:5]}")
    else:   # tests uniquement : poids aleatoires
        for q in m.parameters():
            nn.init.normal_(q, 0, 0.02) if q.dim() > 1 else None
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
        t = m.jetons(x)
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


class Appariement:
    """v0.8.3 : tirage des morceaux reels APPARIES au contenu des morceaux du jeu (methode d'Intel, Richter et al. 2021).
    Sans cela le juge reconnait le jeu a son CONTENU (cabine, foret, autoroute...) que notre petit reseau ne peut pas changer :
    il pousse alors le contraste au hasard (run5v : ecart 1,045 -> 1,114). Chaque morceau reel est indexe par sa signature
    DINOv2 (moyenne des jetons de la couche 11) ; pour un morceau du jeu on tire un des k morceaux reels les plus proches."""

    def __init__(self, J, banque, t, appareil, pas=0.5, k=8):
        self.J, self.t, self.app, self.pas, self.k = J, t, appareil, pas, k
        self.pos, self.sig = [], []
        self.mettre_a_jour(banque, range(len(banque.im)))

    def n(self):
        return sum(len(p) for p in self.pos)

    @torch.no_grad()
    def signature(self, x):
        f = self.J.caracteristiques(x.to(self.app))[-1]
        return F.normalize(f.mean((2, 3)), dim=1)

    @torch.no_grad()
    def mettre_a_jour(self, banque, indices):
        while len(self.pos) < len(banque.im):
            self.pos.append([]); self.sig.append(None)
        for k in indices:
            x = banque.im[k]
            h, w = x.shape[1:]
            t = min(self.t, h, w); s = max(1, int(t * self.pas))
            pos = [(i, j) for i in range(0, h - t + 1, s) for j in range(0, w - t + 1, s)]
            m = torch.stack([banque.morceau(k, i, j, t, False) for i, j in pos])
            self.pos[k] = [(i, j, t) for i, j in pos]
            self.sig[k] = torch.cat([self.signature(m[a:a + 64]) for a in range(0, len(m), 64)]).cpu()
        self._tout = torch.cat(self.sig); self._ref = [(k, q) for k in range(len(self.pos)) for q in range(len(self.pos[k]))]

    @torch.no_grad()
    def lot(self, banque, x, gen):
        sim = self.signature(x[:, :3]).cpu() @ self._tout.T
        meilleurs = sim.topk(min(self.k, sim.shape[1]), dim=1).indices
        out = []
        for b in range(x.shape[0]):
            k, q = self._ref[int(meilleurs[b, gen.randrange(meilleurs.shape[1])])]
            i, j, t = self.pos[k][q]
            out.append(banque.morceau(k, i, j, t, gen.random() < 0.5))
        return torch.stack(out)
