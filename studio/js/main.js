// TSCF Spartan Studio : interface de l'atelier (phase 2 : ensemble 3D, vues, éclairages, livrée d'essai).
import * as THREE from 'three';
import { Scene3D, ECLAIRAGES } from './scene.js';
import { tracteurProvisoire, citerneProvisoire, chargerGlb } from './vehicules.js';
import { decoupe, projeter } from './projection.js';
import { Planche, livreeEssai } from './livree.js';

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
  planche.peindre(livreeEssai(cible, plan.L, plan.H));
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
  placer(); avertir();
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
  await Promise.all([choisir('camion', $('choixCamion').value), choisir('remorque', $('choixRemorque').value)]);
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
// Raccourcis : 1 avant, 2 arrière, 3 gauche, 4 droite, 5 dessus, 6 trois-quarts
const touches = { 1: 'avant', 2: 'arriere', 3: 'gauche', 4: 'droite', 5: 'dessus', 6: 'trois_quarts' };
addEventListener('keydown', (e) => { if (e.target.tagName !== 'INPUT' && touches[e.key]) S.vue(touches[e.key]); });

window.TSCF_etat = etat; window.TSCF_mode = (m) => document.querySelector(`[data-mode="${m}"]`).click();
demarrer().catch((e) => { console.error(e); statut('Erreur : ' + e.message, true); });
