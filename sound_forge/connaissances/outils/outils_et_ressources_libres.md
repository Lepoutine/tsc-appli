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
| Pixabay (sons) | Sons | Licence Pixabay (vérifier la version en vigueur) | À vérifier |

Refusés : NC (non commercial), ND (sans modification), « gratuit » sans licence écrite, fichiers extraits de jeux, logos et marques déposées.
Chaque ressource gardée a un `LICENCE.txt` et une ligne dans `Outils admin\soundforge\bibliotheque_libre\INDEX.csv`. Les ressources CC-BY vont dans les crédits.
