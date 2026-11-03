# Outils existants et ressources libres, vérifiés pour une appli payante

Règle (Mendy, 2026-11-03) : on intègre les outils gratuits et fiables qui existent déjà, après avoir vérifié leur licence. TSC vend son logiciel et sa connexion Claude, jamais les produits des autres.

## Outils

| Outil | Rôle | Licence | Verdict |
|---|---|---|---|
| fmod-studio-mcp (EYamanS) https://github.com/EYamanS/fmod-studio-mcp | Serveur MCP qui pilote FMOD Studio par le port 3663, avec un outil par fonction de l'API | MIT | Intégrable, en gardant la mention de copyright. Sa liste d'API (api_spec.json) sert de référence. |
| FmodStudioMCP (xDarkzx) https://github.com/xDarkzx/Dans_Fmod_Studio_MCP | Serveur MCP FMOD plus haut niveau (événements, sons, paramètres, automation, banques, build) | Apache-2.0 | Intégrable avec les fichiers LICENSE et NOTICE. Il contient des pièges vérifiés en direct sur la 2.03.14 (voir fmod/01). |
| SCS Blender Tools 2.4.1 | Export de modèles vers le jeu | GPL-2.0 | Le joueur l'installe. TSC ne le revend pas et le pilote seulement. |
| Conversion Tools 2.21 (SCS) | Conversion vers le format du jeu | Gratuit, fourni par SCS | Le joueur le télécharge chez SCS. |
| Paint Job Packer | Arborescence de skins et gabarits | à vérifier | En attente. |
| FMOD Studio 2.03 | Création et build des banques | Gratuit pour les budgets inférieurs à 200 k$ (licence indie FMOD), à vérifier pour TSC | Le joueur l'installe lui-même. |

Piste importante : avec un serveur MCP FMOD, la connexion Claude de l'appli peut créer les événements dans FMOD Studio sans que le joueur touche à FMOD. La même idée existe pour Blender (serveurs MCP Blender), à étudier pour l'atelier.

## Ressources libres

| Source | Contenu | Licence | Utilisation |
|---|---|---|---|
| Poly Haven (api.polyhaven.com) | Modèles, textures, HDRI | CC0. API gratuite même en commercial, avec « Powered by Poly Haven » si l'appli l'utilise en direct | OK |
| ambientCG | Textures PBR | CC0 | OK |
| Kenney | Objets simples | CC0 | OK |
| OpenGameArt (filtré CC0) | Sons, modèles | CC0 (vérifier chaque fichier) | OK |
| Freesound | Sons | CC0 / CC-BY / CC-BY-NC selon le son. L'API demande un accord commercial avec l'UPF pour une appli vendue | Le joueur télécharge sur le site et importe. Pas d'API dans l'appli sans accord. |
| Sonniss GameAudioGDC (gratuit) | Échantillons de bibliothèques pro (Scania R143 1990, Volvo F12, Volvo A30E, Ural, ZIL...) | Licence v2.0 du 27/08/2026 : usage commercial dans des projets finis, sans crédit. INTERDIT de distribuer les sons « as sound effects », même modifiés. INTERDIT de s'en servir pour entraîner une IA ou une technologie qui génère des sons. Les mods ne sont pas mentionnés | En attente. Il faut l'accord écrit de Sonniss (mods + produit avec assistant IA). Jamais dans l'appli comme bibliothèque. Téléchargement par parties de plusieurs Go. |
| Pack « Truck Engines » MagicSoundEffects (itch.io, 15 $) | 6 camions, boucles ralenti/bas/moyen/haut/très haut, accélérations, décélérations, démarrage, arrêt | Usage commercial dans des jeux, pas de redistribution des fichiers seuls. Contradiction « un seul projet commercial » sur la page | À faire confirmer par le vendeur pour les mods |
| Pixabay (sons) | Sons | Licence Pixabay (vérifier la version en vigueur) | À vérifier |

Refusés : NC (non commercial), ND (sans modification), « gratuit » sans licence écrite, fichiers extraits de jeux, logos et marques déposées.
Chaque ressource gardée a un `LICENCE.txt` et une ligne dans `Outils admin\soundforge\bibliotheque_libre\INDEX.csv`. Les ressources CC-BY vont dans les crédits.

## Sons déjà présents sur le PC du joueur (choix préféré de Mendy, 2026-11-03)

- On décode les banques FMOD du jeu ou des mods (FSB5 dans le `.bank`) avec vgmstream (licence de type ISC, intégrable avec sa mention) ou python-fsb5 (MIT). On travaille sur une copie, et les originaux ne sont jamais modifiés.
- Après modification dans l'atelier, on obtient une NOUVELLE banque (nom et GUID neufs) et un mod qui pointe seulement le moteur choisi.
- Sons du jeu SCS : les reprendre dans des mods ETS2 est une pratique courante. La politique de SCS est à vérifier avant toute publication.
- Sons d'un mod tiers : il faut l'accord de l'auteur.
- L'appli ne transporte jamais ces sons. L'extraction se fait sur le PC du joueur, depuis sa propre copie du jeu.
