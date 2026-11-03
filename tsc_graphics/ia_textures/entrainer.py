# TSC Textures IA - entrainement. Exemple :
#   python entrainer.py --matieres D:\bibliotheque_libre --videos D:\reel_images --sortie modeles --iterations 60000
# Reprend depuis --depart (le champion actuel) si donne : l'IA continue d'apprendre au lieu de repartir de zero.
import argparse, copy, json, os, time
import torch
import torch.nn.functional as F
from modele import TSCTex, Juge
from degradation import degrader
from donnees import Source, Tirage
import mesures


def perte_frequences(a, b):
    """Compare les spectres du detail : force le reseau a rendre le GRAIN reel, pas une moyenne lisse."""
    fa = torch.fft.rfft2(mesures.hautes_freq(a)).abs(); fb = torch.fft.rfft2(mesures.hautes_freq(b)).abs()
    return F.l1_loss(torch.log1p(fa), torch.log1p(fb))


def jeu_de_test(sources, chemin, n=48, t=256):
    """Jeu de test FIXE : cree une seule fois puis toujours le meme, pour comparer les versions honnetement."""
    if os.path.exists(chemin):
        return torch.load(chemin, weights_only=True)
    tir = Tirage(sources, t=t, graine=1234)
    hr = tir.lot(n)
    import numpy as np
    lr = torch.cat([degrader(hr[i:i + 1], gen=np.random.default_rng(i)) for i in range(n)])
    d = {"hr": hr, "lr": lr}
    torch.save(d, chemin)
    return d


@torch.no_grad()
def evaluer(m, test, appareil):
    m.eval()
    out = []
    for i in range(0, test["lr"].shape[0], 8):
        out.append(m(test["lr"][i:i + 8].to(appareil)).clamp(0, 1).cpu())
    s = torch.cat(out); hr = test["hr"]
    base = F.interpolate(test["lr"], scale_factor=4, mode="bicubic", align_corners=False).clamp(0, 1)
    r = {"psnr": mesures.psnr(s, hr), "psnr_bicubique": mesures.psnr(base, hr),
         "ratio_detail": mesures.ratio_detail(s, hr), "cellules": mesures.cellules(s), "cellules_vrai": mesures.cellules(hr)}
    m.train()
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matieres", nargs="*", default=[], help="dossiers de photos de vraies matieres (CC0, haute definition)")
    ap.add_argument("--videos", nargs="*", default=[], help="dossiers d'images extraites des videos de conduite reelles")
    ap.add_argument("--sortie", default="modeles")
    ap.add_argument("--depart", default="", help="modele a continuer (champion actuel)")
    ap.add_argument("--iterations", type=int, default=60000)
    ap.add_argument("--lot", type=int, default=12)
    ap.add_argument("--taille", type=int, default=192)
    ap.add_argument("--juge_apres", type=int, default=8000, help="iterations en pixel seul avant d'activer le juge (realisme)")
    ap.add_argument("--canaux", type=int, default=64)
    ap.add_argument("--blocs", type=int, default=16)
    a = ap.parse_args()
    appareil = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(a.sortie, exist_ok=True)
    sources = [Source(d, 2.0) for d in a.matieres] + [Source(d, 1.0, video=True) for d in a.videos]
    tir = Tirage(sources, t=a.taille)
    test = jeu_de_test(sources, os.path.join(a.sortie, "jeu_de_test.pt"))
    config = {"canaux": a.canaux, "blocs": a.blocs}
    g = TSCTex(**config).to(appareil)
    debut = 0
    if a.depart and os.path.exists(a.depart):
        e = torch.load(a.depart, map_location=appareil, weights_only=True)
        config = e.get("config", config); g = TSCTex(**config).to(appareil); g.load_state_dict(e["poids"])
        debut = a.juge_apres   # un champion a deja fait sa phase pixel
    d = Juge().to(appareil)
    og = torch.optim.Adam(g.parameters(), 2e-4, betas=(0.9, 0.99))
    od = torch.optim.Adam(d.parameters(), 2e-4, betas=(0.9, 0.99))
    ema = copy.deepcopy(g).eval()
    mixte = appareil == "cuda"
    echelle = torch.amp.GradScaler("cuda", enabled=mixte)
    echelle_d = torch.amp.GradScaler("cuda", enabled=mixte)
    journal = open(os.path.join(a.sortie, "journal_entrainement.txt"), "a", encoding="utf-8")
    t0 = time.time()
    for it in range(1, a.iterations + 1):
        hr = tir.lot(a.lot).to(appareil)
        with torch.no_grad():
            lr = degrader(hr)
        juge = it + debut > a.juge_apres
        with torch.autocast(appareil, enabled=mixte):
            sr = g(lr)
            p = F.l1_loss(sr, hr) + 0.05 * perte_frequences(sr.float(), hr)
            if juge:
                p = p + 0.005 * F.softplus(-d(sr)).mean()
        og.zero_grad(set_to_none=True); echelle.scale(p).backward(); echelle.step(og); echelle.update()
        if juge:
            with torch.autocast(appareil, enabled=mixte):
                pd = F.softplus(-d(hr)).mean() + F.softplus(d(sr.detach())).mean()
            od.zero_grad(set_to_none=True); echelle_d.scale(pd).backward(); echelle_d.step(od); echelle_d.update()
        with torch.no_grad():
            for pe, pg in zip(ema.parameters(), g.parameters()):
                pe.mul_(0.999).add_(pg, alpha=0.001)
        if it % 500 == 0 or it == a.iterations:
            r = evaluer(ema, test, appareil)
            l = f"{time.strftime('%H:%M:%S')} it {it} perte {p.item():.4f} psnr {r['psnr']:.2f} (bicubique {r['psnr_bicubique']:.2f}) detail {r['ratio_detail']:.2f} cellules {r['cellules']:.1f} (vrai {r['cellules_vrai']:.1f}) {time.time() - t0:.0f} s"
            print(l, flush=True); journal.write(l + "\n"); journal.flush()
            torch.save({"poids": ema.state_dict(), "config": config, "mesures": r, "iterations": it + debut}, os.path.join(a.sortie, "dernier.pt"))
    json.dump(evaluer(ema, test, appareil), open(os.path.join(a.sortie, "dernier_mesures.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
