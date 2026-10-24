// TSCF Spartan Studio : projection de la livrée sur la carrosserie.
// La livrée est dessinée « à plat », en mètres, sur une planche découpée en vues : côté gauche, côté droit, dessus, avant, arrière.
// Chaque triangle peint reçoit des coordonnées de texture selon la vue vers laquelle il est tourné.
// Règle TSCF : les deux côtés sont lus depuis l'extérieur, jamais en miroir ; une position se donne en mètres depuis l'avant.
import * as THREE from 'three';

const ECART = 0.2; // marge entre deux vues sur la planche (m), évite les bavures

// Découpe de la planche pour une boîte englobante (repère SCS : x à droite, y en haut, avant vers -z)
export function decoupe(box, pxParM) {
  const L = box.max.z - box.min.z, H = box.max.y - box.min.y, W = box.max.x - box.min.x;
  const R = {
    gauche: { x: 0, y: 0, w: L, h: H },
    droite: { x: 0, y: H + ECART, w: L, h: H },
    dessus: { x: 0, y: 2 * (H + ECART), w: L, h: W },
    avant: { x: 0, y: 2 * (H + ECART) + W + ECART, w: W, h: H },
    arriere: { x: W + ECART, y: 2 * (H + ECART) + W + ECART, w: W, h: H },
  };
  const largeur = Math.max(L, 2 * W + ECART), hauteur = 3 * H + W + 3 * ECART;
  let k = pxParM;
  const maxi = 4096;
  if (Math.max(largeur, hauteur) * k > maxi) k = maxi / Math.max(largeur, hauteur);
  return { box: box.clone(), L, H, W, R, k, px: Math.ceil(largeur * k), py: Math.ceil(hauteur * k) };
}

// Vue d'un triangle : l'orientation vient de sa normale (les côtés sont favorisés : les flancs arrondis d'une citerne restent
// sur le côté), le côté vient de sa position (certains modèles ont des normales tournées vers l'intérieur)
function vue(nx, ny, nz, x, z, box) {
  const ax = Math.abs(nx) * 1.35, ay = Math.abs(ny), az = Math.abs(nz) * 1.1;
  if (ax >= ay && ax >= az) return x < (box.min.x + box.max.x) / 2 ? 'gauche' : 'droite';
  if (az >= ay) return z < (box.min.z + box.max.z) / 2 ? 'avant' : 'arriere';
  return 'dessus';
}

// Coordonnées (a, b) en mètres dans une vue : a vers la droite de la personne qui regarde, b vers le bas depuis le haut de la vue
export function versVue(nomVue, x, y, z, box) {
  const { min, max } = box;
  switch (nomVue) {
    case 'gauche': return [z - min.z, max.y - y];
    case 'droite': return [max.z - z, max.y - y];
    case 'dessus': return [z - min.z, x - min.x];
    case 'avant': return [max.x - x, max.y - y];
    default: return [x - min.x, max.y - y];
  }
}

// Géométrie (repère du véhicule) -> géométrie non indexée avec l'attribut uv projeté
export function projeter(geo, plan) {
  const g = geo.index ? geo.toNonIndexed() : geo.clone();
  const P = g.attributes.position, N = g.attributes.normal;
  const uv = new Float32Array(P.count * 2);
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3();
  for (let i = 0; i < P.count; i += 3) {
    if (N) { n.set(0, 0, 0); for (let j = 0; j < 3; j++) n.x += N.getX(i + j), n.y += N.getY(i + j), n.z += N.getZ(i + j); }
    else { a.fromBufferAttribute(P, i); b.fromBufferAttribute(P, i + 1); c.fromBufferAttribute(P, i + 2); n.subVectors(c, b).cross(a.sub(b)); }
    const cx = (P.getX(i) + P.getX(i + 1) + P.getX(i + 2)) / 3, cz = (P.getZ(i) + P.getZ(i + 1) + P.getZ(i + 2)) / 3;
    const v = vue(n.x, n.y, n.z, cx, cz, plan.box), r = plan.R[v];
    for (let j = 0; j < 3; j++) {
      const [s, t] = versVue(v, P.getX(i + j), P.getY(i + j), P.getZ(i + j), plan.box);
      uv[(i + j) * 2] = ((r.x + s) * plan.k) / plan.px;
      uv[(i + j) * 2 + 1] = 1 - ((r.y + t) * plan.k) / plan.py;
    }
  }
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return g;
}
