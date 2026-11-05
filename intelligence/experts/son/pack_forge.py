"""Pack Forge : la liste de TOUS les sons de travail, rangés par rôle, pour Sound Forge.

Écrit forge_pack.json à la racine du dossier TSC_Sound_Forge du Bureau. Dans Forge, le bouton
« Importer tous mes sons » + le choix de ce dossier importent chaque son avec son rôle, son régime,
le passage à garder et une note. Les fichiers ne sont ni copiés ni modifiés : le pack ne fait que les nommer.

Règles du choix (04/11/2026, Mendy : « vrais sons, pas de composition ») :
- le ralenti actif est le vrai ralenti enregistré (164L, 500 tr/min mesurés) ;
- les autres ralentis réels sont des candidats (rôle Référence : on les essaie en changeant leur rôle) ;
- les couches en charge viennent des boucles réparées du mod V8 de Mendy, seules couches par régime existantes ;
- les vidéos complètes sont en Référence, à découper avec « Extraire le passage ».
Usage : python3 pack_forge.py <dossier TSC_Sound_Forge> [sortie.json]
"""
import json
import os
import re
import sys

SEGMENTS = {  # segments_reels : rôle, régime, note (étiquettes mesurées, à confirmer à l'écoute)
    "01": ("ralenti", 500, "vrai ralenti 164L, allumage mesuré 33,3 Hz = 500 tr/min"),
    "02": ("coup_gaz", 0, "3 vrais coups de gaz à l'arrêt (164L)"),
    "03": ("reference", 0, "candidat ralenti (R580 A) : mets le rôle Ralenti pour l'essayer"),
    "04": ("reference", 0, "candidat ralenti (R580 B)"),
    "05": ("coup_gaz", 0, "vraie montée en régime R580"),
    "06": ("reference", 0, "régime haut stable R580 : extrais un passage stable pour une couche Charge"),
    "07": ("reference", 0, "retour au ralenti R580 (lever de pied)"),
    "08": ("claquement", 0, "claquements R580 (frein moteur ?)"),
    "09": ("reference", 0, "roulage en charge stable R620 : extrais un passage pour une couche Charge"),
    "10": ("reference", 0, "montée en charge R620"),
    "11": ("reference", 0, "charge forte R620"),
    "12": ("autre", 0, "à identifier à l'écoute (souffle ? frein moteur ?)"),
}

V8_EFFETS = {
    "air_compressor": "air_purge", "airbrake_1": "frein_air", "airbrake_2": "frein_air",
    "frein_moteur": "frein_moteur", "frein_moteur_fin": "frein_moteur", "start_op": "demarrage", "stop_op": "arret",
    "turbo": "turbo", "valve": "clapet_on",
}
NG = {"brake": "frein_air", "brake1": "frein_air", "brake2": "frein_air", "hb_off": "frein_parc", "hb_on": "frein_parc",
      "liftaxle": "suspension", "low_air": "air_purge"}
MAN = {"air_brake_0": "frein_air", "air_brake_1": "frein_air", "brake_whistle": "frein_air",
       "clunk": "boite_air", "clunk_off": "boite_air"}


def entree(chemin, role, rpm=0, note="", nom=None, boucle=None, source=""):
    e = {"fichier": chemin.replace(os.sep, "/"), "role": role}
    if rpm:
        e["rpm"] = rpm
    if note:
        e["note"] = note
    if nom:
        e["nom"] = nom
    if boucle is not None:
        e["boucle"] = boucle
    if source:
        e["source"] = source
    return e


def wavs(racine, sous):
    d = os.path.join(racine, sous)
    return sorted(f for f in os.listdir(d) if f.lower().endswith((".wav", ".flac"))) if os.path.isdir(d) else []


CABINE = re.compile(r"blinker|wiper|window|stick|horn|light|warning|richting|alarm|reverse|keys|lift_switch|sw_down|"
                    r"trailer_cables|low_air_warn|r.ckfahr", re.I)


def mes_sons(racine):
    """Chemins des sons de Mes_sons : INDEX.txt (liste complete faite sur le PC) sinon le disque."""
    idx = os.path.join(racine, "Mes_sons", "INDEX.txt")
    vus = []
    if os.path.isfile(idx):
        for l in open(idx, encoding="utf-8-sig"):
            c = [x.strip() for x in l.split("|")]
            if len(c) >= 2 and not c[0].startswith("#") and re.search(r"\.(wav|ogg|mp3|flac|m4a)$", c[1], re.I):
                vus.append("Mes_sons/%s/%s" % (c[0], c[1]))
    base = os.path.join(racine, "Mes_sons")
    if os.path.isdir(base):
        for d in sorted(os.listdir(base)):
            for f in wavs(racine, "Mes_sons/" + d):
                if "Mes_sons/%s/%s" % (d, f) not in vus:
                    vus.append("Mes_sons/%s/%s" % (d, f))
    return vus


