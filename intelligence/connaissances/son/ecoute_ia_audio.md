# Écoute par IA : modèle audio par API (Gemini)

- Source : https://ai.google.dev/gemini-api/docs/generate-content/audio (lu le 03/11/2026)
- Source : https://aistudio.google.com/docs/pricing (lu le 03/11/2026)
- Version : documentation Google au 03/11/2026. Statut : vérifié (doc). Aucun essai fait ; le choix revient à Mendy (cahier des charges TSCF Audio Lab, sections 2 et 3).

## Ce que dit la doc
- Le modèle « comprend » aussi les sons qui ne sont pas de la parole (la doc cite le chant d'oiseau et les sirènes). On peut lui désigner un passage par horodatage MM:SS.
- Formats : WAV, MP3, AIFF, AAC, OGG, FLAC, M4A, Opus, WebM, etc. ; jusqu'à 9,5 h d'audio par requête.
- **Limite importante** : l'audio est réduit à 16 kbit/s et mis en mono avant analyse. Il juge bien les événements (claquement, clic, saturation, rythme, souffle), moins bien la finesse des graves et des aigus. Les mesures TSC (LUFS, bandes, crête) restent donc nécessaires.
- 32 jetons par seconde d'audio, soit 1 920 jetons par minute.
- Prix (offre payante, par million de jetons en entrée) : Gemini 3.6/3.8 Flash 0,75 $ (jusqu'au 31/12/2026), Gemini 2.5 Flash 1,00 $ pour l'audio, Gemini 2.5 Pro 1,25 $. Une minute de son coûte donc environ 0,15 à 0,25 centime, sans compter la réponse écrite.
- Offre gratuite : ses données servent à améliorer les produits Google. Offre payante : elles ne servent pas.

## Usage TSC prévu (si Mendy dit oui)
- Clé API créée par Mendy, gardée comme secret, jamais écrite dans le dépôt ni dans la mémoire.
- Offre payante seulement, pour que ses sons ne servent pas à entraîner un modèle tiers.
- Essai d'abord sur 5 extraits dont Mendy connaît le verdict (ex. aperçu v6 « trop aigu », v7, ralenti réel 164L). On ne s'y fie que si l'IA retrouve ses remarques.
- Le rapport cite ce que le modèle a « entendu », avec horodatage, à côté des mesures. La décision finale reste l'écoute de Mendy.
