#!/usr/bin/env python3
"""TSC-IA Son : ce qui apprend, contre le juge PANNs gelé (même méthode que la TSC-IA Graphics).

- Le juge (juge_panns.py, Cnn14 gelé) transforme chaque fenêtre de 4 s en empreinte. Il n'apprend jamais.
- La TSC-IA Son apprend deux têtes légères sur ces empreintes :
  * « réalisme » : centre des vrais enregistrements contre centre des sons que Mendy a refusés (synthèses v3 à v7,
    puis ses « Je jette » dans Forge) ; score > 0 = plus proche du réel ;
  * « état moteur » : ralenti, montée, haut régime, charge, coups de gaz, claquements (voisins les plus proches sur
    les vrais passages étiquetés).
- Règles communes (intelligence/apprentissage/boucle.py) : 1 son sur 10 est juge pour toujours, une version n'est
  adoptée que si elle fait au moins aussi bien sur ce juge, sinon l'ancienne reste ; versions et journal gardés.
- Application : chercher, dans un VRAI passage, la boucle que le juge trouve la plus fidèle à l'original (aucune
  synthèse, aucune retouche du son : on choisit seulement où couper), avec un raccord sans saut.

  python3 ia_son.py apprendre      # (ré)apprend sur les sons connus, adopte ou refuse
  python3 ia_son.py boucles        # meilleure boucle de chaque vrai passage de ralenti/régime stable
"""
import json
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(ICI)), "apprentissage"))
import juge_panns as J  # noqa: E402
from boucle import Boucle, est_juge  # noqa: E402

PF = "/mnt/project-files/tsc_intelligence/expert_son"
POIDS = os.environ.get("TSC_PANNS", os.path.join(PF, "modeles", "Cnn14_mAP=0.431.pth"))
DOSSIER_IA = os.path.join(PF, "ia_son")
COMPOSES = ("apercu_v3", "apercu_v5", "apercu_v6", "apercu_v7")  # synthèses refusées par Mendy le 04/11 00:15
ETATS = {"ralenti": ("ralenti", "retour_au_ralenti"), "coups_de_gaz": ("coups_de_gaz",), "montee": ("montee",),
         "haut_regime": ("regime_haut",), "charge": ("charge", "roulage"), "claquements": ("claquements",)}


def etat_de(nom):
    n = nom.lower()
    for e, mots in ETATS.items():
        if any(m in n for m in mots):
            return e
    return None


def unit(E):
    E = np.asarray(E, float)
    return E / (np.linalg.norm(E, axis=-1, keepdims=True) + 1e-9)


# ---------------------------------------------------------------- les deux têtes
def entrainer(exemples):
    """exemples : [{cle, E (fenêtres x 2048), reel 0/1, etat}] -> modèle JSON."""
    R = [unit(e["E"]).mean(0) for e in exemples if e["reel"] == 1]
    C = [unit(e["E"]).mean(0) for e in exemples if e["reel"] == 0]
    m = {"centre_reel": unit(np.mean(R, 0)).tolist() if R else None, "centre_refuse": unit(np.mean(C, 0)).tolist() if C else None,
         "etats": [{"etat": e["etat"], "v": unit(unit(e["E"]).mean(0)).tolist()} for e in exemples if e["reel"] == 1 and e["etat"]]}
    return m


def realisme(m, E):
    if not m["centre_reel"] or not m["centre_refuse"]:
        return None
    u = unit(E)
    return float((u @ np.array(m["centre_reel"]) - u @ np.array(m["centre_refuse"])).mean())


def etat_propose(m, E, k=3):
    if not m["etats"]:
        return None
    v = unit(unit(E).mean(0))
    d = sorted(((float(v @ np.array(x["v"])), x["etat"]) for x in m["etats"]), reverse=True)[:k]
    votes = {}
    for s, e in d:
        votes[e] = votes.get(e, 0) + s
    return max(votes, key=votes.get)


def juger(m, juges):
    out = {}
    r = [(realisme(m, e["E"]), e["reel"]) for e in juges]
    r = [(s, y) for s, y in r if s is not None]
    if r:
        out["realisme"] = sum((s > 0) == bool(y) for s, y in r) / len(r)
    et = [(etat_propose(m, e["E"]), e["etat"]) for e in juges if e["reel"] == 1 and e["etat"]]
    if et:
        out["etat"] = sum(p == y for p, y in et) / len(et)
    return out


