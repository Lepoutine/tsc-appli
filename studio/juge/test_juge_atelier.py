# Test du juge de l'atelier sans poids ni photos (poids aleatoires, images synthetiques) : verifie la mecanique seulement.
import os, sys, tempfile, json, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from collecte_photos import licence_ok
from juge_atelier import Juge, charger, est_juge
import torch


def test_licences():
    for ok in ("CC BY 4.0", "CC BY 2.0", "CC0", "Public domain", "CC BY 2.5 nl"):
        assert licence_ok(ok), ok
    for non in ("CC BY-SA 4.0", "CC BY-NC 2.0", "CC BY-ND 3.0", "", "GFDL", "CC BY-SA 3.0 de", "All rights reserved"):
        assert not licence_ok(non), non


def test_juge():
    torch.manual_seed(0)
    d = tempfile.mkdtemp(); reel, rendus = os.path.join(d, "r"), os.path.join(d, "s"); os.makedirs(reel); os.makedirs(rendus)
    rng = np.random.default_rng(0)
    for i in range(80):   # « vraies photos » : bruit texture
        Image.fromarray((rng.random((300, 400, 3)) * 255).astype("uint8")).save(os.path.join(reel, f"p{i}.jpg"))
    Image.fromarray((rng.random((300, 400, 3)) * 255).astype("uint8")).save(os.path.join(rendus, "pareil.png"))
    Image.fromarray(np.full((300, 400, 3), 128, "uint8")).save(os.path.join(rendus, "plat.png"))
    J = Juge(None)
    assert J.morceaux(charger(os.path.join(reel, "p0.jpg"))).shape[1:] == (3, 150, 150)
    assert sum(est_juge(f) for f in os.listdir(reel)) >= 1
    # le script complet avec des poids aleatoires sauvegardes
    from safetensors_ecrire import ecrire
    poids = os.path.join(d, "w.safetensors"); ecrire(J.dino.state_dict(), poids)
    out = os.path.join(d, "o.json")
    r = subprocess.run([sys.executable, "juge_atelier.py", "--poids", poids, "--reel", reel, "--rendus", rendus, "--sortie", out],
                       cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    res = {x["fichier"]: x["realisme"] for x in json.load(open(out))["rendus"]}
    print(res)
    assert res["pareil.png"] > res["plat.png"], res


if __name__ == "__main__":
    test_licences(); test_juge(); print("ok")
