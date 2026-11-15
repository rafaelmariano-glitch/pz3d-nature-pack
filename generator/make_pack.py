"""pz3d Nature Pack - gerador.

Gera um pacote de modelos para o pz3d (Project Zomboid em 3D) que troca vegetacao, chao natural,
pedras, borda de agua e placas de transito planas por modelos 3D com textura.
Tudo e gerado por codigo: nao usa nenhum arquivo do jogo nem do pz3d.

Uso:  python make_pack.py <pasta_de_saida_do_mod> [previa.png]
Requer: Python 3.10+, Pillow, numpy.
Escala do pz3d: 1 unidade = 1 tile, origem no canto do tile, Z para cima.
"""
import json, math, os, random, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foliage
import signs

OUT = sys.argv[1]
PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
ASSETS = os.path.join(OUT, 'common', 'media', 'pz3d', 'assets')

# ---------------- paletas (escuro, medio, claro) ----------------
PAL = {
    'verde_escuro': [(0.09, 0.20, 0.10), (0.13, 0.27, 0.13), (0.18, 0.34, 0.16)],
    'verde':        [(0.14, 0.28, 0.10), (0.20, 0.37, 0.13), (0.28, 0.46, 0.17)],
    'verde_claro':  [(0.24, 0.40, 0.15), (0.33, 0.50, 0.20), (0.43, 0.60, 0.26)],
    'oliva':        [(0.22, 0.25, 0.07), (0.31, 0.34, 0.10), (0.40, 0.42, 0.14)],
    'amarelo':      [(0.40, 0.42, 0.10), (0.56, 0.56, 0.16), (0.70, 0.68, 0.26)],
    'roxo':         [(0.22, 0.14, 0.22), (0.32, 0.21, 0.32), (0.45, 0.32, 0.45)],
    'outono':       [(0.28, 0.17, 0.06), (0.40, 0.25, 0.08), (0.52, 0.34, 0.12)],
    'sebe':         [(0.10, 0.21, 0.08), (0.14, 0.28, 0.10), (0.19, 0.35, 0.13)],
}
SNOW = (0.86, 0.89, 0.92)

# ---------------- geometria basica ----------------
def norm(p):
    l = math.sqrt(sum(x * x for x in p)) or 1
    return tuple(x / l for x in p)

def icosphere(sub):
    t = (1 + 5 ** 0.5) / 2
    v = [norm(p) for p in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t),
                           (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    for _ in range(sub):
        cache, nf = {}, []
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                pa, pb = v[a], v[b]
                v.append(norm(tuple((pa[i] + pb[i]) / 2 for i in range(3))))
                cache[k] = len(v) - 1
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return v, f

class Mesh:
    def __init__(self):
        self.v, self.f = [], []   # f: (a, b, c, material)
        self.cards = []           # (quad, uvs, normal, material): folhas texturizadas
        self.ttris = []           # (p0, p1, p2, uv0, uv1, uv2, material): superficie texturizada (pedras)

    def blob(self, c, r, mat, sub=2, rough=0.25, floor=0.0):
        v, f = icosphere(sub)
        base = len(self.v)
        for p in v:
            k = 1 + random.uniform(-rough, rough)
            z = c[2] + p[2] * r[2] * k
            self.v.append((c[0] + p[0] * r[0] * k, c[1] + p[1] * r[1] * k, max(z, floor)))
        self.f += [(base + a, base + b, base + c_, mat) for a, b, c_ in f]

    def box(self, x0, y0, z0, x1, y1, z1, mat, top_mat=None, div=6, rough=0.035):
        """caixa subdividida com superficie irregular (folhagem podada)."""
        def face(origin, du, dv, n, m):
            base = len(self.v)
            for i in range(div + 1):
                for j in range(div + 1):
                    p = [origin[k] + du[k] * i / div + dv[k] * j / div for k in range(3)]
                    edge = i in (0, div) or j in (0, div)
                    d = 0 if edge else random.uniform(-rough, rough)
                    self.v.append(tuple(p[k] + n[k] * d for k in range(3)))
            for i in range(div):
                for j in range(div):
                    a = base + i * (div + 1) + j
                    b, c, d = a + div + 1, a + div + 2, a + 1
                    cr = [du[1] * dv[2] - du[2] * dv[1], du[2] * dv[0] - du[0] * dv[2], du[0] * dv[1] - du[1] * dv[0]]
                    if sum(cr[k] * n[k] for k in range(3)) < 0:   # garante normal para fora
                        b, d = d, b
                    self.f += [(a, b, c, m), (a, c, d, m)]
        X, Y, Z = x1 - x0, y1 - y0, z1 - z0
        face((x0, y0, z1), (X, 0, 0), (0, Y, 0), (0, 0, 1), top_mat or mat)          # topo
        face((x0, y0, z0), (0, 0, Z), (X, 0, 0), (0, -1, 0), mat)                     # sul
        face((x0, y1, z0), (X, 0, 0), (0, 0, Z), (0, 1, 0), mat)                      # norte
        face((x0, y0, z0), (0, Y, 0), (0, 0, Z), (-1, 0, 0), mat)                     # oeste
        face((x1, y0, z0), (0, 0, Z), (0, Y, 0), (1, 0, 0), mat)                      # leste

    def write(self, path, mats):
        d = os.path.dirname(path); os.makedirs(d, exist_ok=True)
        stem = os.path.splitext(os.path.basename(path))[0]
        with open(os.path.join(d, stem + '.mtl'), 'w', newline='\n') as m:
            for name, val in mats.items():
                if isinstance(val, tuple) and val and val[0] == 'img':
                    val[1](os.path.join(d, name + '.png'))
                    m.write(f'newmtl {name}\nKd 1 1 1\nmap_Kd {name}.png\nPr 0.6\nPm 0.1\nd 1\n\n')
                elif isinstance(val, tuple) and val and val[0] == 'tex':
                    _, kind, pal, sd = val
                    foliage.make_texture(os.path.join(d, name + '.png'), kind, pal, sd)
                    m.write(f'newmtl {name}\nKd 1 1 1\nmap_Kd {name}.png\nPr 0.95\nPm 0\nd 1\n\n')
                else:
                    kd = val
                    m.write(f'newmtl {name}\nKd {kd[0]:.3f} {kd[1]:.3f} {kd[2]:.3f}\nPr 0.9\nPm 0\nd 1\n\n')
        nv = nvt = nvn = 0
        with open(path, 'w', newline='\n') as o:
            o.write('# pz3d Nature Pack: metros, Z up, triangulado.\nmtllib ' + stem + '.mtl\n')
            for name in mats:
                o.write(f'usemtl {name}\n')
                for a, b, c, fm in self.f:
                    if fm != name: continue
                    pa, pb, pc = self.v[a], self.v[b], self.v[c]
                    n = face_normal(pa, pb, pc)
                    for q in (pa, pb, pc): o.write(f'v {q[0]:.4f} {q[1]:.4f} {q[2]:.4f}\n')
                    o.write(f'vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n'); nvn += 1
                    o.write(f'f {nv+1}//{nvn} {nv+2}//{nvn} {nv+3}//{nvn}\n'); nv += 3
                for t in self.ttris:
                    p0, p1, p2, u0, u1, u2, fm = t[:7]
                    if fm != name: continue
                    ns = t[7:10] if len(t) >= 10 else (face_normal(p0, p1, p2),) * 3
                    for q in (p0, p1, p2): o.write(f'v {q[0]:.4f} {q[1]:.4f} {q[2]:.4f}\n')
                    for u, v in (u0, u1, u2): o.write(f'vt {u:.4f} {v:.4f}\n')
                    for n in ns: o.write(f'vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n')
                    o.write(f'f {nv+1}/{nvt+1}/{nvn+1} {nv+2}/{nvt+2}/{nvn+2} {nv+3}/{nvt+3}/{nvn+3}\n')
                    nv += 3; nvt += 3; nvn += 3
                for quad, uvs, n, fm in self.cards:
                    if fm != name: continue
                    for q in quad: o.write(f'v {q[0]:.4f} {q[1]:.4f} {q[2]:.4f}\n')
                    for u, v in uvs: o.write(f'vt {u:.4f} {v:.4f}\n')
                    o.write(f'vn {n[0]:.4f} {n[1]:.4f} {n[2]:.4f}\n'); nvn += 1
                    a, b, c, d_ = [(nv + k + 1, nvt + k + 1) for k in range(4)]
                    for t in ((a, b, c), (a, c, d_), (a, c, b), (a, d_, c)):   # os dois lados
                        o.write('f ' + ' '.join(f'{x}/{y}/{nvn}' for x, y in t) + '\n')
                    nv += 4; nvt += 4
        return len(self.f) + 4 * len(self.cards) + len(self.ttris)

    def tris(self):
        out = []
        for a, b, c, fm in self.f:
            pa, pb, pc = self.v[a], self.v[b], self.v[c]
            out.append((pa, pb, pc, None, None, None, face_normal(pa, pb, pc), fm))
        for t in self.ttris:
            p0, p1, p2, u0, u1, u2, fm = t[:7]
            n = t[7] if len(t) >= 10 else face_normal(p0, p1, p2)
            out.append((p0, p1, p2, u0, u1, u2, n, fm))
        for quad, uvs, n, fm in self.cards:
            out.append((quad[0], quad[1], quad[2], uvs[0], uvs[1], uvs[2], n, fm))
            out.append((quad[0], quad[2], quad[3], uvs[0], uvs[2], uvs[3], n, fm))
        return out

def face_normal(pa, pb, pc):
    u = [pb[k] - pa[k] for k in range(3)]; w = [pc[k] - pa[k] for k in range(3)]
    return norm((u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]))

