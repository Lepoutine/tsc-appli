# TSC Neural - enchaineur de nuit : attend la fin d'un entrainement en cours, puis lance les suivants l'un apres l'autre.
# Un seul geste de Mendy (une ligne PowerShell) ; chaque run part du meilleur champion disponible ; journal dans nuit.txt.
# Usage : python -u nuit.py <dossier tsc_graphics> <run_en_cours>   (ex. . run6)
import os, subprocess, sys, time

base = os.path.abspath(sys.argv[1]); attendre = sys.argv[2] if len(sys.argv) > 2 else ""
py = sys.executable
runs_dir = os.path.join(base, "neural_runs")
journal = open(os.path.join(runs_dir, "nuit.txt"), "a", encoding="utf-8")


def note(t):
    l = time.strftime("%H:%M:%S ") + t
    print(l); journal.write(l + "\n"); journal.flush()


def fini(run):
    c = os.path.join(runs_dir, run + "_console.txt")
    if not os.path.exists(c):
        return False
    s = open(c, encoding="utf-8", errors="ignore").read()
    # fin normale, plantage Python, ou console muette depuis 20 min (processus tue, ex. memoire)
    return "fini." in s or "Traceback" in s or time.time() - os.path.getmtime(c) > 1200


def champion(*runs):
    for r in runs:
        p = os.path.join(runs_dir, r, "champion.pt")
        if os.path.exists(p):
            return p
    return None


COMMUN = ["--jeu", r"neural_donnees\jeu_run6\entrainement", "--reel", r"neural_donnees\reel_panoramax_entrainement",
          "--hlsl", r"a_poser_0.18\tsc-graphics_0.18_sans_poids.hlsl", "--iterations", "30000", "--variations", "1.0",
          "--detail", "6", "--detail_min", "0.75", "--guide", "1", "--reel_ram", "800",
          "--juge_vision", r"poids_externes\dinov2_vit_small_patch14_lvd142m\model.safetensors"]
# run7 : reseau 2x plus large (48 neurones) ; run8 : meme largeur, le reseau peut deplacer davantage les tons (moins tenu aux gris)
PLAN = [("run7", ["--cache", "48"], ("run6", "run5w")),
        ("run8", ["--cache", "48", "--neutres", "4", "--identite", "0.3", "--graine", "2"], ("run7", "run6", "run5w"))]

if attendre:
    note(f"attente de la fin de {attendre}")
    while not fini(attendre):
        time.sleep(60)
    note(f"{attendre} termine")
for nom, opts, departs in PLAN:
    if os.path.exists(os.path.join(runs_dir, nom, "champion.pt")):
        note(f"{nom} deja fait, saute"); continue
    d = champion(*departs) or os.path.join(runs_dir, "run5w", "modele_004000.pt")
    cmd = [py, "-u", os.path.join(base, "neural_0.8.4", "entrainer.py")] + COMMUN + ["--sortie", os.path.join("neural_runs", nom), "--depart", d] + opts
    note(f"lance {nom} depuis {d}")
    with open(os.path.join(runs_dir, nom + "_console.txt"), "w", encoding="utf-8") as fo:
        r = subprocess.run(cmd, cwd=base, stdout=fo, stderr=subprocess.STDOUT)
    note(f"{nom} termine (code {r.returncode})")
note("nuit terminee")
