#!/usr/bin/env python3
"""
Versión vertical (9:16) para Shorts / Reels de «No es un niño con fallas».
Reutiliza los dibujos y la música de ../generar_video.py y la voz de ./voz/.

    python3 generar_short.py [--preview S1,S2,...]
"""
import os, sys, math, random, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
_argv = sys.argv; sys.argv = [sys.argv[0]]
import generar_video as gv
sys.argv = _argv
from PIL import Image, ImageDraw

W, H, FPS = 1080, 1920, 24
gv.W, gv.H = W, H
random.seed(9)
gv.STARS = [(random.uniform(0, W), random.uniform(0, H * 0.97), random.uniform(0.6, 2.2),
             random.uniform(0, 6.28), random.uniform(0.3, 1.2)) for _ in range(200)]
gv.VOICE_LEAD = 0.5
T, Sh = gv.Text, gv.Shape
CREAM, GOLD, SAGE, ROSE, MUTED = gv.CREAM, gv.GOLD, gv.SAGE, gv.ROSE, gv.MUTED
SER, SER_I, SER_B, SANS, SANS_M = gv.F_SERIF, gv.F_SERIF_I, gv.F_SERIF_B, gv.F_SANS, gv.F_SANS_M
CW = 900  # ancho útil (deja margen para los íconos de la app)

def plants_v(base=1150):
    kinds = [("pino", 230), ("helecho", 545), ("girasol", 850)]
    layers = [(gv.plant_layer(k, x, base), x, i) for i, (k, x) in enumerate(kinds)]
    def fn(layer, tl, a):
        d = ImageDraw.Draw(layer)
        d.line([(60, base + 2), (W - 60, base + 2)], fill=gv.col((120, 110, 100), a * 0.7), width=3)
        for pl, x, i in layers:
            g = gv.ease((tl - i * 0.6) / 1.6)
            if g <= 0:
                continue
            top = int(base - 420 * g)
            crop = pl.crop((x - 200, top, x + 200, base + 1))
            if a < 1:
                crop.putalpha(crop.getchannel("A").point(lambda v: int(v * a)))
            layer.alpha_composite(crop, dest=(x - 200, top))
    return fn

def arrow_down(x, y0, y1):
    def fn(layer, tl, a):
        u = gv.ease(tl / 0.6)
        d = ImageDraw.Draw(layer)
        ye = y0 + (y1 - y0) * u
        d.line([(x, y0), (x, ye)], fill=gv.col(GOLD, a), width=4)
        if u > 0.9:
            d.polygon([(x, ye + 6), (x - 12, ye - 12), (x + 12, ye - 12)], fill=gv.col(GOLD, a))
    return fn

