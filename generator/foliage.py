"""Folhagem com textura recortada (estilo das arvores do pz3d) para o make_veg_pack.

- leaf_texture(): desenha um cacho de folhas com fundo transparente (PNG RGBA).
- add_cards(): espalha cartoes de folha num volume, com normais apontando para fora da copa.
- render_preview(): rasterizador simples com z-buffer e recorte por alfa, para conferir os modelos.
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TEX_SIZE = 256

def _rgb(c, k=1.0):
    return tuple(max(0, min(255, int(255 * v * k))) for v in c)

def leaf_texture(path, pal, kind='larga', seed=0):
    """pal: 3 cores (escuro, medio, claro) em 0..1. kind: larga, miuda, agulha."""
    rnd = random.Random(seed)
    S = TEX_SIZE * 2                       # desenha em 2x e reduz: bordas suaves
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    n = {'larga': 46, 'miuda': 110, 'agulha': 160}[kind]
    L = {'larga': 0.20, 'miuda': 0.11, 'agulha': 0.16}[kind] * S
    W = {'larga': 0.42, 'miuda': 0.45, 'agulha': 0.08}[kind]
    leaves = []
    for i in range(n):
        r = 0.40 * S * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        cx, cy = S / 2 + r * math.cos(a), S / 2 + r * math.sin(a)
        ang = a + rnd.uniform(-0.9, 0.9)   # folhas apontando para fora do cacho
        depth = r / (0.40 * S)             # borda mais clara, miolo mais escuro
        leaves.append((depth, cx, cy, ang, L * rnd.uniform(0.75, 1.15)))
    leaves.sort()                           # miolo primeiro, borda por cima
    for depth, cx, cy, ang, ln in leaves:
        t = depth + rnd.uniform(-0.25, 0.25)
        base = pal[0] if t < 0.35 else (pal[1] if t < 0.75 else pal[2])
        col = _rgb(base, rnd.uniform(1.05, 1.35))
        dx, dy = math.cos(ang), math.sin(ang); px, py = -dy, dx
        pts = []
        for k in range(13):                 # contorno de folha: ponta fina, barriga larga
            u = k / 12
            w = math.sin(math.pi * u) ** 0.8 * ln * W * 0.5
            pts.append((cx + dx * ln * (u - 0.3) + px * w, cy + dy * ln * (u - 0.3) + py * w))
        for k in range(12, -1, -1):
            u = k / 12
            w = math.sin(math.pi * u) ** 0.8 * ln * W * 0.5
            pts.append((cx + dx * ln * (u - 0.3) - px * w, cy + dy * ln * (u - 0.3) - py * w))
        dr.polygon(pts, fill=col + (255,))
        if kind != 'agulha':                # nervura central
            vc = _rgb(base, 0.8)
            dr.line([(cx - dx * ln * 0.3, cy - dy * ln * 0.3), (cx + dx * ln * 0.62, cy + dy * ln * 0.62)],
                    fill=vc + (255,), width=max(1, S // 256))
    img = img.resize((TEX_SIZE, TEX_SIZE), Image.LANCZOS)
    a = np.array(img)
    a[..., 3] = np.where(a[..., 3] > 110, 255, 0)      # alfa binario: recorte limpo
    Image.fromarray(a).save(path)

def needle_texture(path, pal, snow=False, seed=0):
    """raminho de pinheiro: galhinho central com agulhas finas para os lados (e neve opcional)."""
    rnd = random.Random(seed)
    S = TEX_SIZE * 2
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    for b in range(5):                                  # 5 raminhos abrindo do centro
        a = -math.pi / 2 + (b - 2) * 0.5 + rnd.uniform(-0.15, 0.15)
        L = S * rnd.uniform(0.32, 0.46)
        x0, y0 = S / 2, S * 0.92
        x1, y1 = x0 + math.cos(a) * L * 1.6, y0 + math.sin(a) * L * 1.6
        dr.line([(x0, y0), (x1, y1)], fill=_rgb((0.20, 0.14, 0.10)) + (255,), width=S // 90)
        for k in range(60):
            t = k / 60
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for sgn in (-1, 1):
                na = a + sgn * rnd.uniform(0.5, 1.0)
                nl = S * 0.09 * (1 - 0.6 * t) * rnd.uniform(0.7, 1.1)
                base = pal[0] if t < 0.3 else (pal[1] if t < 0.7 else pal[2])
                col = _rgb(base, rnd.uniform(1.0, 1.4))
                dr.line([(px, py), (px + math.cos(na) * nl, py + math.sin(na) * nl)], fill=col + (255,), width=max(2, S // 170))
        if snow:
            for k in range(7):
                t = rnd.uniform(0.2, 0.9)
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                r = S * rnd.uniform(0.02, 0.04)
                dr.ellipse([px - r * 1.6, py - r - S * 0.015, px + r * 1.6, py + r - S * 0.015], fill=(225, 230, 236, 255))
    img = img.resize((TEX_SIZE, TEX_SIZE), Image.LANCZOS)
    a = np.array(img); a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    Image.fromarray(a).save(path)

def blade_texture(path, pal, seed=0):
    """lamina de grama: base escura, ponta clara, com veios. sem transparencia (o formato vem da geometria)."""
    rnd = random.Random(seed)
    W, H = 64, 256
    a = np.zeros((H, W, 4), float)
    v = np.linspace(1, 0, H)[:, None]                    # v=1 no topo da imagem = ponta
    c0, c1, c2 = (np.array(c) * 255 * 1.25 for c in pal)
    col = np.where(v[..., None] < 0.5, c0 + (c1 - c0) * (v[..., None] / 0.5), c1 + (c2 - c1) * ((v[..., None] - 0.5) / 0.5))
    col = np.broadcast_to(col, (H, W, 3)).copy()
    x = np.linspace(-1, 1, W)[None, :]
    col *= (1 - 0.18 * np.abs(x))[..., None]              # bordas um pouco mais escuras
    for _ in range(5):                                    # veios longitudinais
        cx = rnd.uniform(-0.7, 0.7)
        col[:, np.abs(x[0] - cx) < 0.04] *= 0.82
    col[:, np.abs(x[0]) < 0.05] *= 1.12                   # nervura central clara
    a[..., :3] = np.clip(col, 0, 255); a[..., 3] = 255
    Image.fromarray(a.astype(np.uint8)).save(path)

def frond_texture(path, pal, snow=False, seed=0):
    """fronde de samambaia vertical: raque central e foliolos recortados afinando ate a ponta."""
    rnd = random.Random(seed)
    W, H = 256, 1024
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    dr.line([(W / 2, H), (W / 2, H * 0.02)], fill=_rgb(pal[0], 0.9) + (255,), width=6)
    n = 26
    for k in range(n):
        t = (k + 0.5) / n
        y = H * (1 - t * 0.97)
        L = W * 0.47 * math.sin(math.pi * (0.15 + 0.85 * t)) ** 0.7 * (1 - 0.5 * t)
        base = pal[0] if t < 0.3 else (pal[1] if t < 0.7 else pal[2])
        col = _rgb(base, rnd.uniform(1.1, 1.4))
        for sgn in (-1, 1):
            pts = [(W / 2, y + 6)]
            for j in range(9):                             # foliolo com dentinhos
                u = j / 8
                lobe = 1 + 0.25 * math.sin(u * math.pi * 6)
                pts.append((W / 2 + sgn * L * u, y - 4 - H * 0.012 * math.sin(math.pi * u) * lobe - u * H * 0.02))
            for j in range(8, -1, -1):
                u = j / 8
                pts.append((W / 2 + sgn * L * u, y + 4 + H * 0.010 * math.sin(math.pi * u) - u * H * 0.02))
            dr.polygon(pts, fill=col + (255,))
            if snow and rnd.random() < 0.5:
                xa, xb = sorted((W / 2 + sgn * L * 0.3, W / 2 + sgn * L * 0.7))
                dr.ellipse([xa - 10, y - 14, xb + 10, y + 2], fill=(225, 230, 236, 255))
    a = np.array(img); a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    Image.fromarray(a).save(path)

def single_leaf_texture(path, pal, seed=0):
    """uma folha so, vertical (base embaixo, ponta em cima), com nervuras."""
    rnd = random.Random(seed)
    S = 256
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    pts = []
    for k in range(21):
        u = k / 20
        w = math.sin(math.pi * u) ** 0.75 * S * 0.30
        pts.append((S / 2 + w, S * (1 - u)))
    for k in range(20, -1, -1):
        u = k / 20
        w = math.sin(math.pi * u) ** 0.75 * S * 0.30
        pts.append((S / 2 - w, S * (1 - u)))
    dr.polygon(pts, fill=_rgb(pal[1], 1.2) + (255,))
    # metade de cima mais clara (luz), metade de baixo mais escura
    for k in range(10):
        u = 0.15 + 0.07 * k
        y = S * (1 - u)
        w = math.sin(math.pi * u) ** 0.75 * S * 0.30
        dr.line([(S / 2, y), (S / 2 + w * 0.9, y - S * 0.07)], fill=_rgb(pal[0], 1.1) + (255,), width=2)
        dr.line([(S / 2, y), (S / 2 - w * 0.9, y - S * 0.07)], fill=_rgb(pal[0], 1.1) + (255,), width=2)
    dr.line([(S / 2, S), (S / 2, S * 0.03)], fill=_rgb(pal[2], 1.2) + (255,), width=4)
    a = np.array(img); a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    Image.fromarray(a).save(path)

def water_texture(path, pal, seed=0):
    """agua parada: ondulacoes suaves entre as cores medidas na agua do jogo. opaca."""
    rng = np.random.default_rng(seed)
    S = 256
    yy, xx = np.mgrid[0:S, 0:S] / S
    f = np.zeros((S, S))
    for k in range(6):                                   # soma de ondas em direcoes aleatorias (repete nas bordas)
        fx, fy = rng.integers(1, 6, 2) * rng.choice([-1, 1], 2)
        f += np.sin(2 * np.pi * (fx * xx + fy * yy) + rng.uniform(0, 6.28)) / (k + 1.5)
    f = (f - f.min()) / (f.max() - f.min())
    lo, mid, hi = (np.array(c) for c in pal)
    col = np.where(f[..., None] < 0.5, lo + (mid - lo) * (f[..., None] / 0.5), mid + (hi - mid) * ((f[..., None] - 0.5) / 0.5))
    a = np.dstack([np.clip(col, 0, 255), np.full((S, S), 255)]).astype(np.uint8)
    Image.fromarray(a).save(path)

def rock_texture(path, pal, seed=0):
    """rocha: ruido em varias escalas, rachaduras escuras e manchas de liquen. opaca e repete nas bordas."""
    rng = np.random.default_rng(seed)
    S = 256
    yy, xx = np.mgrid[0:S, 0:S] / S
    f = np.zeros((S, S))
    for k in range(1, 7):                                # ruido periodico (repete nas bordas)
        for _ in range(3):
            fx, fy = rng.integers(1, 2 ** k + 1, 2) * rng.choice([-1, 1], 2)
            f += np.sin(2 * np.pi * (fx * xx + fy * yy) + rng.uniform(0, 6.28)) / (k ** 1.3)
    f = (f - f.min()) / (f.max() - f.min())
    lo, mid, hi = (np.array(c) for c in pal)
    col = np.where(f[..., None] < 0.5, lo + (mid - lo) * (f[..., None] / 0.5), mid + (hi - mid) * ((f[..., None] - 0.5) / 0.5))
    img = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert('RGBA')
    dr = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for _ in range(9):                                   # rachaduras
        x, y = rnd.uniform(0, S), rnd.uniform(0, S); a = rnd.uniform(0, 6.28)
        pts = [(x, y)]
        for _ in range(rnd.randint(4, 9)):
            a += rnd.uniform(-0.6, 0.6); x += math.cos(a) * rnd.uniform(8, 22); y += math.sin(a) * rnd.uniform(8, 22)
            pts.append((x, y))
        dr.line(pts, fill=tuple(int(v * 0.55) for v in pal[0]) + (255,), width=2)
    for _ in range(14):                                  # liquen
        x, y, r = rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(4, 14)
        dr.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(96, 104, 72, 255))
    img.filter(ImageFilter.GaussianBlur(0.6)).save(path)

def _periodic_noise(S, rng, octaves=6, base=1, beta=1.6):
    """ruido isotropico e emendavel: ruido branco filtrado por 1/f^beta (FFT). base corta as manchas grandes."""
    w = rng.normal(0, 1, (S, S))
    fy = np.fft.fftfreq(S)[:, None] * S; fx = np.fft.fftfreq(S)[None, :] * S
    r = np.sqrt(fx ** 2 + fy ** 2)
    filt = np.where(r < base, 0.0, 1.0 / np.maximum(r, 1) ** beta)
    f = np.real(np.fft.ifft2(np.fft.fft2(w) * filt))
    return (f - f.min()) / (f.max() - f.min())

def _wrap_draw(dr, S, fn):
    """desenha 9 vezes (deslocado) para a textura emendar nas bordas."""
    for ox in (-S, 0, S):
        for oy in (-S, 0, S):
            fn(ox, oy)

def ground_texture(path, kind, pal, seed=0):
    """chao emendavel de 512 px: grama (capim desenhado), terra (torroes e pedrinhas) ou areia (graos)."""
    rng = np.random.default_rng(seed); rnd = random.Random(seed)
    S = 512
    lo, mid, hi = (np.array(c, float) for c in pal)
    f = _periodic_noise(S, rng, octaves=5, base=6)       # so detalhe fino: sem manchas grandes que viram listras
    f = 0.5 + (f - 0.5) * 0.6
    col = np.where(f[..., None] < 0.5, lo + (mid - lo) * (f[..., None] / 0.5), mid + (hi - mid) * ((f[..., None] - 0.5) / 0.5))
    grain = rng.normal(0, 7, (S, S, 1))
    img = Image.fromarray(np.clip(col + grain, 0, 255).astype(np.uint8)).convert('RGBA')
    dr = ImageDraw.Draw(img)
    if kind == 'grama':
        for _ in range(2600):                              # folhinhas de capim vistas de cima/obliquo
            x, y = rnd.uniform(0, S), rnd.uniform(0, S)
            a = rnd.uniform(0, 2 * math.pi); L = rnd.uniform(6, 18)
            c = tuple(int(v) for v in (lo if rnd.random() < 0.35 else (hi if rnd.random() < 0.4 else mid)) * rnd.uniform(0.8, 1.25))
            def blade_fn(ox, oy, x=x, y=y, a=a, L=L, c=c):
                dr.line([(x + ox, y + oy), (x + ox + math.cos(a) * L, y + oy + math.sin(a) * L)], fill=c + (255,), width=2)
            _wrap_draw(dr, S, blade_fn)
        for _ in range(60):                                # manchinhas de terra aparecendo
            x, y, r = rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(3, 8)
            c = (int(lo[0] * 0.9 + 15), int(lo[1] * 0.7), int(lo[2] * 0.6))
            _wrap_draw(dr, S, lambda ox, oy, x=x, y=y, r=r, c=c: dr.ellipse([x + ox - r, y + oy - r * 0.6, x + ox + r, y + oy + r * 0.6], fill=c + (255,)))
    elif kind == 'terra':
        for _ in range(500):                               # torroes
            x, y, r = rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(2, 7)
            k = rnd.uniform(0.7, 1.25); c = tuple(int(v * k) for v in mid)
            _wrap_draw(dr, S, lambda ox, oy, x=x, y=y, r=r, c=c: dr.ellipse([x + ox - r, y + oy - r * 0.7, x + ox + r, y + oy + r * 0.7], fill=c + (255,)))
        for _ in range(140):                               # pedrinhas
            x, y, r = rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(1.5, 4.5)
            g = rnd.randint(110, 170); c = (g, int(g * 0.95), int(g * 0.88))
            _wrap_draw(dr, S, lambda ox, oy, x=x, y=y, r=r, c=c: dr.ellipse([x + ox - r, y + oy - r * 0.8, x + ox + r, y + oy + r * 0.8], fill=c + (255,)))
        for _ in range(25):                                # gravetinhos
            x, y, a, L = rnd.uniform(0, S), rnd.uniform(0, S), rnd.uniform(0, 6.28), rnd.uniform(10, 26)
            c = tuple(int(v * 0.6) for v in lo)
            _wrap_draw(dr, S, lambda ox, oy, x=x, y=y, a=a, L=L, c=c: dr.line([(x + ox, y + oy), (x + ox + math.cos(a) * L, y + oy + math.sin(a) * L)], fill=c + (255,), width=2))
    else:  # areia
        for _ in range(3000):
            x, y = rnd.uniform(0, S), rnd.uniform(0, S)
            k = rnd.uniform(0.8, 1.15); c = tuple(int(min(255, v * k)) for v in mid)
            _wrap_draw(dr, S, lambda ox, oy, x=x, y=y, c=c: dr.point((x + ox, y + oy), fill=c + (255,)))
    arr = np.array(img.filter(ImageFilter.GaussianBlur(0.5)).convert('RGB'), float)
    arr *= (mid / arr.reshape(-1, 3).mean(0))
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA').save(path)

def make_texture(path, kind, pal, seed):
    if kind == 'agua': water_texture(path, pal, seed)
    elif kind in ('chao_grama', 'chao_terra', 'chao_areia'): ground_texture(path, kind[5:], pal, seed)
    elif kind == 'rocha': rock_texture(path, pal, seed)
    elif kind in ('larga', 'miuda', 'agulha'): leaf_texture(path, pal, kind, seed)
    elif kind == 'ramo': needle_texture(path, pal, False, seed)
    elif kind == 'ramo_neve': needle_texture(path, pal, True, seed)
    elif kind == 'lamina': blade_texture(path, pal, seed)
    elif kind == 'fronde': frond_texture(path, pal, False, seed)
    elif kind == 'fronde_neve': frond_texture(path, pal, True, seed)
    elif kind == 'folha': single_leaf_texture(path, pal, seed)
    else: raise ValueError(kind)

def _rot(axis, ang):
    x, y, z = axis; c, s = math.cos(ang), math.sin(ang); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])

def add_cards(m, center, radii, n, size, mat, rnd, shell=(0.55, 1.0), floor=0.0, normal_center=None, up_bias=0.0):
    """espalha n cartoes de folha num elipsoide. normais saem de normal_center (copa redonda)."""
    nc = np.array(normal_center if normal_center else center, dtype=float)
    R = np.array(radii, dtype=float); C = np.array(center, dtype=float)
    for _ in range(n):
        d = np.array([rnd.gauss(0, 1) for _ in range(3)]); d /= np.linalg.norm(d) + 1e-9
        if up_bias: d[2] = abs(d[2]) * up_bias + d[2] * (1 - up_bias); d /= np.linalg.norm(d) + 1e-9
        r = rnd.uniform(*shell)
        p = C + d * R * r
        p[2] = max(p[2], floor + size * 0.3)
        nrm = (p - nc) / (R + 1e-9); nrm /= np.linalg.norm(nrm) + 1e-9
        # cartao virado mais ou menos para fora, com giro e inclinacao aleatorios
        z = nrm + np.array([rnd.uniform(-0.6, 0.6) for _ in range(3)]); z /= np.linalg.norm(z) + 1e-9
        ref = np.array([0, 0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(ref, z); u /= np.linalg.norm(u); v = np.cross(z, u)
        rot = _rot(z, rnd.uniform(0, 2 * math.pi)); u, v = rot @ u, rot @ v
        s = size * rnd.uniform(0.75, 1.25) / 2
        quad = [p - u * s - v * s, p + u * s - v * s, p + u * s + v * s, p - u * s + v * s]
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if rnd.random() < 0.5: uvs = [(1 - a, b) for a, b in uvs]
        m.cards.append(([tuple(q) for q in quad], uvs, tuple(nrm), mat))

# ---------------- previa com textura ----------------
def render_preview(items, out_path, cols=8, cell=200, label_h=18, sprite_dir=None, floor=True):
    """items: lista de (nome, tris, mats, texdir). tris: (p0,p1,p2, uv0,uv1,uv2 ou None, normal, mat)."""
    rows = (len(items) + cols - 1) // cols
    W, H = cols * cell, rows * (cell + label_h)
    canvas = Image.new('RGB', (W, H), (196, 202, 190))
    dr = ImageDraw.Draw(canvas)
    L = np.array([-0.45, -0.75, 1.1]); L /= np.linalg.norm(L)
    tex_cache = {}
    for idx, (name, tris, mats, texdir) in enumerate(items):
        # enquadra o modelo na celula
        P = np.array([p for t in tris for p in t[:3]])
        def proj(p):
            x, y, z = p[..., 0] - 0.5, p[..., 1] - 0.5, p[..., 2]
            return np.stack([(x - y) * 0.866, (x + y) * 0.5 - z], -1), (x + y) + z * 0.5
        sp, _ = proj(P)
        lo, hi = sp.min(0), sp.max(0)
        tile = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
        tsp, _ = proj(tile)
        lo, hi = np.minimum(lo, tsp.min(0)), np.maximum(hi, tsp.max(0))
        sc = (cell - 16) / max(hi - lo)
        off = np.array([cell / 2, cell - 8]) - np.array([(lo[0] + hi[0]) / 2 * sc, hi[1] * sc])
        img = np.zeros((cell, cell, 3)); img[:] = (196, 202, 190)
        zb = np.full((cell, cell), -1e9)
        # chao do tile
        tri_list = ([(tile[0], tile[1], tile[2], None, None, None, (0, 0, 1), '__chao'),
                     (tile[0], tile[2], tile[3], None, None, None, (0, 0, 1), '__chao')] if floor else []) + list(tris)
        for t in tri_list:
            p = np.array(t[:3], float); uv = t[3:6]; n = np.array(t[6], float); mat = t[7]
            s2, dpt = proj(p); s2 = s2 * sc + off
            x0, y0 = np.floor(s2.min(0)).astype(int); x1, y1 = np.ceil(s2.max(0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, cell - 1), min(y1, cell - 1)
            if x1 < x0 or y1 < y0: continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = s2
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9: continue
            w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
            w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any(): continue
            z = w0 * dpt[0] + w1 * dpt[1] + w2 * dpt[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            ok = inside & (z > sub)
            if mat == '__chao':
                col = np.array([160, 170, 150.0]); rgb = np.broadcast_to(col, ok.shape + (3,))
            elif uv[0] is not None:
                key = (texdir, mat)
                if key not in tex_cache:
                    tex_cache.clear()     # uma textura por vez: as das placas sao grandes
                    tex_cache[key] = np.array(Image.open(f'{texdir}/{mat}.png').convert('RGBA'))
                tx = tex_cache[key]; th, tw = tx.shape[:2]
                U = w0 * uv[0][0] + w1 * uv[1][0] + w2 * uv[2][0]
                V = w0 * uv[0][1] + w1 * uv[1][1] + w2 * uv[2][1]
                iu = np.clip((U * tw).astype(int), 0, tw - 1); iv = np.clip(((1 - V) * th).astype(int), 0, th - 1)
                texel = tx[iv, iu].astype(float)
                ok = ok & (texel[..., 3] > 127)
                lum = 0.45 + 0.75 * max(0.0, float(n @ L))
                rgb = texel[..., :3] * lum
            else:
                lum = 0.45 + 0.75 * abs(float(n @ L)) if mat in ('galho', 'casca', 'casca_clara', 'c0') else \
                      0.45 + 0.75 * max(0.0, float(n @ L))
                col = np.array(mats[mat]) * 255 * 1.5 * lum
                rgb = np.broadcast_to(np.clip(col, 0, 255), ok.shape + (3,))
            sub[ok] = z[ok]
            img[y0:y1 + 1, x0:x1 + 1][ok] = rgb[ok]
        if sprite_dir:   # recorte com fundo transparente, para logo e capas
            rgba = np.dstack([np.clip(img, 0, 255), (zb > -1e9) * 255.0]).astype(np.uint8)
            Image.fromarray(rgba, 'RGBA').save(os.path.join(sprite_dir, name + '.png'))
        x, y = (idx % cols) * cell, (idx // cols) * (cell + label_h)
        canvas.paste(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), (x, y))
        dr.text((x + 4, y + cell + 2), name, fill=(0, 0, 0))
    canvas.save(out_path)
