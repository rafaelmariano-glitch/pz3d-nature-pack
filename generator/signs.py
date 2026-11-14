"""Faces de placas de transito desenhadas em alta resolucao (PIL) e montagem dos modelos."""
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = 'C:/Windows/Fonts/segoeuib.ttf'
YEL, BLK, WHT = (240, 196, 30), (20, 20, 20), (245, 245, 245)
GRN, BLU, RED = (22, 110, 62), (32, 64, 170), (196, 24, 32)

def _font(px): return ImageFont.truetype(FONT, px)

def _arrow(dr, pts, width, color, head=1.0):
    """linha grossa com ponta de seta no ultimo ponto."""
    dr.line(pts, fill=color, width=width, joint='curve')
    for p in pts: dr.ellipse([p[0] - width / 2, p[1] - width / 2, p[0] + width / 2, p[1] + width / 2], fill=color)
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0); L = width * 1.9 * head
    tip = (x1 + math.cos(a) * L * 0.6, y1 + math.sin(a) * L * 0.6)
    l = (x1 + math.cos(a + 2.3) * L, y1 + math.sin(a + 2.3) * L)
    r = (x1 + math.cos(a - 2.3) * L, y1 + math.sin(a - 2.3) * L)
    dr.polygon([tip, l, r], fill=color)

def _bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d
                         for a, b, c, d in zip(p0, p1, p2, p3)))
    return out

SYMBOL = {   # caminhos da seta em coordenadas 0..1 (y para baixo), dentro do losango
    'curva_dir': lambda: _bez((0.45, 0.80), (0.45, 0.50), (0.48, 0.38), (0.62, 0.26)),
    'curva_esq': lambda: _bez((0.55, 0.80), (0.55, 0.50), (0.52, 0.38), (0.38, 0.26)),
    'sinuosa':   lambda: _bez((0.50, 0.82), (0.36, 0.62), (0.64, 0.42), (0.48, 0.22)),
    'reversa_dir': lambda: _bez((0.42, 0.82), (0.42, 0.55), (0.62, 0.55), (0.60, 0.22)),
    'reversa_esq': lambda: _bez((0.58, 0.82), (0.58, 0.55), (0.38, 0.55), (0.40, 0.22)),
    'zigue':     lambda: (_bez((0.50, 0.84), (0.34, 0.74), (0.66, 0.62), (0.50, 0.52)) +
                          _bez((0.50, 0.52), (0.34, 0.42), (0.66, 0.32), (0.50, 0.20))[1:]),
}

def diamond_texture(path, symbol, S=1024):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    c = S / 2; R = S * 0.49
    dr.polygon([(c, c - R), (c + R, c), (c, c + R), (c - R, c)], fill=BLK + (255,))
    R2 = R * 0.94
    dr.polygon([(c, c - R2), (c + R2, c), (c, c + R2), (c - R2, c)], fill=YEL + (255,))
    R3 = R * 0.86
    dr.polygon([(c, c - R3), (c + R3, c), (c, c + R3), (c - R3, c)], outline=BLK + (255,), width=int(S * 0.018))
    pts = [(x * S, y * S) for x, y in SYMBOL[symbol]()]
    _arrow(dr, pts, int(S * 0.075), BLK + (255,))
    img.save(path)