def scenes():
    S = []
    # 1 · Gancho
    els = [T("Raíces y Alas  ·  Constelaciones del Aprender", 30, 270, 0.0, GOLD, SANS_M),
           T("¿Un niño\ncon fallas?", 110, 380, 0.0, CREAM, SER_I, width=CW)]
    ws = [("flojo", 300, 770, 1.0), ("distraído", 760, 870, 1.8), ("lento", 320, 990, 2.6),
          ("con fallas", 640, 1100, 3.4)]
    for w_, x, y, t in ws:
        e = T(w_, 60 if w_ != "con fallas" else 76, y, t, ROSE, SER_I, x=x)
        els += [e, gv.text_strike(e, 6.4 + ws.index((w_, x, y, t)) * 0.25)]
    els.append(T("¿O será la mirada\nla que falla?", 66, 1290, 8.0, GOLD, SER_I, width=CW))
    S.append((11, els))
    # 2 · Bosque
    S.append((13, [
        T("Piensa en un bosque.", 74, 320, 0.2, CREAM, SER_I, width=CW),
        Sh(1.0, plants_v(1150)),
        T("Nadie dice que el helecho\nes un pino fallado.", 52, 1220, 4.0, CREAM, SANS, width=CW),
        T("Cada especie funciona distinto.", 56, 1400, 7.5, GOLD, SER_I, width=CW),
    ]))
    # 3 · Neurodiversidad
    S.append((12, [
        Sh(0, gv.constellation_shape([(300, 380), (790, 330)], seed=21, scale=95, per=0.7, lw=3)),
        T("Con los cerebros\npasa lo mismo.", 60, 560, 0.3, MUTED, SANS, width=CW),
        T("NEURODIVERSIDAD", 92, 760, 2.4, GOLD, SER_B),
        T("No hay cerebros rotos.", 72, 960, 5.4, CREAM, SER, width=CW),
        T("Hay cerebros que\nfuncionan distinto.", 62, 1100, 8.0, SAGE, SER_I, width=CW),
    ]))
    # 4 · Cambiar la pregunta
    e_old = T("¿Qué le falta?", 76, 830, 1.6, ROSE, SER_I)
    S.append((8, [
        T("Cambiemos la pregunta", 64, 570, 0.2, CREAM, SER_I, width=CW),
        e_old, gv.text_strike(e_old, 3.6),
        Sh(4.0, arrow_down(W // 2, 970, 1080)),
        T("¿Cómo aprende?", 96, 1120, 4.4, SAGE, SER_I),
    ]))
    # 5 · Responsabilidad
    S.append((8, [
        T("Sin negar las dificultades.", 66, 640, 0.2, GOLD, SER_I, width=CW),
        T("Con los apoyos que necesite,", 52, 880, 2.6, CREAM, SANS, width=CW),
        T("para que pueda ser plenamente quien es.", 62, 1000, 4.4, SAGE, SER_I, width=CW),
    ]))
    # 6 · Cierre + llamado
    S.append((9, [
        T("Raíces para sostener.\nAlas para volar.", 62, 250, 0.2, SAGE, SER_I, width=CW),
        Sh(0.4, gv.tree_shape(W // 2, 1110)),
        T("Video completo en el canal", 54, 1380, 4.8, GOLD, SANS_M, width=CW),
        T("Raíces y Alas  ·  Constelaciones del Aprender", 30, 1470, 5.4, CREAM, SANS),
    ]))
    return S

def main():
    preview = None
    if "--preview" in sys.argv:
        preview = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
    bg = gv.make_background()
    S = scenes()
    clips = []
    for i in range(1, len(S) + 1):
        pth = os.path.join(HERE, "voz", f"{i:02d}.mp3")
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                           "-of", "csv=p=0", pth]).decode())
        clips.append((pth, d))
    S2 = []
    for (d, els), (_, vd) in zip(S, clips):
        nd = max(d, gv.VOICE_LEAD + vd + 0.9)
        k = nd / d
        for e in els:
            e.t_in *= k
        S2.append((nd, els))
    S = S2
    # en la última escena, un respiro más para el llamado
    S[-1] = (S[-1][0] + 1.5, S[-1][1])
    starts, acc = [], 0.0
    for d, _ in S:
        starts.append(acc); acc += d
    total = acc

    def frame_at(t):
        fr = bg.copy()
        gv.draw_stars(fr, t)
        for (d, els), s0 in zip(S, starts):
            if s0 <= t < s0 + d:
                for e in els:
                    # la primera escena aparece de inmediato (el primer cuadro importa en Shorts)
                    e.render(fr, t - s0 + (0.9 if s0 == 0 and e.t_in == 0 else 0), d)
        g = min(1, (total - t) / 1.2)
        if g < 1:
            fr = Image.blend(bg, fr, max(0, g))
        return fr.convert("RGB")

    if preview:
        for t in preview:
            frame_at(t).save(os.path.join(HERE, f"preview_{t:05.1f}.png"))
        return
    print(f"Duración: {total:.1f} s", flush=True)
    music = os.path.join(HERE, "musica.wav")
    gv.make_music(total, music)
    mix = gv.mix_voice(music, clips, starts, total)
    out = os.path.join(HERE, "neurodiversidad_short_vertical.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", mix,
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(frame_at(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    frame_at(1.5).save(os.path.join(HERE, "portada_short.png"))
    for f in (music, mix):
        os.remove(f)
    print("Listo:", out)

if __name__ == "__main__":
    main()
