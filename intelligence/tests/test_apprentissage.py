import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from apprentissage.boucle import Boucle, est_juge  # noqa: E402


def entrainer(ex):  # seuil moyen : un "modele" minimal pour tester la boucle
    return {"seuil": sum(e["x"] for e in ex) / len(ex), "bruit": ex[0].get("bruit", False)}


def juger(m, ex):
    ok = [((e["x"] > m["seuil"]) == e["y"]) != m["bruit"] for e in ex]
    return {"justesse": sum(ok) / len(ok)}


def donnees(n, bruit=False):
    return [{"cle": "s%d" % i, "x": i % 20, "y": i % 20 > 9, "bruit": bruit} for i in range(n)]


class TestBoucle(unittest.TestCase):
    def test_juge_fixe_et_regles(self):
        self.assertEqual(est_juge("abc"), est_juge("abc"))
        with tempfile.TemporaryDirectory() as d:
            b = Boucle(d, entrainer, juger)
            self.assertFalse(b.apprend(donnees(5))["adoptee"])           # trop peu
            self.assertTrue(b.apprend(donnees(60))["adoptee"])           # v1
            self.assertFalse(b.apprend(donnees(60))["adoptee"])          # rien de nouveau
            self.assertFalse(b.apprend(donnees(80, bruit=True))["adoptee"])  # pire sur le juge : refusee
            self.assertTrue(b.apprend(donnees(80))["adoptee"])           # v2
            self.assertEqual(len(b.etat["versions"]), 2)
            self.assertTrue(b.retour())
            self.assertEqual(b.etat["versions"][-1]["n"], 1)
            self.assertTrue(os.path.isfile(os.path.join(d, "version_002.json")))


if __name__ == "__main__":
    unittest.main()
