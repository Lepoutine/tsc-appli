# Protection des créations TSCF et signalement des usages non autorisés

Version 1.0 du 24/10/2026. Document technique de travail, **à faire relire par un professionnel du droit** avant de
s'en servir face à un tiers. Il ne garantit aucun résultat.

## 1. Règles avant toute intégration d'une ressource

1. Un fichier téléchargeable n'est pas libre de droits par défaut.
2. Avant d'intégrer une ressource : noter dans `registre_creations.json` son auteur, sa source (URL), la licence de la
   **version réellement utilisée**, et archiver la preuve dans `registre/preuves/` (capture datée de la page de licence ou
   de l'accord de l'auteur).
3. Origine ou licence incertaine → statut `a_clarifier` → pas de distribution jusqu'à la preuve.
   `python3 generer.py --verifier` refuse une ressource « origine à clarifier » marquée distribuable.
4. Ne jamais retirer les crédits d'origine, ne jamais présenter une ressource tierce comme une création TSCF.
5. Aucun droit exclusif n'est revendiqué sur un composant sous licence tierce : le © TSCF ne se met que sur ce que TSCF
   a créé (consigne de Poutine du 24/10/2026), vérifié par `generer.py`.

## 2. Ce que TSCF peut faire pour protéger ses créations

| Mesure | État | À faire |
|---|---|---|
| Licence claire par produit | Appli : `LICENCE.txt`. Mods : rien | Ajouter un `LICENCE.txt` court dans chaque mod (gratuit, pas de vente ni réupload, crédits) |
| Mentions de droits cohérentes | Partiel | Appliquer `MENTIONS_PRODUITS.md`, harmoniser les en-têtes des shaders |
| Historique des versions | Oui (git, `anciennes_versions/`) | Continuer ; noter chaque version dans le registre |
| Archives des sources | Bundles git sur le PC + fichiers du projet | Garder une 2e copie hors du PC (dépôt privé ou disque externe) |
| Preuve de date de création | Commits git datés | Option : enveloppe Soleau (INPI, numérique) ou dépôt chez un huissier pour les créations importantes |
| Marque « Truck So Clean France » / logo TSC | Non déposée | Option : dépôt de marque INPI (classes à choisir avec un conseil) |
| Empreintes des fichiers publiés | Oui (sha256 dans `catalogue_mods.json` et `update.json`) | Garder ces empreintes : elles prouvent quel fichier a été publié et quand |
| Secrets hors des fichiers distribués | Non (webhook Discord dans l'exe) | Régénérer le webhook, passer par le HUB |

## 3. Questions à poser à un juriste

1. Une grande partie du code et des textures a été produite avec l'assistance d'une IA (Claude) sous la direction de
   Poutine. Dans quelle mesure ces éléments sont-ils protégés par le droit d'auteur, et comment documenter l'apport
   créatif humain (consignes, choix, corrections) ?
2. Mods qui modifient des modèles SCS : les conditions de SCS Software permettent-elles de les distribuer gratuitement
   sur GitHub, et TSCF peut-il revendiquer des droits sur ses ajouts ?
3. Accords d'AkirixDesign3D et de l'auteur de Madame Afro : quelle forme suffit (message Discord, courriel) ?
4. « Truck So Clean France » est-il une association, une entreprise ou un groupe informel ? Qui est titulaire des droits
   (Poutine en personne ou TSCF) ? Les mentions doivent suivre la réponse.
5. Le `LICENCE.txt` de l'appli cite des articles du Code de la propriété intellectuelle : relecture de leur bon usage.

## 4. Procédure de signalement d'une utilisation non autorisée

1. **Constater** : capture d'écran datée, URL, nom du compte, fichier téléchargé si possible.
2. **Comparer** : calculer le sha256 du fichier trouvé et le comparer aux empreintes du catalogue ; noter ce qui est repris.
3. **Vérifier nos droits** dans le registre : la partie copiée est-elle bien une création TSCF ? (ex. une copie de la
   photo Pexels seule n'est pas une atteinte aux droits de TSCF).
4. **Contacter** l'auteur de la copie, poliment, en demandant retrait ou crédit, avec un délai.
5. **Signaler à la plateforme** (Steam Workshop, ModLand, Discord, GitHub : formulaires de retrait / DMCA) si pas de
   réponse.
6. **Consigner** chaque étape dans `registre/signalements/AAAA-MM-JJ_<plateforme>.md`.
7. Au-delà (vente, usage commercial important) : avis d'un professionnel avant toute démarche.

Si quelqu'un signale que TSCF utilise sa création sans droit : suspendre la distribution du produit concerné (statut
`a_clarifier`), répondre, vérifier les preuves, corriger les crédits ou retirer la ressource.
