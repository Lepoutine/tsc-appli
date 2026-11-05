#!/usr/bin/env python3
"""Audit TSC Virtuoso : état réel de chaque IA et file des lacunes à combler (directive du 04/11/2026, §16).

Lit agents.json, la base de connaissances, la mémoire, le dernier passage du banc et la dernière certification.
Écrit :
- lacunes.json : la file de recherche, par ordre de priorité. Chaque lacune dit quoi chercher et pourquoi
  (« manque » déclaré, fiche non vérifiée ou trop vieille, épreuve ratée, critère de la grille non mesuré).
  C'est le point 1 de la recherche autonome : identifier précisément la lacune avant de chercher ;
- BILAN_VIRTUOSO.md : le bilan demandé par Mendy (opérationnel ou non, connaissances, outils, tests, limites).
Rien n'est inventé : ce qui n'est pas mesuré est écrit « non mesuré ».

  python3 intelligence/evaluation/audit.py
"""
import datetime
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(ICI)
sys.path.insert(0, os.path.join(BASE, "outils"))
import tsc_ia  # noqa: E402
import banc  # noqa: E402

VIEILLE_JOURS = 90


def dernier_passage(histo=banc.HISTO):
    if not os.path.isfile(histo):
        return []
    L = [json.loads(l) for l in open(histo, encoding="utf-8") if l.strip()]
    if not L:
        return []
    d = L[-1]["date"]
    return [e for e in L if e["date"] == d]


def taux(histo=banc.HISTO, n=10):
    """Taux de réussite de chaque épreuve sur ses n derniers passages (stabilité de la compétence)."""
    par = {}
    if os.path.isfile(histo):
        for l in open(histo, encoding="utf-8"):
            if l.strip():
                e = json.loads(l)
                par.setdefault(e["epreuve"], []).append(e["ok"])
    return {k: (sum(v[-n:]), len(v[-n:])) for k, v in par.items()}


def dernieres_certifs(f=banc.CERTIF):
    out = {}
    if os.path.isfile(f):
        for l in open(f, encoding="utf-8"):
            if l.strip():
                e = json.loads(l)
                out.setdefault(e["agent"], []).append(e)
    return out


def auditer():
    ag = tsc_ia.lire_json(tsc_ia.AGENTS)["agents"]
    fiches = {f["id"]: f for f in tsc_ia.fiches()}
    mem = tsc_ia.lire_memoire()
    passage = dernier_passage()
    tx = taux()
    certifs = dernieres_certifs()
    auj = datetime.date.today()
    lacunes, lignes = [], []
    for a in ag:
        i = a["id"]
        fk = [fiches[k] for k in a.get("connaissances", []) if k in fiches]
        stat = {}
        for f in fk:
            stat[f.get("statut")] = stat.get(f.get("statut"), 0) + 1
        vieilles = []
        for f in fk:
            try:
                if (auj - datetime.date.fromisoformat(f.get("date_verif", ""))).days > VIEILLE_JOURS:
                    vieilles.append(f["id"])
            except ValueError:
                vieilles.append(f["id"])
        ep = [e for e in passage if e["agent"] == i]
        pc = [p for p in banc.PC if p[0] == i]
        c = certifs.get(i, [])
        m = [e for e in mem if e.get("agent") == i]
        outils_depot = [o for o in a.get("outils", []) if o.get("lieu") == "depot"]
        couv = c[-1]["grille_mesuree_pct"] if c else 0
        if not ep:
            etat = "non mesuré d'ici"
        elif couv >= 80 and not pc and c[-1]["note_sur_100"] >= 80:
            etat = "opérationnel (mesuré)"
        else:
            etat = "partiel : %d %% de la grille mesurée%s" % (couv, ", épreuves PC à passer" if pc else "")
        lignes.append({"agent": i, "nom": a["nom"], "etat": etat, "niveau_declare": a["niveau"],
                       "fiches": len(fk), "fiches_par_statut": stat, "fiches_vieilles": vieilles,
                       "outils": len(a.get("outils", [])), "outils_depot": len(outils_depot), "memoire": len(m),
                       "apprentissage": bool(a.get("apprentissage")),
                       "epreuves": ["%s %s (%d/%d sur les derniers passages)" % ("OK" if e["ok"] else "ÉCHEC", e["epreuve"], *tx.get(e["epreuve"], (0, 0))) for e in ep],
                       "epreuves_pc": [p[1] for p in pc],
                       "certification": c[-1] if c else None, "examen_entree": c[0] if c else None,
                       "manque": a.get("manque", [])})
        # ---- lacunes
        for q in a.get("manque", []):
            lacunes.append({"agent": i, "priorite": 2, "type": "outil ou capacité manquante", "quoi": q})
        for f in fk:
            if f.get("statut") in ("verifie_partiel", "a_verifier", "concu"):
                lacunes.append({"agent": i, "priorite": 2, "type": "fiche à vérifier", "quoi": "%s (%s) : %s" % (f["id"], f["statut"], f.get("titre", ""))})
        for v in vieilles:
            lacunes.append({"agent": i, "priorite": 3, "type": "fiche à revérifier (plus de %d jours)" % VIEILLE_JOURS, "quoi": v})
        if len(fk) < 3:
            lacunes.append({"agent": i, "priorite": 1, "type": "base de connaissances trop mince", "quoi": "%d fiche(s) : compléter avec la documentation officielle et les sources libres du domaine" % len(fk)})
        for e in ep:
            if not e["ok"]:
                lacunes.append({"agent": i, "priorite": 1, "type": "épreuve ratée", "quoi": "%s : obtenu %s, attendu %s" % (e["epreuve"], e["valeur"], e["attendu"])})
        if c:
            for k in c[-1].get("non_mesure", []):
                lacunes.append({"agent": i, "priorite": 3, "type": "critère de certification non mesuré", "quoi": banc.NOMS_GRILLE[k]})
        elif not ep:
            lacunes.append({"agent": i, "priorite": 1, "type": "aucun examen", "quoi": "examen d'entrée à construire (épreuves PC : %s)" % ("; ".join(p[1] for p in pc) or "à définir")})
    lacunes.sort(key=lambda l: (l["priorite"], l["agent"]))
    return lignes, lacunes


