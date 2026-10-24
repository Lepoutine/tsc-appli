// TSCF Spartan Studio : peinture de la livrée sur la planche (couleur + matière).
// Une livrée est une liste d'éléments modifiables un par un (fond, vagues, textes, images), placés en mètres :
//   s = distance depuis l'avant du véhicule, y = hauteur depuis le sol.
// Deux toiles sont produites : la couleur, et la matière (vert = rugosité, bleu = métal) pour l'or, le chrome, la laque.
import * as THREE from 'three';

export const FINITIONS = {
  laque_noire: { nom: 'Noir laqué', rugosite: 0.28, metal: 0.05 },
  rouge_spartiate: { nom: 'Rouge Spartiate nacré', rugosite: 0.26, metal: 0.35 },
  or_metal: { nom: 'Or métallique poli', rugosite: 0.3, metal: 0.9 },
  or_brosse: { nom: 'Or brossé', rugosite: 0.5, metal: 0.85 },
  chrome: { nom: 'Chrome', rugosite: 0.06, metal: 1 },
  mat: { nom: 'Mat', rugosite: 0.85, metal: 0 },
};

export const PALETTE = { noir: '#0b0b0d', rouge: '#b3121b', or: '#c9a24a' };

// Dégradé or (reflets) entre deux hauteurs en pixels
function or(ctx, y0, y1) {
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  g.addColorStop(0, '#fff3c4'); g.addColorStop(0.28, '#e3c06a'); g.addColorStop(0.5, '#9c7322'); g.addColorStop(0.72, '#f1d488'); g.addColorStop(1, '#7d5a17');
  return g;
}
function rouge(ctx, x0, x1) {
  const g = ctx.createLinearGradient(x0, 0, x1, 0);
  g.addColorStop(0, '#5e060b'); g.addColorStop(0.45, '#c0141e'); g.addColorStop(0.7, '#ff3a3f'); g.addColorStop(1, '#7a080e');
  return g;
}
function chrome(ctx, y0, y1) {
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  g.addColorStop(0, '#ffffff'); g.addColorStop(0.35, '#b9bec6'); g.addColorStop(0.5, '#4b4f57'); g.addColorStop(0.62, '#e9edf2'); g.addColorStop(1, '#7c818a');
  return g;
}
function nuance(hex, f) {
  const n = parseInt(hex.slice(1), 16), c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => Math.round(f > 0 ? v + (255 - v) * f : v * (1 + f)));
  return `rgb(${c.join(',')})`;
}
// Teinte d'un élément : « or », « rouge », « chrome » donnent des reflets travaillés ; une couleur #rrggbb un léger relief
export function teinte(ctx, couleur, x0, y0, x1, y1) {
  if (couleur === 'or') return or(ctx, y0, y1);
  if (couleur === 'rouge') return rouge(ctx, x0, x1);
  if (couleur === 'chrome') return chrome(ctx, y0, y1);
  if (!/^#[0-9a-f]{6}$/i.test(couleur || '')) return couleur || '#ffffff';
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  g.addColorStop(0, nuance(couleur, 0.22)); g.addColorStop(0.5, couleur); g.addColorStop(1, nuance(couleur, -0.35));
  return g;
}

// Courbe lisse passant par le milieu des segments (contour fermé)
function contour(ctx, pts) {
  const n = pts.length, m = (i) => { const a = pts[i % n], b = pts[(i + 1) % n]; return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; };
  ctx.beginPath(); const d = m(n - 1); ctx.moveTo(d[0], d[1]);
  for (let i = 0; i < n; i++) { const q = m(i); ctx.quadraticCurveTo(pts[i][0], pts[i][1], q[0], q[1]); }
  ctx.closePath();
}
function polygone(ctx, pts) { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); }

