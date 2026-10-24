// TSCF Spartan Studio : interface de l'atelier (ensemble 3D, vues, éclairages, édition de la livrée).
import * as THREE from 'three';
import { Scene3D, ECLAIRAGES } from './scene.js';
import { tracteurProvisoire, citerneProvisoire, chargerGlb } from './vehicules.js';
import { decoupe, projeter } from './projection.js';
import { Planche, livreeDepart } from './livree.js';
import { Editeur } from './editeur.js';

const $ = (id) => document.getElementById(id);
const S = new Scene3D($('vue3d'));
window.TSCF_STUDIO = S; // pour les essais automatiques

const etat = { camion: null, remorque: null, mode: 'ensemble', modeles: { camions: [], remorques: [] } };

function statut(t, alerte) { const el = $('statut'); el.textContent = t; el.classList.toggle('alerte', !!alerte); }

// Livrée : planche à la taille du véhicule, projection des pièces peintes, peinture des éléments
function habiller(v, cible) {
  const g = v.groupe; g.updateMatrixWorld(true);
  const versVehicule = new THREE.Matrix4().copy(g.matrixWorld).invert(), pieces = [], box = new THREE.Box3();
  g.traverse((o) => {
    if (!o.isMesh || !o.userData.peint) return;
    const geo = o.geometry.clone().applyMatrix4(versVehicule.clone().multiply(o.matrixWorld));
    geo.computeBoundingBox(); box.union(geo.boundingBox); pieces.push([o, geo]);
  });
  const plan = decoupe(box, 170), planche = new Planche(plan);
  const mat = new THREE.MeshPhysicalMaterial({ map: planche.texCouleur, roughnessMap: planche.texMatiere, metalnessMap: planche.texMatiere,
    roughness: 1, metalness: 1, clearcoat: 1, clearcoatRoughness: 0.06 });
  for (const [o, geo] of pieces) {
    // la géométrie est maintenant dans le repère du véhicule : la pièce reçoit l'inverse de la transformation de son parent
    o.geometry = projeter(geo, plan);
    new THREE.Matrix4().copy(o.parent.matrixWorld).invert().multiply(g.matrixWorld).decompose(o.position, o.quaternion, o.scale);
    o.material = mat;
  }
  v.planche = planche; v.plan = plan;
}

// Éditeur de livrée : les calques sont en mètres, la planche de chaque véhicule est repeinte à chaque changement
const dims = (cible) => { const v = etat[cible]; return v ? { L: v.plan.L, H: v.plan.box.max.y } : { L: 6, H: 4 }; };
const depart = (cible) => { const { L, H } = dims(cible); return livreeDepart(cible, L, H); };
function repeindre(cible) {
  const v = etat[cible]; if (!v || !E.projet.livrees[cible]) return;
  v.planche.peindre(E.projet.livrees[cible], E.cible === cible ? E.choisi : null, () => repeindre(cible));
}
const E = new Editeur({ calques: $('calques'), proprietes: $('proprietes'), dims, repeindre, statut });
window.TSCF_editeur = E;

async function choisir(type, id) {
  const liste = type === 'camion' ? etat.modeles.camions : etat.modeles.remorques;
  const info = liste.find((m) => m.id === id);
  let v;
  try {
    if (info && info.fichier) { statut('Chargement de ' + info.nom + '…'); v = await chargerGlb('modeles/' + info.fichier, info.nom, type); }
  } catch (e) { console.warn(e); statut('Modèle introuvable (' + info.fichier + ') : modèle provisoire affiché.', true); }
  if (!v) v = type === 'camion' ? tracteurProvisoire() : citerneProvisoire();
  habiller(v, type);
  const ancien = etat[type]; if (ancien) S.racine.remove(ancien.groupe);
  etat[type] = v; S.racine.add(v.groupe);
  repeindre(type); placer(); avertir();
}

