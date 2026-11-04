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
def logistique(exemples, lam=1e-2, iterations=400, pas=2.0):
    """Tête linéaire réel / refusé sur les fenêtres de 4 s : chaque fichier compte pareil, chaque classe pèse 50 %
    (61 vrais contre 12 synthèses : sans ce poids, la tête dirait « réel » à tout). Descente de gradient simple."""
    X = np.vstack([unit(e["E"]) for e in exemples])
    y = np.concatenate([[e["reel"]] * len(e["E"]) for e in exemples]).astype(float)
    w = np.concatenate([[1.0 / len(e["E"])] * len(e["E"]) for e in exemples])
    for c in (0, 1):
        w[y == c] /= w[y == c].sum()
    mu = X.mean(0)
    X = X - mu
    v, b = np.zeros(X.shape[1]), 0.0
    for _ in range(iterations):
        r = w * (1 / (1 + np.exp(-(X @ v + b))) - y)
        v -= pas * (X.T @ r + lam * v)
        b -= pas * r.sum()
    return {"mu": mu.tolist(), "v": v.tolist(), "b": float(b)}


def entrainer(exemples):
    """exemples : [{cle, E (fenêtres x 2048), reel 0/1, etat}] -> modèle JSON.
    Réalisme : tête logistique (meilleure que les centres de classes en validation un-contre-tous du 04/11 :
    fenêtres de synthèse reconnues 53/59 contre 46/59, vrais fichiers 59/61 contre 57/61)."""
    R = [unit(e["E"]).mean(0) for e in exemples if e["reel"] == 1]
    C = [unit(e["E"]).mean(0) for e in exemples if e["reel"] == 0]
    m = {"centre_reel": unit(np.mean(R, 0)).tolist() if R else None, "centre_refuse": unit(np.mean(C, 0)).tolist() if C else None,
         "logistique": logistique(exemples) if R and C else None,
         "etats": [{"etat": e["etat"], "v": unit(unit(e["E"]).mean(0)).tolist()} for e in exemples if e["reel"] == 1 and e["etat"]]}
    return m


def realisme(m, E):
    """Score moyen sur les fenêtres : > 0 = plus proche des vrais enregistrements que des sons refusés."""
    u = unit(E)
    if m.get("logistique"):
        L = m["logistique"]
        return float(((u - np.array(L["mu"])) @ np.array(L["v"]) + L["b"]).mean())
    if not m["centre_reel"] or not m["centre_refuse"]:
        return None
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
            if f.lower().endswith((".wav", ".flac")):
                reel = 0 if d in COMPOSES else (1 if d in ("segments_reels", "apercu_v8", "videos_completes") else None)
                if reel is not None:
                    L.append({"cle": "%s/%s" % (d, f), "chemin": os.path.join(p, f), "reel": reel, "etat": etat_de(f) if reel else None})
    # bibliothèque libre (Wikimedia Commons, licences vérifiées dans INDEX.csv) : vrais moteurs seulement
    idx = os.path.join(PF, "bibliotheque_commons", "INDEX.csv")
    if os.path.isfile(idx):
        import csv
        for r in csv.DictReader(open(idx, encoding="utf-8-sig"), delimiter=";"):
            mots = {m.strip() for m in r["mots_cles"].split(",")}
            moteur = mots & {"ralenti", "accélération", "passage", "démarrage", "diesel", "bus", "engin/tracteur"}
            if not moteur or ("klaxon" in mots and "ralenti" not in mots) or mots <= {"pneumatique", "camion"}:
                continue
            L.append({"cle": "bibliotheque_commons/" + r["fichier"], "chemin": os.path.join(PF, "bibliotheque_commons", r["fichier"]),
                      "reel": 1, "etat": None, "licence": r["licence"]})
    return L


