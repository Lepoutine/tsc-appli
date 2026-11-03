"""Tests de mesure_son.py sur des sons synthetiques dont on connait la reponse."""
import os, sys, tempfile, unittest, wave
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experts", "son"))
import mesure_son as ms

SR = 44100


def moteur(tr_min=600, cyl=8, duree=4.0, inegal=0.0, grave=1.0, craque=0, ecrete=False, graine=1):
    rng = np.random.default_rng(graine)
    f = tr_min / 60 * cyl / 2
    t = np.arange(int(duree * SR)) / SR
    x = np.zeros_like(t)
    per = 1.0 / f
    k = 0
    for t0 in np.arange(0, duree, per):
        a = 1.0 + (inegal if k % 2 else -inegal) + rng.normal(0, inegal / 2)
        m = (t >= t0) & (t < t0 + per)
        tt = t[m] - t0
        x[m] += a * (grave * np.sin(2 * np.pi * 45 * tt) + 0.4 * np.sin(2 * np.pi * 900 * tt)) * np.exp(-tt * 60)
        k += 1
    x += 0.01 * rng.normal(size=len(x))
    for _ in range(craque):
        i = rng.integers(0, len(x) - 200)
        x[i:i + 60] += rng.normal(0, 0.6, 60)
    x = x / np.max(np.abs(x)) * (1.6 if ecrete else 0.7)
    return np.clip(x, -1, 1)


def ecrire(chemin, x):
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


class TestMesure(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def test_regime_estime(self):
        for tr, ineg in ((600, 0.0), (900, 0.0), (600, 0.35), (750, 0.25)):
            r = ms.mesurer(moteur(tr, inegal=ineg), SR, 8)
            self.assertAlmostEqual(r["regime_estime_tr_min"], tr, delta=0.08 * tr)

    def test_lecture_wav_16_bits(self):
        p = os.path.join(self.d, "a.wav")
        ecrire(p, moteur())
        x, sr = ms.lire_wav(p, 1.0, 2.0)
        self.assertEqual(sr, SR)
        self.assertEqual(len(x), SR)

    def test_diagnostic_trouve_les_defauts(self):
        ref = ms.mesurer(moteur(inegal=0.35, grave=1.5, craque=20), SR, 8)
        mien = ms.mesurer(moteur(inegal=0.0, grave=0.2, ecrete=True), SR, 8)
        texte = " ".join(ms.diagnostic(mien, ref))
        self.assertIn("Pas assez gras", texte)
        self.assertIn("Ecretage", texte)
        self.assertIn("craquements", texte)
        self.assertTrue("regulier" in texte or "borborygme" in texte)

    def test_meme_son_aucun_ecart(self):
        r = ms.mesurer(moteur(inegal=0.3), SR, 8)
        d = ms.diagnostic(r, r)
        self.assertTrue(all("jonction" in x or "Aucun ecart" in x for x in d))


if __name__ == "__main__":
    unittest.main()
