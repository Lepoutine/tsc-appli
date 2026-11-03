# TSC Neural - entrainement sur la carte graphique (Quadro RTX 6000 chez Mendy).
#   python entrainer.py --jeu <dossier images jeu8 PNG> --reel <dossier images reelles> --hlsl <tsc-graphics.hlsl> --sortie <dossier>
# Images du jeu : fichiers *_jeu8.png de neural_lire.py (enregistrement du plugin, cle enregistre, SANS effet TSC).
# Images reelles : images extraites des videos de Mendy (jpg/png). Donnees privees : jamais publiees.
# Regles : 10 % des images de chaque cote sont mises de cote (jamais vues a l'entrainement) pour juger ; un modele n'est
# exporte que s'il bat le champion precedent sur ces images ; chaque version est gardee (retour arriere possible).
import argparse, glob, json, os, random, time
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from modele import TSCNeural, Discriminateur
import exporter

EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


def lister(d, motif=None):
    l = [p for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if p.lower().endswith(EXT)]
    if motif:
        l2 = [p for p in l if motif in os.path.basename(p)]
        l = l2 or l
    return sorted(l)


def charger(p, hauteur):
    im = Image.open(p).convert("RGB")
    if hauteur and im.height != hauteur:
        im = im.resize((max(1, round(im.width * hauteur / im.height)), hauteur), Image.BICUBIC)
    return torch.from_numpy(np.asarray(im, np.float32) / 255).permute(2, 0, 1)


class Banque:
    """Images gardees en memoire (RAM), tirage de morceaux aleatoires a echelle variable."""
    def __init__(self, chemins, hauteur, t):
        self.im = [charger(p, hauteur) for p in chemins]; self.t = t

    def lot(self, n, gen):
        out = []
        for _ in range(n):
            x = self.im[gen.randrange(len(self.im))]
            k = gen.uniform(0.8, 1.25); t = min(int(self.t * k), x.shape[1], x.shape[2])
            i = gen.randrange(x.shape[1] - t + 1); j = gen.randrange(x.shape[2] - t + 1)
            m = x[:, i:i + t, j:j + t]
            if t != self.t:
                m = F.interpolate(m[None], size=(self.t, self.t), mode="bilinear", align_corners=False)[0]
            if gen.random() < 0.5:
                m = m.flip(-1)
            out.append(m)
        return torch.stack(out)


def lum(x):
    return 0.2126 * x[:, 0:1] + 0.7152 * x[:, 1:2] + 0.0722 * x[:, 2:3]


def flou(x, r):
    k = 2 * r + 1
    return F.avg_pool2d(F.pad(x, (r, r, r, r), mode="replicate"), k, 1)


@torch.no_grad()
def stats(x):
    """Signature d'image comparee au reel : tons (p1, p50, p99), saturation, detail fin/moyen, contraste local."""
    l = lum(x)
    q = torch.quantile(l.flatten()[::7], torch.tensor([0.01, 0.25, 0.5, 0.75, 0.99], device=x.device))
    mx = x.max(1, keepdim=True)[0]; mn = x.min(1, keepdim=True)[0]
    sat = ((mx - mn) / mx.clamp_min(1e-3)).mean()
    d1 = (l - flou(l, 1)).abs().mean(); d3 = (flou(l, 1) - flou(l, 4)).abs().mean(); d8 = (flou(l, 4) - flou(l, 12)).abs().mean()
    c = x.mean((0, 2, 3))
    return torch.cat([q, torch.stack([sat, d1 * 10, d3 * 10, d8 * 10]), c - c.mean()]).cpu()


