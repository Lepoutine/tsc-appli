# Cloudflare Workers : limites du service TSC

- Source : https://developers.cloudflare.com/workers/platform/limits/ (lu le 03/11/2026)
- Version : documentation Cloudflare au 03/11/2026. Statut : vérifié (doc) ; le plan réel du compte TSC est à confirmer dans le tableau de bord.

| Limite | Gratuit | Payant |
|---|---|---|
| Temps CPU par requête | 10 ms | 30 s par défaut, jusqu'à 5 min (`cpu_ms`) |
| Requêtes par jour | 100 000 (remise à zéro minuit UTC) | sans limite |
| Sous-requêtes par requête | 50 | 10 000 |
| Mémoire par isolat | 128 Mo | 128 Mo |
| Taille du Worker (non compressé) | 64 Mio | 64 Mio |
| Variables + secrets | 64 | 128 |
| Taille d'une variable | 5 Ko | 5 Ko |

## Usage TSC
- L'assistant Claude dans Forge/atelier (étape 8) passera par le worker : un appel à l'API Claude est une sous-requête qui attend longtemps, mais le temps d'attente réseau n'est pas du temps CPU ; à vérifier par un test avant de promettre quoi que ce soit.
- La clé API reste un secret du worker, jamais dans l'appli.
- 100 000 requêtes/jour en gratuit : surveiller si la mémoire du pilote envoie chez tous les joueurs.