// Attelage : la sellette du camion sous le pivot de la remorque ; mode « écartés » pour les juger séparément
function placer() {
  const { camion: c, remorque: r, mode } = etat; if (!c || !r) return;
  r.groupe.position.set(0, 0, 0);
  const ecart = mode === 'ecartes' ? -4.5 : 0;
  c.groupe.position.set(r.hook.x - c.sellette.x, 0, r.hook.z - c.sellette.z + ecart);
  c.groupe.visible = mode !== 'remorque'; r.groupe.visible = mode !== 'camion';
}

function avertir() {
  const prov = [etat.camion, etat.remorque].filter((v) => v && !v.reel).map((v) => v.nom);
  $('limite').hidden = !prov.length;
  $('limite').innerHTML = prov.length
    ? `<b>Modèle provisoire</b> ${prov.join(' et ')} : forme générique pour juger la livrée, pas le modèle ETS2 exact. Le vrai modèle se convertit depuis le jeu (voir la notice).`
    : '';
  const reels = [etat.camion, etat.remorque].filter((v) => v && v.reel).map((v) => v.nom);
  statut(reels.length ? 'Modèle réel : ' + reels.join(', ') : 'Prêt');
}

function remplir(sel, liste) { sel.innerHTML = liste.map((m) => `<option value="${m.id}">${m.nom}</option>`).join(''); }

async function demarrer() {
  try { const r = await fetch('modeles/modeles.json', { cache: 'no-store' }); if (r.ok) etat.modeles = await r.json(); } catch (e) { /* pas de manifeste : provisoires seulement */ }
  etat.modeles.camions = [...(etat.modeles.camions || []), { id: 'scania_r_prov', nom: 'Scania R (provisoire)' }];
  etat.modeles.remorques = [...(etat.modeles.remorques || []), { id: 'citerne_prov', nom: 'Citerne (provisoire)' }];
  remplir($('choixCamion'), etat.modeles.camions); remplir($('choixRemorque'), etat.modeles.remorques);
  $('choixEclairage').innerHTML = Object.entries(ECLAIRAGES).map(([k, e]) => `<option value="${k}">${e.nom}</option>`).join('');
  await document.fonts.load('italic 900 40px "Saira"'); await document.fonts.load('40px "Kaushan Script"');
  await document.fonts.load('40px "Great Vibes"'); await document.fonts.load('700 40px "Rajdhani"');
  await Promise.all([choisir('camion', $('choixCamion').value), choisir('remorque', $('choixRemorque').value)]);
  E.charger(depart); repeindre('camion'); repeindre('remorque');
  S.vue('trois_quarts', 1);
  document.body.classList.add('pret');
}

$('choixCamion').onchange = (e) => choisir('camion', e.target.value).then(() => S.vue('trois_quarts'));
$('choixRemorque').onchange = (e) => choisir('remorque', e.target.value).then(() => S.vue('trois_quarts'));
$('choixEclairage').onchange = (e) => S.eclairage(e.target.value);
document.querySelectorAll('[data-mode]').forEach((b) => b.onclick = () => {
  etat.mode = b.dataset.mode; document.querySelectorAll('[data-mode]').forEach((x) => x.classList.toggle('on', x === b));
  placer(); S.vue('trois_quarts');
});
document.querySelectorAll('[data-vue]').forEach((b) => b.onclick = () => S.vue(b.dataset.vue));
$('capture').onclick = () => { const a = document.createElement('a'); a.href = S.capture(); a.download = 'tscf_spartan_studio.png'; a.click(); };
// Clic sur la carrosserie : choisir l'élément touché et le glisser ; ailleurs, la caméra tourne comme d'habitude
function toucher(e) {
  const r = S.rendu.domElement.getBoundingClientRect();
  S.rayon.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), S.cam);
  const hit = S.rayon.intersectObjects(S.racine.children, true).find((x) => x.object.visible && isVisible(x.object));
  if (!hit || !hit.object.userData.peint || !hit.uv) return null;
  const cible = ['camion', 'remorque'].find((c) => etat[c] && aPourParent(hit.object, etat[c].groupe)); if (!cible) return null;
  const pos = etat[cible].planche.versMetres(hit.uv.x, hit.uv.y);
  return pos ? { cible, ...pos } : null;
}
const isVisible = (o) => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
const aPourParent = (o, g) => { for (let p = o; p; p = p.parent) if (p === g) return true; return false; };
let glisse = null;
$('vue3d').addEventListener('pointerdown', (e) => {
  if (e.button !== 0 || !E.projet.livrees.camion) return;
  const t = toucher(e); if (!t) return;
  const el = etat[t.cible].planche.trouver(E.projet.livrees[t.cible], t.s, t.y); if (!el) return;
  e.stopPropagation(); e.preventDefault();          // la caméra ne bouge pas pendant qu'on déplace un élément
  E.choisir(el, t.cible); glisse = { ...t, el, bouge: false };
  $('vue3d').classList.add('glisse');
}, true);
addEventListener('pointermove', (e) => {
  if (!glisse) return;
  const t = toucher(e); if (!t || t.cible !== glisse.cible || t.vue !== glisse.vue) return;
  E.deplacer(glisse.el, t.s - glisse.s, t.y - glisse.y); glisse.s = t.s; glisse.y = t.y; glisse.bouge = true; E.direct();
});
addEventListener('pointerup', () => {
  if (!glisse) return;
  if (glisse.bouge) { E.valider(); E.dessinerProprietes(); }
  glisse = null; $('vue3d').classList.remove('glisse');
});

