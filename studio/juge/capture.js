// Juge de l'atelier : captures automatiques des rendus (page juge_capture.html = index.html + ce script, rien d'autre ne change).
// Quand l'atelier est pret, prend les vues de cote et de 3/4 en plein jour et au couchant, et les envoie au lanceur
// (juge_lancer.ps1) qui les range dans juge\captures_atelier. Seul le dessin 3D est capture, jamais les panneaux.
const VUES = ['gauche', 'droite', 'trois_quarts', 'trois_quarts_arriere'];
const LUMIERES = ['jour', 'couchant'];
const attendre = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  for (let i = 0; i < 600 && !document.body.classList.contains('pret'); i++) await attendre(200);
  const S = window.TSCF_STUDIO, envoi = (nom, corps) => fetch('/juge/capture?nom=' + encodeURIComponent(nom), { method: 'POST', body: corps });
  if (!S || !document.body.classList.contains('pret')) { await fetch('/juge/fin?erreur=atelier_pas_pret', { method: 'POST' }); return; }
  await attendre(1500);   // textures et polices
  for (const l of LUMIERES) {
    S.eclairage(l); await attendre(600);
    for (const v of VUES) { S.figer(v); await attendre(400); await envoi(l + '_' + v, S.capture()); }
  }
  await fetch('/juge/fin', { method: 'POST' });
  document.title = 'Captures terminees';
})();
