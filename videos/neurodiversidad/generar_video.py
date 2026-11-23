#!/usr/bin/env python3
"""
Generador del video «No es un niño con fallas: neurodiversidad»
Raíces y Alas · Constelaciones del Aprender

Dibuja cada cuadro con Pillow, sintetiza una música ambiental con numpy
y une todo con ffmpeg. Uso:

    python3 generar_video.py [carpeta_salida] [--preview SEGUNDO] [--voz]

Sin dependencias externas de red: solo Pillow, numpy y ffmpeg.
"""
import math, random, subprocess, sys, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 24
OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
PREVIEW = None
if "--preview" in sys.argv:
    PREVIEW = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]

# ---------- Paleta (noche estrellada + tierra) ----------
CREAM = (246, 238, 224)
GOLD = (232, 194, 122)
SAGE = (156, 201, 165)
ROSE = (214, 150, 146)
MUTED = (170, 180, 200)
BROWN = (176, 132, 92)
BG_TOP = (14, 22, 42)
BG_BOT = (34, 42, 74)

F_SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf"
F_SERIF_I = "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf"
F_SERIF_B = "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"
F_SANS = "/usr/share/fonts/opentype/inter/InterDisplay-Light.otf"
F_SANS_M = "/usr/share/fonts/opentype/inter/InterDisplay-Regular.otf"
_fonts = {}
def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]

def ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3

def ease_io(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)

# ---------- Fondo ----------
def make_background():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array(BG_TOP), np.array(BG_BOT)
    grad = top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None]
    grad = np.repeat(grad, W, axis=1)
    # viñeta suave
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 1.6)) ** 2 + ((yy - H / 2) / (H / 1.3)) ** 2)
    vig = np.clip(1 - 0.35 * d ** 2, 0.55, 1)[..., None]
    # bruma cálida abajo
    glow = np.exp(-(((xx - W * 0.5) / (W * 0.6)) ** 2 + ((yy - H * 1.05) / (H * 0.45)) ** 2))[..., None]
    img = grad * vig + glow * np.array([40, 26, 30])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")

def make_glow(radius, color, core=0.25):
    s = radius * 2 + 1
    yy, xx = np.mgrid[0:s, 0:s]
    d = np.sqrt((xx - radius) ** 2 + (yy - radius) ** 2) / radius
    a = np.clip(np.exp(-d * d * 4) * 0.8 + np.clip(1 - d / core, 0, 1), 0, 1)
    arr = np.zeros((s, s, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")

random.seed(7)
STARS = [(random.uniform(0, W), random.uniform(0, H * 0.95), random.uniform(0.6, 2.2),
          random.uniform(0, 6.28), random.uniform(0.3, 1.2)) for _ in range(230)]

def draw_stars(img, t):
    d = ImageDraw.Draw(img)
    for x, y, r, ph, sp in STARS:
        b = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * sp + ph))
        xx = (x + t * 3 * (r / 2)) % W
        c = tuple(int(v * b * 0.85) + int(20 * (1 - b)) for v in (235, 230, 255))
        d.ellipse([xx - r / 2, y - r / 2, xx + r / 2, y + r / 2], fill=c + (255,))

# ---------- Elementos ----------
class Elem:
    fade = 0.9
    def __init__(self, t_in):
        self.t_in = t_in
    def alpha(self, t, scene_dur):
        a = ease((t - self.t_in) / self.fade)
        out = ease_io((scene_dur - t) / 0.7)
        return a * out

