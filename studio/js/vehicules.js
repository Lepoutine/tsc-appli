// TSCF Spartan Studio : véhicules de l'aperçu.
// - Modèles réels : fichiers .glb convertis depuis les modèles SCS du jeu ou des mods (outils/pmg_vers_glb.py), listés dans modeles/modeles.json.
// - Modèles provisoires : tracteur type Scania R et citerne génériques dessinés ici, signalés comme tels à l'écran.
// Repère SCS : x à droite, y en haut, avant vers -z, mètres. Origine des remorques : sol, sous le pivot d'attelage décalé (repère « hook »).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export const MATIERES = {
  noir: () => new THREE.MeshStandardMaterial({ color: 0x0c0c0e, roughness: 0.62, metalness: 0.1 }),
  plastique: () => new THREE.MeshStandardMaterial({ color: 0x151517, roughness: 0.8 }),
  chrome: () => new THREE.MeshStandardMaterial({ color: 0xe8e8ec, roughness: 0.08, metalness: 1 }),
  alu: () => new THREE.MeshStandardMaterial({ color: 0xc9cbd0, roughness: 0.28, metalness: 1 }),
  verre: () => new THREE.MeshPhysicalMaterial({ color: 0x0a0d12, roughness: 0.04, metalness: 0.2, clearcoat: 1, transparent: true, opacity: 0.88 }),
  feu: () => new THREE.MeshStandardMaterial({ color: 0x3a0406, emissive: 0xd0101a, emissiveIntensity: 0.6, roughness: 0.2 }),
  phare: () => new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff3dd, emissiveIntensity: 0.8, roughness: 0.1 }),
  ambre: () => new THREE.MeshStandardMaterial({ color: 0x402400, emissive: 0xffa21a, emissiveIntensity: 0.9, roughness: 0.2 }),
  pneu: () => new THREE.MeshStandardMaterial({ color: 0x111112, roughness: 0.92 }),
  // Peinture : la couleur et la matière viennent de la planche de livrée ; vernis par-dessus
  peinture: () => new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 1, metalness: 1, clearcoat: 1, clearcoatRoughness: 0.06 }),
};

function mesh(geo, mat, x = 0, y = 0, z = 0, peint = false) {
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true;
  if (peint) m.userData.peint = true;
  return m;
}

// Roue : pneu en révolution + jante chromée ; axe le long de x
function roue(rayon = 0.52, largeur = 0.32, jumelee = false) {
  const g = new THREE.Group(), r0 = rayon * 0.62;
  const prof = [[r0, -largeur / 2], [rayon - 0.05, -largeur / 2], [rayon, -largeur / 2 + 0.05], [rayon, largeur / 2 - 0.05], [rayon - 0.05, largeur / 2], [r0, largeur / 2]]
    .map(([r, y]) => new THREE.Vector2(r, y));
  const pneu = new THREE.LatheGeometry(prof, 40); pneu.rotateZ(Math.PI / 2);
  const jante = new THREE.CylinderGeometry(r0, r0, largeur * 0.9, 32, 1); jante.rotateZ(Math.PI / 2);
  const moyeu = new THREE.CylinderGeometry(r0 * 0.35, r0 * 0.4, largeur * 0.96, 16); moyeu.rotateZ(Math.PI / 2);
  for (const dx of jumelee ? [-largeur / 2 - 0.01, largeur / 2 + 0.01] : [0]) {
    g.add(mesh(pneu, MATIERES.pneu(), dx)); g.add(mesh(jante, MATIERES.chrome(), dx)); g.add(mesh(moyeu, MATIERES.noir(), dx));
  }
  return g;
}

