# Piloter FMOD Studio par script (sans que le joueur ouvre FMOD)

Statut : [vérifié] pour la liste des fonctions (référence officielle 2.03, reprise dans fmod-studio-mcp, MIT). [vérifié en direct par des tiers] pour les remarques marquées « 2.03.14 ». À revérifier sur le PC de Mendy (FMOD Studio 2.03.12 / 2.03.15) avant usage.
Sources : https://www.fmod.com/docs/2.03/studio/scripting-api-reference-project.html, https://www.fmod.com/docs/2.03/studio/scripting-terminal-reference.html, https://github.com/EYamanS/fmod-studio-mcp (MIT), https://github.com/xDarkzx/Dans_Fmod_Studio_MCP (Apache-2.0). Lu le 2026-11-03.

## Deux façons de lancer un script

1. **Serveur de scripts TCP** (FMOD Studio ouvert, projet chargé).
   - Activer : Preferences → Interface → Script Server, port **3663**, puis redémarrer FMOD Studio. Il est désactivé par défaut.
   - Une fois activé, le journal de FMOD indique `[Scripting] ScriptServer started on 127.0.0.1 (3663)`.
   - Le serveur n'écoute que si un projet est ouvert.
   - On envoie du JavaScript en texte UTF-8. FMOD l'évalue et renvoie le résultat sous forme de texte. Du texte de console peut précéder le résultat.
   - Bonne pratique : envelopper chaque commande dans `(function(){ try { ... return JSON.stringify({success:true,result:r}); } catch(e) { return JSON.stringify({success:false,error:String(e)}); } })()`, puis lire le dernier objet JSON de la réponse.
2. **Ligne de commande `fmodstudiocl.exe`** (sans fenêtre). [vérifié avec `-help` en 2.03.15, sur le PC de Mendy, le 2026-11-03]
   - Usage : `fmodstudiocl [-build] [-shared-audio-source-dir <dossier>] [-banks <b1,b2>] [-platforms <p1,p2>] [-export-guids] [-script <fichier.js>] [-diagnostic] [-ignore-warnings] [-log-dir <dossier>] [-log-max-file-size <octets>] [-working-dir <dossier>] [-unpack <dossier>] [-version] <projet.fspro>`
   - Exemple pour Sound Forge : `fmodstudiocl -build -banks "tsc_mon_v8,tsc_mon_v8_rm" -export-guids projet.fspro`. Ce n'est pas encore testé.
   - Pour lancer un script sur le projet : `fmodstudiocl -script creer_moteur.js projet.fspro`.
   - `-diagnostic` vérifie que le projet n'est pas corrompu.
   - Installation : `C:\Program Files\FMOD SoundSystem\FMOD Studio 2.03.15\`.
     - Le manuel hors ligne (60 pages HTML) est dans `documentation\FMOD Studio User Manual\`.
     - Les scripts d'exemple sont dans `scripts\` : AddAhdsrToSelectedEvents, AddGroupTrack, BatchRename, EngineDesigner, exportGUIDsHeader, RandomizeColors, SVN.
     - Un paquet d'exemples se trouve dans `examples\Examples.fspackage`.

Sound Forge utilisera la voie 2 pour le build, et la voie 1 (ou un script lancé par fmodstudiocl) pour créer les événements.

## Fonctions utiles (référence 2.03)

- **Projet**
  - `studio.project.create(entityName)` crée un objet. Exemples : `create('Event')`, `create('Bank')`.
  - `studio.project.lookup(cheminOuGuid)` retrouve un objet : `'event:/engine/engine'`, `'bank:/mon_moteur'`, `'bus:/outside/exterior/truck_engine'` ou `'{guid}'`.
  - `studio.project.importAudioFile(cheminAbsolu)` renvoie un Asset. L'opération est longue, car le fichier est copié dans le projet.
  - `studio.project.save()`.
  - `studio.project.build()` ou `studio.project.build({ banks: [...], platforms: [...] })`. Limiter le build à une banque va beaucoup plus vite. Les événements `buildStarted` et `buildEnded.connect(function(succes){...})` signalent le début et la fin.
  - `studio.project.exportGUIDs()` écrit `build/GUIDs.txt`.
  - `studio.project.deleteObject(obj)`.
  - `studio.project.filePath`.
- **Espace de travail**
  - `studio.project.workspace.addEvent(nom, avecSpatialiseur)` crée un événement, en 3D si le second argument est `true`.
  - `workspace.addGameParameter(definition)` crée un paramètre prédéfini du projet.
- **Événement**
  - `event.addGameParameter({ name, type: studio.project.parameterType.User, min, max })`.
  - `event.addGroupTrack(nom)` ajoute une piste audio.
  - `event.addMarkerTrack()`, puis `markerTrack.addRegion(position, longueur, nom, studio.project.regionLoopMode.Looping)` crée une région de boucle.
  - `event.getPath()`, `event.is3D()`, `event.isOneShot()`.
  - `event.relationships.banks.add(banque)` assigne l'événement à une banque.
  - `event.mixerInput.output = studio.project.lookup('bus:/...')` route vers un bus [à vérifier : nom exact de la relation].
- **Pistes et instruments**
  - `groupTrack.addSound(parametre, 'SingleSound', debut, longueur)`.
    - Sur la timeline : `parametre = event.timeline`.
    - Sur un paramètre : `parametre` est la définition du paramètre, et la position et la longueur sont exprimées en unités du paramètre (par exemple en tr/min).
  - `instrument.audioFile = asset` attache le son.
  - Les types d'instruments sont `SingleSound`, `MultiSound`, `ProgrammerSound`, `SoundScatterer` et `EventSound`.
  - `sound.setFadeInCurve(longueur, forme)` et `setFadeOutCurve` règlent les fondus entre instruments voisins sur un paramètre. C'est ainsi qu'on fait le fondu enchaîné rpm.
- **Automation**
  - `objet.addAutomator('volume' | 'pitch')`.
  - `automator.addAutomationCurve(parametre)`.
  - `courbe.addAutomationPoint(position, valeur)`.
  - Remarque 2.03.14 : `addAutomationCurve` crée TOUJOURS une nouvelle courbe. Il faut d'abord chercher dans `automator.relationships.automationCurves.destinations` une courbe déjà liée au même paramètre.
- **Modulateurs** : `objet.addModulator(type, propriete)`.
- **Conditions** : `triggerable.addParameterCondition(parametre, min, max)`, pour un instrument qui ne joue que si `load` est inférieur à 0,05, par exemple.
- **Introspection** :
  - `ManagedObject.id` donne le GUID. Il n'existe pas de `.guid`.
  - `obj.getPath()` est une méthode : `.path` vaut toujours undefined.
  - Autres outils : `obj.dump()`, `obj.document()` et `studio.project.model.<Entite>.findInstances()`.
- **Système**
  - `studio.system.start(exe, { workingDir, args, timeout })` lance un programme externe en bloquant.
  - `studio.system.readDir`, `studio.system.getFile`.
  - `studio.system.message` ouvre une fenêtre bloquante. À ÉVITER en automatique.

## Pièges connus

- Ne jamais joindre des instructions JS déjà terminées par « ; » avec des virgules (`a;,b;`) : c'est une erreur de syntaxe, et la réponse n'est pas du JSON.
- Les boîtes de dialogue (`alert`, `system.message`, `question`) bloquent FMOD. Il ne faut jamais en déclencher dans un script automatique.
- Le modèle SCS 1.43 est au format Studio 2.01 et FMOD 2.03 le convertit à l'ouverture. Il faut toujours travailler sur une copie (voir `../../docs/techniques_sound_forge.md`).