class Text(Elem):
    def __init__(self, text, size, y, t_in, color=CREAM, f=F_SERIF, width=1500,
                 align="center", x=None, spacing=1.32, rise=22):
        super().__init__(t_in)
        fnt = font(f, size)
        lines = []
        for para in text.split("\n"):
            cur = ""
            for w in para.split(" "):
                test = (cur + " " + w).strip()
                if fnt.getlength(test) <= width or not cur:
                    cur = test
                else:
                    lines.append(cur); cur = w
            lines.append(cur)
        lh = int(size * spacing)
        tw = int(max(fnt.getlength(l) for l in lines)) + 8
        th = lh * len(lines) + int(size * 0.35)
        im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        for i, l in enumerate(lines):
            lw = fnt.getlength(l)
            lx = (tw - lw) / 2 if align == "center" else 0
            dr.text((lx + 4, i * lh), l, font=fnt, fill=color + (255,))
        self.img = im
        self.w, self.h = tw, th
        if align == "center":
            self.x = int((x if x is not None else W / 2) - tw / 2)
        else:
            self.x = int(x)
        self.y = y
        self.rise = rise
        self._cache = {}
    def render(self, frame, t, sd):
        a = self.alpha(t, sd)
        if a <= 0.004:
            return
        q = round(a * 24)
        if q not in self._cache:
            im = self.img.copy()
            al = im.getchannel("A").point(lambda v: int(v * q / 24))
            im.putalpha(al)
            self._cache[q] = im
        dy = int((1 - ease((t - self.t_in) / self.fade)) * self.rise)
        frame.alpha_composite(self._cache[q], dest=(self.x, self.y + dy))

class Shape(Elem):
    """Elemento dibujado con una función f(draw, t_local, alpha) sobre una capa."""
    def __init__(self, t_in, fn):
        super().__init__(t_in)
        self.fn = fn
    def render(self, frame, t, sd):
        a = self.alpha(t, sd)
        if a <= 0.004:
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        self.fn(layer, t - self.t_in, a)
        frame.alpha_composite(layer)

def col(c, a):
    return c + (int(255 * a),)

def lerp(p, q, u):
    return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)

# ---------- Dibujos ----------
def strike(x0, x1, y, dur=0.6, color=ROSE, width=4):
    def fn(layer, tl, a):
        u = ease(tl / dur)
        d = ImageDraw.Draw(layer)
        d.line([(x0, y), (x0 + (x1 - x0) * u, y + 2)], fill=col(color, a), width=width)
    return fn

def text_strike(txt_elem, t_in, color=ROSE):
    y = txt_elem.y + int(txt_elem.h * 0.42)
    return Shape(t_in, strike(txt_elem.x - 6, txt_elem.x + txt_elem.w + 6, y, color=color))

def plant_layer(kind, cx, base):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "pino":
        d.rectangle([cx - 10, base - 60, cx + 10, base], fill=BROWN + (255,))
        for i, (wd, y0) in enumerate([(150, 70), (125, 140), (100, 205), (70, 265)]):
            yb = base - y0 + 30
            d.polygon([(cx - wd, yb), (cx + wd, yb), (cx, yb - 110)],
                      fill=(88 + i * 10, 150 + i * 8, 118 + i * 6, 255))
    elif kind == "helecho":
        pts = [(cx + 40 * math.sin(i / 30 * 1.6) - 20, base - i * 10) for i in range(31)]
        d.line(pts, fill=(120, 170, 120, 255), width=6)
        for i in range(2, 30, 2):
            x, y = pts[i]
            L = 70 * (1 - i / 34)
            for s in (-1, 1):
                d.ellipse([x + (s * L if s < 0 else 0), y - 10, x + (L if s > 0 else 0), y + 8],
                          fill=(140, 196, 140, 255))
    elif kind == "cactus":
        g = (110, 168, 128, 255)
        d.rounded_rectangle([cx - 38, base - 290, cx + 38, base], radius=38, fill=g)
        d.rounded_rectangle([cx - 115, base - 200, cx - 72, base - 95], radius=22, fill=g)
        d.rounded_rectangle([cx - 115, base - 120, cx - 30, base - 80], radius=20, fill=g)
        d.rounded_rectangle([cx + 72, base - 240, cx + 112, base - 140], radius=20, fill=g)
        d.rounded_rectangle([cx + 30, base - 165, cx + 112, base - 128], radius=18, fill=g)
        for k in range(6):
            d.ellipse([cx - 12 + (k % 2) * 16, base - 300 - k * 4, cx + 2 + (k % 2) * 16, base - 286 - k * 4],
                      fill=ROSE + (255,))
    elif kind == "girasol":
        d.line([(cx, base), (cx + 8, base - 260)], fill=(110, 160, 100, 255), width=9)
        d.ellipse([cx - 70, base - 150, cx + 5, base - 115], fill=(120, 175, 110, 255))
        d.ellipse([cx + 5, base - 110, cx + 80, base - 75], fill=(120, 175, 110, 255))
        hx, hy = cx + 8, base - 300
        for k in range(16):
            ang = k / 16 * 2 * math.pi
            px, py = hx + math.cos(ang) * 52, hy + math.sin(ang) * 52
            d.ellipse([px - 22, py - 22, px + 22, py + 22], fill=GOLD + (255,))
        d.ellipse([hx - 36, hy - 36, hx + 36, hy + 36], fill=(120, 82, 52, 255))
    elif kind == "lavanda":
        random.seed(3)
        for k in range(9):
            sx = cx - 80 + k * 20
            top = base - random.randint(170, 250)
            d.line([(sx, base), (sx + (k - 4) * 6, top)], fill=(120, 165, 120, 255), width=4)
            for j in range(7):
                yy = top + j * 12
                xx = sx + (k - 4) * 6 * (1 - j / 14)
                d.ellipse([xx - 7, yy - 7, xx + 7, yy + 7], fill=(178, 158, 214, 255))
    return im

