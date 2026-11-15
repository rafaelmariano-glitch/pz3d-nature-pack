"""Logo, capa da Workshop, poster do jogo e banner do README.

    python generator/branding.py <pasta_dos_recortes> <pasta_de_saida>

Os recortes sao os modelos do pack renderizados com fundo transparente
(make_pack.py com PREVIEW_SPRITES e PREVIEW_FLOOR=0); o build.py gera tudo sozinho.
"""
import os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = 'C:/Windows/Fonts/'
INK = (240, 238, 222)
LEAF = (126, 196, 92)
NIGHT_TOP, NIGHT_BOT = (16, 34, 26), (40, 70, 44)


def font(name, size):
    for n in (name, 'segoeuib.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(FONTS + n if os.path.exists(FONTS + n) else n, size)
        except OSError:
            pass
    return ImageFont.load_default()


def sprite(d, name, height):
    im = Image.open(os.path.join(d, name + '.png')).convert('RGBA')
    im = im.crop(im.getbbox())
    return im.resize((max(1, round(im.width * height / im.height)), height), Image.LANCZOS)


def gradient(w, h, top=NIGHT_TOP, bot=NIGHT_BOT, glow=True):
    t = np.linspace(0, 1, h)[:, None, None]
    img = np.array(top, float) * (1 - t) + np.array(bot, float) * t
    img = np.broadcast_to(img, (h, w, 3)).copy()
    if glow:   # luz suave atras do diorama
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot((xx - w * 0.5) / (w * 0.55), (yy - h * 0.42) / (h * 0.5))
        img += np.clip(1 - r, 0, 1)[..., None] ** 2 * np.array([60, 80, 40])
    rnd = np.random.default_rng(3)
    img += rnd.normal(0, 2.0, img.shape)        # grao leve, evita faixas no degrade
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')


def shadow(canvas, cx, cy, w, h, alpha=110):
    sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=(0, 0, 0, alpha))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(2, h / 3))))