# ---------------- modelos ----------------
def bush(size, seed):
    """moita arredondada: miolo escuro + cartoes de folha recortada por fora."""
    random.seed(seed); rnd = random.Random(seed); m = Mesh()
    h = size * 1.5
    m.blob((0.5, 0.5, h * 0.40), (size * 0.66, size * 0.66, h * 0.40), 'c0', sub=1, rough=0.2)
    def add(c, r, n, sz):
        foliage.add_cards(m, c, r, n, sz, 'folhas', rnd, floor=0.0, normal_center=(0.5, 0.5, h * 0.25))
    add((0.5, 0.5, h * 0.48), (size * 0.92, size * 0.92, h * 0.52), int(78 * size / 0.42), size * 0.62)
    add((0.5, 0.5, h * 0.20), (size * 0.95, size * 0.95, h * 0.22), int(22 * size / 0.42), size * 0.5)
    return m

def _surface_cards(m, rnd, x0, y0, x1, y1, height, n, size, mat, top=True):
    """cartoes de folha cobrindo as faces de uma caixa (sebe podada)."""
    faces = [((0, -1, 0), lambda: (rnd.uniform(x0, x1), y0, rnd.uniform(0.05, height))),
             ((0, 1, 0), lambda: (rnd.uniform(x0, x1), y1, rnd.uniform(0.05, height))),
             ((-1, 0, 0), lambda: (x0, rnd.uniform(y0, y1), rnd.uniform(0.05, height))),
             ((1, 0, 0), lambda: (x1, rnd.uniform(y0, y1), rnd.uniform(0.05, height)))]
    if top: faces.append(((0, 0, 1), lambda: (rnd.uniform(x0, x1), rnd.uniform(y0, y1), height)))
    for i in range(n):
        nrm, pick = faces[i % len(faces)]
        q = pick()
        c = tuple(q[k] + nrm[k] * rnd.uniform(-0.01, 0.04) for k in range(3))
        foliage.add_cards(m, c, (0.001, 0.001, 0.001), 1, size, mat, rnd,
                          normal_center=tuple(c[k] - nrm[k] for k in range(3)))

def hedge(height, snow, seed):
    random.seed(seed); rnd = random.Random(seed); m = Mesh()
    m.box(0.07, 0.07, 0.0, 0.93, 0.93, height - 0.04, 'c0', top_mat='neve' if snow else 'c0', div=3, rough=0.0)
    _surface_cards(m, rnd, 0.05, 0.05, 0.95, 0.95, height, int(420 * height / 1.45) + 90, 0.26, 'folhas',
                   top=not snow)
    return m

def topiary_cone(snow, seed):
    random.seed(seed); rnd = random.Random(seed); m = Mesh()
    for i, (z, r) in enumerate([(0.18, 0.22), (0.42, 0.19), (0.66, 0.15), (0.88, 0.11), (1.06, 0.07)]):
        m.blob((0.5, 0.5, z), (r, r, 0.15), 'c0', sub=1, rough=0.1)
        foliage.add_cards(m, (0.5, 0.5, z), (r + 0.05, r + 0.05, 0.16), 46 - i * 7, 0.18, 'folhas', rnd,
                          shell=(0.85, 1.05), normal_center=(0.5, 0.5, z - 0.05))
    if snow: m.blob((0.5, 0.5, 1.18), (0.06, 0.06, 0.05), 'neve', sub=1, rough=0.1)
    return m

def topiary_ball(snow, seed):
    random.seed(seed); rnd = random.Random(seed); m = Mesh()
    m.blob((0.5, 0.5, 0.33), (0.30, 0.30, 0.30), 'c0', sub=2, rough=0.04, floor=0.0)
    foliage.add_cards(m, (0.5, 0.5, 0.34), (0.34, 0.34, 0.34), 190, 0.17, 'folhas', rnd, shell=(0.9, 1.02))
    if snow: m.blob((0.5, 0.5, 0.56), (0.24, 0.24, 0.12), 'neve', sub=2, rough=0.06)
    return m

# ---------------- catalogo: modelo -> tiles ----------------
# arbustos inteiros (os galhos 0-31 e as camadas soltas de folha/flor ficam de fora)
BIG = {96: 'amarelo', 97: 'roxo', 98: 'roxo', 99: 'verde_claro', 100: 'verde_escuro', 101: 'verde', 102: 'verde',
       103: 'oliva', 104: 'verde', 105: 'verde_claro', 106: 'verde_escuro', 107: 'verde_claro', 108: 'verde_claro',
       109: 'verde_escuro', 110: 'verde_escuro', 111: 'verde'}
SMALL = {64: 'amarelo', 65: 'roxo', 66: 'roxo', 67: 'verde', 68: 'verde_escuro', 69: 'verde_claro', 70: 'verde_claro',
         71: 'oliva', 72: 'verde', 73: 'verde', 74: 'verde_escuro', 75: 'verde_claro', 76: 'verde_claro',
         77: 'verde_escuro', 78: 'verde_escuro', 79: 'verde'}
FOLIAGE = {0: ('outono', 'm'), 1: ('roxo', 'm'), 2: ('verde', 'm'), 3: ('oliva', 'm'), 4: ('verde', 'm'),
           5: ('outono', 'm'), 8: ('verde_claro', 'g'), 9: ('verde_claro', 'm'), 10: ('verde_escuro', 'm'),
           11: ('amarelo', 'p'), 12: ('verde', 'm'), 13: ('outono', 'm'), 14: ('oliva', 'm')}
# sebes: altas, baixas, cone, bola. f_bushes_2 10-23 sao as mesmas com neve.
HEDGE_KIND = {0: 'alta', 1: 'alta', 2: 'alta', 3: 'alta', 4: 'baixa', 5: 'baixa', 6: 'baixa', 7: 'baixa',
              8: 'cone', 9: 'bola', 10: 'alta', 11: 'alta', 12: 'baixa', 13: 'baixa'}

SIZES = {'g': 0.42, 'm': 0.35, 'p': 0.26}
def seed_of(t): return sum(ord(c) * (i + 1) for i, c in enumerate(t))
variants = {}   # nome -> (Mesh, mats, [tiles])

def want(name, builder, mats, tile):
    if name not in variants:
        variants[name] = (builder(), mats, [])
    variants[name][2].append(tile)

def bush_mats(pal):
    return {'c0': tuple(v * 0.7 for v in PAL[pal][0]), 'folhas': ('tex', 'larga', tuple(PAL[pal]), seed_of(pal))}

for idx, pal in BIG.items():
    want(f'arbusto_grande_{pal}', lambda pal=pal: bush(SIZES['g'], seed_of(pal)), bush_mats(pal), f'f_bushes_1_{idx}')
for idx, pal in SMALL.items():
    want(f'arbusto_pequeno_{pal}', lambda pal=pal: bush(SIZES['p'], seed_of(pal) + 7), bush_mats(pal), f'f_bushes_1_{idx}')
for idx, (pal, sz) in FOLIAGE.items():
    nome = {'g': 'grande', 'm': 'medio', 'p': 'pequeno'}[sz]
    want(f'arbusto_{nome}_{pal}', lambda pal=pal, sz=sz: bush(SIZES[sz], seed_of(pal + sz) + 3), bush_mats(pal),
         f'vegetation_foliage_01_{idx}')

def hedge_variant(kind, snow):
    sm = {'c0': tuple(v * 0.7 for v in PAL['sebe'][0]), 'folhas': ('tex', 'miuda', tuple(PAL['sebe']), 7)}
    if snow: sm['neve'] = SNOW
    build = {'alta': lambda: hedge(1.45, snow, 11), 'baixa': lambda: hedge(0.85, snow, 12),
             'cone': lambda: topiary_cone(snow, 13), 'bola': lambda: topiary_ball(snow, 14)}[kind]
    return f'sebe_{kind}' + ('_neve' if snow else ''), build, sm

for idx, kind in HEDGE_KIND.items():
    name, build, sm = hedge_variant(kind, False)
    want(name, build, sm, f'vegetation_ornamental_01_{idx}')
for idx in range(24):                       # f_bushes_2: 0-9 normais, 10-23 com neve
    kind = {0: 'alta', 1: 'alta', 2: 'alta', 3: 'alta', 4: 'baixa', 5: 'baixa', 6: 'baixa', 7: 'baixa', 8: 'cone',
            9: 'bola'}.get(idx if idx < 10 else (idx - 10 if idx < 20 else None),
                           'alta' if idx in (20, 21) else 'baixa')
    name, build, sm = hedge_variant(kind, idx >= 10)
    want(name, build, sm, f'f_bushes_2_{idx}')

# ================= vegetacao da mata (v0.3) =================
def add_vert(m, p):
    m.v.append(p); return len(m.v) - 1

def tri2(m, a, b, c, mat):
    """triangulo dos dois lados (laminas finas: grama, folhas)."""
    m.f.append((a, b, c, mat)); m.f.append((a, c, b, mat))