def plants_shape(base=720):
    kinds = [("pino", 330), ("helecho", 650), ("cactus", 960), ("girasol", 1270), ("lavanda", 1590)]
    layers = [(plant_layer(k, x, base), x, i) for i, (k, x) in enumerate(kinds)]
    def fn(layer, tl, a):
        d = ImageDraw.Draw(layer)
        d.line([(160, base + 2), (W - 160, base + 2)], fill=col((120, 110, 100), a * 0.7), width=3)
        for pl, x, i in layers:
            g = ease((tl - i * 0.6) / 1.6)
            if g <= 0:
                continue
            top = int(base - 420 * g)
            crop = pl.crop((x - 200, top, x + 200, base + 1))
            if a < 1:
                crop.putalpha(crop.getchannel("A").point(lambda v: int(v * a)))
            layer.alpha_composite(crop, dest=(x - 200, top))
    return fn

STAR_GLOW = make_glow(18, GOLD)
STAR_GLOW_S = make_glow(10, CREAM)

def constellation_shape(centers, seed=11, scale=120, start_delay=0.0, per=1.4, lw=2, n=(6, 8)):
    rng = random.Random(seed)
    groups = []
    for cx, cy in centers:
        k = rng.randint(*n)
        pts = []
        for _ in range(k):
            ang = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(0.25, 1) * scale
            pts.append((cx + math.cos(ang) * r * 1.2, cy + math.sin(ang) * r))
        # camino: vecino más cercano
        path = [pts.pop(0)]
        while pts:
            last = path[-1]
            j = min(range(len(pts)), key=lambda i: (pts[i][0] - last[0]) ** 2 + (pts[i][1] - last[1]) ** 2)
            path.append(pts.pop(j))
        extra = []
        if len(path) > 4 and rng.random() < 0.8:
            extra.append((path[1], path[rng.randint(3, len(path) - 1)]))
        groups.append((path, extra))
    def fn(layer, tl, a):
        d = ImageDraw.Draw(layer)
        for gi, (path, extra) in enumerate(groups):
            lt = tl - start_delay - gi * per
            if lt <= 0:
                continue
            segs = list(zip(path[:-1], path[1:])) + extra
            nseg = len(segs)
            prog = lt / 2.2 * nseg
            for si, (p, q) in enumerate(segs):
                u = max(0, min(1, prog - si))
                if u > 0:
                    d.line([p, lerp(p, q, u)], fill=col(GOLD, a * 0.55), width=lw)
            for pi, p in enumerate(path):
                sa = ease((lt - pi * 0.12) / 0.5) * a
                if sa <= 0:
                    continue
                g = STAR_GLOW if pi % 3 == 0 else STAR_GLOW_S
                gg = g.copy()
                gg.putalpha(gg.getchannel("A").point(lambda v: int(v * sa)))
                layer.alpha_composite(gg, dest=(int(p[0] - g.width / 2), int(p[1] - g.height / 2)))
    return fn

