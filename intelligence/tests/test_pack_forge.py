import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experts", "son"))
import pack_forge  # noqa: E402

ROLES_FORGE = {"ralenti", "charge", "sans", "turbo", "clapet", "clapet_on", "clapet_off", "demarrage", "arret", "coup_gaz",
               "claquement", "frein_moteur", "boite_air", "air_purge", "frein_air", "frein_parc", "suspension", "reference", "autre"}


class TestPackForge(unittest.TestCase):
    def test_roles_et_chemins(self):
        with tempfile.TemporaryDirectory() as d:
            fichiers = ["expert_son/segments_reels/01_164L_ralenti_stable.wav", "expert_son/segments_reels/08_R580_claquements.wav",
                        "Mes_sons/boucles_reparees/c_900_op_idle.wav", "Mes_sons/boucles_reparees/c_500_op_idle.wav",
                        "Mes_sons/Scania_V8_open_pipe_v2/claquant_1.wav", "Mes_sons/Scania_NG_effets/liftaxle.wav",
                        "Mes_sons/MAN_TGX_2020/air_gear_0.wav", "expert_son/videos_completes/r580.flac"]
            for f in fichiers:
                os.makedirs(os.path.join(d, os.path.dirname(f)), exist_ok=True)
                open(os.path.join(d, f), "wb").close()
            p = pack_forge.construire(d)
            r = {e["fichier"]: e for e in p["sons"]}
            self.assertEqual(len(r), len(fichiers))
            self.assertTrue(all(e["role"] in ROLES_FORGE for e in p["sons"]))
            self.assertEqual(r[fichiers[0]]["role"], "ralenti")
            self.assertEqual(r[fichiers[0]]["rpm"], 500)
            self.assertEqual(r[fichiers[1]]["role"], "claquement")
            self.assertEqual((r[fichiers[2]]["role"], r[fichiers[2]]["rpm"]), ("charge", 900))
            self.assertEqual(r[fichiers[3]]["role"], "autre")  # un seul ralenti actif : le vrai
            self.assertEqual(r[fichiers[5]]["role"], "suspension")
            self.assertEqual(r[fichiers[6]]["role"], "boite_air")
            self.assertEqual(r[fichiers[7]]["role"], "reference")
            self.assertEqual(sum(e["role"] == "ralenti" for e in p["sons"]), 1)


if __name__ == "__main__":
    unittest.main()
