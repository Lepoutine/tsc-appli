#!/usr/bin/env python3
"""TSC Intelligence : memoire commune, recherche et verification des 10 experts.

Python 3 seul, sans dependance. Ne modifie jamais un fichier du jeu, d'un mod ou de l'appli.

  python3 intelligence/outils/tsc_ia.py verifier [--projet /mnt/project-files] [--code DOSSIER]
  python3 intelligence/outils/tsc_ia.py demarrer <agent>      # etat a relire avant d'agir
  python3 intelligence/outils/tsc_ia.py chercher <mots...>    # fiches + memoire
  python3 intelligence/outils/tsc_ia.py noter --agent mods --type correction --resume "..." --preuve "..."
  python3 intelligence/outils/tsc_ia.py transfert --de textures --vers graphics --objet "..." --fichiers a b --preuve "..."
"""
import argparse
import datetime
import json
import os
import sys
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(ICI)            # intelligence/
DEPOT = os.path.dirname(BASE)          # racine du depot
AGENTS = os.path.join(BASE, "agents", "agents.json")
INDEX = os.path.join(BASE, "connaissances", "index.json")
MEMOIRE = os.path.join(BASE, "memoire", "entrees.jsonl")
TRANSFERTS = os.path.join(BASE, "transferts")
EVAL = os.path.join(BASE, "evaluation", "taches.json")

TYPES = {"decision", "parametre", "probleme", "correction", "test", "limite", "amelioration", "projet"}
STATUTS_MEM = {"valide", "en_attente", "refuse", "obsolete"}
STATUTS_FICHE = {"verifie", "verifie_partiel", "a_verifier", "concu"}
LIEUX = {"depot", "code", "projet", "pc", "memoire"}


def lire_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def lire_memoire(chemin=MEMOIRE):
    entrees = []
    if not os.path.exists(chemin):
        return entrees
    with open(chemin, encoding="utf-8") as f:
        for n, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if ligne:
                e = json.loads(ligne)
                e["_ligne"] = n
                entrees.append(e)
    return entrees


def fiches(index_chemin=INDEX, depot=DEPOT):
    """Fiches de la base commune + celles des bases jointes (ex. Sound Forge), sans les recopier."""
    idx = lire_json(index_chemin)
    tout = []
    for f in idx.get("fiches", []):
        tout.append(dict(f, _base="intelligence"))
    for b in idx.get("bases_jointes", []):
        chemin = os.path.join(depot, b["chemin"])
        if not os.path.exists(chemin):
            continue
        jointe = lire_json(chemin)
        racine = os.path.dirname(b["chemin"])
        for f in jointe.get("fiches", []):
            g = dict(f)
            g.setdefault("lieu", "depot")
            g["fichier"] = racine + "/" + f["fichier"]
            g.setdefault("version", b.get("version", ""))
            g.setdefault("date_verif", b.get("date_verif", jointe.get("maj", "")))
            g["_base"] = b["chemin"]
            tout.append(g)
    return tout


