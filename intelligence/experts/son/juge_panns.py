#!/usr/bin/env python3
"""Juge son TSC : PANNs Cnn14 gelé, en NumPy seul (aucun PyTorch, aucun envoi : choix de Mendy du 04/11/2026 21:47).

Rôle : mesurer l'écart entre un son TSC et les VRAIS enregistrements de Mendy, comme le juge DINOv2 de la TSC-IA
Graphics mesure l'écart d'une image au réel. Le juge ne s'entraîne jamais et ne décide pas : il mesure, l'oreille de
Mendy tranche.

Provenance (traçabilité des licences) :
- architecture Cnn14 : Kong et al., « PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern
  Recognition », 2020 ; code https://github.com/qiuqiangkong/audioset_tagging_cnn (licence MIT), réécrit ici en NumPy
  d'après models.py (Cnn14) ;
- poids : Cnn14_mAP=0.431.pth, https://zenodo.org/records/3987831, licence Creative Commons Attribution 4.0
  (attribution obligatoire : Qiuqiang Kong et al.), md5 541141fa2ee191a88f24a3219fff024e ;
- le fichier .pth est lu par un dépickleur restreint (seules les classes de tenseurs sont acceptées) : aucun code
  contenu dans le fichier ne peut s'exécuter.

Chaîne (identique à Cnn14) : 32 kHz mono -> STFT 1024 / pas 320 (noyaux du fichier) -> 64 bandes mel 50-14000 Hz
(matrice du fichier) -> 10 log10 -> bn0 -> 6 blocs de 2 convolutions 3x3 + BN + ReLU + moyenne 2x2 -> moyenne
fréquence -> max + moyenne temps -> fc1 + ReLU = empreinte (2048) ; fc_audioset + sigmoïde = 527 étiquettes AudioSet.

  python3 juge_panns.py poids.pth son.wav [autre.wav ...]
"""
import hashlib
import os
import pickle
import struct
import sys
import wave

import numpy as np

SR = 32000
MD5_POIDS = "541141fa2ee191a88f24a3219fff024e"
EPS_BN = 1e-5
# Étiquettes AudioSet utiles (index de class_labels_indices.csv, ontologie AudioSet) : vérifiées au premier passage
# par le contrôle d'identité (un vrai moteur doit sortir « Vehicle »/« Engine » en tête), voir verifier_identite().


# ---------------------------------------------------------------- lecture sûre d'un .pth (format ancien et zip)
class _Stockage:
    def __init__(self, dtype, cle, n):
        self.dtype, self.cle, self.n, self.data = dtype, cle, n, None


_TYPES = {"FloatStorage": np.float32, "DoubleStorage": np.float64, "LongStorage": np.int64, "IntStorage": np.int32,
          "HalfStorage": np.float16, "ByteStorage": np.uint8}


class _Tenseur:
    def __init__(self, st, off, taille, pas):
        self.st, self.off, self.taille, self.pas = st, off, tuple(taille), tuple(pas)

    def numpy(self):
        d = self.st.data
        el = d.itemsize
        if not self.taille:
            return d[self.off].copy()
        return np.lib.stride_tricks.as_strided(d[self.off:], shape=self.taille, strides=[s * el for s in self.pas]).copy()


def _reconstruit(st, off, taille, pas, *reste):
    return _Tenseur(st, off, taille, pas)


class _Classe:  # type de stockage (torch.FloatStorage) vu comme un simple marqueur
    def __init__(self, nom):
        self.nom = nom


