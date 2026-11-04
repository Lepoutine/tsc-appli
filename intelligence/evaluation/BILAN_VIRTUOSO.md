# Bilan TSC Virtuoso

Généré par `intelligence/evaluation/audit.py` le 2026-11-04. Tout chiffre vient du banc d'évaluation ou des fichiers ; ce qui n'est pas mesuré est écrit tel quel.

Grille de certification (objectifs, pas niveaux atteints) : Connaissances métier vérifiées 20 %, Diagnostic et résolution 25 %, Autonomie opérationnelle 20 %, Qualité et fiabilité des livrables 25 %, Innovation démontrée 10 %.

| IA | État | Note (grille mesurée) | Examen d'entrée | Fiches | Outils | Mémoire | Apprend |
|---|---|---|---|---|---|---|---|
| IA Pro Photoréalisme | non mesuré d'ici | non mesuré | — | 1 (verifie_partiel 1) | 8 | 4 | oui |
| TSC Textures Expert | non mesuré d'ici | non mesuré | — | 1 (verifie_partiel 1) | 7 | 4 | oui |
| TSC Performance Expert | non mesuré d'ici | non mesuré | — | 2 (verifie 2) | 7 | 3 | non |
| TSC Mod Engineering Expert | non mesuré d'ici | non mesuré | — | 3 (verifie 3) | 10 | 6 | non |
| TSC Sound Engineering Expert | opérationnel (mesuré) | 95/100 (80 %) | 95/100 | 6 (concu 1, verifie 4, verifie_partiel 1) | 8 | 17 | non |
| TSC FMOD Sound Engineering / Sound Forge Expert | partiel : 20 % de la grille mesurée, épreuves PC à passer | 80/100 (20 %) | 80/100 | 7 (a_verifier 1, verifie 5, verifie_partiel 1) | 7 | 6 | oui |
| TSC Driving Intelligence Expert | non mesuré d'ici | non mesuré | — | 2 (verifie 1, verifie_partiel 1) | 8 | 2 | non |
| TSC Software Engineering Expert | partiel : 25 % de la grille mesurée | 100/100 (25 %) | 100/100 | 3 (verifie 3) | 7 | 2 | non |
| TSC Knowledge & Quality Expert | partiel : 50 % de la grille mesurée | 100/100 (50 %) | 100/100 | 4 (concu 1, verifie 3) | 6 | 2 | non |
| TSC Atelier Spartan / Blender Expert | non mesuré d'ici | non mesuré | — | 4 (verifie 2, verifie_partiel 2) | 6 | 1 | oui |

## Épreuves par IA

**IA Pro Photoréalisme** : aucune épreuve automatique d'ici
  Épreuves à passer sur le PC : écart jeu/réel d'une version du plugin sur le jeu de captures fixe

**TSC Textures Expert** : aucune épreuve automatique d'ici
  Épreuves à passer sur le PC : TSC-IA textures : gain en dB sur images réelles jamais vues

**TSC Performance Expert** : aucune épreuve automatique d'ici
  Épreuves à passer sur le PC : Test-PerfLab.ps1 + diagnostic avant/après

**TSC Mod Engineering Expert** : aucune épreuve automatique d'ici
  Épreuves à passer sur le PC : game.log réel -> mod et fichier fautifs ; contrôle .scs

**TSC Sound Engineering Expert** : OK son_lufs (5/5 sur les derniers passages); OK son_crete_vraie (5/5 sur les derniers passages); OK son_regime (4/5 sur les derniers passages); OK son_regime_bas (5/5 sur les derniers passages); OK son_regime_reel (5/5 sur les derniers passages); OK son_innovation_regime (4/5 sur les derniers passages); OK son_raccord (5/5 sur les derniers passages); OK son_cycle (5/5 sur les derniers passages)

**TSC FMOD Sound Engineering / Sound Forge Expert** : OK forge_roles (5/5 sur les derniers passages); OK forge_ia_js (3/5 sur les derniers passages)
  Épreuves à passer sur le PC : build fmodstudiocl de l'exemple Peterbilt + GUID

