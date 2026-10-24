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

// Courbe lisse passant par le milieu des segments (contour fermé)
function contour(ctx, pts) {
  const n = pts.length, m = (i) => { const a = pts[i % n], b = pts[(i + 1) % n]; return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; };
  ctx.beginPath(); const d = m(n - 1); ctx.moveTo(d[0], d[1]);
  for (let i = 0; i < n; i++) { const q = m(i); ctx.quadraticCurveTo(pts[i][0], pts[i][1], q[0], q[1]); }
  ctx.closePath();
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
  peindre(livree) {
    const C = this.couleur.getContext('2d'), M = this.matiere.getContext('2d'), { plan } = this;
    for (const el of livree.elements) {
      if (el.visible === false) continue;
      const f = FINITIONS[el.finition] || FINITIONS.laque_noire;
      const mat = `rgb(0,${Math.round(f.rugosite * 255)},${Math.round(f.metal * 255)})`;
      if (el.type === 'fond') {
        for (const [nom, r] of Object.entries(plan.R)) {
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
        for (const X of [C, M]) { X.beginPath(); X.rect(r.x * plan.k, r.y * plan.k, r.w * plan.k, r.h * plan.k); X.clip(); }
        if (el.type === 'vague') this.vague(C, M, vue, el, mat);
        else if (el.type === 'texte') this.texte(C, M, vue, el, mat);
        C.restore(); M.restore();
      }
    }
    this.texCouleur.needsUpdate = true; this.texMatiere.needsUpdate = true;
  }
  vague(C, M, vue, el, mat) {
    const pts = el.points.map(([s, y]) => this.px(vue, s, y));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    contour(C, pts);
    C.fillStyle = el.couleur === 'or' ? or(C, y0, y1) : rouge(C, vue === 'droite' ? x1 : x0, vue === 'droite' ? x0 : x1);
    C.shadowColor = 'rgba(0,0,0,.55)'; C.shadowBlur = 0.05 * this.plan.k; C.fill(); C.shadowBlur = 0;
    if (el.filet) { C.lineWidth = el.filet * this.plan.k; C.strokeStyle = or(C, y0, y1); C.stroke(); }
    contour(M, pts); M.fillStyle = mat; M.fill();
    if (el.filet) { M.lineWidth = el.filet * this.plan.k; M.strokeStyle = 'rgb(0,60,255)'; M.stroke(); }
  }
  texte(C, M, vue, el, mat) {
    const [x, y] = this.px(vue, el.s, el.y), k = this.plan.k, t = el.taille * k;
    const police = `${el.italique ? 'italic ' : ''}${el.graisse || 400} ${t}px "${el.police}"`;
    for (const X of [C, M]) { X.font = police; X.textAlign = 'center'; X.textBaseline = 'alphabetic'; }
    if (el.rotation) for (const X of [C, M]) { X.translate(x, y); X.rotate((el.rotation * Math.PI) / 180); X.translate(-x, -y); }
    if (el.contour) { C.lineJoin = 'round'; C.lineWidth = el.contour * k; C.strokeStyle = el.couleurContour || '#000'; C.strokeText(el.texte, x, y); }
    C.shadowColor = 'rgba(0,0,0,.6)'; C.shadowBlur = 0.04 * k; C.shadowOffsetY = 0.015 * k;
    C.fillStyle = el.couleur === 'or' ? or(C, y - t * 0.8, y + t * 0.1) : el.couleur; C.fillText(el.texte, x, y);
    M.fillStyle = mat; M.fillText(el.texte, x, y);
    if (el.contour) { M.lineWidth = el.contour * k; M.strokeStyle = mat; M.strokeText(el.texte, x, y); }
  }
}

// Livrée d'essai (phase 2) : sert à juger le rendu des matières. La vraie livrée TSCF éditable arrive en phase 3.
export function livreeEssai(cible, L, H) {
  const els = [{ id: 'fond', type: 'fond', couleur: '#09090b', haut: '#1d1d22', bas: '#030304', finition: 'laque_noire' }];
  if (cible === 'remorque') {
    els.push(
      { id: 'vague_rouge', type: 'vague', finition: 'rouge_spartiate', couleur: 'rouge', filet: 0.025,
        points: [[0.6, 1.5], [3.5, 1.7], [7.5, 2.6], [11.5, 3.9], [L - 0.3, 4.1], [L - 0.4, 3.4], [10.5, 3.0], [7.0, 2.0], [3.0, 1.35]] },
      { id: 'vague_or', type: 'vague', finition: 'or_metal', couleur: 'or',
        points: [[1.0, 1.32], [4.5, 1.5], [8.5, 2.3], [12.2, 3.35], [L - 0.5, 3.35], [11.8, 3.15], [8.0, 2.1], [4.0, 1.38]] },
      { id: 'tscf', type: 'texte', texte: 'TSCF', police: 'Saira', graisse: 900, italique: true, taille: 0.8, s: L * 0.42, y: 2.55, couleur: 'or', finition: 'or_metal', contour: 0.03 },
      { id: 'devise', type: 'texte', texte: 'Plus qu’une route, une famille.', police: 'Kaushan Script', taille: 0.3, s: L * 0.45, y: 2.08, couleur: 'or', finition: 'or_brosse' },
    );
  } else {
    els.push(
      { id: 'vague_rouge', type: 'vague', finition: 'rouge_spartiate', couleur: 'rouge', filet: 0.02,
        points: [[0.1, 0.55], [1.2, 0.9], [2.0, 2.0], [2.3, 3.2], [2.25, 3.9], [1.9, 3.4], [1.5, 2.0], [0.8, 1.1]] },
      { id: 'vague_or', type: 'vague', finition: 'or_metal', couleur: 'or', points: [[0.2, 1.4], [1.0, 1.7], [1.7, 2.8], [1.55, 2.9], [0.9, 1.85]] },
      { id: 'tscf', type: 'texte', texte: 'TSCF', police: 'Saira', graisse: 900, italique: true, taille: 0.42, s: 1.0, y: 3.45, couleur: 'or', finition: 'or_metal', contour: 0.015 },
    );
  }
  return { nom: 'Essai TSCF noir rouge or', elements: els };
}