def blade(m, x, y, h, w, lean, ang, mat_base, mat_tip, segs=2):
    """lamina de grama afinando ate a ponta, curvando para fora."""
    dx, dy = math.cos(ang), math.sin(ang)          # direcao para onde a lamina tomba
    px, py = -dy, dx                                # largura perpendicular
    prev = None
    for s in range(segs + 1):
        t = s / segs
        bend = lean * t * t
        cx, cy, cz = x + dx * bend, y + dy * bend, h * t * (1 - 0.25 * lean * t)
        half = w * (1 - t) * 0.5
        if s < segs:
            l = add_vert(m, (cx - px * half, cy - py * half, cz)); r = add_vert(m, (cx + px * half, cy + py * half, cz))
            if prev:
                mat = mat_base if s <= segs // 2 else mat_tip
                tri2(m, prev[0], prev[1], r, mat); tri2(m, prev[0], r, l, mat)
            prev = (l, r)
        else:
            tip = add_vert(m, (cx, cy, cz))
            tri2(m, prev[0], prev[1], tip, mat_tip)

def quad(m, q, uvs, n, mat):
    m.cards.append(([tuple(x) for x in q], uvs, tuple(n), mat))

def blade_tex(m, x, y, h, w, lean, ang, mat='lamina', segs=3):
    """lamina de grama com textura: base escura, ponta clara. normal puxada para cima (luz macia)."""
    dx, dy = math.cos(ang), math.sin(ang); px, py = -dy, dx
    n = norm((dx * 0.35, dy * 0.35, 1.0))
    rows = []
    for s_ in range(segs + 1):
        t = s_ / segs
        bend = lean * t * t
        cx, cy, cz = x + dx * bend, y + dy * bend, h * t * (1 - 0.25 * lean * t)
        half = max(w * (1 - t) * 0.5, w * 0.03)
        rows.append(((cx - px * half, cy - py * half, cz), (cx + px * half, cy + py * half, cz), t))
    for k in range(segs):
        (l0, r0, t0), (l1, r1, t1) = rows[k], rows[k + 1]
        quad(m, [l0, r0, r1, l1], [(0, t0), (1, t0), (1, t1), (0, t1)], n, mat)

def grass(kind, seed):
    """kind: alta, media, rala."""
    random.seed(seed); m = Mesh()
    if kind == 'rala':
        clumps = [(random.uniform(0.15, 0.85), random.uniform(0.15, 0.85), 9) for _ in range(5)]
        H, W = 0.24, 0.024
    else:
        clumps = [(0.5 + random.uniform(-0.2, 0.2), 0.5 + random.uniform(-0.2, 0.2), 22 if kind == 'alta' else 18)
                  for _ in range(3)]
        H, W = (0.62, 0.03) if kind == 'alta' else (0.38, 0.026)
    for cx, cy, n in clumps:
        for _ in range(n):
            r = random.uniform(0, 0.16 if kind != 'rala' else 0.07)
            a = random.uniform(0, 2 * math.pi)
            blade_tex(m, cx + r * math.cos(a), cy + r * math.sin(a), H * random.uniform(0.6, 1.1), W * random.uniform(0.9, 1.4),
                      random.uniform(0.05, 0.22), a + random.uniform(-0.6, 0.6))
    return m

def leaf(m, base, ang, length, width, droop, mat, up=0.55):
    """folha saindo de base e caindo na ponta. mat 'folha' = quad com textura; senao losango colorido."""
    dx, dy = math.cos(ang), math.sin(ang); px, py = -dy, dx
    mid = (base[0] + dx * length * 0.45, base[1] + dy * length * 0.45, base[2] + length * up * 0.6)
    tipp = (base[0] + dx * length, base[1] + dy * length, base[2] + length * up * 0.6 - droop)
    if mat == 'folha':
        w = width * 1.7
        l = (mid[0] - px * w, mid[1] - py * w, mid[2]); r = (mid[0] + px * w, mid[1] + py * w, mid[2])
        n = face_normal(base, r, tipp)
        if n[2] < 0: n = tuple(-v for v in n)
        n = norm((n[0] * 0.6, n[1] * 0.6, n[2] + 0.4))
        quad(m, [base, r, tipp, l], [(0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5)], n, 'folha')
        return
    b = add_vert(m, base); tip = add_vert(m, tipp)
    l = add_vert(m, (mid[0] - px * width, mid[1] - py * width, mid[2]))
    r = add_vert(m, (mid[0] + px * width, mid[1] + py * width, mid[2]))
    tri2(m, b, r, tip, mat); tri2(m, b, tip, l, mat)

def fern(size, seed, n=9):
    """frondes arqueadas: cada uma e uma tira com a textura de fronde (foliolos recortados)."""
    random.seed(seed); m = Mesh()
    for i in range(n):
        a = 2 * math.pi * i / n + random.uniform(-0.2, 0.2)
        L = size * random.uniform(0.85, 1.15)
        dx, dy = math.cos(a), math.sin(a); px, py = -dy, dx
        roll = random.uniform(-0.25, 0.25)
        segs = 6
        rows = []
        for k in range(segs + 1):
            t = k / segs
            c = (0.5 + dx * L * t, 0.5 + dy * L * t, L * (0.95 * t - 0.8 * t * t) + 0.02)
            half = size * 0.30 * (1.0 - 0.55 * t) + 0.01
            side = (px * half, py * half, roll * half)
            rows.append(((c[0] - side[0], c[1] - side[1], c[2] - side[2]), (c[0] + side[0], c[1] + side[1], c[2] + side[2]), t))
        for k in range(segs):
            (l0, r0, t0), (l1, r1, t1) = rows[k], rows[k + 1]
            nn = norm((dx * 0.2, dy * 0.2, 1.0))
            quad(m, [l0, r0, r1, l1], [(0, t0), (1, t0), (1, t1), (0, t1)], nn, 'fronde')
    return m

def leafy_plant(kind, seed):
    """kind: folhosa (moitinha de folhas largas), alta (hastes), muda (brotinhos)."""
    random.seed(seed); m = Mesh()
    if kind == 'folhosa':
        for _ in range(26):
            a = random.uniform(0, 2 * math.pi); r = random.uniform(0, 0.12)
            base = (0.5 + r * math.cos(a), 0.5 + r * math.sin(a), random.uniform(0.0, 0.18))
            leaf(m, base, a + random.uniform(-0.4, 0.4), random.uniform(0.18, 0.28), random.uniform(0.05, 0.08),
                 random.uniform(0.04, 0.12), 'folha')
    elif kind == 'alta':
        for _ in range(7):
            x, y = 0.5 + random.uniform(-0.18, 0.18), 0.5 + random.uniform(-0.18, 0.18)
            h = random.uniform(0.45, 0.7)
            blade(m, x, y, h, 0.025, 0.04, random.uniform(0, 6.28), 'c0', 'c0', segs=2)
            for k in range(5):
                z = h * (0.3 + 0.13 * k)
                leaf(m, (x, y, z), random.uniform(0, 6.28), 0.11, 0.03, 0.04, 'folha', up=0.3)
    else:  # muda
        for _ in range(6):
            x, y = random.uniform(0.15, 0.85), random.uniform(0.15, 0.85)
            blade(m, x, y, 0.08, 0.012, 0.0, 0, 'c0', 'c0', segs=1)
            for k in range(3):
                leaf(m, (x, y, 0.07), random.uniform(0, 6.28), 0.07, 0.025, 0.02, 'folha', up=0.4)
    return m

def tube(m, p0, p1, r0, r1, mat, sides=4):
    d = norm(tuple(p1[k] - p0[k] for k in range(3)))
    ref = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
    u = norm((d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0]))
    w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
    ring0, ring1 = [], []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        o = tuple(u[k] * math.cos(a) + w[k] * math.sin(a) for k in range(3))
        ring0.append(add_vert(m, tuple(p0[k] + o[k] * r0 for k in range(3))))
        ring1.append(add_vert(m, tuple(p1[k] + o[k] * r1 for k in range(3))))
    for i in range(sides):
        j = (i + 1) % sides
        m.f.append((ring0[i], ring0[j], ring1[j], mat)); m.f.append((ring0[i], ring1[j], ring1[i], mat))

def branch_bush(size, leaves, snow, seed):
    """moita de galhos baixa e aberta: muitas hastes saindo do chao, folhas ao longo delas."""
    random.seed(seed); rnd = random.Random(seed); m = Mesh()
    nodes = []
    def grow(p, d, length, r, depth):
        q = tuple(p[k] + d[k] * length for k in range(3))
        tube(m, p, q, r, r * 0.7, 'galho', sides=3)
        nodes.append((q, depth))
        if depth == 0: return
        for _ in range(2):
            nd = norm((d[0] + random.uniform(-0.6, 0.6), d[1] + random.uniform(-0.6, 0.6), d[2] * 0.7 + random.uniform(0.0, 0.3)))
            grow(q, nd, length * random.uniform(0.6, 0.8), r * 0.7, depth - 1)
    n = 9
    for i in range(n):
        a = 2 * math.pi * i / n + random.uniform(-0.3, 0.3)
        lean = random.uniform(0.7, 1.1)                       # hastes bem inclinadas: abre para os lados
        d = norm((math.cos(a) * lean, math.sin(a) * lean, 1.0))
        grow((0.5 + random.uniform(-0.05, 0.05), 0.5 + random.uniform(-0.05, 0.05), 0.0), d,
             size * random.uniform(0.30, 0.40), 0.014, 2)
    for q, depth in nodes:
        if leaves:
            foliage.add_cards(m, q, (size * 0.10, size * 0.10, size * 0.08), 3 if depth == 0 else 2, size * 0.26,
                              'folhas', rnd, shell=(0.0, 1.0), normal_center=(0.5, 0.5, size * 0.15))
        elif snow and depth == 0 and random.random() < 0.5:
            m.blob((q[0], q[1], q[2]), (0.022, 0.022, 0.010), 'neve', sub=0, rough=0.2)
    if snow:
        m.blob((0.5, 0.5, 0.0), (size * 0.32, size * 0.32, 0.03), 'neve', sub=1, rough=0.15, floor=0.0)
    return m

