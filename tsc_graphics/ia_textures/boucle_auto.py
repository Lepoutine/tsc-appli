# TSC Textures IA - apprentissage permanent avec regles (regles.json).
# A chaque cycle : s'il y a assez de nouvelles images (trajets, videos), l'IA reprend son apprentissage depuis le champion,
# puis la nouvelle version est jugee sur le jeu de test FIXE. Elle ne remplace le champion que si elle est meilleure sur
# tous les criteres ; sinon on la garde a part et le champion reste. Chaque champion est sauvegarde (retour arriere possible).
#   python boucle_auto.py --matieres ... --videos ... --dossier modeles [--forcer]
import argparse, json, os, shutil, subprocess, sys, time
import torch
from modele import TSCTex
from donnees import lister
from entrainer import evaluer, jeu_de_test
from donnees import Source

ICI = os.path.dirname(os.path.abspath(__file__))


def score(r):
    return r["psnr"] + 3.0 * (1 - abs(r["ratio_detail"] - 1)) - 0.05 * max(0.0, r["cellules"] - r["cellules_vrai"])


def ecrire(dossier, texte):
    l = time.strftime("%Y-%m-%d %H:%M:%S ") + texte
    print(l, flush=True)
    open(os.path.join(dossier, "journal_boucle.txt"), "a", encoding="utf-8").write(l + "\n")


def juger(cand, champ, R):
    """Rend (accepte, raisons)."""
    raisons = []
    if champ is None:
        if cand["psnr"] < cand["psnr_bicubique"] + R["battre_bicubique_de"]:
            raisons.append(f"ne bat pas l'agrandissement simple (psnr {cand['psnr']:.2f} contre {cand['psnr_bicubique']:.2f})")
    else:
        if cand["psnr"] < champ["psnr"] - R["psnr_perte_max"]:
            raisons.append(f"psnr en baisse ({cand['psnr']:.2f} contre {champ['psnr']:.2f})")
        if cand["cellules"] > champ["cellules"] * R["cellules_hausse_max"]:
            raisons.append(f"plus de motifs inventes ({cand['cellules']:.1f} contre {champ['cellules']:.1f})")
        if score(cand) < score(champ) + R["gain_score_min"]:
            raisons.append(f"pas assez de progres (score {score(cand):.3f} contre {score(champ):.3f})")
    if not (R["ratio_detail_min"] <= cand["ratio_detail"] <= R["ratio_detail_max"]):
        raisons.append(f"grain hors limites ({cand['ratio_detail']:.2f})")
    return not raisons, raisons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matieres", nargs="*", default=[])
    ap.add_argument("--videos", nargs="*", default=[])
    ap.add_argument("--dossier", default="modeles")
    ap.add_argument("--forcer", action="store_true")
    a = ap.parse_args()
    R = json.load(open(os.path.join(ICI, "regles.json"), encoding="utf-8"))
    os.makedirs(os.path.join(a.dossier, "versions"), exist_ok=True)
    etat_f = os.path.join(a.dossier, "etat.json")
    etat = json.load(open(etat_f)) if os.path.exists(etat_f) else {"images": 0, "version": 0}
    n = sum(len(lister(d)) for d in a.matieres + a.videos)
    if not a.forcer and etat["version"] > 0 and n - etat["images"] < R["nouvelles_images_min"]:
        ecrire(a.dossier, f"rien a apprendre : {n - etat['images']} nouvelles images (minimum {R['nouvelles_images_min']})")
        return
    champ_f = os.path.join(a.dossier, "champion.pt")
    cand_dir = os.path.join(a.dossier, "candidat")
    cmd = [sys.executable, os.path.join(ICI, "entrainer.py"), "--sortie", cand_dir, "--iterations", str(R["iterations_par_cycle"] if os.path.exists(champ_f) else 60000)]
    if a.matieres: cmd += ["--matieres"] + a.matieres
    if a.videos: cmd += ["--videos"] + a.videos
    if os.path.exists(champ_f): cmd += ["--depart", champ_f]
    os.makedirs(cand_dir, exist_ok=True)
    # le jeu de test est celui du dossier principal, fixe pour toujours
    test_f = os.path.join(a.dossier, "jeu_de_test.pt")
    sources = [Source(d, 2.0) for d in a.matieres] + [Source(d, 1.0, video=True) for d in a.videos]
    test = jeu_de_test(sources, test_f)
    shutil.copyfile(test_f, os.path.join(cand_dir, "jeu_de_test.pt"))
    ecrire(a.dossier, f"cycle : {n} images, apprentissage depuis {'le champion' if os.path.exists(champ_f) else 'zero'}")
    if subprocess.call(cmd) != 0:
        ecrire(a.dossier, "apprentissage interrompu : champion inchange"); return
    appareil = "cuda" if torch.cuda.is_available() else "cpu"
    def mesurer(f):
        e = torch.load(f, map_location=appareil, weights_only=True)
        m = TSCTex(**e["config"]).to(appareil); m.load_state_dict(e["poids"])
        return evaluer(m, test, appareil)
    cand = mesurer(os.path.join(cand_dir, "dernier.pt"))
    champ = mesurer(champ_f) if os.path.exists(champ_f) else None
    ok, raisons = juger(cand, champ, R)
    v = etat["version"] + 1
    if ok:
        if os.path.exists(champ_f):
            shutil.copyfile(champ_f, os.path.join(a.dossier, "versions", f"champion_v{etat['version']:03d}.pt"))
        shutil.copyfile(os.path.join(cand_dir, "dernier.pt"), champ_f)
        etat = {"images": n, "version": v, "mesures": cand, "date": time.strftime("%Y-%m-%d %H:%M")}
        json.dump(etat, open(etat_f, "w"), indent=1)
        ecrire(a.dossier, f"NOUVEAU CHAMPION v{v:03d} : psnr {cand['psnr']:.2f}, grain {cand['ratio_detail']:.2f}, motifs {cand['cellules']:.1f}, score {score(cand):.3f}")
        vs = sorted(os.listdir(os.path.join(a.dossier, "versions")))
        for f in vs[:-R["versions_gardees"]]:
            os.remove(os.path.join(a.dossier, "versions", f))
    else:
        shutil.copyfile(os.path.join(cand_dir, "dernier.pt"), os.path.join(a.dossier, "versions", f"refuse_{time.strftime('%Y%m%d_%H%M')}.pt"))
        ecrire(a.dossier, "candidat REFUSE, champion garde : " + " ; ".join(raisons))


if __name__ == "__main__":
    main()
