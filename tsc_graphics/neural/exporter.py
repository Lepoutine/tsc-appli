# TSC Neural - ecrit les poids appris dans tsc-graphics.hlsl (bloc entre // <<TSC_NEURAL>> et // <</TSC_NEURAL>>).
# Le plugin recharge le HLSL a chaud : pas de relance du jeu. Usage : python exporter.py modele.pt tsc-graphics.hlsl sortie.hlsl
import re, sys
import torch
from caracteristiques import RAYONS, N_ENTREES, N_GUIDE
from modele import TSCNeural, DELTA_MAX


def f(x):
    return f"{float(x):.6g}"


def code_hlsl(m):
    w1 = m.c1.weight.detach().cpu().view(m.c1.out_channels, -1); b1 = m.c1.bias.detach().cpu()
    w2 = m.c2.weight.detach().cpu().view(m.c2.out_channels, -1); b2 = m.c2.bias.detach().cpu()
    w3 = m.c3.weight.detach().cpu().view(3, -1); b3 = m.c3.bias.detach().cpu()
    H = w1.shape[0]
    NE = N_ENTREES + (N_GUIDE if getattr(m, "guide", False) else 0)
    L = []
    tab = lambda nom, t: L.append(f"static const float {nom}[{t.numel()}] = {{{', '.join(f(v) for v in t.flatten())}}};")
    tab("NW1", w1); tab("NB1", b1); tab("NW2", w2); tab("NB2", b2); tab("NW3", w3); tab("NB3", b3)
    L.append("float3 neural_ldr(float2 uv, float3 c) {")
    L.append(f"\tfloat x[{NE}];")
    L.append("\tfloat3 e = srgb_enc3(c); x[0] = e.r; x[1] = e.g; x[2] = e.b;")
    for k, r in enumerate(RAYONS):
        i = 3 + 3 * k
        L.append(f"\t{{ float3 m = (nl_tap(uv, {r}, {r}) + nl_tap(uv, -{r}, {r}) + nl_tap(uv, {r}, -{r}) + nl_tap(uv, -{r}, -{r})) * 0.25; x[{i}] = m.r; x[{i + 1}] = m.g; x[{i + 2}] = m.b; }}")
    L.append(f"\tx[{N_ENTREES - 1}] = uv.y;")
    if NE > N_ENTREES:   # v0.7 / plugin 0.18 : canaux du G-buffer de la vue (t1 profondeur, t2 albedo), p11.z/w = presents
        g = N_ENTREES
        L.append("\t{ float3 al = p11.z > 0.5 ? srgb_enc3(saturate(tGb2.SampleLevel(sPt, uv, 0).rgb)) : 0; float ci = 0, cb = 0, df = 0;")
        L.append("\t  if (p11.w > 0.5) { float dp = tProf.SampleLevel(sPt, uv, 0); ci = ciel(dp) ? 1 : 0; cb = cabine(dp) ? 1 : 0; df = ci > 0 ? 1 : (cb > 0 ? 0 : saturate(log2(1 + lineaire(dp)) / 10)); }")
        L.append(f"\t  x[{g}] = al.r; x[{g + 1}] = al.g; x[{g + 2}] = al.b; x[{g + 3}] = df; x[{g + 4}] = ci; x[{g + 5}] = cb; }}")
    L.append(f"\tfloat h1[{H}], h2[{H}];")
    L.append(f"\t[unroll] for (int j = 0; j < {H}; j++) {{ float s = NB1[j]; [unroll] for (int k = 0; k < {NE}; k++) s += NW1[j * {NE} + k] * x[k]; h1[j] = max(s, 0); }}")
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
    sd = torch.load(sys.argv[1], map_location="cpu", weights_only=True)["modele"]
    m = TSCNeural(cache=sd["c1.weight"].shape[0], guide=sd["c1.weight"].shape[1] > N_ENTREES); m.load_state_dict(sd)
    ecrire(m, sys.argv[2], sys.argv[3])
    print("HLSL ecrit :", sys.argv[3])
