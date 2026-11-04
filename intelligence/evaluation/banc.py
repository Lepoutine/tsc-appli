#!/usr/bin/env python3
"""Banc d'évaluation TSC Virtuoso (directive de Mendy du 04/11/2026, sections 7, 12 et 13).

Chaque épreuve vise un expert et un niveau (1 = base, 2 = métier, 3 = difficile). Elle tire un problème NEUF à
chaque passage (graine = horloge) : l'expert ne peut pas l'avoir « appris par cœur ». Chaque épreuve rend une
mesure et l'attendu, jamais une simple déclaration.

Après chaque passage :
- historique.jsonl reçoit une ligne par épreuve (pour suivre le niveau dans le temps) ;
- une épreuve réussie aux 3 derniers passages et ratée maintenant est une RÉGRESSION : le banc la signale et rend 2
  (3 passages : les problèmes étant tirés au hasard, un seul succès ne prouve pas une compétence stable) ;
- chaque échec est noté dans la mémoire commune (type test, avec la cause mesurée) pour être corrigé puis rejoué.

Les épreuves qui demandent le PC de Mendy (jeu, GPU, Blender, PowerShell) sont listées comme « pc » avec la raison :
elles ne sont jamais comptées comme réussies d'ici.

  python3 intelligence/evaluation/banc.py [--graine N] [--sans-memoire] [--agent son]
"""
import argparse
import datetime
import json
import math
import os
import subprocess
import sys
import tempfile
import traceback

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(ICI)
DEPOT = os.path.dirname(BASE)
HISTO = os.path.join(ICI, "historique.jsonl")
sys.path.insert(0, os.path.join(BASE, "experts", "son"))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "outils"))

SR = 48000
EPREUVES = []


# Grille de certification interne TSC Virtuoso (Mendy, 04/11/2026) : objectifs, pas niveaux atteints.
GRILLE = {"connaissances": 20, "diagnostic": 25, "autonomie": 20, "qualite": 25, "innovation": 10}
NOMS_GRILLE = {"connaissances": "Connaissances métier vérifiées", "diagnostic": "Diagnostic et résolution",
               "autonomie": "Autonomie opérationnelle", "qualite": "Qualité et fiabilité des livrables", "innovation": "Innovation démontrée"}
CERTIF = os.path.join(ICI, "certifications.jsonl")


def epreuve(agent, niveau, titre, critere):
    assert critere in GRILLE
    def deco(f):
        EPREUVES.append({"id": f.__name__, "agent": agent, "niveau": niveau, "titre": titre, "critere": critere, "f": f})
        return f
    return deco


def moteur_synthetique(rng, rpm, cylindres=8, duree=4.0, bruit=0.05):
    """Train d'impulsions d'allumage amorties (grave) + bruit : un moteur dont on connaît le vrai régime."""
    n = int(duree * SR)
    x = np.zeros(n)
    f_all = rpm / 60.0 * cylindres / 2.0
    t0 = 0.0
    k = np.arange(int(0.03 * SR)) / SR
    coup = np.sin(2 * np.pi * rng.uniform(60, 110) * k) * np.exp(-k * rng.uniform(80, 140))
    # chaque cylindre a sa force propre et fixe (comme un vrai moteur) : c'est ce qui fait qu'un cycle se répète
    force = rng.uniform(0.45, 1.0, cylindres)
    c = 0
    while t0 < duree:
        i = int(t0 * SR)
        m = min(len(coup), n - i)
        x[i:i + m] += coup[:m] * force[c % cylindres] * rng.uniform(0.95, 1.05)
        c += 1
        t0 += 1.0 / f_all * rng.uniform(0.99, 1.01)
    x += bruit * rng.standard_normal(n)
    return 0.5 * x / np.abs(x).max()


# ---------------------------------------------------------------- son (expert 5)
@epreuve("son", 1, "sonie LUFS d'un sinus d'amplitude inconnue (BS.1770)", "connaissances")
def son_lufs(rng):
    from audio_lab.controles import lufs
    a = rng.uniform(0.05, 0.9)
    t = np.arange(8 * SR) / SR
    v = lufs(a * np.sin(2 * np.pi * 997 * t), SR)
    att = -3.01 + 20 * math.log10(a)
    return abs(v - att) <= 0.1, round(v, 2), "%.2f ±0,1" % att