// Tracteur provisoire type Scania R (cabine haute) : proportions d'un 4x2, sans prétendre au modèle exact
export function tracteurProvisoire() {
  const g = new THREE.Group(); g.name = 'Tracteur provisoire';
  const M = MATIERES, peinture = M.peinture();
  const av = -4.85; // face avant du pare-chocs ; sellette en z = 0
  const cab = new RoundedBoxGeometry(2.5, 2.85, 2.3, 4, 0.14);
  g.add(mesh(cab, peinture, 0, 1.1 + 2.85 / 2, av + 0.12 + 1.15, true));
  // pare-chocs et calandre
  g.add(mesh(new RoundedBoxGeometry(2.5, 0.62, 0.55, 3, 0.08), peinture, 0, 0.78, av + 0.28, true));
  g.add(mesh(new THREE.BoxGeometry(1.7, 0.9, 0.04), M.plastique(), 0, 1.72, av + 0.1));
  for (let i = 0; i < 6; i++) g.add(mesh(new THREE.BoxGeometry(1.62, 0.035, 0.03), M.chrome(), 0, 1.36 + i * 0.14, av + 0.08));
  // pare-brise, pare-soleil, vitres latérales
  const pb = mesh(new THREE.BoxGeometry(2.26, 1.0, 0.03), M.verre(), 0, 2.85, av + 0.13); pb.rotation.x = -0.1; g.add(pb);
  g.add(mesh(new RoundedBoxGeometry(2.42, 0.18, 0.32, 2, 0.05), peinture, 0, 3.5, av + 0.05, true));
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.03, 0.78, 0.95), M.verre(), sx * 1.252, 2.78, av + 0.75));
  // phares, feux de toit, rétroviseurs, marchepieds
  for (const sx of [-1, 1]) {
    g.add(mesh(new RoundedBoxGeometry(0.55, 0.2, 0.08, 2, 0.04), M.phare(), sx * 0.9, 1.0, av - 0.01));
    const bras = mesh(new THREE.BoxGeometry(0.32, 0.04, 0.04), M.noir(), sx * 1.4, 2.95, av + 0.35); g.add(bras);
    g.add(mesh(new RoundedBoxGeometry(0.1, 0.62, 0.28, 2, 0.04), M.noir(), sx * 1.56, 2.75, av + 0.35));
    for (let k = 0; k < 2; k++) g.add(mesh(new THREE.BoxGeometry(0.06, 0.04, 0.42), M.alu(), sx * 1.24, 0.55 + k * 0.33, av + 1.6));
  }
  for (let i = 0; i < 6; i++) g.add(mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.08, 16).rotateX(Math.PI / 2), M.ambre(), -0.75 + i * 0.3, 4.03, av + 0.35));
  g.add(mesh(new THREE.BoxGeometry(2.0, 0.08, 0.1), M.chrome(), 0, 4.03, av + 0.42));
  // jupes latérales peintes, châssis, réservoirs, ailes, sellette
  for (const sx of [-1, 1]) g.add(mesh(new RoundedBoxGeometry(0.06, 0.62, 2.4, 2, 0.02), peinture, sx * 1.22, 0.72, -1.75, true));
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.09, 0.3, 6.0), M.noir(), sx * 0.43, 0.77, -1.6));
  g.add(mesh(new THREE.CylinderGeometry(0.33, 0.33, 1.3, 24).rotateX(Math.PI / 2), M.alu(), -0.82, 0.8, -1.7));
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.62, 0.06, 1.15), M.plastique(), sx * 0.95, 1.12, 0.12));
  g.add(mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.12, 32), M.noir(), 0, 0.93, 0));
  // roues : essieu avant simple, pont arrière jumelé
  for (const [z, jum] of [[-3.55, false], [0.15, true]]) for (const sx of [-1, 1]) {
    const r = roue(0.52, 0.32, jum); r.position.set(sx * (jum ? 0.92 : 1.02), 0.52, z); g.add(r);
  }
  return { groupe: g, nom: 'Scania R (modèle provisoire)', reel: false, sellette: new THREE.Vector3(0, 0.97, 0) };
}

// Citerne provisoire : cuve elliptique sur châssis, trois essieux
export function citerneProvisoire() {
  const g = new THREE.Group(); g.name = 'Citerne provisoire';
  const M = MATIERES, L = 12.4, peinture = M.peinture();
  const cuve = new THREE.CylinderGeometry(1, 1, L, 64, 1); cuve.rotateX(Math.PI / 2); cuve.scale(1.25, 1.1, 1);
  const fond = new THREE.SphereGeometry(1, 48, 16, 0, Math.PI * 2, 0, Math.PI / 2); fond.scale(1.25, 1.1, 0.35);
  const fAv = fond.clone().rotateX(-Math.PI / 2).translate(0, 0, -L / 2), fAr = fond.clone().rotateX(Math.PI / 2).translate(0, 0, L / 2);
  const tout = mergeGeometries([cuve.toNonIndexed(), fAv.toNonIndexed(), fAr.toNonIndexed()]); tout.computeVertexNormals();
  g.add(mesh(tout, peinture, 0, 2.55, 0.4, true));
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.1, 0.32, 13.2), M.noir(), sx * 0.5, 1.15, 0.3));
  g.add(mesh(new THREE.BoxGeometry(2.0, 0.06, 12.6), M.alu(), 0, 3.72, 0.4));
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.05, 0.05, 12.4), M.chrome(), sx * 1.0, 3.86, 0.4));
  for (const z of [1.68, 2.99, 4.29]) for (const sx of [-1, 1]) { const r = roue(0.5, 0.42); r.position.set(sx * 1.0, 0.5, z); g.add(r); }
  for (const sx of [-1, 1]) g.add(mesh(new THREE.BoxGeometry(0.4, 0.14, 0.05), M.feu(), sx * 0.9, 0.95, 6.82));
  g.add(mesh(new THREE.BoxGeometry(2.5, 0.12, 0.12), M.noir(), 0, 0.75, 6.8));
  return { groupe: g, nom: 'Citerne (modèle provisoire)', reel: false, hook: new THREE.Vector3(0, 0.97, -4.99) };
}

// Modèle réel converti : les matières sont reprises d'après la catégorie écrite par le convertisseur
const CATEGORIE = { peinture: 'peinture', chrome: 'chrome', alu: 'alu', verre: 'verre', feu: 'feu', noir: 'noir', pneu: 'pneu' };
export async function chargerGlb(url, nom, type) {
  const gltf = await new GLTFLoader().loadAsync(url);
  const g = gltf.scene, locs = {};
  const peinture = MATIERES.peinture();
  g.traverse((o) => {
    if (o.name && o.name.startsWith('loc:')) locs[o.name.slice(4)] = o;
    if (!o.isMesh) return;
    const cat = o.material?.userData?.categorie || o.material?.name;
    o.castShadow = true; o.receiveShadow = true;
    if (cat === 'peinture') { o.material = peinture; o.userData.peint = true; }
    else if (CATEGORIE[cat]) o.material = MATIERES[CATEGORIE[cat]]();
    else { const c = o.material.color; const m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.55, metalness: 0.1 }); o.material = m; }
  });
  const v = { groupe: g, nom, reel: true };
  g.updateMatrixWorld(true);
  if (type === 'remorque') v.hook = locs.hook ? locs.hook.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(0, 0.97, -5);
  else v.sellette = locs.fifth_wheel ? locs.fifth_wheel.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(0, 0.97, 0);
  return v;
}
