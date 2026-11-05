"""Tests de l'expert Performance (comparateur PresentMon) et de l'expert Conduite (contrôleur 561/2006)."""
import os
import sys
import tempfile
import unittest

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "experts", "performance"))
sys.path.insert(0, os.path.join(ICI, "..", "experts", "conduite"))
import frametime  # noqa: E402
import regles_561  # noqa: E402


class TestFrametime(unittest.TestCase):
    def test_stats_constant(self):
        s = frametime.stats(np.full(500, 20.0))
        self.assertAlmostEqual(s["fps_moyen"], 50.0)
        self.assertAlmostEqual(s["fps_1pc_bas"], 50.0)
        self.assertEqual(s["saccades"], 0)

    def test_lire_csv_filtre_et_colonnes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("Application,FrameTime\n" + "".join("eurotrucks2.exe,16.6\ndwm.exe,5\n" for _ in range(150)))
        try:
            v = frametime.lire_csv(f.name, "eurotrucks2.exe")
        finally:
            os.unlink(f.name)
        self.assertEqual(len(v), 150)
        self.assertTrue(np.all(v == 16.6))

    def test_trop_court(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("MsBetweenPresents\n" + "16\n" * 20)
        try:
            with self.assertRaises(ValueError):
                frametime.lire_csv(f.name)
        finally:
            os.unlink(f.name)

    def test_verdicts(self):
        rng = np.random.default_rng(3)
        a = 16.0 + rng.normal(0, 0.8, 3000)
        self.assertEqual(frametime.comparer(a, 16.0 + rng.normal(0, 0.8, 3000))["verdict"], "pas de différence prouvée")
        self.assertEqual(frametime.comparer(a, 14.0 + rng.normal(0, 0.7, 3000))["verdict"], "mieux")
        b = 14.0 + rng.normal(0, 0.7, 3000)
        b[::25] *= 3  # plus d'images/s en moyenne mais des saccades : le 1 % bas l'emporte
        self.assertEqual(frametime.comparer(a, b)["verdict"], "pire")


class TestRegles561(unittest.TestCase):
    def art(self, tr):
        return [i["article"] for i in regles_561.controler(tr)["infractions"]]

    def test_journee_legale(self):
        self.assertEqual(self.art([("conduite", 270), ("repos", 45), ("conduite", 270), ("repos", 660)]), [])

    def test_pause_15_puis_30(self):
        self.assertEqual(self.art([("conduite", 200), ("repos", 15), ("conduite", 70), ("repos", 30), ("conduite", 200), ("repos", 660)]), [])

    def test_pause_30_puis_15_refusee(self):
        self.assertEqual(self.art([("conduite", 200), ("repos", 30), ("conduite", 70), ("repos", 15), ("conduite", 10), ("repos", 660)]), ["7"])

    def test_pause_de_moins_de_15_ne_compte_pas(self):
        self.assertEqual(self.art([("conduite", 200), ("repos", 14), ("conduite", 80), ("repos", 660)]), ["7"])

    def test_dix_heures_et_plus(self):
        r = regles_561.controler([("conduite", 270), ("repos", 45), ("conduite", 270), ("repos", 45), ("conduite", 60), ("repos", 660)])
        self.assertEqual((r["infractions"], r["prolongations"]), ([], 1))
        self.assertEqual(self.art([("conduite", 270), ("repos", 45), ("conduite", 270), ("repos", 45), ("conduite", 61), ("repos", 660)]), ["6(1)"])

    def test_repos_fractionne_et_reduit(self):
        self.assertEqual(regles_561.controler([("conduite", 240), ("repos", 180), ("conduite", 240), ("repos", 540)])["repos_reduits"], 0)
        self.assertEqual(regles_561.controler([("conduite", 240), ("repos", 45), ("conduite", 240), ("repos", 540)])["repos_reduits"], 1)

    def test_repos_apres_24h(self):
        self.assertEqual(self.art([("conduite", 200), ("travail", 800), ("repos", 540)]), ["8(2)"])

    def test_activite_inconnue(self):
        with self.assertRaises(ValueError):
            regles_561.controler([("sieste", 10)])


if __name__ == "__main__":
    unittest.main()
