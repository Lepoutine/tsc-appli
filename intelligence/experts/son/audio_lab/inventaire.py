"""Section 4.1-4.2 du cahier des charges : inventaire des sources, sans jamais les modifier.

Pour chaque fichier : chemin, taille, SHA-256, format, frequence, canaux, duree (WAV lu directement,
autres formats via ffprobe s'il est present), et la colonne « droits » laissee a remplir par Mendy.
Usage : python3 -m audio_lab.inventaire <dossier ou fichier>... --sortie inventaire.json
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import wave

EXT = (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".mp4", ".mov", ".mkv", ".webm", ".aac")


def sha256(chemin, bloc=1 << 20):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(bloc), b""):
            h.update(b)
    return h.hexdigest()


def infos(chemin):
    if chemin.lower().endswith(".wav"):
        try:
            with wave.open(chemin, "rb") as w:
                return {"format": "wav pcm %d bits" % (8 * w.getsampwidth()), "frequence_hz": w.getframerate(),
                        "canaux": w.getnchannels(), "duree_s": round(w.getnframes() / w.getframerate(), 3)}
        except Exception as e:  # WAV non PCM (float, extensible...) : on passe a ffprobe
            err = str(e)
    else:
        err = ""
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                            "stream=codec_name,sample_rate,channels:format=duration", "-of", "json", chemin],
                           capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            s = (d.get("streams") or [{}])[0]
            return {"format": s.get("codec_name", "?"), "frequence_hz": int(s.get("sample_rate", 0) or 0),
                    "canaux": s.get("channels", 0), "duree_s": round(float(d.get("format", {}).get("duration", 0) or 0), 3)}
        except Exception as e:
            err = str(e)
    return {"format": "inconnu", "erreur": err or "ffprobe absent"}


def inventorier(chemins):
    lignes = []
    for c in chemins:
        fichiers = [c] if os.path.isfile(c) else [os.path.join(r, n) for r, _, ns in os.walk(c) for n in sorted(ns)]
        for f in fichiers:
            if not f.lower().endswith(EXT):
                continue
            st = os.stat(f)
            lig = {"fichier": f, "taille_o": st.st_size, "sha256": sha256(f),
                   "modifie": datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat(timespec="seconds"),
                   "droits": "a preciser par Mendy"}
            lig.update(infos(f))
            lignes.append(lig)
    return lignes


def ecrire(lignes, sortie):
    rapport = {"genere": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "regle": "originaux en lecture seule : comparer le sha256 avant chaque travail", "fichiers": lignes}
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=1)
    cols = ["fichier", "taille_o", "sha256", "format", "frequence_hz", "canaux", "duree_s", "modifie", "droits", "erreur"]
    with open(os.path.splitext(sortie)[0] + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cols)
        for l in lignes:
            w.writerow([l.get(k, "") for k in cols])


def verifier(rapport_json):
    """Recalcule les empreintes : liste des fichiers modifies ou disparus depuis l'inventaire."""
    with open(rapport_json, encoding="utf-8") as f:
        r = json.load(f)
    return [l["fichier"] for l in r["fichiers"] if not os.path.exists(l["fichier"]) or sha256(l["fichier"]) != l["sha256"]]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("chemins", nargs="+")
    p.add_argument("--sortie", default="inventaire.json")
    a = p.parse_args()
    l = inventorier(a.chemins)
    ecrire(l, a.sortie)
    print("%d fichiers -> %s" % (len(l), a.sortie))