// Points (s, y) en mètres d'une forme, après déplacement et échelle de l'élément
export function pointsForme(el) {
  if (el.type === 'bande') {
    const e = el.epaisseur / 2, p = el.pente || 0, l = el.s1 - el.s0;
    return [[el.s0, el.y + e], [el.s1, el.y + e + p * l], [el.s1, el.y - e + p * l], [el.s0, el.y - e]];
  }
  const P = el.points, k = el.echelle || 1, ds = el.ds || 0, dy = el.dy || 0;
  const cs = P.reduce((a, q) => a + q[0], 0) / P.length, cy = P.reduce((a, q) => a + q[1], 0) / P.length;
  return P.map(([s, y]) => [cs + (s - cs) * k + ds, cy + (y - cy) * k + dy]);
}

const IMAGES = {};
// Image d'un calque (fichier de l'atelier ou image importée) ; quand elle arrive, la planche est repeinte
function image(src, pret) {
  let im = IMAGES[src];
  if (!im) { im = IMAGES[src] = new Image(); im.onload = () => pret && pret(); im.src = src; }
  return im.complete && im.naturalWidth ? im : null;
}

export class Planche {
  constructor(plan) {
    this.plan = plan;
    const mk = () => { const c = document.createElement('canvas'); c.width = plan.px; c.height = plan.py; return c; };
    this.couleur = mk(); this.matiere = mk();
    this.texCouleur = new THREE.CanvasTexture(this.couleur); this.texCouleur.colorSpace = THREE.SRGBColorSpace; this.texCouleur.anisotropy = 8;
    this.texMatiere = new THREE.CanvasTexture(this.matiere); this.texMatiere.anisotropy = 8;
  }
  // (s, y) en mètres -> pixels de la vue, côté gauche ou droit
  px(vue, s, y) {
    const { R, L, k, box } = this.plan, r = R[vue];
    const a = vue === 'droite' ? L - s : s, b = box.max.y - y;
    return [(r.x + a) * k, (r.y + b) * k];
  }
  // Coordonnées de texture (u, v) d'un point de la carrosserie -> côté et position en mètres (null hors des côtés)
  versMetres(u, v) {
    const { R, L, k, box, px, py } = this.plan, X = (u * px) / k, Y = ((1 - v) * py) / k;
    for (const vue of ['gauche', 'droite']) {
      const r = R[vue];
      if (X >= r.x && X <= r.x + r.w && Y >= r.y && Y <= r.y + r.h) {
        const a = X - r.x; return { vue, s: vue === 'droite' ? L - a : a, y: box.max.y - (Y - r.y) };
      }
    }
    return null;
  }
  // Élément visible le plus haut sous le point (s, y) ; le fond n'est jamais pris
  trouver(livree, s, y) {
    const C = this.couleur.getContext('2d');
    for (let i = livree.elements.length - 1; i >= 0; i--) {
      const el = livree.elements[i]; if (el.visible === false || el.type === 'fond' || el.verrou) continue;
      if (el.type === 'texte') {
        C.font = `${el.italique ? 'italic ' : ''}${el.graisse || 400} 100px "${el.police}"`;
        const l = (C.measureText(el.texte).width / 100) * el.taille;
        if (Math.abs(s - el.s) <= l / 2 + 0.05 && y >= el.y - el.taille * 0.3 && y <= el.y + el.taille * 0.85) return el;
      } else if (el.type === 'image') {
        const im = image(el.src), r = im ? im.naturalWidth / im.naturalHeight : 1, h = el.hauteur;
        if (Math.abs(s - el.s) <= (h * r) / 2 && Math.abs(y - el.y) <= h / 2) return el;
      } else if (el.type === 'vague' || el.type === 'bande') {
        const P = pointsForme(el); C.beginPath(); P.forEach(([a, b], j) => (j ? C.lineTo(a * 100, b * 100) : C.moveTo(a * 100, b * 100))); C.closePath();
        if (C.isPointInPath(s * 100, y * 100)) return el;
      }
    }
    return null;
  }
  peindre(livree, choisi, pret) {
    const C = this.couleur.getContext('2d'), M = this.matiere.getContext('2d'), { plan } = this;
    C.clearRect(0, 0, plan.px, plan.py); M.clearRect(0, 0, plan.px, plan.py);
    C.fillStyle = '#0b0b0d'; C.fillRect(0, 0, plan.px, plan.py); M.fillStyle = 'rgb(0,72,13)'; M.fillRect(0, 0, plan.px, plan.py);
    for (const el of livree.elements) {
      if (el.visible === false) continue;
      const f = FINITIONS[el.finition] || FINITIONS.laque_noire;
      const mat = `rgb(0,${Math.round(f.rugosite * 255)},${Math.round(f.metal * 255)})`;
      if (el.type === 'fond') {
        for (const r of Object.values(plan.R)) {
          const y0 = r.y * plan.k, y1 = (r.y + r.h) * plan.k, g = C.createLinearGradient(0, y0, 0, y1);
          g.addColorStop(0, el.haut || '#1a1a1f'); g.addColorStop(0.55, el.couleur || PALETTE.noir); g.addColorStop(1, el.bas || '#050506');
          C.fillStyle = g; C.fillRect(r.x * plan.k, y0, r.w * plan.k, r.h * plan.k);
          M.fillStyle = mat; M.fillRect(r.x * plan.k, y0, r.w * plan.k, r.h * plan.k);
        }
        continue;
      }
      for (const vue of ['gauche', 'droite']) {
        const r = plan.R[vue];
        C.save(); M.save();
        for (const X of [C, M]) { X.beginPath(); X.rect(r.x * plan.k, r.y * plan.k, r.w * plan.k, r.h * plan.k); X.clip(); X.globalAlpha = el.opacite ?? 1; }
        if (el.type === 'vague' || el.type === 'bande') this.forme(C, M, vue, el, mat);
        else if (el.type === 'texte') this.texte(C, M, vue, el, mat);
        else if (el.type === 'image') this.image(C, M, vue, el, mat, pret);
        C.restore(); M.restore();
        if (el === choisi) this.cadre(C, vue, el);
      }
    }
    this.texCouleur.needsUpdate = true; this.texMatiere.needsUpdate = true;
  }
  // Cadre pointillé autour de l'élément choisi (aperçu seulement, jamais exporté)
  cadre(C, vue, el) {
    const k = this.plan.k; let a, b;
    if (el.type === 'texte') {
      C.font = `${el.italique ? 'italic ' : ''}${el.graisse || 400} ${el.taille * k}px "${el.police}"`;
      const l = C.measureText(el.texte).width / k; a = [el.s - l / 2, el.y + el.taille * 0.85]; b = [el.s + l / 2, el.y - el.taille * 0.3];
    } else if (el.type === 'image') {
      const im = image(el.src), r = im ? im.naturalWidth / im.naturalHeight : 1, h = el.hauteur;
      a = [el.s - (h * r) / 2, el.y + h / 2]; b = [el.s + (h * r) / 2, el.y - h / 2];
    } else {
      const P = pointsForme(el), ss = P.map((q) => q[0]), yy = P.map((q) => q[1]);
      a = [Math.min(...ss), Math.max(...yy)]; b = [Math.max(...ss), Math.min(...yy)];
    }
    const p = this.px(vue, a[0], a[1]), q = this.px(vue, b[0], b[1]);
    C.save(); C.setLineDash([0.08 * k, 0.05 * k]); C.lineWidth = Math.max(2, 0.02 * k);
    C.strokeStyle = '#ffd34d'; C.strokeRect(Math.min(p[0], q[0]), p[1], Math.abs(q[0] - p[0]), q[1] - p[1]); C.restore();
  }
  forme(C, M, vue, el, mat) {
    const pts = pointsForme(el).map(([s, y]) => this.px(vue, s, y)), lisse = el.type === 'vague';
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const trace = (X) => (lisse ? contour(X, pts) : polygone(X, pts));
    trace(C);
    C.fillStyle = teinte(C, el.couleur, vue === 'droite' ? x1 : x0, y0, vue === 'droite' ? x0 : x1, y1);
    C.shadowColor = 'rgba(0,0,0,.55)'; C.shadowBlur = 0.05 * this.plan.k; C.fill(); C.shadowBlur = 0;
    if (el.filet) { C.lineWidth = el.filet * this.plan.k; C.strokeStyle = teinte(C, el.couleurFilet || 'or', x0, y0, x1, y1); C.stroke(); }
    trace(M); M.fillStyle = mat; M.fill();
    if (el.filet) { M.lineWidth = el.filet * this.plan.k; M.strokeStyle = 'rgb(0,60,255)'; M.stroke(); }
  }
  texte(C, M, vue, el, mat) {
    const [x, y] = this.px(vue, el.s, el.y), k = this.plan.k, t = el.taille * k;
    const police = `${el.italique ? 'italic ' : ''}${el.graisse || 400} ${t}px "${el.police}"`;
    for (const X of [C, M]) { X.font = police; X.textAlign = 'center'; X.textBaseline = 'alphabetic'; }
    // une rotation garde le même sens de lecture des deux côtés (jamais de miroir)
    if (el.rotation) for (const X of [C, M]) { X.translate(x, y); X.rotate((el.rotation * Math.PI) / 180); X.translate(-x, -y); }
    if (el.contour) { C.lineJoin = 'round'; C.lineWidth = el.contour * k; C.strokeStyle = el.couleurContour || '#000'; C.strokeText(el.texte, x, y); }
    C.shadowColor = 'rgba(0,0,0,.6)'; C.shadowBlur = 0.04 * k; C.shadowOffsetY = 0.015 * k;
    const l = C.measureText(el.texte).width;
    C.fillStyle = teinte(C, el.couleur, x - l / 2, y - t * 0.8, x + l / 2, y + t * 0.1); C.fillText(el.texte, x, y);
    M.fillStyle = mat; M.fillText(el.texte, x, y);
    if (el.contour) { M.lineWidth = el.contour * k; M.strokeStyle = mat; M.strokeText(el.texte, x, y); }
  }
  image(C, M, vue, el, mat, pret) {
    const im = image(el.src, pret); if (!im) return;
    const k = this.plan.k, h = el.hauteur * k, w = (h * im.naturalWidth) / im.naturalHeight, [x, y] = this.px(vue, el.s, el.y);
    for (const X of [C, M]) { X.translate(x, y); if (el.rotation) X.rotate((el.rotation * Math.PI) / 180); }
    // une image regarde vers l'avant des deux côtés : à droite elle est retournée (le texte, lui, ne l'est jamais)
    if (vue === 'droite' && el.versAvant !== false) for (const X of [C, M]) X.scale(-1, 1);
    C.shadowColor = 'rgba(0,0,0,.6)'; C.shadowBlur = 0.04 * k; C.drawImage(im, -w / 2, -h / 2, w, h);
    // matière : la forme de l'image (canal alpha) prend la finition choisie
    const t = document.createElement('canvas'); t.width = Math.max(1, Math.ceil(w)); t.height = Math.max(1, Math.ceil(h));
    const T = t.getContext('2d'); T.drawImage(im, 0, 0, t.width, t.height); T.globalCompositeOperation = 'source-in'; T.fillStyle = mat; T.fillRect(0, 0, t.width, t.height);
    M.drawImage(t, -w / 2, -h / 2, w, h);
  }
}