@epreuve("son", 2, "crête vraie entre deux échantillons (sinus fs/4 déphasé)", "connaissances")
def son_crete_vraie(rng):
    from audio_lab.controles import crete_vraie
    a = rng.uniform(0.3, 0.9)
    n = np.arange(SR)
    x = a * np.sin(2 * np.pi * n / 4 + math.pi / 4)  # échantillons à 0,707 a, vraie crête a
    v = crete_vraie(x)
    att = 20 * math.log10(a)
    return abs(v - att) <= 0.3, round(v, 2), "%.2f ±0,3 (les échantillons montrent %.2f)" % (att, 20 * math.log10(np.abs(x).max()))


def juge_regime(res, rpm, doute_admis=False):
    """Juste à 5 %, ou bien doute annoncé avec la bonne réponse parmi les candidats (règle : ne jamais
    transformer une hypothèse en certitude). Une réponse fausse donnée comme sûre est un échec."""
    _, v, d = res
    juste = v is not None and abs(v - rpm) / rpm <= 0.05
    doute_honnete = doute_admis and d["ambigu"] and any(abs(c - rpm) / rpm <= 0.05 for c in d["candidats"])
    return juste or doute_honnete, "%s%s" % (round(v or 0), " (ambigu : %s)" % d["candidats"] if d["ambigu"] else ""), "%d ±5 %%" % rpm + (", ou doute annoncé avec la bonne réponse" if doute_admis else "")


@epreuve("son", 2, "régime d'un V8 inconnu par son allumage (450-1800 tr/min)", "diagnostic")
def son_regime(rng):
    import mesure_son as ms
    rpm = rng.uniform(450, 1800)
    return juge_regime(ms.allumage(moteur_synthetique(rng, rpm), SR, 8, details=True), rpm)


@epreuve("son", 3, "régime d'un ralenti très bas (250-450 tr/min) avec bruit fort", "diagnostic")
def son_regime_bas(rng):
    import mesure_son as ms
    rpm = rng.uniform(250, 450)
    return juge_regime(ms.allumage(moteur_synthetique(rng, rpm, bruit=0.25), SR, 8, details=True), rpm, doute_admis=True)


@epreuve("son", 2, "régime du vrai ralenti Scania 164L (référence mesurée : 33,3 Hz = 500 tr/min)", "diagnostic")
def son_regime_reel(rng):
    import mesure_son as ms
    f = "/mnt/project-files/tsc_intelligence/expert_son/segments_reels/01_164L_ralenti_stable.wav"
    if not os.path.isfile(f):
        return None, "fichier absent", "500 ±5 %"
    x, sr = ms.lire_wav(f)
    d0 = rng.uniform(0, max(0.1, len(x) / sr - 5.0))  # 5 s prises au hasard dans le passage
    x = x[int(d0 * sr):int((d0 + 5) * sr)]
    _, v, d = ms.allumage(x, sr, 8, details=True)
    return v is not None and abs(v - 500) / 500 <= 0.05, "%s (à partir de %.1f s)%s" % (round(v or 0), d0, ", doute signalé %s" % d["candidats"] if d["ambigu"] else ""), "500 ±5 % en première réponse"