@torch.no_grad()
def ecart(m, jeu, ref_stats, appareil):
    """Ecart (plus bas = plus proche du reel) entre la signature des images du jeu passees dans le reseau et celle du reel."""
    s = []
    for x in jeu:
        y = m(x[None].to(appareil)) if m is not None else x[None].to(appareil)
        s.append(stats(y))
    s = torch.stack(s).mean(0)
    return float((s - ref_stats).abs().sum())


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--jeu", required=True); a.add_argument("--reel", required=True)
    a.add_argument("--hlsl", required=True); a.add_argument("--sortie", required=True)
    a.add_argument("--iterations", type=int, default=20000); a.add_argument("--taille", type=int, default=256)
    a.add_argument("--lot", type=int, default=12); a.add_argument("--hauteur", type=int, default=1080)
    a.add_argument("--structure", type=float, default=4.0, help="poids qui garde les contours du jeu (anti-invention)")
    a.add_argument("--identite", type=float, default=0.5, help="poids qui garde le reseau proche de l'image du jeu")
    a.add_argument("--depart", default="", help="modele.pt a reprendre (apprentissage continu)")
    a.add_argument("--graine", type=int, default=1)
    o = a.parse_args()
    os.makedirs(o.sortie, exist_ok=True)
    appareil = "cuda" if torch.cuda.is_available() else "cpu"
    print("appareil :", appareil, torch.cuda.get_device_name(0) if appareil == "cuda" else "")
    gen = random.Random(o.graine); torch.manual_seed(o.graine)

    pj = lister(o.jeu, "_jeu8"); pr = lister(o.reel)
    if len(pj) < 5 or len(pr) < 5:
        raise SystemExit(f"pas assez d'images : jeu {len(pj)}, reel {len(pr)}")
    gen.shuffle(pj); gen.shuffle(pr)
    nj, nr = max(1, len(pj) // 10), max(1, len(pr) // 10)
    test_j, train_j, test_r, train_r = pj[:nj], pj[nj:], pr[:nr], pr[nr:]
    json.dump({"test_jeu": test_j, "test_reel": test_r}, open(os.path.join(o.sortie, "jeu_de_test.json"), "w"), indent=1)
    print(f"images jeu {len(train_j)} (+{nj} test), reel {len(train_r)} (+{nr} test)")
    BJ, BR = Banque(train_j, 0, o.taille), Banque(train_r, o.hauteur, o.taille)
    tj = [charger(p, 0) for p in test_j]
    tr = [charger(p, o.hauteur) for p in test_r]
    ref = torch.stack([stats(x[None].to(appareil)) for x in tr]).mean(0)

    G, D = TSCNeural().to(appareil), Discriminateur().to(appareil)
    if o.depart:
        G.load_state_dict(torch.load(o.depart, map_location=appareil, weights_only=True)["modele"])
    oG = torch.optim.Adam(G.parameters(), 2e-4, betas=(0.5, 0.99)); oD = torch.optim.Adam(D.parameters(), 2e-4, betas=(0.5, 0.99))

    champion_f = os.path.join(o.sortie, "champion.json")
    champion = json.load(open(champion_f)) if os.path.exists(champion_f) else None
    base = ecart(None, tj, ref, appareil)
    # plancher = ecart entre deux lots d'images REELLES (le reel ne peut pas faire mieux que lui-meme)
    plancher = ecart(None, [charger(p, o.hauteur) for p in train_r[:min(40, len(train_r))]], ref, appareil)
    pct = lambda e: 100 * max(e - plancher, 0) / max(base - plancher, 1e-6)
    # regle Mendy 03/11 23:45 : ecart au reel restant <= 10 % (du chemin jeu brut -> reel) pour parler de photorealisme
    meilleur = champion["ecart"] if champion else base
    print(f"ecart au reel : jeu brut {base:.4f} (100 %), reel contre reel {plancher:.4f} (0 %)" + (f", champion {meilleur:.4f} ({pct(meilleur):.0f} %)" if champion else ""))
    journal = open(os.path.join(o.sortie, "journal.txt"), "a", encoding="utf-8")
    t0 = time.time()
    for it in range(1, o.iterations + 1):
        x = BJ.lot(o.lot, gen).to(appareil); r = BR.lot(o.lot, gen).to(appareil)
        y = G(x)
        # discriminateur : reel = 1, jeu transforme = 0 (moindres carres)
        lD = ((D(r) - 1) ** 2).mean() + (D(y.detach()) ** 2).mean()
        oD.zero_grad(set_to_none=True); lD.backward(); oD.step()
        # generateur : tromper le juge, garder les contours et la scene du jeu
        la = ((D(y) - 1) ** 2).mean()
        ly, lx = lum(y), lum(x)
        ls = F.l1_loss(ly - flou(ly, 2), lx - flou(lx, 2) * 1.0) * 0.5 + F.l1_loss(flou(ly, 2) - flou(ly, 8), flou(lx, 2) - flou(lx, 8))
        li = F.l1_loss(flou(y, 8), flou(x, 8))
        lG = la + o.structure * ls + o.identite * li
        oG.zero_grad(set_to_none=True); lG.backward(); oG.step()
        if it % 200 == 0:
            ligne = f"{it} D {lD.item():.3f} G {la.item():.3f} structure {ls.item():.4f} identite {li.item():.4f} {time.time() - t0:.0f} s"
            print(ligne); journal.write(ligne + "\n"); journal.flush()
        if it % 2000 == 0 or it == o.iterations:
            G.eval(); e = ecart(G, tj, ref, appareil); G.train()
            nom = os.path.join(o.sortie, f"modele_{it:06d}.pt")
            torch.save({"modele": G.state_dict(), "ecart": e, "iteration": it}, nom)
            ligne = f"== {it} : ecart au reel {e:.4f} = {pct(e):.0f} % restant (objectif <= 10 %) ; jeu brut {base:.4f}, meilleur {meilleur:.4f}"
            print(ligne); journal.write(ligne + "\n"); journal.flush()
            if e < meilleur:
                meilleur = e
                torch.save({"modele": G.state_dict(), "ecart": e, "iteration": it}, os.path.join(o.sortie, "champion.pt"))
                exporter.ecrire(G, o.hlsl, os.path.join(o.sortie, "tsc-graphics.hlsl"), note=f"iteration {it}, ecart {e:.4f}")
                json.dump({"ecart": e, "pourcent_restant": pct(e), "objectif_10pc": pct(e) <= 10, "iteration": it, "jeu_brut": base, "plancher_reel": plancher, "fichier": nom}, open(champion_f, "w"), indent=1)
                apercu(G, tj[:3], appareil, os.path.join(o.sortie, f"apercu_{it:06d}.png"))
                print("   -> nouveau champion, HLSL ecrit dans", o.sortie)
    print("fini. meilleur ecart", meilleur, "(jeu brut", base, ")")


@torch.no_grad()
def apercu(G, imgs, appareil, chemin):
    """Planche avant (jeu) / apres (TSC Neural), cote a cote."""
    G.eval(); lignes = []
    for x in imgs:
        y = G(x[None].to(appareil))[0].cpu()
        lignes.append(torch.cat([x, y], 2))
    G.train()
    w = max(l.shape[2] for l in lignes)
    p = torch.cat([F.pad(l, (0, w - l.shape[2])) for l in lignes], 1)
    Image.fromarray((p.permute(1, 2, 0).clamp(0, 1).numpy() * 255).astype(np.uint8)).save(chemin)


if __name__ == "__main__":
    main()
