"""Juge PANNs : lecture sûre des poids et chaîne NumPy (sans le gros fichier de poids)."""
import io
import os
import pickle
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experts", "son"))
import juge_panns as J  # noqa: E402


class Piege:
    def __reduce__(self):
        return (os.system, ("echo pirate",))


class TestJugePanns(unittest.TestCase):
    def test_depickleur_refuse_le_code(self):
        with self.assertRaises(pickle.UnpicklingError):
            J._Depickleur(io.BytesIO(pickle.dumps(Piege())), {}).load()

    def test_conv3_contre_calcul_direct(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=(2, 5, 4)).astype(np.float32)
        w = rng.normal(size=(3, 2, 3, 3)).astype(np.float32)
        y = J._conv3(x, w)
        p = np.pad(x, ((0, 0), (1, 1), (1, 1)))
        ref = np.zeros((3, 5, 4))
        for o in range(3):
            for t in range(5):
                for f in range(4):
                    ref[o, t, f] = (w[o] * p[:, t:t + 3, f:f + 3]).sum()
        self.assertTrue(np.allclose(y, ref, atol=1e-4))

    def test_reechantillonne_garde_la_frequence(self):
        sr = 48000
        t = np.arange(sr) / sr
        y = J.reechantillonne(np.sin(2 * np.pi * 440 * t).astype(np.float32), sr)
        self.assertEqual(len(y), 32000)
        f = np.argmax(np.abs(np.fft.rfft(y))) * 32000 / len(y)
        self.assertAlmostEqual(f, 440, delta=1)

    def test_distance(self):
        a = np.array([[1.0, 0.0]])
        self.assertAlmostEqual(J.distance(a, a), 0.0)
        self.assertAlmostEqual(J.distance(a, np.array([[0.0, 1.0]])), 1.0)


if __name__ == "__main__":
    unittest.main()
