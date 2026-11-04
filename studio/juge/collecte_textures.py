# (c) 2026 Truck So Clean France. Atelier Spartan Studio / Blender : collecte de MATIERES PBR LIBRES (CC0 uniquement)
# pour l'IA de l'atelier (references de peintures, chromes, metaux, caoutchouc, bache, asphalte...).
# Sources : Poly Haven (api.polyhaven.com, tout en CC0) et ambientCG (ambientcg.com, tout en CC0).
# Chaque matiere garde sa source, son auteur et sa licence dans manifeste.json. Jamais redistribue tel quel dans un mod.
# A lancer sur le PC :  python collecte_textures.py --sortie matieres_libres --max 120
import argparse, io, json, os, re, urllib.parse, urllib.request, zipfile

AGENT = "TSC-Spartan-Studio/1.0 (atelier de livrees, usage interne)"
MOTS = ["car paint", "paint", "metal", "chrome", "brushed", "steel", "aluminium", "rubber", "plastic", "leather", "fabric",
        "tarp", "asphalt", "road", "concrete", "rust", "carbon"]


def lire(url, binaire=False):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = r.read()
    return d if binaire else json.loads(d)


def polyhaven(sortie, man, maxi):
    actifs = lire("https://api.polyhaven.com/assets?t=textures")
    for ident, a in actifs.items():
        if len(man["matieres"]) >= maxi:
            return
        texte = (a.get("name", "") + " " + " ".join(a.get("tags", [])) + " " + " ".join(a.get("categories", []))).lower()
        if ident in man["ids"] or not any(m in texte for m in MOTS):
            continue
        f = lire("https://api.polyhaven.com/files/" + ident)
        d = os.path.join(sortie, "polyhaven_" + ident); os.makedirs(d, exist_ok=True)
        cartes = {}
        for carte in ("Diffuse", "nor_gl", "Rough", "Metal", "AO", "Displacement"):
            v = f.get(carte, {}).get("2k", {}).get("jpg") or f.get(carte, {}).get("2k", {}).get("png")
            if v:
                nom = carte.lower() + os.path.splitext(v["url"])[1]
                open(os.path.join(d, nom), "wb").write(lire(v["url"], True)); cartes[carte] = nom
        if not cartes:
            continue
        man["ids"].append(ident)
        man["matieres"].append({"id": ident, "dossier": os.path.basename(d), "nom": a.get("name"), "cartes": cartes, "source": "https://polyhaven.com/a/" + ident,
                                "auteur": ", ".join((a.get("authors") or {}).keys()), "licence": "CC0"})
        json.dump(man, open(os.path.join(sortie, "manifeste.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Poly Haven :", a.get("name"))


def ambientcg(sortie, man, maxi):
    for mot in MOTS:
        if len(man["matieres"]) >= maxi:
            return
        q = urllib.parse.urlencode({"type": "Material", "q": mot, "limit": 8, "include": "downloadData"})
        for a in lire("https://ambientcg.com/api/v2/full_json?" + q).get("foundAssets", []):
            if len(man["matieres"]) >= maxi:
                return
            ident = a.get("assetId")
            if not ident or ident in man["ids"]:
                continue
            dl = [z for c in a.get("downloadFolders", {}).values() for cat in c.get("downloadFiletypeCategories", {}).values()
                  for z in cat.get("downloads", []) if z.get("attribute") == "2K-JPG"]
            if not dl:
                continue
            d = os.path.join(sortie, "ambientcg_" + ident); os.makedirs(d, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(lire(dl[0]["fullDownloadPath"], True))) as z:
                for n in z.namelist():
                    if n.lower().endswith((".jpg", ".png")) and "/" not in n:
                        open(os.path.join(d, re.sub(r"[^\w.\-]", "_", n)), "wb").write(z.read(n))
            man["ids"].append(ident)
            man["matieres"].append({"id": ident, "dossier": os.path.basename(d), "nom": ident, "source": "https://ambientcg.com/view?id=" + ident,
                                    "auteur": "ambientCG (Lennart Demes)", "licence": "CC0"})
            json.dump(man, open(os.path.join(sortie, "manifeste.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("ambientCG :", ident)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="matieres_libres")
    ap.add_argument("--max", type=int, default=120)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    fm = os.path.join(a.sortie, "manifeste.json")
    man = json.load(open(fm, encoding="utf-8")) if os.path.exists(fm) else {"regle": "CC0 uniquement, reference de l'atelier, jamais redistribue tel quel", "ids": [], "matieres": []}
    for source in (polyhaven, ambientcg):
        try:
            source(a.sortie, man, a.max)
        except Exception as e:
            print(source.__name__, ":", e)
    print(len(man["matieres"]), "matieres libres")


if __name__ == "__main__":
    main()
