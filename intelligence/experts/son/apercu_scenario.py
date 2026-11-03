"""Apercu v5 : un scenario complet a ecouter avant de construire le projet FMOD.

Reprend tout ce que Mendy a demande le 03/11/2026 :
- ralenti tres bas facon V8 a cames (« bop bop », galop de v4) ;
- echappement sur un ton grave ;
- claquements au passage de rapport et a la levee de pied ;
- sons d'air : purge du compresseur (decompression), frein de parc, pschitt de boite, frein pneumatique, suspension.

Simulation hors FMOD et hors jeu, faite seulement avec les sons de Mendy (lecture seule).
Usage : python3 apercu_scenario.py <dossier Mes_sons> <dossier sortie> [regime_ralenti | boucle_ralenti.wav]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mesure_son as ms  # noqa: E402
from apercu_v3 import (COUCHES, PETARADES, SR, ecrire, grains_allumage, moteur,  # noqa: E402
                       normaliser, petarades, ralenti_galop, timbre_reference)

V8 = "Scania_V8_open_pipe_v2"
NG = "Scania_NG_effets"
MAN = "MAN_TGX_2020"

# Evenements d'air : (role, dossier, fichier). Choisis d'apres la mesure du 03/11 (pas d'ecretage, signature d'air).
AIR = {
    "purge": (V8, "air_compressor"),       # decompression du regulateur (air_cutoff)
    "frein_parc_off": (NG, "hb_off"),       # desserrage du frein de parc
    "boite": (MAN, "air_gear_0"),           # pschitt de la boite pneumatique
    "boite_b": (MAN, "air_gear_1"),
    "clunk": (MAN, "clunk"),                # verrouillage mecanique du rapport
    "frein": (NG, "brake1"),                # relachement du frein pneumatique a l'arret
    "suspension": (NG, "liftaxle"),         # air de la suspension (mise a niveau)
}


def lire(sons, dossier, nom):
    x, sr = ms.lire_wav(os.path.join(sons, dossier, nom + ".wav"))
    if sr != SR:  # reechantillonnage lineaire simple
        t = np.arange(int(len(x) * SR / sr)) * sr / SR
        x = np.interp(t, np.arange(len(x)), x)
    return x


def egaliser_grave(x, sr=SR):
    """Ton grave : +4 dB de 70 a 250 Hz, aigus adoucis au-dessus de 2 kHz (-6 dB a 4 kHz et plus), sub inchange."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    g_db = np.zeros_like(f)
    corps = (f >= 70) & (f <= 250)
    g_db[corps] = 4.0
    rampe = (f > 250) & (f < 400)
    g_db[rampe] = 4.0 * (400 - f[rampe]) / 150
    haut = f >= 2000
    g_db[haut] = -6.0 * np.clip((f[haut] - 2000) / 2000, 0, 1)
    return np.fft.irfft(X * 10 ** (g_db / 20), len(x))