def tree_shape(cx, ground):
    rng = random.Random(5)
    branches, roots = [], []
    def grow(x, y, ang, L, depth, out, maxd, spread, shrink):
        if depth > maxd:
            return
        x2, y2 = x + math.cos(ang) * L, y + math.sin(ang) * L
        out.append((depth, (x, y), (x2, y2), max(1, int(14 * (shrink ** depth)))))
        for s in (-1, 1):
            grow(x2, y2, ang + s * spread * rng.uniform(0.7, 1.2), L * rng.uniform(0.66, 0.78),
                 depth + 1, out, maxd, spread, shrink)
    trunk_top = ground - 170
    branches.append((0, (cx, ground), (cx, trunk_top), 18))
    for s in (-1, 1):
        grow(cx, trunk_top, -math.pi / 2 + s * 0.55, 120, 1, branches, 6, 0.42, 0.72)
    for s in (-1, 0, 1):
        grow(cx, ground, math.pi / 2 + s * 0.6, 70, 1, roots, 5, 0.5, 0.65)
    tips = [q for (dp, p, q, w) in branches if dp == 6]
    def fn(layer, tl, a):
        d = ImageDraw.Draw(layer)
        d.line([(cx - 260, ground), (cx + 260, ground)], fill=col((130, 110, 95), a * 0.8), width=3)
        rprog = tl / 0.7
        for dp, p, q, w in roots:
            u = max(0, min(1, rprog - dp))
            if u > 0:
                d.line([p, lerp(p, q, u)], fill=col(BROWN, a * 0.9), width=max(1, w - 2))
        bprog = (tl - 2.0) / 0.55
        for dp, p, q, w in branches:
            u = max(0, min(1, bprog - dp))
            if u > 0:
                c = BROWN if dp < 3 else (150, 175, 140)
                d.line([p, lerp(p, q, u)], fill=col(c, a), width=w)
        la = ease((tl - 6.0) / 1.5) * a
        if la > 0:
            for i, (x, y) in enumerate(tips):
                r = 6 + (i % 3) * 2
                c = SAGE if i % 4 else GOLD
                d.ellipse([x - r, y - r, x + r, y + r], fill=col(c, la * 0.9))
    return fn

def divider(x, y0, y1):
    def fn(layer, tl, a):
        u = ease(tl / 1.2)
        ImageDraw.Draw(layer).line([(x, y0), (x, y0 + (y1 - y0) * u)], fill=col(GOLD, a * 0.5), width=2)
    return fn

def sparkle(x, y, r=12, color=GOLD):
    def fn(layer, tl, a):
        d = ImageDraw.Draw(layer)
        pts = []
        for k in range(8):
            ang = k * math.pi / 4 - math.pi / 2
            rr = r if k % 2 == 0 else r * 0.32
            pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
        d.polygon(pts, fill=col(color, a))
    return fn

def arrow(x0, x1, y):
    def fn(layer, tl, a):
        u = ease(tl / 0.6)
        d = ImageDraw.Draw(layer)
        xe = x0 + (x1 - x0) * u
        d.line([(x0, y), (xe, y)], fill=col(GOLD, a), width=3)
        if u > 0.9:
            d.polygon([(xe + 4, y), (xe - 12, y - 8), (xe - 12, y + 8)], fill=col(GOLD, a))
    return fn

# ---------- Escenas ----------
def bullets(title, items, t0=1.6, gap=2.4, y0=300, dy=124, title_color=GOLD):
    els = [Text(title, 64, 150, 0.3, title_color, F_SERIF_I)]
    for i, it in enumerate(items):
        y = y0 + i * dy
        t = t0 + i * gap
        els.append(Shape(t, sparkle(300, y + 26)))
        els.append(Text(it, 40, y, t, CREAM, F_SANS, width=1430, align="left", x=345))
    return els