def stop_texture(path, S=1024):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    def octo(r):
        return [(S / 2 + r * math.cos(math.pi / 8 + k * math.pi / 4), S / 2 + r * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    dr.polygon(octo(S * 0.49), fill=WHT + (255,))
    dr.polygon(octo(S * 0.455), fill=RED + (255,))
    f = _font(int(S * 0.27))
    dr.text((S / 2, S / 2), 'STOP', font=f, fill=WHT + (255,), anchor='mm')
    img.save(path)

def back_texture(path, front_path, gray=(150, 152, 156)):
    """verso cinza com o mesmo contorno da frente."""
    fr = Image.open(front_path).convert('RGBA')
    a = fr.split()[3]
    img = Image.new('RGBA', fr.size, gray + (255,)); img.putalpha(a)
    dr = ImageDraw.Draw(img)
    W, H = fr.size
    for k in range(1, 6):                      # trilhos de fixacao
        y = H * k / 6
        dr.line([(0, y), (W, y)], fill=tuple(int(v * 0.85) for v in gray) + (255,), width=max(2, H // 120))
    img.putalpha(a)
    img.save(path)

def _bent_arrow(dr, x, y, s, right, color):
    """seta de conversao (sobe e vira) usada nas placas verdes."""
    w = int(s * 0.17)
    sgn = 1 if right else -1
    pts = [(x, y + s * 0.62), (x, y + s * 0.08), (x + sgn * s * 0.62, y + s * 0.08)]
    _arrow(dr, pts, w, color, head=1.1)

def green_texture(path, text, arrow, W=2048, H=1152):
    """placa verde de cidade, inteira (sera cortada ao meio para os dois tiles)."""
    img = Image.new('RGBA', (W, H), WHT + (255,)); dr = ImageDraw.Draw(img)
    m = int(H * 0.035)
    dr.rounded_rectangle([m, m, W - m, H - m], radius=int(H * 0.06), fill=GRN + (255,))
    dr.rounded_rectangle([m * 2.2, m * 2.2, W - m * 2.2, H - m * 2.2], radius=int(H * 0.05), outline=WHT + (255,), width=int(H * 0.012))
    if arrow:
        _bent_arrow(dr, W * (0.42 if arrow == 'esq' else 0.58), H * 0.16, H * 0.52, arrow == 'dir', WHT + (255,))
    f = _font(int(H * 0.30))
    dr.text((W / 2, H * (0.70 if arrow else 0.52)), text, font=f, fill=WHT + (255,), anchor='mm')
    img.save(path)

def _icon(dr, kind, x, y, s):
    c = WHT + (255,); lw = max(3, int(s * 0.06))
    dr.rectangle([x, y, x + s, y + s], outline=c, width=lw)
    if kind == 'garfo':
        dr.line([(x + s * 0.35, y + s * 0.15), (x + s * 0.35, y + s * 0.85)], fill=c, width=lw * 2)
        for k in (-1, 0, 1): dr.line([(x + s * (0.35 + 0.08 * k), y + s * 0.15), (x + s * (0.35 + 0.08 * k), y + s * 0.4)], fill=c, width=lw)
        dr.ellipse([x + s * 0.55, y + s * 0.15, x + s * 0.72, y + s * 0.5], fill=c)
        dr.line([(x + s * 0.64, y + s * 0.4), (x + s * 0.64, y + s * 0.85)], fill=c, width=lw * 2)
    elif kind == 'bomba':
        dr.rectangle([x + s * 0.25, y + s * 0.2, x + s * 0.6, y + s * 0.85], fill=c)
        dr.rectangle([x + s * 0.32, y + s * 0.28, x + s * 0.53, y + s * 0.45], fill=BLU + (255,))
        dr.line([(x + s * 0.6, y + s * 0.35), (x + s * 0.78, y + s * 0.45), (x + s * 0.78, y + s * 0.75)], fill=c, width=lw)
    elif kind == 'carro':
        dr.rounded_rectangle([x + s * 0.12, y + s * 0.4, x + s * 0.88, y + s * 0.7], radius=int(s * 0.08), fill=c)
        dr.polygon([(x + s * 0.28, y + s * 0.4), (x + s * 0.36, y + s * 0.22), (x + s * 0.66, y + s * 0.22), (x + s * 0.74, y + s * 0.4)], fill=c)
        for k in (0.3, 0.7): dr.ellipse([x + s * (k - 0.09), y + s * 0.62, x + s * (k + 0.09), y + s * 0.8], fill=BLK + (255,))
    elif kind == 'cama':
        dr.rectangle([x + s * 0.12, y + s * 0.5, x + s * 0.88, y + s * 0.65], fill=c)
        dr.rectangle([x + s * 0.12, y + s * 0.3, x + s * 0.2, y + s * 0.8], fill=c)
        dr.rectangle([x + s * 0.8, y + s * 0.45, x + s * 0.88, y + s * 0.8], fill=c)
        dr.ellipse([x + s * 0.24, y + s * 0.36, x + s * 0.4, y + s * 0.5], fill=c)

def blue_texture(path, arrow, plate, W=2048, H=1600):
    """placa azul de area de descanso: seta, icones e (opcional) plaquinha REST AREA embaixo."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    top_h = H * (0.74 if plate else 1.0)
    m = int(H * 0.025)
    dr.rounded_rectangle([0, 0, W, top_h], radius=int(H * 0.04), fill=WHT + (255,))
    dr.rounded_rectangle([m, m, W - m, top_h - m], radius=int(H * 0.035), fill=BLU + (255,))
    y = top_h * 0.20
    if arrow == 'esq': _arrow(dr, [(W * 0.75, y), (W * 0.25, y)], int(top_h * 0.09), WHT + (255,))
    else: _arrow(dr, [(W * 0.25, y), (W * 0.75, y)], int(top_h * 0.09), WHT + (255,))
    s = min(top_h * 0.42, W * 0.84 / 4.6)
    for k, kind in enumerate(['garfo', 'bomba', 'carro', 'cama']):
        _icon(dr, kind, W * 0.08 + k * (W * 0.84 - s) / 3, top_h * 0.42, s)
    if plate:
        py = top_h + H * 0.04
        dr.rounded_rectangle([0, py, W, H], radius=int(H * 0.03), fill=WHT + (255,))
        dr.rounded_rectangle([m, py + m, W - m, H - m], radius=int(H * 0.025), fill=BLU + (255,))
        dr.text((W / 2, (py + H) / 2), 'REST AREA', font=_font(int((H - py) * 0.62)), fill=WHT + (255,), anchor='mm')
    img.save(path)

def half(src, dst, which):
    im = Image.open(src); W, H = im.size
    (im.crop((0, 0, W // 2, H)) if which == 'esq' else im.crop((W // 2, 0, W, H))).save(dst)
