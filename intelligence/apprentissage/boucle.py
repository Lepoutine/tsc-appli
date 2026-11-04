"""Boucle d'apprentissage commune aux IA TSC (règles : regles.json).

Une IA fournit deux fonctions : entrainer(exemples) -> modele et juger(modele, exemples) -> {critere: score}.
La boucle garde le juge fixe, n'adopte que si chaque critère fait au moins aussi bien, sauvegarde chaque
version et tient le journal. Elle sert à l'atelier Blender (Spartan Studio) comme à toute autre IA TSC ;
Sound Forge en a la même règle en JavaScript (sound_forge/ui/forge_ia.js).
"""
import datetime
import json
import os
import zlib

ICI = os.path.dirname(os.path.abspath(__file__))
REGLES = json.load(open(os.path.join(ICI, "regles.json"), encoding="utf-8"))
P = REGLES["parametres"]


def est_juge(cle):
    return zlib.crc32(str(cle).encode("utf-8")) % P["juge_1_sur"] == 0


class Boucle:
    def __init__(self, dossier, entrainer, juger):
        self.dossier, self.entrainer, self.juger = dossier, entrainer, juger
        os.makedirs(dossier, exist_ok=True)
        self.f = os.path.join(dossier, "etat.json")
        self.etat = json.load(open(self.f, encoding="utf-8")) if os.path.isfile(self.f) else {"versions": [], "journal": []}

    def _note(self, ok, raison):
        self.etat["journal"].append({"date": datetime.datetime.now().isoformat(timespec="minutes"), "ok": ok, "raison": raison})
        self.etat["journal"] = self.etat["journal"][-200:]
        with open(self.f, "w", encoding="utf-8") as f:
            json.dump(self.etat, f, ensure_ascii=False, indent=1)
        return {"adoptee": ok, "raison": raison}

    def modele(self, n=None):
        v = self.etat["versions"]
        if not v:
            return None
        n = n or v[-1]["n"]
        return json.load(open(os.path.join(self.dossier, "version_%03d.json" % n), encoding="utf-8"))

    def apprend(self, exemples):
        appr = [e for e in exemples if not est_juge(e["cle"])]
        juges = [e for e in exemples if est_juge(e["cle"])]
        if len(appr) < P["exemples_minimum"]:
            return self._note(False, "pas assez d'exemples (%d / %d)" % (len(appr), P["exemples_minimum"]))
        if len(juges) < P["juge_minimum"]:
            return self._note(False, "juge trop petit (%d / %d)" % (len(juges), P["juge_minimum"]))
        der = self.etat["versions"][-1] if self.etat["versions"] else None
        if der and der["appris"] == len(appr) and der["juges"] == len(juges):
            return {"adoptee": False, "raison": "rien de nouveau depuis la version %d" % der["n"]}
        nouveau = self.entrainer(appr)
        s = self.juger(nouveau, juges)
        if der:
            s_old = self.juger(self.modele(der["n"]), juges)  # l'ancienne rejugée sur le même juge
            pires = [k for k in s if k in s_old and s[k] < s_old[k]]
            if pires:
                return self._note(False, "version refusée : moins bonne sur %s" % ", ".join(pires))
        n = (der["n"] if der else 0) + 1
        with open(os.path.join(self.dossier, "version_%03d.json" % n), "w", encoding="utf-8") as f:
            json.dump(nouveau, f, ensure_ascii=False)
        self.etat["versions"].append({"n": n, "appris": len(appr), "juges": len(juges), "scores": s})
        self.etat["versions"] = self.etat["versions"][-P["versions_gardees"]:]
        return self._note(True, "version %d adoptée : %s" % (n, ", ".join("%s %.0f %%" % (k, 100 * v) for k, v in s.items())))

    def retour(self):
        if len(self.etat["versions"]) < 2:
            return False
        v = self.etat["versions"].pop()
        self._note(True, "retour arrière : version %d retirée" % v["n"])
        return True
