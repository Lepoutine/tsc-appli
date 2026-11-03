// TSC Neural Graphics 0.9.2 (table de couleurs 3D apprise sur les videos) + 0.9.1 (meme reference de lumiere pour les 3 ecrans) + 0.9 (etage apres tone mapping du jeu) + 0.8 (calage exposition/neutre/teinte apres T3) + 0.7 (devoile, contraste local, noirs, soleil, vegetation) + 0.6 « route mouillee v1 + camera v1 + ambiances + eau sur vitre + budget » : passe temps reel sur chaque vue d'ETS2, dans la cible HDR, avant exposition, tone mapping et
// interface (recharge a chaud par le plugin). Copyright (c) 2026 Truck So Clean France.
// t0 = copie HDR de la vue (RGBA16F, lumieres non ecretees), t1 = copie de sa profondeur (D32 en Z inverse).
// Le resultat remplace la cible HDR du jeu ; tout est recalcule a chaque image depuis la profondeur reelle.
Texture2D tCouleur : register(t0);
Texture2D<float> tProf : register(t1);
Texture2D<float> tLm : register(t3);   // 0.9.1 : luminance moyenne de l'image, mesuree une fois (vue 1) et partagee par les 3 vues
Texture2D tGb2 : register(t2);
Texture3D tLut : register(t4);   // 0.9.2 : table de couleurs 32x32x32 (entree/sortie en sRGB), apprise jeu -> videos reelles   // 0.7 : cible 2 du G-buffer (albedo RGB, alpha = masque du feuillage) ; absente = vegetation coupee
SamplerState sLin : register(s0);
SamplerState sPt : register(s1);
cbuffer P : register(b0) {
	float4 p0; // vue de controle (0..3), humidite 0..1, tan(fov_v/2), largeur/hauteur
	float4 p1; // plan proche (m), debut et fin de la plage du monde dans la profondeur (cabine au-dela), decalage z
	float4 p2; // largeur, hauteur, 1/largeur, 1/hauteur
	float4 p3; // intensite, rugosite, flou (largeur du lobe brillant), trainees (bruit d'axe)
	float4 p4; // etirement vertical des reflets, pas de marche (m), epaisseur (m), f0
	float4 p5; // index de la vue, assombrissement de l'asphalte mouille, attenuation sur la peinture, dernier niveau de mip
	float4 p6; // camera v1 : intensite globale, brouillard (densite), diffusion (halo des lumieres), grain
	float4 p7; // saturation des hautes lumieres, desaturation du lointain, ombres de contact, numero d'image (grain anime)
	float4 p8; // 0.6 : qualite (budget GPU, 0,4-1), ambiance automatique, luminance moyenne de nuit, de jour (a caler)
	float4 p9; // 0.6 : eau sur vitre (force), taille des gouttes, pluie detectee par le jeu, secondes
	float4 p10; // 0.7 : devoile (retire la brume du jeu), clarte (contraste local), noirs, chaleur (soleil chaud / ombres froides)
	float4 p11; // 0.7 : vegetation (0 si pas de copie du G-buffer) ; 0.8 : teinte vegetation, neutre (surfaces grises), G-buffer present
	float4 p12; // 0.8 : exposition, gamma du monde (eclaircit les tons sombres), hautes lumieres, saturation globale
	float4 p13; // 0.9 apres tone mapping : exposition, contraste, epaule (debut de la compression des blancs), saturation
	float4 p14; // 0.9 : saturation des hautes lumieres (negatif = moins), temperature, teinte (vert/magenta), point noir
	float4 p15; // 0.9 : verts ; 0.9.1 : y = reference partagee presente ; 0.9.2 : z = force de la table de couleurs, w = taille (0 = absente)
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

float4 route(VSO i) {
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
	int pasmax = (int)(16 + 48 * saturate(p8.x));   // budget : moins de pas de marche si la qualite baisse
	[loop] for (int k = 0; k < pasmax; k++) {
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

// ---------- camera v1 (0.5) : ce que montrent les videos reelles et que le jeu ne rend pas ----------
// Mesures du 03/11 (mesures_reel.json / mesures_jeu.json) : le reel a des hautes lumieres saturees (0,33-0,41 contre
// 0,07 en jeu), un lointain voile et delave (perspective aerienne), des lumieres qui bavent (diffusion de l'optique),
// des ombres dans les creux et un grain de capteur. Tout est fait ici en HDR, avant l'exposition et le tone mapping du jeu.
float lum(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }
// 0.9.1 : en 0.8 chaque vue calculait sa propre moyenne -> l'ecran de droite (contre-jour, plus sombre) etait eclairci et
// sature bien plus que le centre, d'ou des coupures aux montants. Toutes les vues utilisent maintenant la meme reference.
float lm_propre() {
	float s = 0;
	[unroll] for (int y = 0; y < 4; y++) [unroll] for (int x = 0; x < 4; x++) s += lum(tCouleur.SampleLevel(sLin, float2(0.125 + x * 0.25, 0.125 + y * 0.25), max(p5.w - 1, 0)).rgb);
	return max(s / 16, 1e-4);
}
float lm_vue() { return p15.y > 0.5 ? max(tLm.Load(int3(0, 0, 0)), 1e-4) : lm_propre(); }
float4 ps_lm(VSO i) : SV_Target { return lm_propre(); }
float3 camera(float2 uv, float3 col) {
	float k = p6.x; if (k <= 0) return col;
	float d = tProf.SampleLevel(sPt, uv, 0);
	bool monde = !(ciel(d) || cabine(d));
	float lm = lm_vue();
	// ambiance automatique : nuit d'apres la luminance moyenne de la vue (seuils nuit_lum / jour_lum a caler en jeu), pluie d'apres l'humidite
	float nuit = p8.y > 0.5 ? saturate((log2(max(p8.w, 1e-5)) - log2(lm)) / max(log2(max(p8.w, 1e-5)) - log2(max(p8.z, 1e-6)), 0.1)) : 0;
	float pl = saturate(p0.y);
	float k_br = p6.y * lerp(1, 0.3, nuit) * (1 + 1.4 * pl), k_dif = p6.z * lerp(1, 1.7, nuit) * (1 + 0.3 * pl);
	float k_gr = p6.w * lerp(1, 2.5, nuit), k_sat = p7.x * lerp(1, 1.2, nuit) * (1 - 0.4 * pl), k_des = p7.y * (1 + pl);
	float3 c = col;
	if (monde) {
		float3 P = posVue(uv); float z = P.z;
		// ombres de contact : creux et pieds d'objets, depuis la profondeur reelle (8 directions, ~0,5 m)
		if (p7.z > 0 && p8.x > 0.55) {
			float pxm = p2.y / (2 * p0.z * max(z, p1.x)); float r = clamp(0.5 * pxm, 2, 40);
			float occ = 0, occ2 = 0; float3 rebond = 0;
			// 0.7 : deux anneaux (contact ~0,5 m et occlusion ambiante ~2 m) + lumiere indirecte (couleur des occulteurs proches)
			[unroll] for (int a = 0; a < 8; a++) {
				float ang = a * 0.785398 + bruit(uv * p2.xy) * 0.785398;
				float2 dir = float2(cos(ang), sin(ang));
				float2 u2 = uv + dir * r * p2.zw;
				float ds = tProf.SampleLevel(sPt, u2, 0);
				if (!(ciel(ds) || cabine(ds))) {
					float dz = z - lineaire(ds);
					occ += saturate(dz / (0.5 + 0.02 * z)) * saturate(1 - dz / (3 + 0.1 * z));
				}
				float2 u3 = uv + dir * min(r * 4, 160) * p2.zw;
				float ds3 = tProf.SampleLevel(sPt, u3, 0);
				if (!(ciel(ds3) || cabine(ds3))) {
					float dz3 = z - lineaire(ds3);
					float w3 = saturate(dz3 / (1.5 + 0.03 * z)) * saturate(1 - dz3 / (8 + 0.2 * z));
					occ2 += w3;
					rebond += tCouleur.SampleLevel(sLin, u3, min(2, p5.w)).rgb * w3;
				}
			}
			float ao = saturate(occ / 8 * 1.6) * 0.5 + saturate(occ2 / 8 * 1.4) * 0.35;
			float3 alb = max(tGb2.SampleLevel(sPt, uv, 0).rgb, 0);
			c = c * (1 - p7.z * ao) + rebond / 8 * (alb + 0.15) * p7.z * 0.25;
		}
		// perspective aerienne : le lointain se voile vers la couleur moyenne du ciel et se delave
		float b = 1 - exp(-max(z - 20, 0) * k_br * 0.002);
		float3 voile = lm * float3(0.95, 0.98, 1.05) * 1.3;
		float l = lum(c);
		c = lerp(c, lerp(c, float3(l, l, l), saturate(k_des)), saturate(b * 2));
		c = lerp(c, voile, saturate(b * 0.85));
	}
	// diffusion de l'optique : les lumieres fortes bavent (mips de la copie HDR, au-dessus de 3x la moyenne)
	if (k_dif > 0) {
		float3 h = 0;
		[unroll] for (int m = 2; m <= 5; m++) { float3 s = tCouleur.SampleLevel(sLin, uv, min((float)m, p5.w)).rgb; h += max(s - lm * 5, 0) * (0.5 / (m - 1)); }
		c += h * k_dif * 0.2;
	}
	// hautes lumieres plus saturees (comme la camera), sans toucher aux tons moyens
	if (k_sat > 0) { float l = lum(c); float w = saturate((l / lm - 1.5) / 3); c = max(0, l + (c - l) * (1 + k_sat * w)); }
	// grain de capteur, plus visible dans les ombres, anime d'une image a l'autre
	if (k_gr > 0) { float g = bruit(uv * p2.xy + p7.w * float2(17.3, 9.1)) - 0.5; float l = lum(c); c *= 1 + g * k_gr * 2 * (0.4 + 0.6 * saturate(1 - l / (lm * 2))); }
	c = lerp(col, c, saturate(k));
	if (any(isnan(c)) || any(isinf(c))) return col;
	return min(max(c, 0), 65504);
}

// ---------- eau sur la vitre (0.6) : seulement en vue cabine, sur ce qu'on voit A TRAVERS le pare-brise ----------
// Regle du socle 0.9h : la cabine est la couche de profondeur > 0,9 ; ce qui est en dessous est vu a travers les vitres.
float h21(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
float2 h22(float2 p) { return frac(sin(float2(dot(p, float2(127.1, 311.7)), dot(p, float2(269.5, 183.3)))) * 43758.5453); }
bool vue_cabine() {
	int n = 0;
	[unroll] for (int y = 0; y < 4; y++) [unroll] for (int x = 0; x < 4; x++) { float d = tProf.SampleLevel(sPt, float2(0.125 + x * 0.25, 0.125 + y * 0.25), 0); if (cabine(d)) n++; }
	return n >= 2;
}
float3 vitre(float2 uv, float3 col) {
	float amt = p9.x * saturate(p9.z) * max(saturate(p0.y), 0.5);   // 0.7 : seulement quand le jeu fait vraiment pleuvoir
	if (amt <= 0.01) return col;
	float d = tProf.SampleLevel(sPt, uv, 0);
	if (cabine(d) || !vue_cabine()) return col;
	float2 px = uv * p2.xy;
	// film d'eau : leger flou de tout ce qui est vu a travers la vitre
	float3 flou = tCouleur.SampleLevel(sLin, uv, min(1.5, p5.w)).rgb;
	float3 c = lerp(col, flou, 0.3 * amt);
	// deux couches de gouttes (cellules), qui se renouvellent lentement
	[unroll] for (int L = 0; L < 2; L++) {
		float s = (L == 0 ? 26.0 : 13.0) * max(p9.y, 0.2);
		float2 cell = floor(px / s);
		float2 cid = cell + L * 71.0;
		float vie = floor(p9.w / (5 + 4 * h21(cid)) + h21(cid + 3.1));
		float2 rnd = h22(cid + vie * 13.7);
		if (h21(cid + vie) > 0.35 * amt + 0.05) continue;      // densite selon la pluie (0.7 : bien moins de gouttes)
		float2 ctr = (cell + 0.05 + 0.9 * rnd) * s;           // placement libre dans la cellule : plus de grille visible
		float r = s * (0.08 + 0.32 * h21(cid * 1.7 + vie) * h21(cid * 2.3 + vie));   // surtout des petites, quelques grosses
		float2 v = (px - ctr) / r; float q = dot(v, v);
		if (q < 1) {
			// la goutte agit comme une lentille : image inversee et nette du decor, bord sombre, petit reflet
			float2 ur = (ctr - v * r * 2.5) * p2.zw;
			float3 g = tCouleur.SampleLevel(sLin, saturate(ur), 0.5).rgb;
			float bord = smoothstep(0.55, 1.0, q);
			g = lerp(g * 1.05, g * 0.45, bord);
			g += lum(g) * 0.6 * saturate(1 - length(v - float2(-0.35, -0.35)) * 3);
			c = lerp(c, g, saturate((1 - q) * 6) * 0.9);
		}
	}
	return c;
}

// ---------- 0.7 : photo (T2 : l'image changeait de moins d'un point ; ici on agit franchement) ----------
// devoile : le jeu ajoute une brume claire qui croit avec la distance ; on la retire (inverse du melange de brouillard)
// vegetation : feuillage (alpha de la cible 2 du G-buffer) moins criard, plus profond, translucide au soleil
float3 monde_photo(float2 uv, float3 c, float lm, float nuit) {
	float d = tProf.SampleLevel(sPt, uv, 0);
	if (ciel(d) || cabine(d)) return c;
	float z = lineaire(d);
	if (p10.x > 0) {
		float3 A = lm * float3(1.0, 1.02, 1.06) * 1.25;          // couleur de la brume : grise legerement bleutee
		float a = saturate(p10.x) * 0.55 * (1 - exp(-max(z - 8, 0) / 450)) * (1 - 0.6 * nuit);
		float3 j = (c - A * a) / max(1 - a, 0.3);
		c = max(j, c * 0.3);
	}
	if (p11.w > 0.5 && p11.z > 0) {
		// 0.8 : surfaces grises (route, beton, glissieres) : albedo peu sature et pas du feuillage -> on retire la dominante brune
		float4 g0 = tGb2.SampleLevel(sPt, uv, 0);
		float mx = max(g0.r, max(g0.g, g0.b)), mn = min(g0.r, min(g0.g, g0.b));
		float sat_alb = (mx - mn) / max(mx, 1e-3);
		float k = saturate(p11.z) * saturate(1 - sat_alb / 0.25) * saturate(1 - g0.a * 4);
		float l0 = lum(c);
		c = lerp(c, l0 * float3(0.98, 1.0, 1.0), k * 0.7);
	}
	if (p11.x > 0) {
		float4 g = tGb2.SampleLevel(sPt, uv, 0);
		float f = saturate(g.a * 2.5) * saturate(p11.x);
		if (f > 0.01) {
			float l = lum(c);
			float3 v = c;
			// verts du jeu trop saturés et trop jaunes : vers un vert olive / bleu-vert naturel
			v = lerp(float3(l, l, l), v, 0.78);
			v *= lerp(float3(1, 1, 1), float3(0.90, 1.0, 1.10), saturate(p11.y));   // 0.8 : contre le jaune-olive vu en T3
			// profondeur du feuillage : les parties sombres s'assombrissent (ombre interne des houppiers)
			float x = l / max(lm, 1e-4);
			v *= lerp(0.85, 1.0, saturate(x * 1.2));
			// translucidite : le soleil traverse les feuilles fines, lueur vert clair
			float3 alb = max(g.rgb, 0);
			v += alb * float3(0.75, 1.0, 0.6) * lm * 0.35 * (1 - nuit) * saturate(1 - x);
			c = lerp(c, v, f);
		}
	}
	return c;
}
// finition : contraste local (clarte), noirs profonds (pied de courbe), soleil chaud / ombres froides
float3 finition(float2 uv, float3 c, float lm, float nuit) {
	float l = max(lum(c), 1e-6);
	if (p10.y > 0) {
		float lb = max(lum(tCouleur.SampleLevel(sLin, uv, min(4, p5.w)).rgb), 1e-6);
		c *= clamp(pow(l / lb, p10.y * 0.7), 0.6, 1.7);
		l = max(lum(c), 1e-6);
	}
	if (p10.z > 0) {
		float x = l / lm;
		float k = p10.z * 0.35;
		c *= x / (x + k) * (1 + k);          // ombres plus profondes, hautes lumieres conservees
		l = max(lum(c), 1e-6);
	}
	if (p10.w > 0) {
		float w = saturate((l / lm - 0.6) / 1.5) * 2 - 1;     // -1 ombres, +1 lumieres
		float k = p10.w * 0.12 * (1 - nuit);
		c *= 1 + k * w * float3(0.6, 0.1, -0.7);
	}
	// 0.8 : calage sur le reel (route claire, hautes lumieres plus hautes et saturees)
	{
		float l2 = max(lum(c), 1e-6), x = l2 / lm;
		if (p12.y != 0) c *= clamp(pow(max(x, 1e-3), -p12.y * saturate(1 - x)), 0.5, 2.0);   // eclaircit les tons sombres et moyens
		if (p12.z > 0) c *= 1 + p12.z * saturate((x - 1.5) / 4);                            // hautes lumieres plus hautes
		if (p12.w != 1) { float l3 = lum(c); c = max(l3 + (c - l3) * p12.w, 0); }          // saturation globale
		c *= max(p12.x, 0.1);                                                               // exposition
	}
	return c;
}
float nuit_de(float lm) {
	return p8.y > 0.5 ? saturate((log2(max(p8.w, 1e-5)) - log2(lm)) / max(log2(max(p8.w, 1e-5)) - log2(max(p8.z, 1e-6)), 0.1)) : 0;
}
float4 ps_principal(VSO i) : SV_Target {
	float4 r = route(i);
	if ((int)p0.x != 0) return r;   // vues de controle : sans camera
	float lm = lm_vue();
	float nt = nuit_de(lm);
	float3 v = monde_photo(i.uv, r.rgb, lm, nt);
	v = vitre(i.uv, v);
	v = camera(i.uv, v);
	float3 f = finition(i.uv, v, lm, nt);
	f = lerp(v, f, saturate(p6.x));
	if (any(isnan(f)) || any(isinf(f))) f = v;
	return float4(min(max(f, 0), 65504), r.a);
}

// ---------- 0.9 : etage APRES l'auto-exposition et le tone mapping du jeu ----------
// Entree : la vue 8 bits sRGB du jeu (lue en lineaire par la vue sRGB), avant sa composition et avant l'interface.
// L'auto-exposition du jeu a deja ete calculee : ce qu'on change ici reste a l'ecran (T3/boucle 0.8 : elle annulait tout en HDR).
float epaule(float x, float s) { return x < s ? x : s + (1 - s) * (1 - exp(-(x - s) / max(1 - s, 1e-3))); }
float4 ps_ldr(VSO i) : SV_Target {
	float4 t = tCouleur.SampleLevel(sPt, i.uv, 0);
	float3 c = max(t.rgb, 0);
	// balance : temperature (+ chaud / - froid) et teinte (+ vert / - magenta)
	c *= float3(1 + 0.08 * p14.y, 1 + 0.06 * p14.z, 1 - 0.08 * p14.y);
	// exposition puis epaule douce : on eclaircit sans bruler les blancs
	c *= max(p13.x, 0.1);
	c = float3(epaule(c.r, p13.z), epaule(c.g, p13.z), epaule(c.b, p13.z));
	// contraste autour du gris moyen (0,18 lineaire)
	if (p13.y != 1) c = 0.18 * pow(max(c, 1e-5) / 0.18, p13.y);
	// point noir
	if (p14.w != 0) { float b = p14.w * 0.02; c = max(c - b, 0) / (1 - b); }
	float l = lum(c);
	// verts jaunes trop vifs (vegetation du jeu) : moins satures, un peu plus clairs
	if (p15.x > 0) {
		float mx = max(c.r, max(c.g, c.b)), mn = min(c.r, min(c.g, c.b));
		float vert = saturate((c.g - max(c.r, c.b)) / max(mx, 1e-4) * 4) * saturate((c.g - c.b) / max(mx, 1e-4) * 2);
		float k = saturate(p15.x) * vert;
		c = lerp(c, l + (c - l) * 0.6, k);
		c *= 1 + 0.15 * k;
		l = lum(c);
	}
	// saturation globale, puis hautes lumieres
	c = l + (c - l) * max(p13.w, 0);
	float w = smoothstep(0.35, 0.85, l);
	c = l + (c - l) * max(1 + p14.x * w, 0);
	c = saturate(c);
	// 0.9.2 : table de couleurs apprise (en sRGB), appliquee en dernier
	if (p15.w > 1 && p15.z > 0) {
		float3 e = pow(c, 1 / 2.2);
		float3 uvw = (e * (p15.w - 1) + 0.5) / p15.w;
		float3 o = pow(saturate(tLut.SampleLevel(sLin, uvw, 0).rgb), 2.2);
		c = lerp(c, o, saturate(p15.z));
	}
	if (any(isnan(c))) c = t.rgb;
	return float4(c, t.a);
}