# paletas da mata, por estacao (o jogo troca o tile conforme a epoca)
PAL.update({
    'grama_verao':     [(0.10, 0.20, 0.06), (0.17, 0.32, 0.09), (0.26, 0.42, 0.13)],
    'grama_viva':      [(0.13, 0.24, 0.07), (0.22, 0.38, 0.11), (0.33, 0.48, 0.16)],
    'grama_amarelada': [(0.22, 0.26, 0.08), (0.36, 0.40, 0.14), (0.50, 0.50, 0.22)],
    'grama_oliva':     [(0.20, 0.21, 0.07), (0.31, 0.31, 0.11), (0.42, 0.38, 0.16)],
    'grama_seca':      [(0.27, 0.20, 0.09), (0.42, 0.32, 0.15), (0.55, 0.44, 0.24)],
    'samambaia':       [(0.09, 0.20, 0.08), (0.14, 0.30, 0.11), (0.20, 0.39, 0.15)],
    'samambaia_neve':  [(0.12, 0.22, 0.12), (0.45, 0.55, 0.50), (0.85, 0.88, 0.90)],
    'folhosa':         [(0.12, 0.24, 0.12), (0.18, 0.33, 0.15), (0.26, 0.42, 0.20)],
    'folhosa_clara':   [(0.20, 0.33, 0.17), (0.28, 0.43, 0.22), (0.37, 0.52, 0.28)],
    'muda':            [(0.20, 0.28, 0.14), (0.28, 0.45, 0.32), (0.36, 0.55, 0.40)],
    'muda_seca':       [(0.25, 0.18, 0.10), (0.38, 0.27, 0.15), (0.48, 0.36, 0.20)],
})
def mats3(pal, extra=None):
    d = {'c0': PAL[pal][0], 'c1': PAL[pal][1], 'c2': PAL[pal][2]}
    if extra: d.update(extra)
    return d

# grama e_newgrass_1: 5 estacoes de 24 tiles; dentro de cada uma +0..5 alta, +8..13 media, +16..21 rala
for k, pal in enumerate(['grama_verao', 'grama_viva', 'grama_amarelada', 'grama_oliva', 'grama_seca']):
    for off, kind in [(0, 'alta'), (8, 'media'), (16, 'rala')]:
        for i in range(6):
            want(f'grama_{kind}_{pal[6:]}', lambda kind=kind, pal=pal: grass(kind, seed_of(kind + pal)),
                 mats3(pal, {'lamina': ('tex', 'lamina', tuple(PAL[pal]), seed_of(pal))}), f'e_newgrass_1_{24 * k + off + i}')

# samambaias d_generic_1
for i in (48, 49, 51, 54, 80, 81, 86, 87):
    want('samambaia_grande', lambda: fern(0.42, 21), mats3('samambaia', {'fronde': ('tex', 'fronde', tuple(PAL['samambaia']), 21)}), f'd_generic_1_{i}')
for i in (50, 52, 53, 55, 82, 83, 84, 85):
    want('samambaia_pequena', lambda: fern(0.28, 22, n=7), mats3('samambaia', {'fronde': ('tex', 'fronde', tuple(PAL['samambaia']), 22)}), f'd_generic_1_{i}')
for i in (64, 65, 67, 70, 96, 97, 98, 101, 102, 103):
    want('samambaia_grande_neve', lambda: fern(0.40, 23), mats3('samambaia_neve', {'fronde': ('tex', 'fronde_neve', tuple(PAL['samambaia']), 23)}), f'd_generic_1_{i}')
for i in (66, 68, 69, 71, 99, 100):
    want('samambaia_pequena_neve', lambda: fern(0.27, 24, n=7), mats3('samambaia_neve', {'fronde': ('tex', 'fronde_neve', tuple(PAL['samambaia']), 24)}), f'd_generic_1_{i}')
# brotinhos de grama no chao da mata
for i in (3, 4, 5, 6, 7, 19, 20, 21, 32, 33, 34, 35, 36, 38, 39):
    want('broto', lambda: grass('rala', 31), mats3('grama_oliva', {'lamina': ('tex', 'lamina', tuple(PAL['grama_oliva']), 31)}), f'd_generic_1_{i}')

# plantas d_plants_1
for i in (16, 17, 20, 21, 22, 23, 37, 51, 53, 54):
    want('planta_folhosa', lambda: leafy_plant('folhosa', 41), mats3('folhosa', {'folha': ('tex', 'folha', tuple(PAL['folhosa']), 41)}), f'd_plants_1_{i}')
for i in (32, 33, 34, 35, 38, 39, 49, 50, 52, 55):
    want('planta_folhosa_clara', lambda: leafy_plant('folhosa', 42), mats3('folhosa_clara', {'folha': ('tex', 'folha', tuple(PAL['folhosa_clara']), 42)}), f'd_plants_1_{i}')
for i in (18, 19, 36, 64):
    want('planta_alta', lambda: leafy_plant('alta', 43), mats3('folhosa', {'folha': ('tex', 'folha', tuple(PAL['folhosa']), 43)}), f'd_plants_1_{i}')
for i in range(0, 8):
    want('muda', lambda: leafy_plant('muda', 44), mats3('muda', {'folha': ('tex', 'folha', tuple(PAL['muda']), 44)}), f'd_plants_1_{i}')
for i in range(8, 16):
    want('muda_seca', lambda: leafy_plant('muda', 45), mats3('muda_seca', {'folha': ('tex', 'folha', tuple(PAL['muda_seca']), 45)}), f'd_plants_1_{i}')

# moitas de galhos f_bushes_1: 0-7 pequenas, 8-15 grandes, 16-31 as mesmas com neve
GALHO = {'galho': (0.24, 0.17, 0.12)}
for i in range(0, 8):
    want('moita_galhos_pequena', lambda: branch_bush(0.60, True, False, 51), mats3('verde', {**GALHO, 'folhas': ('tex', 'larga', tuple(PAL['verde']), 51)}), f'f_bushes_1_{i}')
for i in range(8, 16):
    want('moita_galhos_grande', lambda: branch_bush(0.90, True, False, 52), mats3('verde', {**GALHO, 'folhas': ('tex', 'larga', tuple(PAL['verde']), 51)}), f'f_bushes_1_{i}')
for i in range(16, 24):
    want('moita_galhos_pequena_neve', lambda: branch_bush(0.60, False, True, 53), {**GALHO, 'neve': SNOW}, f'f_bushes_1_{i}')
for i in range(24, 32):
    want('moita_galhos_grande_neve', lambda: branch_bush(0.90, False, True, 54), {**GALHO, 'neve': SNOW}, f'f_bushes_1_{i}')

# ================= arvores jovens (v0.4) =================
# Cada folha e_<especie>_1 tem 4 tamanhos de crescimento por estacao:
#   folhosas: 0-3 peladas, 4-7 peladas com neve, 8-11 primavera, 12-15 verao, 16-19 outono, 20-23 fim do outono
#   pinheiros (azevinho, cicuta): 0-3 verdes, 4-7 com neve
# Um modelo por especie+estacao; o tamanho vem da escala de cada ligacao.
H_MUDA = 2.3          # altura do modelo no maior estagio (tiles)
STAGE_SCALE = [0.32, 0.52, 0.78, 1.0]
tile_scale = {}       # tile -> escala fixa (usada na gravacao das ligacoes)

