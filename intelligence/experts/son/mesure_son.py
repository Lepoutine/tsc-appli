#!/usr/bin/env python3
"""TSC Sound Engineering : mesure d'un son moteur et comparaison avec une reference.

Python 3 + numpy seulement (pas de scipy : absent du Shadow). Lecture seule : aucun son n'est modifie.

  python3 mesure_son.py mesurer son.wav [--cylindres 8] [--json rapport.json]
  python3 mesure_son.py comparer mon_son.wav reference.wav [--cylindres 8] [--debut 10.8 --fin 12.2]

Ce que l'outil mesure (et pourquoi) :
- niveaux (RMS, crete, ecretage) : un son ecrete gresille ;
- frequence d'allumage -> regime estime : pour un 4 temps, f = tr/min / 60 * cylindres / 2 ;
- energie par bandes : grave (<80 Hz) = « gras », corps 80-250, medium, rauque 1-4 kHz, aigu >4 kHz (souffle, gresillement) ;
- rondeur V8 (demi-ordre f/2) : un V8 a vilebrequin croise allume de facon inegale, ce qui donne le « borborygme » ;
- irregularite des coups d'allumage : un ralenti trop regulier sonne synthetique ;
- craquements (transitoires aigus par seconde) : petards de decel ;
- jonction de boucle : saut entre la fin et le debut, qui s'entend a chaque tour de boucle.
"""
import argparse
import json
import sys
import wave

import numpy as np

BANDES = [("grave", 20, 80), ("corps", 80, 250), ("medium", 250, 1000), ("rauque", 1000, 4000), ("aigu", 4000, 16000)]


def lire_wav(chemin, debut=None, fin=None):
    with wave.open(chemin, "rb") as w:
        n, sr, larg, nb = w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes()
        brut = w.readframes(nb)
    if larg == 2:
        x = np.frombuffer(brut, dtype="<i2").astype(np.float64) / 32768.0
    elif larg == 3:
        b = np.frombuffer(brut, dtype=np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float64) / float(1 << 23)
    elif larg == 4:
        x = np.frombuffer(brut, dtype="<i4").astype(np.float64) / 2147483648.0
    elif larg == 1:
        x = (np.frombuffer(brut, dtype=np.uint8).astype(np.float64) - 128) / 128.0
    else:
        raise ValueError("format WAV non gere (%d octets)" % larg)
    x = x.reshape(-1, n).mean(axis=1)
    if debut is not None or fin is not None:
        a = int((debut or 0) * sr)
        z = int(fin * sr) if fin is not None else len(x)
        x = x[a:z]
    return x, sr


def db(v):
    return float(20 * np.log10(max(v, 1e-9)))