// Livrée de départ TSCF noir, rouge et or : chaque élément est un calque modifiable (nom, couleur, finition, position en mètres)
export function livreeDepart(cible, L, H) {
  const els = [{ id: 'fond', nom: 'Fond noir laqué', type: 'fond', couleur: '#09090b', haut: '#1d1d22', bas: '#030304', finition: 'laque_noire' }];
  if (cible === 'remorque') {
    els.push(
      { id: 'vague_rouge', nom: 'Vague rouge', type: 'vague', finition: 'rouge_spartiate', couleur: 'rouge', filet: 0.025,
        points: [[0.6, 1.5], [3.5, 1.7], [7.5, 2.6], [11.5, 3.9], [L - 0.3, 4.1], [L - 0.4, 3.4], [10.5, 3.0], [7.0, 2.0], [3.0, 1.35]] },
      { id: 'vague_or', nom: 'Vague or', type: 'vague', finition: 'or_metal', couleur: 'or',
        points: [[1.0, 1.32], [4.5, 1.5], [8.5, 2.3], [12.2, 3.35], [L - 0.5, 3.35], [11.8, 3.15], [8.0, 2.1], [4.0, 1.38]] },
      { id: 'lion', nom: 'Lion TSCF', type: 'image', src: 'css/embleme_detoure.png', s: L - 1.5, y: 2.45, hauteur: 1.25, finition: 'or_metal' },
      { id: 'tscf', nom: 'TSCF', type: 'texte', texte: 'TSCF', police: 'Saira', graisse: 900, italique: true, taille: 0.8, s: L * 0.42, y: 2.55, couleur: 'or', finition: 'or_metal', contour: 0.03 },
      { id: 'devise', nom: 'Devise', type: 'texte', texte: 'Plus qu’une route, une famille.', police: 'Kaushan Script', taille: 0.3, s: L * 0.45, y: 2.08, couleur: 'or', finition: 'or_brosse' },
    );
  } else {
    els.push(
      { id: 'vague_rouge', nom: 'Vague rouge', type: 'vague', finition: 'rouge_spartiate', couleur: 'rouge', filet: 0.02,
        points: [[0.1, 0.55], [1.2, 0.9], [2.0, 2.0], [2.3, 3.2], [2.25, 3.9], [1.9, 3.4], [1.5, 2.0], [0.8, 1.1]] },
      { id: 'vague_or', nom: 'Vague or', type: 'vague', finition: 'or_metal', couleur: 'or', points: [[0.2, 1.4], [1.0, 1.7], [1.7, 2.8], [1.55, 2.9], [0.9, 1.85]] },
      { id: 'tscf', nom: 'TSCF', type: 'texte', texte: 'TSCF', police: 'Saira', graisse: 900, italique: true, taille: 0.36, s: 1.25, y: 3.2, couleur: 'or', finition: 'or_metal', contour: 0.012 },
    );
  }
  return { nom: 'TSCF noir rouge or', elements: els };
}

// Nouveaux calques ajoutés depuis l'éditeur, posés au milieu du côté visible
let compteur = 0;
export function nouvelElement(type, L, H) {
  const id = type + '_' + Date.now().toString(36) + (compteur++);
  if (type === 'texte') return { id, nom: 'Texte', type, texte: 'TSCF', police: 'Saira', graisse: 900, italique: true, taille: 0.4, s: L / 2, y: H * 0.6, couleur: 'or', finition: 'or_metal', contour: 0.012 };
  if (type === 'bande') return { id, nom: 'Bande', type, s0: 0.2, s1: L - 0.2, y: H * 0.35, epaisseur: 0.12, pente: 0, couleur: 'rouge', finition: 'rouge_spartiate', filet: 0.01 };
  if (type === 'vague') return { id, nom: 'Vague', type, couleur: 'or', finition: 'or_metal', filet: 0,
    points: [[L * 0.2, H * 0.3], [L * 0.5, H * 0.45], [L * 0.8, H * 0.7], [L * 0.78, H * 0.6], [L * 0.5, H * 0.38]] };
  return { id, nom: 'Image', type: 'image', src: 'css/embleme_detoure.png', s: L / 2, y: H * 0.55, hauteur: 1, finition: 'or_metal' };
}