class _Depickleur(pickle.Unpickler):
    AUTORISE = {("torch._utils", "_rebuild_tensor_v2"), ("torch._utils", "_rebuild_tensor"), ("collections", "OrderedDict")}

    def __init__(self, f, stockages, lecteur=None):
        super().__init__(f)
        self.stockages, self.lecteur = stockages, lecteur

    def find_class(self, module, nom):
        if (module, nom) in self.AUTORISE:
            if nom.startswith("_rebuild_tensor"):
                return _reconstruit
            import collections
            return collections.OrderedDict
        if module == "torch" and nom in _TYPES:
            return _Classe(nom)
        raise pickle.UnpicklingError("classe refusée dans le fichier de poids : %s.%s" % (module, nom))

    def persistent_load(self, pid):
        typ, cls, cle, lieu, n = pid[:5]
        if typ != "storage":
            raise pickle.UnpicklingError("objet persistant inconnu")
        nom = cls.nom if isinstance(cls, _Classe) else str(cls)
        if cle not in self.stockages:
            st = _Stockage(_TYPES[nom], cle, n)
            if self.lecteur:
                st.data = self.lecteur(cle, st.dtype)
            self.stockages[cle] = st
        return self.stockages[cle]


def lire_pth(chemin):
    """Rend {nom: tableau NumPy} du state_dict (clé 'model' si présente)."""
    import zipfile
    st = {}
    if zipfile.is_zipfile(chemin):
        z = zipfile.ZipFile(chemin)
        racine = z.namelist()[0].split("/")[0]
        lect = lambda cle, dt: np.frombuffer(z.read("%s/data/%s" % (racine, cle)), dtype=dt)
        obj = _Depickleur(z.open("%s/data.pkl" % racine), st, lect).load()
    else:
        with open(chemin, "rb") as f:
            for _ in range(3):  # nombre magique, protocole, infos système
                pickle.load(f)
            obj = _Depickleur(f, st).load()
            cles = pickle.load(f)
            for cle in cles:
                n = struct.unpack("<q", f.read(8))[0]
                s = st[cle]
                s.data = np.frombuffer(f.read(n * np.dtype(s.dtype).itemsize), dtype=s.dtype)
    if isinstance(obj, dict) and "model" in obj:
        obj = obj["model"]
    return {k: (v.numpy() if isinstance(v, _Tenseur) else v) for k, v in obj.items()}


