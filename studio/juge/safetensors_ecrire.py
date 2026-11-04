# Ecriture safetensors minimale (tests uniquement).
import json, struct
def ecrire(sd, fichier):
    tete, brut, pos = {}, b"", 0
    for k, v in sd.items():
        b = v.detach().float().contiguous().numpy().tobytes()
        tete[k] = {"dtype": "F32", "shape": list(v.shape), "data_offsets": [pos, pos + len(b)]}; brut += b; pos += len(b)
    h = json.dumps(tete).encode()
    with open(fichier, "wb") as f:
        f.write(struct.pack("<Q", len(h))); f.write(h); f.write(brut)
