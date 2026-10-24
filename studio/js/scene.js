// TSCF Spartan Studio : scène 3D (rendu, lumière, caméra libre, vues prédéfinies).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export const ECLAIRAGES = {
  studio: { nom: 'Studio photo', fond: 0x101115, reflets: 'studio', env: 1.0, cle: [0xffffff, 3.2], dir: [-6, 12, -8], expo: 1.0, sol: 0x111114 },
  jour: { nom: 'Plein jour', fond: 0x9fb6cc, reflets: 'piece', env: 0.9, cle: [0xfff4e2, 5.0], dir: [-8, 16, -4], expo: 0.95, sol: 0x5d5f63 },
  couchant: { nom: 'Coucher de soleil', fond: 0x2a1621, reflets: 'studio', env: 0.6, cle: [0xff9a4d, 4.2], dir: [-14, 4, -6], expo: 1.05, sol: 0x1d1416 },
  nuit: { nom: 'Nuit', fond: 0x05070c, reflets: 'studio', env: 0.15, cle: [0x7d95ff, 0.8], dir: [6, 10, 6], expo: 1.2, sol: 0x07080b },
};

// Studio photo : pièce sombre et grandes boîtes à lumière, comme pour photographier une carrosserie laquée
function studioPhoto() {
  const s = new THREE.Scene();
  s.add(new THREE.Mesh(new THREE.BoxGeometry(60, 30, 60), new THREE.MeshBasicMaterial({ color: 0x08080a, side: THREE.BackSide })));
  const boite = (l, h, x, y, z, rx, ry, k, teinte = [1, 1, 1]) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(l, h), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
    m.material.color.setRGB(teinte[0] * k, teinte[1] * k, teinte[2] * k); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); s.add(m);
  };
  boite(30, 5, 0, 14, 0, Math.PI / 2, 0, 6);                 // bande de plafond
  boite(26, 4, -18, 6, 0, 0, Math.PI / 2, 3.5);              // boîte latérale gauche
  boite(26, 4, 18, 6, 0, 0, -Math.PI / 2, 3.5);              // boîte latérale droite
  boite(10, 6, 0, 5, -22, 0, 0, 2.5, [1, 0.9, 0.75]);         // face avant, légèrement chaude
  boite(10, 6, 0, 5, 22, 0, Math.PI, 2, [0.85, 0.9, 1]);    // face arrière, légèrement froide
  boite(60, 60, 0, -1, 0, -Math.PI / 2, 0, 0.25, [1, 0.85, 0.7]);            // rebond du sol
  return s;
}