# ---------------------------------------------------------------- audio
def lire_wav(chemin):
    w = wave.open(chemin)
    sr, nc, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
    b = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(b, "<i2").astype(np.float32) / 32768.0
    elif sw == 3:
        a = np.frombuffer(b, np.uint8).reshape(-1, 3)
        x = ((a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int32) << 16)) << 8 >> 8).astype(np.float32) / 8388608.0
    elif sw == 4:
        x = np.frombuffer(b, "<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError("%s : %d octets par échantillon non gérés" % (chemin, sw))
    return x.reshape(-1, nc).mean(axis=1), sr


def reechantillonne(x, sr, cible=SR):
    """Rééchantillonnage par FFT (coupure nette à la nouvelle fréquence de Nyquist)."""
    if sr == cible:
        return x.astype(np.float32)
    n = int(round(len(x) * cible / sr))
    X = np.fft.rfft(x)
    m = n // 2 + 1
    Y = np.zeros(m, complex)
    k = min(m, len(X))
    Y[:k] = X[:k]
    return (np.fft.irfft(Y, n) * (n / len(x))).astype(np.float32)


# ---------------------------------------------------------------- réseau Cnn14
def _conv3(x, w):
    """x (C, T, F), w (O, C, 3, 3), remplissage 1, sans biais."""
    C, T, F = x.shape
    p = np.pad(x, ((0, 0), (1, 1), (1, 1)))
    cols = np.empty((C, 3, 3, T, F), np.float32)
    for i in range(3):
        for j in range(3):
            cols[:, i, j] = p[:, i:i + T, j:j + F]
    return (w.reshape(w.shape[0], -1) @ cols.reshape(C * 9, T * F)).reshape(w.shape[0], T, F)


class Cnn14:
    def __init__(self, poids):
        self.p = {k: (v.astype(np.float32) if v.dtype.kind == "f" else v) for k, v in poids.items()}
        need = ["spectrogram_extractor.stft.conv_real.weight", "logmel_extractor.melW", "fc1.weight", "fc_audioset.weight"]
        manq = [k for k in need if k not in self.p]
        if manq:
            raise ValueError("poids incomplets : %s" % manq)

    def _bn(self, x, nom, axe=0):
        p = self.p
        g = p[nom + ".weight"] / np.sqrt(p[nom + ".running_var"] + EPS_BN)
        b = p[nom + ".bias"] - p[nom + ".running_mean"] * g
        sh = [1] * x.ndim
        sh[axe] = -1
        return x * g.reshape(sh) + b.reshape(sh)

    def logmel(self, x):
        p = self.p
        wr = p["spectrogram_extractor.stft.conv_real.weight"][:, 0, :]  # (513, 1024)
        wi = p["spectrogram_extractor.stft.conv_imag.weight"][:, 0, :]
        n = wr.shape[1]
        x = np.pad(x, (n // 2, n // 2), mode="reflect")
        T = 1 + (len(x) - n) // 320
        trames = np.lib.stride_tricks.as_strided(x, shape=(T, n), strides=(x.strides[0] * 320, x.strides[0]))
        re, im = trames @ wr.T, trames @ wi.T
        mel = (re * re + im * im) @ p["logmel_extractor.melW"]  # (T, 64)
        return 10.0 * np.log10(np.maximum(mel, 1e-10)).astype(np.float32)

    def __call__(self, x):
        """x : signal mono 32 kHz. Rend (empreinte 2048, probabilités 527)."""
        m = self.logmel(np.asarray(x, np.float32))
        h = self._bn(m, "bn0", axe=1)[None]  # (1, T, 64) : bn0 agit sur les 64 bandes
        for b in range(1, 7):
            k = "conv_block%d" % b
            h = np.maximum(self._bn(_conv3(h, self.p[k + ".conv1.weight"]), k + ".bn1"), 0)
            h = np.maximum(self._bn(_conv3(h, self.p[k + ".conv2.weight"]), k + ".bn2"), 0)
            if b < 6:
                C, T, F = h.shape
                h = h[:, :T // 2 * 2, :F // 2 * 2].reshape(C, T // 2, 2, F // 2, 2).mean(axis=(2, 4))
        h = h.mean(axis=2)  # fréquence
        h = h.max(axis=1) + h.mean(axis=1)  # temps
        e = np.maximum(self.p["fc1.weight"] @ h + self.p["fc1.bias"], 0)
        z = self.p["fc_audioset.weight"] @ e + self.p["fc_audioset.bias"]
        return e, 1.0 / (1.0 + np.exp(-z))


def charger(chemin, verifier_md5=True):
    if verifier_md5:
        h = hashlib.md5()
        with open(chemin, "rb") as f:
            for bloc in iter(lambda: f.read(1 << 20), b""):
                h.update(bloc)
        if h.hexdigest() != MD5_POIDS:
            raise ValueError("empreinte md5 inattendue : %s (attendu %s)" % (h.hexdigest(), MD5_POIDS))
    return Cnn14(lire_pth(chemin))


def empreinte(modele, x, sr, fenetre_s=4.0, pas_s=2.0):
    """Empreintes sur des fenêtres glissantes (même durée pour tous : comparer à contenu semblable)."""
    x = reechantillonne(x, sr)
    L, P = int(fenetre_s * SR), int(pas_s * SR)
    if len(x) < L:
        x = np.pad(x, (0, L - len(x)))
    E, Pr = [], []
    for d in range(0, len(x) - L + 1, P):
        e, p = modele(x[d:d + L])
        E.append(e)
        Pr.append(p)
    return np.array(E), np.array(Pr)


def distance(EA, EB):
    """Distance cosinus moyenne entre deux jeux d'empreintes (0 = identique, 1 = sans rapport)."""
    a = EA / (np.linalg.norm(EA, axis=1, keepdims=True) + 1e-9)
    b = EB / (np.linalg.norm(EB, axis=1, keepdims=True) + 1e-9)
    return float(1.0 - (a @ b.T).mean())


if __name__ == "__main__":
    mod = charger(sys.argv[1])
    for f in sys.argv[2:]:
        x, sr = lire_wav(f)
        E, P = empreinte(mod, x, sr)
        top = np.argsort(-P.mean(axis=0))[:5]
        print(os.path.basename(f), "fenêtres", len(E), "top", [(int(i), round(float(P.mean(axis=0)[i]), 3)) for i in top])