# ---------------------------------------------------------------- données
def sons_connus():
    """Tous les sons dont on connaît la vérité : vrais passages (segments_reels, boucles v8 tirées du réel,
    bibliothèque libre) et synthèses refusées par Mendy."""
    L = []
    for d in sorted(os.listdir(PF)):
        p = os.path.join(PF, d)
        if not os.path.isdir(p) or d in ("apercu_v9",):  # v9 = scénarios montés, mélange : exclus
            continue
        for f in sorted(os.listdir(p)):
            if f.lower().endswith(".wav"):
                reel = 0 if d in COMPOSES else (1 if d in ("segments_reels", "apercu_v8") or d.startswith("bibliotheque") else None)
                if reel is not None:
                    L.append({"cle": "%s/%s" % (d, f), "chemin": os.path.join(p, f), "reel": reel, "etat": etat_de(f) if reel else None})
    return L


def empreintes(sons, modele, cache=os.path.join(DOSSIER_IA, "empreintes.npz")):
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    old = dict(np.load(cache)) if os.path.isfile(cache) else {}
    for s in sons:
        if s["cle"] not in old:
            x, sr = J.lire_wav(s["chemin"])
            old[s["cle"]] = J.empreinte(modele, x, sr)[0]
        s["E"] = old[s["cle"]]
    np.savez(cache, **old)
    return sons


# ---------------------------------------------------------------- boucles guidées par le juge
def saut_raccord(x, sr, a, b, w=0.2):
    n = int(w * sr)
    db = lambda s: 10 * np.log10(np.mean(s.astype(float) ** 2) + 1e-12)
    return abs(db(x[b - n:b]) - db(x[a:a + n]))


def meilleure_boucle(x, sr, modele, cycle_s, duree_min=3.0, essais=12, rng=None):
    """Cherche [a, b) dans le vrai passage x : longueur = nombre entier de cycles moteur, raccord <= 1,5 dB, et
    la boucle répétée doit rester la plus proche possible de l'original pour le juge."""
    rng = rng or np.random.default_rng(0)
    E0 = J.empreinte(modele, x, sr)[0]
    ncyc = max(1, int(np.ceil(duree_min / cycle_s)))
    L = int(round(ncyc * cycle_s * sr))
    if L >= len(x) - sr // 10:
        return None
    cands = []
    for a in rng.integers(0, len(x) - L, size=essais * 4):
        s = saut_raccord(x, sr, int(a), int(a) + L)
        cands.append((s, int(a)))
    cands = sorted(cands)[:essais]
    best = None
    for s, a in cands:
        seg = x[a:a + L]
        rep = np.tile(seg, int(np.ceil(len(x) / L)) + 1)[:max(len(x), 4 * sr)]
        d = J.distance(J.empreinte(modele, rep, sr)[0], E0)
        if best is None or (s <= 1.5 and (best["saut_db"] > 1.5 or d < best["distance_juge"])) or (best["saut_db"] > 1.5 and s < best["saut_db"]):
            best = {"debut_s": a / sr, "fin_s": (a + L) / sr, "cycles": ncyc, "saut_db": round(float(s), 2), "distance_juge": round(d, 4)}
    return best


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "apprendre"
    mod = J.charger(POIDS)
    sons = empreintes(sons_connus(), mod)
    b = Boucle(DOSSIER_IA, entrainer, juger)
    if cmd == "apprendre":
        r = b.apprend(sons)
        print(r["raison"])
        juges = [s["cle"] for s in sons if est_juge(s["cle"])]
        print("juge fixe (%d sons, jamais appris) : %s" % (len(juges), ", ".join(juges)))
    elif cmd == "boucles":
        sys.path.insert(0, ICI)
        import boucle_reelle
        out = []
        for s in sons:
            if s["reel"] and s["etat"] in ("ralenti", "haut_regime", "charge") and s["cle"].startswith("segments_reels"):
                x, sr = J.lire_wav(s["chemin"])
                c = boucle_reelle.cycle_moteur(x, sr)
                cyc = c[0] if isinstance(c, (tuple, list)) else c
                r = meilleure_boucle(x, sr, mod, float(cyc))
                out.append({"son": s["cle"], "cycle_s": round(float(cyc), 4), **(r or {"erreur": "passage trop court"})})
                print(json.dumps(out[-1], ensure_ascii=False))
        json.dump(out, open(os.path.join(DOSSIER_IA, "boucles_juge.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv)
