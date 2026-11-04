# Tests de non-regression TSC Neural (cycle QA Virtuoso : test unitaire + regression avant toute livraison).
# Lancer : python -m pytest tsc_graphics/tests  (ou python tsc_graphics/tests/test_neural.py)
# 1. parite Python <-> HLSL : le bloc exporte est relu et execute en numpy avec les MEMES indices que la boucle HLSL ;
#    il doit redonner la sortie du reseau torch (sinon le jeu ne montre pas ce que l'entrainement a mesure).
# 2. detail garde : sans correction (depart), l'image du jeu ressort identique ; le detail fin (e - flou3) passe tel quel.
# 3. guide : formule distance/ciel/cabine identique a lineaire()/ciel()/cabine() du HLSL.
# 4. le HLSL du depot compile (glslangValidator) avec un bloc guide exporte.
import os, re, shutil, subprocess, sys, tempfile
import numpy as np
import torch

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "neural"))
from caracteristiques import RAYONS, N_ENTREES, N_GUIDE, PROCHE, PLAGE_MIN, PLAGE_MAX, DECALAGE_Z, guide_depuis, flou3, srgb_enc  # noqa
from modele import TSCNeural, DELTA_MAX  # noqa
import exporter  # noqa

HLSL = os.path.join(ICI, "..", "plugin", "tsc-graphics.hlsl")


def reseau(guide, graine=1):
    torch.manual_seed(graine)
    m = TSCNeural(guide=guide)
    with torch.no_grad():
        for c in (m.c1, m.c2, m.c3):
            c.weight.normal_(0, 0.4); c.bias.normal_(0, 0.1)
    return m.eval()


def tableaux(code):
    t = {}
    for nom, val in re.findall(r"static const float (\w+)\[\d+\] = \{([^}]*)\};", code):
        t[nom] = np.array([float(v) for v in val.split(",")], dtype=np.float64)
    return t


def emule_hlsl(code, x):
    """x : (NE,) entrees deja calculees -> delta (3,), boucles exactement comme le HLSL emis."""
    t = tableaux(code); NE = x.size; H = t["NB1"].size
    h1 = np.array([max(t["NB1"][j] + sum(t["NW1"][j * NE + k] * x[k] for k in range(NE)), 0) for j in range(H)])
    h2 = np.array([max(t["NB2"][j] + sum(t["NW2"][j * H + k] * h1[k] for k in range(H)), 0) for j in range(H)])
    return np.array([np.tanh(t["NB3"][o] + sum(t["NW3"][o * H + k] * h2[k] for k in range(H))) * DELTA_MAX for o in range(3)])


def _parite(guide):
    m = reseau(guide)
    m.detail_garde = False   # on compare le reseau seul (la recomposition est testee a part)
    code = exporter.code_hlsl(m)
    torch.manual_seed(2)
    e = torch.rand(1, 3, 40, 40)
    g = guide_depuis(np.random.RandomState(3).uniform(0, 1, (40, 40)).astype(np.float32),
                     np.random.RandomState(4).uniform(0, 1, (40, 40, 3)).astype(np.float32))[None] if guide else None
    from caracteristiques import caracteristiques
    f = caracteristiques(e, None, g)[0]
    with torch.no_grad():
        sortie = m(torch.cat([e, g], 1) if guide else e)[0]
    for (y, x) in [(0, 0), (20, 20), (39, 5), (7, 33)]:
        d = emule_hlsl(code, f[:, y, x].double().numpy())
        attendu = np.clip(e[0, :, y, x].double().numpy() + d, 0, 1)
        assert np.abs(attendu - sortie[:, y, x].double().numpy()).max() < 1e-5, (guide, y, x)
    assert f"float x[{N_ENTREES + (N_GUIDE if guide else 0)}]" in code


def test_parite_sans_guide():
    _parite(False)


def test_parite_guide():
    _parite(True)


def test_depart_identite_et_detail_garde():
    m = TSCNeural(guide=True).eval()   # c3 a zero = image du jeu inchangee
    torch.manual_seed(5)
    e = torch.rand(1, 3, 32, 32); g = torch.rand(1, 6, 32, 32)
    with torch.no_grad():
        s = m(torch.cat([e, g], 1))
    assert torch.allclose(s, e, atol=1e-6)
    m2 = reseau(False)
    with torch.no_grad():
        s2 = m2(e)
    hp = lambda x: x - flou3(x)
    # le passe-haut fin du jeu survit (hors pixels satures par le clamp)
    ok = (s2 > 0.01) & (s2 < 0.99)
    assert (hp(s2) - hp(e))[ok].abs().mean() < 0.15


def test_guide_formule_hlsl():
    d = np.array([[0.0, 1e-8, 0.02, 0.5], [0.89, 0.95, 0.3, 0.1]], dtype=np.float32)
    g = guide_depuis(d, None).numpy()
    for (y, x), v in np.ndenumerate(d):
        ci = v <= 1e-7; cb = v > PLAGE_MAX
        ndc = (v - PLAGE_MIN) / max(PLAGE_MAX - PLAGE_MIN, 1e-6) - DECALAGE_Z
        lin = PROCHE / max(ndc, 1e-7)
        df = 1.0 if ci else (0.0 if cb else min(max(np.log2(1 + lin) / 10, 0), 1))
        assert abs(g[3, y, x] - df) < 1e-5 and g[4, y, x] == ci and g[5, y, x] == cb


def test_hlsl_depot_compile_avec_guide():
    if not shutil.which("glslangValidator"):
        return
    with tempfile.TemporaryDirectory() as tmp:
        sortie = os.path.join(tmp, "t.hlsl")
        exporter.ecrire(reseau(True), HLSL, sortie, "test")
        for ep in ("ps_ldr", "ps_principal"):
            r = subprocess.run(["glslangValidator", "-D", "-V", "-S", "frag", "-e", ep, "-o", os.path.join(tmp, ep + ".spv"), sortie], capture_output=True, text=True)
            assert r.returncode == 0, r.stdout[-800:]


def test_juge_vision_gele_et_gradient():
    try:
        import timm  # noqa
    except ImportError:
        return
    import juge_vision as jv
    J = jv.JugeVision()
    x = torch.rand(2, 3, 96, 96, requires_grad=True)
    jv.perte_generateur(J, x).backward()
    assert x.grad.abs().sum() > 0                                  # le reseau TSC recoit bien un signal du juge
    assert all(q.grad is None for q in J.dino.parameters())        # DINOv2 n'est jamais modifie
    J.train(); assert not J.dino.training


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_"):
            fn(); print("OK", n)
