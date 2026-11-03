"""Tests de l'outil TSC Intelligence : python3 -m unittest discover -s intelligence/tests"""
import io, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "outils"))
import tsc_ia


class TestBase(unittest.TestCase):
    def test_base_reelle_sans_erreur(self):
        err, _ = tsc_ia.verifier()
        self.assertEqual(err, [])

    def test_dix_experts(self):
        ids = [a["id"] for a in tsc_ia.lire_json(tsc_ia.AGENTS)["agents"]]
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(set(ids)), 10)

    def test_base_jointe_sound_forge_chargee(self):
        ids = {f["id"] for f in tsc_ia.fiches()}
        self.assertIn("fmod_scripting", ids)
        self.assertIn("audit_pipeline_161", ids)

    def test_chercher_trouve_le_piege_zip(self):
        out = io.StringIO()
        res = tsc_ia.chercher(["zip"], out)
        self.assertTrue(any(r[2] == "piege_zip_scs" for r in res))

    def test_demarrer_montre_memoire_commune(self):
        out = io.StringIO()
        self.assertEqual(tsc_ia.demarrer("mods", out), 0)
        self.assertIn("UK", out.getvalue())
        self.assertIn("Avant d'agir", out.getvalue())

    def test_agent_inconnu(self):
        self.assertEqual(tsc_ia.demarrer("inconnu", io.StringIO()), 2)


class TestEcriture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mem = os.path.join(self.tmp, "m.jsonl")

    def test_noter_numerote_et_refuse_sans_preuve(self):
        e1 = tsc_ia.noter("mods", "test", "a", "p", chemin=self.mem)
        e2 = tsc_ia.noter("mods", "test", "b", "p", chemin=self.mem)
        self.assertEqual((e1["id"], e2["id"]), ("m0001", "m0002"))
        with self.assertRaises(ValueError):
            tsc_ia.noter("mods", "test", "c", "", chemin=self.mem)

    def test_verifier_detecte_erreurs(self):
        with open(self.mem, "w") as f:
            f.write(json.dumps({"id": "m1", "date": "x", "agent": "zz", "type": "?", "statut": "ok", "preuve": ""}) + "\n")
        err, _ = tsc_ia.verifier(memoire_chemin=self.mem)
        texte = " ".join(err)
        for mot in ("agent inconnu", "type inconnu", "statut inconnu", "sans preuve", "date invalide"):
            self.assertIn(mot, texte)

    def test_fiche_sans_source_refusee(self):
        idx = {"fiches": [{"id": "x", "titre": "t", "domaine": "mods", "lieu": "depot", "fichier": "README.md",
                           "sources": [], "version": "1", "date_verif": "2026-11-03", "statut": "verifie"}]}
        p = os.path.join(self.tmp, "i.json")
        json.dump(idx, open(p, "w"))
        err, _ = tsc_ia.verifier(index_chemin=p)
        self.assertTrue(any("sans source" in e or "'sources' manquant" in e for e in err))

    def test_transfert_garde_fichiers(self):
        f = os.path.join(self.tmp, "a.dds")
        open(f, "wb").write(b"1234")
        c = tsc_ia.transfert("textures", "graphics", "route", [f], "planche", ["BC3"], dossier=self.tmp)
        t = json.load(open(c))
        self.assertEqual(t["fichiers"][0]["taille"], 4)
        self.assertEqual(t["hypotheses"], ["BC3"])


if __name__ == "__main__":
    unittest.main()
