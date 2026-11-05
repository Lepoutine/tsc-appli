# Budget de mémoire vidéo (VRAM) : ce que Windows autorise vraiment

- Source : Microsoft Learn, structure `DXGI_QUERY_VIDEO_MEMORY_INFO` (dxgi1_4.h), lue le 04/11/2026 :
  https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_4/ns-dxgi1_4-dxgi_query_video_memory_info
- Version : DXGI 1.4 (Windows 10 et suivants). Domaine : performance (textures HD de TSC Graphics). Statut : vérifié pour la définition des champs ; la mesure sur le Shadow reste à faire.

## Ce que dit la source (citations traduites)
- `Budget` : le budget de mémoire vidéo **fourni par le système**, en octets, que l'application doit viser. Si `CurrentUsage` dépasse `Budget`, l'application **peut subir des saccades ou des pertes de performance**, parce que le système travaille en arrière-plan pour partager équitablement la mémoire vidéo.
- `CurrentUsage` : ce que l'application utilise en ce moment, en octets.
- `AvailableForReservation` : ce que l'application peut réserver, via `IDXGIAdapter3::SetVideoMemoryReservation`.
- `CurrentReservation` : ce qu'elle a réservé ; le système s'en sert comme indication de son minimum de travail, et l'application doit pouvoir réduire sa consommation jusqu'à ce niveau.
- La structure est remplie par `IDXGIAdapter3::QueryVideoMemoryInfo(NodeIndex, MemorySegmentGroup, &info)`. Le groupe « local » est la mémoire de la carte, « non local » la mémoire système vue par la carte (à relire dans `DXGI_MEMORY_SEGMENT_GROUP` avant de coder : non lu aujourd'hui).

## Ce que TSC en tire
- Le chiffre qui compte pour les textures HD n'est **pas** la VRAM totale de la carte, mais `Budget` : il est plus petit (Windows et les autres programmes en gardent une part) et il bouge pendant le jeu.
- Règle proposée pour le cache HD du module TSC Graphics : rester sous `Budget` moins une marge (à mesurer), et relâcher des textures dès que `CurrentUsage` s'en approche. Le bug de budget du cache HD 0.14.1 est exactement ce cas.
- Mesure à faire sur le Shadow : relever `Budget` et `CurrentUsage` (groupe local) toutes les secondes depuis le module DX11, sur un trajet fixe, avec et sans textures HD. Tant que ce n'est pas fait, aucun chiffre de budget ne doit être annoncé.

## Limites
- La page ne dit rien de la vitesse à laquelle le budget change, ni de la marge à garder : c'est à mesurer, pas à supposer.
