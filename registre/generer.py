# (c) 2026 Truck So Clean France. Registre des créations et des crédits TSCF.
# Vérifie registre_creations.json puis produit REGISTRE_CREATIONS.md (lecture) et CREDITS.txt (à joindre aux produits).
#   python3 generer.py            vérifie et régénère
#   python3 generer.py --verifier vérifie seulement (code de sortie 1 en cas d'erreur)
# On ne modifie que le JSON : les deux autres fichiers sont régénérés.
import json, os, re, sys

ICI = os.path.dirname(os.path.abspath(__file__))
CHAMPS = ['id', 'nom', 'categorie', 'origine', 'auteurs', 'source', 'licence', 'autorisations', 'modifications',
          'redistribution', 'credits', 'projets', 'statut', 'a_faire', 'verifie_le']
LISTES = {'auteurs', 'projets', 'a_faire'}
ORIGINES_TSCF = ('originale_tscf', 'tscf_sur_ressource_autorisee')
COPYRIGHT_TSCF = re.compile(r'©[^.]*(Truck So Clean|TSCF)|(Truck So Clean France|TSCF)[^.]*(Tous droits|propriété)', re.I)
ORDRE_STATUT = ['bloque', 'a_clarifier', 'distribuable_sous_conditions', 'distribuable', 'non_distribue']


def charger():
    with open(os.path.join(ICI, 'registre_creations.json'), encoding='utf-8') as f:
        return json.load(f)


def verifier(reg):
    err = []
    origines, statuts = reg['valeurs']['origine'], reg['valeurs']['statut']
    vus = set()
    for i, r in enumerate(reg['ressources']):
        nom = r.get('id', '#%d' % i)
        for c in CHAMPS:
            if c not in r:
                err.append('%s : champ « %s » manquant' % (nom, c))
            elif c in LISTES and not isinstance(r[c], list):
                err.append('%s : « %s » doit être une liste' % (nom, c))
            elif c not in LISTES and c != 'a_faire' and not str(r[c]).strip():
                err.append('%s : « %s » vide' % (nom, c))
        if nom in vus:
            err.append('%s : identifiant en double' % nom)
        vus.add(nom)
        if r.get('origine') not in origines:
            err.append('%s : origine « %s » inconnue' % (nom, r.get('origine')))
        if r.get('statut') not in statuts:
            err.append('%s : statut « %s » inconnu' % (nom, r.get('statut')))
        # une origine non établie ne peut pas être déclarée distribuable (règle 1.4)
        if r.get('origine') == 'a_clarifier' and r.get('statut') in ('distribuable', 'distribuable_sous_conditions'):
            err.append('%s : origine à clarifier mais statut « %s »' % (nom, r.get('statut')))
        # le copyright TSCF ne se met que sur ce que TSCF a créé (consigne de Poutine du 24/10/2026)
        if COPYRIGHT_TSCF.search(r.get('credits', '')) and (r.get('origine') not in ORIGINES_TSCF or r.get('statut') == 'a_clarifier'):
            err.append('%s : © TSCF sur une ressource qui n\'est pas une création TSCF établie' % nom)
        if r.get('statut') == 'a_clarifier' and not r.get('a_faire'):
            err.append('%s : à clarifier sans action « a_faire »' % nom)
    return err


def cellule(v):
    if isinstance(v, list):
        v = ' ; '.join(v) if v else '—'
    return str(v).replace('|', '\\|').replace('\n', ' ')