def allumage_ancien(x, sr, cylindres):
    """Méthode d'avant le 04/11 (autocorrélation d'enveloppe), gardée ici comme référence à battre."""
    import mesure_son as ms
    e = ms.enveloppe(x, sr, 400.0)
    e = e - e.mean()
    pas = max(sr // 2000, 1)
    e = e[::pas]
    sr2 = sr / pas
    n = 1 << int(np.ceil(np.log2(2 * len(e))))
    ac = np.fft.irfft(np.abs(np.fft.rfft(e, n)) ** 2)[: len(e)]
    ac = ac / ac[0]
    lo, hi = int(sr2 / 250), int(sr2 / 15)
    seg = ac[lo:hi]
    fort = float(seg.max())
    i = int(np.argmax(seg)) + lo
    for j in range(1, len(seg) - 1):
        if seg[j] >= seg[j - 1] and seg[j] >= seg[j + 1] and seg[j] >= 0.3 * fort:
            i = j + lo
            break
    return sr2 / i * 60.0 / (cylindres / 2.0)


@epreuve("son", 3, "innovation mesurée : le nouvel estimateur de régime contre l'ancien (vrai 164L + 12 moteurs neufs)", "innovation")
def son_innovation_regime(rng):
    """Avantage démontré = juste sur le vrai enregistrement là où l'ancienne méthode se trompe, sans perdre plus
    d'un cas sur 12 moteurs synthétiques neufs."""
    import mesure_son as ms
    f = "/mnt/project-files/tsc_intelligence/expert_son/segments_reels/01_164L_ralenti_stable.wav"
    if not os.path.isfile(f):
        return None, "fichier absent", "-"
    x, sr = ms.lire_wav(f)
    d0 = rng.uniform(0, max(0.1, len(x) / sr - 5.0))
    x = x[int(d0 * sr):int((d0 + 5) * sr)]
    reel_nv, reel_an = ms.allumage(x, sr, 8)[1], allumage_ancien(x, sr, 8)
    nv = an = 0
    for _ in range(12):
        rpm = rng.uniform(300, 1800)
        y = moteur_synthetique(rng, rpm, bruit=float(rng.choice([0.05, 0.15])))
        nv += abs(ms.allumage(y, SR, 8)[1] - rpm) / rpm <= 0.05
        an += abs(allumage_ancien(y, SR, 8) - rpm) / rpm <= 0.05
    ok_reel = abs(reel_nv - 500) / 500 <= 0.05
    ok = ok_reel and abs(reel_an - 500) / 500 > 0.05 and nv >= an - 1
    return ok, "vrai 164L : nouveau %d, ancien %d ; synthétiques : nouveau %d/12, ancien %d/12" % (reel_nv, reel_an, nv, an), "nouveau juste là où l'ancien se trompe, synthétiques >= ancien - 1"


@epreuve("son", 3, "raccord de boucle : trouver un saut caché, sans fausse alarme sur une boucle propre", "qualite")
def son_raccord(rng):
    from audio_lab.controles import SEUILS, raccord
    rpm = rng.uniform(500, 900)
    cyc = 120.0 / rpm
    x = moteur_synthetique(rng, rpm, duree=cyc * 12 + 0.5, bruit=0.0)
    propre = x[:int(round(cyc * 10 * SR))]
    saut = rng.uniform(3, 6)
    mauvais = propre.copy()
    mauvais[-int(0.3 * SR):] *= 10 ** (-saut / 20)
    _, n1 = raccord(propre, SR)
    _, n2 = raccord(mauvais, SR)
    ok = n1 <= SEUILS["raccord_niveau_db"] and n2 > SEUILS["raccord_niveau_db"]
    return ok, "propre %.1f dB, cassée %.1f dB" % (n1, n2), "propre <= %.1f, cassée > %.1f (saut %.1f dB)" % (SEUILS["raccord_niveau_db"], SEUILS["raccord_niveau_db"], saut)


@epreuve("son", 3, "cycle moteur pour une boucle sans saut (120/tr/min s)", "qualite")
def son_cycle(rng):
    import boucle_reelle as br
    rpm = rng.uniform(450, 900)
    v = br.cycle_moteur(moteur_synthetique(rng, rpm, duree=6.0), SR)
    att = 120.0 / rpm
    # un multiple ou sous-multiple d'allumage donne aussi une boucle propre ; on exige le cycle complet à 5 %
    return abs(v - att) / att <= 0.05, round(v, 4), "%.4f s ±5 %%" % att


# ---------------------------------------------------------------- forge (expert 10)
@epreuve("forge", 1, "ranger des sons jamais vus par leur nom (pack Forge)", "autonomie")
def forge_roles(rng):
    import pack_forge as pf
    cas = [("MAN_TGX_2020", "air_gear_%d.wav", "boite_air"), ("Scania_NG_effets", "hb_off.wav", "frein_parc"),
           ("Scania_V8_open_pipe_v2", "claquant_%d.wav", "claquement"), ("Scania_NG_effets", "liftaxle.wav", "suspension"),
           ("boucles_reparees", "c_%d00_op_idle.wav", "charge"), ("Klaxons", "klaxon_%d.wav", "autre"),
           ("MAN_TGX_2020", "parking_brake_on.wav", "frein_parc"), ("Scania_NG_effets", "retarder.wav", "frein_moteur")]
    bon = 0
    rates = []
    for d, motif, att in cas:
        nom = motif % rng.integers(6, 23) if "%d" in motif else motif
        r = pf.classer(d, nom)[0]
        bon += r == att
        if r != att:
            rates.append("%s/%s -> %s" % (d, nom, r))
    return bon == len(cas), "%d/%d" % (bon, len(cas)) + (" ; ratés : " + ", ".join(rates) if rates else ""), "%d/%d" % (len(cas), len(cas))


@epreuve("forge", 3, "IA Forge (JS) : apprendre une règle d'écoute cachée et la retrouver sur le juge", "autonomie")
def forge_ia_js(rng):
    """On fabrique des sons dont la règle « garder » est connue (grave = garder, aigu = jeter) et on vérifie que
    l'IA Forge l'apprend avec ses propres règles (node + le vrai forge_ia.js, sans navigateur)."""
    graine = int(rng.integers(1, 1 << 30))
    js = r"""
const fs = require('fs'); let mem = {};
global.window = global; global.localStorage = { getItem: k => mem[k] || null, setItem: (k, v) => { mem[k] = v; } };
window.SF = {};
eval(fs.readFileSync(process.argv[2], 'utf8'));
let s = %d; const r = () => (s = (s * 1103515245 + 12345) %% 2147483648) / 2147483648;
function buf(f) { const n = 48000, d = new Float32Array(n); for (let i = 0; i < n; i++) d[i] = 0.4 * Math.sin(2 * Math.PI * f * i / 48000) + 0.05 * (r() - 0.5); return { sampleRate: 48000, length: n, numberOfChannels: 1, duration: 1, getChannelData: () => d }; }
const ex = [];
for (let i = 0; i < 70; i++) { const grave = r() < 0.5, f = grave ? 60 + 150 * r() : 1500 + 4000 * r(); ex.push({ cle: 'son' + i + '_' + s, t: SF.traits(buf(f), 0, 1), role: grave ? 'ralenti' : 'turbo', verdict: grave ? 'garder' : 'jeter' }); }
const res = SF.IA.apprend(ex); const v = SF.IA.etat().version;
console.log(JSON.stringify({ adoptee: res.adoptee, raison: res.raison, role: v && v.score_role, verdict: v && v.score_verdict }));
""" % graine
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
    try:
        out = subprocess.run(["node", f.name, os.path.join(DEPOT, "sound_forge", "ui", "forge_ia.js")], capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(f.name)
    if out.returncode:
        return False, "node : " + out.stderr.strip()[-200:], "version adoptée, >= 90 % sur le juge"
    o = json.loads(out.stdout.strip().splitlines()[-1])
    ok = o["adoptee"] and (o["verdict"] or 0) >= 0.9 and (o["role"] or 0) >= 0.9
    return ok, "adoptée %s, rôle %s, garder/jeter %s" % (o["adoptee"], o["role"], o["verdict"]), "version adoptée, >= 90 % sur le juge"


# ---------------------------------------------------------------- qualité (expert 8)
@epreuve("qualite", 1, "la base commune passe la vérification (0 erreur)", "qualite")
def qualite_base(rng):
    import tsc_ia
    err, _ = tsc_ia.verifier()
    return not err, "%d erreur(s)" % len(err) + (" : " + err[0] if err else ""), "0 erreur"


@epreuve("qualite", 2, "le vérificateur attrape une fiche sans source glissée au hasard (test de mutation)", "diagnostic")
def qualite_mutation(rng):
    import tsc_ia
    idx = json.load(open(tsc_ia.INDEX, encoding="utf-8"))
    cible = idx["fiches"][int(rng.integers(0, len(idx["fiches"])))]
    cible["sources"] = []
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=os.path.dirname(tsc_ia.INDEX), encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    try:
        err, _ = tsc_ia.verifier(index_chemin=f.name)
    finally:
        os.unlink(f.name)
    vu = any(cible["id"] in e for e in err)
    return vu, "fiche %s : %s" % (cible["id"], "attrapée" if vu else "PAS vue"), "attrapée"


@epreuve("qualite", 3, "boucle d'apprentissage : une version moins bonne est refusée, l'ancienne reste", "qualite")
def qualite_boucle(rng):
    from apprentissage.boucle import Boucle
    seuil_vrai = float(rng.uniform(5, 15))

    def entrainer(ex):
        return {"seuil": float(np.mean([e["x"] for e in ex if e["y"]]) + np.mean([e["x"] for e in ex if not e["y"]])) / 2, "triche": ex[0].get("triche", False)}

    def juger(m, ex):
        return {"justesse": float(np.mean([((e["x"] > m["seuil"]) == e["y"]) != m["triche"] for e in ex]))}

    def donnees(n, triche=False):
        x = rng.uniform(0, 20, n)
        return [{"cle": "e%d_%f" % (i, v), "x": float(v), "y": bool(v > seuil_vrai), "triche": triche} for i, v in enumerate(x)]
    with tempfile.TemporaryDirectory() as d:
        b = Boucle(d, entrainer, juger)
        a = b.apprend(donnees(200))["adoptee"]
        refus = not b.apprend(donnees(220, triche=True))["adoptee"]
        garde = b.etat["versions"][-1]["n"] == 1
    return a and refus and garde, "v1 %s, pire refusée %s, v1 gardée %s" % (a, refus, garde), "True, True, True"


# ---------------------------------------------------------------- logiciel (expert 7)
@epreuve("logiciel", 1, "tous les tests unitaires du dépôt passent (non-régression)", "qualite")
def logiciel_tests(rng):
    out = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", os.path.join(BASE, "tests")], capture_output=True, text=True, timeout=600, cwd=BASE)
    der = out.stderr.strip().splitlines()
    return out.returncode == 0, " ".join(der[-3:]), "OK"


@epreuve("logiciel", 2, "syntaxe de tous les JS de Sound Forge (node)", "qualite")
def logiciel_js(rng):
    d = os.path.join(DEPOT, "sound_forge", "ui")
    ko = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".js"):
            r = subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(process.argv[1],'utf8'))", os.path.join(d, f)], capture_output=True, text=True)
            if r.returncode:
                ko.append(f)
    return not ko, "%s" % (", ".join(ko) or "aucune erreur"), "aucune erreur"


