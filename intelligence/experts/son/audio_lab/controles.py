"""Section 9 du cahier des charges : tests automatiques, rapport CSV/JSON horodate.

Mesures (NumPy seul, pas besoin de SciPy) :
- crete vraie (dBTP) : sur-echantillonnage x4 par interpolation spectrale ;
- sonie integree (LUFS) selon ITU-R BS.1770-4 : ponderation K (etage « tete » + passe-haut RLB),
  blocs de 400 ms avec recouvrement de 75 %, porte absolue -70 LUFS puis porte relative -10 LU.
  Le filtre est applique en frequence (module seul) : ecart attendu < 0,1 LU sur un son de moteur ;
- ecretage, decalage continu (DC), silences anormaux, raccord de boucle (saut fin -> debut).
Chaque mesure donne une ligne : fichier, segment, horodatage, mesure, valeur, seuil, decision.
Aucune mesure ne remplace l'ecoute (cahier des charges, section 2).

Usage : python3 -m audio_lab.controles <wav>... --sortie rapport.json [--boucle]
"""
import argparse
import csv
import datetime
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mesure_son as ms  # noqa: E402

SEUILS = {
    "crete_vraie_dbtp": -1.0,      # au-dessus : risque de saturation apres encodage Vorbis
    "ecretage_pct": 0.01,
    "dc_pct": 0.5,                 # moyenne / crete
    "silence_s": 0.25,             # trou sous -60 dBFS plus long que ca
    "raccord_x_pente": 8.0,        # saut fin->debut / pente mediane
    "raccord_niveau_db": 1.5,      # ecart de niveau entre les 200 ms de fin et de debut
}


def _biquad_reponse(b, a, w):
    z = np.exp(-1j * w)
    return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)


def ponderation_k(sr):
    """Coefficients des deux etages de la ponderation K (formules de Brecht De Man, valables a toute frequence ;
    a 48 kHz elles redonnent les coefficients publies dans BS.1770)."""
    G, f0, Q = 3.99984385397, 1681.974450955533, 0.7071752369554196
    K = math.tan(math.pi * f0 / sr)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1.0, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = math.tan(math.pi * f0 / sr)
    d = 1 + K / Q + K * K
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, 2 * (K * K - 1) / d, (1 - K / Q + K * K) / d]
    return (b1, a1), (b2, a2)


def filtre_k(x, sr):
    (b1, a1), (b2, a2) = ponderation_k(sr)
    n = len(x)
    X = np.fft.rfft(x)
    w = 2 * np.pi * np.fft.rfftfreq(n, 1.0 / sr) / sr
    H = np.abs(_biquad_reponse(b1, a1, w) * _biquad_reponse(b2, a2, w))
    return np.fft.irfft(X * H, n)


def lufs(x, sr):
    """Sonie integree d'un signal mono (dB LUFS). -inf si tout est sous la porte absolue."""
    y = filtre_k(x, sr)
    bloc, pas = int(0.4 * sr), int(0.1 * sr)
    if len(y) < bloc:
        bloc = pas = len(y)
    z = np.array([np.mean(y[i:i + bloc] ** 2) for i in range(0, len(y) - bloc + 1, pas)])
    l = -0.691 + 10 * np.log10(z + 1e-20)
    z = z[l > -70]
    if not len(z):
        return float("-inf")
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    z2 = z[(-0.691 + 10 * np.log10(z)) > rel]
    return float(-0.691 + 10 * np.log10(z2.mean() if len(z2) else z.mean()))


def crete_vraie(x, facteur=4, morceau=1 << 16):
    """Crete apres sur-echantillonnage x4 (interpolation spectrale par morceaux recouvrants)."""
    m = 0.0
    bord = 64
    for i in range(0, len(x), morceau):
        s = x[max(0, i - bord):i + morceau + bord]
        X = np.fft.rfft(s)
        y = np.fft.irfft(X, len(s) * facteur) * facteur
        m = max(m, float(np.abs(y).max()))
    return 20 * math.log10(max(m, 1e-9))


