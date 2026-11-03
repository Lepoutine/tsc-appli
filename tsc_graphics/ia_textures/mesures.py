# TSC Textures IA - mesures objectives qui decident si une version est meilleure (regles de la boucle automatique).
import torch
import torch.nn.functional as F


def luma(x):
    return 0.2126 * x[:, 0:1] + 0.7152 * x[:, 1:2] + 0.0722 * x[:, 2:3]


def psnr(a, b):
    m = F.mse_loss(luma(a), luma(b)).item()
    return 99.0 if m <= 1e-12 else -10.0 * torch.log10(torch.tensor(m)).item()


def hautes_freq(x, s=2.0):
    from degradation import flou_gauss
    return x - flou_gauss(x, s)


def ratio_detail(sortie, vrai):
    """Energie du detail fin produit / energie du detail du vrai : ~1 = grain realiste ; <0,7 = trop lisse (aplat) ; >1,4 = trop dur."""
    a = hautes_freq(luma(sortie)).pow(2).mean().sqrt().item()
    b = hautes_freq(luma(vrai)).pow(2).mean().sqrt().item()
    return a / max(b, 1e-6)


def cellules(x):
    """Motifs reguliers inventes (le defaut vu avec les modeles generalistes sur le gravier) : pic du spectre du detail
    par rapport a sa mediane. Plus c'est haut, plus il y a de motif periodique."""
    d = hautes_freq(luma(x))[:, 0]
    s = torch.fft.rfft2(d - d.mean(dim=(-2, -1), keepdim=True)).abs()
    s[..., 0, 0] = 0
    s = s.flatten(1)
    return (s.max(1).values / (s.median(1).values + 1e-6)).mean().item()


def correlation_detail(sortie, base):
    """Correlation entre le detail ajoute et le detail deja present dans la texture du jeu agrandie : basse = l'IA invente."""
    a = hautes_freq(luma(sortie), 1.5).flatten(1); b = hautes_freq(luma(base), 1.5).flatten(1)
    a = a - a.mean(1, keepdim=True); b = b - b.mean(1, keepdim=True)
    return ((a * b).sum(1) / (a.norm(dim=1) * b.norm(dim=1) + 1e-8)).mean().item()
