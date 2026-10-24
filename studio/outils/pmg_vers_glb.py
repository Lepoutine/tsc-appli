# TSCF Spartan Studio : conversion d'un modele SCS (.pmg + .pmd + .mat) en fichier glTF binaire (.glb) pour l'apercu 3D.
# Le modele reste sur le PC (fichiers du jeu ou du mod d'origine) : rien n'est publie.
#
#   python3 pmg_vers_glb.py --code <TSC>/tests_pilote/cuir --racine <dossier extrait> --modele tnkdorse/chassis.pmg
#           [--roue tnkdorse/upg/wheel/disk.pmg --roue tnkdorse/upg/wheel/ftire.pmg] [--look 0] --sortie citerne.glb
#
# Chaque piece est classee d'apres l'effet de sa matiere : peinture (truckpaint, UV de peinture gardee), chrome, verre,
# feu, noir, couleur ; les ombres factices sont ignorees. Les reperes (hook, wheel_*, ...) deviennent des noeuds « loc:<nom> ».
# Axes SCS gardes tels quels : x a droite, y en haut, avant vers -z, en metres.
import argparse, json, os, re, struct, sys
import numpy as np

def lire_mat(racine, chemin):
    p = os.path.join(racine, chemin.lstrip('/'))
    if not os.path.isfile(p): return {'effet': '', 'diffuse': [0.5, 0.5, 0.5], 'env': 0}
    t = open(p, encoding='utf-8', errors='replace').read()
    e = re.search(r'effect\s*:\s*"([^"]+)"', t); d = re.search(r'diffuse\s*:\s*\{\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', t)
    f = re.search(r'env_factor\s*:\s*\{\s*([\d.]+)', t)
    return {'effet': e.group(1) if e else '', 'diffuse': [float(x) for x in d.groups()] if d else [1, 1, 1], 'env': float(f.group(1)) if f else (1.0 if 'env' in (e.group(1) if e else '') else 0)}

def classer(nom, m):
    n = nom.split('/')[-1].lower(); e = m['effet']; lum = sum(m['diffuse']) / 3
    if n.startswith(('golge', 'fakeshadow')) or 'shadow_only' in e or 'fakeshadow' in e: return None
    if 'truckpaint' in e: return 'peinture'
    if 'glass' in e: return 'feu' if any(k in n for k in ('stob', 'stop', 'lamp', 'feu')) else 'verre'
    if 'stob' in n or 'stopl' in n: return 'feu'
    if 'env' in e and m['env'] >= 0.4 and lum > 0.25: return 'chrome'
    if lum < 0.12: return 'noir'
    return 'couleur'