def spectre(x, sr):
    taille = 1 << 15
    if len(x) < taille:
        taille = 1 << int(np.floor(np.log2(max(len(x), 256))))
    pas = taille // 2
    fen = np.hanning(taille)
    acc = np.zeros(taille // 2 + 1)
    k = 0
    for a in range(0, max(len(x) - taille, 0) + 1, pas):
        acc += np.abs(np.fft.rfft(x[a:a + taille] * fen)) ** 2
        k += 1
    return np.fft.rfftfreq(taille, 1.0 / sr), acc / max(k, 1)


def enveloppe(x, sr, fc=40.0):
    """Enveloppe d'amplitude lissee (moyenne glissante ~ 1/fc)."""
    n = max(int(sr / fc), 1)
    return np.convolve(np.abs(x), np.ones(n) / n, mode="same")


def allumage(x, sr, cylindres, details=False):
    """Frequence d'allumage par somme des harmoniques du spectre (15-250 Hz).

    Version du 04/11/2026 : l'ancienne autocorrelation d'enveloppe lisait l'ondulation de la forme d'onde au lieu
    de l'allumage sur les vrais enregistrements (164L : 3000 tr/min au lieu de 500). Trouve par le banc TSC Virtuoso.
    L'octave reste parfois ambigue (allumage inegal, signature des cylindres) : details=True rend les candidats et
    le drapeau « ambigu » ; le regime est alors a confirmer (nom du fichier, oreille de Mendy), jamais affirme.
    """
    pas = max(sr // 2000, 1)
    y = x[: len(x) // pas * pas].reshape(-1, pas).mean(1) if len(x) >= pas else x
    fs = sr / pas
    N = 1 << 14
    if len(y) < N // 4:
        return (None, None, {"ambigu": True, "candidats": []}) if details else (None, None)
    w = np.hanning(N)
    acc = None
    for i in range(0, max(1, len(y) - N + 1), N // 2):
        s = y[i:i + N]
        if len(s) < N:
            s = np.pad(s, (0, N - len(s)))
        P = np.abs(np.fft.rfft((s - s.mean()) * w)) ** 2
        acc = P if acc is None else acc + P
    f = np.fft.rfftfreq(N, 1 / fs)
    L = np.log(acc + acc.max() * 1e-6)
    cand = np.arange(15.0, 250.0, 0.05)
    sc = np.zeros(len(cand))
    poids = 0.0
    for k in range(1, 7):
        sc += np.interp(cand * k, f, L, right=L.min()) * 0.85 ** (k - 1)
        poids += 0.85 ** (k - 1)
    sc /= poids
    pics = [i for i in range(1, len(sc) - 1) if sc[i] >= sc[i - 1] and sc[i] >= sc[i + 1]]
    if not pics:
        return (None, None, {"ambigu": True, "candidats": []}) if details else (None, None)
    m = max(sc[i] for i in pics)
    bons = [i for i in pics if sc[i] >= m - 0.6]       # quasi ex aequo : on garde le plus aigu (evite les sous-multiples)
    i = max(bons, key=lambda q: cand[q])

    def autour(fc):  # meilleur score a +-3 % de fc
        j = int(np.argmin(np.abs(cand - fc)))
        r = max(1, int(0.03 * fc / 0.05))
        lo, hi = max(0, j - r), min(len(sc), j + r + 1)
        k = lo + int(np.argmax(sc[lo:hi]))
        return float(cand[k]), float(sc[k])
    fa = float(cand[i])
    # pas de doublement automatique : sur les vrais Scania (164L, R580, R620) il donnait des regimes faux.
    # L'octave du dessus ou du dessous est rendue comme candidat quand elle marque presque autant.
    tr_min = fa * 60.0 / (cylindres / 2.0)
    if not details:
        return fa, tr_min
    alt = {round(tr_min)}
    for fc in (fa / 2, fa * 2):
        if 15 <= fc < 250:
            f2, s2 = autour(fc)
            if s2 >= m - 2.0:
                alt.add(round(f2 * 60.0 / (cylindres / 2.0)))
    return fa, tr_min, {"ambigu": len(alt) > 1, "candidats": sorted(alt)}


def craquements(x, sr, k=4.0):
    if len(x) < sr // 10:
        return 0.0
    e = np.diff(x, prepend=x[:1]) ** 2
    w = max(int(0.005 * sr), 1)
    st = np.convolve(e, np.ones(w) / w, "same")[::w]
    L = 40
    pad = np.pad(st, (L // 2, L // 2), mode="edge")
    med = np.median(np.lib.stride_tricks.sliding_window_view(pad, L + 1), axis=1)[: len(st)]
    haut = st > k * med + 1e-12
    return float(np.count_nonzero(haut[1:] & ~haut[:-1])) / (len(x) / sr)


def mesurer(x, sr, cylindres=8):
    r = {"duree_s": round(len(x) / sr, 2), "frequence_echantillonnage": sr}
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    crete = float(np.max(np.abs(x))) if len(x) else 0.0
    r["niveau_rms_dbfs"] = round(db(rms), 1)
    r["crete_dbfs"] = round(db(crete), 1)
    r["facteur_crete_db"] = round(db(crete) - db(rms), 1)
    r["ecretage_pct"] = round(100.0 * float(np.mean(np.abs(x) >= 0.999)), 3)

    f, p = spectre(x, sr)
    total = float(p[(f >= 20) & (f < 16000)].sum()) or 1e-12
    r["bandes_pct"] = {nom: round(100.0 * float(p[(f >= a) & (f < b)].sum()) / total, 1) for nom, a, b in BANDES}
    r["centroide_hz"] = round(float((f * p).sum() / max(p.sum(), 1e-12)), 0)

    fa, tr, dt = allumage(x, sr, cylindres, details=True)
    r["allumage_hz"] = round(fa, 1) if fa else None
    r["regime_estime_tr_min"] = round(tr) if tr else None
    r["regime_ambigu"] = dt["ambigu"]
    r["regime_candidats"] = dt["candidats"]
    if fa:
        def autour(fc, larg=0.08):
            m = (f >= fc * (1 - larg)) & (f <= fc * (1 + larg))
            return float(p[m].sum()) if m.any() else 0.0
        e1, e_demi = autour(fa), autour(fa / 2)
        r["rondeur_demi_ordre_db"] = round(float(10 * np.log10(max(e_demi, 1e-12) / max(e1, 1e-12))), 1)
        # irregularite : variation des pics d'enveloppe d'un coup d'allumage a l'autre
        per = int(sr / fa)
        e = enveloppe(x, sr, fa * 4)
        pics = [float(e[a:a + per].max()) for a in range(0, len(e) - per, per)]
        if len(pics) > 4:
            pics = np.array(pics)
            r["irregularite_pct"] = round(100.0 * float(pics.std() / max(pics.mean(), 1e-12)), 1)

    # craquements : trames de 5 ms dont l'energie aigue (derivee) depasse 4 x la mediane locale (200 ms).
    # Relatif au voisinage : un moteur aigu en continu ne compte pas, une petarade si (verifie le 03/11 :
    # claquant_1-3 = 16-18/s, boucles de ralenti = 0-0,3/s).
    r["craquements_par_s"] = round(craquements(x, sr), 2)

    # jonction de boucle : saut d'echantillon et ecart de niveau entre la fin et le debut
    n50 = int(0.05 * sr)
    if len(x) > 4 * n50:
        saut = abs(float(x[-1] - x[0]))
        pente = float(np.median(np.abs(np.diff(x)))) + 1e-9
        r["jonction_saut_x_pente_mediane"] = round(saut / pente, 1)
        r["jonction_ecart_niveau_db"] = round(db(float(np.sqrt(np.mean(x[-n50:] ** 2)))) - db(float(np.sqrt(np.mean(x[:n50] ** 2)))), 1)
    return r


def diagnostic(mien, ref):
    """Ecarts mesures -> phrases claires. Seuils prudents : on ne dit que ce que les chiffres montrent."""
    d = []
    bm, br = mien["bandes_pct"], ref["bandes_pct"]
    if bm["grave"] + bm["corps"] < br["grave"] + br["corps"] - 8:
        d.append("Pas assez gras : %.0f %% d'energie sous 250 Hz contre %.0f %% dans la reference." % (bm["grave"] + bm["corps"], br["grave"] + br["corps"]))
    if bm["aigu"] > br["aigu"] + 5:
        d.append("Trop d'aigu (souffle ou gresillement) : %.0f %% au-dessus de 4 kHz contre %.0f %%." % (bm["aigu"], br["aigu"]))
    if bm["rauque"] < br["rauque"] - 6:
        d.append("Manque de rauque (1-4 kHz) : %.0f %% contre %.0f %%." % (bm["rauque"], br["rauque"]))
    if mien.get("rondeur_demi_ordre_db") is not None and ref.get("rondeur_demi_ordre_db") is not None:
        if mien["rondeur_demi_ordre_db"] < ref["rondeur_demi_ordre_db"] - 4:
            d.append("Pas assez de « borborygme » V8 (demi-ordre %.1f dB contre %.1f dB) : allumage trop regulier." % (mien["rondeur_demi_ordre_db"], ref["rondeur_demi_ordre_db"]))
    if mien.get("irregularite_pct") is not None and ref.get("irregularite_pct") is not None:
        if mien["irregularite_pct"] < 0.6 * ref["irregularite_pct"]:
            d.append("Ralenti trop regulier, il sonne synthetique (irregularite %.0f %% contre %.0f %%)." % (mien["irregularite_pct"], ref["irregularite_pct"]))
    if mien.get("craquements_par_s", 0) < 0.5 * ref.get("craquements_par_s", 0):
        d.append("Moins de craquements que la reference (%.1f/s contre %.1f/s)." % (mien.get("craquements_par_s", 0), ref.get("craquements_par_s", 0)))
    if mien["ecretage_pct"] > 0.01:
        d.append("Ecretage : %.3f %% des echantillons au maximum, cela gresille." % mien["ecretage_pct"])
    if mien["facteur_crete_db"] < ref["facteur_crete_db"] - 4:
        d.append("Son trop compresse, sans punch (facteur de crete %.1f dB contre %.1f dB)." % (mien["facteur_crete_db"], ref["facteur_crete_db"]))
    if mien.get("jonction_saut_x_pente_mediane", 0) > 20 or abs(mien.get("jonction_ecart_niveau_db", 0)) > 2:
        d.append("La jonction de boucle s'entend (saut %.0f x, ecart %.1f dB)." % (mien.get("jonction_saut_x_pente_mediane", 0), mien.get("jonction_ecart_niveau_db", 0)))
    # le regime estime n'est qu'indicatif sur de vrais sons (essai du 03/11 sur les sons de Mendy : erreurs d'octave
    # frequentes) ; on ne compare que le regime nominal (nom du fichier ou --regime)
    if mien.get("regime_nominal") and ref.get("regime_nominal"):
        if abs(mien["regime_nominal"] - ref["regime_nominal"]) > 0.15 * ref["regime_nominal"]:
            d.append("Regimes differents (%d contre %d tr/min) : comparer a regime egal." % (mien["regime_nominal"], ref["regime_nominal"]))
    if not d:
        d.append("Aucun ecart net sur les mesures : la difference est ailleurs (dynamique des coups de gaz, mixage en jeu). Ecouter la vraie banque dans TSCF_Lab.")
    return d


def regime_du_nom(nom):
    """'1500_op_idle.wav' ou 'rv8op 900ex.wav' -> 1500 / 900 (regime auquel le mod joue la couche)."""
    import re
    m = re.search(r"(?<!\d)(\d{3,4})(?!\d)", nom)
    return int(m.group(1)) if m and 300 <= int(m.group(1)) <= 3000 else None


def mesurer_dossier(dossier, csv_chemin, cylindres=8):
    import csv
    import os
    cols = ["fichier", "duree_s", "regime_nominal", "regime_estime_tr_min", "niveau_rms_dbfs", "crete_dbfs", "facteur_crete_db", "ecretage_pct",
            "grave", "corps", "medium", "rauque", "aigu", "rondeur_demi_ordre_db", "irregularite_pct", "craquements_par_s",
            "jonction_saut_x_pente_mediane", "jonction_ecart_niveau_db", "erreur"]
    n = 0
    with open(csv_chemin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        for racine, _, noms in os.walk(dossier):
            for nom in sorted(noms):
                if not nom.lower().endswith(".wav"):
                    continue
                chemin = os.path.join(racine, nom)
                lig = {"fichier": os.path.relpath(chemin, dossier)}
                try:
                    x, sr = lire_wav(chemin)
                    r = mesurer(x, sr, cylindres)
                    r["regime_nominal"] = regime_du_nom(nom)
                    lig.update({k: v for k, v in r.items() if k != "bandes_pct"})
                    lig.update(r["bandes_pct"])
                except Exception as e:  # un fichier illisible ne bloque pas les autres
                    lig["erreur"] = str(e) or type(e).__name__
                w.writerow([lig.get(c, "") for c in cols])
                n += 1
    print("%d sons mesures -> %s" % (n, csv_chemin))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="TSC Sound Engineering : mesure de sons moteur")
    sp = ap.add_subparsers(dest="cmd", required=True)
    m = sp.add_parser("mesurer")
    m.add_argument("wav")
    c = sp.add_parser("comparer")
    c.add_argument("wav")
    c.add_argument("reference")
    for s in (m, c):
        s.add_argument("--cylindres", type=int, default=8)
        s.add_argument("--debut", type=float)
        s.add_argument("--fin", type=float)
        s.add_argument("--json")
    dd = sp.add_parser("dossier", help="mesure tous les .wav d'un dossier (lecture seule) -> CSV")
    dd.add_argument("dossier")
    dd.add_argument("--cylindres", type=int, default=8)
    dd.add_argument("--csv", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "dossier":
        return mesurer_dossier(a.dossier, a.csv, a.cylindres)
    x, sr = lire_wav(a.wav, a.debut, a.fin)
    r = {"son": a.wav, "mesures": mesurer(x, sr, a.cylindres)}
    if a.cmd == "comparer":
        y, sr2 = lire_wav(a.reference, a.debut, a.fin)
        r["reference"] = {"son": a.reference, "mesures": mesurer(y, sr2, a.cylindres)}
        r["diagnostic"] = diagnostic(r["mesures"], r["reference"]["mesures"])
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