def bilan_md(lignes, lacunes):
    L = ["# Bilan TSC Virtuoso", "", "Généré par `intelligence/evaluation/audit.py` le %s. Tout chiffre vient du banc d'évaluation ou des fichiers ; ce qui n'est pas mesuré est écrit tel quel." % datetime.date.today().isoformat(), "",
         "Grille de certification (objectifs, pas niveaux atteints) : " + ", ".join("%s %d %%" % (banc.NOMS_GRILLE[c], w) for c, w in banc.GRILLE.items()) + ".", "",
         "| IA | État | Note (grille mesurée) | Examen d'entrée | Fiches | Outils | Mémoire | Apprend |", "|---|---|---|---|---|---|---|---|"]
    for l in lignes:
        c, e = l["certification"], l["examen_entree"]
        L.append("| %s | %s | %s | %s | %d %s | %d | %d | %s |" % (
            l["nom"], l["etat"], "%.0f/100 (%d %%)" % (c["note_sur_100"], c["grille_mesuree_pct"]) if c else "non mesuré",
            "%.0f/100" % e["note_sur_100"] if e else "—", l["fiches"], "(" + ", ".join("%s %d" % kv for kv in sorted(l["fiches_par_statut"].items())) + ")" if l["fiches_par_statut"] else "",
            l["outils"], l["memoire"], "oui" if l["apprentissage"] else "non"))
    L += ["", "## Épreuves par IA", ""]
    for l in lignes:
        L.append("**%s** : %s" % (l["nom"], "; ".join(l["epreuves"]) or "aucune épreuve automatique d'ici"))
        if l["epreuves_pc"]:
            L.append("  Épreuves à passer sur le PC : %s" % "; ".join(l["epreuves_pc"]))
        L.append("")
    L += ["## Lacunes, par priorité (%d)" % len(lacunes), ""]
    for q in lacunes:
        L.append("- P%d · %s · %s : %s" % (q["priorite"], q["agent"], q["type"], q["quoi"]))
    return "\n".join(L) + "\n"


def main():
    lignes, lacunes = auditer()
    with open(os.path.join(ICI, "lacunes.json"), "w", encoding="utf-8") as f:
        json.dump({"genere": datetime.datetime.now().isoformat(timespec="minutes"), "lacunes": lacunes}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ICI, "audit.json"), "w", encoding="utf-8") as f:
        json.dump(lignes, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ICI, "BILAN_VIRTUOSO.md"), "w", encoding="utf-8") as f:
        f.write(bilan_md(lignes, lacunes))
    for l in lignes:
        print("%-12s %-24s fiches %2d  épreuves %d  %s" % (l["agent"], l["etat"], l["fiches"], len(l["epreuves"]),
                                                        ("note %.0f/100" % l["certification"]["note_sur_100"]) if l["certification"] else "pas de note"))
    print("%d lacunes -> lacunes.json, BILAN_VIRTUOSO.md" % len(lacunes))


if __name__ == "__main__":
    main()