**TSC Driving Intelligence Expert** : aucune épreuve automatique d'ici
  Épreuves à passer sur le PC : rejouer traces.json sur le Pilote de tête

**TSC Software Engineering Expert** : OK logiciel_tests (5/5 sur les derniers passages); OK logiciel_js (5/5 sur les derniers passages)

**TSC Knowledge & Quality Expert** : OK qualite_base (5/5 sur les derniers passages); OK qualite_mutation (5/5 sur les derniers passages); OK qualite_boucle (5/5 sur les derniers passages)

**TSC Atelier Spartan / Blender Expert** : aucune épreuve automatique d'ici
  Épreuves à passer sur le PC : Blender -b -P : UV, échelle, origine d'un modèle SCS

## Lacunes, par priorité (64)

- P1 · atelier · aucun examen : examen d'entrée à construire (épreuves PC : Blender -b -P : UV, échelle, origine d'un modèle SCS)
- P1 · conduite · base de connaissances trop mince : 2 fiche(s) : compléter avec la documentation officielle et les sources libres du domaine
- P1 · conduite · aucun examen : examen d'entrée à construire (épreuves PC : rejouer traces.json sur le Pilote de tête)
- P1 · graphics · base de connaissances trop mince : 1 fiche(s) : compléter avec la documentation officielle et les sources libres du domaine
- P1 · graphics · aucun examen : examen d'entrée à construire (épreuves PC : écart jeu/réel d'une version du plugin sur le jeu de captures fixe)
- P1 · mods · aucun examen : examen d'entrée à construire (épreuves PC : game.log réel -> mod et fichier fautifs ; contrôle .scs)
- P1 · performance · base de connaissances trop mince : 2 fiche(s) : compléter avec la documentation officielle et les sources libres du domaine
- P1 · performance · aucun examen : examen d'entrée à construire (épreuves PC : Test-PerfLab.ps1 + diagnostic avant/après)
- P1 · textures · base de connaissances trop mince : 1 fiche(s) : compléter avec la documentation officielle et les sources libres du domaine
- P1 · textures · aucun examen : examen d'entrée à construire (épreuves PC : TSC-IA textures : gain en dB sur images réelles jamais vues)
- P2 · atelier · outil ou capacité manquante : pilotage de Blender en arriere-plan (blender -b -P) teste
- P2 · atelier · outil ou capacité manquante : fiches API Python Blender 3.6 et formats PMG/PMD/PMA sourcees
- P2 · atelier · outil ou capacité manquante : controles automatiques UV / echelle / origine / nombre de triangles
- P2 · atelier · outil ou capacité manquante : export SCS -> mod par le moteur de TSC Mod Engineering (pas de second moteur)
- P2 · atelier · fiche à vérifier : conversion_skins (verifie_partiel) : Conversion Tools et peintures (paint jobs)
- P2 · atelier · fiche à vérifier : outils_libres (verifie_partiel) : Outils existants et ressources libres
- P2 · conduite · outil ou capacité manquante : tests rejoues automatiquement sur traces.json a chaque version
- P2 · conduite · outil ou capacité manquante : fiche limites de l'API telemetrie (ce qui n'est pas expose)
- P2 · conduite · outil ou capacité manquante : analyse des memoires recues des joueurs
- P2 · conduite · fiche à vérifier : reglement_561_2006 (verifie_partiel) : Temps de conduite, pauses et repos UE (561/2006, articles 6 a 9)
- P2 · forge · outil ou capacité manquante : pilotage fmodstudiocl de bout en bout (build + export GUID) teste sur le PC
- P2 · forge · outil ou capacité manquante : generateur .soundref/.sui a partir des GUID reels
- P2 · forge · outil ou capacité manquante : controle automatique du mod audio avant de le declarer utilisable
- P2 · forge · outil ou capacité manquante : dossier projet complet sur le Bureau + rapport de tests
- P2 · forge · fiche à vérifier : fmod_scripting (verifie_partiel) : Piloter FMOD Studio par script
- P2 · forge · fiche à vérifier : recette_moteur (a_verifier) : Recette Sound Forge : événement moteur par script
- P2 · graphics · outil ou capacité manquante : fiches DX11/HLSL officielles sourcees
- P2 · graphics · outil ou capacité manquante : jeu de captures de reference fixe pour comparer chaque version
- P2 · graphics · outil ou capacité manquante : sources du socle tscf_probe 0.2 a 0.9h (introuvables sur le Shadow)
- P2 · graphics · fiche à vérifier : audit_pipeline_161 (verifie_partiel) : Pipeline de rendu ETS2 1.61.1.9 : G-buffer, profondeur Z inverse, cout du SSR
- P2 · logiciel · outil ou capacité manquante : sources dans un depot versionne (aujourd'hui des bundles)
- P2 · logiciel · outil ou capacité manquante : suite de tests unique lancee avant chaque version
- P2 · logiciel · outil ou capacité manquante : verification ETS2 nouvelle version (SDK, plugins)
- P2 · mods · outil ou capacité manquante : analyseur automatique de game.log (erreurs -> mod -> fichier)
- P2 · mods · outil ou capacité manquante : fiches SII/SUI/.mat/.tobj officielles sourcees
- P2 · mods · outil ou capacité manquante : etendre Verifier_Mods_TSC.ps1 (PC) au controle complet avant livraison, sans creer un 2e verificateur
- P2 · performance · outil ou capacité manquante : mesure frametime fiable derriere ReShade (PresentMon ne voit pas la vraie chaine)
- P2 · performance · outil ou capacité manquante : fiche VRAM / budget textures HD
- P2 · performance · outil ou capacité manquante : comparaison avant/apres automatique
- P2 · qualite · outil ou capacité manquante : liste de controle de livraison par type (mod, appli, plugin)
- P2 · qualite · outil ou capacité manquante : detection des erreurs deja corrigees qui reviennent
- P2 · qualite · fiche à vérifier : livraison_mod (concu) : Liste de controle de livraison d'un mod TSC
- P2 · son · outil ou capacité manquante : passer mesure_son.py sur les 360 sons et les extraits v2 (outil fait, pas encore lance sur le PC)
- P2 · son · outil ou capacité manquante : module d'isolation : soustraction spectrale du bruit + detection et classement des evenements (numpy) ; separation par reseau (Demucs, MIT) seulement si torch est installe sur le Shadow, accord de Mendy
- P2 · son · outil ou capacité manquante : detection automatique des points de boucle
- P2 · son · outil ou capacité manquante : test d'ecoute en jeu d'un son TSC
- P2 · son · fiche à vérifier : guide_metier (verifie_partiel) : Guide de métier Sound Forge
- P2 · son · fiche à vérifier : tsc_clapet (concu) : TSC Clapet : clapet d'échappement sur touche
- P2 · textures · outil ou capacité manquante : fiches materiaux (route, beton, metal, peinture) sourcees
- P2 · textures · outil ou capacité manquante : jeu de test fixe de textures avant/apres
- P2 · textures · outil ou capacité manquante : regle UV ecrite et verifiee automatiquement
- P2 · textures · fiche à vérifier : outils_libres (verifie_partiel) : Outils existants et ressources libres
- P3 · forge · critère de certification non mesuré : Connaissances métier vérifiées
- P3 · forge · critère de certification non mesuré : Diagnostic et résolution
- P3 · forge · critère de certification non mesuré : Qualité et fiabilité des livrables
- P3 · forge · critère de certification non mesuré : Innovation démontrée
- P3 · logiciel · critère de certification non mesuré : Connaissances métier vérifiées
- P3 · logiciel · critère de certification non mesuré : Diagnostic et résolution
- P3 · logiciel · critère de certification non mesuré : Autonomie opérationnelle
- P3 · logiciel · critère de certification non mesuré : Innovation démontrée
- P3 · qualite · critère de certification non mesuré : Connaissances métier vérifiées
- P3 · qualite · critère de certification non mesuré : Autonomie opérationnelle
- P3 · qualite · critère de certification non mesuré : Innovation démontrée
- P3 · son · critère de certification non mesuré : Autonomie opérationnelle
