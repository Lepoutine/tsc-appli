// TSCF Spartan Studio : éditeur de livrée (phase 3).
// Calques du camion et de la remorque, propriétés de l'élément choisi, annuler / rétablir, sauvegarde automatique,
// export et import du projet. Toutes les positions restent en mètres (s depuis l'avant, y depuis le sol) : le même projet
// sert plus tard à générer le mod sur les gabarits ETS2.
import { FINITIONS, nouvelElement } from './livree.js';

const CLE = 'tscf_spartan_studio_projet';
const COULEURS = { or: 'Or métallique', rouge: 'Rouge Spartiate', chrome: 'Chrome', '#0b0b0d': 'Noir', '#ffffff': 'Blanc' };
const POLICES = { Saira: [900, true], Rajdhani: [700, false], 'Kaushan Script': [400, false], 'Great Vibes': [400, false] };
const TYPES = { fond: 'Fond', vague: 'Vague', bande: 'Bande', texte: 'Texte', image: 'Image' };

const h = (t, a = {}, ...enf) => {
  const e = document.createElement(t);
  for (const [k, v] of Object.entries(a)) if (k.startsWith('on')) e[k] = v; else if (v !== undefined && v !== false) e.setAttribute(k, v === true ? '' : v);
  for (const c of enf.flat()) if (c != null) e.append(c);
  return e;
};

export class Editeur {
  constructor({ calques, proprietes, dims, repeindre, statut }) {
    Object.assign(this, { $calques: calques, $props: proprietes, dims, repeindreVehicule: repeindre, statut });
    this.cible = 'camion'; this.choisi = null; this.passe = []; this.futur = [];
    this.projet = { version: 1, nom: 'Ensemble TSCF', livrees: {} };
  }
  // Au démarrage : reprend le dernier projet enregistré sur ce PC, sinon livrée de départ
  charger(depart) {
    let p = null;
    try { p = JSON.parse(localStorage.getItem(CLE) || 'null'); } catch (e) { p = null; }
    if (p && p.livrees && p.livrees.camion && p.livrees.remorque) { this.projet = p; this.statut('Projet repris : ' + p.nom); }
    else this.projet.livrees = { camion: depart('camion'), remorque: depart('remorque') };
    this.instantane = JSON.stringify(this.projet);
    this.dessiner();
  }
  get livree() { return this.projet.livrees[this.cible]; }
  element(id) { return this.livree.elements.find((e) => e.id === id); }

  // --- modifications : « direct » repeint seulement (glissement), « valider » enregistre une étape d'historique
  direct() { this.repeindreVehicule(this.cible); }
  valider() {
    const j = JSON.stringify(this.projet); if (j === this.instantane) return;
    this.passe.push(this.instantane); if (this.passe.length > 200) this.passe.shift();
    this.futur = []; this.instantane = j; this.sauver(); this.direct(); this.majHistorique();
  }
  sauver() { try { localStorage.setItem(CLE, this.instantane); } catch (e) { this.statut('Sauvegarde automatique impossible (images trop lourdes ?) : utilise « Exporter »', true); } }
  retablirEtat(j) {
    const id = this.choisi && this.choisi.id; this.projet = JSON.parse(j); this.instantane = j; this.sauver();
    this.choisi = id ? this.element(id) || null : null;
    this.repeindreVehicule('camion'); this.repeindreVehicule('remorque'); this.dessiner();
  }
  annuler() { if (!this.passe.length) return; this.futur.push(this.instantane); this.retablirEtat(this.passe.pop()); this.statut('Annulé'); }
  refaire() { if (!this.futur.length) return; this.passe.push(this.instantane); this.retablirEtat(this.futur.pop()); this.statut('Rétabli'); }

