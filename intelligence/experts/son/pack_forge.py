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
    br = "Mes_sons/boucles_reparees"
    for f in wavs(racine, br):
        b = f[:-4]
        m = re.search(r"(\d{3,4})", b)
        rpm = int(m.group(1)) if m else 0
        if b.startswith("c_") and rpm and rpm > 500:
            S.append(entree(br + "/" + f, "charge", rpm, "couche moteur (ton mod V8 v2, boucle réparée)", boucle=True))
        elif b.startswith("t_"):
            S.append(entree(br + "/" + f, "turbo", 0, "turbo (ton mod V8 v2)", boucle=True))
        elif b.startswith("f_"):
            S.append(entree(br + "/" + f, "frein_moteur", 0, "frein moteur en boucle (ton mod V8 v2)", boucle=True))
        else:
            S.append(entree(br + "/" + f, "autre", rpm, "boucle réparée (échappement par régime ou variante) : rôle à choisir"))
    v8 = "Mes_sons/Scania_V8_open_pipe_v2"
    for f in wavs(racine, v8):
        b = f[:-4]
        if b in V8_EFFETS:
            S.append(entree(v8 + "/" + f, V8_EFFETS[b], 0, "ton mod V8 v2"))
        elif b.startswith("claquant"):
            S.append(entree(v8 + "/" + f, "claquement", 0, "claquement (ton mod V8 v2)"))
        elif b.startswith("gear"):
            S.append(entree(v8 + "/" + f, "boite_air", 0, "passage de rapport (ton mod V8 v2)"))
        else:
            m = re.search(r"(\d{3,4})", b)
            S.append(entree(v8 + "/" + f, "autre", int(m.group(1)) if m else 0, "version brute du mod V8 v2 (la boucle réparée est dans boucles_reparees)"))
    for sous, table, quoi in (("Mes_sons/Scania_NG_effets", NG, "Scania NG"), ("Mes_sons/MAN_TGX_2020", MAN, "MAN TGX 2020")):
        for f in wavs(racine, sous):
            b = f[:-4]
            r = table.get(b) or ("boite_air" if b.startswith(("gear", "air_gear")) else "autre")
            S.append(entree(sous + "/" + f, r, 0, "effet " + quoi))
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
