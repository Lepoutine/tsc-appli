/* TSC Sound Forge - interface de l'atelier (phase 1 : studio + analyse) */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const SF = window.SF;
  const COUL = ['#d9202b', '#e2b04a', '#ff7a3d', '#c46bff', '#3fa9f5', '#2fd16b', '#8b8f99', '#ff4b8b'];
  const CAMIONS_DEFAUT = [
    { id: 'scania.r_2016', nom: 'Scania R 2016', moteurs: ['DC16 V8 (sound_hi)', 'DC13 (sound_lo)'] },
    { id: 'scania.s_2016', nom: 'Scania S 2016', moteurs: ['DC16 V8 (sound_hi)', 'DC13 (sound_lo)'] },
    { id: 'volvo.fh_2021', nom: 'Volvo FH 2021', moteurs: ['D13 (engine_hi)', 'D13 (engine_lo)'] }
  ];

  /* ---------- état ---------- */
  let P = { nom: 'Mon_son_moteur', camion: 'scania.r_2016', moteur: '', couches: [] };
  const bufs = {};            // id -> AudioBuffer
  let sel = null, avant = false, boucleOn = false, ana = null, camSel = null, filtreEtat = '';
  const moteur = new SF.Moteur();

  function toast(t) { const e = $('toast'); e.textContent = t; e.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(() => { e.hidden = true; }, 3200); }
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const nomPropre = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'Mon_son_moteur';
  const tps = s => { s = Math.max(0, s || 0); const m = Math.floor(s / 60); return String(m).padStart(2, '0') + ':' + (s - m * 60).toFixed(3).padStart(6, '0'); };

  /* ---------- sauvegarde locale (rien à ressaisir après une mise à jour) ---------- */
  let db = null;
  function ouvreDb() {
    return new Promise(ok => {
      try {
        const r = indexedDB.open('tsc_sound_forge', 1);
        r.onupgradeneeded = () => r.result.createObjectStore('sons');
        r.onsuccess = () => { db = r.result; ok(db); };
        r.onerror = () => ok(null);
      } catch (e) { ok(null); }
    });
  }
  function dbPut(id, val) { try { if (db) db.transaction('sons', 'readwrite').objectStore('sons').put(val, id); } catch (e) {} }
  function dbDel(id) { try { if (db) db.transaction('sons', 'readwrite').objectStore('sons').delete(id); } catch (e) {} }
  function dbGet(id) { return new Promise(ok => { try { const r = db.transaction('sons').objectStore('sons').get(id); r.onsuccess = () => ok(r.result); r.onerror = () => ok(null); } catch (e) { ok(null); } }); }
  function sauve() { try { localStorage.setItem('tsc_forge_projet', JSON.stringify(P)); } catch (e) {} majProjet(); }

  /* ---------- import ---------- */
  function devineRole(nom) {
    const n = nom.toLowerCase();
    if (/valve.?open|clapet.?(ouv|on)/.test(n)) return 'clapet_on';
    if (/valve.?clos|clapet.?(ferm|off)|op.?valve/.test(n)) return 'clapet_off';
    if (/(^|[^a-z])(rv8)?op[ _]?\d{3,4}|_op_|clapet|open.?pipe/.test(n) && /\d{3,4}/.test(n)) return 'clapet';
    if (/turbo|sifl|whistle/.test(n)) return 'turbo';
    if (/demar|start/.test(n)) return 'demarrage';
    if (/arret|stop|shut/.test(n)) return 'arret';
    if (/brake|frein_moteur/.test(n)) return 'autre';
    if (/unload|no_?fuel|decel|sans|coast|lift|\d{3,4}_idle/.test(n)) return 'sans';
    if (/ralenti|idle/.test(n)) return 'ralenti';
    if (/charge|accel|load|on_|_on/.test(n)) return 'charge';
    return /\d{3,4}/.test(n) ? 'charge' : 'autre';
  }
  function devineRpm(nom, role) {
    const m = nom.match(/(\d{3,4})/); const v = m ? +m[1] : 0;
    if (v >= 400 && v <= 2600) return v;
    const c = nom.match(/_(\d{2})(?:\.\w+)?$/); // ex. loaded_sc_v8_09 = 900 tr/min
    if (c && +c[1] >= 4 && +c[1] <= 26 && /load/.test(nom.toLowerCase())) return +c[1] * 100;
    return SF.ROLES[role].rpm || 1200;
  }
  async function importe(files) {
    const liste = Array.from(files || []); if (!liste.length) return;
    let ok = 0;
    for (const f of liste) {
      try {
        const ab = await f.arrayBuffer();
        const b = await SF.decode(ab);
        const id = 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
        const role = devineRole(f.name);
        const c = { id, fichier: f.name, nom: f.name.replace(/\.[^.]+$/, ''), role, rpm: devineRpm(f.name, role),
          gain: 0, bas: 0, haut: 0, fondu: 150, boucle: SF.ROLES[role].boucle, norm: false,
          debut: 0, fin: b.duration, duree: b.duration, sr: b.sampleRate, canaux: b.numberOfChannels,
          licence: 'perso', source: '', couleur: COUL[P.couches.length % COUL.length] };
        bufs[id] = b; P.couches.push(c); dbPut(id, ab); ok++;
        if (!sel) sel = id;
      } catch (e) { toast('« ' + f.name + ' » n\'a pas pu être lu (format non pris en charge).'); }
    }
    if (ok) { sauve(); rendTout(); toast(ok + ' son' + (ok > 1 ? 's importés' : ' importé') + '.'); }
  }

  /* ---------- dessin d'une forme d'onde ---------- */
  function onde(cv, c, opts) {
    const b = bufs[c.id]; const w = cv.clientWidth || 300, h = cv.clientHeight || 50;
    const r = window.devicePixelRatio || 1; cv.width = Math.round(w * r); cv.height = Math.round(h * r);
    const g = cv.getContext('2d'); g.setTransform(r, 0, 0, r, 0, 0); g.clearRect(0, 0, w, h);
    if (!b) { g.fillStyle = '#8b8f99'; g.font = '12px Inter,Segoe UI,sans-serif'; g.fillText('son à réimporter', 8, h / 2 + 4); return; }
    const pk = SF.pics(b, Math.max(10, Math.floor(w)), 0, b.duration), D = b.duration;
    const x0 = c.debut / D * w, x1 = c.fin / D * w;
    g.fillStyle = c.couleur + '1f'; g.fillRect(x0, 2, x1 - x0, h - 4);
    for (let i = 0; i < pk.length / 2; i++) {
      const dedans = i >= x0 && i <= x1;
      g.fillStyle = dedans ? c.couleur : '#3a2a2d';
      const y0 = h / 2 - pk[i * 2 + 1] * (h / 2 - 3), y1 = h / 2 - pk[i * 2] * (h / 2 - 3);
      g.fillRect(i, y0, 1, Math.max(1, y1 - y0));
    }
    if (opts && opts.edit) {
      if (c.boucle && c.fondu) { const xf = Math.max(x0, x1 - c.fondu / 1000 / D * w); g.fillStyle = 'rgba(226,176,74,.18)'; g.fillRect(xf, 0, x1 - xf, h); }
      g.fillStyle = '#d9202b'; g.fillRect(x0 - 2, 0, 4, h); g.fillRect(x1 - 2, 0, 4, h);
      g.fillRect(x0 - 6, 0, 12, 8); g.fillRect(x1 - 6, 0, 12, 8);
      const pos = SF.position();
      if (pos != null) { const xp = pos / D * w; g.fillStyle = '#e2b04a'; g.fillRect(xp - 1, 0, 2, h); }
    }
  }

  /* ---------- rendu ---------- */
  function rendLib() {
    const L = $('lib');
    if (!P.couches.length) { L.innerHTML = '<div class="vide">Aucun son pour l\'instant.</div>'; return; }
    L.innerHTML = P.couches.map(c => '<button type="button" class="it' + (c.id === sel ? ' on' : '') + '" data-id="' + c.id + '"><i style="background:' + c.couleur + '"></i><b>' + esc(c.fichier) + '</b><small>' +
      (c.sr / 1000).toFixed(c.sr % 1000 ? 1 : 0) + ' kHz · ' + c.duree.toFixed(1) + ' s' + (bufs[c.id] ? '' : ' · à réimporter') + '</small>' + (c.licence === 'refus' ? '<small class="lic">licence refusée : non exporté</small>' : (c.licence === 'ccby' || c.licence === 'mod') && !c.source ? '<small class="lic">auteur à indiquer</small>' : '') + '</button>').join('');
  }
  function rendPistes() {
    const T = $('pistes');
    if (!P.couches.length) { T.innerHTML = '<div class="vide">Les couches de ton moteur s\'afficheront ici.</div>'; return; }
    T.innerHTML = P.couches.map(c => '<button type="button" class="trk' + (c.id === sel ? ' on' : '') + '" data-id="' + c.id + '"><span class="nm"><b>' + esc(SF.ROLES[c.role].court) +
      (c.role === 'charge' || c.role === 'sans' || c.role === 'ralenti' ? ' ' + c.rpm : '') + '</b><small>' + esc(c.fichier) + '</small></span><canvas></canvas></button>').join('');
    T.querySelectorAll('.trk').forEach(el => onde(el.querySelector('canvas'), P.couches.find(c => c.id === el.dataset.id)));
  }
  function couche() { return P.couches.find(c => c.id === sel) || null; }
  function rendEd() {
    const c = couche(); $('ed').hidden = !c; $('edVide').hidden = !!c; $('edNom').textContent = c ? c.fichier : '';
    ['bJoue', 'bStop', 'bBoucle', 'bAvant', 'bSuppr'].forEach(id => { $(id).disabled = !c; });
    if (!c) return;
    $('eRole').value = c.role; $('eRpm').value = c.rpm; $('eGain').value = c.gain; $('eBas').value = c.bas; $('eHaut').value = c.haut;
    $('eFondu').value = c.fondu; $('eBoucle').checked = !!c.boucle; $('eNorm').checked = !!c.norm; $('eLic').value = c.licence || 'perso'; $('eSrc').value = c.source || '';
    $('eRpm').disabled = !(c.role === 'charge' || c.role === 'sans' || c.role === 'ralenti');
    $('eFondu').disabled = !c.boucle;
    sorties(); onde($('wvc'), c, { edit: true });
  }
  function sorties() {
    const c = couche(); if (!c) return;
    $('oRpm').textContent = $('eRpm').disabled ? '—' : c.rpm; $('oGain').textContent = (c.gain > 0 ? '+' : '') + c.gain + ' dB';
    $('oBas').textContent = (c.bas > 0 ? '+' : '') + c.bas + ' dB'; $('oHaut').textContent = (c.haut > 0 ? '+' : '') + c.haut + ' dB';
    $('oFondu').textContent = c.fondu + ' ms';
  }
  function rendRoles() {
    const n = r => P.couches.filter(c => c.role === r).length;
    const items = [
      ['Ralenti', n('ralenti') >= 1, '1 son, régime stable vers 600 tr/min'],
      ['Accélération (charge)', n('charge') >= 2, '2 à 5 régimes, pied au plancher'],
      ['Lever de pied', n('sans') >= 1, 'conseillé : mêmes régimes sans charge'],
      ['Turbo', n('turbo') >= 1, 'facultatif'],
      ['Démarrage', n('demarrage') >= 1, 'facultatif (start_bad dans le jeu)'],
      ['Clapet ouvert', n('clapet') >= 2, 'facultatif : TSC Clapet, 2 régimes ou plus, et un son d\'ouverture']
    ];
    $('roles').innerHTML = items.map(i => '<li class="' + (i[1] ? 'ok' : '') + '">' + (i[1] ? '✓ ' : '') + i[0] + ' <span class="mut">· ' + i[2] + '</span></li>').join('');
  }
  function majProjet() {
    const cam = camions().find(k => k.id === P.camion);
    const nbSim = P.couches.filter(c => SF.ROLES[c.role].sim).length;
    $('kvProjet').innerHTML = '<span>Nom</span><b>' + esc(P.nom) + '</b><span>Camion</span><b>' + esc(cam ? cam.nom : P.camion) + '</b><span>Moteur</span><b>' + esc(P.moteur || '—') +
      '</b><span>Couches</span><b>' + P.couches.length + ' (' + nbSim + ' dans le simulateur)</b><span>Dossier final</span><b class="mono" style="font-size:11px">Bureau\\TSC_Sound_Forge\\' + esc(P.nom) + '</b>';
    const aCharge = P.couches.some(c => c.role === 'charge'), aRal = P.couches.some(c => c.role === 'ralenti');
    const E = [['Sons importés', P.couches.length > 0], ['Ralenti + régimes en charge', aRal && aCharge], ['Écouté au simulateur', !!majProjet.ecoute], ['Couches exportées (WAV 48 kHz)', !!majProjet.exporte],
      ['Projet FMOD (phase 3)', false], ['Vraie banque compilée par FMOD (phase 4)', false], ['Mod ETS2 + test en jeu (phases 5-6)', false]];
    let cur = false;
    $('etapes').innerHTML = E.map(e => { let k = e[1] ? 'ok' : (!cur ? (cur = true, 'cur') : ''); return '<li class="' + k + '">' + e[0] + '</li>'; }).join('');
  }
  function rendTout() { rendLib(); rendPistes(); rendEd(); rendRoles(); majProjet(); simMaj(); rendGen(); }

  /* ---------- générateur TSC ---------- */
  function rendGen() {
    const refs = P.couches.filter(c => bufs[c.id] && c.licence !== 'tsc' && (c.role === 'ralenti' || c.role === 'charge' || c.role === 'sans'));
    const v = $('gRef').value;
    $('gRef').innerHTML = refs.length ? refs.map(c => '<option value="' + c.id + '">' + esc(SF.ROLES[c.role].court + ' ' + c.rpm + ' · ' + c.fichier) + '</option>').join('') : '<option value="">Importe un son à régime stable</option>';
    if (refs.some(c => c.id === v)) $('gRef').value = v;
    $('bMesure').disabled = !refs.length;
    const E = P.empreinte;
    $('bGenere').disabled = !E;
    $('gEtat').textContent = E ? 'Empreinte gardée : ' + E.ordres.length + ' harmoniques mesurées à ' + E.rpm + ' tr/min, ' + E.cyl + ' cylindres (' + E.date + '). Aucun échantillon audio conservé.' : 'Pas encore d\'empreinte.';
  }
  function mesure() {
    const c = P.couches.find(x => x.id === $('gRef').value); if (!c || !bufs[c.id]) return;
    try {
      const E = SF.empreinte(bufs[c.id], c.debut, c.fin, c.rpm, +$('gCyl').value);
      E.reference = { role: c.role, fichier: c.fichier, licence: c.licence || 'perso' };
      P.empreinte = E;
      if ($('gRetire').checked) { P.couches = P.couches.filter(x => x !== c); delete bufs[c.id]; dbDel(c.id); if (sel === c.id) sel = P.couches[0] ? P.couches[0].id : null; }
      sauve(); rendTout(); toast('Empreinte mesurée. ' + ($('gRetire').checked ? 'Le son de référence a été retiré.' : ''));
    } catch (e) { toast(e.message); }
  }
  async function genere() {
    const E = P.empreinte; if (!E) return;
    $('bGenere').disabled = true; $('gEtat').textContent = 'Fabrication des couches…';
    await new Promise(ok => setTimeout(ok, 30));
    // retire les anciennes couches générées
    P.couches.filter(c => c.licence === 'tsc').forEach(c => { delete bufs[c.id]; dbDel(c.id); });
    P.couches = P.couches.filter(c => c.licence !== 'tsc');
    const mel = +$('gMel').value / 100, plan = [['ralenti', 600, 0.05]];
    SF.REGIMES_GEN.slice(1).forEach(r => { plan.push(['charge', r, 1]); plan.push(['sans', r, 0.1]); });
    let i = 0;
    for (const q of plan) {
      const b = SF.genere(E, { rpm: q[1], charge: q[2], melange: mel, graine: ++i, duree: 2.7 });
      const id = 'g' + Date.now().toString(36) + i, nom = 'tsc_' + q[0] + '_' + q[1] + '.wav';
      bufs[id] = b;
      P.couches.push({ id, fichier: nom, nom: nom.replace('.wav', ''), role: q[0], rpm: q[1], gain: 0, bas: 0, haut: 0, fondu: 0, boucle: true, norm: false,
        debut: 0, fin: b.duration, duree: b.duration, sr: b.sampleRate, canaux: 1, licence: 'tsc', source: 'Générateur TSC, empreinte du ' + E.date, couleur: COUL[P.couches.length % COUL.length] });
      try { dbPut(id, await SF.wav(b).arrayBuffer()); } catch (e) {}
      await new Promise(ok => setTimeout(ok, 0));
    }
    sel = P.couches.find(c => c.licence === 'tsc').id; sauve(); if (moteur.marche) moteur.demarre(P.couches, bufs); rendTout();
    toast(plan.length + ' couches TSC fabriquées. Démarre le moteur pour écouter.');
  }

  /* ---------- camion visé ---------- */
  function camions() {
    if (ana && ana.camions && ana.camions.length) return ana.camions.map(k => ({ id: k.id, nom: k.id, moteurs: (k.moteurs || []).map(m => typeof m === 'string' ? m : (m.nom || m.id || m.fichier || '')).filter(Boolean) }));
    return CAMIONS_DEFAUT;
  }
  function rendCamions() {
    const L = camions();
    if (!L.some(k => k.id === P.camion)) P.camion = L[0].id;
    $('selCamion').innerHTML = L.map(k => '<option value="' + esc(k.id) + '"' + (k.id === P.camion ? ' selected' : '') + '>' + esc(k.nom) + '</option>').join('');
    const cam = L.find(k => k.id === P.camion), M = cam && cam.moteurs.length ? cam.moteurs : ['(moteur à choisir)'];
    if (!M.includes(P.moteur)) P.moteur = M[0];
    $('selMoteur').innerHTML = M.map(m => '<option' + (m === P.moteur ? ' selected' : '') + '>' + esc(m) + '</option>').join('');
  }

  /* ---------- simulateur ---------- */
  let anim = 0, clapetOuvert = false, clapetK = 0, clapetAnim = 0;
  const TOUCHE_CLAPET = 'v'; // en attente du choix de Mendy
  function clapet() {
    if (!P.couches.some(c => c.role === 'clapet')) { toast('Ajoute des couches « Clapet ouvert » pour essayer le clapet.'); return; }
    clapetOuvert = !clapetOuvert;
    const one = P.couches.find(c => c.role === (clapetOuvert ? 'clapet_on' : 'clapet_off') && bufs[c.id]);
    if (one && moteur.marche) SF.joueEffet(one, bufs[one.id]);
    $('bClapet').classList.toggle('gold', clapetOuvert);
    $('bClapet').textContent = clapetOuvert ? 'Fermer le clapet (V)' : 'Ouvrir le clapet (V)';
    cancelAnimationFrame(clapetAnim);
    const de = clapetK, vers = clapetOuvert ? 1 : 0, t0 = performance.now(), D = clapetOuvert ? 180 : 350; // ouverture franche, fermeture plus douce
    (function pas(t) { const u = Math.min(1, (t - t0) / D); clapetK = de + (vers - de) * u; if (!anim) simMaj(); if (u < 1) clapetAnim = requestAnimationFrame(pas); })(t0);
  }
  function simMaj() {
    const rpm = +$('rpm').value, load = +$('load').value / 100;
    $('rpmO').textContent = rpm; $('loadO').textContent = Math.round(load * 100) + ' %'; $('rpmV').textContent = rpm;
    $('rpmG').style.setProperty('--v', Math.round((rpm - 500) / 1900 * 100));
    const sim = P.couches.filter(c => SF.ROLES[c.role].sim);
    const p = moteur.marche ? moteur.regle(P.couches, bufs, rpm, load, clapetK) : SF.poids(sim, rpm, load, clapetK);
    $('layers').innerHTML = sim.length ? sim.map(c => { const g = p[c.id] ? p[c.id].g : 0; return '<div class="ly"><span title="' + esc(c.fichier) + '">' + esc(SF.ROLES[c.role].court) + (c.rpm && c.role !== 'turbo' ? ' ' + c.rpm : '') + '</span><span class="g"><i style="width:' + Math.round(g * 100) + '%"></i></span><output>' + Math.round(g * 100) + '%</output></div>'; }).join('')
      : '<div class="vide">Ajoute au moins un ralenti et des régimes en charge pour entendre le moteur.</div>';
  }
  function moteurOnOff() {
    if (moteur.marche) { moteur.arrete(); arreteAccel(); $('bMoteur').textContent = 'Démarrer le moteur'; $('simEtat').className = 'etat nv'; $('simEtat').textContent = 'à l\'arrêt'; simMaj(); return; }
    const sim = P.couches.filter(c => SF.ROLES[c.role].sim && bufs[c.id]);
    if (!sim.length) { toast('Importe d\'abord un ralenti et des régimes en charge.'); return; }
    SF.stopSolo(); moteur.demarre(P.couches, bufs); majProjet.ecoute = true; majProjet();
    $('bMoteur').textContent = 'Couper le moteur'; $('simEtat').className = 'etat ok'; $('simEtat').textContent = 'moteur en marche'; simMaj();
  }
  function arreteAccel() { cancelAnimationFrame(anim); anim = 0; $('bAccel').classList.remove('gold'); }
  function accel() {
    if (anim) { arreteAccel(); return; }
    if (!moteur.marche) moteurOnOff(); if (!moteur.marche) return;
    $('bAccel').classList.add('gold');
    const t0 = performance.now();
    (function pas(t) {
      const s = ((t - t0) / 1000) % 12; let rpm, load;
      if (s < 1.5) { rpm = 600; load = 0; } else if (s < 7) { rpm = 600 + (s - 1.5) / 5.5 * 1300; load = 1; } else if (s < 7.6) { rpm = 1900 - (s - 7) * 300; load = 0.3; } else { rpm = 1720 - (s - 7.6) / 4.4 * 1120; load = 0; }
      $('rpm').value = Math.round(rpm); $('load').value = Math.round(load * 100); simMaj();
      anim = requestAnimationFrame(pas);
    })(t0);
  }

  /* ---------- lecture d'une couche ---------- */
  let raf = 0;
  function suit() { const pos = SF.position(); $('tc').textContent = tps(pos || 0); const c = couche(); if (c) onde($('wvc'), c, { edit: true }); if (pos != null) raf = requestAnimationFrame(suit); }
  function joue() { const c = couche(); if (!c || !bufs[c.id]) return; moteur.marche && moteurOnOff(); SF.joue(c, bufs[c.id], { boucle: boucleOn, brut: avant }); cancelAnimationFrame(raf); suit(); }

  /* ---------- édition à la souris / au doigt sur la forme d'onde ---------- */
  (function () {
    const wv = $('wv'); let prise = null;
    function t(ev) { const r = wv.getBoundingClientRect(), c = couche(); return Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * (c ? c.duree : 0); }
    wv.addEventListener('pointerdown', ev => {
      const c = couche(); if (!c) return; const x = t(ev), tol = c.duree * 0.03;
      prise = Math.abs(x - c.debut) < tol ? 'd' : Math.abs(x - c.fin) < tol ? 'f' : (Math.abs(x - c.debut) < Math.abs(x - c.fin) ? 'd' : 'f');
      wv.setPointerCapture(ev.pointerId); bouge(ev);
    });
    function bouge(ev) {
      const c = couche(); if (!prise || !c) return; const x = t(ev), mini = 0.05;
      if (prise === 'd') c.debut = Math.min(x, c.fin - mini); else c.fin = Math.max(x, c.debut + mini);
      c.debut = Math.round(c.debut * 1000) / 1000; c.fin = Math.round(c.fin * 1000) / 1000;
      onde($('wvc'), c, { edit: true }); $('tc').textContent = tps(c.fin - c.debut);
    }
    wv.addEventListener('pointermove', bouge);
    const fin = () => { if (prise) { prise = null; sauve(); rendPistes(); if (moteur.marche) { moteur.demarre(P.couches, bufs); simMaj(); } } };
    wv.addEventListener('pointerup', fin); wv.addEventListener('pointercancel', fin);
  })();

  /* ---------- export ---------- */
  function telecharge(blob, nom) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nom; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000); }
  async function exporteWav() {
    const refus = P.couches.filter(c => c.licence === 'refus').length;
    const sansAuteur = P.couches.filter(c => (c.licence === 'ccby' || c.licence === 'mod') && !c.source && c.role !== 'autre');
    if (sansAuteur.length) { toast('Indique l\'auteur et le lien de : ' + sansAuteur.map(c => c.fichier).join(', ') + ' (licence CC-BY ou son de mod).'); sel = sansAuteur[0].id; rendTout(); return; }
    const L = P.couches.filter(c => bufs[c.id] && c.role !== 'autre' && c.licence !== 'refus');
    if (refus) toast(refus + ' son(s) à licence refusée laissé(s) de côté.');
    if (!L.length) { toast('Rien à exporter.'); return; }
    $('bExportWav').disabled = true;
    try {
      const noms = {};
      for (const c of L) {
        const r = await SF.rendu(c, bufs[c.id]);
        let n = nomPropre(c.role + (c.role === 'charge' || c.role === 'sans' || c.role === 'ralenti' ? '_' + c.rpm : '')).toLowerCase();
        if (noms[n]) n += '_' + (++noms[n]); else noms[n] = 1;
        telecharge(SF.wav(r), n + '.wav');
        await new Promise(ok => setTimeout(ok, 250));
      }
      const LIC = { jeu: 'son du jeu ETS2 (SCS Software), retravaillé', mod: 'son de mod retravaillé', tsc: 'création TSC (générateur, à partir de mesures)', perso: 'enregistrement personnel', cc0: 'CC0 (domaine public)', ccby: 'CC-BY' };
      const cr = ['Projet ' + P.nom + ' - TSC Sound Forge', 'Sons utilisés :', ''].concat(L.map(c => '- ' + c.fichier + ' : ' + (LIC[c.licence] || c.licence) + (c.source ? ' - ' + c.source : ''))).join('\r\n') + '\r\n';
      telecharge(new Blob([cr], { type: 'text/plain' }), 'CREDITS_sons.txt');
      majProjet.exporte = true; majProjet(); toast(L.length + ' couche' + (L.length > 1 ? 's exportées' : ' exportée') + ' en WAV 48 kHz 24 bits.');
    } catch (e) { toast('Export impossible : ' + e.message); }
    $('bExportWav').disabled = false;
  }
  function exporteProjet() {
    const o = { format: 'tsc_sound_forge', version: 1, projet: P };
    telecharge(new Blob([JSON.stringify(o, null, 1)], { type: 'application/json' }), nomPropre(P.nom) + '.tscforge.json');
  }
  async function ouvreProjet(f) {
    try {
      const o = JSON.parse(await f.text());
      if (!o || o.format !== 'tsc_sound_forge' || !o.projet) throw new Error('fichier non reconnu');
      moteur.arrete(); SF.stopSolo(); P = o.projet; sel = P.couches[0] ? P.couches[0].id : null;
      for (const c of P.couches) { if (!bufs[c.id]) { const ab = await dbGet(c.id); if (ab) try { bufs[c.id] = await SF.decode(ab); } catch (e) {} } }
      $('nomProjet').value = P.nom; rendCamions(); sauve(); rendTout(); toast('Projet ouvert. Les sons absents de ce PC sont à réimporter.');
    } catch (e) { toast('Ce fichier n\'est pas un projet Sound Forge.'); }
  }

  /* ---------- analyse ETS2 ---------- */
  const ETATS = { compatible: ['ok', 'Compatible'], partiel: ['att', 'Partiel'], non_pris_en_charge: ['ko', 'Non pris en charge'], non_verifie: ['nv', 'Non vérifié'] };
  function etat(k) { const e = ETATS[k] || ['nv', k || '?']; return '<span class="etat ' + e[0] + '">' + esc(e[1]) + '</span>'; }
  function chargeAna(o) {
    if (!o || !Array.isArray(o.camions)) { $('anaMsg').textContent = 'Ce fichier n\'est pas un résultat d\'analyse Sound Forge.'; return; }
    ana = o; try { localStorage.setItem('tsc_forge_analyse', JSON.stringify({ environnement: o.environnement, resume: o.resume, camions: o.camions.map(k => ({ id: k.id, origine: k.origine, compatibilite: k.compatibilite, raison: k.raison, moteurs: k.moteurs, references: (k.references || []).slice(0, 60) })) })); } catch (e) {}
    rendAna(); rendCamions(); sauve();
  }
  function rendAna() {
    if (!ana) return; $('anaRes').hidden = false;
    const R = ana.resume || {};
    const S = [[R.camions, 'camions'], [R.moteurs, 'moteurs'], [R.banques, 'banques'], [R.mods_audio_actifs != null ? R.mods_audio_actifs : R.mods_audio, 'mods audio actifs'], [R.conflits, 'conflits'], [R.compatibles, 'compatibles']];
    $('stats').innerHTML = S.map(s => '<div class="stat"><b>' + (s[0] == null ? '—' : s[0]) + '</b><span>' + s[1] + '</span></div>').join('');
    const F = [['', 'Tous']].concat(Object.keys(ETATS).map(k => [k, ETATS[k][1]]));
    $('filtEtat').innerHTML = F.map(f => '<button type="button" class="tb' + (f[0] === filtreEtat ? ' on' : '') + '" data-f="' + f[0] + '">' + f[1] + ' (' + (f[0] ? ana.camions.filter(k => k.compatibilite === f[0]).length : ana.camions.length) + ')</button>').join('');
    const q = $('filtre').value.trim().toLowerCase();
    const L = ana.camions.filter(k => (!filtreEtat || k.compatibilite === filtreEtat) && (!q || (k.id + ' ' + k.origine).toLowerCase().includes(q)));
    $('tCam').innerHTML = L.map(k => '<tr data-id="' + esc(k.id) + '"' + (k.id === camSel ? ' class="on"' : '') + '><td><b>' + esc(k.id) + '</b></td><td class="mut">' + esc(k.origine) + '</td><td>' + ((k.moteurs || []).length) + '</td><td>' + etat(k.compatibilite) + '</td></tr>').join('') || '<tr><td colspan="4" class="mut">Aucun camion.</td></tr>';
    const E = ana.environnement || {}, kv = [];
    const v = (n, x) => { if (x != null && x !== '' && typeof x !== 'object') kv.push('<span>' + n + '</span><b>' + esc(x) + '</b>'); };
    const j = Array.isArray(E.ets2) ? E.ets2[0] : E.ets2;
    v('ETS2', E.version_game_log || (j && j.version_exe)); v('Dossier du jeu', j && j.dossier);
    v('FMOD du jeu', j && Array.isArray(j.fmod_du_jeu) ? j.fmod_du_jeu.join(', ') : '');
    v('FMOD Studio', Array.isArray(E.fmod_studio) ? E.fmod_studio.map(x => (x.nom || '') + ' ' + (x.version || '')).join(', ') : E.fmod_studio);
    v('Profils', Array.isArray(E.profils) ? E.profils.length : E.profils); v('Mods actifs', E.mods_actifs_game_log); v('Durée de l\'analyse', E.duree_s != null ? E.duree_s + ' s' : '');
    $('kvEnv').innerHTML = kv.join('') || '<span>Détails</span><b>dans le rapport</b>';
    rendDiag();
  }
  function rendDiag() {
    const k = ana && ana.camions.find(x => x.id === camSel);
    if (!k) { $('diag').innerHTML = '<span class="mut">Clique sur un camion.</span>'; return; }
    const refs = (k.references || []).filter(r => r.etat && r.etat !== 'ok');
    $('diag').innerHTML = '<div><b>' + esc(k.id) + '</b> ' + etat(k.compatibilite) + '</div>' + (k.raison ? '<div class="mut">' + esc(k.raison) + '</div>' : '') +
      '<div class="mut">' + (k.moteurs || []).length + ' moteur(s) · ' + (k.references || []).length + ' référence(s) son</div>' +
      refs.slice(0, 12).map(r => '<div class="ref">' + esc(r.fichier || '') + '<br>→ ' + esc(r.reference || '') + '<br><span style="color:var(--warn)">' + esc(r.raison || r.etat) + '</span></div>').join('') +
      (refs.length > 12 ? '<div class="mut">… et ' + (refs.length - 12) + ' autres dans le rapport.</div>' : '') +
      '<button class="b gold" type="button" id="bCible">Choisir ce camion pour mon son</button>';
    $('bCible').onclick = () => { P.camion = k.id; P.moteur = ''; rendCamions(); sauve(); onglet('studio'); toast(k.id + ' choisi.'); };
  }
  async function lanceAnalyse() {
    $('anaMsg').textContent = 'Analyse en cours, en lecture seule (1 à 2 minutes la première fois)…';
    $('bAnalyser').disabled = true;
    try {
      const tok = (window.parent && window.parent.TOKEN_TSC) || '';
      const r = await fetch('/forge/analyse', { method: 'POST', headers: { 'X-T': tok } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      chargeAna(await r.json()); $('anaMsg').textContent = 'Analyse terminée.';
    } catch (e) {
      $('anaMsg').textContent = 'L\'analyse automatique depuis la tablette arrive avec la prochaine version de l\'appli. En attendant, lance Analyser_mon_ETS2.bat puis ouvre le fichier base_connaissances.json ici.';
    }
    $('bAnalyser').disabled = false;
  }

  /* ---------- onglets ---------- */
  function onglet(v) {
    document.querySelectorAll('#onglets button[data-v]').forEach(b => { b.classList.toggle('on', b.dataset.v === v); b.setAttribute('aria-selected', b.dataset.v === v); });
    $('vStudio').hidden = v !== 'studio'; $('vAnalyse').hidden = v !== 'analyse';
    if (v === 'studio') rendTout();
  }

  /* ---------- événements ---------- */
  function lie() {
    document.querySelectorAll('#onglets button[data-v]').forEach(b => b.addEventListener('click', () => onglet(b.dataset.v)));
    $('nomProjet').addEventListener('change', () => { P.nom = nomPropre($('nomProjet').value); $('nomProjet').value = P.nom; sauve(); });
    $('selCamion').addEventListener('change', () => { P.camion = $('selCamion').value; P.moteur = ''; rendCamions(); sauve(); });
    $('selMoteur').addEventListener('change', () => { P.moteur = $('selMoteur').value; sauve(); });
    const drop = $('drop');
    $('fic').addEventListener('change', e => { importe(e.target.files); e.target.value = ''; });
    drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('fic').click(); } });
    ['dragenter', 'dragover'].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', e => importe(e.dataTransfer.files));
    const choisit = e => { const el = e.target.closest('[data-id]'); if (el) { sel = el.dataset.id; rendLib(); rendPistes(); rendEd(); } };
    $('lib').addEventListener('click', choisit); $('pistes').addEventListener('click', choisit);
    $('bJoue').onclick = joue;
    $('bStop').onclick = () => { SF.stopSolo(); cancelAnimationFrame(raf); $('tc').textContent = tps(0); const c = couche(); if (c) onde($('wvc'), c, { edit: true }); };
    $('bBoucle').onclick = () => { boucleOn = !boucleOn; $('bBoucle').classList.toggle('on', boucleOn); };
    $('bAvant').onclick = () => { avant = !avant; $('bAvant').classList.toggle('on', avant); $('bAvant').textContent = avant ? 'Son brut' : 'Avant / après'; if (SF.position() != null) joue(); };
    $('bSuppr').onclick = () => { const c = couche(); if (!c) return; SF.stopSolo(); P.couches = P.couches.filter(x => x !== c); delete bufs[c.id]; dbDel(c.id); sel = P.couches[0] ? P.couches[0].id : null; if (moteur.marche) moteur.demarre(P.couches, bufs); sauve(); rendTout(); };
    $('eRole').innerHTML = Object.keys(SF.ROLES).map(k => '<option value="' + k + '">' + SF.ROLES[k].nom + '</option>').join('');
    const champ = (id, k, num) => $(id).addEventListener('input', () => { const c = couche(); if (!c) return; c[k] = num ? +$(id).value : $(id).checked; sorties(); simMaj(); if (k === 'fondu' || k === 'boucle') onde($('wvc'), c, { edit: true }); });
    champ('eRpm', 'rpm', 1); champ('eGain', 'gain', 1); champ('eBas', 'bas', 1); champ('eHaut', 'haut', 1); champ('eFondu', 'fondu', 1); champ('eBoucle', 'boucle', 0); champ('eNorm', 'norm', 0);
    ['eRpm', 'eGain', 'eBas', 'eHaut', 'eFondu', 'eBoucle', 'eNorm'].forEach(id => $(id).addEventListener('change', () => { sauve(); rendPistes(); rendRoles(); if (id === 'eBoucle') rendEd(); }));
    $('eLic').addEventListener('change', () => { const c = couche(); if (!c) return; c.licence = $('eLic').value; sauve(); rendLib(); });
    $('eSrc').addEventListener('change', () => { const c = couche(); if (!c) return; c.source = $('eSrc').value.trim(); sauve(); rendLib(); });
    $('eRole').addEventListener('change', () => { const c = couche(); if (!c) return; c.role = $('eRole').value; c.boucle = SF.ROLES[c.role].boucle; if (SF.ROLES[c.role].rpm && (c.role === 'ralenti')) c.rpm = 600; if (moteur.marche) moteur.demarre(P.couches, bufs); sauve(); rendTout(); });
    $('rpm').addEventListener('input', () => { arreteAccel(); simMaj(); }); $('load').addEventListener('input', () => { arreteAccel(); simMaj(); });
    $('bMoteur').onclick = moteurOnOff; $('bAccel').onclick = accel; $('bClapet').onclick = clapet;
    document.addEventListener('keydown', e => { if (e.key.toLowerCase() === TOUCHE_CLAPET && !(e.target.tagName === 'TEXTAREA' || (e.target.tagName === 'INPUT' && /^(text|search|number)$/.test(e.target.type))) && !e.repeat) { e.preventDefault(); clapet(); } });
    $('bDemarre').onclick = () => { const c = P.couches.find(x => x.role === 'demarrage' && bufs[x.id]); if (!c) { toast('Aucun son de démarrage dans le projet.'); return; } SF.joue(c, bufs[c.id], {}); };
    $('bExportWav').onclick = exporteWav; $('bExportJson').onclick = exporteProjet;
    $('ficProjet').addEventListener('change', e => { if (e.target.files[0]) ouvreProjet(e.target.files[0]); e.target.value = ''; });
    $('bAnalyser').onclick = lanceAnalyse;
    $('bMesure').onclick = mesure; $('bGenere').onclick = genere;
    $('gMel').addEventListener('input', () => { $('oMel').textContent = $('gMel').value + ' %'; });
    $('ficAna').addEventListener('change', async e => { const f = e.target.files[0]; e.target.value = ''; if (!f) return; try { chargeAna(JSON.parse(await f.text())); $('anaMsg').textContent = 'Résultat chargé : ' + f.name; } catch (x) { $('anaMsg').textContent = 'Fichier illisible.'; } });
    $('filtre').addEventListener('input', rendAna);
    $('filtEtat').addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (b) { filtreEtat = b.dataset.f; rendAna(); } });
    $('tCam').addEventListener('click', e => { const tr = e.target.closest('tr[data-id]'); if (tr) { camSel = tr.dataset.id; rendAna(); } });
    let rt = 0; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { rendPistes(); const c = couche(); if (c) onde($('wvc'), c, { edit: true }); }, 120); });
  }

  /* ---------- démarrage ---------- */
  async function init() {
    lie();
    try { const s = JSON.parse(localStorage.getItem('tsc_forge_projet') || 'null'); if (s && Array.isArray(s.couches)) P = s; } catch (e) {}
    try { const a = JSON.parse(localStorage.getItem('tsc_forge_analyse') || 'null'); if (a && a.camions) ana = a; } catch (e) {}
    $('nomProjet').value = P.nom; sel = P.couches[0] ? P.couches[0].id : null;
    rendCamions(); rendTout(); if (ana) rendAna();
    await ouvreDb();
    for (const c of P.couches) { const ab = await dbGet(c.id); if (ab) { try { bufs[c.id] = await SF.decode(ab); } catch (e) {} } }
    rendTout();
  }
  window.TSC_forge = { importe, projet: () => P, poids: SF.poids, chargeAna, mesure, genere };
  init();
})();
