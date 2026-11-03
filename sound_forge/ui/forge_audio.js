/* TSC Sound Forge - moteur audio de l'atelier (Web Audio, aucune dépendance).
   Sert à écouter et préparer les couches. Le vrai son du jeu sera compilé par FMOD Studio (phases 3 et 4). */
(function () {
  'use strict';
  const SF = {};
  let ctx = null;

  SF.ROLES = {
    ralenti:    { nom: 'Ralenti', court: 'Ralenti',               boucle: true,  rpm: 600,  sim: true },
    charge:     { nom: 'Accélération (charge)', court: 'Charge', boucle: true,  rpm: 1200, sim: true },
    sans:       { nom: 'Lever de pied', court: 'Pied levé',         boucle: true,  rpm: 1200, sim: true },
    turbo:      { nom: 'Turbo', court: 'Turbo',                 boucle: true,  rpm: 0,    sim: true },
    clapet:     { nom: 'Clapet ouvert (par régime)', court: 'Clapet', boucle: true, rpm: 1200, sim: true },
    clapet_on:  { nom: 'Ouverture du clapet', court: 'Clapet +',  boucle: false, rpm: 0,    sim: false },
    clapet_off: { nom: 'Fermeture du clapet', court: 'Clapet −',  boucle: false, rpm: 0,    sim: false },
    demarrage:  { nom: 'Démarrage', court: 'Démarrage',             boucle: false, rpm: 0,    sim: false },
    arret:      { nom: 'Arrêt', court: 'Arrêt',                 boucle: false, rpm: 0,    sim: false },
    autre:      { nom: 'Autre (non utilisé)', court: 'Autre',   boucle: false, rpm: 0,    sim: false }
  };

  SF.ctx = function () {
    if (!ctx) {
      const C = window.AudioContext || window.webkitAudioContext;
      try { ctx = new C({ sampleRate: 48000 }); } catch (e) { ctx = new C(); }
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  };

  SF.decode = function (ab) {
    const c = SF.ctx();
    return new Promise((ok, ko) => {
      const p = c.decodeAudioData(ab.slice(0), ok, ko);
      if (p && p.then) p.then(ok, ko);
    });
  };

  const dbLin = d => Math.pow(10, d / 20);
  SF.dbLin = dbLin;

  /* pics min/max par colonne pour dessiner une forme d'onde */
  SF.pics = function (buf, n, debut, fin) {
    const d = buf.getChannelData(0), sr = buf.sampleRate;
    const a = Math.max(0, Math.floor((debut || 0) * sr)), b = Math.min(d.length, Math.floor((fin || buf.duration) * sr));
    const out = new Float32Array(n * 2), pas = Math.max(1, (b - a) / n);
    for (let i = 0; i < n; i++) {
      let mn = 1, mx = -1; const s = Math.floor(a + i * pas), e = Math.min(b, Math.floor(a + (i + 1) * pas));
      for (let j = s; j < e; j++) { const v = d[j]; if (v < mn) mn = v; if (v > mx) mx = v; }
      if (e <= s) { mn = 0; mx = 0; }
      out[i * 2] = mn; out[i * 2 + 1] = mx;
    }
    return out;
  };

  /* crête de la zone gardée, pour égaliser le volume à -1 dBFS */
  SF.crete = function (buf, debut, fin) {
    let m = 0; const sr = buf.sampleRate;
    for (let c = 0; c < buf.numberOfChannels; c++) {
      const d = buf.getChannelData(c), a = Math.floor(debut * sr), b = Math.min(d.length, Math.floor(fin * sr));
      for (let i = a; i < b; i++) { const v = Math.abs(d[i]); if (v > m) m = v; }
    }
    return m;
  };
  SF.gainTotal = function (c, buf) {
    let g = dbLin(c.gain || 0);
    if (c.norm && buf) { const p = SF.crete(buf, c.debut, c.fin); if (p > 1e-5) g *= dbLin(-1) / p; }
    return g;
  };

  /* Poids de chaque couche pour un régime et une charge donnés.
     Fondu à puissance constante entre les deux couches de régime voisines, mélange charge / lever de pied selon la charge. */
  /* clapet : 0 = fermé, 1 = ouvert (TSC Clapet). Ouvert, les couches « clapet » prennent le dessus
     et l'échappement normal baisse de CLAPET_BAISSE. */
  SF.CLAPET_BAISSE = 0.6;
  SF.poids = function (couches, rpm, charge, clapet) {
    const K = Math.max(0, Math.min(1, clapet || 0));
    const res = {};
    couches.forEach(c => { res[c.id] = { g: 0, vitesse: 1 }; });
    const L = Math.max(0, Math.min(1, charge));
    const groupe = role => couches.filter(c => c.role === role || c.role === 'ralenti').sort((a, b) => a.rpm - b.rpm);
    const gc = groupe('charge'), gs = groupe('sans');
    const aCharge = couches.some(c => c.role === 'charge'), aSans = couches.some(c => c.role === 'sans');
    // courbe de l'exemple officiel SCS (Peterbilt 579) : sans charge sous 0,2, fondu de 0,2 a 0,35, charge au-dessus
    const tc = Math.max(0, Math.min(1, (L - 0.2) / 0.15));
    let pc = Math.sin(tc * Math.PI / 2), ps = Math.cos(tc * Math.PI / 2);
    if (!aCharge && !aSans) { pc = 1; ps = 0; }
    else if (!aCharge) { pc = 0; ps = 1; }
    else if (!aSans) { pc = 1; ps = 0; }
    function fondu(g, poidsGroupe) {
      if (!g.length || poidsGroupe <= 0) return;
      let i = 0; while (i < g.length && g[i].rpm < rpm) i++;
      if (i === 0) { res[g[0].id].g += poidsGroupe; return; }
      if (i === g.length) { res[g[g.length - 1].id].g += poidsGroupe; return; }
      const a = g[i - 1], b = g[i], t = (rpm - a.rpm) / Math.max(1, b.rpm - a.rpm);
      res[a.id].g += poidsGroupe * Math.cos(t * Math.PI / 2);
      res[b.id].g += poidsGroupe * Math.sin(t * Math.PI / 2);
    }
    fondu(gc, pc); fondu(gs, ps);
    const gk = couches.filter(c => c.role === 'clapet').sort((a, b) => a.rpm - b.rpm);
    if (gk.length) {
      couches.forEach(c => { if (c.role === 'ralenti' || c.role === 'charge' || c.role === 'sans') res[c.id].g *= 1 - SF.CLAPET_BAISSE * K; });
      fondu(gk, K * (0.55 + 0.45 * L)); // plus fort en charge, présent aussi au lever de pied
    }
    couches.forEach(c => {
      if (c.role === 'ralenti' || c.role === 'charge' || c.role === 'sans' || c.role === 'clapet') {
        res[c.id].vitesse = Math.max(0.5, Math.min(2, rpm / Math.max(100, c.rpm)));
      } else if (c.role === 'turbo') {
        const k = Math.max(0, Math.min(1, (rpm - 1000) / 1000));
        res[c.id].g = L * k; res[c.id].vitesse = 0.85 + 0.3 * k;
      }
      res[c.id].g = Math.min(1, res[c.id].g);
    });
    return res;
  };

  function chaine(c, buf, dest) {
    const x = SF.ctx();
    const bas = x.createBiquadFilter(); bas.type = 'lowshelf'; bas.frequency.value = 120; bas.gain.value = c.bas || 0;
    const haut = x.createBiquadFilter(); haut.type = 'highshelf'; haut.frequency.value = 3000; haut.gain.value = c.haut || 0;
    const g = x.createGain(); g.gain.value = SF.gainTotal(c, buf);
    bas.connect(haut); haut.connect(g); g.connect(dest);
    return { entree: bas, bas, haut, g };
  }

  /* lecture d'une seule couche (avant / après) */
  let solo = null;
  SF.joue = function (c, buf, opts) {
    SF.stopSolo();
    const x = SF.ctx(), brut = opts && opts.brut;
    const s = x.createBufferSource(); s.buffer = buf;
    const m = x.createGain(); m.gain.value = 0.9; m.connect(x.destination);
    let ch = null;
    if (brut) s.connect(m); else { ch = chaine(c, buf, m); s.connect(ch.entree); }
    const d = brut ? 0 : c.debut, f = brut ? buf.duration : c.fin;
    if (opts && opts.boucle) { s.loop = true; s.loopStart = d; s.loopEnd = f; s.start(0, d); }
    else s.start(0, d, Math.max(0.01, f - d));
    solo = { s, m, t0: x.currentTime, d, f, boucle: !!(opts && opts.boucle) };
    s.onended = () => { if (solo && solo.s === s) solo = null; };
    return solo;
  };
  SF.position = function () {
    if (!solo) return null;
    const x = SF.ctx(), len = solo.f - solo.d, t = x.currentTime - solo.t0;
    return solo.d + (solo.boucle ? t % len : Math.min(t, len));
  };
  /* effet ponctuel (ouverture / fermeture du clapet) joué par-dessus le moteur, sans couper le reste */
  SF.joueEffet = function (c, buf) {
    const x = SF.ctx(), s = x.createBufferSource(); s.buffer = buf;
    const m = x.createGain(); m.gain.value = 0.9; m.connect(x.destination);
    const ch = chaine(c, buf, m); s.connect(ch.entree);
    s.start(0, c.debut, Math.max(0.01, c.fin - c.debut)); s.onended = () => m.disconnect();
  };
  SF.stopSolo = function () { if (solo) { try { solo.s.stop(); } catch (e) {} solo.m.disconnect(); solo = null; } };

  /* simulateur : toutes les couches de moteur jouent en boucle, leur volume et leur vitesse suivent régime et charge */
  SF.Moteur = function () {
    const x = SF.ctx(); const maitre = x.createGain(); maitre.gain.value = 0.8;
    const comp = x.createDynamicsCompressor(); comp.threshold.value = -6; comp.ratio.value = 4;
    maitre.connect(comp); comp.connect(x.destination);
    const voix = {};
    this.marche = false;
    this.demarre = function (couches, bufs) {
      this.arrete();
      couches.forEach(c => {
        if (!SF.ROLES[c.role] || !SF.ROLES[c.role].sim || !bufs[c.id]) return;
        const b = bufs[c.id]; const s = x.createBufferSource(); s.buffer = b;
        s.loop = true; s.loopStart = c.debut; s.loopEnd = c.fin;
        const mix = x.createGain(); mix.gain.value = 0; mix.connect(maitre);
        const ch = chaine(c, b, mix); s.connect(ch.entree); s.start(0, c.debut);
        voix[c.id] = { s, mix, ch };
      });
      this.marche = true;
    };
    this.regle = function (couches, bufs, rpm, charge, clapet) {
      const p = SF.poids(couches.filter(c => voix[c.id]), rpm, charge, clapet), t = x.currentTime;
      // sous 400 tr/min le moteur s'éteint doucement (0 = silence)
      maitre.gain.setTargetAtTime(0.8 * Math.max(0, Math.min(1, rpm / 400)), t, 0.05);
      Object.keys(voix).forEach(id => {
        const v = voix[id], q = p[id] || { g: 0, vitesse: 1 };
        v.mix.gain.setTargetAtTime(q.g, t, 0.04);
        v.s.playbackRate.setTargetAtTime(q.vitesse, t, 0.06);
        const c = couches.find(k => k.id === id);
        if (c) { v.ch.bas.gain.value = c.bas || 0; v.ch.haut.gain.value = c.haut || 0; v.ch.g.gain.value = SF.gainTotal(c, bufs[id]); }
      });
      return p;
    };
    this.arrete = function () {
      Object.keys(voix).forEach(id => { try { voix[id].s.stop(); } catch (e) {} voix[id].mix.disconnect(); delete voix[id]; });
      this.marche = false;
    };
  };

  /* Rendu final d'une couche (coupe, volume, égaliseur, boucle sans clic) en 48 kHz pour FMOD. */
  SF.rendu = function (c, buf) {
    const sr = 48000, nc = Math.min(2, buf.numberOfChannels);
    const dur = Math.max(0.02, c.fin - c.debut), n = Math.ceil(dur * sr);
    const O = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    const off = new O(nc, n, sr);
    const s = off.createBufferSource(); s.buffer = buf;
    const bas = off.createBiquadFilter(); bas.type = 'lowshelf'; bas.frequency.value = 120; bas.gain.value = c.bas || 0;
    const haut = off.createBiquadFilter(); haut.type = 'highshelf'; haut.frequency.value = 3000; haut.gain.value = c.haut || 0;
    const g = off.createGain(); g.gain.value = SF.gainTotal(c, buf);
    s.connect(bas); bas.connect(haut); haut.connect(g); g.connect(off.destination);
    s.start(0, c.debut, dur);
    return off.startRendering().then(r => SF.boucleSansClic(r, c.boucle ? (c.fondu || 0) / 1000 : 0));
  };

  /* Boucle sans clic : la fin est fondue dans le début (puissance constante). Le résultat est plus court du fondu. */
  SF.boucleSansClic = function (buf, fondu) {
    const sr = buf.sampleRate, F = Math.floor(fondu * sr), L = buf.length;
    if (F < 2 || F * 2 >= L) return buf;
    const x = SF.ctx(), out = x.createBuffer(buf.numberOfChannels, L - F, sr);
    for (let c = 0; c < buf.numberOfChannels; c++) {
      const a = buf.getChannelData(c), o = out.getChannelData(c);
      for (let i = 0; i < L - F; i++) o[i] = a[i];
      for (let i = 0; i < F; i++) { const t = i / F; o[i] = a[i] * Math.sin(t * Math.PI / 2) + a[L - F + i] * Math.cos(t * Math.PI / 2); }
    }
    return out;
  };

  /* WAV PCM 24 bits */
  SF.wav = function (buf) {
    const nc = buf.numberOfChannels, n = buf.length, sr = buf.sampleRate, bps = 3;
    const ab = new ArrayBuffer(44 + n * nc * bps), v = new DataView(ab);
    const ecr = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    ecr(0, 'RIFF'); v.setUint32(4, 36 + n * nc * bps, true); ecr(8, 'WAVE'); ecr(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, nc, true); v.setUint32(24, sr, true);
    v.setUint32(28, sr * nc * bps, true); v.setUint16(32, nc * bps, true); v.setUint16(34, 24, true);
    ecr(36, 'data'); v.setUint32(40, n * nc * bps, true);
    const ch = []; for (let c = 0; c < nc; c++) ch.push(buf.getChannelData(c));
    let o = 44;
    for (let i = 0; i < n; i++) for (let c = 0; c < nc; c++) {
      let s = Math.max(-1, Math.min(1, ch[c][i])); s = Math.round(s * 8388607);
      v.setUint8(o, s & 255); v.setUint8(o + 1, (s >> 8) & 255); v.setUint8(o + 2, (s >> 16) & 255); o += 3;
    }
    return new Blob([ab], { type: 'audio/wav' });
  };

  window.SF = SF;
})();
