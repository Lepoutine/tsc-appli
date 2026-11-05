#!/usr/bin/env python3
"""Expert Conduite : contrôler une journée de conduite contre le règlement (CE) 561/2006.

Référence : fiches reglement_561_2006 (art. 4, 6, 7, 8) et tachygraphe_165_2014 (les quatre activités).
Sert de règle de vérité pour le tachygraphe du Pilote de tête : le code du pilote (sur le PC) peut être comparé à
ce contrôleur sur les mêmes traces. Temps en minutes de JEU (ETS2 accélère le temps).

Une trace = liste de segments (activite, duree_min), dans l'ordre, activite parmi :
  conduite, travail (autre travail), dispo (disponibilité), repos (pause ou repos).

Contrôlé :
- art. 7 : après 4 h 30 de conduite, pause d'au moins 45 min, ou 15 min puis 30 min ; une pause de moins de 15 min
  ne compte pas ;
- art. 6(1) : conduite journalière (entre deux repos journaliers) au plus 9 h, 10 h tolérées (signalées comme
  prolongation : au plus deux fois par semaine, à suivre sur la semaine) ;
- art. 8(2) + art. 4(g) : dans les 24 h après la fin du repos précédent, un repos journalier complet : au moins
  11 h, ou 3 h puis 9 h, ou réduit au moins 9 h (compté).
Pas encore contrôlé (signalé, pas deviné) : semaine (56 h, 90 h sur deux semaines, art. 6(2)(3)), repos
hebdomadaire et ses compensations (art. 8(6)), équipage multiple, ferry/train (art. 9).
"""
import json
import sys

ACTIVITES = ("conduite", "travail", "dispo", "repos")
CONDUITE_MAX = 270          # art. 7 : 4 h 30
PAUSE_PLEINE, PAUSE_1, PAUSE_2 = 45, 15, 30
JOUR_NORMAL, JOUR_PROLONGE = 540, 600   # art. 6(1)
REPOS_NORMAL, REPOS_REDUIT, REPOS_PART1 = 660, 540, 180   # art. 4(g)
NON_CONTROLE = ["semaine 56 h / 90 h sur deux semaines (art. 6)", "repos hebdomadaire (art. 8(6))", "équipage multiple", "ferry / train (art. 9)"]


def controler(trace):
    """Rend {infractions: [{article, minute, detail}], prolongations, repos_reduits, non_controle}."""
    seg = []
    t = 0
    for act, d in trace:
        if act not in ACTIVITES or d < 0:
            raise ValueError("segment invalide : %r" % ((act, d),))
        if seg and seg[-1][0] == act:  # deux segments identiques collés = un seul
            seg[-1][2] += d
        else:
            seg.append([act, t, d])
        t += d
    inf, prolong, reduits = [], 0, 0

    # ---- art. 7 : pauses
    cumul, part1, signale = 0, False, False
    for act, deb, d in seg:
        if act == "conduite":
            if cumul + d > CONDUITE_MAX and not signale:  # une infraction par période sans pause valable
                inf.append({"article": "7", "minute": deb + CONDUITE_MAX - cumul,
                            "detail": "plus de 4 h 30 de conduite sans pause de 45 min (ou 15 + 30)"})
                signale = True
            cumul += d
        elif act == "repos":
            if d >= PAUSE_PLEINE or (part1 and d >= PAUSE_2):
                cumul, part1, signale = 0, False, False
            elif d >= PAUSE_1:
                part1 = True

    # ---- découpage en journées : un repos d'au moins 9 h termine la journée (le bloc de 3 h d'un repos fractionné, non)
    journees, debut, conduite, part3 = [], 0, 0, False
    for act, deb, d in seg:
        if act == "repos" and (d >= REPOS_REDUIT):
            complet = d >= REPOS_NORMAL or part3
            journees.append({"debut": debut, "fin_repos": deb + d, "conduite": conduite, "repos": d, "fractionne": part3 and d < REPOS_NORMAL, "reduit": not complet})
            debut, conduite, part3 = deb + d, 0, False
        else:
            if act == "conduite":
                conduite += d
            if act == "repos" and d >= REPOS_PART1:
                part3 = True
    fin_trace = t
    conduite_jour_cours = conduite
    for j in journees:
        if j["conduite"] > JOUR_PROLONGE:
            inf.append({"article": "6(1)", "minute": j["debut"], "detail": "conduite journalière %d min > 10 h" % j["conduite"]})
        elif j["conduite"] > JOUR_NORMAL:
            prolong += 1
        if j["reduit"]:
            reduits += 1
        if j["fin_repos"] - j["debut"] > 1440:
            inf.append({"article": "8(2)", "minute": j["debut"], "detail": "repos journalier pas terminé dans les 24 h (fini à +%d min)" % (j["fin_repos"] - j["debut"])})
    # journée en cours (pas encore de repos) : conduite au-delà de 10 h, ou 24 h dépassées sans repos possible
    if conduite_jour_cours > JOUR_PROLONGE:
        inf.append({"article": "6(1)", "minute": debut, "detail": "conduite journalière %d min > 10 h" % conduite_jour_cours})
    if fin_trace - debut > 1440:
        inf.append({"article": "8(2)", "minute": debut, "detail": "plus de 24 h sans repos journalier"})
    if reduits > 3:
        inf.append({"article": "8(4)", "minute": 0, "detail": "%d repos journaliers réduits (3 au plus entre deux repos hebdomadaires)" % reduits})
    inf.sort(key=lambda i: i["minute"])
    return {"infractions": inf, "prolongations": prolong, "repos_reduits": reduits, "non_controle": NON_CONTROLE}


if __name__ == "__main__":
    tr = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else json.load(sys.stdin)
    print(json.dumps(controler([tuple(s) for s in tr]), ensure_ascii=False, indent=1))