def sapling(kind, leaves, snow, seed):
    """kind: folhosa ou betula. arvore jovem com tronco, galhos e copa."""
    random.seed(seed); m = Mesh()
    bark = 'casca_clara' if kind == 'betula' else 'casca'
    nodes = []
    trunk_h = H_MUDA * (0.42 if kind == 'folhosa' else 0.5)
    trunks = [(0.5, 0.5)] if kind == 'folhosa' else [(0.46, 0.48), (0.55, 0.53)]
    for tx, ty in trunks:
        lean = norm((random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), 1))
        top = (tx + lean[0] * trunk_h, ty + lean[1] * trunk_h, trunk_h)
        tube(m, (tx, ty, 0), top, 0.045, 0.03, bark, sides=5)
        def grow(p, d, length, r, depth):
            q = tuple(p[k] + d[k] * length for k in range(3))
            tube(m, p, q, r, r * 0.65, bark, sides=4 if depth > 1 else 3)
            nodes.append((q, depth))
            if depth == 0: return
            for _ in range(2 if depth > 1 else 3):
                spread = 0.55 if kind == 'folhosa' else 0.35
                nd = norm((d[0] + random.uniform(-spread, spread), d[1] + random.uniform(-spread, spread),
                           d[2] + random.uniform(0.2, 0.6)))
                grow(q, nd, length * random.uniform(0.6, 0.75), r * 0.65, depth - 1)
        for i in range(4):
            a = 2 * math.pi * i / 4 + random.uniform(-0.4, 0.4)
            out = 0.8 if kind == 'folhosa' else 0.45
            d = norm((math.cos(a) * out, math.sin(a) * out, 1.0))
            start = tuple(top[k] - (0, 0, random.uniform(0, 0.25))[k] for k in range(3))
            grow(start, d, H_MUDA * 0.24, 0.024, 2)
        # ponteiro central
        grow(top, (0, 0, 1), H_MUDA * 0.2, 0.022, 1)
    if leaves:
        rnd = random.Random(seed)
        zc = H_MUDA * 0.68
        for q, depth in nodes:
            if depth > 1: continue
            foliage.add_cards(m, q, (H_MUDA * 0.10,) * 3, 6 if depth == 0 else 3,
                              H_MUDA * (0.15 if kind == 'folhosa' else 0.12), 'folhas', rnd, shell=(0.0, 1.0),
                              normal_center=(0.5, 0.5, zc))
    elif snow:
        for q, depth in nodes:
            if depth == 0 and random.random() < 0.6:
                m.blob(q, (0.03, 0.03, 0.014), 'neve', sub=0, rough=0.2)
        m.blob((0.5, 0.5, 0.0), (0.28, 0.28, 0.025), 'neve', sub=1, rough=0.15, floor=0.0)
    return m

def conifer(snow, seed):
    """pinheiro jovem: tronco e camadas densas de raminhos de agulha, caindo levemente para fora."""
    random.seed(seed); rnd = random.Random(seed); m = Mesh()
    tube(m, (0.5, 0.5, 0), (0.5, 0.5, H_MUDA * 0.97), 0.045, 0.012, 'casca', sides=5)
    layers = 11
    for i in range(layers):
        t = i / (layers - 1)
        z = H_MUDA * (0.08 + 0.86 * t)
        r = 0.50 * (1 - t) ** 1.1 + 0.05
        # anel externo (silhueta) e anel interno (tapa o vazio perto do tronco)
        foliage.add_cards(m, (0.5, 0.5, z), (r, r, H_MUDA * 0.05), int(40 * (1 - t) + 10),
                          0.34 * (1 - t) + 0.13, 'ramo', rnd, shell=(0.55, 1.0),
                          normal_center=(0.5, 0.5, z - H_MUDA * 0.25))
        foliage.add_cards(m, (0.5, 0.5, z + H_MUDA * 0.02), (r * 0.45, r * 0.45, H_MUDA * 0.05), int(14 * (1 - t) + 4),
                          0.26 * (1 - t) + 0.10, 'ramo', rnd, shell=(0.0, 1.0),
                          normal_center=(0.5, 0.5, z - H_MUDA * 0.25))
    return m

PAL.update({
    'casca_pal': None,
    # primavera
    'silverbell_flor': [(0.70, 0.72, 0.68), (0.84, 0.86, 0.82), (0.94, 0.95, 0.92)],
    'espinheiro_flor': [(0.66, 0.66, 0.52), (0.80, 0.80, 0.66), (0.90, 0.90, 0.78)],
    'corniso_flor':    [(0.45, 0.20, 0.35), (0.60, 0.28, 0.46), (0.72, 0.40, 0.58)],
    'olaia_flor':      [(0.52, 0.26, 0.45), (0.66, 0.36, 0.58), (0.78, 0.50, 0.70)],
    'bordo_broto':     [(0.32, 0.38, 0.12), (0.44, 0.50, 0.18), (0.56, 0.60, 0.26)],
    'betula_broto':    [(0.30, 0.42, 0.16), (0.42, 0.54, 0.22), (0.54, 0.64, 0.30)],
    # verao
    'folha_verao':     [(0.14, 0.28, 0.12), (0.21, 0.38, 0.16), (0.30, 0.48, 0.21)],
    'folha_verao_cl':  [(0.22, 0.36, 0.14), (0.31, 0.46, 0.19), (0.41, 0.56, 0.25)],
    # outono
    'amarelo_out':     [(0.50, 0.38, 0.08), (0.66, 0.52, 0.12), (0.80, 0.66, 0.20)],
    'laranja_out':     [(0.50, 0.20, 0.07), (0.66, 0.30, 0.10), (0.78, 0.42, 0.16)],
    'vermelho_out':    [(0.42, 0.08, 0.06), (0.58, 0.12, 0.09), (0.70, 0.20, 0.14)],
    'ferrugem_out':    [(0.38, 0.17, 0.08), (0.52, 0.25, 0.11), (0.64, 0.35, 0.16)],
    'salmao_out':      [(0.48, 0.26, 0.16), (0.62, 0.36, 0.22), (0.74, 0.47, 0.30)],
    'ouro_out':        [(0.48, 0.40, 0.14), (0.62, 0.52, 0.20), (0.74, 0.64, 0.28)],
    'pinheiro':        [(0.06, 0.16, 0.09), (0.09, 0.22, 0.12), (0.13, 0.29, 0.15)],
})
del PAL['casca_pal']
CASCA = {'casca': (0.22, 0.16, 0.12), 'casca_clara': (0.80, 0.78, 0.72)}

SPECIES = {   # especie: (forma, primavera, verao, outono, fim do outono)
    'carolinasilverbell': ('folhosa', 'silverbell_flor', 'folha_verao_cl', 'amarelo_out', 'salmao_out'),
    'cockspurhawthorn':   ('folhosa', 'espinheiro_flor', 'folha_verao', 'laranja_out', 'ferrugem_out'),
    'dogwood':            ('folhosa', 'corniso_flor', 'folha_verao', 'amarelo_out', 'ferrugem_out'),
    'easternredbud':      ('folhosa', 'olaia_flor', 'folha_verao_cl', 'amarelo_out', 'salmao_out'),
    'redmaple':           ('folhosa', 'bordo_broto', 'folha_verao', 'vermelho_out', 'vermelho_out'),
    'riverbirch':         ('betula', 'betula_broto', 'folha_verao_cl', 'ouro_out', 'amarelo_out'),
    'yellowwood':         ('folhosa', 'silverbell_flor', 'folha_verao', 'amarelo_out', 'ouro_out'),
}

def want_scaled(name, builder, mats, tile, scale):
    want(name, builder, mats, tile)
    tile_scale[tile] = scale

for sp, (shape, spring, summer, aut1, aut2) in SPECIES.items():
    sd = seed_of(sp)
    bare = 'muda_betula' if shape == 'betula' else 'muda_folhosa'
    for st in range(4):
        sc = STAGE_SCALE[st]
        want_scaled(f'{bare}_pelada', lambda shape=shape: sapling(shape, False, False, 61 + (shape == 'betula')),
                    {**CASCA}, f'e_{sp}_1_{st}', sc)
        want_scaled(f'{bare}_pelada_neve', lambda shape=shape: sapling(shape, False, True, 63 + (shape == 'betula')),
                    {**CASCA, 'neve': SNOW}, f'e_{sp}_1_{4 + st}', sc)
        for off, pal in ((8, spring), (12, summer), (16, aut1), (20, aut2)):
            want_scaled(f'{bare}_{pal}', lambda shape=shape, pal=pal, sd=sd: sapling(shape, True, False, 70 + (shape == 'betula')),
                        mats3(pal, {**CASCA, 'folhas': ('tex', 'miuda' if shape == 'betula' else 'larga', tuple(PAL[pal]), seed_of(pal))}), f'e_{sp}_1_{off + st}', sc)
for sp in ('americanholly', 'canadianhemlock'):
    for st in range(4):
        sc = STAGE_SCALE[st]
        want_scaled('muda_pinheiro', lambda: conifer(False, 81), mats3('pinheiro', {**CASCA, 'ramo': ('tex', 'ramo', tuple(PAL['pinheiro']), 81)}), f'e_{sp}_1_{st}', sc)
        want_scaled('muda_pinheiro_neve', lambda: conifer(True, 82), mats3('pinheiro', {**CASCA, 'neve': SNOW, 'ramo': ('tex', 'ramo_neve', tuple(PAL['pinheiro']), 82)}),
                    f'e_{sp}_1_{4 + st}', sc)

# ================= v0.5: ervas secas, gravetos, folha larga =================
def dry_weed(seed, n=5):
    """erva seca: hastes finas marrons com folhinhas secas viradas para baixo."""
    random.seed(seed); m = Mesh()
    for _ in range(n):
        x, y = 0.5 + random.uniform(-0.25, 0.25), 0.5 + random.uniform(-0.25, 0.25)
        h = random.uniform(0.12, 0.26)
        ang = random.uniform(0, 6.28)
        blade(m, x, y, h, 0.014, 0.03, ang, 'c0', 'c1', segs=2)
        for k in range(3):
            leaf(m, (x, y, h * (0.35 + 0.25 * k)), random.uniform(0, 6.28), 0.06, 0.018, 0.035, 'folha', up=0.15)
    return m

