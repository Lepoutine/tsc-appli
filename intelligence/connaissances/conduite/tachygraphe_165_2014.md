# Tachygraphe : ce que le conducteur enregistre (règlement 165/2014, article 34)

- Source : https://www.legislation.gov.uk/eur/2014/165/article/34 (lue le 04/11/2026). EUR-Lex refuse la lecture automatique : texte non relu sur EUR-Lex.
- Version : texte « révisé » de legislation.gov.uk : base UE révisée au 20/08/2020, plus des modifications britanniques jusqu'au 24/12/2022. Ce n'est **pas** la version UE en vigueur.
- Statut : vérifié partiel. Le principe (quatre activités, saisie manuelle hors véhicule) ne dépend pas des modifications britanniques ; les détails nationaux, si.

## Ce que dit l'article 34
- Le conducteur utilise une feuille ou une **carte conducteur chaque jour où il conduit**, et la laisse en place jusqu'à la fin de sa période de travail journalière (sauf retrait autorisé).
- Avec deux conducteurs ou plus dans un véhicule à tachygraphe numérique, chacun met **sa** carte dans la bonne fente.
- L'heure enregistrée doit correspondre à l'heure officielle du pays d'immatriculation du véhicule.
- Avec le sélecteur, le conducteur enregistre séparément : **le temps de conduite, les autres travaux, la disponibilité, les pauses et le repos** (et le repos à bord d'un ferry ou d'un train).
- Les activités faites loin du véhicule sont **saisies à la main** sur la carte, par la fonction de saisie manuelle du tachygraphe.
- Tachygraphe numérique : le conducteur saisit le pays de début et de fin de journée et le premier arrêt après une frontière, sauf si le tachygraphe enregistre lui-même la position (article 8).

## Ce que TSC en tire pour le tachygraphe du Pilote de tête
- Quatre états à tenir, pas deux : conduite, autre travail, disponibilité, pause ou repos. La télémétrie ne donne aucun de ces états (fiche `limites_api_telemetrie`) : le TSC les déduit (véhicule qui roule = conduite) et laisse le joueur choisir les trois autres.
- Les seuils (4 h 30, 45 min, 9 h, 11 h, 45 h) viennent de la fiche `reglement_561_2006`.
- Équipage multiple : une carte par conducteur, donc un compteur par joueur dans un convoi.
