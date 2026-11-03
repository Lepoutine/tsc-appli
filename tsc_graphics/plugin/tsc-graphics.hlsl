// TSC Neural Graphics 0.1 : passe temps reel appliquee a chaque image dans ETS2 (recharge a chaud par le plugin).
// Copyright (c) 2026 Truck So Clean France.
// Entrees : t0 = image du jeu (copie), t1 = profondeur du jeu (copie). Tout est recalcule a chaque image depuis la
// profondeur reelle : les reflets suivent la camera, les vehicules et les lumieres.
Texture2D tCouleur : register(t0);
Texture2D<float> tProf : register(t1);
SamplerState sLin : register(s0);
SamplerState sPt : register(s1);
cbuffer P : register(b0) {
	float4 p0; // vue (0 normale, 1 profondeur, 2 normales, 3 masque), humidite, tan(fov_v/2), rapport l/h d'un ecran
	float4 p1; // proche, loin, z inverse (1/0), temps
	float4 p2; // largeur, hauteur, 1/largeur, 1/hauteur
	float4 p3; // intensite, rugosite, profondeur disponible, trainees
	float4 p4; // distance cabine (m), pas de marche (m), epaisseur (m), f0
	float4 p5; // nombre d'ecrans, assombrissement de l'asphalte mouille
};
struct VSO { float4 pos : SV_Position; float2 uv : TEXCOORD0; };
VSO vs_principal(uint id : SV_VertexID) {
	VSO o; float2 uv = float2((id << 1) & 2, id & 2);
	o.uv = uv; o.pos = float4(uv * float2(2, -2) + float2(-1, 1), 0, 1); return o;
}
// --- geometrie reconstruite depuis la profondeur (par ecran si plusieurs ecrans cote a cote) ---
float nEcr() { return max(p5.x, 1); }
float2 local(float2 uv, out float off) { float n = nEcr(); float k = min(floor(uv.x * n), n - 1); off = k / n; return float2((uv.x - off) * n, uv.y); }
float lineaire(float d) {
	float n = p1.x, f = p1.y;
	if (p1.z > 0.5) d = 1 - d;
	return n * f / max(f - d * (f - n), 1e-6);
}
float3 posVue(float2 uv) {
	float off; float2 l = local(uv, off);
	float z = lineaire(tProf.SampleLevel(sPt, uv, 0));
	float2 ndc = l * float2(2, -2) + float2(-1, 1);
	return float3(ndc.x * p0.z * p0.w * z, ndc.y * p0.z * z, z);
}
float2 versUV(float3 v, float off) {
	float2 ndc = float2(v.x / (v.z * p0.z * p0.w), v.y / (v.z * p0.z));
	float2 l = ndc * float2(0.5, -0.5) + 0.5;
	return float2(l.x / nEcr() + off, l.y);
}
float3 normale(float2 uv, float3 c) {
	float2 t = p2.zw;
	float3 r = posVue(uv + float2(t.x, 0)), l = posVue(uv - float2(t.x, 0));
	float3 u = posVue(uv - float2(0, t.y)), b = posVue(uv + float2(0, t.y));
	float3 dx = abs(r.z - c.z) < abs(c.z - l.z) ? r - c : c - l;
	float3 dy = abs(b.z - c.z) < abs(c.z - u.z) ? b - c : c - u;
	return normalize(cross(dx, dy));   // sol : vers le haut (+y)
}
float bruit(float2 p) { return frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453); }

float4 ps_principal(VSO i) : SV_Target {
	float3 col = tCouleur.SampleLevel(sPt, i.uv, 0).rgb;
	if (p3.z < 0.5) return float4(col, 1);   // pas de profondeur : image du jeu intacte
	int vue = (int)p0.x;
	float3 P = posVue(i.uv);
	float3 N = normale(i.uv, P);
	if (vue == 1) { float z = P.z; return float4(lerp(float3(1, 0.9, 0.2), float3(0.1, 0.2, 1), saturate(log2(z) / 10)) * (0.6 + 0.4 * frac(log2(z))), 1); }
	if (vue == 2) return float4(N * 0.5 + 0.5, 1);
	// surface mouillable : orientee vers le haut, au-dela de la cabine, pas le ciel
	float haut = saturate((N.y - 0.80) * 6);
	float dehors = saturate((P.z - p4.x) / 1.5) * (P.z < p1.y * 0.9 ? 1 : 0);
	float mouille = haut * dehors * p0.y;
	if (vue == 3) return float4(lerp(col, float3(0, 0.45, 1), mouille * 0.8), 1);
	if (mouille < 0.01) return float4(col, 1);

	float off; local(i.uv, off);
	float3 V = normalize(P);
	// rugosite de l'asphalte : normale perturbee, davantage dans l'axe de la route (trainees des lumieres)
	float2 px = i.uv * p2.xy;
	float h1 = bruit(px), h2 = bruit(px * 1.37 + 17.0);
	float3 Nr = normalize(N + float3((h1 - 0.5) * p3.y * 0.25, 0, (h2 - 0.5) * p3.y * p3.w));
	float3 R = reflect(V, Nr);
	// marche du rayon dans l'espace de la camera, contre la profondeur reelle
	float3 pos = P + N * 0.02; float pas = p4.y; float3 refl = 0; float touche = 0;
	[loop] for (int k = 0; k < 56; k++) {
		pos += R * pas; pas *= 1.07;
		if (pos.z < p1.x) break;
		float2 uv = versUV(pos, off);
		if (uv.x < off || uv.x > off + 1 / nEcr() || uv.y < 0 || uv.y > 1) break;
		float zs = lineaire(tProf.SampleLevel(sPt, uv, 0));
		float dz = pos.z - zs;
		if (dz > 0 && dz < p4.z + pas) {
			// affinage
			float3 a = pos - R * pas, b = pos;
			[unroll] for (int j = 0; j < 5; j++) { float3 m = (a + b) * 0.5; float2 um = versUV(m, off); if (m.z - lineaire(tProf.SampleLevel(sPt, um, 0)) > 0) b = m; else a = m; }
			uv = versUV(b, off);
			refl = tCouleur.SampleLevel(sLin, uv, 0).rgb;
			float2 e = abs((uv - float2(off + 0.5 / nEcr(), 0.5)) * float2(2 * nEcr(), 2));
			touche = saturate(1 - pow(max(e.x, e.y), 8)) * saturate(1 - k / 56.0);
			break;
		}
	}
	float cosv = saturate(dot(-V, N));
	float F = p4.w + (1 - p4.w) * pow(1 - cosv, 5);
	float3 base = col * (1 - p5.y * mouille);                      // asphalte mouille plus sombre
	float3 res = base + refl * touche * F * mouille * p3.x;        // + reflet de la scene reelle (phares, feux, lampadaires)
	return float4(res, 1);
}
