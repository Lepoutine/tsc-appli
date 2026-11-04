#!/usr/bin/env python3
"""Expert Performance : lire une capture PresentMon et comparer AVANT / APRÈS sans se raconter d'histoire.

Sert au manque « comparaison avant/après automatique » (agents.json). Mendy capture deux CSV PresentMon sur le même
trajet (fiche presentmon) ; ce script dit si la version APRÈS est mieux, pire, ou si la différence n'est pas prouvée.

- Colonnes lues : PresentMon 1.x « MsBetweenPresents », PresentMon 2.x « FrameTime » (ou « msBetweenPresents »).
  Filtre facultatif sur la colonne « Application » (ex. eurotrucks2.exe).
- Chiffres : images/s moyennes (1000 / frametime moyen), « 1 % bas » = images/s au 99e centile des frametimes,
  p99 en ms, saccades = images plus de 2 fois plus longues que la médiane.
- Verdict : intervalle de confiance à 95 % par rééchantillonnage en blocs (les images voisines se ressemblent :
  tirer image par image donnerait une fausse certitude). Une différence n'est retenue que si l'intervalle exclut 0
  ET dépasse le seuil d'écart utile : 3 % sur les images/s moyennes, 5 % sur le 1 % bas (le 99e centile est bruité :
  réglé au banc le 04/11 pour zéro fausse alarme sur 300 paires de captures identiques). Sinon : « pas de différence
  prouvée ». Une seule capture par version reste fragile : en faire deux ou trois de chaque côté si possible.

  python3 frametime.py avant.csv apres.csv [--appli eurotrucks2.exe] [--seuil 3] [--seuil-bas 5]
"""
import argparse
import csv
import json
import sys

import numpy as np

COLONNES = ("MsBetweenPresents", "FrameTime", "msBetweenPresents")


def lire_csv(chemin, appli=None):
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        col = next((c for c in COLONNES if c in (r.fieldnames or [])), None)
        if not col:
            raise ValueError("%s : aucune colonne de frametime (%s)" % (chemin, ", ".join(COLONNES)))
        v = []
        for ligne in r:
            if appli and ligne.get("Application", appli).lower() != appli.lower():
                continue
            try:
                x = float(ligne[col])
            except (TypeError, ValueError):
                continue
            if x > 0:
                v.append(x)
    if len(v) < 100:
        raise ValueError("%s : %d images seulement, il en faut au moins 100" % (chemin, len(v)))
    return np.array(v)


def stats(ft):
    ft = np.asarray(ft, float)
    med = float(np.median(ft))
    p99 = float(np.percentile(ft, 99))
    return {"images": int(len(ft)), "fps_moyen": 1000.0 / float(np.mean(ft)), "fps_1pc_bas": 1000.0 / p99,
            "ft_median_ms": med, "ft_p99_ms": p99, "saccades": int(np.sum(ft > 2 * med))}


def _blocs(rng, ft, taille):
    n = len(ft)
    k = max(1, n // taille)
    deb = rng.integers(0, n - taille + 1, size=k)
    return np.concatenate([ft[d:d + taille] for d in deb])


def comparer(avant, apres, seuil_pct=3.0, seuil_bas_pct=5.0, tirages=400, graine=0):
    """Rend {avant, apres, ecarts, verdict}. Écart en % : positif = APRÈS meilleur."""
    rng = np.random.default_rng(graine)
    A, B = stats(avant), stats(apres)
    taille = max(10, min(len(avant), len(apres)) // 20)
    d_moy, d_bas = [], []
    for _ in range(tirages):
        a, b = _blocs(rng, avant, taille), _blocs(rng, apres, taille)
        d_moy.append(100.0 * (np.mean(a) / np.mean(b) - 1))
        d_bas.append(100.0 * (np.percentile(a, 99) / np.percentile(b, 99) - 1))
    ec = {}
    for nom, d, val, seuil in (("fps_moyen", d_moy, 100.0 * (B["fps_moyen"] / A["fps_moyen"] - 1), seuil_pct),
                               ("fps_1pc_bas", d_bas, 100.0 * (B["fps_1pc_bas"] / A["fps_1pc_bas"] - 1), seuil_bas_pct)):
        lo, hi = np.percentile(d, [2.5, 97.5])
        if lo > 0 and val >= seuil:
            s = "mieux"
        elif hi < 0 and val <= -seuil:
            s = "pire"
        else:
            s = "pas de différence prouvée"
        ec[nom] = {"ecart_pct": round(val, 2), "ic95": [round(float(lo), 2), round(float(hi), 2)], "sens": s}
    sens = {e["sens"] for e in ec.values()}
    if "pire" in sens:
        verdict = "pire"  # une baisse prouvée du 1 % bas suffit à refuser, même si la moyenne monte
    elif "mieux" in sens:
        verdict = "mieux"
    else:
        verdict = "pas de différence prouvée"
    return {"avant": A, "apres": B, "ecarts": ec, "verdict": verdict, "seuils_pct": {"fps_moyen": seuil_pct, "fps_1pc_bas": seuil_bas_pct}}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("avant")
    p.add_argument("apres")
    p.add_argument("--appli")
    p.add_argument("--seuil", type=float, default=3.0)
    p.add_argument("--seuil-bas", type=float, default=5.0)
    a = p.parse_args(argv)
    r = comparer(lire_csv(a.avant, a.appli), lire_csv(a.apres, a.appli), a.seuil, a.seuil_bas)
    for k in ("avant", "apres"):
        s = r[k]
        print("%-5s %6d images  %.1f img/s  1 %% bas %.1f  p99 %.1f ms  saccades %d" % (k.upper(), s["images"], s["fps_moyen"], s["fps_1pc_bas"], s["ft_p99_ms"], s["saccades"]))
    for k, e in r["ecarts"].items():
        print("%-12s %+.1f %%  (IC95 %+.1f / %+.1f)  %s" % (k, e["ecart_pct"], e["ic95"][0], e["ic95"][1], e["sens"]))
    print("VERDICT :", r["verdict"])
    print(json.dumps(r, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
