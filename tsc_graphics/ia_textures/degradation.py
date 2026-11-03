# TSC Textures IA - fabrique une "texture de jeu" a partir d'une vraie photo : flou, reduction x4, compression BC1 (DXT1)
# comme les textures du jeu, leger bruit. Le reseau apprend le chemin inverse : texture de jeu -> matiere reelle.
import numpy as np
import torch
import torch.nn.functional as F


def flou_gauss(x, sigma):
    if sigma < 0.05:
        return x
    r = max(1, int(round(sigma * 3)))
    t = torch.arange(-r, r + 1, dtype=x.dtype, device=x.device)
    k = torch.exp(-(t ** 2) / (2 * sigma * sigma)); k = k / k.sum()
    c = x.shape[1]
    x = F.conv2d(F.pad(x, (r, r, 0, 0), mode="reflect"), k.view(1, 1, 1, -1).repeat(c, 1, 1, 1), groups=c)
    x = F.conv2d(F.pad(x, (0, 0, r, r), mode="reflect"), k.view(1, 1, -1, 1).repeat(c, 1, 1, 1), groups=c)
    return x


def bc1(x):
    """Simule la compression BC1 par blocs 4x4 : 2 couleurs extremes (axe principal) en RGB565, 4 niveaux interpoles."""
    n, c, h, w = x.shape
    b = x.reshape(n, c, h // 4, 4, w // 4, 4).permute(0, 2, 4, 3, 5, 1).reshape(n, h // 4, w // 4, 16, 3)
    m = b.mean(3, keepdim=True)
    d = b - m
    cov = d.transpose(-1, -2) @ d
    v = torch.ones(n, h // 4, w // 4, 3, 1, dtype=x.dtype, device=x.device)
    for _ in range(4):   # iteration de puissance : axe principal du bloc
        v = cov @ v; v = v / (v.norm(dim=-2, keepdim=True) + 1e-8)
    p = (d @ v).squeeze(-1)
    lo = m.squeeze(3) + p.min(-1, keepdim=True).values * v.squeeze(-1)
    hi = m.squeeze(3) + p.max(-1, keepdim=True).values * v.squeeze(-1)
    q = torch.tensor([31.0, 63.0, 31.0], dtype=x.dtype, device=x.device)
    lo = torch.round(lo.clamp(0, 1) * q) / q; hi = torch.round(hi.clamp(0, 1) * q) / q
    pal = torch.stack([lo, hi, (2 * lo + hi) / 3, (lo + 2 * hi) / 3], 3)   # n,H,W,4,3
    dist = ((b.unsqueeze(4) - pal.unsqueeze(3)) ** 2).sum(-1)              # n,H,W,16,4
    i = dist.argmin(-1)
    out = torch.gather(pal, 3, i.unsqueeze(-1).expand(*i.shape, 3))
    return out.reshape(n, h // 4, w // 4, 4, 4, 3).permute(0, 5, 1, 3, 2, 4).reshape(n, c, h, w)


def degrader(hr, gen=None, fixe=False):
    """hr : n,3,H,W dans [0,1] (H, W multiples de 16). Rend lr : n,3,H/4,W/4."""
    rng = np.random.default_rng(0 if fixe else None) if gen is None else gen
    x = flou_gauss(hr, float(rng.uniform(0.2, 1.2)))
    mode = ["area", "bicubic", "bilinear"][int(rng.integers(3))]
    x = F.interpolate(x, scale_factor=0.25, mode=mode, **({} if mode == "area" else {"align_corners": False}))
    x = x.clamp(0, 1)
    if rng.uniform() < 0.8:
        h, w = x.shape[-2:]
        x = bc1(x[..., : h - h % 4, : w - w % 4])
    if rng.uniform() < 0.3:
        x = x + torch.randn_like(x) * float(rng.uniform(0, 0.01))
    return x.clamp(0, 1)