export class Scene3D {
  constructor(conteneur) {
    this.el = conteneur;
    const r = this.rendu = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    r.setPixelRatio(Math.min(2, devicePixelRatio)); r.toneMapping = THREE.ACESFilmicToneMapping; r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
    conteneur.appendChild(r.domElement);
    const s = this.scene = new THREE.Scene();
    const pm = new THREE.PMREMGenerator(r);
    this.envs = { piece: pm.fromScene(new RoomEnvironment(), 0.04).texture, studio: pm.fromScene(studioPhoto(), 0.02).texture };
    this.cam = new THREE.PerspectiveCamera(32, 1, 0.1, 400);
    this.cam.position.set(-14, 5, -16);
    const c = this.ctl = new OrbitControls(this.cam, r.domElement);
    c.enableDamping = true; c.dampingFactor = 0.08; c.maxPolarAngle = Math.PI * 0.495; c.minDistance = 1.2; c.maxDistance = 70; c.target.set(0, 1.8, 0);
    const cle = this.cle = new THREE.DirectionalLight(0xffffff, 3);
    cle.castShadow = true; cle.shadow.mapSize.set(4096, 4096); cle.shadow.bias = -0.0004; cle.shadow.normalBias = 0.02;
    Object.assign(cle.shadow.camera, { left: -14, right: 14, top: 14, bottom: -14, near: 1, far: 80 });
    s.add(cle, cle.target);
    this.contre = new THREE.DirectionalLight(0xbfd2ff, 0.8); this.contre.position.set(10, 6, 14); s.add(this.contre);
    const sol = this.sol = new THREE.Mesh(new THREE.CircleGeometry(60, 96), new THREE.MeshStandardMaterial({ color: 0x17181c, roughness: 0.7, metalness: 0 }));
    sol.rotation.x = -Math.PI / 2; sol.receiveShadow = true; s.add(sol);
    this.racine = new THREE.Group(); s.add(this.racine);
    this.anim = null;
    new ResizeObserver(() => this.taille()).observe(conteneur); this.taille();
    // Double-clic : zoom sur le détail visé
    this.rayon = new THREE.Raycaster();
    r.domElement.addEventListener('dblclick', (e) => this.zoomDetail(e));
    const boucle = (t) => { requestAnimationFrame(boucle); if (!this.enPause) this.pas(t); };
    requestAnimationFrame(boucle);
    this.eclairage('studio');
  }
  taille() {
    const w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    this.rendu.setSize(w, h, false); this.cam.aspect = w / h; this.cam.updateProjectionMatrix();
  }
  eclairage(nom) {
    const E = ECLAIRAGES[nom]; this.nomEclairage = nom;
    this.scene.background = new THREE.Color(E.fond); this.scene.environment = this.envs[E.reflets]; this.scene.environmentIntensity = E.env;
    this.cle.color.set(E.cle[0]); this.cle.intensity = E.cle[1]; this.cle.position.set(...E.dir);
    this.rendu.toneMappingExposure = E.expo; this.sol.material.color.set(E.sol);
    this.contre.intensity = nom === 'nuit' ? 0.25 : 0.8;
    this.scene.fog = new THREE.Fog(E.fond, 45, 90);
  }
  // Boîte englobante des objets visibles
  boite() {
    const b = new THREE.Box3();
    this.racine.traverseVisible((o) => { if (o.isMesh) b.expandByObject(o); });
    if (b.isEmpty()) b.set(new THREE.Vector3(-1, 0, -1), new THREE.Vector3(1, 2, 1));
    return b;
  }
  vue(nom, duree = 650) {
    const b = this.boite(), c = b.getCenter(new THREE.Vector3()), t = b.getSize(new THREE.Vector3());
    const rayon = t.length() / 2, fov = (this.cam.fov * Math.PI) / 180;
    const d = (rayon / Math.sin(fov / 2)) * 0.82;
    const dirs = {
      avant: [0, 0.12, -1], arriere: [0, 0.12, 1], gauche: [-1, 0.08, 0], droite: [1, 0.08, 0], dessus: [0.001, 1, 0.12],
      trois_quarts: [-0.75, 0.32, -0.62], trois_quarts_arriere: [0.7, 0.3, 0.68],
    };
    const v = new THREE.Vector3(...(dirs[nom] || dirs.trois_quarts)).normalize();
    // de face ou de dos, l'ensemble paraît étroit : on se rapproche
    const k = nom === 'avant' || nom === 'arriere' ? Math.max(t.x, t.y) / t.length() * 2.3 : nom === 'dessus' ? 0.9 : 1;
    this.aller(c.clone().add(v.multiplyScalar(d * k)), c.clone().setY(Math.max(1.2, c.y * 0.9)), duree);
  }
  aller(pos, cible, duree = 650) {
    this.anim = { p0: this.cam.position.clone(), c0: this.ctl.target.clone(), p1: pos, c1: cible, t0: performance.now(), d: duree };
  }
  zoomDetail(e) {
    const r = this.rendu.domElement.getBoundingClientRect();
    this.rayon.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), this.cam);
    const hit = this.rayon.intersectObjects(this.racine.children, true).find((h) => h.object.visible);
    if (!hit) return;
    const dir = this.cam.position.clone().sub(hit.point).normalize();
    this.aller(hit.point.clone().add(dir.multiplyScalar(3.2)), hit.point.clone());
  }
  pas() {
    if (this.anim) {
      const a = this.anim, u = Math.min(1, (performance.now() - a.t0) / a.d), e = u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
      this.cam.position.lerpVectors(a.p0, a.p1, e); this.ctl.target.lerpVectors(a.c0, a.c1, e);
      if (u >= 1) this.anim = null;
    }
    this.ctl.update();
    this.rendu.render(this.scene, this.cam);
  }
  // Essais automatiques : image fixe, caméra posée directement
  figer(nom) { this.enPause = true; this.vue(nom, 1); this.anim.t0 -= 10; this.pas(); this.pas(); }
  capture() { return this.rendu.domElement.toDataURL('image/png'); }
}