def sans_accents(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def chemin_existe(lieu, chemin, depot, projet, code):
    """True / False si on peut verifier, None si le lieu n'est pas accessible d'ici."""
    if lieu == "depot":
        return os.path.exists(os.path.join(depot, chemin))
    if lieu == "projet" and projet:
        return os.path.exists(os.path.join(projet, chemin))
    if lieu == "code" and code:
        return os.path.exists(os.path.join(code, chemin))
    return None


def verifier(depot=DEPOT, projet=None, code=None, agents_chemin=AGENTS, index_chemin=INDEX, memoire_chemin=MEMOIRE):
    """Retourne (erreurs, avertissements). Une erreur bloque : base incomplete ou incoherente."""
    err, avert = [], []
    ag = lire_json(agents_chemin)
    toutes = fiches(index_chemin, depot)
    ids_fiches = {}
    for f in toutes:
        q = f.get("id", "?")
        if q in ids_fiches:
            err.append("fiche %s en double (%s et %s)" % (q, ids_fiches[q], f["_base"]))
        ids_fiches[q] = f["_base"]
        if f["_base"] == "intelligence":
            for champ in ("titre", "domaine", "lieu", "fichier", "sources", "version", "date_verif", "statut"):
                if not f.get(champ):
                    err.append("fiche %s : champ '%s' manquant" % (q, champ))
        if f.get("statut") not in STATUTS_FICHE:
            err.append("fiche %s : statut inconnu '%s'" % (q, f.get("statut")))
        if f.get("statut") in ("verifie", "verifie_partiel") and not f.get("sources"):
            msg = "fiche %s : marquee verifiee sans source" % q
            # base jointe (ex. Sound Forge) : signale sans bloquer, a corriger par son fil
            (err if f["_base"] == "intelligence" else avert).append(msg)
        if f.get("lieu") not in LIEUX:
            err.append("fiche %s : lieu inconnu '%s'" % (q, f.get("lieu")))
        ok = chemin_existe(f.get("lieu"), f.get("fichier", ""), depot, projet, code)
        if ok is False:
            err.append("fiche %s : fichier introuvable %s:%s" % (q, f.get("lieu"), f.get("fichier")))

    ids_agents = set()
    for a in ag["agents"]:
        ids_agents.add(a["id"])
        for champ in ("nom", "specialite", "niveau", "preuve_niveau", "outils", "manque", "demande_avant"):
            if a.get(champ) in (None, "", []):
                err.append("agent %s : champ '%s' manquant" % (a["id"], champ))
        if not isinstance(a.get("niveau"), int) or not 0 <= a["niveau"] <= 6:
            err.append("agent %s : niveau hors echelle 0-6" % a["id"])
        for k in a.get("connaissances", []):
            if k not in ids_fiches:
                err.append("agent %s : fiche '%s' inconnue" % (a["id"], k))
        if not a.get("connaissances"):
            avert.append("agent %s : aucune fiche de connaissances" % a["id"])
        for o in a.get("outils", []):
            if o.get("lieu") not in LIEUX:
                err.append("agent %s : outil '%s' lieu inconnu" % (a["id"], o.get("nom")))
                continue
            ok = chemin_existe(o["lieu"], o["chemin"], depot, projet, code)
            if ok is False:
                err.append("agent %s : outil introuvable %s:%s" % (a["id"], o["lieu"], o["chemin"]))
            elif ok is None and o["lieu"] in ("pc", "code", "projet"):
                avert.append("agent %s : %s:%s non verifiable d'ici" % (a["id"], o["lieu"], o["chemin"]))

    vus = set()
    for e in lire_memoire(memoire_chemin):
        q = e.get("id", "ligne %d" % e["_ligne"])
        if q in vus:
            err.append("memoire %s en double" % q)
        vus.add(q)
        if e.get("agent") != "commun" and e.get("agent") not in ids_agents:
            err.append("memoire %s : agent inconnu '%s'" % (q, e.get("agent")))
        if e.get("type") not in TYPES:
            err.append("memoire %s : type inconnu '%s'" % (q, e.get("type")))
        if e.get("statut") not in STATUTS_MEM:
            err.append("memoire %s : statut inconnu '%s'" % (q, e.get("statut")))
        if not e.get("preuve"):
            err.append("memoire %s : sans preuve" % q)
        try:
            datetime.date.fromisoformat(e.get("date", ""))
        except ValueError:
            err.append("memoire %s : date invalide" % q)
    return err, avert


def demarrer(agent_id, sortie=sys.stdout):
    ag = {a["id"]: a for a in lire_json(AGENTS)["agents"]}
    if agent_id not in ag:
        sortie.write("Agent inconnu. Choix : %s\n" % ", ".join(sorted(ag)))
        return 2
    a = ag[agent_id]
    p = lambda t="": sortie.write(t + "\n")
    p("== %s (niveau %d/6) ==" % (a["nom"], a["niveau"]))
    p("Preuve du niveau : " + a["preuve_niveau"])
    p("Avant d'agir : " + a["demande_avant"])
    p("\nOutils existants :")
    for o in a["outils"]:
        p("  - %s  [%s] %s" % (o["nom"], o["lieu"], o["chemin"]))
    p("\nConnaissances :")
    par_id = {f["id"]: f for f in fiches()}
    for k in a.get("connaissances", []):
        f = par_id.get(k)
        if f:
            p("  - %s [%s, %s, verifie le %s] %s" % (f["titre"], f["statut"], f.get("version", ""), f.get("date_verif", ""), f["fichier"]))
    mem = [e for e in lire_memoire() if e["agent"] in (agent_id, "commun") and e["statut"] in ("valide", "en_attente")]
    p("\nMemoire (commune + %s), %d entrees :" % (agent_id, len(mem)))
    for e in sorted(mem, key=lambda e: e["date"]):
        attente = " (EN ATTENTE)" if e["statut"] == "en_attente" else ""
        p("  %s %s [%s/%s]%s %s" % (e["id"], e["date"], e["agent"], e["type"], attente, e["resume"]))
    p("\nLacunes connues :")
    for m in a["manque"]:
        p("  - " + m)
    return 0


def chercher(mots, sortie=sys.stdout):
    termes = [sans_accents(m) for m in mots]
    res = []
    for f in fiches():
        texte = sans_accents(" ".join([f.get("titre", ""), f.get("domaine", ""), " ".join(f.get("mots_cles", []))]))
        s = sum(texte.count(t) for t in termes)
        if s:
            res.append((s, "fiche", f["id"], "%s [%s] %s" % (f["titre"], f["statut"], f["fichier"])))
    for e in lire_memoire():
        if e["statut"] in ("refuse", "obsolete"):
            continue
        texte = sans_accents(e["resume"] + " " + e["type"] + " " + e["agent"])
        s = sum(texte.count(t) for t in termes)
        if s:
            res.append((s, "memoire", e["id"], "[%s/%s] %s" % (e["agent"], e["type"], e["resume"])))
    res.sort(key=lambda r: -r[0])
    for _, genre, q, texte in res:
        sortie.write("%-7s %-22s %s\n" % (genre, q, texte))
    if not res:
        sortie.write("Rien trouve. Chercher alors dans les fichiers autorises, puis la doc officielle, avant de demander a Mendy.\n")
    return res


def noter(agent, type_, resume, preuve, fichiers=None, version="-", statut="valide", chemin=MEMOIRE, date=None):
    mem = lire_memoire(chemin)
    n = max([int(e["id"][1:]) for e in mem if e.get("id", "").startswith("m")] + [0]) + 1
    e = {"id": "m%04d" % n, "date": date or datetime.date.today().isoformat(), "agent": agent, "type": type_,
         "resume": resume, "preuve": preuve, "fichiers": fichiers or [], "version": version, "statut": statut}
    if type_ not in TYPES or statut not in STATUTS_MEM or not preuve:
        raise ValueError("type, statut ou preuve invalide")
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e


def transfert(de, vers, objet, fichiers, preuve, hypotheses=None, dossier=TRANSFERTS):
    """Fiche de passage entre experts : garde fichiers, versions (taille + date), hypotheses et preuves."""
    os.makedirs(dossier, exist_ok=True)
    maintenant = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    t = {"date": maintenant, "de": de, "vers": vers, "objet": objet, "hypotheses": hypotheses or [],
         "preuve": preuve, "fichiers": [], "statut": "a_reprendre"}
    for fi in fichiers:
        info = {"chemin": fi}
        if os.path.exists(fi):
            st = os.stat(fi)
            info.update(taille=st.st_size, modifie=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"))
        t["fichiers"].append(info)
    chemin = os.path.join(dossier, "%s_%s_vers_%s.json" % (maintenant, de, vers))
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=1)
    return chemin


def main(argv=None):
    ap = argparse.ArgumentParser(description="TSC Intelligence")
    sp = ap.add_subparsers(dest="cmd", required=True)
    v = sp.add_parser("verifier")
    v.add_argument("--projet")
    v.add_argument("--code")
    d = sp.add_parser("demarrer")
    d.add_argument("agent")
    c = sp.add_parser("chercher")
    c.add_argument("mots", nargs="+")
    n = sp.add_parser("noter")
    n.add_argument("--agent", required=True)
    n.add_argument("--type", required=True, choices=sorted(TYPES))
    n.add_argument("--resume", required=True)
    n.add_argument("--preuve", required=True)
    n.add_argument("--fichiers", nargs="*", default=[])
    n.add_argument("--version", default="-")
    n.add_argument("--statut", default="valide", choices=sorted(STATUTS_MEM))
    t = sp.add_parser("transfert")
    t.add_argument("--de", required=True)
    t.add_argument("--vers", required=True)
    t.add_argument("--objet", required=True)
    t.add_argument("--fichiers", nargs="*", default=[])
    t.add_argument("--preuve", required=True)
    t.add_argument("--hypotheses", nargs="*", default=[])
    a = ap.parse_args(argv)

    if a.cmd == "verifier":
        err, avert = verifier(projet=a.projet, code=a.code)
        for x in avert:
            print("attention : " + x)
        for x in err:
            print("ERREUR : " + x)
        nb_f, nb_m = len(fiches()), len(lire_memoire())
        print("%d fiches, %d entrees de memoire, %d erreurs" % (nb_f, nb_m, len(err)))
        return 1 if err else 0
    if a.cmd == "demarrer":
        return demarrer(a.agent)
    if a.cmd == "chercher":
        chercher(a.mots)
        return 0
    if a.cmd == "noter":
        ids = {x["id"] for x in lire_json(AGENTS)["agents"]} | {"commun"}
        if a.agent not in ids:
            print("agent inconnu")
            return 2
        print(json.dumps(noter(a.agent, a.type, a.resume, a.preuve, a.fichiers, a.version, a.statut), ensure_ascii=False))
        return 0
    if a.cmd == "transfert":
        print(transfert(a.de, a.vers, a.objet, a.fichiers, a.preuve, a.hypotheses))
        return 0


if __name__ == "__main__":
    sys.exit(main())