def silences(x, sr, seuil_db=-60.0, mini=0.25):
    e = ms.enveloppe(x, sr, 50.0)
    bas = e < 10 ** (seuil_db / 20)
    trous, debut = [], None
    for i, v in enumerate(bas[::48]):
        t = i * 48 / sr
        if v and debut is None:
            debut = t
        elif not v and debut is not None:
            if t - debut >= mini:
                trous.append((round(debut, 2), round(t - debut, 2)))
            debut = None
    if debut is not None and len(x) / sr - debut >= mini:
        trous.append((round(debut, 2), round(len(x) / sr - debut, 2)))
    return trous


def raccord(x, sr, fenetre=0.2):
    """Saut fin -> debut, et ecart de niveau entre la fin et le debut. Fenetre de 200 ms : sur un moteur, 50 ms
    tombent tantot sur un coup d'allumage, tantot entre deux, et donnent de faux ecarts."""
    pente = np.median(np.abs(np.diff(x))) + 1e-9
    saut = abs(x[0] - x[-1]) / pente
    n = int(fenetre * sr)
    niv = abs(ms.db(np.sqrt(np.mean(x[-n:] ** 2))) - ms.db(np.sqrt(np.mean(x[:n] ** 2))))
    return float(saut), float(niv)


def controler(chemin, boucle=False, debut=None, fin=None):
    x, sr = ms.lire_wav(chemin, debut, fin)
    seg = "%s-%s s" % (debut or 0, fin if fin is not None else round(len(x) / sr, 2))
    h = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    lignes = []

    def ajoute(mesure, valeur, seuil, ok, preuve=""):
        lignes.append({"fichier": chemin, "segment": seg, "horodatage": h, "mesure": mesure,
                       "valeur": valeur, "seuil": seuil, "decision": "ok" if ok else "a corriger", "preuve": preuve})

    tp = crete_vraie(x)
    ajoute("crete_vraie_dbtp", round(tp, 2), SEUILS["crete_vraie_dbtp"], tp <= SEUILS["crete_vraie_dbtp"])
    ajoute("sonie_lufs", round(lufs(x, sr), 2), "info", True)
    pk = np.abs(x).max() + 1e-12
    ec = 100 * float(np.mean(np.abs(x) >= 0.999))
    ajoute("ecretage_pct", round(ec, 3), SEUILS["ecretage_pct"], ec <= SEUILS["ecretage_pct"])
    dc = 100 * abs(float(x.mean())) / pk
    ajoute("dc_pct", round(dc, 3), SEUILS["dc_pct"], dc <= SEUILS["dc_pct"])
    tr = silences(x, sr, mini=SEUILS["silence_s"])
    ajoute("silences", len(tr), 0, not tr, "; ".join("%.2f s (%.2f s)" % t for t in tr[:10]))
    if boucle:
        s, nv = raccord(x, sr)
        ajoute("raccord_saut_x_pente", round(s, 2), SEUILS["raccord_x_pente"], s <= SEUILS["raccord_x_pente"])
        ajoute("raccord_niveau_db", round(nv, 2), SEUILS["raccord_niveau_db"], nv <= SEUILS["raccord_niveau_db"])
    return lignes


def ecrire(lignes, sortie):
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump({"genere": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                   "avertissement": "mesures numeriques seulement : elles ne remplacent pas l'ecoute", "lignes": lignes},
                  f, ensure_ascii=False, indent=1)
    cols = ["fichier", "segment", "horodatage", "mesure", "valeur", "seuil", "decision", "preuve"]
    with open(os.path.splitext(sortie)[0] + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        for l in lignes:
            w.writerow([l.get(k, "") for k in cols])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("wav", nargs="+")
    p.add_argument("--sortie", default="rapport_controles.json")
    p.add_argument("--boucle", action="store_true", help="controler aussi le raccord fin -> debut")
    a = p.parse_args()
    tout = []
    for w in a.wav:
        tout += controler(w, a.boucle)
    ecrire(tout, a.sortie)
    print("%d mesures, %d a corriger -> %s" % (len(tout), sum(l["decision"] != "ok" for l in tout), a.sortie))