def dry_twigs(seed):
    """gravetos secos em pe: 2-3 varetas ramificadas."""
    random.seed(seed); m = Mesh()
    def grow(p, d, length, r, depth):
        q = tuple(p[k] + d[k] * length for k in range(3))
        tube(m, p, q, r, r * 0.6, 'c0', sides=3)
        if depth == 0: return
        for _ in range(2):
            nd = norm((d[0] + random.uniform(-0.8, 0.8), d[1] + random.uniform(-0.8, 0.8), d[2] + 0.3))
            grow(q, nd, length * 0.6, r * 0.6, depth - 1)
    for _ in range(3):
        x, y = 0.5 + random.uniform(-0.2, 0.2), 0.5 + random.uniform(-0.2, 0.2)
        grow((x, y, 0), norm((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 1)), random.uniform(0.18, 0.3), 0.012, 2)
    return m

def broadleaf(seed):
    """planta de folhas largas compridas saindo do centro (tipo inhame)."""
    random.seed(seed); m = Mesh()
    for i in range(7):
        a = 2 * math.pi * i / 7 + random.uniform(-0.3, 0.3)
        h = random.uniform(0.25, 0.45)
        x, y = 0.5 + math.cos(a) * 0.05, 0.5 + math.sin(a) * 0.05
        blade(m, x, y, h, 0.02, 0.12, a, 'c0', 'c0', segs=2)        # talo
        top = (x + math.cos(a) * 0.12, y + math.sin(a) * 0.12, h * 0.95)
        leaf(m, top, a, random.uniform(0.28, 0.36), random.uniform(0.09, 0.12), 0.12, 'folha', up=0.2)
    return m

PAL.update({
    'erva_seca':  [(0.24, 0.16, 0.09), (0.36, 0.25, 0.13), (0.46, 0.34, 0.19)],
    'graveto':    [(0.20, 0.15, 0.11), (0.28, 0.21, 0.15), (0.34, 0.26, 0.19)],
})
for i in (0, 1, 2, 9, 26, 27, 29, 30, 37, 41, 42, 46):
    want('erva_seca', lambda: dry_weed(91), mats3('erva_seca', {'folha': ('tex', 'folha', tuple(PAL['erva_seca']), 91)}), f'd_generic_1_{i}')
for i in (16, 17, 18):
    want('gravetos', lambda: dry_twigs(92), mats3('graveto'), f'd_generic_1_{i}')
want('planta_folha_larga', lambda: broadleaf(93), mats3('folhosa', {'folha': ('tex', 'folha', tuple(PAL['folhosa']), 93)}), 'd_plants_1_48')

# ================= v0.7: borda de agua deitada no chao =================
# blends_natural_02 fica na camada de objetos, entao o pz3d o desenhava em pe.
# Cada tile vira uma peca plana com textura de agua, no formato do desenho original.
AGUA_Z = 0.008
def flat_water(poly):
    m = Mesh()
    pts = [(x, y, AGUA_Z) for x, y in poly]
    if len(pts) == 3:                                # triangulo vira quad pelo meio da hipotenusa (sem face degenerada)
        a_, b_, c_ = pts
        pts = [a_, b_, tuple((b_[k] + c_[k]) / 2 for k in range(3)), c_]
    uvs = [(x, y) for x, y, _ in pts]
    m.cards.append((pts, uvs, (0.0, 0.0, 1.0), 'agua'))
    return m

E = 0.14   # largura das faixas de borda
WATER_SHAPES = {
    1: ('agua_canto_norte', [(0, 0), (1, 0), (0, 1)]),
    2: ('agua_canto_sul',   [(1, 0), (1, 1), (0, 1)]),
    3: ('agua_canto_oeste', [(0, 0), (1, 1), (0, 1)]),
    4: ('agua_canto_leste', [(0, 0), (1, 0), (1, 1)]),
}
STRIPS = {  # faixas finas: ao longo de cada borda do tile
    'agua_faixa_y0': [(0, 0), (1, 0), (1, E), (0, E)],
    'agua_faixa_x0': [(0, 0), (E, 0), (E, 1), (0, 1)],
    'agua_faixa_x1': [(1 - E, 0), (1, 0), (1, 1), (1 - E, 1)],
    'agua_faixa_y1': [(0, 1 - E), (1, 1 - E), (1, 1), (0, 1)],
}
STRIP_TILES = {8: 'agua_faixa_y0', 12: 'agua_faixa_y0', 9: 'agua_faixa_x0', 13: 'agua_faixa_x0',
               10: 'agua_faixa_x1', 14: 'agua_faixa_x1', 11: 'agua_faixa_y1', 15: 'agua_faixa_y1'}
AGUA_MATS = {'agua': ('tex', 'agua', ((62, 78, 84), (80, 96, 101), (101, 115, 118)), 5)}
for idx, (name, poly) in WATER_SHAPES.items():
    want(name, lambda poly=poly: flat_water(poly), AGUA_MATS, f'blends_natural_02_{idx}')
for idx, name in STRIP_TILES.items():
    want(name, lambda name=name: flat_water(STRIPS[name]), AGUA_MATS, f'blends_natural_02_{idx}')

# ================= v0.8: pedras 3D =================
def rock(m, c, r, seed, mat='rocha', sub=2, rough=0.22, flat=1.0, sink=0.12):
    """pedra: icosfera com planos de quebra, base pouco enterrada, normais suaves e textura por projecao."""
    rnd = random.Random(seed)
    v, f = icosphere(sub)
    cuts = [norm((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))) for _ in range(5)]
    pts = []
    for q in v:
        k = 1 + rnd.uniform(-rough, rough) * 0.35
        for cn in cuts:
            d = q[0] * cn[0] + q[1] * cn[1] + q[2] * cn[2]
            if d > 0.6: k *= 1 - (d - 0.6) * 0.7
        z = q[2] * r[2] * k * flat
        pts.append((c[0] + q[0] * r[0] * k, c[1] + q[1] * r[1] * k, max(c[2] + z - r[2] * sink, 0.0)))
    # normais por vertice: media das faces vizinhas (pedra arredondada, sem cara de bloco)
    acc = [[0.0, 0.0, 0.0] for _ in pts]
    for a, b, cc in f:
        n = face_normal(pts[a], pts[b], pts[cc])
        for i in (a, b, cc):
            for k in range(3): acc[i][k] += n[k]
    vn = [norm(tuple(a)) for a in acc]
    s_uv = 2.6
    for a, b, cc in f:
        tri = [pts[a], pts[b], pts[cc]]
        n = face_normal(*tri)
        ax = max(range(3), key=lambda i: abs(n[i]))
        uv = [((p[1], p[2]) if ax == 0 else (p[0], p[2]) if ax == 1 else (p[0], p[1])) for p in tri]
        uv = [(u * s_uv, w * s_uv) for u, w in uv]
        m.ttris.append((tri[0], tri[1], tri[2], uv[0], uv[1], uv[2], mat, vn[a], vn[b], vn[cc]))

def boulder(seed, size=0.30):
    m = Mesh(); rnd = random.Random(seed)
    rock(m, (0.5, 0.5, size * 0.6), (size, size * rnd.uniform(0.8, 1.0), size * 0.75), seed)
    if rnd.random() < 0.6:
        rock(m, (0.5 + size * 0.9, 0.5 + rnd.uniform(-0.2, 0.2), size * 0.3), (size * 0.4,) * 3, seed + 1, sub=1)
    return m

def slab(seed):
    """laje/lasca grande: alta e angulosa."""
    m = Mesh(); rnd = random.Random(seed)
    rock(m, (0.5, 0.5, 0.32), (0.34, 0.16, 0.42), seed, sub=1, rough=0.35, sink=0.1)
    rock(m, (0.62, 0.42, 0.12), (0.16, 0.14, 0.14), seed + 3, sub=1)
    return m

def pebbles(seed, n=3, big=0.10):
    m = Mesh(); rnd = random.Random(seed)
    for i in range(n):
        sz = big * rnd.uniform(0.5, 1.0)
        rock(m, (0.5 + rnd.uniform(-0.25, 0.25), 0.5 + rnd.uniform(-0.25, 0.25), sz * 0.4),
             (sz, sz * rnd.uniform(0.7, 1.0), sz * 0.7), seed + i, sub=2, sink=0.15)
    return m

def ground_stones(seed):
    """pedras rasas meio enterradas (no lugar das pedras desenhadas no chao)."""
    m = Mesh(); rnd = random.Random(seed)
    for i in range(rnd.randint(2, 4)):
        sz = rnd.uniform(0.10, 0.22)
        rock(m, (0.5 + rnd.uniform(-0.25, 0.25), 0.5 + rnd.uniform(-0.25, 0.25), sz * 0.3),
             (sz, sz * rnd.uniform(0.6, 1.0), sz * 0.6), seed + i, sub=2, sink=0.2)
    return m

ROCHA = {'rocha': ('tex', 'rocha', ((112, 111, 107), (150, 148, 142), (188, 185, 178)), 11)}
for i in range(8):                                   # pedregulhos medios
    want(f'pedra_media_{i % 3}', lambda i=i: boulder(100 + i % 3), ROCHA, f'boulders_{i}')
for i in list(range(8, 16)) + list(range(48, 56)):   # seixos
    want(f'seixos_{i % 2}', lambda i=i: pebbles(120 + i % 2, n=2, big=0.09), ROCHA, f'boulders_{i}')
for i in range(16, 36):                              # lajes e lascas grandes
    want(f'laje_{i % 4}', lambda i=i: slab(140 + i % 4), ROCHA, f'boulders_{i}')