def classer(dossier, f):
    """(role, regime, note) d'un son de Mes_sons. Un seul moteur joue dans le simulateur : le V8 de Mendy
    (boucles reparees). Les couches des autres moteurs sont en Reference, avec leur regime : on les essaie
    en changeant leur role."""
    b = f.rsplit(".", 1)[0]
    m = re.search(r"(\d{3,4})", b)
    rpm = int(m.group(1)) if m and 400 <= int(m.group(1)) <= 2600 else 0
    bl = b.lower()
    if dossier == "boucles_reparees":
        if b.startswith("c_") and rpm > 500:
            return "charge", rpm, "couche moteur (ton mod V8 v2, boucle reparee)"
        if b.startswith("t_"):
            return "turbo", 0, "turbo (ton mod V8 v2)"
        if b.startswith("f_"):
            return "frein_moteur", 0, "frein moteur en boucle (ton mod V8 v2)"
        return "autre", rpm, "boucle reparee (echappement par regime ou variante) : role a choisir"
    if dossier == "Apercus_v2":
        return "autre", 0, "ancien apercu"
    if dossier == "Telechargements":
        return "reference", 0, "son telecharge, a decouper si utile"
    if dossier in ("Klaxons", "Alertes_et_commodos") or CABINE.search(bl):
        if "parking_brake" in bl:
            return "frein_parc", 0, "frein de parc (" + dossier + ")"
        return "autre", 0, "son de cabine ou klaxon (hors moteur)"
    if dossier == "Scania_V8_open_pipe_v2" and b in V8_EFFETS:
        return V8_EFFETS[b], 0, "ton mod V8 v2"
    if dossier == "Scania_NG_effets" and b in NG:
        return NG[b], 0, "effet Scania NG"
    if dossier == "MAN_TGX_2020" and b in MAN:
        return MAN[b], 0, "effet MAN TGX 2020"
    quoi = {"Scania_V8_open_pipe_v2": "ton mod V8 v2", "Scania_R770_clapet": "mod Scania R770 clapet",
            "MAN_TGX_2020": "MAN TGX 2020", "Scania_NG_effets": "Scania NG"}.get(dossier, dossier)
    if "claquant" in bl:
        return "claquement", 0, "claquement (" + quoi + ")"
    if re.search(r"(^|_)gear|air_gear|clunk", bl):
        return "boite_air", 0, "passage de rapport (" + quoi + ")"
    if "parking_brake" in bl or bl.startswith(("hb_", "int_hb")):
        return "frein_parc", 0, "frein de parc (" + quoi + ")"
    if "retarder" in bl or "exhaust brake" in bl or "eb shift" in bl or bl.endswith("eb"):
        return "frein_moteur", 0, "frein moteur / ralentisseur (" + quoi + ")"
    if "valve" in bl:
        return "clapet_on", 0, "ouverture du clapet (" + quoi + ")"
    if "souffle" in bl or "bov" in bl:
        return "autre", rpm, "souffle de turbo (" + quoi + ")"
    if dossier == "Scania_V8_open_pipe_v2":
        return "autre", rpm, "version brute du mod V8 v2 (la boucle reparee est dans boucles_reparees)"
    return "reference", rpm, "couche ou son moteur (" + quoi + ")" + (" a %d tr/min" % rpm if rpm else "") + " : change son role pour l'essayer"


def boucles_ia_son(cat):
    import csv
    out = []
    for x in csv.DictReader(open(cat, encoding="utf-8-sig"), delimiter=";"):
        note = ("boucle coupée par l'IA son dans %s (%s-%s s), coupe seule · régime mesuré %s tr/min (à confirmer) · "
                "raccord %s dB · réalisme %s · état proposé : %s") % (x["video"], x["debut_s"], x["fin_s"], x["regime_mesure_trmin"],
                                                                   x["saut_raccord_db"], x["realisme"], x["etat_propose"])
        out.append(entree("expert_son/boucles_ia_son/" + x["fichier"], "reference", int(x["regime_mesure_trmin"]), note,
                          nom="IA son · " + x["fichier"][:-4], boucle=True, source="vidéo de référence, passage réel"))
    return out


def construire(racine):
    S = []
    seg = "expert_son/segments_reels"
    for f in wavs(racine, seg):
        r, rpm, note = SEGMENTS.get(f[:2], ("reference", 0, ""))
        S.append(entree(seg + "/" + f, r, rpm, note + " · non retouché", boucle=r == "ralenti",
                        source="vidéo de référence, passage réel"))
    for f in wavs(racine, "expert_son/apercu_v8"):
        note = "boucle de vrai ralenti (cycles entiers)" + (" · raccord à revoir : saute de 2,3 dB" if "_B_" in f else "")
        S.append(entree("expert_son/apercu_v8/" + f, "reference", 0, note + " · candidat ralenti"))
    for f in wavs(racine, "expert_son/videos_completes"):
        S.append(entree("expert_son/videos_completes/" + f, "reference", 0, "son complet de la vidéo : choisis un passage puis « Extraire le passage »"))
    cat = os.path.join(racine, "expert_son", "boucles_ia_son", "catalogue.csv")
    if os.path.isfile(cat):  # boucles coupées dans les vidéos par la TSC-IA Son (juge PANNs), sans aucun traitement
        S += boucles_ia_son(cat)
    for chem in mes_sons(racine):
        dossier, f = chem.split("/")[1], chem.split("/")[-1]
        r, rpm, note = classer(dossier, f)
        S.append(entree(chem, r, rpm, note, boucle=True if r in ("charge", "turbo") else None))
    return {"format": "tsc_forge_pack", "version": 1, "nom": "Tous mes sons TSC", "dossier": "TSC_Sound_Forge",
            "avertissement": "rôles proposés d'après les noms et les mesures : c'est l'écoute de Mendy qui tranche",
            "sons": S}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 1
    p = construire(argv[0])
    sortie = argv[1] if len(argv) > 1 else os.path.join(argv[0], "forge_pack.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    roles = {}
    for e in p["sons"]:
        roles[e["role"]] = roles.get(e["role"], 0) + 1
    print("%d sons -> %s" % (len(p["sons"]), sortie))
    print(", ".join("%s %d" % kv for kv in sorted(roles.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
