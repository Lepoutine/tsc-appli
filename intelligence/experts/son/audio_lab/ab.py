"""Section 8 du cahier des charges : comparaison A/B a volume egal.

Les deux sons sont ramenes a la meme sonie (LUFS), puis on ecrit :
- un fichier d'ecoute qui alterne A et B par tranches (avec un bip grave court entre les deux, 1 bip = A, 2 = B) ;
- les ecarts de bandes de frequence et de dynamique, mesures dans les memes conditions.
L'avis final reste celui de Mendy a l'ecoute.
Usage : python3 -m audio_lab.ab A.wav B.wav sortie.wav [--tranche 4]
"""
import argparse
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mesure_son as ms  # noqa: E402
from audio_lab.controles import lufs  # noqa: E402

SR = 48000


def charger(chemin):
    x, sr = ms.lire_wav(chemin)
    if sr != SR:
        t = np.arange(int(len(x) * SR / sr)) * sr / SR
        x = np.interp(t, np.arange(len(x)), x)
    return x


def bip(n_bips):
    t = np.arange(int(0.08 * SR)) / SR
    b = 0.2 * np.sin(2 * np.pi * 220 * t) * np.hanning(len(t))
    pause = np.zeros(int(0.06 * SR))
    return np.concatenate([np.concatenate([b, pause]) for _ in range(n_bips)] + [np.zeros(int(0.15 * SR))])


def a_volume_egal(a, b, cible=-20.0):
    return a * 10 ** ((cible - lufs(a, SR)) / 20), b * 10 ** ((cible - lufs(b, SR)) / 20)


def alterner(a, b, tranche=4.0):
    n = int(tranche * SR)
    f = int(0.01 * SR)
    morceaux = []
    for i in range(0, min(len(a), len(b)), n):
        for k, s in ((1, a), (2, b)):
            m = s[i:i + n].copy()
            m[:f] *= np.linspace(0, 1, f)
            m[-f:] *= np.linspace(1, 0, f)
            morceaux += [bip(k), m]
    return np.concatenate(morceaux)


def comparer(a, b):
    ma, mb = ms.mesurer(a, SR), ms.mesurer(b, SR)
    lignes = []
    for k in ma["bandes_pct"]:
        lignes.append(("bande %s (%%)" % k, round(ma["bandes_pct"][k], 1), round(mb["bandes_pct"][k], 1)))
    for k in ("centroide_hz", "facteur_crete_db", "irregularite_pct", "craquements_par_s"):
        lignes.append((k, ma[k], mb[k]))
    return lignes


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("sortie")
    p.add_argument("--tranche", type=float, default=4.0)
    o = p.parse_args(argv)
    a, b = a_volume_egal(charger(o.a), charger(o.b))
    x = alterner(a, b, o.tranche)
    x = x / max(1.0, np.abs(x).max() / 0.89)
    with wave.open(o.sortie, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    print("A/B a volume egal (-20 LUFS) -> %s" % o.sortie)
    for nom, va, vb in comparer(a, b):
        print("  %-24s A %-8s B %s" % (nom, va, vb))
    return 0


if __name__ == "__main__":
    sys.exit(main())
