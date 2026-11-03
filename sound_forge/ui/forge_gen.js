/* TSC Sound Forge - analyse de référence et générateur de moteur TSC.
   On mesure un son de référence (empreinte = chiffres seulement, aucun échantillon gardé),
   puis on fabrique un son NEUF à partir de ces chiffres (synthèse additive + bruit mis en forme). */
(function () {
  'use strict';
  const SF = window.SF;

  /* FFT radix-2 en place (re, im : Float64Array de taille 2^n) */
  function fft(re, im, inverse) {
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit;
      if (i < j) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const a = (inverse ? 2 : -2) * Math.PI / len, wr = Math.cos(a), wi = Math.sin(a);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let k = 0; k < len / 2; k++) {
          const p = i + k, q = p + len / 2;
          const xr = re[q] * cr - im[q] * ci, xi = re[q] * ci + im[q] * cr;
          re[q] = re[p] - xr; im[q] = im[p] - xi; re[p] += xr; im[p] += xi;
          const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
        }
      }
    }
    if (inverse) for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
  }
  SF.fft = fft;

  /* Bandes de fréquence (en Hz) pour l'enveloppe et le bruit */
  const BANDES = [20, 40, 60, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000];
  SF.BANDES = BANDES;
  const db = x => 20 * Math.log10(Math.max(1e-9, x));
  function interpBandes(valeurs, f) {
    if (f <= BANDES[0]) return valeurs[0];
    for (let i = 1; i < BANDES.length; i++) if (f <= BANDES[i]) {
      const t = Math.log(f / BANDES[i - 1]) / Math.log(BANDES[i] / BANDES[i - 1]);
      return valeurs[i - 1] * (1 - t) + valeurs[i] * t;
    }
    return valeurs[valeurs.length - 1];
  }

  /* Empreinte d'un son de moteur à régime stable.
     cyl : nombre de cylindres (4 temps) ; la fréquence de base mesurée est celle d'un cycle moteur (rpm/120). */
  SF.empreinte = function (buf, debut, fin, rpm, cyl) {
    const sr = buf.sampleRate, N = 1 << 16;
    const d = new Float64Array(N), im = new Float64Array(N);
    const a = Math.floor(debut * sr), b = Math.floor(fin * sr), L = b - a;
    if (L < sr * 0.3) throw new Error('Il faut au moins 0,3 s de son stable.');
    // moyenne des canaux, fenêtre de Hann, centrée dans la zone
    const deb = a + Math.max(0, Math.floor((L - N) / 2)), n = Math.min(N, L);
    for (let i = 0; i < n; i++) {
      let v = 0; for (let c = 0; c < buf.numberOfChannels; c++) v += buf.getChannelData(c)[deb + i] || 0;
      d[i] = v / buf.numberOfChannels * (0.5 - 0.5 * Math.cos(2 * Math.PI * i / (n - 1)));
    }
    fft(d, im, false);
    const mag = new Float64Array(N / 2); for (let i = 0; i < N / 2; i++) mag[i] = Math.hypot(d[i], im[i]);
    const hz = sr / N, base = rpm / 120;
    // harmoniques du cycle moteur jusqu'à 8 kHz
    const harm = []; const pris = new Uint8Array(N / 2);
    for (let k = 1; k * base < Math.min(8000, sr / 2 - 100); k++) {
      const f = k * base, c = Math.round(f / hz), w = Math.max(2, Math.round(f * 0.015 / hz));
      let m = 0; for (let j = c - w; j <= c + w; j++) if (j > 0 && j < N / 2) { if (mag[j] > m) m = mag[j]; pris[j] = 1; }
      harm.push(m);
    }
    // bruit : moyenne hors harmoniques, par bande
    const bruit = BANDES.map((f0, i) => {
      const f1 = BANDES[i + 1] || sr / 2; let s = 0, k = 0;
      for (let j = Math.floor(f0 / hz); j < Math.min(N / 2, f1 / hz); j++) if (!pris[j]) { s += mag[j]; k++; }
      return k ? s / k : 0;
    });
    // enveloppe (en Hz) tirée des pics harmoniques : maximum par bande
    const env = BANDES.map((f0, i) => {
      const f1 = BANDES[i + 1] || sr / 2; let m = 0;
      harm.forEach((v, k) => { const f = (k + 1) * base; if (f >= f0 && f < f1 && v > m) m = v; });
      return m;
    });
    for (let i = 0; i < env.length; i++) if (!env[i]) env[i] = env[i - 1] || 0;
    const ref = Math.max.apply(null, harm.concat(bruit)) || 1;
    return {
      version: 1, rpm, cyl, sr,
      ordres: harm.map(v => +(v / ref).toFixed(5)),          // profil par ordre (multiple du cycle)
      enveloppe_db: env.map(v => +db(v / ref).toFixed(2)),  // couleur fixe en Hz (résonances)
      bruit_db: bruit.map(v => +db(v / ref).toFixed(2)),    // grain
      date: new Date().toISOString().slice(0, 10)
    };
  };

  /* Fabrique une boucle neuve (parfaitement bouclable) au régime voulu.
     opts : { rpm, charge (0..1), duree (s), melange (0 = ordres, 1 = enveloppe), graine } */
  SF.genere = function (E, opts) {
    const sr = 48000, rpm = opts.rpm, charge = opts.charge == null ? 1 : opts.charge;
    const N = 1 << Math.round(Math.log2((opts.duree || 2.7) * sr));
    const re = new Float64Array(N), im = new Float64Array(N);
    let g = (opts.graine || 1) * 9301 + 49297; const rnd = () => { g = (g * 9301 + 49297) % 233280; return g / 233280; };
    const hz = sr / N, base = rpm / 120, m = opts.melange == null ? 0.6 : opts.melange;
    const envLin = E.enveloppe_db.map(v => Math.pow(10, v / 20)), brLin = E.bruit_db.map(v => Math.pow(10, v / 20));
    // charge : plus d'aigus et de grain en charge, plus sourd en lever de pied
    const pente = f => Math.pow(Math.max(f, 50) / 500, (charge - 0.5) * 0.6);
    const ordreFeu = E.cyl / 2;
    for (let k = 1; k * base < sr / 2 - 200; k++) {
      const f = k * base, c = Math.round(f / hz); if (c <= 0 || c >= N / 2) continue;
      const parOrdre = E.ordres[k - 1] != null ? E.ordres[k - 1] : E.ordres[E.ordres.length - 1] * Math.pow((E.ordres.length) / k, 1.5);
      const parEnv = interpBandes(envLin, f) * (k % ordreFeu === 0 ? 1 : 0.35);
      let amp = (parOrdre * (1 - m) + parEnv * m) * pente(f);
      // phases : cohérentes sur les ordres d'allumage (impulsions), aléatoires ailleurs
      const ph = (k % ordreFeu === 0 ? 0.15 : 1) * rnd() * 2 * Math.PI;
      re[c] += amp * Math.cos(ph) * N / 4; im[c] += amp * Math.sin(ph) * N / 4;
    }
    // bruit mis en forme (grain d'échappement), plus fort en charge
    const nb = 0.6 + 0.8 * charge;
    for (let j = 1; j < N / 2; j++) {
      const a = interpBandes(brLin, j * hz) * nb * pente(j * hz) * Math.sqrt(N) * 0.5, ph = rnd() * 2 * Math.PI;
      re[j] += a * Math.cos(ph); im[j] += a * Math.sin(ph);
    }
    for (let j = 1; j < N / 2; j++) { re[N - j] = re[j]; im[N - j] = -im[j]; }
    fft(re, im, true);
    let p = 0; for (let i = 0; i < N; i++) p = Math.max(p, Math.abs(re[i]));
    const x = SF.ctx(), out = x.createBuffer(1, N, sr), o = out.getChannelData(0), k = p ? 0.89 / p : 1;
    for (let i = 0; i < N; i++) o[i] = re[i] * k;
    return out;
  };

  /* Régimes conseillés pour un jeu de couches (comme l'exemple officiel SCS) */
  SF.REGIMES_GEN = [600, 900, 1200, 1500, 1800, 2100];
})();