def empreintes(sons, modele, cache=os.path.join(DOSSIER_IA, "empreintes.npz")):
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    old = dict(np.load(cache)) if os.path.isfile(cache) else {}
    for s in sons:
        if s["cle"] not in old:
            x, sr = J.lire_audio(s["chemin"])
            old[s["cle"]] = J.empreinte(modele, x, sr, max_fenetres=12)[0]
            np.savez(cache, **old)  # sauvegarde au fil de l'eau : un plantage ne perd rien
        s["E"] = old[s["cle"]]
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


if __name__ == "__main__" and (len(sys.argv) < 2 or sys.argv[1] != "catalogue"):
    main(sys.argv)


# ---------------------------------------------------------------- catalogue de boucles tirées des vidéos complètes
def passages_stables(x, sr, fen=4.0, pas=1.0, ecart_regime=0.08, ecart_db=3.0, mini=3):
    """Fenêtres consécutives où le régime (allumage) et le niveau restent stables : ce sont les passages où une
    boucle a un sens (ralenti, régime tenu, charge tenue). Rend [(début_s, fin_s, régime moyen, niveau dB)]."""
    import mesure_son as ms
    L, P = int(fen * sr), int(pas * sr)
    M = []
    for d in range(0, len(x) - L + 1, P):
        w = x[d:d + L]
        _, rpm = ms.allumage(w, sr, 8)
        M.append((d / sr, rpm, 10 * np.log10(np.mean(w.astype(float) ** 2) + 1e-12)))
    out, i = [], 0
    while i < len(M):
        j = i
        while j + 1 < len(M) and M[j + 1][1] and M[i][1]:
            r = [m[1] for m in M[i:j + 2]]
            n = [m[2] for m in M[i:j + 2]]
            if (max(r) - min(r)) / np.mean(r) > ecart_regime or max(n) - min(n) > ecart_db:
                break
            j += 1
        if j - i + 1 >= mini:
            out.append((M[i][0], M[j][0] + fen, float(np.mean([m[1] for m in M[i:j + 1]])), float(np.mean([m[2] for m in M[i:j + 1]]))))
            i = j + 1
        else:
            i += 1
    return out


def catalogue(mod, sortie=os.path.join(PF, "catalogue_boucles")):
    import csv
    import wave
    import boucle_reelle
    sons = empreintes(sons_connus(), mod)
    b = Boucle(DOSSIER_IA, entrainer, juger)
    m = b.modele()
    os.makedirs(sortie, exist_ok=True)
    lignes = []
    for f in sorted(os.listdir(os.path.join(PF, "videos_completes"))):
        x, sr = J.lire_audio(os.path.join(PF, "videos_completes", f))
        x = x - x.mean()
        for k, (a, z, rpm, niv) in enumerate(passages_stables(x, sr)):
            seg = x[int(a * sr):int(z * sr)]
            cyc = boucle_reelle.cycle_moteur(seg, sr)
            r = meilleure_boucle(seg, sr, mod, cyc, rng=np.random.default_rng(k))
            if not r or r["saut_db"] > 1.5:
                continue
            bo = seg[int(r["debut_s"] * sr):int(r["fin_s"] * sr)]  # coupe seule, aucun traitement
            E = J.empreinte(mod, bo, sr)[0]
            nom = "%s_%03ds_%04dtrmin.wav" % (f.split("_")[1], int(a + r["debut_s"]), int(round(rpm)))
            with wave.open(os.path.join(sortie, nom), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes((np.clip(bo, -1, 1) * 32767).astype("<i2").tobytes())
            lignes.append({"fichier": nom, "video": f, "debut_s": round(a + r["debut_s"], 2), "fin_s": round(a + r["fin_s"], 2),
                           "regime_mesure_trmin": int(round(rpm)), "niveau_db": round(niv, 1), "saut_raccord_db": r["saut_db"],
                           "distance_juge": r["distance_juge"], "realisme": round(realisme(m, E), 3), "etat_propose": etat_propose(m, E)})
            print(json.dumps(lignes[-1], ensure_ascii=False))
    with open(os.path.join(sortie, "catalogue.csv"), "w", encoding="utf-8-sig", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=list(lignes[0]), delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    return lignes


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "catalogue":
    catalogue(J.charger(POIDS))