for i in list(range(40, 48)) + list(range(56, 64)):  # pedras desenhadas no chao (tiles de piso)
    want(f'pedras_chao_{i % 3}', lambda i=i: ground_stones(160 + i % 3), ROCHA, f'boulders_{i}')

# ================= v0.9: manta de chao com relevo (tiles de piso blends_natural_01) =================
# Cada tipo ocupa 16 tiles: +0,+5,+6,+7 inteiros; +1..+4 meios-losangos (norte, sul, oeste, leste);
# +8..+15 faixas de borda (mesmo padrao da agua). As mantas cobrem o piso liso do pz3d e emendam entre si,
# porque a textura repete exatamente a cada tile (uv = posicao no tile).
CHAO_Z = 0.004          # base inteira
CHAO_Z_BORDA = 0.007    # transicoes por cima da base
GRID = 8

def chao_altura(x, y):
    """relevo leve: soma de ondulacoes que zeram na borda do tile (emenda sem degrau)."""
    e = (math.sin(math.pi * x) * math.sin(math.pi * y)) ** 0.6
    h = (0.6 * math.sin(2 * math.pi * (2 * x + 1 * y) + 0.7) + 0.5 * math.sin(2 * math.pi * (1 * x - 3 * y) + 2.1)
         + 0.35 * math.sin(2 * math.pi * (4 * x + 3 * y) + 4.0))
    return 0.003 * (h + 1.45) / 2.9 * e

def _dentro(shape, x, y):
    if shape == 'cheio': return True
    if shape == 'norte': return x + y <= 1.0001
    if shape == 'sul': return x + y >= 0.9999
    if shape == 'oeste': return y >= x - 0.0001
    if shape == 'leste': return x >= y - 0.0001
    w = 1.0 / GRID
    if shape == 'y0': return y <= w + 1e-4
    if shape == 'y1': return y >= 1 - w - 1e-4
    if shape == 'x0': return x <= w + 1e-4
    if shape == 'x1': return x >= 1 - w - 1e-4

def chao_piece(shape, z0, lawn=0, seed=0):
    m = Mesh()
    N = GRID
    P = [[(i / N, j / N, z0 + chao_altura(i / N, j / N)) for j in range(N + 1)] for i in range(N + 1)]
    def nrm(i, j):
        return (0.0, 0.0, 1.0)      # normal para cima: mesma luz do piso do pz3d (sem listras nem troca de tom)
    diag = shape in ('oeste', 'leste')        # corta as celulas no sentido do meio-losango
    for i in range(N):
        for j in range(N):
            a, b, c, d = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
            tris = [(a, b, c), (a, c, d)] if diag else [(a, b, d), (b, c, d)]
            for t in tris:
                cx = sum(P[q[0]][q[1]][0] for q in t) / 3; cy = sum(P[q[0]][q[1]][1] for q in t) / 3
                if not _dentro(shape, cx, cy): continue
                pts = [P[q[0]][q[1]] for q in t]
                m.ttris.append((pts[0], pts[1], pts[2], (pts[0][0], pts[0][1]), (pts[1][0], pts[1][1]), (pts[2][0], pts[2][1]),
                                'chao', nrm(*t[0]), nrm(*t[1]), nrm(*t[2])))
    if lawn:
        random.seed(seed)
        for _ in range(lawn):
            x, y = random.uniform(0.03, 0.97), random.uniform(0.03, 0.97)
            k = len(m.cards)
            blade_tex(m, x, y, random.uniform(0.06, 0.15), random.uniform(0.02, 0.032), random.uniform(0.02, 0.1),
                      random.uniform(0, 6.28), mat='lamina', segs=1)
            dz = z0 + chao_altura(x, y)
            m.cards[k:] = [([(q[0], q[1], q[2] + dz) for q in quad], uvs, n, mt) for quad, uvs, n, mt in m.cards[k:]]
    return m

CHAO = {   # base: (nome, textura, cores medidas no piso do jogo p10/mediana/p90, tem capim)
    0:  ('areia',        'chao_areia', ((192, 166, 121), (201, 178, 136), (210, 192, 152)), False),
    16: ('grama_escura', 'chao_grama', ((56, 69, 16), (80, 92, 30), (104, 118, 44)), True),
    32: ('grama_media',  'chao_grama', ((71, 73, 20), (95, 96, 36), (118, 118, 50)), True),
    48: ('grama_clara',  'chao_grama', ((87, 79, 26), (111, 101, 42), (136, 122, 57)), True),
    64: ('terra',        'chao_terra', ((76, 53, 14), (91, 63, 20), (106, 76, 29)), False),
    80: ('terra_escura', 'chao_terra', ((64, 44, 12), (77, 55, 18), (96, 79, 31)), False),
    96: ('terra_marrom', 'chao_terra', ((88, 64, 41), (104, 74, 51), (117, 86, 61)), False),
}
FORMA = {0: 'cheio', 5: 'cheio', 6: 'cheio', 7: 'cheio', 1: 'norte', 2: 'sul', 3: 'oeste', 4: 'leste',
         8: 'y0', 12: 'y0', 9: 'x0', 13: 'x0', 10: 'x1', 14: 'x1', 11: 'y1', 15: 'y1'}
for base, (nome, kind, pal, capim) in CHAO.items():
    mats = {'chao': ('tex', kind, pal, seed_of(nome))}
    if capim:
        lam = tuple(tuple(min(1.0, c / 255 * 1.1) for c in cor) for cor in pal)
        mats_cheio = {**mats, 'lamina': ('tex', 'lamina', lam, seed_of(nome) + 1)}
    for off, forma in FORMA.items():
        tile = f'blends_natural_01_{base + off}'
        if forma == 'cheio':
            want(f'chao_{nome}', lambda nome=nome, capim=capim: chao_piece('cheio', CHAO_Z, lawn=34 if capim else 0, seed=seed_of(nome)),
                 mats_cheio if capim else mats, tile)
        else:
            want(f'chao_{nome}_{forma}', lambda forma=forma: chao_piece(forma, CHAO_Z_BORDA), mats, tile)

# ================= v0.9: folhas secas soltas no chao (d_floorleaves_1) =================
def flat_leaf(m, x, y, z, size, ang, mat):
    dx, dy = math.cos(ang), math.sin(ang); px, py = -dy, dx
    tilt = random.uniform(-0.25, 0.25)
    base = (x - dx * size * 0.5, y - dy * size * 0.5, z)
    tip = (x + dx * size * 0.5, y + dy * size * 0.5, z + tilt * size * 0.3)
    l = (x - px * size * 0.35, y - py * size * 0.35, z + abs(tilt) * size * 0.2)
    r = (x + px * size * 0.35, y + py * size * 0.35, z)
    quad(m, [base, r, tip, l], [(0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5)], (0.0, 0.0, 1.0), mat)

def leaf_litter(seed, n=90):
    random.seed(seed); m = Mesh()
    for i in range(n):
        r = 0.42 * math.sqrt(random.random()); a = random.uniform(0, 6.28)
        x, y = 0.5 + r * math.cos(a), 0.5 + r * math.sin(a)
        flat_leaf(m, x, y, 0.012 + 0.002 * (i % 5), random.uniform(0.06, 0.11), random.uniform(0, 6.28),
                  random.choice(['fa', 'fa', 'fb', 'fc']))
    return m
SECAS = {'fa': ('tex', 'folha', ((0.28, 0.17, 0.08), (0.40, 0.25, 0.11), (0.50, 0.33, 0.15)), 201),
         'fb': ('tex', 'folha', ((0.40, 0.10, 0.06), (0.54, 0.16, 0.08), (0.64, 0.24, 0.12)), 202),
         'fc': ('tex', 'folha', ((0.48, 0.36, 0.10), (0.62, 0.48, 0.16), (0.74, 0.60, 0.24)), 203)}
for i in range(12):
    want(f'folhas_secas_{i % 3}', lambda i=i: leaf_litter(300 + i % 3), SECAS, f'd_floorleaves_1_{i}')

# ================= v0.10: placas de transito =================
# Lado da placa: medido pela inclinacao do desenho isometrico de cada tile.
#   '\\' (inclinacao +) = placa no plano do eixo x, frente para +y;  '/' (inclinacao -) = plano do eixo y, frente para +x.
#   Tiles que mostram o verso cinza tem a frente virada para o lado oposto (-y ou -x).
# "Direita" de quem olha a frente: r = (ny, -nx). Placas grandes ocupam 2 tiles: cada tile tem a sua metade.
def _sign_board(m, n, s0, s1, z0, z1, u0, u1, front_mat, back_mat, dist=0.05):
    nx, ny = n; rx, ry = ny, -nx
    cx, cy = 0.5 + nx * dist, 0.5 + ny * dist
    def P(sv, z, off=0.0): return (cx + rx * sv + nx * off, cy + ry * sv + ny * off, z)
    quad(m, [P(s0, z0), P(s1, z0), P(s1, z1), P(s0, z1)], [(u0, 0), (u1, 0), (u1, 1), (u0, 1)], (nx, ny, 0.0), front_mat)
    # verso: espelhado em u para ficar coerente visto por tras
    quad(m, [P(s0, z0, -0.012), P(s1, z0, -0.012), P(s1, z1, -0.012), P(s0, z1, -0.012)],
         [(1 - u0, 0), (1 - u1, 0), (1 - u1, 1), (1 - u0, 1)], (-nx, -ny, 0.0), back_mat)

