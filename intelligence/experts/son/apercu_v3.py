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


# ---------------------------------------------------------------------------------------------
# Ralenti tres lent « bop bop bop » (demande de Mendy 03/11 19:44) : on ne ralentit pas la boucle
# (le son deviendrait sourd et baveux), on recompose le ralenti coup d'allumage par coup d'allumage,
# avec les vrais coups pris dans ses sons, espaces au regime voulu et accentues une fois par tour.

def grains_allumage(x, sr, nb=24, avant=0.004, apres=0.075):
    """Extrait les coups d'allumage les plus nets : pics d'enveloppe espaces d'au moins 22 ms."""
    e = ms.enveloppe(x, sr, 60.0)
    dist = int(0.022 * sr)
    pics = []
    i = dist
    while i < len(e) - dist:
        j = i + int(np.argmax(e[i:i + dist]))
        if e[j] == e[max(j - dist, 0):j + dist].max():
            pics.append(j)
        i = j + dist
    pics = sorted(pics, key=lambda p: -e[p])[:nb]
    a, z = int(avant * sr), int(apres * sr)
    fen = np.concatenate([np.linspace(0, 1, a), np.exp(-np.linspace(0, 5, z))])
    return [x[p - a:p + z] * fen for p in pics if p - a >= 0 and p + z <= len(x)]


def ralenti_lent(grains_moteur, grains_echap, rpm, duree, rng, cylindres=8):
    """Un coup tous les 120/(rpm*cyl) s ; accent par tour (motif V8 a vilebrequin croise) ; petites irregularites."""
    n = int(duree * SR)
    out = np.zeros(n + SR)
    pas = 120.0 / (rpm * cylindres)
    motif = [1.0, 0.45, 0.7, 0.4]  # 4 coups par tour : un fort, des plus faibles -> « bop » une fois par tour
    t, k = 0.0, 0
    while t < duree:
        g = grains_moteur[rng.integers(len(grains_moteur))]
        h = grains_echap[rng.integers(len(grains_echap))]
        amp = motif[k % 4] * rng.uniform(0.85, 1.15)
        i = int(t * SR)
        out[i:i + len(g)] += amp * g
        out[i:i + len(h)] += amp * 0.9 * h  # le grave de l'echappement fait le « bop »
        t += pas * rng.uniform(0.93, 1.07)
        k += 1
    return out[:n]


def main_lent(sons, sortie, regimes=(300, 200), duree=8.0):
    rng = np.random.default_rng(11)
    gm = grains_allumage(charger(sons, "500_op_idle"), SR)
    ge = grains_allumage(charger(sons, "exhaust_op"), SR)
    noms = []
    for rpm in regimes:
        x = ralenti_lent(gm, ge, rpm, duree, rng)
        nom = os.path.join(sortie, "v3_3_ralenti_lent_%d.wav" % rpm)
        ecrire(nom, normaliser(x, -1))
        noms.append(nom)
    return noms


# ---------------------------------------------------------------------------------------------
# v4 calee sur la reference envoyee par Mendy (video Shelby GT500 1967, V8 a gros arbre a cames),
# mesuree le 03/11 : 75-92 % de l'energie entre 80 et 250 Hz, presque rien au-dessus de 1 kHz,
# coups d'allumage rapides modules par un « galop » lent et irregulier (~2 par seconde).