# ---------------------------------------------------------------- épreuves du PC (jamais comptées réussies d'ici)
PC = [
    ("graphics", "écart jeu/réel d'une version du plugin sur le jeu de captures fixe", "jeu + GPU du Shadow (fil Graphics)"),
    ("textures", "TSC-IA textures : gain en dB sur images réelles jamais vues", "PC (tsc_graphics\\tsc_ia), juge déjà en place"),
    ("performance", "Test-PerfLab.ps1 + diagnostic avant/après", "PowerShell absent du cloud"),
    ("mods", "game.log réel -> mod et fichier fautifs ; contrôle .scs", "Verifier_Mods_TSC.ps1 sur le PC"),
    ("conduite", "rejouer traces.json sur le Pilote de tête", "code du pilote sur le PC"),
    ("atelier", "Blender -b -P : UV, échelle, origine d'un modèle SCS", "Blender sur le PC"),
    ("forge", "build fmodstudiocl de l'exemple Peterbilt + GUID", "FMOD Studio sur le PC"),
]


def lancer(graine=None, agent=None, memoire=True, histo=HISTO):
    graine = int(graine if graine is not None else datetime.datetime.now().timestamp() * 1000) % (2 ** 32)
    date = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    precedent = {}
    if os.path.isfile(histo):
        for l in open(histo, encoding="utf-8"):
            try:
                e = json.loads(l)
                precedent.setdefault(e["epreuve"], []).append(e["ok"])
            except (ValueError, KeyError):
                pass
    res = []
    for i, ep in enumerate(EPREUVES):
        if agent and ep["agent"] != agent:
            continue
        rng = np.random.default_rng(graine + i)
        try:
            ok, valeur, attendu = ep["f"](rng)
            if ok is None:  # donnée absente ici : ni réussite ni échec
                continue
        except Exception as x:  # une épreuve qui plante est un échec, avec sa cause
            ok, valeur, attendu = False, "plantage : %s" % "".join(traceback.format_exception_only(type(x), x)).strip(), "-"
        avant = precedent.get(ep["id"])
        r = {"date": date, "graine": graine, "epreuve": ep["id"], "agent": ep["agent"], "niveau": ep["niveau"], "titre": ep["titre"], "critere": ep["critere"],
             "ok": bool(ok), "valeur": str(valeur), "attendu": str(attendu), "regression": bool(avant and len(avant) >= 3 and all(avant[-3:]) and not ok)}
        res.append(r)
    with open(histo, "a", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if memoire:
        import tsc_ia
        for r in res:
            if not r["ok"]:
                tsc_ia.noter(r["agent"], "test", "%s épreuve %s (niveau %d) ratée : %s" % ("RÉGRESSION :" if r["regression"] else "", r["epreuve"], r["niveau"], r["titre"]),
                             "banc.py graine %d : obtenu %s, attendu %s" % (graine, r["valeur"], r["attendu"]), statut="en_attente")
    return graine, res


def niveaux(res):
    """Niveau mesuré par expert : le plus haut niveau dont TOUTES les épreuves (et celles d'en dessous) passent."""
    par = {}
    for r in res:
        par.setdefault(r["agent"], {}).setdefault(r["niveau"], []).append(r["ok"])
    out = {}
    for a, nv in par.items():
        n = 0
        for k in sorted(nv):
            if all(nv[k]) and k == n + 1:
                n = k
            else:
                break
        out[a] = {"niveau_mesure": n, "reussies": sum(sum(v) for v in nv.values()), "total": sum(len(v) for v in nv.values())}
    return out


def certifier(res, histo=CERTIF):
    """Note sur 100 par expert selon la grille, avec la part de la grille réellement mesurée.
    1re note = examen d'entrée ; les suivantes = examens après amélioration, comparés au précédent."""
    date = res[0]["date"] if res else ""
    stab = {}
    if os.path.isfile(HISTO):
        for l in open(HISTO, encoding="utf-8"):
            if l.strip():
                e = json.loads(l)
                stab.setdefault(e["epreuve"], []).append(e["ok"])
    prec = {}
    if os.path.isfile(histo):
        for l in open(histo, encoding="utf-8"):
            e = json.loads(l)
            prec[e["agent"]] = e
    out = []
    for ag in sorted({r["agent"] for r in res}):
        R = [r for r in res if r["agent"] == ag]
        par = {}
        for r in R:  # taux de réussite de chaque épreuve sur ses 5 derniers passages : un coup de chance ne suffit pas
            v = stab.get(r["epreuve"], [r["ok"]])[-5:]
            par.setdefault(r["critere"], []).append(sum(v) / len(v))
        detail = {c: round(100.0 * sum(v) / len(v)) for c, v in par.items()}
        couv = sum(GRILLE[c] for c in detail)
        note = round(sum(GRILLE[c] * detail[c] / 100.0 for c in detail) * 100.0 / couv, 1) if couv else 0.0
        e = {"date": date, "agent": ag, "examen": "apres_amelioration" if ag in prec else "entree", "note_sur_100": note,
             "grille_mesuree_pct": couv, "detail": detail, "non_mesure": [c for c in GRILLE if c not in detail]}
        p = prec.get(ag)
        if p:
            e["avant"] = p["note_sur_100"]
            e["criteres_en_baisse"] = [c for c, v in detail.items() if c in p["detail"] and v < p["detail"][c]]
        out.append(e)
    with open(histo, "a", encoding="utf-8") as f:
        for e in out:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--graine", type=int)
    p.add_argument("--agent")
    p.add_argument("--sans-memoire", action="store_true")
    p.add_argument("--certifier", action="store_true", help="examen de certification : note la grille et compare au précédent")
    p.add_argument("--passages", type=int, default=1, help="nombre de passages (problèmes neufs à chaque fois) ; 5 conseillé pour un examen")
    a = p.parse_args(argv)
    for k in range(a.passages - 1):
        lancer(None if a.graine is None else a.graine + 1000 * (k + 1), a.agent, not a.sans_memoire)
    graine, res = lancer(a.graine, a.agent, not a.sans_memoire)
    print("Banc TSC Virtuoso, graine %d (problèmes neufs)" % graine)
    for r in res:
        print("  %-5s %-9s N%d %-20s %s  [attendu %s]%s" % ("OK" if r["ok"] else "ÉCHEC", r["agent"], r["niveau"], r["epreuve"], r["valeur"], r["attendu"], "  << RÉGRESSION" if r["regression"] else ""))
    for ag, n in sorted(niveaux(res).items()):
        print("  %-9s niveau mesuré %d (%d/%d)" % (ag, n["niveau_mesure"], n["reussies"], n["total"]))
    for ag, quoi, ou in PC:
        print("  PC    %-9s %s  (%s)" % (ag, quoi, ou))
    if a.certifier:
        print("Certification interne TSC Virtuoso (grille : %s)" % ", ".join("%s %d %%" % (NOMS_GRILLE[c], w) for c, w in GRILLE.items()))
        for e in certifier(res):
            print("  %-9s %s : %.1f/100 sur %d %% de la grille mesurée (réussite sur les 5 derniers passages)%s%s" % (e["agent"], "examen d'entrée" if e["examen"] == "entree" else "après amélioration", e["note_sur_100"], e["grille_mesuree_pct"],
                  " (avant %.1f)" % e["avant"] if "avant" in e else "", " ; EN BAISSE : " + ", ".join(e["criteres_en_baisse"]) if e.get("criteres_en_baisse") else ""))
            print("            non mesuré ici : %s" % (", ".join(NOMS_GRILLE[c] for c in e["non_mesure"]) or "rien"))
    return 2 if any(r["regression"] for r in res) else (1 if not all(r["ok"] for r in res) else 0)


if __name__ == "__main__":
    sys.exit(main())
