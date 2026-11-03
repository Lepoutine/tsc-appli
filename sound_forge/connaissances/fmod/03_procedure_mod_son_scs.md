# Procédure officielle pour créer un mod de son (SCS + FMOD)

Statut : [vérifié] sur le wiki SCS (lu le 2026-11-03).
Sources :
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound/Modding
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound/Downloads

## Modèles et exemples officiels

| Fichier | Jeu | FMOD | Lien |
|---|---|---|---|
| Modèle 1.43 | 1.43 | 2.01.05 | https://download.eurotrucksimulator2.com/sound/fmod_template_sound_project_143_01.zip |
| Modèle 1.39 | 1.39 | 2.01.05 | https://download.eurotrucksimulator2.com/sound/fmod_template_sound_project_139_01.zip |
| Moteur Peterbilt 579 (avec le son distant) | 1.42 | 2.01.05 | https://download.eurotrucksimulator2.com/sound/example_sound_engine_peterbilt_579_142_01.zip |
| Sons de camion (exemple) | 1.39 | 2.01.05 | https://download.eurotrucksimulator2.com/sound/example_sounds_truck_139_01.zip |
| Sons du monde (exemple) | 1.40 | 2.01.05 | https://download.eurotrucksimulator2.com/sound/example_sounds_world_140_01.zip |

- Versions de FMOD par version du jeu selon le wiki : 1.37 → 2.00.07, 1.38 → 2.01.01, 1.39 → 2.01.05, 1.43 → 2.02.05 (le modèle 1.43 dit pourtant 2.01.05), 1.56 → 2.03.09.
- Le jeu 1.61 embarque FMOD 2.3.11 [vérifié sur le PC]. On compile donc avec FMOD Studio 2.03.x.
- Les exemples servent à copier la STRUCTURE des événements dans son propre projet, créé à partir du modèle. Il ne faut jamais livrer un exemple tel quel.
- Le modèle 1.43 a été vérifié le 2026-11-03 : il a les mêmes bus et GUID que le jeu 1.61.

## Étapes

1. **Projet**
   - Décompresser le modèle et renommer le `.fspro` (conseillé).
   - L'ouvrir dans FMOD Studio, sur une copie.
2. **Banque**
   - Créer une nouvelle banque (New Bank), avec un nom en minuscules, sans espace ni caractère spécial. Ce nom devient le nom du fichier.
   - FMOD crée lui-même un GUID unique.
3. **Événements**
   - Créer un nouvel événement (New Event) en 2D ou 3D, avec un nom simple.
   - L'assigner à la banque (Assign to Bank).
   - Le router vers le bon bus (Mixer Routing).
   - Régler la boucle et les paramètres comme le son qu'il remplace.
   - Pour dupliquer, faire un copier-coller, ce qui crée de nouveaux GUID.
4. **Build**
   - File > Build produit `build/<banque>.bank`. Ignorer `master.bank` et `master.strings.bank`.
5. **GUID**
   - File > Export GUIDs produit `build/GUIDs.txt`, à renommer en `<banque>.bank.guids`.
   - On peut l'élaguer pour ne garder que ses propres objets, mais ce n'est pas obligatoire.
6. **Livraison**
   - Livrer uniquement `<banque>.bank` et `<banque>.bank.guids`, plus les `.soundref` / `.sui` qui pointent vers ses événements.

## Trois façons de remplacer un son

1. **Remplacer une banque entière** : nouvelle banque du MÊME nom, qui écrase l'originale. C'est la façon la plus brutale, et elle entre en conflit avec les autres mods.
2. **Changer un son global ou par défaut** : nouvelle banque et nouvel événement, puis on écrase seulement le `.soundref`.
3. **Changer un composant (moteur, accessoire)** : nouvelle banque et nouvel événement, puis on écrase seulement le fichier de config de ce composant. C'est le choix de Sound Forge.

## À faire / à ne pas faire

- Toujours créer de nouvelles banques et de nouveaux événements. Réutiliser des GUID casse tout.
- Ne jamais renommer « master ».
- Ne jamais supprimer les bus standard. Les recréer sous le même nom ne marche pas.
- Écraser le moins de fichiers possible.
- Créer chaque nouveau projet à partir du modèle, jamais à partir d'un ancien projet.
