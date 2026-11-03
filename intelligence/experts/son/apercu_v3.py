#!/usr/bin/env python3
"""Apercu v3 du V8 de Mendy (hors FMOD) : ralenti + 3 coups de gaz avec petarades de deceleration.

Python 3 + numpy. Lit les sons de Mes_sons (copie), n'ecrit que des apercus WAV dans --sortie.
Choix d'apres DIAGNOSTIC_V2.md : seulement des couches non ecretees, petarades tirees de claquant_1-3,
coups de gaz = vraie montee/descente de regime par fondu entre couches (pas une seule boucle accelaree).

  python3 apercu_v3.py --sons <Mes_sons> --sortie <dossier>
"""
import argparse
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesure_son as ms  # noqa: E402

SR = 48000
# couches moteur retenues (ecretage mesure < 0,01 %) et regime nominal de chacune
COUCHES = [(500, "500_op_idle"), (700, "700_op_idle"), (900, "900_op_idle"), (1100, "1100_op_idle"), (1300, "1300_op_idle")]
PETARADES = ["claquant_1", "claquant_2", "claquant_3"]
PITCH_MAX = 0.12  # jamais plus de 12 % de decalage de hauteur


def charger(dossier, nom):
    x, sr = ms.lire_wav(os.path.join(dossier, "Scania_V8_open_pipe_v2", nom + ".wav"))
    if sr != SR:  # reechantillonnage lineaire simple
        t = np.arange(int(len(x) * SR / sr)) * sr / SR
        x = np.interp(t, np.arange(len(x)), x)
    return x


def lire_variable(boucle, vitesse, phase0=0.0):
    """Lit une boucle a vitesse variable (1 = hauteur d'origine) ; renvoie le signal et la phase finale."""
    pos = phase0 + np.cumsum(vitesse)
    n = len(boucle)
    i = np.floor(pos).astype(np.int64) % n
    f = pos - np.floor(pos)
    return boucle[i] * (1 - f) + boucle[(i + 1) % n] * f, pos[-1]


def moteur(couches, regime, charge, decel=None):
    """Melange a puissance constante des 2 couches voisines du regime ; charge 0..1 renforce le grave."""
    rpms = np.array([r for r, _ in couches], dtype=float)
    out = np.zeros(len(regime))
    for k, (r, boucle) in enumerate(couches):
        # poids triangulaire entre couches voisines
        g = np.zeros(len(regime))
        if k > 0:
            m = (regime >= rpms[k - 1]) & (regime <= r)
            g[m] = (regime[m] - rpms[k - 1]) / (r - rpms[k - 1])
        else:
            g[regime <= r] = 1.0
        if k < len(couches) - 1:
            m = (regime > r) & (regime <= rpms[k + 1])
            g[m] = 1 - (regime[m] - r) / (rpms[k + 1] - r)
        else:
            g[regime > r] = 1.0
        g = np.sqrt(np.clip(g, 0, 1))  # puissance constante
        if not g.any():
            continue
        vitesse = np.clip(regime / r, 1 - PITCH_MAX, 1 + PITCH_MAX)
        sig, _ = lire_variable(boucle, vitesse)
        out += g * sig
    # charge : un peu plus de corps quand on accelere, moins a la levee de pied
    gain = 0.8 + 0.35 * charge
    if decel is not None:  # levee de pied : le moteur retombe, ce sont les petarades qu'on entend
        gain = gain - 0.45 * decel
    return out * gain


def petarades(sources, decel, rng):
    """Pose des fragments de petarades pendant les deceleration (decel = 0..1 par echantillon)."""
    out = np.zeros(len(decel))
    t = 0
    while t < len(decel) - SR // 10:
        if decel[t] > 0.3:
            src = sources[rng.integers(len(sources))]
            # fragments de 0,15-0,35 s (plusieurs claquements), fondus courts de 5 ms pour garder l'attaque
            lg = min(int(SR * rng.uniform(0.15, 0.35)), len(decel) - t)
            a = rng.integers(0, len(src) - lg)
            frag = src[a:a + lg].copy()
            fd = int(0.005 * SR)
            frag[:fd] *= np.linspace(0, 1, fd)
            frag[-fd:] *= np.linspace(1, 0, fd)
            out[t:t + lg] += frag * decel[t:t + lg] * rng.uniform(0.7, 1.0)
            t += int(lg * rng.uniform(0.7, 1.0))
        else:
            t += SR // 100
    return out


def profil_coups_de_gaz(duree, ralenti=600, coups=((1.5, 1400), (4.2, 1450), (7.0, 1300))):
    """Coups de gaz plafonnes a 1450 tr/min : au-dessus, les couches du jeu de Mendy sont ecretees (diagnostic v2).
    Regime et charge : montee rapide (~0,35 s), redescente plus lente (~0,9 s), comme un vrai coup de gaz."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    regime = np.full(n, float(ralenti))
    charge = np.zeros(n)
    decel = np.zeros(n)
    for t0, haut in coups:
        mont = (t >= t0) & (t < t0 + 0.35)
        x = (t[mont] - t0) / 0.35
        regime[mont] = ralenti + (haut - ralenti) * np.sin(x * np.pi / 2)
        charge[mont] = 1.0
        desc = (t >= t0 + 0.35) & (t < t0 + 1.25)
        x = (t[desc] - t0 - 0.35) / 0.9
        regime[desc] = ralenti + (haut - ralenti) * (1 - x) ** 2
        decel[desc] = np.clip(1.2 - x, 0, 1)
    # lissage pour eviter les marches
    k = np.ones(480) / 480
    return np.convolve(regime, k, "same"), np.convolve(charge, k, "same"), np.convolve(decel, k, "same")


def normaliser(x, crete_db=-1.0):
    return x / max(np.max(np.abs(x)), 1e-9) * 10 ** (crete_db / 20)


def ecrire(chemin, x):
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sons", required=True)
    ap.add_argument("--sortie", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.sortie, exist_ok=True)
    rng = np.random.default_rng(7)
    couches = [(r, charger(a.sons, n)) for r, n in COUCHES]
    # chaque couche a le meme niveau RMS, pour que les fondus ne creusent pas
    couches = [(r, b / np.sqrt(np.mean(b ** 2))) for r, b in couches]
    sources = [charger(a.sons, n) for n in PETARADES]

    # 1. ralenti seul, 8 s
    n = 8 * SR
    ral = moteur(couches, np.full(n, 600.0), np.zeros(n))
    ecrire(os.path.join(a.sortie, "v3_1_ralenti_600.wav"), normaliser(ral, -3))

    # 2. trois coups de gaz a l'arret avec petarades, 10 s
    regime, charge, decel = profil_coups_de_gaz(10.0)
    mot = moteur(couches, regime, charge, decel)
    pet = petarades(sources, decel, rng)
    # niveau des petarades : RMS egal a celui du moteur pendant les decelerations
    m = decel > 0.3
    pet = pet * 1.0 * np.sqrt(np.mean(mot[m] ** 2)) / max(np.sqrt(np.mean(pet[m] ** 2)), 1e-9)
    ecrire(os.path.join(a.sortie, "v3_2_coups_de_gaz_petarades.wav"), normaliser(mot + pet, -1))
    print("ecrit dans", a.sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