def lire_modele(S, racine, pmg, look):
    g = S.PMG(os.path.join(racine, pmg)); d = S.PMD(os.path.join(racine, pmg[:-4] + '.pmd')); mats = d.look(look)
    lots = {}
    for p in g.pieces:
        nom = mats[p.mat]; m = lire_mat(racine, nom); k = classer(nom, m)
        if k == 'couleur' and 'tire' in os.path.basename(pmg): k = 'pneu'
        if not k: continue
        pos = p.pos(); nrm = p.nrm(); t = p.tris().astype(np.uint32)
        # sens des triangles : glTF attend le sens direct (normale de face du meme cote que les normales des sommets)
        if len(t):
            fn = np.cross(pos[t[:, 1]] - pos[t[:, 0]], pos[t[:, 2]] - pos[t[:, 0]])
            if (np.einsum('ij,ij->i', fn, nrm[t].sum(1)) < 0).mean() > 0.5: t = t[:, ::-1].copy()
        nuv = p.rec[3] if len(p.rec) > 3 else 1
        alt = 'altuv' in m['effet'] and nuv > 1
        uv = p.uv(1 if alt else 0) if p.rel(2) is not None else np.zeros((len(pos), 2), np.float32)
        cle = (k, tuple(round(c, 3) for c in m['diffuse'])) if k != 'peinture' else (k, ())
        lots.setdefault(cle, []).append((pos, nrm, uv, t))
    locs = []
    for i in range(len(g.locs) // 44):
        h, x, y, z, sc, qw, qx, qy, qz, _ = struct.unpack('<Q8fi', g.locs[44 * i:44 * i + 44])
        locs.append((S.untoken(h), [x, y, z], [qx, qy, qz, qw]))
    return lots, locs

class GLB:
    def __init__(s): s.bin = bytearray(); s.j = {'asset': {'version': '2.0', 'generator': 'TSCF Spartan Studio'}, 'scene': 0,
                                                    'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [], 'materials': [], 'accessors': [], 'bufferViews': []}
    def vue(s, a, cible):
        while len(s.bin) % 4: s.bin += b'\0'
        o = len(s.bin); s.bin += a.tobytes(); s.j['bufferViews'].append({'buffer': 0, 'byteOffset': o, 'byteLength': a.nbytes, 'target': cible})
        return len(s.j['bufferViews']) - 1
    def acc(s, a, typ, cible, mm=False):
        comp = {np.dtype('<f4'): 5126, np.dtype('<u4'): 5125}[a.dtype]
        d = {'bufferView': s.vue(a, cible), 'componentType': comp, 'count': len(a), 'type': typ}
        if mm: d['min'] = a.min(0).tolist(); d['max'] = a.max(0).tolist()
        s.j['accessors'].append(d); return len(s.j['accessors']) - 1
    def maillage(s, nom, lots):
        prims = []
        for (k, coul), morceaux in lots.items():
            P, N, U, T, base = [], [], [], [], 0
            for pos, nrm, uv, t in morceaux: P.append(pos); N.append(nrm); U.append(uv); T.append(t + base); base += len(pos)
            P = np.concatenate(P).astype('<f4'); N = np.concatenate(N).astype('<f4'); U = np.concatenate(U).astype('<f4'); T = np.concatenate(T).ravel().astype('<u4')
            n = np.linalg.norm(N, axis=1, keepdims=True); N = (N / np.maximum(n, 1e-8)).astype('<f4')
            s.j['materials'].append({'name': k, 'pbrMetallicRoughness': {'baseColorFactor': list(coul or (1, 1, 1)) + [1], 'metallicFactor': 0, 'roughnessFactor': 0.5},
                                     'doubleSided': True, 'extras': {'categorie': k}})
            prims.append({'attributes': {'POSITION': s.acc(P, 'VEC3', 34962, True), 'NORMAL': s.acc(N, 'VEC3', 34962), 'TEXCOORD_0': s.acc(U, 'VEC2', 34962)},
                          'indices': s.acc(T, 'SCALAR', 34963), 'material': len(s.j['materials']) - 1})
        s.j['meshes'].append({'name': nom, 'primitives': prims}); return len(s.j['meshes']) - 1
    def noeud(s, d, racine=False):
        s.j['nodes'].append(d); i = len(s.j['nodes']) - 1
        if racine: s.j['scenes'][0]['nodes'].append(i)
        return i
    def ecrire(s, chemin):
        while len(s.bin) % 4: s.bin += b'\0'
        s.j['buffers'] = [{'byteLength': len(s.bin)}]
        js = json.dumps(s.j, separators=(',', ':')).encode()
        while len(js) % 4: js += b' '
        out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(s.bin)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(s.bin), 0x004E4942) + bytes(s.bin)
        open(chemin, 'wb').write(out)

def main():
    a = argparse.ArgumentParser(); a.add_argument('--code', required=True); a.add_argument('--racine', required=True); a.add_argument('--modele', required=True)
    a.add_argument('--roue', action='append', default=[]); a.add_argument('--look', type=int, default=0); a.add_argument('--sortie', required=True)
    a.add_argument('--nom', default=None)
    o = a.parse_args(); sys.path.insert(0, o.code); import scs_model as S
    lots, locs = lire_modele(S, o.racine, o.modele, o.look)
    G = GLB(); enfants = [G.noeud({'name': 'corps', 'mesh': G.maillage('corps', lots)})]
    if o.roue:
        rl = {}
        for r in o.roue:
            l2, _ = lire_modele(S, o.racine, r, 0)
            for k, v in l2.items(): rl.setdefault(k, []).extend(v)
        mr = G.maillage('roue', rl)
        for nom, p, q in locs:
            if nom.startswith('wheel'):
                # les roues SCS sont modelisees pour le cote gauche : on les retourne de 180 degres a droite
                d = {'name': 'roue_' + nom, 'mesh': mr, 'translation': p}
                if p[0] > 0: d['rotation'] = [0, 1, 0, 0]
                enfants.append(G.noeud(d))
    for nom, p, q in locs: enfants.append(G.noeud({'name': 'loc:' + nom, 'translation': p, 'rotation': q}))
    G.noeud({'name': o.nom or os.path.splitext(os.path.basename(o.sortie))[0], 'children': enfants}, racine=True)
    G.ecrire(o.sortie)
    print('ok', o.sortie, os.path.getsize(o.sortie) // 1024, 'Ko', {k[0]: len(v) for k, v in lots.items()})

if __name__ == '__main__': main()