def timbre_reference(x, sr=SR):
    """Filtre doux en frequence : garde 80-250 Hz, -4 dB sous 80 Hz, -8 dB sous 60 Hz (la reference a 25 % sous 80 Hz), pente de -10 dB vers 1 kHz et au-dela."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    g_db = np.zeros_like(f)
    g_db[f < 80] = -4.0
    g_db[f < 60] = -8.0
    haut = f > 300
    g_db[haut] = -10.0 * np.clip(np.log2(f[haut] / 300) / np.log2(1000 / 300), 0, 1.6)
    return np.fft.irfft(X * 10 ** (g_db / 20), len(x))


def ralenti_galop(grains_moteur, grains_echap, rpm, duree, rng, cylindres=8):
    """Comme ralenti_lent, plus un galop d'arbre a cames : tous les 2 a 3 tours, un tour plus fort et un peu retarde."""
    n = int(duree * SR)
    out = np.zeros(n + SR)
    pas = 120.0 / (rpm * cylindres)
    motif = [1.0, 0.45, 0.7, 0.4]
    t, k, tour, prochain_galop = 0.0, 0, 0, 2
    accent = 1.0
    while t < duree:
        if k % 4 == 0:
            tour += 1
            if tour >= prochain_galop:
                accent, prochain_galop = rng.uniform(1.35, 1.6), tour + rng.integers(2, 4)
                t += pas * rng.uniform(0.15, 0.35)  # petit retard : le « galop »
            else:
                accent = rng.uniform(0.75, 0.95)
        g = grains_moteur[rng.integers(len(grains_moteur))]
        h = grains_echap[rng.integers(len(grains_echap))]
        amp = motif[k % 4] * accent * rng.uniform(0.9, 1.1)
        i = int(t * SR)
        out[i:i + len(g)] += amp * g
        out[i:i + len(h)] += amp * 1.1 * h
        t += pas * rng.uniform(0.94, 1.06)
        k += 1
    return out[:n]


def main_v4(sons, sortie, regimes=(300, 200), duree=8.0):
    rng = np.random.default_rng(23)
    gm = grains_allumage(charger(sons, "500_op_idle"), SR)
    ge = grains_allumage(charger(sons, "exhaust_op"), SR)
    noms = []
    for rpm in regimes:
        x = timbre_reference(ralenti_galop(gm, ge, rpm, duree, rng))
        nom = os.path.join(sortie, "v4_ralenti_galop_%d.wav" % rpm)
        ecrire(nom, normaliser(x, -1))
        noms.append(nom)
    return noms


# --- v6 (03/11 20:16, Mendy : « trop rapide et aigu, je veux du grave ») ---
def grave_grain(g, facteur=0.6):
    """Joue un coup d'allumage reel plus lentement : plus grave et plus long (facteur 0,6 = environ -9 demi-tons)."""
    t = np.arange(int(len(g) / facteur)) * facteur
    return np.interp(t, np.arange(len(g)), g)