def markdown(reg):
    o, s = reg['valeurs']['origine'], reg['valeurs']['statut']
    res = sorted(reg['ressources'], key=lambda r: (ORDRE_STATUT.index(r['statut']), r['categorie'], r['id']))
    L = ['# Registre des créations et des crédits TSCF',
         '',
         '> Fichier généré par `generer.py` à partir de `registre_creations.json` (version %s du %s). Ne pas modifier à la main.'
         % (reg['version_registre'], reg['date']),
         '>',
         '> ' + reg['avertissement'],
         '']
    compte = {}
    for r in res:
        compte[r['statut']] = compte.get(r['statut'], 0) + 1
    L += ['## Résumé', '', '| Statut | Nombre |', '|---|---|']
    L += ['| %s | %d |' % (s[k], compte[k]) for k in ORDRE_STATUT if k in compte]
    bloquants = [r for r in res if r['statut'] in ('bloque', 'a_clarifier')]
    L += ['', '## À clarifier ou bloqué', '']
    for r in bloquants:
        L.append('- **%s** (%s) : %s' % (r['nom'], s[r['statut']].split(' (')[0], ' ; '.join(r['a_faire']) or 'ne pas utiliser'))
    L += ['', '## Toutes les ressources', '',
          '| Nom | Catégorie | Origine | Auteurs | Licence | Statut | Projets |', '|---|---|---|---|---|---|---|']
    for r in res:
        L.append('| ' + ' | '.join(cellule(x) for x in (
            r['nom'], r['categorie'], o[r['origine']], r['auteurs'], r['licence'], s[r['statut']], r['projets'])) + ' |')
    L += ['', '## Fiches détaillées', '']
    for r in res:
        L += ['### %s' % r['nom'], '',
              '- Identifiant : `%s`' % r['id'],
              '- Catégorie : %s' % r['categorie'],
              '- Origine : %s' % o[r['origine']],
              '- Auteurs : %s' % cellule(r['auteurs']),
              '- Source : %s' % r['source'],
              '- Licence : %s' % r['licence'],
              '- Autorisations : %s' % r['autorisations'],
              '- Modifications : %s' % r['modifications'],
              '- Redistribution : %s' % r['redistribution'],
              '- Crédits à afficher : %s' % r['credits'],
              '- Projets : %s' % cellule(r['projets']),
              '- Statut : %s' % s[r['statut']],
              '- À faire : %s' % cellule(r['a_faire']),
              '- Vérifié le : %s' % r['verifie_le'], '']
    return '\n'.join(L)


def credits(reg):
    L = ['CRÉDITS - TRUCK SO CLEAN FRANCE (TSCF)',
         'Registre %s du %s' % (reg['version_registre'], reg['date']), '',
         'Le copyright TSCF ne porte que sur les créations TSCF de la première liste.', '',
         '1. CRÉATIONS TSCF', '']
    garde = [r for r in sorted(reg['ressources'], key=lambda r: r['nom'].lower())
             if r['statut'] != 'bloque' and not r['credits'].startswith('À définir')]
    L += ['- %s : %s' % (r['nom'], r['credits']) for r in garde
          if r['origine'] in ORIGINES_TSCF and r['statut'] != 'a_clarifier']
    L += ['', '2. COMPOSANTS DE TIERS (ce ne sont pas des créations TSCF ; ils restent la propriété de leurs auteurs,',
          '   sous leur propre licence)', '']
    L += ['- %s : %s' % (r['nom'], r['credits']) for r in garde
          if r['origine'] not in ORIGINES_TSCF or r['statut'] == 'a_clarifier']
    return '\n'.join(L) + '\n'


def main():
    reg = charger()
    err = verifier(reg)
    for e in err:
        print('ERREUR', e)
    if err:
        sys.exit(1)
    print('%d ressources, registre valide' % len(reg['ressources']))
    if '--verifier' in sys.argv:
        return
    with open(os.path.join(ICI, 'REGISTRE_CREATIONS.md'), 'w', encoding='utf-8') as f:
        f.write(markdown(reg) + '\n')
    with open(os.path.join(ICI, 'CREDITS.txt'), 'w', encoding='utf-8') as f:
        f.write(credits(reg))
    print('REGISTRE_CREATIONS.md et CREDITS.txt régénérés')


if __name__ == '__main__':
    main()
