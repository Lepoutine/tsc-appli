# TSC Neural - ecrit les poids appris dans tsc-graphics.hlsl (bloc entre // <<TSC_NEURAL>> et // <</TSC_NEURAL>>).
# Le plugin recharge le HLSL a chaud : pas de relance du jeu. Usage : python exporter.py modele.pt tsc-graphics.hlsl sortie.hlsl
import re, sys
import torch
from caracteristiques import RAYONS, N_ENTREES
from modele import TSCNeural, DELTA_MAX


def f(x):
    return f"{float(x):.6g}"


def code_hlsl(m):
    w1 = m.c1.weight.detach().cpu().view(m.c1.out_channels, -1); b1 = m.c1.bias.detach().cpu()
    w2 = m.c2.weight.detach().cpu().view(m.c2.out_channels, -1); b2 = m.c2.bias.detach().cpu()
    w3 = m.c3.weight.detach().cpu().view(3, -1); b3 = m.c3.bias.detach().cpu()
    H = w1.shape[0]
    L = []
    tab = lambda nom, t: L.append(f"static const float {nom}[{t.numel()}] = {{{', '.join(f(v) for v in t.flatten())}}};")
    tab("NW1", w1); tab("NB1", b1); tab("NW2", w2); tab("NB2", b2); tab("NW3", w3); tab("NB3", b3)
    L.append("float3 neural_ldr(float2 uv, float3 c) {")
    L.append(f"\tfloat x[{N_ENTREES}];")
    L.append("\tfloat3 e = srgb_enc3(c); x[0] = e.r; x[1] = e.g; x[2] = e.b;")
    for k, r in enumerate(RAYONS):
        i = 3 + 3 * k
        L.append(f"\t{{ float3 m = (nl_tap(uv, {r}, {r}) + nl_tap(uv, -{r}, {r}) + nl_tap(uv, {r}, -{r}) + nl_tap(uv, -{r}, -{r})) * 0.25; x[{i}] = m.r; x[{i + 1}] = m.g; x[{i + 2}] = m.b; }}")
    L.append(f"\tx[{N_ENTREES - 1}] = uv.y;")
    L.append(f"\tfloat h1[{H}], h2[{H}];")
    L.append(f"\t[unroll] for (int j = 0; j < {H}; j++) {{ float s = NB1[j]; [unroll] for (int k = 0; k < {N_ENTREES}; k++) s += NW1[j * {N_ENTREES} + k] * x[k]; h1[j] = max(s, 0); }}")
    L.append(f"\t[unroll] for (int j2 = 0; j2 < {H}; j2++) {{ float s = NB2[j2]; [unroll] for (int k = 0; k < {H}; k++) s += NW2[j2 * {H} + k] * h1[k]; h2[j2] = max(s, 0); }}")
    L.append("\tfloat3 d;")
    L.append(f"\t[unroll] for (int o = 0; o < 3; o++) {{ float s = NB3[o]; [unroll] for (int k = 0; k < {H}; k++) s += NW3[o * {H} + k] * h2[k]; d[o] = tanh(s) * {f(DELTA_MAX)}; }}")
    L.append("\treturn srgb_dec3(saturate(e + d));")
    L.append("}")
    return "\n".join(L)


def ecrire(m, hlsl_entree, hlsl_sortie, note=""):
    s = open(hlsl_entree, encoding="utf-8").read()
    debut, fin = "// <<TSC_NEURAL>>\n", "// <</TSC_NEURAL>>"
    if s.count(debut) != 1 or s.count(fin) != 1:
        raise SystemExit("marqueurs TSC_NEURAL absents du HLSL (version 0.16 ou plus recente requise)")
    a = s.index(debut) + len(debut); b = s.index(fin)
    bloc = (f"// reseau TSC Neural {note}\n" if note else "") + code_hlsl(m) + "\n"
    s = s[:a] + bloc + s[b:]
    with open(hlsl_sortie, "w", encoding="utf-8", newline="\n") as fo:
        fo.write(s)


if __name__ == "__main__":
    m = TSCNeural(); m.load_state_dict(torch.load(sys.argv[1], map_location="cpu", weights_only=True)["modele"])
    ecrire(m, sys.argv[2], sys.argv[3])
    print("HLSL ecrit :", sys.argv[3])