def filtre_grave(x, sr=SR):
    """Garde le grave : +5 dB de 40 a 120 Hz, coupe douce au-dessus de 500 Hz (-12 dB a 1 kHz, -24 dB a 2 kHz)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    g_db = np.zeros_like(f)
    g_db[(f >= 40) & (f <= 120)] = 5.0
    r = (f > 120) & (f < 200)
    g_db[r] = 5.0 * (200 - f[r]) / 80
    g_db[f < 25] = -12.0
    h = f > 500
    g_db[h] = -12.0 * np.log2(f[h] / 500)
    return np.fft.irfft(X * 10 ** (np.maximum(g_db, -40) / 20), len(x))


def ralenti_grave(grains_moteur, grains_echap, rpm, duree, rng, facteur=0.6, cylindres=8):
    """Un gros « bop » grave par tour, les 3 autres allumages tres faibles, galop tous les 2-3 tours."""
    gm = [grave_grain(g, facteur) for g in grains_moteur]
    ge = [grave_grain(g, facteur) for g in grains_echap]
    n = int(duree * SR)
    out = np.zeros(n + 2 * SR)
    pas = 120.0 / (rpm * cylindres)
    motif = [1.0, 0.12, 0.25, 0.1]
    t, k, tour, prochain = 0.0, 0, 0, 2
    accent = 1.0
    while t < duree:
        if k % 4 == 0:
            tour += 1
            if tour >= prochain:
                accent, prochain = rng.uniform(1.3, 1.5), tour + rng.integers(2, 4)
                t += pas * rng.uniform(0.15, 0.35)
            else:
                accent = rng.uniform(0.8, 0.95)
        g = gm[rng.integers(len(gm))]
        h = ge[rng.integers(len(ge))]
        amp = motif[k % 4] * accent * rng.uniform(0.9, 1.1)
        i = int(t * SR)
        out[i:i + len(g)] += amp * g
        out[i:i + len(h)] += amp * 1.2 * h
        t += pas * rng.uniform(0.95, 1.05)
        k += 1
    return filtre_grave(out[:n])


def main_v6(sons, sortie, regimes=(150, 120), duree=10.0):
    rng = np.random.default_rng(29)
    gm = grains_allumage(charger(sons, "500_op_idle"), SR, apres=0.11)
    ge = grains_allumage(charger(sons, "exhaust_op"), SR, apres=0.11)
    noms = []
    for rpm in regimes:
        nom = os.path.join(sortie, "v6_ralenti_grave_%d.wav" % rpm)
        ecrire(nom, normaliser(ralenti_grave(gm, ge, rpm, duree, rng), -1))
        noms.append(nom)
    return noms


# --- v7 (03/11 20:17, Mendy : « les sons sont saturés ») ---
# Aucun ecretage numerique mesure (sources et v5/v6 : 0 plateau). La saturation entendue vient de :
# coups d'allumage coupes avec une attaque lineaire de 4 ms (clic), coups pris avec leur voisin (rapes),
# niveau a -1 dBFS avec beaucoup de sub (un petit haut-parleur sature sous 50 Hz).
def grains_propres(x, sr, nb=12, avant=0.008, apres=0.11):
    """Coups d'allumage les plus propres : fenetre en cosinus (pas de clic), on garde ceux qui ont le moins d'aigus."""
    e = ms.enveloppe(x, sr, 60.0)
    dist = int(0.022 * sr)
    pics, i = [], dist
    while i < len(e) - dist:
        j = i + int(np.argmax(e[i:i + dist]))
        if e[j] == e[max(j - dist, 0):j + dist].max():
            pics.append(j)
        i = j + dist
    a, z = int(avant * sr), int(apres * sr)
    fen = np.concatenate([0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a)), 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, z))])
    gs = []
    for p in pics:
        if p - a < 0 or p + z > len(x):
            continue
        g = x[p - a:p + z] * fen
        G = np.abs(np.fft.rfft(g)) ** 2
        f = np.fft.rfftfreq(len(g), 1.0 / sr)
        gs.append((G[f > 1000].sum() / (G.sum() + 1e-12), g / (np.abs(g).max() + 1e-9)))
    gs.sort(key=lambda t: t[0])
    return [g for _, g in gs[:nb]]


def adoucir(x, sr=SR):
    """Coupe sous 35 Hz (le sub qui fait saturer les petits haut-parleurs), coupe douce au-dessus de 400 Hz."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    g = np.ones_like(f)
    g[f < 35] = (f[f < 35] / 35) ** 4
    h = f > 400
    g[h] = 1.0 / (1 + (f[h] / 400) ** 4) ** 0.5 * (1 + 1) ** 0.5
    return np.fft.irfft(X * np.minimum(g, 1.0), len(x))


def main_v7(sons, sortie, regimes=(150, 120), duree=10.0):
    rng = np.random.default_rng(31)
    gm = grains_propres(charger(sons, "500_op_idle"), SR)
    ge = grains_propres(charger(sons, "exhaust_op"), SR)
    noms = []
    for rpm in regimes:
        x = adoucir(ralenti_grave(gm, ge, rpm, duree, rng, facteur=0.65))
        nom = os.path.join(sortie, "v7_ralenti_grave_propre_%d.wav" % rpm)
        ecrire(nom, normaliser(x, -6.0))  # 5 dB de marge de plus que v6
        noms.append(nom)
    return noms
