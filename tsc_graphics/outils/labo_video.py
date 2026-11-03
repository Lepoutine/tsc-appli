"""TSC Neural Graphics : laboratoire video HORS JEU (experimental).

Sert a essayer et valider des methodes sur des enregistrements ETS2 avant de les porter dans le plugin temps reel.
Rien de ce qui sort d'ici ne prouve qu'un effet marche en jeu : la profondeur est ESTIMEE (MiDaS), pas lue dans le jeu,
et le mouvement est estime par flot optique.

Usage :
  python3 -I labo_video.py <video> <dossier_sortie> [ambiance] [debut_s] [duree_s] [largeur]
Sorties :
  avant_apres.mp4   : gauche = video d'origine, droite = experimentation TSC (marquee « EXPERIMENTAL HORS JEU »)
  profondeur.mp4    : profondeur estimee et stabilisee dans le temps
  mesures.json/csv  : scintillement avant/apres (ecart image a image apres compensation du mouvement), part de pixels
                      rejetes par le controle de coherence du mouvement (risque de trainees), bruit temporel de la profondeur.
Methode, image par image :
  1. flot optique DIS (image t vers t-1) et controle aller-retour -> pixels fiables ;
  2. profondeur MiDaS, lissee dans le temps en suivant le mouvement (sauf pixels non fiables) ;
  3. rendu TSC (etalon.rendu_photo : exposition camera, brume, route mouillee Fresnel, flou de pluie, ombres de contact) ;
  4. accumulation temporelle de la sortie (comme un TAA) : melange avec la sortie precedente recalee, coupee la ou le
     mouvement n'est pas fiable, pour supprimer le scintillement sans trainee.
"""
import json, os, subprocess, sys, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etalon, profondeur  # noqa: E402


def lire_video(chemin, debut, duree, largeur):
    info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                           '-of', 'csv=p=0', chemin], capture_output=True, text=True, check=True).stdout.strip().split(',')
    w0, h0 = int(info[0]), int(info[1]); num, den = info[2].split('/'); fps = float(num) / float(den or 1)
    h = int(round(h0 * largeur / w0 / 2)) * 2
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(debut), '-t', str(duree), '-i', chemin, '-vf', f'scale={largeur}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = largeur * h * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield fps, np.frombuffer(b, np.uint8).reshape(h, largeur, 3)
    p.wait()


class Ecrivain:
    def __init__(self, chemin, w, h, fps):
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-',
                                   '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'medium', chemin], stdin=subprocess.PIPE)

    def ecrire(self, img):
        self.p.stdin.write(np.ascontiguousarray(img).tobytes())

    def fermer(self):
        self.p.stdin.close(); self.p.wait()


def recaler(img, flot):
    h, w = flot.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + flot[..., 0], gy + flot[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def etiquette(img, texte, pos=(10, 24)):
    cv2.putText(img, texte, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, texte, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def labo(video, sortie, ambiance='pluie', debut=0.0, duree=8.0, largeur=960, accumulation=0.65):
    os.makedirs(sortie, exist_ok=True)
    look = dict(etalon.LOOKS[ambiance])
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    prec = None
    mesures = []
    ecr = ecr_p = None
    t0 = time.time()
    for k, (fps, rgb) in enumerate(lire_video(video, debut, duree, largeur)):
        src = rgb.astype(np.float32) / 255
        gris = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        d = profondeur.disparite(src).astype(np.float32)
        fiable = None
        if prec is not None:
            arr = dis.calc(gris, prec['gris'], None)     # t -> t-1
            av = dis.calc(prec['gris'], gris, None)      # t-1 -> t
            ecart = np.linalg.norm(arr + recaler(av, arr), axis=-1)
            fiable = (ecart < 0.5 + 0.05 * np.linalg.norm(arr, axis=-1)).astype(np.float32)
            fiable = cv2.erode(fiable, np.ones((5, 5), np.uint8))
            d = d * (1 - 0.7 * fiable) + recaler(prec['d'], arr) * 0.7 * fiable
        out = etalon.rendu_photo(src, look, d).astype(np.float32)
        brut = out.copy()
        m = {'image': k}
        if prec is not None:
            a = accumulation * fiable[..., None]
            out = out * (1 - a) + recaler(prec['out'], arr) * a
            stat = fiable > 0.5
            m['scintillement_origine'] = float(np.abs(src - recaler(prec['src'], arr))[stat].mean())
            m['scintillement_tsc_sans_accumulation'] = float(np.abs(brut - recaler(prec['brut'], arr))[stat].mean())
            m['scintillement_tsc'] = float(np.abs(out - recaler(prec['out'], arr))[stat].mean())
            m['pixels_rejetes'] = float(1 - fiable.mean())
            m['bruit_profondeur'] = float(np.abs(d - recaler(prec['d'], arr))[stat].mean())
        mesures.append(m)
        prec = {'gris': gris, 'd': d, 'out': out, 'brut': brut, 'src': src}
        h, w = rgb.shape[:2]
        if ecr is None:
            ecr = Ecrivain(os.path.join(sortie, 'avant_apres.mp4'), w * 2, h, fps)
            ecr_p = Ecrivain(os.path.join(sortie, 'profondeur.mp4'), w, h, fps)
        g = etiquette(rgb.copy(), 'ETS2 origine')
        dte = etiquette((np.clip(out, 0, 1) * 255).astype(np.uint8), 'TSC labo - EXPERIMENTAL HORS JEU')
        ecr.ecrire(np.concatenate([g, dte], 1))
        dc = cv2.applyColorMap((np.clip(d, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_TURBO)[..., ::-1]
        ecr_p.ecrire(etiquette(dc.copy(), 'profondeur ESTIMEE (MiDaS), pas celle du jeu'))
        if k % 30 == 0:
            print(f'image {k}  {time.time() - t0:.0f} s', flush=True)
    if ecr: ecr.fermer(); ecr_p.fermer()
    cles = ['scintillement_origine', 'scintillement_tsc_sans_accumulation', 'scintillement_tsc', 'pixels_rejetes', 'bruit_profondeur']
    resume = {c: float(np.mean([m[c] for m in mesures if c in m])) for c in cles if any(c in m for m in mesures)}
    resume.update({'images': len(mesures), 'ambiance': ambiance, 'video': os.path.basename(video), 'debut_s': debut, 'duree_s': duree,
                   'secondes_calcul_par_image': (time.time() - t0) / max(1, len(mesures)),
                   'avertissement': 'Experimentation hors jeu : profondeur estimee, pas lue dans ETS2. Ne prouve rien sur le rendu en jeu.'})
    with open(os.path.join(sortie, 'mesures.json'), 'w', encoding='utf-8') as f:
        json.dump({'resume': resume, 'images': mesures}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(sortie, 'mesures.csv'), 'w', encoding='utf-8') as f:
        f.write('image;' + ';'.join(cles) + '\n')
        for m in mesures:
            f.write(str(m['image']) + ';' + ';'.join(f"{m.get(c, '')}" for c in cles) + '\n')
    print(json.dumps(resume, ensure_ascii=False, indent=1))
    return resume


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) < 2:
        print(__doc__); sys.exit(1)
    labo(a[0], a[1], a[2] if len(a) > 2 else 'pluie', float(a[3]) if len(a) > 3 else 0.0, float(a[4]) if len(a) > 4 else 8.0,
         int(a[5]) if len(a) > 5 else 960)
