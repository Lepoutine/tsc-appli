# (c) 2026 Truck So Clean France. Juge de l'atelier Spartan Studio : « ce rendu de livree ressemble-t-il a un vrai camion ? »
# Meme methode que TSC Graphics (juge_vision.py, copie du commit 07b2957 de tsc_graphics/neural) :
#   - DINOv2 ViT-S/14 (Meta, poids Apache 2.0) GELE, jamais modifie : il apporte le « savoir du reel » (142 M d'images) ;
#   - references = photos REELLES LIBRES de camions (collecte_photos.py, CC0 / CC BY, auteur et source notes) ;
#   - APPARIEMENT (lecon de Graphics run5v) : chaque morceau du rendu n'est compare qu'aux morceaux reels qui lui ressemblent
#     le plus (k plus proches), sinon le juge reconnait le contenu (fond de studio, route) au lieu de la qualite ;
#   - juge fixe : 1 photo sur 10 (crc32 du nom), jamais dans la banque, sert d'etalon « vrai contre vrai » ;
#   - aucun entrainement : score = proximite des morceaux du rendu aux vrais morceaux, divisee par celle de l'etalon.
#     realisme 1,00 = aussi proche du reel qu'une vraie photo jamais vue ; plus bas = plus « jeu video ».
# Ce score est UN critere : c'est l'oeil de Mendy qui tranche (regles intelligence/apprentissage/regles.json).
#   python juge_atelier.py --poids model.safetensors --reel photos_reelles --rendus captures_atelier --sortie juge_resultats.json
import argparse, json, os, zlib

import torch
import torch.nn.functional as F

from juge_vision import creer_dino, MOY, ECT, COUCHES

EXT = (".jpg", ".jpeg", ".png", ".webp")


def est_juge(nom):
    return zlib.crc32(os.path.basename(nom).encode("utf-8")) % 10 == 0


def charger(fichier, cote=448):
    from PIL import Image
    im = Image.open(fichier).convert("RGB")
    im.thumbnail((cote * 2, cote * 2))
    x = torch.from_numpy(__import__("numpy").asarray(im).copy()).permute(2, 0, 1).float() / 255
    return x


class Juge:
    def __init__(self, poids=None, taille=224, pas=0.5, k=8, appareil="cpu"):
        self.dino = creer_dino(poids).to(appareil)
        for q in self.dino.parameters():
            q.requires_grad_(False)
        self.t, self.pas, self.k, self.app = taille, pas, k, appareil

    def morceaux(self, x):
        """Decoupe l'image (3,H,W) en morceaux carres de cote min(H,W)/2 environ, au pas de 50 %."""
        h, w = x.shape[1:]
        t = max(64, min(h, w) // 2); s = max(1, int(t * self.pas))
        return torch.stack([x[:, i:i + t, j:j + t] for i in range(0, h - t + 1, s) for j in range(0, w - t + 1, s)])

    @torch.no_grad()
    def signatures(self, m):
        """Signature DINOv2 de chaque morceau : jetons de la derniere couche utilisee, moyennes, normalises."""
        out = []
        for a in range(0, len(m), 32):
            x = F.interpolate(m[a:a + 32].to(self.app), size=(self.t, self.t), mode="bilinear", align_corners=False, antialias=True)
            x = (x - MOY.to(x)) / ECT.to(x)
            t = self.dino.jetons(x)
            for i, b in enumerate(self.dino.blocks):
                t = b(t)
                if i >= COUCHES[-1]:
                    break
            out.append(F.normalize(t[:, self.dino.num_prefix_tokens:].mean(1), dim=1).cpu())
        return torch.cat(out)

    def proximite(self, sig, banque):
        """Moyenne, sur les morceaux, de la similarite moyenne aux k morceaux reels les plus proches (appariement)."""
        sim = sig @ banque.T
        return sim.topk(min(self.k, banque.shape[0]), dim=1).values.mean(1)


def images(dossier):
    return sorted(os.path.join(dossier, f) for f in os.listdir(dossier) if f.lower().endswith(EXT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poids", required=True, help="model.safetensors de timm/vit_small_patch14_dinov2.lvd142m")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--rendus", required=True)
    ap.add_argument("--sortie", default="juge_resultats.json")
    ap.add_argument("--k", type=int, default=8)
    a = ap.parse_args()
    app = "cuda" if torch.cuda.is_available() else "cpu"
    J = Juge(a.poids, k=a.k, appareil=app)
    reel = images(a.reel)
    banque, etalon = [], []
    for f in reel:
        s = J.signatures(J.morceaux(charger(f)))
        (etalon if est_juge(f) else banque).append(s)
    if len(etalon) < 3 or not banque:
        raise SystemExit(f"pas assez de photos reelles : {len(banque)} en banque, {len(etalon)} etalons (3 minimum)")
    B = torch.cat(banque)
    ref = torch.cat([J.proximite(s, B) for s in etalon]).mean().item()
    res = {"juge": "DINOv2 ViT-S/14 gele, appariement k=%d" % a.k, "photos_banque": len(banque), "photos_etalon": len(etalon),
           "proximite_etalon_reel": round(ref, 4), "rendus": []}
    for f in images(a.rendus):
        p = J.proximite(J.signatures(J.morceaux(charger(f))), B)
        res["rendus"].append({"fichier": os.path.basename(f), "realisme": round(p.mean().item() / ref, 4),
                              "pire_morceau": round(p.min().item() / ref, 4)})
    json.dump(res, open(a.sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in res["rendus"]:
        print(f"{r['fichier']:40s} realisme {r['realisme']:.3f}  (pire morceau {r['pire_morceau']:.3f})")
    print(f"etalon : {len(etalon)} vraies photos jamais vues = 1,000")


if __name__ == "__main__":
    main()