def poser(piste, son, t, gain=1.0, duree=None, fondu=0.03):
    i = int(t * SR)
    s = son if duree is None else son[:int(duree * SR)].copy()
    s = s.copy()
    fd = min(int(fondu * SR), len(s) // 2)
    if fd:
        s[-fd:] *= np.linspace(1, 0, fd)
    fin = min(len(piste), i + len(s))
    piste[i:fin] += gain * s[:fin - i]


def courbe(points, n):
    """Courbe par morceaux lineaire a partir de (temps s, valeur)."""
    t = np.arange(n) / SR
    pt = np.array(points, dtype=float)
    return np.interp(t, pt[:, 0], pt[:, 1])


def scenario(sons, ralenti=300, graine=5, boucle_ralenti=None):
    rng = np.random.default_rng(graine)
    duree = 46.0
    n = int(duree * SR)
    # Regime (tr/min) et charge (0..1) du scenario
    regime = courbe([(0, 600), (12, 600), (12.4, 1400), (13.3, 650), (14.6, 650), (15.0, 1450), (16.0, 650),
                     (19.0, 650), (20.5, 1350), (22.0, 1400), (22.4, 950), (24.5, 1350), (26.0, 1400),
                     (26.4, 1000), (29.0, 1350), (31.0, 1350), (33.5, 700), (34.5, 600), (46, 600)], n)
    charge = courbe([(0, 0), (12, 0), (12.05, 1), (12.4, 1), (12.45, 0), (14.6, 0), (14.65, 1), (15.0, 1),
                     (15.05, 0), (19.0, 0), (19.1, 0.8), (22.0, 0.8), (22.05, 0), (22.4, 0), (22.5, 0.8),
                     (26.0, 0.8), (26.05, 0), (26.4, 0), (26.5, 0.8), (31.0, 0.6), (31.1, 0), (46, 0)], n)
    # decel : regime au-dessus du ralenti et pied leve -> claquements
    decel = np.clip((regime - 800) / 400, 0, 1) * (charge < 0.05)
    # Ralenti tres bas (galop), present seulement pres du ralenti
    gm = grains_allumage(lire(sons, V8, "500_op_idle"), SR)
    ge = grains_allumage(lire(sons, V8, "exhaust_op"), SR)
    if boucle_ralenti:  # vrai ralenti enregistre (boucle_reelle.py), repete sans saut
        b, _ = ms.lire_wav(boucle_ralenti)
        bas = np.tile(b, int(np.ceil(n / len(b))))[:n]
    else:
        bas = timbre_reference(ralenti_galop(gm, ge, ralenti, duree, rng))
    bas = bas / (np.sqrt(np.mean(bas ** 2)) + 1e-9)
    couches = [(r, lire(sons, V8, nom)) for r, nom in COUCHES]
    haut = moteur(couches, regime, charge, decel)
    haut = haut / (np.sqrt(np.mean(haut[regime > 900] ** 2)) + 1e-9)
    # fondu ralenti bas -> couches entre 650 et 850 tr/min (puissance constante)
    a = np.clip((regime - 650) / 200, 0, 1)
    eng = np.sqrt(1 - a) * bas * 0.9 + np.sqrt(a) * haut
    pops = petarades([lire(sons, V8, p) for p in PETARADES], decel, rng)
    pops = pops / (np.sqrt(np.mean(pops[decel > 0.3] ** 2)) + 1e-9) if (decel > 0.3).any() else pops
    moteur_total = egaliser_grave(eng + 0.9 * pops)
    # Sons d'air (pas d'egalisation grave : ce sont des souffles)
    air = np.zeros(n)
    s = {k: lire(sons, d, f) for k, (d, f) in AIR.items()}
    for k in s:
        s[k] = s[k] / (np.sqrt(np.mean(s[k] ** 2)) + 1e-9)
    poser(air, s["purge"], 7.0, 0.35)                     # purge du compresseur au ralenti
    poser(air, s["frein_parc_off"], 17.0, 0.30, 2.5)      # desserrage avant le depart
    for t in (22.05, 26.05):                             # passages de rapport
        poser(air, s["boite"] if t < 24 else s["boite_b"], t, 0.30)
        poser(air, s["clunk"], t + 0.25, 0.12)
    poser(air, s["frein"], 35.0, 0.35)                    # arret : frein pneumatique relache
    poser(air, s["suspension"], 37.5, 0.32, 3.0, 0.4)     # suspension qui se remet a niveau
    poser(air, s["purge"], 42.0, 0.35)
    mix = moteur_total + air
    return normaliser(mix, -1.0), regime, charge


REPERES = [
    (0, "ralenti tres bas (galop)"), (7.0, "purge du compresseur"), (12.0, "coup de gaz + claquements"),
    (14.6, "2e coup de gaz"), (17.0, "frein de parc desserre"), (19.0, "depart en charge"),
    (22.0, "passage de rapport : claquements + pschitt de boite"), (26.0, "2e passage de rapport"),
    (31.0, "levee de pied : claquements"), (35.0, "arret : frein pneumatique"), (37.5, "suspension a niveau"),
    (42.0, "purge au ralenti"),
]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print(__doc__)
        return 1
    sons, sortie = argv[0], argv[1]
    arg = argv[2] if len(argv) > 2 else "300"
    os.makedirs(sortie, exist_ok=True)
    if arg.lower().endswith(".wav"):  # 3e argument = boucle de vrai ralenti
        x, _, _ = scenario(sons, boucle_ralenti=arg)
        nom = os.path.join(sortie, "scenario_complet_" + os.path.basename(arg))
    else:
        ralenti = int(arg)
        x, _, _ = scenario(sons, ralenti)
        nom = os.path.join(sortie, "v5_scenario_complet_ralenti_%d.wav" % ralenti)
    ecrire(nom, x)
    with open(os.path.join(sortie, "v5_reperes.txt"), "w", encoding="utf-8") as f:
        for t, quoi in REPERES:
            f.write("%5.1f s  %s\n" % (t, quoi))
    print(nom)
    return 0


if __name__ == "__main__":
    sys.exit(main())
