// TSC Neural Graphics 0.2 : passe temps reel sur chaque vue d'ETS2, dans la cible HDR, avant exposition, tone mapping et
// interface (recharge a chaud par le plugin). Copyright (c) 2026 Truck So Clean France.
// t0 = copie HDR de la vue (RGBA16F, lumieres non ecretees), t1 = copie de sa profondeur (D32 en Z inverse).
// Le resultat remplace la cible HDR du jeu ; tout est recalcule a chaque image depuis la profondeur reelle.
Texture2D tCouleur : register(t0);
Texture2D<float> tProf : register(t1);
SamplerState sLin : register(s0);
SamplerState sPt : register(s1);
cbuffer P : register(b0) {
	float4 p0; // vue de controle (0..3), humidite 0..1, tan(fov_v/2), largeur/hauteur
	float4 p1; // plan proche (m), debut et fin de la plage du monde dans la profondeur (cabine au-dela), temps
	float4 p2; // largeur, hauteur, 1/largeur, 1/hauteur
	float4 p3; // intensite, rugosite, -, trainees
	float4 p4; // -, pas de marche (m), epaisseur (m), f0
	float4 p5; // index de la vue, assombrissement de l'asphalte mouille
};
struct VSO { float4 pos : SV_Position; float2 uv : TEXCOORD0; };
VSO vs_principal(uint id : SV_VertexID) {
	VSO o; float2 uv = float2((id << 1) & 2, id & 2);
	o.uv = uv; o.pos = float4(uv * float2(2, -2) + float2(-1, 1), 0, 1); return o;
}
// Z inverse a plan lointain infini, ramene a la plage du monde : z = proche / ndc
bool cabine(float d) { return d > p1.z; }
bool ciel(float d) { return d <= 1e-7; }
float lineaire(float d) {
	float ndc = saturate((d - p1.y) / max(p1.z - p1.y, 1e-6));
	return p1.x / max(ndc, 1e-7);
}
float3 posVue(float2 uv) {
	float z = lineaire(tProf.SampleLevel(sPt, uv, 0));
	float2 ndc = uv * float2(2, -2) + float2(-1, 1);
	return float3(ndc.x * p0.z * p0.w * z, ndc.y * p0.z * z, z);
}
float2 versUV(float3 v) {
	float2 ndc = float2(v.x / (v.z * p0.z * p0.w), v.y / (v.z * p0.z));
	return ndc * float2(0.5, -0.5) + 0.5;
}
float3 normale(float2 uv, float3 c) {
	float2 t = p2.zw;
	float3 r = posVue(uv + float2(t.x, 0)), l = posVue(uv - float2(t.x, 0));
	float3 u = posVue(uv - float2(0, t.y)), b = posVue(uv + float2(0, t.y));
	float3 dx = abs(r.z - c.z) < abs(c.z - l.z) ? r - c : c - l;
	float3 dy = abs(b.z - c.z) < abs(c.z - u.z) ? b - c : c - u;
	return normalize(cross(dx, dy));
}
// bruit stable a l'ecran (pas de scintillement d'une image a l'autre) ; motif entrelace pour casser les bandes
float bruit(float2 p) { return frac(52.9829189 * frac(dot(p, float2(0.06711056, 0.00583715)))); }

float4 ps_principal(VSO i) : SV_Target {
	float4 src = tCouleur.SampleLevel(sPt, i.uv, 0);
	float3 col = src.rgb;
	int vue = (int)p0.x;
	float d = tProf.SampleLevel(sPt, i.uv, 0);
	if (vue == 1) {
		if (ciel(d)) return float4(0.2, 0.4, 1, 1);
		if (cabine(d)) return float4(1, 0.3, 0.1, 1);
		float z = lineaire(d); return float4(lerp(float3(1, 0.9, 0.2), float3(0.1, 0.9, 0.3), saturate(log2(z) / 9)) * (0.5 + 0.5 * frac(log2(z))), 1);
	}
	if (ciel(d) || cabine(d)) return src;
	float3 P = posVue(i.uv);
	float3 N = normale(i.uv, P);
	if (vue == 2) return float4(N * 0.5 + 0.5, 1);
	// surface mouillable : orientee vers le haut (route, trottoir, parking)
	float haut = saturate((N.y - 0.82) * 6);
	float mouille = haut * p0.y;
	if (vue == 3) return float4(lerp(col, float3(0, 0.45, 1) * max(dot(col, float3(0.33, 0.33, 0.33)), 0.05) * 3, mouille * 0.8), src.a);
	if (mouille < 0.01) return src;

	float3 V = normalize(P);
	float2 px = i.uv * p2.xy;
	float h1 = bruit(px), h2 = bruit(px + float2(37, 11));
	// rugosite de l'asphalte : normale perturbee, surtout dans l'axe de la route (trainees des lumieres)
	float3 Nr = normalize(N + float3((h1 - 0.5) * p3.y * 0.3, 0, (h2 - 0.5) * p3.y * p3.w));
	float3 R = reflect(V, Nr);
	float3 pos = P + N * 0.03;
	float pas = p4.y * (0.5 + h1);       // depart decale par pixel : pas de « traits multiplies »
	float3 refl = 0; float poids = 0;
	[loop] for (int k = 0; k < 64; k++) {
		pos += R * pas; pas *= 1.06;
		if (pos.z < p1.x) break;
		float2 uv = versUV(pos);
		if (any(uv < 0) || any(uv > 1)) break;
		float ds = tProf.SampleLevel(sPt, uv, 0);
		if (cabine(ds)) continue;                         // la cabine ne se reflete pas dans la route
		float zs = ciel(ds) ? 1e9 : lineaire(ds);
		float dz = pos.z - zs;
		if (dz > 0 && dz < p4.z + pas * 2) {
			float3 a = pos - R * pas, b = pos;
			[unroll] for (int j = 0; j < 6; j++) { float3 m = (a + b) * 0.5; float dm = tProf.SampleLevel(sPt, versUV(m), 0); if (m.z - (ciel(dm) ? 1e9 : lineaire(dm)) > 0) b = m; else a = m; }
			uv = versUV(b);
			refl = tCouleur.SampleLevel(sLin, uv, 0).rgb;
			float2 e = abs(uv - 0.5) * 2;
			poids = saturate(1 - pow(max(e.x, e.y), 6)) * saturate(1.2 - k / 64.0);
			break;
		}
	}
	// rayon parti vers le ciel sans rien toucher : reflet du ciel (premier pixel de ciel au-dessus, meme colonne)
	if (poids == 0 && R.y > 0) {
		[loop] for (int s = 1; s <= 16; s++) { float2 u2 = float2(i.uv.x, i.uv.y * (1 - s / 16.0)); if (ciel(tProf.SampleLevel(sPt, u2, 0))) { refl = tCouleur.SampleLevel(sLin, u2, 0).rgb; poids = 0.5; break; } }
	}
	float cosv = saturate(dot(-V, N));
	float F = p4.w + (1 - p4.w) * pow(1 - cosv, 5);
	float3 base = col * (1 - p5.y * mouille);
	float3 res = base + refl * poids * F * mouille * p3.x;
	return float4(res, src.a);
}