document.querySelectorAll('[data-cible]').forEach((b) => b.onclick = () => E.choisirCible(b.dataset.cible));
document.querySelectorAll('[data-ajout]').forEach((b) => b.onclick = () => E.ajouter(b.dataset.ajout));
$('annuler').onclick = () => E.annuler(); $('refaire').onclick = () => E.refaire();
$('exporter').onclick = () => E.exporter();
$('importer').onclick = () => $('fichierProjet').click();
$('fichierProjet').onchange = (e) => { if (e.target.files[0]) E.importer(e.target.files[0]); e.target.value = ''; };
$('repartir').onclick = () => { if (confirm('Remettre la livrée de départ sur le ' + (E.cible === 'camion' ? 'camion' : 'la remorque') + ' ? (Annuler reste possible)')) E.repartir(depart); };

// Raccourcis : 1 avant, 2 arrière, 3 gauche, 4 droite, 5 dessus, 6 trois-quarts
const touches = { 1: 'avant', 2: 'arriere', 3: 'gauche', 4: 'droite', 5: 'dessus', 6: 'trois_quarts' };
addEventListener('keydown', (e) => {
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
  const k = e.key.toLowerCase();
  if (e.ctrlKey && k === 'z') { e.preventDefault(); e.shiftKey ? E.refaire() : E.annuler(); return; }
  if (e.ctrlKey && k === 'y') { e.preventDefault(); E.refaire(); return; }
  if (e.ctrlKey && k === 'd') { e.preventDefault(); E.dupliquer(); return; }
  if ((k === 'delete' || k === 'backspace') && E.choisi) { e.preventDefault(); E.supprimer(); return; }
  // flèches : déplacer l'élément choisi de 5 cm (1 cm avec Maj)
  const fl = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, 1], arrowdown: [0, -1] }[k];
  if (fl && E.choisi && E.choisi.type !== 'fond') { e.preventDefault(); const p = e.shiftKey ? 0.01 : 0.05; E.deplacer(E.choisi, fl[0] * p, fl[1] * p); E.valider(); E.dessinerProprietes(); return; }
  if (touches[e.key]) S.vue(touches[e.key]);
});

// essais automatiques : élément sous un point de l'écran
window.__toucher = (e) => { const t = toucher(e); return t ? { ...t, el: etat[t.cible].planche.trouver(E.projet.livrees[t.cible], t.s, t.y) } : null; };
window.TSCF_etat = etat; window.TSCF_mode = (m) => document.querySelector(`[data-mode="${m}"]`).click();
demarrer().catch((e) => { console.error(e); statut('Erreur : ' + e.message, true); });