def scenes():
    S = []
    # 1 · Portada
    S.append((10, [
        Shape(0, constellation_shape([(1560, 250), (330, 820)], seed=3, scale=110, per=0.8)),
        Text("Raíces y Alas  ·  Constelaciones del Aprender", 32, 300, 0.4, GOLD, F_SANS_M),
        Text("No es un niño con fallas.", 104, 400, 1.2, CREAM, F_SERIF_I),
        Text("Neurodiversidad: cerebros que funcionan distinto,\nno cerebros rotos.", 46, 590, 2.8, SAGE, F_SANS),
        Text("Para familias y docentes", 30, 790, 4.2, MUTED, F_SANS),
    ]))
    # 2 · Las palabras que usamos
    words = [("flojo", 380, 360), ("distraído", 960, 330), ("lento", 1540, 380),
             ("problemático", 600, 520), ("«no pone atención»", 1330, 520), ("con fallas", 960, 680)]
    els = [Text("¿Qué palabras usamos cuando un niño aprende distinto?", 58, 150, 0.3, CREAM, F_SERIF)]
    wt = []
    for i, (w_, x, y) in enumerate(words):
        e = Text(w_, 54 if w_ != "con fallas" else 64, y, 1.6 + i * 0.55, ROSE, F_SERIF_I, x=x)
        els.append(e); wt.append(e)
    for i, e in enumerate(wt):
        els.append(text_strike(e, 6.6 + i * 0.25))
    els.append(Text("¿Y si lo que falla no es el niño, sino la mirada?", 56, 860, 8.8, GOLD, F_SERIF_I))
    S.append((13, els))
    # 3 · Las palabras construyen
    S.append((12, [
        Text("Las palabras no solo describen.", 72, 350, 0.4, CREAM, F_SERIF),
        Text("También construyen.", 72, 450, 2.2, GOLD, F_SERIF_I),
        Text("Un niño que escucha una y otra vez «tienes fallas» puede terminar creyendo que él mismo es la falla.",
             44, 640, 4.6, CREAM, F_SANS, width=1350),
    ]))
    # 4 · El bosque
    S.append((15, [
        Text("Piensa en un bosque.", 64, 130, 0.3, CREAM, F_SERIF_I),
        Shape(1.2, plants_shape(720)),
        Text("Nadie dice que el helecho es un pino fallado,", 44, 770, 5.6, CREAM, F_SANS),
        Text("ni que el cactus es un girasol defectuoso.", 44, 835, 7.0, CREAM, F_SANS),
        Text("Cada especie funciona distinto. Y el bosque vive gracias a esa diferencia.",
             44, 940, 9.6, GOLD, F_SERIF_I, width=1700),
    ]))
    # 5 · Definición
    S.append((15, [
        Text("A eso, en las personas, lo llamamos", 44, 230, 0.3, MUTED, F_SANS),
        Text("NEURODIVERSIDAD", 112, 300, 1.2, GOLD, F_SERIF_B),
        Text("La variedad natural en la forma en que funcionan los cerebros humanos: "
             "cómo percibimos, sentimos, pensamos, aprendemos y nos relacionamos.",
             44, 490, 3.0, CREAM, F_SANS, width=1400),
        Text("Todos y todas formamos parte de ella.", 54, 730, 7.0, SAGE, F_SERIF_I),
        Text("Concepto propuesto a finales de los años 90 por la socióloga australiana Judy Singer.",
             30, 930, 9.0, MUTED, F_SANS),
    ]))
    # 6 · Neurotípico / neurodivergente
    S.append((17, [
        Shape(0.2, divider(W // 2, 260, 760)),
        Text("Neurotípico", 62, 270, 0.6, GOLD, F_SERIF_I, x=W // 2 - 440),
        Text("Un cerebro que funciona de forma cercana a lo que la sociedad considera «lo esperado».",
             38, 390, 1.5, CREAM, F_SANS, width=700, x=W // 2 - 440),
        Text("Neurodivergente", 62, 270, 3.6, SAGE, F_SERIF_I, x=W // 2 + 440),
        Text("Un cerebro que funciona de forma distinta a esa norma. Por ejemplo: autismo, TDAH, dislexia, "
             "discalculia, dispraxia, síndrome de Tourette, altas capacidades…",
             38, 390, 4.5, CREAM, F_SANS, width=700, x=W // 2 + 440),
        Text("Ninguno es «mejor» ni «peor».\nSon formas distintas de estar en el mundo.",
             48, 830, 9.5, CREAM, F_SERIF),
    ]))
    # 7 · Dos miradas
    rows = [("¿Qué le falta?", "¿Cómo aprende?"),
            ("Corregir lo que está mal", "Comprender y acompañar"),
            ("Una etiqueta que encierra", "Un mapa que orienta"),
            ("Que el niño se adapte a la escuela", "Que el entorno también se adapte")]
    els = [Text("Dos miradas", 64, 110, 0.3, CREAM, F_SERIF_I),
           Text("Mirada del déficit", 44, 245, 1.0, ROSE, F_SANS_M, x=W // 2 - 450),
           Text("Mirada de la neurodiversidad", 44, 245, 1.0, SAGE, F_SANS_M, x=W // 2 + 450)]
    for i, (l, r) in enumerate(rows):
        y = 360 + i * 108
        t = 2.4 + i * 1.9
        els.append(Text(l, 40, y, t, (214, 200, 196), F_SANS, x=W // 2 - 450, width=760))
        els.append(Shape(t + 0.5, arrow(W // 2 - 40, W // 2 + 40, y + 26)))
        els.append(Text(r, 40, y, t + 0.8, CREAM, F_SANS_M, x=W // 2 + 450, width=760))
    els.append(Text("Distinto no significa roto.", 64, 850, 11.0, GOLD, F_SERIF_I))
    S.append((16, els))
    # 8 · Responsabilidad: no negar dificultades
    S.append((17, [
        Text("Ojo: esto no significa negar las dificultades.", 56, 170, 0.3, GOLD, F_SERIF_I),
        Text("Un niño neurodivergente puede pasarla muy mal: con el ruido del aula, con ciertas normas, "
             "con la frustración de no ser comprendido.", 42, 320, 2.2, CREAM, F_SANS, width=1450),
        Text("El diagnóstico, las terapias y los apoyos son herramientas valiosas.",
             42, 500, 5.6, CREAM, F_SANS, width=1450),
        Text("La diferencia está en desde dónde los usamos:", 42, 620, 8.2, CREAM, F_SANS),
        Text("no para «arreglar» a alguien, sino para que pueda ser plenamente quien es.",
             48, 720, 10.0, SAGE, F_SERIF_I, width=1700),
    ]))
    # 9 · Constelaciones
    S.append((16, [
        Text("En Constelaciones del Aprender lo pienso así:", 44, 110, 0.3, MUTED, F_SANS),
        Shape(1.0, constellation_shape([(360, 450), (780, 410), (1150, 480), (1560, 420)],
                                       seed=21, scale=125, per=1.3, lw=3)),
        Text("Cada niño es una constelación única.", 60, 720, 7.0, CREAM, F_SERIF_I),
        Text("Sus estrellas se conectan de otra forma. Nuestro trabajo no es reordenarlas: "
             "es aprender a leer su mapa.", 42, 830, 9.2, GOLD, F_SANS, width=1500),
    ]))
    # 10 · Raíces y Alas
    S.append((17, [
        Shape(0.3, tree_shape(500, 640)),
        Text("Raíces y Alas", 72, 210, 1.0, GOLD, F_SERIF_I, align="left", x=950),
        Text("Raíces: que se sienta seguro, visto y aceptado tal como es.",
             42, 360, 3.0, CREAM, F_SANS, width=850, align="left", x=950),
        Text("Alas: que pueda desplegar su propia forma de aprender, crear y brillar.",
             42, 520, 6.0, CREAM, F_SANS, width=850, align="left", x=950),
        Text("Primero raíces. Desde ahí, las alas.", 50, 720, 9.5, SAGE, F_SERIF_I, align="left", x=950),
    ]))
    # 11 · Familias
    S.append((19, bullets("Sugerencias para las familias", [
        "Cambia «¿qué le pasa?» por «¿qué necesita?».",
        "Observa cuándo florece: qué le apasiona, dónde se calma, cómo se concentra.",
        "Nombra sus fortalezas tanto como sus desafíos.",
        "Háblale de su forma de aprender, nunca de sus «fallas».",
        "Cuida también tu energía: acompañar cansa, y pedir apoyo está bien.",
    ])))
    # 12 · Docentes
    S.append((19, bullets("Sugerencias para docentes", [
        "Ofrece más de un camino para aprender… y para demostrar lo aprendido.",
        "Antes de pedir que el niño se ajuste, pregúntate qué del entorno puede ajustarse.",
        "Usa un lenguaje que describe, no que sentencia.",
        "Busca su interés profundo: suele ser la puerta de entrada.",
        "Trabaja en red con la familia y los especialistas.",
    ], title_color=SAGE)))
    # 13 · Cambios de lenguaje
    pairs = [("«Tiene fallas»", "«Aprende de otra manera»"),
             ("«Es un niño problema»", "«Tiene necesidades que aún no comprendemos»"),
             ("«No sirve para esto»", "«Todavía no encontramos su camino para esto»"),
             ("«Es un caso»", "«Es una persona, con nombre e historia»")]
    els = [Text("Pequeños cambios de lenguaje, grandes cambios de mirada", 54, 130, 0.3, CREAM, F_SERIF_I)]
    for i, (o, n) in enumerate(pairs):
        y = 290 + i * 125
        t = 1.6 + i * 2.3
        eo = Text(o, 40, y, t, ROSE, F_SERIF_I, x=520, width=600)
        els += [eo, text_strike(eo, t + 0.9),
                Shape(t + 1.0, arrow(820, 900, y + 26)),
                Text(n, 40, y, t + 1.2, CREAM, F_SANS_M, align="left", x=940, width=900)]
    els.append(Text("Y cuando sea posible, pregúntale a la persona cómo prefiere nombrarse.",
                    38, 860, 11.5, SAGE, F_SANS))
    S.append((17, els))
    # 14 · Cierre
    S.append((16, [
        Shape(0, constellation_shape([(330, 230), (1600, 800)], seed=8, scale=100, per=0.6)),
        Text("No hay cerebros rotos.", 84, 330, 0.5, CREAM, F_SERIF),
        Text("Hay cerebros distintos esperando ser comprendidos.", 56, 450, 2.6, GOLD, F_SERIF_I),
        Text("Raíces para sostener. Alas para volar.", 46, 600, 5.0, SAGE, F_SERIF_I),
        Text("Raíces y Alas  ·  Constelaciones del Aprender", 34, 860, 7.0, CREAM, F_SANS_M),
        Text("Si este mensaje te resonó, compártelo con alguien que acompaña a un niño.",
             30, 925, 8.2, MUTED, F_SANS),
    ]))
    return S

# ---------- Música ambiental ----------
def make_music(seconds, path, sr=44100):
    n = int(seconds * sr)
    t = np.arange(n) / sr
    def hz(m): return 440 * 2 ** ((m - 69) / 12)
    chords = [[48, 55, 64, 71], [45, 52, 60, 67], [41, 48, 57, 64], [43, 50, 59, 62]]  # Cmaj7 Am7 Fmaj7 G
    cl = 8.0
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    nch = int(math.ceil(seconds / cl)) + 1
    for k in range(nch):
        s0 = int((k * cl - 1.5) * sr)
        seg_len = int((cl + 3.0) * sr)
        a0, a1 = max(0, s0), min(n, s0 + seg_len)
        if a1 <= a0: continue
        tt = (np.arange(a0, a1) - s0) / sr
        env = np.clip(tt / 2.5, 0, 1) * np.clip((cl + 3.0 - tt) / 2.5, 0, 1)
        env = env ** 1.5
        for j, m in enumerate(chords[k % 4]):
            f = hz(m)
            for det, pan in ((-0.6, 0.7), (0.6, 0.3)):
                w = np.sin(2 * np.pi * (f + det) * tt + j) * 0.6 + np.sin(2 * np.pi * 2 * (f + det) * tt) * 0.08
                L[a0:a1] += (w * env * pan * 0.05).astype(np.float32)
                R[a0:a1] += (w * env * (1 - pan) * 0.05).astype(np.float32)
    # campanitas (pentatónica)
    rng = np.random.default_rng(4)
    penta = [72, 74, 76, 79, 81, 84, 86, 88]
    tb = 2.0
    while tb < seconds - 3:
        m = penta[rng.integers(len(penta))]
        f = hz(m)
        a0 = int(tb * sr); a1 = min(n, a0 + int(4 * sr))
        tt = np.arange(a1 - a0) / sr
        w = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3)) * np.exp(-tt * 1.3)
        pan = rng.uniform(0.2, 0.8)
        L[a0:a1] += (w * 0.035 * pan).astype(np.float32)
        R[a0:a1] += (w * 0.035 * (1 - pan)).astype(np.float32)
        tb += rng.choice([1.5, 2.0, 3.0, 4.0])
    # reverb por convolución con ruido decreciente
    ir_len = int(2.8 * sr)
    for ch, seed in ((L, 1), (R, 2)):
        ir = np.random.default_rng(seed).standard_normal(ir_len).astype(np.float32) * np.exp(-np.arange(ir_len) / sr * 2.2)
        ir /= np.abs(ir).sum() / 6
        N = 1 << int(math.ceil(math.log2(n + ir_len)))
        wet = np.fft.irfft(np.fft.rfft(ch, N) * np.fft.rfft(ir, N), N)[:n].astype(np.float32)
        ch[:] = ch * 0.55 + wet * 0.45
    fade = np.clip(t / 3, 0, 1) * np.clip((seconds - t) / 4, 0, 1)
    st = np.stack([L * fade, R * fade], 1)
    st /= np.abs(st).max() / 0.6
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

# ---------- Voz ----------
VOZ = "--voz" in sys.argv
VOICE_LEAD = 0.8
VOZ_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voz")

def voice_clips():
    clips = []
    for i in range(1, 15):
        pth = os.path.join(VOZ_DIR, f"{i:02d}.mp3")
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                           "-of", "csv=p=0", pth]).decode().strip())
        clips.append((pth, d))
    return clips

def mix_voice(music, clips, starts, total):
    """Mezcla la voz sobre la música, bajando la música cuando hay voz."""
    out = music.replace(".wav", "_mezcla.wav")
    args = ["ffmpeg", "-y", "-loglevel", "error", "-i", music]
    fc = []
    for i, (pth, _) in enumerate(clips):
        args += ["-i", pth]
        ms = int((starts[i] + VOICE_LEAD) * 1000)
        fc.append(f"[{i + 1}]aformat=sample_rates=44100:channel_layouts=stereo,adelay={ms}|{ms}[v{i}]")
    n = len(clips)
    fc.append("".join(f"[v{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,asplit[vo][key]")
    fc.append("[0]volume=0.55[m]")
    fc.append("[m][key]sidechaincompress=threshold=0.015:ratio=5:attack=150:release=1400[md]")
    fc.append("[md][vo]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11")
    args += ["-filter_complex", ";".join(fc), "-t", f"{total}", "-ar", "44100", out]
    subprocess.run(args, check=True)
    return out

# ---------- Render ----------
def main():
    bg = make_background()
    S = scenes()
    voz = voice_clips() if VOZ else None
    if voz:
        # Cada escena dura lo que su narración (+ respiro) y los textos se reparten a ese ritmo
        S2 = []
        for (d, els), (path, vd) in zip(S, voz):
            nd = max(d, VOICE_LEAD + vd + 1.8)
            k = nd / d
            for e in els:
                e.t_in *= k
            S2.append((nd, els))
        S = S2
    total = sum(d for d, _ in S)
    starts, acc = [], 0.0
    for d, _ in S:
        starts.append(acc); acc += d

    def frame_at(T):
        fr = bg.copy()
        draw_stars(fr, T)
        for (d, els), s0 in zip(S, starts):
            if s0 <= T < s0 + d:
                tl = T - s0
                for e in els:
                    e.render(fr, tl, d)
        # fundido de entrada / salida global
        g = min(1, T / 1.2, (total - T) / 1.8)
        if g < 1:
            fr = Image.blend(bg, fr, max(0, g))
        return fr.convert("RGB")

    os.makedirs(OUT, exist_ok=True)
    if PREVIEW:
        for T in PREVIEW:
            frame_at(T).save(os.path.join(OUT, f"preview_{T:06.1f}.png"))
        return

    print(f"Duración: {total:.0f} s · {int(total * FPS)} cuadros", flush=True)
    music = os.path.join(OUT, "musica.wav")
    make_music(total, music)
    name = "neurodiversidad_raices_y_alas"
    if voz:
        music = mix_voice(music, voz, starts, total)
        name += "_con_voz"
    out = os.path.join(OUT, name + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", music,
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    nf = int(total * FPS)
    for i in range(nf):
        p.stdin.write(frame_at(i / FPS).tobytes())
        if i % (FPS * 10) == 0:
            print(f"  {i / FPS:5.0f} s", flush=True)
    p.stdin.close(); p.wait()
    # miniatura
    frame_at(4.5).save(os.path.join(OUT, "miniatura.png"))
    print("Listo:", out)

if __name__ == "__main__":
    main()