def sign_model(kind, n, half=None):
    m = Mesh()
    if kind == 'losango':
        tube(m, (0.5, 0.5, 0), (0.5, 0.5, 2.05), 0.028, 0.028, 'metal', sides=6)
        _sign_board(m, n, -0.53, 0.53, 1.27, 2.33, 0, 1, 'frente', 'verso')
    elif kind == 'pare':
        tube(m, (0.5, 0.5, 0), (0.5, 0.5, 1.8), 0.028, 0.028, 'metal', sides=6)
        _sign_board(m, n, -0.38, 0.38, 1.17, 1.93, 0, 1, 'frente', 'verso')
    else:   # placa grande de 2 tiles (verde ou azul), cada tile com metade
        z0, z1 = (1.50, 2.57) if kind == 'verde' else (1.10, 2.58)
        tube(m, (0.5, 0.5, 0), (0.5, 0.5, z1 - 0.1), 0.035, 0.035, 'metal', sides=6)
        if half == 'esq': _sign_board(m, n, -0.45, 0.5, z0, z1, 0.0, 0.5, 'frente', 'verso')
        else:             _sign_board(m, n, -0.5, 0.45, z0, z1, 0.5, 1.0, 'frente', 'verso')
    return m

import tempfile
TEXDIR = tempfile.mkdtemp(prefix='pz3d_placas_')   # texturas inteiras das placas grandes (temporario)
os.makedirs(TEXDIR, exist_ok=True)
def _full(name, fn):
    path = os.path.join(TEXDIR, name + '.png')
    if not os.path.exists(path): fn(path)
    return path
def tex_losango(sym): return ('img', lambda out, sym=sym: signs.diamond_texture(out, sym))
def tex_pare(): return ('img', lambda out: signs.stop_texture(out))
def tex_metade(name, fn, which):
    return ('img', lambda out, name=name, fn=fn, which=which: signs.half(_full(name, fn), out, which))
def tex_verso(front):
    def make(out, front=front):
        tmp = out + '.frente.png'; front[1](tmp); signs.back_texture(out, tmp); os.remove(tmp)
    return ('img', make)
METAL = (0.55, 0.56, 0.58)
N = {'+y': (0, 1), '+x': (1, 0), '-y': (0, -1), '-x': (-1, 0)}

# placas amarelas de 1 tile (r4, r5 = verso de losango)
LOSANGO = {8: ('curva_dir', '+y'), 9: ('curva_esq', '+y'), 10: ('sinuosa', '+y'), 11: ('reversa_dir', '+y'), 12: ('zigue', '+y'),
           16: ('curva_dir', '+x'), 17: ('curva_esq', '+x'), 18: ('reversa_esq', '+x'), 19: ('sinuosa', '+x'), 20: ('zigue', '+x'),
           4: ('curva_dir', '-y'), 5: ('curva_dir', '-x')}
for idx, (sym, d) in LOSANGO.items():
    fr = tex_losango(sym)
    want(f'placa_{sym}_{d[0] == "+" and "p" or "m"}{d[1]}', lambda d=d: sign_model('losango', N[d]),
         {'frente': fr, 'verso': tex_verso(fr), 'metal': METAL}, f'street_roadsigns_01_{idx}')
# PARE (street_decoration_01 0-3)
for idx, d in {0: '+y', 1: '+x', 2: '-y', 3: '-x'}.items():
    fr = tex_pare()
    want(f'placa_pare_{d[0] == "+" and "p" or "m"}{d[1]}', lambda d=d: sign_model('pare', N[d]),
         {'frente': fr, 'verso': tex_verso(fr), 'metal': METAL}, f'street_decoration_01_{idx}')
# placas grandes de 2 tiles: (tile esquerdo, tile direito, tipo, textura, lado)
GRANDES = [
    (34, 35, 'verde', 'muldraugh_esq', lambda o: signs.green_texture(o, 'Muldraugh', 'esq'), '+x'),
    (36, 37, 'verde', 'westpoint_esq', lambda o: signs.green_texture(o, 'West Point', 'esq'), '+y'),
    (42, 43, 'verde', 'rosewood_esq', lambda o: signs.green_texture(o, 'Rosewood', 'esq'), '+x'),
    (44, 45, 'verde', 'rosewood_dir', lambda o: signs.green_texture(o, 'Rosewood', 'dir'), '+x'),
    (46, 47, 'verde', 'marchridge_esq', lambda o: signs.green_texture(o, 'March Ridge', 'esq'), '+x'),
    (32, 33, 'azul', 'descanso_esq', lambda o: signs.blue_texture(o, 'esq', True), '+x'),
    (38, 39, 'azul', 'descanso_dir', lambda o: signs.blue_texture(o, 'dir', True), '+y'),
    (40, 41, 'azul', 'descanso_dir', lambda o: signs.blue_texture(o, 'dir', True), '+y'),
    (48, 49, 'azul', 'descanso_dir', lambda o: signs.blue_texture(o, 'dir', True), '+x'),
    (50, 51, 'azul', 'descanso_esq_sem', lambda o: signs.blue_texture(o, 'esq', False), '+x'),
    (0, 1, 'verde', 'muldraugh_esq', lambda o: signs.green_texture(o, 'Muldraugh', 'esq'), '-x'),   # versos
    (2, 3, 'verde', 'westpoint_esq', lambda o: signs.green_texture(o, 'West Point', 'esq'), '-y'),
]
for le, ri, kind, tname, fn, d in GRANDES:
    for idx, which in ((le, 'esq'), (ri, 'dir')):
        fr = tex_metade(tname, fn, which)
        want(f'placa_{tname}_{which}_{d[0] == "+" and "p" or "m"}{d[1]}', lambda kind=kind, d=d, which=which: sign_model(kind, N[d], which),
             {'frente': fr, 'verso': tex_verso(fr), 'metal': METAL}, f'street_roadsigns_01_{idx}')

# ---------------- grava modelos e assets.json ----------------
ns = uuid.UUID('6f1c1e9a-3d0b-4a57-9a51-7b2d6c0f1a11')
assets, total = [], 0
import shutil
if os.path.isdir(ASSETS): shutil.rmtree(ASSETS)
for name, (mesh, mats, tiles) in sorted(variants.items()):
    total += mesh.write(os.path.join(ASSETS, name, name + '.obj'), mats)
    random.seed(name)
    binds = []
    for t in tiles:
        if t in tile_scale:                       # arvores jovens: escala = estagio de crescimento
            s = round(tile_scale[t] * random.uniform(0.95, 1.05), 3)
        else:
            s = 1.0 if name.startswith(('sebe', 'agua', 'chao', 'placa')) else round(random.uniform(0.92, 1.08), 2)
        off = round(0.5 - 0.5 * s, 4)
        binds.append({"tile": t, "placement": {"position": [off, off, 0], "rotation": [0, 0, 0], "scale": [s, s, s]}})
    assets.append({"directory": name, "id": str(uuid.uuid5(ns, name)), "name": name.replace('_', ' ').capitalize(),
                   "author": "pz3d Nature Pack", "allowRepack": True,
                   "variants": {name: {"file": name + ".obj", "bindings": binds}}})
os.makedirs(ASSETS, exist_ok=True)
with open(os.path.join(ASSETS, 'assets.json'), 'w', newline='\n') as j:
    json.dump({"schema": "pz3d:assets/1", "assets": assets}, j, indent=2)

os.makedirs(os.path.join(OUT, '42'), exist_ok=True)
with open(os.path.join(OUT, '42', 'mod.info'), 'w', newline='\n') as mi:
    mi.write('name=pz3d Nature Pack\nid=pz3d_naturepack\nauthor=rafaelmariano-glitch\nmodversion=0.11.0\n'
             'versionMin=42.22.2\nrequire=\\pz3d\nposter=poster.png\n'
             'url=https://github.com/rafaelmariano-glitch/pz3d-nature-pack\n'
             'description=Unofficial add-on for pz3d. Replaces flat bushes, hedges, grass, ferns, plants, young trees, '
             'natural ground, rocks, shoreline and road signs with textured 3D models. Enable together with pz3d.\n')
import shutil as _sh
_sh.rmtree(TEXDIR, ignore_errors=True)

ntiles = sum(len(v[2]) for v in variants.values())
print(f'modelos: {len(variants)}  tiles ligados: {ntiles}  triangulos totais: {total}')
for name, (mesh, _, tiles) in sorted(variants.items()):
    print(f'  {name:28s} {len(mesh.f):5d} tri  {len(tiles):3d} tiles')

# ---------------- previa com textura ----------------
if PREVIEW:
    only = os.environ.get('PREVIEW_ONLY')
    exact = os.environ.get('PREVIEW_EXACT') == '1'
    keys = only.split(',') if only else []
    names = ([k for k in keys if k in variants] if exact else
             [n for n in sorted(variants) if not only or any(k in n for k in keys)])
    foliage.render_preview([(n, variants[n][0].tris(), variants[n][1], os.path.join(ASSETS, n)) for n in names], PREVIEW,
                           cols=int(os.environ.get('PREVIEW_COLS', 8)), cell=int(os.environ.get('PREVIEW_CELL', 200)),
                           sprite_dir=os.environ.get('PREVIEW_SPRITES'), floor=os.environ.get('PREVIEW_FLOOR', '1') == '1')
    print('preview:', PREVIEW, len(names))
