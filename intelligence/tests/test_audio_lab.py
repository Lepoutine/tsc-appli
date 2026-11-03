import math
import os
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experts", "son"))
from audio_lab import controles, inventaire  # noqa: E402

SR = 48000


def ecrire(chemin, x):
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


class TestAudioLab(unittest.TestCase):
    def test_lufs_sinus_1khz(self):
        # BS.1770 : un sinus 997 Hz a 0 dBFS sur un canal vaut -3,01 LUFS
        t = np.arange(10 * SR) / SR
        x = np.sin(2 * np.pi * 997 * t)
        self.assertAlmostEqual(controles.lufs(x, SR), -3.01, delta=0.1)
        self.assertAlmostEqual(controles.lufs(0.1 * x, SR), -23.01, delta=0.1)

    def test_crete_vraie_inter_echantillons(self):
        # sinus a fs/4 dephase de 45 degres : echantillons a 0,707, vraie crete a 1,0 (0 dBTP)
        n = np.arange(SR)
        x = np.sin(2 * np.pi * n / 4 + math.pi / 4)
        self.assertLess(20 * math.log10(np.abs(x).max()), -2.9)
        self.assertAlmostEqual(controles.crete_vraie(x), 0.0, delta=0.2)

    def test_raccord_et_silence(self):
        t = np.arange(2 * SR) / SR
        propre = 0.5 * np.sin(2 * np.pi * 50 * t)  # 100 periodes entieres : raccord propre
        s, _ = controles.raccord(propre, SR)
        self.assertLess(s, controles.SEUILS["raccord_x_pente"])
        coupe = propre[: int(1.505 * SR)]
        s2, _ = controles.raccord(coupe, SR)
        self.assertGreater(s2, controles.SEUILS["raccord_x_pente"])
        trou = propre.copy()
        trou[SR // 2: SR] = 0
        self.assertEqual(len(controles.silences(trou, SR)), 1)

    def test_rapport_et_inventaire(self):
        with tempfile.TemporaryDirectory() as d:
            w = os.path.join(d, "a.wav")
            ecrire(w, 0.3 * np.sin(2 * np.pi * 100 * np.arange(SR) / SR))
            lignes = controles.controler(w, boucle=True)
            mesures = {l["mesure"]: l for l in lignes}
            self.assertEqual(mesures["ecretage_pct"]["decision"], "ok")
            self.assertIn("raccord_saut_x_pente", mesures)
            inv = inventaire.inventorier([d])
            self.assertEqual(inv[0]["frequence_hz"], SR)
            self.assertEqual(len(inv[0]["sha256"]), 64)
            j = os.path.join(d, "inv.json")
            inventaire.ecrire(inv, j)
            self.assertEqual(inventaire.verifier(j), [])
            ecrire(w, np.zeros(100))
            self.assertEqual(inventaire.verifier(j), [w])


if __name__ == "__main__":
    unittest.main()