  choisirCible(c) { if (c === this.cible) return; this.cible = c; this.choisi = null; this.repeindreVehicule('camion'); this.repeindreVehicule('remorque'); this.dessiner(); }
  choisir(el, cible = this.cible) {
    const avant = this.cible; this.cible = cible; this.choisi = el;
    if (avant !== cible) this.repeindreVehicule(avant);
    this.direct(); this.dessiner();
  }
  ajouter(type) {
    const { L, H } = this.dims(this.cible), el = nouvelElement(type, L, H);
    this.livree.elements.push(el); this.choisi = el; this.valider(); this.dessiner();
  }
  dupliquer() {
    const el = this.choisi; if (!el || el.type === 'fond') return;
    const c = JSON.parse(JSON.stringify(el)); c.id = el.type + '_' + Date.now().toString(36); c.nom = el.nom + ' (copie)';
    if ('s' in c) c.s += 0.3; else if (c.type === 'bande') c.y -= 0.2; else c.dy = (c.dy || 0) - 0.2;
    const L = this.livree.elements; L.splice(L.indexOf(el) + 1, 0, c); this.choisi = c; this.valider(); this.dessiner();
  }
  supprimer() {
    const el = this.choisi; if (!el || el.type === 'fond') return;
    const L = this.livree.elements; L.splice(L.indexOf(el), 1); this.choisi = null; this.valider(); this.dessiner();
  }
  monter(el, d) {
    const L = this.livree.elements, i = L.indexOf(el), j = i + d;
    if (j < 1 || j >= L.length || el.type === 'fond') return; // le fond reste dessous
    [L[i], L[j]] = [L[j], L[i]]; this.valider(); this.dessiner();
  }
  // déplacement en mètres (glisser à la souris ou flèches du clavier)
  deplacer(el, ds, dy) {
    if (el.type === 'texte' || el.type === 'image') { el.s += ds; el.y += dy; }
    else if (el.type === 'bande') { el.s0 += ds; el.s1 += ds; el.y += dy; }
    else if (el.type === 'vague') { el.ds = (el.ds || 0) + ds; el.dy = (el.dy || 0) + dy; }
  }
  // Projet complet : fichier .json (versions, partage, futur export du mod)
  exporter() {
    const b = new Blob([JSON.stringify(this.projet, null, 1)], { type: 'application/json' });
    const a = h('a', { href: URL.createObjectURL(b), download: (this.projet.nom || 'projet').replace(/[^\w\- ]+/g, '_') + '.tscf.json' }); a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }
  importer(fichier) {
    const r = new FileReader();
    r.onload = () => {
      try {
        const p = JSON.parse(r.result);
        if (!p.livrees || !p.livrees.camion || !p.livrees.remorque) throw new Error('ce fichier n’est pas un projet Spartan Studio');
        this.passe.push(this.instantane); this.futur = []; this.choisi = null; this.retablirEtat(JSON.stringify(p)); this.majHistorique();
        this.statut('Projet importé : ' + p.nom);
      } catch (e) { this.statut('Import impossible : ' + e.message, true); }
    };
    r.readAsText(fichier);
  }
  repartir(depart) {
    this.passe.push(this.instantane); this.futur = [];
    this.projet.livrees[this.cible] = depart(this.cible); this.choisi = null;
    this.instantane = JSON.stringify(this.projet); this.sauver(); this.direct(); this.dessiner(); this.majHistorique();
  }
  majHistorique() {
    const a = document.getElementById('annuler'), r = document.getElementById('refaire');
    if (a) a.disabled = !this.passe.length; if (r) r.disabled = !this.futur.length;
  }

