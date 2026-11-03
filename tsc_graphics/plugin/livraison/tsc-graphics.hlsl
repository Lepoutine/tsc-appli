// TSC Neural Graphics 0.4.3 « route mouillee v1 » : passe temps reel sur chaque vue d'ETS2, dans la cible HDR, avant exposition, tone mapping et
// interface (recharge a chaud par le plugin). Copyright (c) 2026 Truck So Clean France.
// t0 = copie HDR de la vue (RGBA16F, lumieres non ecretees), t1 = copie de sa profondeur (D32 en Z inverse).
// Le resultat remplace la cible HDR du jeu ; tout est recalcule a chaque image depuis la profondeur reelle.
Texture2D tCouleur : register(t0);
Texture2D<float> tProf : register(t1);
SamplerState sLin : register(s0);
SamplerState sPt : register(s1);
cbuffer P : register(b0) {
	float4 p0; // vue de controle (0..3), humidite 0..1, tan(fov_v/2), largeur/hauteur
	float4 p1; // plan proche (m), debut et fin de la plage du monde dans la profondeur (cabine au-dela), decalage z
	float4 p2; // largeur, hauteur, 1/largeur, 1/hauteur
	float4 p3; // intensite, rugosite, flou (largeur du lobe brillant), trainees (bruit d'axe)
	float4 p4; // etirement vertical des reflets, pas de marche (m), epaisseur (m), f0
	float4 p5; // index de la vue, assombrissement de l'asphalte mouille, attenuation sur la peinture, dernier niveau de mip
};
struct VSO { float4 pos : SV_Position; float2 uv : TEXCOORD0; };
VSO vs_principal(uint id : SV_VertexID) {
	VSO o; float2 uv = float2((id << 1) & 2, id & 2);
	o.uv = uv; o.pos = float4(uv * float2(2, -2) + float2(-1, 1), 0, 1); return o;
}
// Projection du jeu relevee par l'audit (socle v0.4) : P00 2,1445, P11 2,5416 (43 deg vertical), ndc_z = decalage + 0,2 / z
// (Z inverse, plan lointain infini), ecrite dans la plage du viewport du monde (0,01-0,9) ; la cabine utilise 0,9-1.
// Decalage mesure le 03/11 sur un vidage reel (profondeur D32 contre distance du G-buffer, 614 000 pixels) : -0,000194.
bool cabine(float d) { return d > p1.z; }
bool ciel(float d) { return d <= 1e-7; }
float lineaire(float d) {
	float ndc = (d - p1.y) / max(p1.z - p1.y, 1e-6) - p1.w;
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
	if (any(isnan(col)) || any(isinf(col))) return src;
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
	// Calage sur les videos reelles (nuit et pluie, Norvege) : la route mouillee n'est pas un miroir. Les lumieres s'y
	// etirent en colonnes verticales douces vers le conducteur, d'autant plus longues que la surface est loin ; les
	// immeubles et les arbres n'y laissent qu'une trace floue ; au loin la route prend un voile clair (ciel, Fresnel) ;
	// les marquages restent mats. On garde donc le rayon reflechi (position physique du reflet), mais on lit la couleur
	// touchee dans une version floutee de l'image (mips) dont le flou grandit avec la distance parcourue par le rayon.
	float3 Nr = normalize(N + float3((h1 - 0.5) * p3.y * 0.15, 0, (h2 - 0.5) * p3.y * p3.w * 0.3));
	float3 R = reflect(V, Nr);
	float3 pos = P + N * 0.03;
	float pas = p4.y * (0.5 + h1);       // depart decale par pixel : pas de « traits multiplies »
	float3 refl = 0; float poids = 0; float2 libre = -1;
	[loop] for (int k = 0; k < 64; k++) {
		pos += R * pas; pas *= 1.06;
		if (pos.z < p1.x) break;
		float2 uv = versUV(pos);
		if (any(uv < 0) || any(uv > 1)) break;
		float ds = tProf.SampleLevel(sPt, uv, 0);
		if (cabine(ds)) continue;                         // la cabine ne se reflete pas dans la route
		float zs = ciel(ds) ? 1e9 : lineaire(ds);
		float dz = pos.z - zs;
		if (dz <= 0) libre = uv;                          // point du rayon encore visible
		if (dz > 0 && dz < p4.z + pas * 2) {
			float3 a = pos - R * pas, b = pos;
			[unroll] for (int j = 0; j < 6; j++) { float3 m = (a + b) * 0.5; float dm = tProf.SampleLevel(sPt, versUV(m), 0); if (m.z - (ciel(dm) ? 1e9 : lineaire(dm)) > 0) b = m; else a = m; }
			uv = versUV(b);
			// largeur du lobe brillant a l'endroit touche, en pixels : rugosite x longueur du rayon, projetee a l'ecran
			float l = length(b - P);
			float pxm = p2.y / (2 * p0.z * max(b.z, p1.x));          // pixels par metre a la distance touchee
			float lobe = max(1, p3.z * p3.y * l * pxm);
			float lod = clamp(log2(lobe), 0, p5.w);
			// etirement vertical : plus fort en regard rasant (cosv petit), comme sur les videos
			float cosv0 = saturate(dot(-V, N));
			float ext = min(p4.x * lobe * p2.w / (cosv0 + 0.15), 0.06);   // videos : colonnes jusqu'a ~11 % de la hauteur
			float3 acc = 0; float wt = 0;
			[unroll] for (int t = -3; t <= 3; t++) {
				float o = t / 3.0; float2 ut = uv + float2(0, o * ext);
				float dt = tProf.SampleLevel(sPt, ut, 0), zt = ciel(dt) ? 1e9 : lineaire(dt);
				float w = exp(-o * o * 2) * exp(-abs(zt - b.z) / (0.03 * b.z));   // pas de fuite a travers les silhouettes
				acc += tCouleur.SampleLevel(sLin, ut, lod).rgb * w; wt += w;
			}
			refl = acc / max(wt, 1e-6);
			float2 e = abs(uv - 0.5) * 2;
			poids = saturate(1 - pow(max(e.x, e.y), 6)) * saturate(1.2 - k / 64.0);
			break;
		}
	}
	// rayon sorti de l'image sans impact : dernier point encore visible, poids 0,35 (jamais un point cache)
	if (poids == 0 && libre.x >= 0) { refl = tCouleur.SampleLevel(sLin, libre, max(p5.w - 1, 0)).rgb; poids = 0.35; }
	// rayon parti vers le ciel sans rien toucher : voile du ciel, tres flou (premier pixel de ciel au-dessus, meme colonne)
	if (poids == 0 && R.y > 0) {
		[loop] for (int s = 1; s <= 16; s++) { float2 u2 = float2(i.uv.x, i.uv.y * (1 - s / 16.0)); if (ciel(tProf.SampleLevel(sPt, u2, 0))) { refl = tCouleur.SampleLevel(sLin, u2, p5.w).rgb; poids = 0.6; break; } }
	}
	float cosv = saturate(dot(-V, N));
	float F = p4.w + (1 - p4.w) * pow(1 - cosv, 5);
	// marquages au sol : plus clairs que l'asphalte autour (niveau de mip 3) -> peinture, reflet attenue
	float lc = dot(col, float3(0.2126, 0.7152, 0.0722));
	float lm = dot(tCouleur.SampleLevel(sLin, i.uv, min(3, p5.w)).rgb, float3(0.2126, 0.7152, 0.0722));
	float peinture = saturate((lc / max(lm, 1e-4) - 1.3) * 2.5);
	float spec = mouille * (1 - p5.z * peinture) * saturate(1 - (P.z - 150) / 150);   // fondu de 150 a 300 m
	// asphalte mouille : plus sombre et un peu plus sature (l'eau remplit les pores)
	float3 base = col * (1 - p5.y * mouille * (1 - 0.6 * peinture));
	float gris = lc * (1 - p5.y * mouille);
	base = max(0, lerp(float3(gris, gris, gris), base, 1 + 0.15 * mouille));
	// 0.4.2 (test T1b) : taches bleues/violettes = valeurs HDR invalides (NaN/infini) propagees par les mips ou lues
	// sur les gouttes de la vitre : on ne garde qu'un reflet fini et borne, sinon le pixel du jeu tel quel
	if (any(isnan(refl)) || any(isinf(refl))) { refl = 0; poids = 0; }
	refl = clamp(refl, 0, 64);
	float3 res = base + refl * poids * F * spec * p3.x;
	if (any(isnan(res)) || any(isinf(res))) return src;
	res = min(max(res, 0), 65504);   // en D3D11 min/max renvoient l'operande valide : un NaN restant devient 0
	return float4(res, src.a);
}
