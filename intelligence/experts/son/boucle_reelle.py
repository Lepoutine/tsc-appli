"""Boucle de ralenti tiree d'un VRAI enregistrement (video de reference de Mendy).

1. On prend une zone ou le niveau est stable (moteur au ralenti, sans voix ni coup de gaz).
2. On mesure le cycle moteur dans l'enveloppe (un cycle 4 temps = 2 tours).
3. On coupe un nombre entier de cycles et on raccorde la fin sur le debut par un fondu a puissance constante,
   pose sur une frontiere de cycle : la boucle tourne sans saut ni clic.
4. En option, on la joue plus lentement (plus lent ET plus grave, comme un moteur plus bas).

Usage : python3 boucle_reelle.py <wav> <debut s> <fin s> <sortie.wav> [vitesse=1.0] [duree_cible=8]
"""
import sys

import numpy as np

import mesure_son as ms

SR = 48000


def cycle_moteur(x, sr, mini=0.12, maxi=0.6):
    """Periode du cycle moteur (s) : pic d'autocorrelation de l'enveloppe entre mini et maxi."""
    e = ms.enveloppe(x, sr, 40.0)
    e = e - e.mean()
    pas = 48
    e = e[::pas]
    fs = sr / pas
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    a, b = int(mini * fs), int(maxi * fs)
    k = a + int(np.argmax(ac[a:b]))
    return k / fs


def boucle(x, sr, duree_cible=8.0, fondu=0.08):
    cyc = cycle_moteur(x, sr)
    n_cyc = max(1, int(round(duree_cible / cyc)))
    L = int(round(n_cyc * cyc * sr))
    F = int(fondu * sr)
    if L + F > len(x):
        n_cyc = int((len(x) - F) / sr / cyc)
        L = int(round(n_cyc * cyc * sr))
    corps = x[:L].copy()
    suite = x[L:L + F]  # ce qui suit la fin dans l'enregistrement : il se raccorde au debut
    t = np.linspace(0, np.pi / 2, F)
    corps[:F] = corps[:F] * np.sin(t) + suite * np.cos(t)
    return corps, cyc, n_cyc


def ralentir(x, vitesse):
    if vitesse == 1.0:
        return x
    t = np.arange(int(len(x) / vitesse)) * vitesse
    return np.interp(t, np.arange(len(x)), x)


def faire(wav, debut, fin, sortie, vitesse=1.0, duree_cible=8.0):
    x, sr = ms.lire_wav(wav, debut, fin)
    x = x - x.mean()
    b, cyc, n = boucle(x, sr, duree_cible * vitesse)
    b = ralentir(b, vitesse)
    b = b / (np.abs(b).max() + 1e-9) * 10 ** (-6 / 20)
    import wave
    with wave.open(sortie, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(b, -1, 1) * 32767).astype("<i2").tobytes())
    rpm = 120.0 / cyc  # 1 cycle = 2 tours
    return {"cycle_s": round(cyc, 4), "cycles": n, "regime_source_tr_min": round(rpm), "regime_joue_tr_min": round(rpm * vitesse),
            "duree_s": round(len(b) / sr, 2)}


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 4:
        print(__doc__)
        sys.exit(1)
    print(faire(a[0], float(a[1]), float(a[2]), a[3], float(a[4]) if len(a) > 4 else 1.0, float(a[5]) if len(a) > 5 else 8.0))
