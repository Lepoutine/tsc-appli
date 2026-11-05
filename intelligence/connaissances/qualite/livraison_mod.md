# Liste de contrôle de livraison d'un mod TSC

- Sources : fiches `formats_scs` (wiki SCS Formats + Mod manager, lus le 03/11/2026), `fmodstudiocl` (manuel FMOD 2.03), `regle_noms_sii_11`, `regles_mods_mendy`, `piege_zip_scs`.
- Version : ETS2 1.61, au 03/11/2026. Statut : conçu (liste TSC écrite à partir de sources vérifiées, pas encore appliquée par un outil).

## Avant de montrer un mod à Mendy
1. manifest.sii à la racine, unité `mod_package : .nom`, `package_version` à jour, icône .jpg 276x162, description .txt UTF-8.
2. Archive : zip lisible par le jeu (méthode et attributs, voir piège zip .scs) ; pas de dossier racine en trop.
3. Noms d'unités : chaque segment ≤ 11 caractères (sauf suffixe `.addon_hookup`).
4. Extensions connues du moteur seulement ; aucun fichier temporaire (.blend1, .psd, Thumbs.db).
5. Son : `.bank` + `.bank.guids` issus d'un vrai build FMOD (jamais inventés), `.soundref` pointant vers un événement qui existe dans la banque.
6. Pas de version UK (conduite à droite), copyright TSCF seulement sur ce que TSC a créé.
7. Aperçu validé par Mendy avant toute installation ; installation seulement dans TSCF_Lab, avec sauvegarde.
8. Après le test en jeu : relire game.log, zéro erreur venant du mod.