  // --- affichage
  dessiner() { this.dessinerCalques(); this.dessinerProprietes(); this.majHistorique(); }
  dessinerCalques() {
    const els = [...this.livree.elements].reverse();
    document.querySelectorAll('[data-cible]').forEach((b) => b.classList.toggle('on', b.dataset.cible === this.cible));
    this.$calques.replaceChildren(...els.map((el) => {
      const oeil = h('button', { class: 'oeil', title: el.visible === false ? 'Afficher' : 'Masquer', onclick: (e) => { e.stopPropagation(); el.visible = el.visible === false; this.valider(); this.dessiner(); } },
        el.visible === false ? '◌' : '●');
      const fl = (d, t) => h('button', { class: 'fl', title: d < 0 ? 'Descendre' : 'Monter', disabled: el.type === 'fond', onclick: (e) => { e.stopPropagation(); this.monter(el, d); } }, t);
      return h('li', { class: 'calque' + (el === this.choisi ? ' choisi' : '') + (el.visible === false ? ' cache' : ''), onclick: () => this.choisir(el) },
        oeil, h('span', { class: 'type' }, TYPES[el.type]), h('span', { class: 'nom' }, el.nom || TYPES[el.type]), fl(1, '▲'), fl(-1, '▼'));
    }));
  }
  dessinerProprietes() {
    const el = this.choisi, P = this.$props;
    if (!el) { P.replaceChildren(h('p', { class: 'note' }, 'Clique sur un calque, ou directement sur un élément du camion ou de la remorque, pour le modifier. Glisse-le pour le déplacer.')); return; }
    const champs = [];
    const maj = (f) => (e) => { f(e.target); this.direct(); };
    const fin = () => this.valider();
    const texte = (lib, cle) => h('label', {}, lib, h('input', { type: 'text', value: el[cle] ?? '', oninput: maj((t) => { el[cle] = t.value; if (cle === 'nom') this.dessinerCalques(); }), onchange: fin }));
    const curseur = (lib, cle, min, max, pas, unite = 'm', lire = () => el[cle] ?? 0, ecrire = (v) => { el[cle] = v; }) => {
      const sortie = h('output', {}, fmt(lire(), unite));
      const nb = h('input', { type: 'range', min, max, step: pas, value: lire(), oninput: maj((t) => { ecrire(+t.value); sortie.textContent = fmt(+t.value, unite); }), onchange: fin });
      return h('label', { class: 'curseur' }, h('span', {}, lib, sortie), nb);
    };
    const choix = (lib, cle, opts, apres) => h('label', {}, lib, h('select', { onchange: (e) => { el[cle] = e.target.value; apres && apres(e.target.value); this.valider(); this.dessinerProprietes(); } },
      Object.entries(opts).map(([v, n]) => h('option', { value: v, selected: String(el[cle]) === v }, n))));
    const couleur = (lib, cle) => {
      const perso = !(el[cle] in COULEURS), pal = { ...COULEURS, perso: 'Autre couleur…' };
      const sel = h('select', { onchange: (e) => { el[cle] = e.target.value === 'perso' ? (perso ? el[cle] : '#2b6cff') : e.target.value; this.valider(); this.dessinerProprietes(); } },
        Object.entries(pal).map(([v, n]) => h('option', { value: v, selected: perso ? v === 'perso' : el[cle] === v }, n)));
      const pick = perso ? h('input', { type: 'color', value: /^#[0-9a-f]{6}$/i.test(el[cle]) ? el[cle] : '#2b6cff', oninput: maj((t) => { el[cle] = t.value; }), onchange: fin }) : null;
      return h('label', {}, lib, h('div', { class: 'ligne' }, sel, pick));
    };
    const finition = () => choix('Finition', 'finition', Object.fromEntries(Object.entries(FINITIONS).map(([k, f]) => [k, f.nom])));
    const { L, H } = this.dims(this.cible);

    champs.push(texte('Nom du calque', 'nom'));
    if (el.type === 'fond') {
      champs.push(h('label', {}, 'Couleur principale', h('input', { type: 'color', value: el.couleur, oninput: maj((t) => { el.couleur = t.value; }), onchange: fin })));
      champs.push(h('label', {}, 'Haut (reflet)', h('input', { type: 'color', value: el.haut, oninput: maj((t) => { el.haut = t.value; }), onchange: fin })));
      champs.push(h('label', {}, 'Bas', h('input', { type: 'color', value: el.bas, oninput: maj((t) => { el.bas = t.value; }), onchange: fin })));
      champs.push(finition());
    }
    if (el.type === 'texte') {
      champs.push(texte('Texte', 'texte'));
      champs.push(choix('Police', 'police', Object.fromEntries(Object.keys(POLICES).map((p) => [p, p])), (v) => { [el.graisse, el.italique] = POLICES[v]; }));
      champs.push(couleur('Couleur', 'couleur'), finition());
      champs.push(curseur('Taille', 'taille', 0.05, 1.6, 0.01));
      champs.push(curseur('Depuis l’avant', 's', 0, L, 0.01), curseur('Hauteur', 'y', 0, H, 0.01));
      champs.push(curseur('Inclinaison', 'rotation', -30, 30, 0.5, '°'));
      champs.push(curseur('Contour noir', 'contour', 0, 0.06, 0.002));
    }
    if (el.type === 'vague') {
      champs.push(couleur('Couleur', 'couleur'), finition());
      champs.push(curseur('Avancer / reculer', 'ds', -L, L, 0.01), curseur('Monter / descendre', 'dy', -H, H, 0.01));
      champs.push(curseur('Taille', 'echelle', 0.2, 2.5, 0.01, '×', () => el.echelle ?? 1));
      champs.push(curseur('Filet or', 'filet', 0, 0.06, 0.002));
    }
    if (el.type === 'bande') {
      champs.push(couleur('Couleur', 'couleur'), finition());
      champs.push(curseur('Début (depuis l’avant)', 's0', 0, L, 0.01), curseur('Fin', 's1', 0, L, 0.01));
      champs.push(curseur('Hauteur', 'y', 0, H, 0.01), curseur('Épaisseur', 'epaisseur', 0.01, 1.5, 0.005));
      champs.push(curseur('Pente', 'pente', -0.4, 0.4, 0.005, ''), curseur('Filet or', 'filet', 0, 0.06, 0.002));
    }
    if (el.type === 'image') {
      const fichier = h('input', { type: 'file', accept: 'image/png,image/jpeg,image/webp', onchange: (e) => {
        const f = e.target.files[0]; if (!f) return; const r = new FileReader();
        r.onload = () => { el.src = r.result; el.nom = f.name.replace(/\.\w+$/, ''); this.valider(); this.dessiner(); }; r.readAsDataURL(f);
      } });
      champs.push(h('label', {}, 'Image (PNG détouré conseillé)', fichier));
      champs.push(finition());
      champs.push(curseur('Hauteur de l’image', 'hauteur', 0.1, 3.5, 0.01));
      champs.push(curseur('Depuis l’avant', 's', 0, L, 0.01), curseur('Hauteur', 'y', 0, H, 0.01));
      champs.push(curseur('Rotation', 'rotation', -45, 45, 0.5, '°'));
      champs.push(h('label', { class: 'case' }, h('input', { type: 'checkbox', checked: el.versAvant !== false, onchange: (e) => { el.versAvant = e.target.checked; this.valider(); } }), 'Regarde vers l’avant des deux côtés'));
    }
    if (el.type !== 'fond') champs.push(curseur('Opacité', 'opacite', 0.1, 1, 0.01, '%', () => el.opacite ?? 1));
    const actions = el.type === 'fond' ? null : h('div', { class: 'actions' },
      h('button', { onclick: () => this.dupliquer() }, 'Dupliquer'), h('button', { class: 'danger', onclick: () => this.supprimer() }, 'Supprimer'));
    P.replaceChildren(h('div', { class: 'titreProps' }, TYPES[el.type], h('small', {}, this.cible === 'camion' ? ' · camion' : ' · remorque')), ...champs, actions);
  }
}

function fmt(v, u) {
  if (u === '%') return Math.round(v * 100) + ' %';
  if (u === '°') return v.toFixed(1) + '°';
  if (u === '×') return '×' + v.toFixed(2);
  if (u === '') return v.toFixed(3);
  return v.toFixed(2) + ' m';
}
