/* IA Forge : apprend de l'oreille de Mendy, avec les mêmes règles que l'IA Pro Photoréalisme (Graphics).
   - Données : ses choix dans Forge (rôle d'un son, « je garde » / « je jette »). Rien ne sort du PC.
   - Traits : mesures du son (bandes de fréquence, brillance, niveau, crête, impulsions par seconde, durée).
   - Juge fixe : 1 choix sur 10, tiré une fois pour toutes d'après l'identifiant du son, ne sert jamais à apprendre.
   - Une nouvelle version n'est adoptée que si elle fait au moins aussi bien sur le juge (sinon on garde l'ancienne).
   - Chaque version est gardée (20 dernières) ; retour à la précédente en un clic.
   Ce sont des mesures et des votes de voisins : l'IA propose, c'est l'écoute de Mendy qui tranche. */
(function () {
  'use strict';
  const SF = window.SF;
  const CLE = 'tsc_forge_ia';
  const REGLES = {
    juge_1_sur: 10,              // 1 choix sur 10 devient juge, pour toujours
    juge_minimum: 3,             // en dessous, aucune version n'est adoptée (pas assez de preuves)
    exemples_minimum: 8,
    adoption: 'meilleure ou égale sur le juge, rôle ET garder/jeter, sinon refus',
    versions_gardees: 20,
    voisins: 5,
    donnees: 'locales : jamais envoyées hors du PC'
  };

  /* ---------- traits d'un son ---------- */
  function fft(re, im) { // FFT radix 2 en place
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let b = n >> 1; for (; j & b; b >>= 1) j ^= b; j ^= b;
      if (i < j) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const a = -2 * Math.PI / len, wr = Math.cos(a), wi = Math.sin(a);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let k = 0; k < len / 2; k++) {
          const p = i + k, q = p + len / 2;
          const tr = re[q] * cr - im[q] * ci, ti = re[q] * ci + im[q] * cr;
          re[q] = re[p] - tr; im[q] = im[p] - ti; re[p] += tr; im[p] += ti;
          const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr;
        }
      }
    }
  }
  const BANDES = [0, 80, 250, 800, 2500, 24000];
  const NOMS = ['sub <80 Hz', 'grave 80-250', 'médium 250-800', 'haut-médium 0,8-2,5 k', 'aigu >2,5 k', 'brillance', 'niveau', 'crête/niveau', 'impulsions/s', 'durée'];
  SF.traits = function (buf, debut, fin) {
    const sr = buf.sampleRate, i0 = Math.max(0, Math.floor(debut * sr)), i1 = Math.min(buf.length, Math.ceil(fin * sr));
    const n = i1 - i0, ch = [];
    for (let c = 0; c < buf.numberOfChannels; c++) ch.push(buf.getChannelData(c));
    const x = i => { let s = 0; for (const d of ch) s += d[i]; return s / ch.length; };
    // spectre moyen sur 24 fenêtres de 4096 points au plus
    const N = 4096, E = new Float64Array(BANDES.length - 1); let cent = 0, tot = 0;
    const nf = Math.max(1, Math.min(24, Math.floor(n / N)));
    for (let f = 0; f < nf; f++) {
      const s = i0 + Math.floor((n - Math.min(n, N)) * (nf > 1 ? f / (nf - 1) : 0));
      const re = new Float64Array(N), im = new Float64Array(N);
      for (let k = 0; k < N && s + k < i1; k++) re[k] = x(s + k) * (0.5 - 0.5 * Math.cos(2 * Math.PI * k / (N - 1)));
      fft(re, im);
      for (let k = 1; k < N / 2; k++) {
        const hz = k * sr / N, p = re[k] * re[k] + im[k] * im[k];
        tot += p; cent += p * hz;
        for (let b = 0; b < E.length; b++) if (hz >= BANDES[b] && hz < BANDES[b + 1]) { E[b] += p; break; }
      }
    }
    // niveau, crête, impulsions (montées d'énergie de plus de 6 dB en 10 ms)
    let sq = 0, pk = 0; const pas = Math.max(1, Math.floor(n / 400000)); let m = 0;
    for (let i = i0; i < i1; i += pas) { const v = x(i); sq += v * v; m++; if (Math.abs(v) > pk) pk = Math.abs(v); }
    const rms = Math.sqrt(sq / Math.max(1, m)), db = v => 20 * Math.log10(Math.max(v, 1e-9));
    const w = Math.floor(0.01 * sr); let imp = 0, prec = 0;
    for (let i = i0; i + w <= i1; i += w) {
      let e = 0; for (let k = 0; k < w; k += 4) { const v = x(i + k); e += v * v; }
      e = Math.sqrt(e / (w / 4)) + 1e-9; if (prec && e / prec > 2) imp++; prec = e;
    }
    const d = n / sr, t = tot || 1;
    return Array.from(E, v => 100 * v / t).concat([cent / t / 1000, db(rms), db(pk) - db(rms), imp / Math.max(0.01, d), Math.log2(1 + d)]);
  };

  /* ---------- mémoire de l'IA ---------- */
  function lit() { try { return JSON.parse(localStorage.getItem(CLE) || 'null') || { versions: [], journal: [] }; } catch (e) { return { versions: [], journal: [] }; } }
  function ecrit(m) { try { localStorage.setItem(CLE, JSON.stringify(m)); } catch (e) {} }
  const hash = s => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
  const estJuge = cle => hash(cle) % REGLES.juge_1_sur === 0;

  function normes(X) {
    const k = X[0].length, mu = new Array(k).fill(0), sd = new Array(k).fill(0);
    X.forEach(v => v.forEach((a, i) => { mu[i] += a / X.length; }));
    X.forEach(v => v.forEach((a, i) => { sd[i] += (a - mu[i]) ** 2 / X.length; }));
    return { mu, sd: sd.map(s => Math.sqrt(s) || 1) };
  }
  function proche(modele, t, champ) {
    const z = t.map((a, i) => (a - modele.norme.mu[i]) / modele.norme.sd[i]);
    const d = modele.exemples.filter(e => e[champ] != null).map(e => [e.z.reduce((s, a, i) => s + (a - z[i]) ** 2, 0), e[champ]]).sort((a, b) => a[0] - b[0]).slice(0, REGLES.voisins);
    if (!d.length) return null;
    const votes = {}; d.forEach(([dist, v]) => { votes[v] = (votes[v] || 0) + 1 / (1 + dist); });
    const tot = Object.values(votes).reduce((a, b) => a + b, 0), best = Object.keys(votes).sort((a, b) => votes[b] - votes[a])[0];
    return { valeur: best, confiance: votes[best] / tot };
  }
  function score(modele, juges, champ) {
    const J = juges.filter(e => e[champ] != null); if (!J.length) return null;
    return J.filter(e => { const p = proche(modele, e.t, champ); return p && p.valeur === e[champ]; }).length / J.length;
  }

  /* exemples = [{cle, t, role, verdict}] ; renvoie {adoptee, raison, version} */
  SF.IA = {
    REGLES, NOMS,
    etat() { const m = lit(); return { version: m.versions[m.versions.length - 1] || null, journal: m.journal.slice(-8), versions: m.versions.length }; },
    apprend(exemples) {
      const m = lit(), date = new Date().toISOString().slice(0, 16).replace('T', ' ');
      const appr = exemples.filter(e => !estJuge(e.cle)), juges = exemples.filter(e => estJuge(e.cle));
      const note = (ok, raison, v) => { m.journal.push({ date, ok, raison }); m.journal = m.journal.slice(-50); ecrit(m); return { adoptee: ok, raison, version: v }; };
      if (appr.length < REGLES.exemples_minimum) return note(false, 'pas assez de choix pour apprendre (' + appr.length + ' / ' + REGLES.exemples_minimum + ')', null);
      if (juges.length < REGLES.juge_minimum) return note(false, 'juge trop petit (' + juges.length + ' / ' + REGLES.juge_minimum + ' choix mis de côté) : continue à trier', null);
      const a0 = m.versions[m.versions.length - 1];
      if (a0 && a0.appris === appr.length && a0.juges === juges.length) return { adoptee: false, raison: 'rien de nouveau depuis la version ' + a0.n + ' : trie d\'autres sons', version: a0 };
      const norme = normes(appr.map(e => e.t));
      const v = { n: m.versions.length + 1, date, norme, appris: appr.length, juges: juges.length,
        exemples: appr.map(e => ({ z: e.t.map((a, i) => (a - norme.mu[i]) / norme.sd[i]), role: e.role, verdict: e.verdict })) };
      v.score_role = score(v, juges, 'role'); v.score_verdict = score(v, juges, 'verdict');
      const a = m.versions[m.versions.length - 1];
      if (a) { // la règle : l'ancienne version est rejugée sur le MÊME juge d'aujourd'hui
        const sr = score(a, juges, 'role'), sv = score(a, juges, 'verdict');
        const pire = (n, o) => n != null && o != null && n < o;
        if (pire(v.score_role, sr) || pire(v.score_verdict, sv))
          return note(false, 'version ' + v.n + ' refusée : moins bonne que la ' + a.n + ' sur le juge (rôle ' + pct(v.score_role) + ' contre ' + pct(sr) + ', garder/jeter ' + pct(v.score_verdict) + ' contre ' + pct(sv) + ')', a);
      }
      m.versions.push(v); m.versions = m.versions.slice(-REGLES.versions_gardees);
      return note(true, 'version ' + v.n + ' adoptée : rôle juste ' + pct(v.score_role) + ', garder/jeter juste ' + pct(v.score_verdict) + ' sur ' + juges.length + ' choix jamais vus', v);
    },
    propose(t) {
      const v = lit().versions.slice(-1)[0]; if (!v) return null;
      return { version: v.n, role: proche(v, t, 'role'), verdict: proche(v, t, 'verdict') };
    },
    retour() {
      const m = lit(); if (m.versions.length < 2) return false;
      const v = m.versions.pop(); m.journal.push({ date: new Date().toISOString().slice(0, 16).replace('T', ' '), ok: true, raison: 'retour arrière : version ' + v.n + ' retirée' }); ecrit(m); return true;
    },
    exporte() { const m = lit(); return { format: 'tsc_forge_ia', regles: REGLES, traits: NOMS, versions: m.versions.map(v => ({ n: v.n, date: v.date, appris: v.appris, juges: v.juges, score_role: v.score_role, score_verdict: v.score_verdict })), journal: m.journal }; },
    estJuge
  };
  function pct(v) { return v == null ? '—' : Math.round(v * 100) + ' %'; }
  SF.pct = pct;
})();
