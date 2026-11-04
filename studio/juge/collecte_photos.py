# (c) 2026 Truck So Clean France. Juge de l'atelier Spartan Studio : collecte de PHOTOS REELLES LIBRES de camions et semi-remorques.
# Regle de Mendy (03/11/2026) : CC0 et CC BY acceptes ; NC, ND, SA, sans licence, extraits de jeux refuses.
# Chaque fichier garde sa source, son auteur et sa licence dans manifeste.json (credits obligatoires pour CC BY).
# Les photos servent UNIQUEMENT de reference au juge (jamais redistribuees, jamais dans un mod).
# Source : API publique de Wikimedia Commons. A lancer sur le PC (le conteneur de developpement n'a pas acces a Commons).
#   python collecte_photos.py --sortie photos_reelles --max 400
import argparse, json, os, re, time, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
AGENT = "TSC-Spartan-Studio-juge/1.0 (atelier de livrees, usage interne)"
# Categories de vrais camions europeens, vues de cote / 3/4 (les sous-categories sont parcourues sur 1 niveau)
CATEGORIES = [
    "Scania R-series", "Scania S-series (2016)", "Volvo FH", "Volvo FH16", "DAF XF", "Mercedes-Benz Actros",
    "MAN TGX", "Renault Trucks T", "Iveco S-Way", "Semi-trailer trucks in France", "Tank trucks in France",
    "Livestock trucks", "Tipper trucks",
]


def licence_ok(nom):
    """CC0 / domaine public / CC BY x.x seulement (pas SA, NC, ND)."""
    n = (nom or "").strip().lower()
    if not n:
        return False
    if n in ("cc0", "public domain", "pd", "cc-zero") or n.startswith("cc0"):
        return True
    if re.fullmatch(r"cc[ -]by[ -]\d(\.\d)?( [a-z\-]+)?", n):   # « CC BY 4.0 », « CC BY 2.0 de »...
        return not any(x in n for x in ("-sa", " sa", "-nc", " nc", "-nd", " nd"))
    return False


def texte(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def appel(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fichiers_categorie(cat, profondeur=1):
    vus, a_voir = [], [(cat, 0)]
    while a_voir:
        c, p = a_voir.pop(0)
        suite = {}
        while True:
            d = appel({"action": "query", "list": "categorymembers", "cmtitle": "Category:" + c, "cmtype": "file|subcat", "cmlimit": 500, **suite})
            for m in d.get("query", {}).get("categorymembers", []):
                if m["ns"] == 6:
                    vus.append(m["title"])
                elif m["ns"] == 14 and p < profondeur:
                    a_voir.append((m["title"].split(":", 1)[1], p + 1))
            if "continue" not in d:
                break
            suite = d["continue"]
    return vus


def infos(titres):
    d = appel({"action": "query", "titles": "|".join(titres), "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1024})
    for p in d.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [None])[0]
        if not ii or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        md = ii.get("extmetadata", {})
        yield {"titre": p["title"], "licence": texte(md.get("LicenseShortName", {}).get("value")),
               "auteur": texte(md.get("Artist", {}).get("value")), "url_licence": md.get("LicenseUrl", {}).get("value", ""),
               "page": ii.get("descriptionurl", ""), "image": ii.get("thumburl") or ii.get("url"), "largeur": ii.get("width", 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="photos_reelles")
    ap.add_argument("--max", type=int, default=400)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    fman = os.path.join(a.sortie, "manifeste.json")
    man = json.load(open(fman, encoding="utf-8")) if os.path.exists(fman) else {"regle": "CC0 / CC BY uniquement, reference du juge, jamais redistribue", "photos": []}
    deja = {p["titre"] for p in man["photos"]}
    refus = {}
    for cat in CATEGORIES:
        if len(man["photos"]) >= a.max:
            break
        try:
            titres = [t for t in fichiers_categorie(cat) if t not in deja]
        except Exception as e:
            print("categorie", cat, ":", e); continue
        for i in range(0, len(titres), 40):
            for f in infos(titres[i:i + 40]):
                if len(man["photos"]) >= a.max:
                    break
                if f["largeur"] < 800 or not licence_ok(f["licence"]):
                    refus[f["licence"] or "sans licence"] = refus.get(f["licence"] or "sans licence", 0) + 1; continue
                nom = re.sub(r"[^\w.\-]+", "_", f["titre"].split(":", 1)[1])[:120]
                if not nom.lower().endswith((".jpg", ".jpeg", ".png")):
                    nom += ".jpg"
                try:
                    req = urllib.request.Request(f["image"], headers={"User-Agent": AGENT})
                    with urllib.request.urlopen(req, timeout=60) as r, open(os.path.join(a.sortie, nom), "wb") as o:
                        o.write(r.read())
                except Exception as e:
                    print("telechargement", nom, ":", e); continue
                man["photos"].append({"fichier": nom, "titre": f["titre"], "categorie": cat, "licence": f["licence"], "url_licence": f["url_licence"],
                                      "auteur": f["auteur"], "source": f["page"]})
                deja.add(f["titre"])
                json.dump(man, open(fman, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                time.sleep(0.2)   # politesse envers Commons
            print(cat, ":", len(man["photos"]), "photos gardees")
    print("refusees par licence :", refus)


if __name__ == "__main__":
    main()