def iso_block(size, depth):
    """bloco isometrico de grama e terra, como um tile do PZ visto de cima. size = largura."""
    W, H = size, size // 2
    im = Image.new('RGBA', (W, H + depth), (0, 0, 0, 0))
    rnd = random.Random(7)
    top = [(W / 2, 0), (W, H / 2), (W / 2, H), (0, H / 2)]
    left = [(0, H / 2), (W / 2, H), (W / 2, H + depth), (0, H / 2 + depth)]
    right = [(W / 2, H), (W, H / 2), (W, H / 2 + depth), (W / 2, H + depth)]
    for poly, base in ((left, (104, 72, 46)), (right, (78, 52, 34))):
        side = Image.new('RGBA', im.size, base + (255,)); sd = ImageDraw.Draw(side)
        for _ in range(int(size * 0.8)):      # pedrinhas e estratos de terra
            x, y = rnd.uniform(0, W), rnd.uniform(H * 0.4, H + depth)
            r = rnd.uniform(1, size / 90)
            k = rnd.uniform(0.7, 1.25)
            sd.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=tuple(min(255, int(c * k)) for c in base) + (255,))
        mask = Image.new('L', im.size, 0); ImageDraw.Draw(mask).polygon(poly, fill=255)
        im.paste(side, (0, 0), mask)
    # topo de grama com textura
    g = Image.new('RGBA', im.size, (82, 128, 56, 255)); gd = ImageDraw.Draw(g)
    for _ in range(int(size * 3)):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        c = rnd.choice([(70, 116, 48), (96, 146, 62), (110, 160, 70), (64, 104, 44), (120, 150, 72)])
        r = rnd.uniform(1, size / 70)
        gd.ellipse([x - r, y - r / 2, x + r, y + r / 2], fill=c + (255,))
    gmask = Image.new('L', im.size, 0); ImageDraw.Draw(gmask).polygon(top, fill=255)
    im.paste(g, (0, 0), gmask)
    fr = ImageDraw.Draw(im)
    for _ in range(int(size / 3)):            # grama caindo pela borda
        t = rnd.random()
        if rnd.random() < 0.5:
            x, y = t * W / 2, H / 2 + t * H / 2
        else:
            x, y = W / 2 + t * W / 2, H - t * H / 2
        fr.line([x, y - 1, x + rnd.uniform(-2, 2), y + rnd.uniform(2, size / 40)],
                fill=(70, 112, 48, 255), width=max(1, size // 160))
    fr.line([top[3], top[0], top[1]], fill=(150, 196, 104, 255), width=max(1, size // 200))
    return im


def diorama(spr, size):
    """bloco de grama com a vegetacao do pack em cima. Retorna RGBA quadrado."""
    S = size
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bw = int(S * 0.86); depth = int(S * 0.11)
    block = iso_block(bw, depth)
    bx, by = (S - bw) // 2, int(S * 0.52)
    shadow(im, S / 2, by + bw / 4 + depth + S * 0.02, bw * 0.95, S * 0.08, 120)
    im.alpha_composite(block, (bx, by))
    cx, cy = S / 2, by + bw / 4         # centro do topo do bloco

    def put(name, h, u, v, sh=0.5):
        # u, v em -1..1 nos eixos do tile (como x e y do jogo)
        s = sprite(spr, name, int(h * S))
        x = cx + (u - v) * bw / 4 * 0.9
        y = cy + (u + v) * bw / 8 * 0.9
        shadow(im, x, y, s.width * sh * 1.6, s.width * sh * 0.45, 90)
        im.alpha_composite(s, (int(x - s.width / 2), int(y - s.height)))

    # de tras para frente (menor u+v primeiro)
    put('muda_pinheiro', 0.50, -0.85, -0.85)
    put('muda_folhosa_vermelho_out', 0.44, 0.75, -0.75)
    put('muda_betula_ouro_out', 0.36, -0.95, 0.35)
    put('placa_curva_dir_py', 0.24, 0.95, -0.05, 0.25)
    put('sebe_bola', 0.17, -0.25, 0.05)
    put('arbusto_grande_verde', 0.20, 0.45, 0.45)
    put('grama_alta_verao', 0.14, -0.55, 0.85, 0.3)
    put('pedra_media_1', 0.09, 0.10, 0.90)
    put('samambaia_grande', 0.10, 0.85, 0.80)
    return im


def wordmark(width, sub=True):
    """etiqueta 'pz3d' + NATURE PACK. Retorna RGBA recortado."""
    W = width; H = int(width * 0.5)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fs = int(width * 0.2)
    while True:     # maior tamanho que cabe na largura
        big = font('seguibl.ttf', fs)
        b = d.textbbox((0, 0), 'NATURE PACK', font=big)
        if b[2] - b[0] <= W * 0.96 or fs < 8: break
        fs -= 2
    small = font('segoeuib.ttf', int(fs * 0.45))
    tb = d.textbbox((0, 0), 'pz3d', font=small)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    pad = width * 0.022
    x0 = (W - tw) / 2 - pad * 1.6
    d.rounded_rectangle([x0, 0, x0 + tw + pad * 3.2, th + pad * 2], radius=pad * 1.4, fill=LEAF + (255,))
    d.text((W / 2, (th + pad * 2) / 2), 'pz3d', font=small, fill=NIGHT_TOP, anchor='mm')
    ty = th + pad * 2 + width * 0.02
    d.text((W / 2 + width * 0.006, ty + width * 0.008), 'NATURE PACK', font=big, fill=(0, 0, 0, 140), anchor='ma')
    d.text((W / 2, ty), 'NATURE PACK', font=big, fill=INK + (255,), anchor='ma')
    ty += d.textbbox((0, 0), 'NATURE PACK', font=big)[3] + width * 0.02
    if sub:
        sf = font('segoeui.ttf', int(width * 0.05))
        d.text((W / 2, ty), '3D nature add-on for pz3d', font=sf, fill=(190, 214, 170, 255), anchor='ma')
    return im.crop(im.getbbox())


def cover(spr, size):
    im = gradient(size, size)
    dio = diorama(spr, int(size * 0.80))
    im.alpha_composite(dio, ((size - dio.width) // 2, int(-size * 0.04)))
    wm = wordmark(int(size * 0.88), sub=size >= 400)
    im.alpha_composite(wm, ((size - wm.width) // 2, size - wm.height - int(size * (0.05 if size >= 400 else 0.035))))
    return im.convert('RGB')


def logo(spr, size):
    """emblema com fundo transparente."""
    im = Image.new('RGBA', (size, int(size * 1.2)), (0, 0, 0, 0))
    dio = diorama(spr, size)
    im.alpha_composite(dio, (0, int(-size * 0.08)))
    wm = wordmark(int(size * 0.9), sub=False)
    ol = Image.new('RGBA', wm.size, NIGHT_TOP + (0,))           # contorno escuro: le em fundo claro
    ol.putalpha(wm.getchannel('A').filter(ImageFilter.MaxFilter(9)))
    p = ((size - wm.width) // 2, im.height - wm.height - 6)
    im.alpha_composite(ol, p); im.alpha_composite(wm, p)
    return im.crop(im.getbbox())


def banner(spr, w, h):
    im = gradient(w, h, glow=False)
    ground = h * 0.80
    g = Image.new('RGBA', (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.rectangle([0, ground, w, h], fill=(48, 82, 40, 255))
    rnd = random.Random(5)
    for _ in range(w * 2):
        x, y = rnd.uniform(0, w), rnd.uniform(ground, h)
        c = rnd.choice([(58, 96, 46), (66, 108, 50), (40, 70, 34)])
        gd.ellipse([x - 3, y - 1, x + 3, y + 1], fill=c + (255,))
    im.alpha_composite(g)
    row = [('muda_pinheiro', 0.74), ('arbusto_medio_outono', 0.22), ('muda_folhosa_olaia_flor', 0.66),
           ('placa_pare_px', 0.42), ('muda_folhosa_vermelho_out', 0.70), ('samambaia_grande', 0.16),
           ('muda_betula_ouro_out', 0.64), ('arbusto_grande_verde', 0.26), ('muda_pinheiro_neve', 0.62)]
    x0 = w * 0.40                       # titulo ocupa a esquerda
    k = 1.0
    while True:
        sprites = [sprite(spr, n, int(h * s * k)) for n, s in row]
        gap = (w - x0 - sum(s.width for s in sprites)) / (len(sprites) + 1)
        if gap >= -w * 0.012: break     # leve sobreposicao: parece mata
        k *= 0.93
    x = x0 + gap
    for s in sprites:
        base = ground + h * 0.06
        shadow(im, x + s.width / 2, base, s.width * 0.9, h * 0.04, 100)
        im.alpha_composite(s, (int(x), int(base - s.height)))
        x += s.width + gap
    wm = wordmark(int(w * 0.34))
    im.alpha_composite(wm, (int(x0 / 2 - wm.width / 2), int(ground / 2 - wm.height / 2)))
    return im.convert('RGB')


def main(spr, out):
    os.makedirs(out, exist_ok=True)
    logo(spr, 1024).save(os.path.join(out, 'logo.png'))
    cover(spr, 1024).save(os.path.join(out, 'cover.png'))
    cover(spr, 512).save(os.path.join(out, 'poster.png'))
    cover(spr, 256).save(os.path.join(out, 'preview.png'))    # Workshop do PZ: 256x256
    banner(spr, 1600, 500).save(os.path.join(out, 'banner.png'))
    print('branding:', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
