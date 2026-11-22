import sys
import time
from pathlib import Path

import numpy as np
import pygame

TAU = np.pi * 2
GOLDEN = np.pi * (3 - np.sqrt(5))
LOOP = 28.0
PERIOD = 2.0
BEAT0 = 0.2

T_BLOOM = (0.0, 4.0)
T_LEAP = (3.4, 6.2)
T_WINGS = (4.2, 6.4)
T_GLIDE1 = (7.0, 11.2)
T_GLIDE2 = (11.2, 15.4)
T_TWIRL = (15.4, 19.2)
T_MAGIC = 6.2
T_FINALE = (17.8, 19.6)
T_FOLD = (20.8, 23.2)
T_RETURN = (21.0, 24.2)
T_CLOSE = (23.4, 27.4)
FLASH = 0.55
BURST_SPARKS, BURST_SPEED = 90, 3.2

BODY, HAIR, DRESS, WING_U, WING_L, SHOE, WAND, FLOWER, STEM, MARK = range(10)
HARD = np.isin(np.arange(10), (BODY, HAIR, DRESS, WING_U, WING_L, SHOE, WAND, FLOWER, STEM))
POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"]
C = lambda ch: ord(ch) - 32
FILL = np.array([[C(p[k % len(p)]) for k in range(12)] for p in POOLS])
SLOPE = np.array([C(c) for c in "-/|\\-"])

WHITE = np.array([1.00, 0.99, 0.95])
GOLD = np.array([1.00, 0.86, 0.34])
SKIN = np.array([1.00, 0.86, 0.74])
BLONDE = np.array([1.00, 0.88, 0.36])
BLONDE_HI = np.array([1.00, 0.96, 0.68])
STEM_COL = np.array([0.14, 0.62, 0.34])
PETAL_IN = np.array([0.82, 0.18, 0.54])
PETAL_OUT = np.array([1.00, 0.68, 0.88])

PALETTES = np.array([
    [[0.20, 0.82, 0.28], [0.68, 1.00, 0.40], [0.38, 0.92, 1.00], [0.76, 0.96, 1.00], [1.00, 0.98, 0.90]],
    [[0.16, 0.86, 0.46], [0.60, 1.00, 0.78], [0.30, 0.86, 1.00], [0.64, 0.76, 1.00], [0.96, 0.98, 1.00]],
    [[0.24, 0.82, 0.24], [0.94, 0.98, 0.38], [1.00, 0.88, 0.42], [0.58, 0.96, 0.94], [1.00, 0.98, 0.92]],
    [[0.16, 0.76, 0.52], [0.52, 0.98, 0.88], [0.54, 0.66, 1.00], [0.86, 0.62, 1.00], [1.00, 0.90, 0.98]],
    [[0.28, 0.84, 0.30], [0.80, 1.00, 0.46], [0.98, 0.66, 0.90], [0.62, 0.92, 1.00], [1.00, 0.96, 0.84]],
    [[0.22, 0.84, 0.32], [1.00, 0.92, 0.46], [1.00, 0.86, 0.40], [1.00, 0.94, 0.68], [1.00, 0.99, 0.94]],
])
WAVE_SPEED = 1.55
PALE = lambda rgb, k: rgb + (WHITE - rgb) * k
DUST_COL = np.array([1.00, 0.88, 0.48])
SPARK_INK = np.array([GOLD, [0.42, 0.94, 1.00], [0.58, 1.00, 0.54], [1.00, 0.74, 0.92], WHITE])


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def fib_sphere(n):
    i = np.arange(n) + 0.5
    y = 1 - 2 * i / n
    r = np.sqrt(1 - y * y)
    return np.stack([r * np.cos(GOLDEN * i), y, r * np.sin(GOLDEN * i)], 1)


def slope_char(dx, dy):
    ang = np.degrees(np.arctan2(dy, dx)) % 180
    return SLOPE[np.digitize(ang, [25, 72, 108, 155])]


def outline_letter(gx, gy):
    ax, ay = np.abs(gx), np.abs(gy)
    c = np.where(ax > 2 * ay, C("|"), np.where(ay > 2 * ax, np.where(gy > 0, C("_"), C("-")),
                 np.where(gx * gy > 0, C("/"), C("\\"))))
    return np.where(ax + ay == 0, C("+"), c)


def span(t, between):
    return smooth((np.asarray(t, float) - between[0]) / (between[1] - between[0]))


def beat(t):
    ph = ((np.asarray(t, float) - BEAT0) / PERIOD) % 1.0
    return np.where(ph < 0.22, smooth(ph / 0.22), 1 - smooth((ph - 0.22) / 0.78))


FLOWER_Y = -0.58
CLIP_Y = FLOWER_Y + 0.03


def fairy_state(t):
    t = np.asarray(t, float)
    leap = span(t, T_LEAP)
    ret = span(t, T_RETURN)
    presence = leap * (1.0 - ret)
    g1 = span(t, T_GLIDE1)
    g2 = span(t, T_GLIDE2)
    twirl = span(t, T_TWIRL)

    x = (0.36 * g1 - 0.72 * g2 + 0.36 * twirl
         + 0.03 * np.sin(1.3 * t) * presence)

    jump_arc = 0.22 * np.sin(np.pi * leap)
    g1_arc = 0.20 * np.sin(np.pi * g1)
    g2_arc = 0.16 * np.sin(np.pi * g2)
    bob = 0.045 * np.sin(2.4 * t) * presence
    y = -1.04 + 1.24 * presence + jump_arc + g1_arc + g2_arc + bob

    z = 0.20 * np.sin(np.pi * g1) - 0.18 * np.sin(np.pi * g2)

    yaw = (-0.35 + 0.90 * np.sin(np.pi * g1) - 0.90 * np.sin(np.pi * g2)
           + TAU * twirl + 0.14 * np.sin(0.8 * t) * presence)

    tilt = (-0.20 * np.sin(np.pi * g1) + 0.20 * np.sin(np.pi * g2)
            + 0.12 * np.sin(TAU * twirl) + 0.05 * np.sin(1.8 * t) * presence)
    return x, y, z, yaw, tilt


def carry(p, t, lag=0.0):
    td = t - lag
    fx, fy, fz, yaw, tilt = fairy_state(td)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    ct, st = np.cos(tilt), np.sin(tilt)
    x, y = x * ct - y * st, x * st + y * ct
    cy, sy = np.cos(yaw), np.sin(yaw)
    return np.stack([x * cy + z * sy + fx, y + fy, -x * sy + z * cy + fz], -1)


def make_ellipsoid(cx, cy, cz, rx, ry, rz, n, y_min=-1.0, y_max=1.0):
    s = fib_sphere(n)
    m = (s[:, 1] >= y_min) & (s[:, 1] <= y_max)
    s = s[m]
    p = np.stack([cx + rx * s[:, 0], cy + ry * s[:, 1], cz + rz * s[:, 2]], 1)
    nrm = unit(np.stack([s[:, 0] / rx, s[:, 1] / ry, s[:, 2] / rz], 1))
    return p, nrm


def make_tube(pts, radii, nu=28, nv=12):
    pts = np.asarray(pts, float)
    t_in = np.linspace(0, 1, len(pts))
    u = np.linspace(0, 1, nu)
    c = np.stack([np.interp(u, t_in, pts[:, k]) for k in range(3)], 1)
    r = np.interp(u, t_in, radii)
    tan = unit(np.gradient(c, axis=0))
    ref = np.where(np.abs(tan[:, 2:3]) < 0.9, [0, 0, 1.0], [1.0, 0, 0])
    b1 = unit(np.cross(tan, ref))
    b2 = unit(np.cross(tan, b1))
    th = np.linspace(0, TAU, nv, endpoint=False)
    cos_t, sin_t = np.cos(th)[None, :, None], np.sin(th)[None, :, None]
    nrm = b1[:, None, :] * cos_t + b2[:, None, :] * sin_t
    p = c[:, None, :] + r[:, None, None] * nrm
    return p.reshape(-1, 3), nrm.reshape(-1, 3)


def build_head_torso():
    pts, nrms, prts, cols = [], [], [], []

    def add_part(p, n, part, col):
        pts.append(p), nrms.append(n)
        prts.append(np.full(len(p), part))
        cols.append(np.tile(col, (len(p), 1)))

    add_part(*make_ellipsoid(0.0, 0.34, 0.0, 0.076, 0.086, 0.074, 900), BODY, SKIN)
    add_part(*make_tube([[0, 0.265, 0], [0, 0.19, 0]], [0.022, 0.026], 10, 10), BODY, SKIN)
    add_part(*make_ellipsoid(0.0, 0.358, -0.014, 0.084, 0.088, 0.082, 850, y_min=-0.12), HAIR, BLONDE)
    add_part(*make_ellipsoid(0.0, 0.485, -0.015, 0.056, 0.048, 0.054, 550), HAIR, BLONDE_HI)
    add_part(*make_tube([[-0.032, 0.432, 0.035], [0.032, 0.432, 0.035], [0.036, 0.432, -0.045],
                         [-0.036, 0.432, -0.045], [-0.032, 0.432, 0.035]], [0.014] * 5, 22, 8),
             DRESS, PALETTES[0, 1])
    add_part(*make_tube([[0, 0.20, 0], [0, 0.155, 0.004]], [0.050, 0.044], 10, 16), BODY, SKIN)

    return np.concatenate(pts), np.concatenate(nrms), np.concatenate(prts), np.concatenate(cols)


HEAD_P, HEAD_N, HEAD_PRT, HEAD_COL = build_head_torso()


def animated_limbs(t):
    leap = float(span(t, T_LEAP))
    ret = float(span(t, T_RETURN))
    hop_energy = (np.sin(np.pi * float(span(t, T_GLIDE1)))
                  + np.sin(np.pi * float(span(t, T_GLIDE2)))
                  + np.sin(np.pi * leap)) * (1.0 - ret)
    wave = 0.065 * np.sin(3.6 * t) * (1.0 - ret)
    kick = (0.075 * np.sin(3.0 * t) + 0.085 * hop_energy) * (1.0 - ret)

    pts, nrms, prts, cols = [], [], [], []

    def add_part(p, n, part, col):
        pts.append(p), nrms.append(n)
        prts.append(np.full(len(p), part))
        cols.append(np.tile(col, (len(p), 1)))

    r_hand = np.array([0.23 + 0.04 * np.cos(2.6 * t), 0.28 + wave + 0.06 * hop_energy, 0.08])
    r_elbow = np.array([0.14, 0.20 + 0.4 * wave, 0.04])
    add_part(*make_tube([[0.052, 0.185, 0.0], r_elbow, r_hand], [0.020, 0.017, 0.014], 20, 10), BODY, SKIN)

    wand_tip = r_hand + np.array([0.15, 0.17 + 0.05 * np.sin(4.4 * t), 0.06])
    add_part(*make_tube([r_hand, wand_tip], [0.008, 0.006], 20, 8), WAND, GOLD)

    l_hand = np.array([-0.22, 0.08 - 0.6 * wave + 0.08 * hop_energy, 0.05])
    l_elbow = np.array([-0.14, 0.13 - 0.3 * wave, 0.03])
    add_part(*make_tube([[-0.052, 0.185, 0.0], l_elbow, l_hand], [0.020, 0.017, 0.014], 20, 10), BODY, SKIN)

    l_foot = np.array([-0.075 - 0.03 * kick, -0.44 + 0.06 * hop_energy, 0.02 - 0.05 * kick])
    l_knee = np.array([-0.045, -0.29 + 0.03 * hop_energy, 0.04])
    add_part(*make_tube([[-0.032, -0.15, 0.0], l_knee, l_foot], [0.028, 0.021, 0.014], 22, 10), BODY, SKIN)

    r_foot = np.array([0.055 + 0.03 * kick, -0.39 + 0.10 * hop_energy, -0.07 - 0.04 * hop_energy])
    r_knee = np.array([0.068, -0.26 + 0.06 * hop_energy, 0.07])
    add_part(*make_tube([[0.032, -0.15, 0.0], r_knee, r_foot], [0.028, 0.021, 0.014], 22, 10), BODY, SKIN)

    add_part(*make_ellipsoid(*(l_foot + [-0.01, -0.02, 0.01]), 0.032, 0.017, 0.020, 160), SHOE, PALETTES[0, 0])
    add_part(*make_ellipsoid(*(r_foot + [0.01, -0.02, 0.01]), 0.032, 0.017, 0.020, 160), SHOE, PALETTES[0, 0])
    add_part(*make_ellipsoid(*(l_foot + [-0.032, -0.01, 0.025]), 0.017, 0.017, 0.017, 90), MARK, WHITE)
    add_part(*make_ellipsoid(*(r_foot + [0.030, -0.01, 0.025]), 0.017, 0.017, 0.017, 90), MARK, WHITE)

    return np.concatenate(pts), np.concatenate(nrms), np.concatenate(prts), np.concatenate(cols), wand_tip


def sheet(na, nr):
    return np.meshgrid(np.linspace(0, 1, na), np.linspace(0, 1, nr), indexing="ij")


STEM_P, STEM_N = make_tube([[0.0, FLOWER_Y, 0.0], [-0.02, FLOWER_Y - 0.16, 0.0], [0.01, FLOWER_Y - 0.34, 0.0]],
                           [0.028, 0.022, 0.018], 20, 12)
FLOWER_CORE_P, FLOWER_CORE_N = make_ellipsoid(0.0, FLOWER_Y + 0.03, 0.0, 0.11, 0.045, 0.11, 260)
PETAL_A, PETAL_R = sheet(18, 22)
PETAL_INK = (PETAL_IN + (PETAL_OUT - PETAL_IN) * smooth(PETAL_R)[..., None]).reshape(-1, 3)


def flower_petal_surface(angle, tier, open_q, t):
    tier_q = smooth((open_q - tier * 0.16) / (1.0 - tier * 0.16))
    breathe = 0.04 * np.sin(1.6 * t + angle) * tier_q
    base_pitch = (0.28, 0.18, 0.10)[tier]
    open_pitch = (1.32, 1.04, 0.76)[tier]
    pitch = base_pitch + (open_pitch - base_pitch + breathe) * tier_q
    length = (0.46, 0.39, 0.31)[tier] * (0.70 + 0.30 * tier_q)
    width = (0.17, 0.15, 0.12)[tier] * np.sin(np.pi * np.clip(PETAL_R, 0.02, 0.98)) ** 0.72
    u = (PETAL_A - 0.5) * 2.0

    s = length * PETAL_R
    curl = 0.08 * (PETAL_R ** 2.4) * tier_q
    cup = 0.055 * (1.0 - u * u) * np.sin(np.pi * PETAL_R)
    rad = 0.045 + s * np.sin(pitch) + curl - cup * np.cos(pitch)
    y = FLOWER_Y + s * np.cos(pitch) - 0.4 * curl + cup * np.sin(pitch)

    ca, sa = np.cos(angle), np.sin(angle)
    x = rad * ca - (u * width) * sa
    z = rad * sa + (u * width) * ca
    return np.stack([x, y, z], -1)


DRESS_A, DRESS_R = sheet(110, 44)
DRESS_INK = np.array([
    (k[0] + (k[1] - k[0]) * smooth(DRESS_R)[..., None]).reshape(-1, 3)
    for k in PALETTES
])


def dress_surface(a, r, t):
    th = a * TAU
    petals = 7
    scallop = 0.84 + 0.16 * np.abs(np.cos(petals * np.pi * a)) ** 0.52
    twirl_flare = 0.10 * np.sin(np.pi * span(t, T_TWIRL)) ** 2
    rad = (0.044 + (0.145 + twirl_flare) * (r ** 1.15) * scallop
           + 0.016 * r * np.sin(petals * th + 2.6 * t))
    y = 0.165 - 0.365 * r * (0.92 + 0.08 * scallop)
    x = rad * np.cos(th)
    z = rad * np.sin(th)
    return np.stack([x, y, z], -1), 0.22 * r


WING_A, WING_R = sheet(86, 46)
WING_INK = np.array([
    np.where(
        (WING_R < 0.5)[..., None],
        k[2] + (k[3] - k[2]) * smooth(WING_R / 0.5)[..., None],
        k[3] + (k[4] - k[3]) * smooth((WING_R - 0.5) / 0.48)[..., None]
    ).reshape(-1, 3)
    for k in PALETTES
])


def wing_surface(side, upper, a, r, t, g):
    flap = 0.30 + 0.32 * np.sin(6.4 * t + (0.0 if upper else 0.55)) * (0.25 + 0.75 * g)
    if upper:
        ang = (0.16 + 0.96 * a) * (0.30 + 0.70 * g)
        shape = np.sin(np.pi * np.clip(0.07 + 0.86 * a, 0, 1)) ** 0.52
        length = 0.62 * shape * g
        y0, z0 = 0.14, -0.045
    else:
        ang = (-0.14 - 0.84 * a) * (0.30 + 0.70 * g)
        shape = np.sin(np.pi * np.clip(0.09 + 0.82 * a, 0, 1)) ** 0.58
        length = 0.38 * shape * g
        y0, z0 = 0.08, -0.050

    reach = length * r
    ripple = 0.040 * (r ** 1.45) * np.sin(6.5 * a - 6.4 * t + (0.0 if upper else 1.4)) * g
    x = side * (0.032 + reach * np.cos(ang) * np.cos(flap))
    y = y0 + reach * np.sin(ang)
    z = z0 - reach * np.cos(ang) * np.sin(flap) + ripple
    return np.stack([x, y, z], -1), 0.18 * r


def glitter_points(grid, seed):
    rng = np.random.default_rng(seed)
    r = grid[-1].ravel()
    at = np.flatnonzero((rng.random(len(r)) < 0.020) & (r > 0.35))
    return at, 2.8 + 3.6 * rng.random(len(at)), rng.random(len(at)) * TAU


WING_GLITTER = [glitter_points((WING_A, WING_R), s) for s in (11, 12, 13, 14)]

EYE_POS, TARGET = np.array([0.0, 0.0, 6.0]), np.array([0.0, 0.0, 0.0])
FWD = unit(TARGET - EYE_POS)
RIGHT = unit(np.cross(FWD, [0, 1.0, 0]))
UP = np.cross(RIGHT, FWD)
BASIS = np.stack([RIGHT, UP, FWD])
EYE_CAM = BASIS @ EYE_POS
ZOOM = 7.4
VIEW = unit(EYE_POS - TARGET)
KEY = unit([-0.45, 0.65, 0.62])
HALF = unit(KEY + VIEW)


def to_cam(p):
    return p @ BASIS.T - EYE_CAM


def project_cam(cam, cols, rows, aspect):
    z = cam[..., 2]
    zz = np.maximum(z, 0.2)
    return (0.5 + cam[..., 0] / zz * ZOOM * 0.5) * cols, (0.5 - cam[..., 1] / zz * ZOOM * 0.5 * aspect) * rows, z


def scene(t, cols, rows, aspect):
    SX, SY, Z, L, RGBs, PRT, G, AREA = [], [], [], [], [], [], [], []
    flares = []

    change = int(np.floor((t - T_MAGIC) / PERIOD))
    old, new = np.clip([change, change + 1], 0, len(PALETTES) - 1)
    wave_at = (t - T_MAGIC - change * PERIOD) * WAVE_SPEED if change >= 0 else -9.0

    def lit(way, inks, lum):
        on = smooth((wave_at - way) / 0.22)[:, None]
        band = 0.85 * np.exp(-((wave_at - way) / 0.07) ** 2)
        rgb = inks[old] + (inks[new] - inks[old]) * on
        return rgb + (WHITE - rgb) * np.clip(band, 0, 1)[:, None] * 0.65, lum + 0.45 * band

    def add(p, lum, rgb, part, glyph, area=None):
        sx, sy, z = project_cam(to_cam(p), cols, rows, aspect)
        SX.append(sx), SY.append(sy), Z.append(z), L.append(lum), RGBs.append(rgb), G.append(glyph)
        PRT.append(part if isinstance(part, np.ndarray) else np.full(len(lum), part))
        AREA.append(np.ones(len(lum)) if area is None else area)

    open_q = float(span(t, T_BLOOM)) * (1.0 - float(span(t, T_CLOSE)))
    add(STEM_P, 0.55 + 0.40 * np.clip(STEM_N @ KEY, 0, 1), np.tile(STEM_COL, (len(STEM_P), 1)), STEM, np.full(len(STEM_P), -1))
    add(FLOWER_CORE_P, (0.90 + 0.35 * np.clip(FLOWER_CORE_N @ KEY, 0, 1)) * (0.4 + 0.6 * open_q),
        np.tile(GOLD, (len(FLOWER_CORE_P), 1)), MARK, np.full(len(FLOWER_CORE_P), C("*")))

    if open_q > 0.20:
        glow_in = float(np.sin(np.pi * np.clip((t - 1.5) / 5.0, 0, 1)))
        glow_out = float(np.sin(np.pi * np.clip((t - 21.5) / 4.5, 0, 1)))
        glow_k = max(glow_in, glow_out)
        if glow_k > 0.05:
            flares.append((np.array([0.0, FLOWER_Y + 0.08, 0.0]), int(2 + 5 * glow_k), glow_k, GOLD, True))

    for tier in range(3):
        for k in range(6):
            ang = k * TAU / 6.0 + tier * (TAU / 18.0)
            p = flower_petal_surface(ang, tier, open_q, t)
            sx, sy, z = project_cam(to_cam(p), cols, rows, aspect)
            n = unit(np.cross(np.gradient(p, axis=0), np.gradient(p, axis=1)))
            n = (n * np.sign(n @ VIEW)[..., None]).reshape(-1, 3)
            lum = 0.42 + 0.62 * np.clip(n @ KEY, 0, 1) ** 0.85 + 0.32 * np.clip(n @ HALF, 0, 1) ** 14
            rgb = PETAL_INK * (0.86 + 0.12 * tier)
            area = np.abs(np.gradient(sx, axis=0) * np.gradient(sy, axis=1) - np.gradient(sx, axis=1) * np.gradient(sy, axis=0))
            SX.append(sx.ravel()), SY.append(sy.ravel()), Z.append(z.ravel()), L.append(lum)
            RGBs.append(rgb), G.append(np.full(len(lum), -1)), PRT.append(np.full(len(lum), FLOWER))
            AREA.append(1.7 * area.ravel() + 0.02)

    if T_LEAP[0] <= t <= T_RETURN[1]:
        lp, ln, lprt, lcol, wand_tip_local = animated_limbs(t)
        bp = np.concatenate([HEAD_P, lp])
        bn = np.concatenate([HEAD_N, ln])
        bprt = np.concatenate([HEAD_PRT, lprt])
        bcol = np.concatenate([HEAD_COL, lcol])

        p = carry(bp, t)
        keep = p[:, 1] >= CLIP_Y
        if keep.any():
            _, _, _, yaw, _ = fairy_state(t)
            cy, sy = np.cos(yaw), np.sin(yaw)
            n0 = bn[keep]
            n = np.stack([n0[:, 0] * cy + n0[:, 2] * sy, n0[:, 1], -n0[:, 0] * sy + n0[:, 2] * cy], -1)
            n = n * np.sign(n @ VIEW)[:, None]
            lum = 0.58 + 0.38 * np.clip(n @ KEY, 0, 1) + 0.50 * np.clip(n @ HALF, 0, 1) ** 18 + 0.26 * (1 - np.abs(n @ VIEW)) ** 2
            add(p[keep], lum, bcol[keep], bprt[keep], np.full(int(keep.sum()), -1))

        def add_sheet(surface, grid, g, part, inks, way_off, way_len, done, rays_n=None, sparkle=None, is_wing=False):
            local, lag = surface
            sp = carry(local, t, lag)
            sx, sy, z = project_cam(to_cam(sp), cols, rows, aspect)
            sn = unit(np.cross(np.gradient(sp, axis=-3), np.gradient(sp, axis=-2)))
            sn = (sn * np.sign(sn @ VIEW)[..., None]).reshape(-1, 3)
            a, r = grid[-2].ravel(), grid[-1].ravel()
            slum = 0.34 + 0.74 * np.clip(sn @ KEY, 0, 1) ** 0.85 + 0.44 * np.clip(sn @ HALF, 0, 1) ** 16 + 0.22 * smooth((r - 0.84) / 0.14)
            srgb, slum = lit(way_off + way_len * g * r, inks, slum)
            srgb = srgb + (WHITE - srgb) * np.clip((slum - 0.92) * 0.85, 0, 0.55)[:, None]
            sglyph = np.full(len(r), -1)
            if rays_n is not None:
                ray = (np.cos(rays_n * TAU * a) > 0.86) & (r > 0.12)
                sglyph[ray] = slope_char(np.gradient(sx, axis=1), -np.gradient(sy, axis=1) / aspect * cols / rows).ravel()[ray]
                slum[ray] = 0.65 + 0.50 * slum[ray]
                srgb[ray] = PALE(srgb[ray], 0.45)
            if sparkle is not None and g >= 1:
                at, speed, phase = sparkle
                on = at[np.sin(t * speed + phase) > 0.92]
                sglyph[on], slum[on], srgb[on] = C("*"), 1.35, WHITE
            if g < 1 and t < T_FOLD[0]:
                tip = (r > 0.96) & (np.arange(len(r)) // grid[-1].shape[-1] % 3 == 0)
                sglyph[tip], slum[tip] = C("*"), 1.3
                srgb = np.where(tip[:, None], GOLD, srgb)
            whole = float(np.clip(1 - (t - done) / FLASH, 0, 1) ** 2) if t >= done else 0.0
            if whole > 0.05:
                srgb, slum = srgb + (WHITE - srgb) * 0.6 * whole, slum + 0.35 * whole
            area = np.abs(np.gradient(sx, axis=-2) * np.gradient(sy, axis=-1) - np.gradient(sx, axis=-1) * np.gradient(sy, axis=-2))
            skeep = sp[..., 1].ravel() >= CLIP_Y
            if not skeep.any():
                return
            area_f = np.where(sglyph >= 0, 1.0, (1.45 if is_wing else 1.8) * area.ravel() + 0.02)
            SX.append(sx.ravel()[skeep]), SY.append(sy.ravel()[skeep]), Z.append(z.ravel()[skeep])
            L.append(slum[skeep]), RGBs.append(srgb[skeep]), G.append(sglyph[skeep])
            PRT.append(np.full(int(skeep.sum()), part))
            AREA.append(area_f[skeep])

        add_sheet(dress_surface(DRESS_A, DRESS_R, t), (DRESS_A, DRESS_R), 1.0, DRESS, DRESS_INK, 0.15, 0.45, T_LEAP[1])

        gw = float(span(t, T_WINGS)) * (1.0 - float(span(t, T_FOLD)))
        if gw > 0.01:
            idx = 0
            for side in (-1, 1):
                add_sheet(wing_surface(side, True, WING_A, WING_R, t, gw), (WING_A, WING_R), gw, WING_U, WING_INK,
                          0.25, 0.65, T_WINGS[1], rays_n=6, sparkle=WING_GLITTER[idx], is_wing=True)
                idx += 1
                add_sheet(wing_surface(side, False, WING_A, WING_R, t, gw), (WING_A, WING_R), gw, WING_L, WING_INK,
                          0.25, 0.45, T_WINGS[1], rays_n=5, sparkle=WING_GLITTER[idx], is_wing=True)
                idx += 1

        wand_tip_world = carry(wand_tip_local, t)
        if wand_tip_world[1] > CLIP_Y + 0.04:
            pulse = 0.78 + 0.28 * np.sin(5.5 * t) + 0.35 * float(beat(t))
            flares.append((wand_tip_world, int(3 + 3 * pulse), min(1.3, pulse), GOLD, True))

    if not SX:
        return [np.empty(0) for _ in range(8)], flares
    return [np.concatenate(x) for x in (SX, SY, Z, L, RGBs, PRT, G, AREA)], flares


_HASH = {}


def HASH(rows, cols):
    if (rows, cols) not in _HASH:
        r, c = np.mgrid[0:rows, 0:cols]
        _HASH[rows, cols] = (r * 7919 + c * 104729) % 9973
    return _HASH[rows, cols]


def bodies(sx, sy, z, lum, rgb, part, glyph, area, cols, rows, t):
    if len(sx) == 0:
        return np.zeros((rows, cols), int), np.zeros((rows, cols, 3)), np.full((rows, cols), np.inf)
    ok = np.flatnonzero((sx >= 0) & (sx < cols) & (sy >= 0) & (sy < rows) & (z > 0.3))
    cell = sy[ok].astype(int) * cols + sx[ok].astype(int)
    cover = np.clip(np.bincount(cell, weights=area[ok], minlength=rows * cols), 0, 1).reshape(rows, cols)
    order = np.argsort(-z[ok])
    gi = np.full(rows * cols, -1)
    gi[cell[order]] = ok[order]
    gi = gi.reshape(rows, cols)
    body = gi >= 0
    g = np.maximum(gi, 0)
    prt = np.where(body, part[g], -1)
    dep = np.where(body, z[g], np.inf)
    own = np.where(body, glyph[g], -1)
    solid = body & (own < 0)
    pp, pd = np.pad(prt, 1, constant_values=-1), np.pad(dep, 1, constant_values=np.inf)
    edge = np.zeros_like(body)
    gx, gy = np.zeros((rows, cols)), np.zeros((rows, cols))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            nb, nz = pp[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx], pd[1 + dy:rows + 1 + dy, 1 + dx:cols + 1 + dx]
            other = (nb >= 0) & (nb != prt)
            seam = HARD[np.maximum(prt, 0)] & other & HARD[np.maximum(nb, 0)] & (prt < nb)
            out = solid & ((nb < 0) | (other & (nz > dep + 0.035)) | seam)
            gx += dx * out
            gy += dy * out
            if dx == 0 or dy == 0:
                edge |= out
    h = HASH(rows, cols)
    L = np.where(body, lum[g], 0.0)
    level = np.clip(((L - 0.42) * 4.6).astype(int), 0, 3)
    inside = FILL[level, (h + (t * 4 + h % 11).astype(int)) % 12]
    char = np.where(body, np.where(own >= 0, own, np.where(edge, outline_letter(gx, gy), inside)), 0)
    bright = np.where(own >= 0, L, np.where(edge, np.maximum(0.85, L), np.clip(0.45 + 0.55 * L / 0.9, 0.45, 1.0)))
    bright = bright * np.where(own >= 0, 1.0, 0.30 + 0.70 * cover ** 0.7)
    col = np.where(body[..., None], rgb[g] * np.minimum(bright, 1.4)[..., None], 0.0)
    return char, col, dep


def put(char, col, y, x, ch, rgb, k):
    if 0 <= y < char.shape[0] and 0 <= x < char.shape[1]:
        char[y, x], col[y, x] = C(ch), np.asarray(rgb) * k


def rays(char, col, cy, cx, reach, rgb, strength=1.0):
    rows, cols = char.shape
    for dist in range(1, reach + 1):
        fade = (1 - dist / (reach + 1)) * strength
        arms = [(0, 1, "-"), (0, -1, "-"), (1, 0, "|"), (-1, 0, "|")]
        if dist <= reach // 2:
            arms += [(1, 1, "\\"), (-1, -1, "\\"), (1, -1, "/"), (-1, 1, "/")]
        for dy, dx, ch in arms:
            yy, xx = cy + dy * dist, cx + dx * dist * (2 if dy == 0 else 1)
            k = fade * (0.7 if dx and dy else 1.0)
            if 0 <= yy < rows and 0 <= xx < cols and col[yy, xx].max() < k:
                char[yy, xx], col[yy, xx] = C(ch), rgb * k
    put(char, col, cy, cx, "*", rgb, 1.3 * strength)


def dots(char, col, dep, p, glyph, rgb, k, cols, rows, aspect):
    sx, sy, z = project_cam(to_cam(p), cols, rows, aspect)
    ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
    ok = np.flatnonzero((ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (k > 0.05))
    ok = ok[z[ok] < dep[iy[ok], ix[ok]]]
    ok = ok[np.argsort(k[ok])]
    char[iy[ok], ix[ok]] = glyph[ok]
    col[iy[ok], ix[ok]] = rgb[ok] * k[ok, None]


TRAIL_N = 190
TRAIL_RNG = np.random.default_rng(19).random((TRAIL_N, 4))


def wand_tip_at(t):
    leap = float(span(t, T_LEAP))
    ret = float(span(t, T_RETURN))
    hop_energy = (np.sin(np.pi * float(span(t, T_GLIDE1)))
                  + np.sin(np.pi * float(span(t, T_GLIDE2)))
                  + np.sin(np.pi * leap)) * (1.0 - ret)
    wave = 0.065 * np.sin(3.6 * t) * (1.0 - ret)
    r_hand = np.array([0.23 + 0.04 * np.cos(2.6 * t), 0.28 + wave + 0.06 * hop_energy, 0.08])
    return carry(r_hand + np.array([0.15, 0.17 + 0.05 * np.sin(4.4 * t), 0.06]), t)


def wand_dust(t):
    if t < T_LEAP[0] + 0.6:
        return []
    ages = np.linspace(0.015, 3.4, TRAIL_N)
    t0 = t - ages
    live = (t0 > T_LEAP[0] + 0.5) & (t0 < T_RETURN[1] - 0.6)
    if not live.any():
        return []
    ages, t0, r = ages[live], t0[live], TRAIL_RNG[live]
    p = np.stack([wand_tip_at(x) for x in t0])
    above = p[:, 1] > CLIP_Y
    if not above.any():
        return []
    p, ages, r = p[above], ages[above], r[above]
    spread = 0.03 + 0.06 * ages
    p[:, 0] += spread * np.sin(4.0 * ages + r[:, 0] * TAU) + (r[:, 3] - 0.5) * 0.05 * ages
    p[:, 1] -= 0.065 * ages + 0.025 * ages * ages
    p[:, 2] += spread * np.cos(4.0 * ages + r[:, 1] * TAU)
    tw = 0.58 + 0.42 * np.sin(t * 8.0 + r[:, 2] * 30.0)
    fade = (1.0 - ages / 3.4) ** 0.80 * tw * 1.18
    glyph = np.where(ages < 1.0, C("*"), np.where(ages < 2.2, C("+"), C(".")))
    rgb = GOLD + (WHITE - GOLD) * np.clip(1 - ages / 0.9, 0, 1)[:, None]
    return [(p, glyph, rgb, fade)]


DRAG, TAILS, TAIL_GAP = 1.6, 5, 0.035


def make_bursts():
    rng = np.random.default_rng(22)
    out = []
    for tb in T_FINALE:
        n, t0 = BURST_SPARKS, tb + 0.2
        centre = wand_tip_at(t0)
        way = fib_sphere(n)[rng.permutation(n)] * [1, 1, 0.55]
        way[:, 2] = -np.abs(way[:, 2])
        way = unit(way)
        vel = way * (BURST_SPEED * (0.45 + 0.55 * rng.random(n)))[:, None]
        out.append((t0, centre + 0.15 * way, vel, SPARK_INK[rng.integers(0, len(SPARK_INK), n)],
                    1.5 + 0.8 * rng.random(n), rng.random(n) * TAU, centre))
    return out


BURSTS = make_bursts()


def sparks(t):
    out = []
    for t0, start, vel, ink, life, seed, centre in BURSTS:
        if not 0 <= t - t0 < 2.4:
            continue

        def at(age):
            p = start + vel * (1 - np.exp(-DRAG * max(age, 0.0))) / DRAG
            p[:, 1] -= 0.07 * age * age
            return p

        age = t - t0
        head, back = to_cam(at(age)), to_cam(at(age - TAIL_GAP))
        stroke_ = slope_char(head[:, 0] / head[:, 2] - back[:, 0] / back[:, 2],
                             head[:, 1] / head[:, 2] - back[:, 1] / back[:, 2])
        dying = age > life - 0.6
        flick = np.where(dying, np.sin(age * 38 + seed) > -0.2, True)
        fade = np.clip((life - age) / 0.5, 0, 1) * flick
        rgb = ink + (WHITE - ink) * max(0.0, 1 - age / 0.3)
        for j in range(TAILS, 0, -1):
            if age - TAIL_GAP * j > 0:
                out.append((at(age - TAIL_GAP * j), np.where(dying, C("."), stroke_), rgb, fade * (0.85 - 0.14 * j)))
        out.append((at(age), np.where(dying, C("+"), C("*")), rgb, fade * 1.3))
    return out


N_STARS = 90
STAR_AT = np.random.default_rng(5).random((N_STARS, 5))
STAR_GLYPH = np.array([C("."), C("."), C("."), C("+"), C("*")])


def frame(t, cols, rows, aspect):
    pts, flares = scene(t, cols, rows, aspect)
    char, col, dep = bodies(*pts, cols, rows, t)
    free = char == 0

    size = STAR_AT[:, 4]
    ix = ((STAR_AT[:, 0] + 0.008 * np.sin(t * (0.8 + 1.5 * STAR_AT[:, 2]) + STAR_AT[:, 3] * 40)) % 1.0 * cols).astype(int)
    iy = (((STAR_AT[:, 1] - t * (0.012 + 0.03 * size)) % 1.0) * rows).astype(int)
    ok = free[iy, ix]
    tw = 0.55 + 0.45 * np.sin(t * (1.2 + 2.8 * STAR_AT[:, 2]) + STAR_AT[:, 3] * 40)
    char[iy[ok], ix[ok]] = STAR_GLYPH[np.clip((size * 5).astype(int), 0, 4)][ok]
    col[iy[ok], ix[ok]] = DUST_COL * ((0.16 + 0.42 * size) * tw)[ok][:, None]

    for p, glyph, rgb, k in wand_dust(t) + sparks(t):
        dots(char, col, dep, p, glyph, rgb, k, cols, rows, aspect)

    for t0, start, vel, ink, life, seed, centre in BURSTS:
        pop = float(np.clip(1 - (t - t0) / 0.5, 0, 1)) if t >= t0 else 0.0
        if pop > 0.05:
            flares.append((centre + [0, 0.05, 0.2], int(3 + 7 * pop), pop, WHITE, True))

    for p, reach, strength, rgb, always in flares:
        sx, sy, z = project_cam(to_cam(np.asarray(p, float)[None]), cols, rows, aspect)
        y, x = int(sy[0]), int(sx[0])
        if 0 <= y < rows and 0 <= x < cols and (always or z[0] <= dep[y, x] + 0.08):
            rays(char, col, y, x, reach, rgb, strength)

    return char, col


TITLE = "ASCII Tinkerbell"
CW, CH, FONT_PX = 7, 10, 11
COLS, ROWS = 113, 103
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
TRAIL = 0.50


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = cols * cw, rows * ch
        font = pygame.font.SysFont(MONO, font_px)
        atlas = []
        for code in range(32, 127):
            s = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            atlas.append(pygame.surfarray.array3d(s).transpose(1, 0, 2))
        self.atlas = np.stack(atlas)
        self.art = pygame.Surface((self.w, self.h))
        self.trail = pygame.Surface((self.w, self.h))
        self.out = pygame.Surface((self.w, self.h))
        self.last_t = None

    @staticmethod
    def blur(src, size, radius):
        small = pygame.transform.smoothscale(src, size)
        if hasattr(pygame.transform, "gaussian_blur"):
            small = pygame.transform.gaussian_blur(small, max(1, radius))
        return small

    def glow(self, src):
        w, h = self.w, self.h
        tight = self.blur(src, (w // 4, h // 4), 2)
        wide = self.blur(tight, (w // 8, h // 8), 3)
        for layer, amount in ((tight, 0.78), (wide, 0.48)):
            layer = pygame.transform.smoothscale(layer, (w, h))
            layer.fill((int(255 * amount),) * 3, special_flags=pygame.BLEND_MULT)
            self.out.blit(layer, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw(self, t):
        w, h = self.w, self.h
        char, col = frame(t, self.cols, self.rows, w / h)
        pygame.surfarray.blit_array(self.art, self.atlas[char].transpose(1, 3, 0, 2, 4).reshape(w, h, 3))
        tint = pygame.surfarray.make_surface((np.clip(col, 0, 1) * 255).astype(np.uint8).transpose(1, 0, 2))
        self.art.blit(pygame.transform.scale(tint, (w, h)), (0, 0), special_flags=pygame.BLEND_MULT)
        if self.last_t is None or t < self.last_t:
            self.trail.fill((0, 0, 0))
        self.last_t = t
        self.trail.fill((int(TRAIL * 255),) * 3, special_flags=pygame.BLEND_MULT)
        self.trail.blit(self.art, (0, 0), special_flags=pygame.BLEND_MAX)
        self.out.fill((0, 0, 0))
        self.out.blit(self.trail, (0, 0))
        self.glow(self.out)
        return self.out


def window_size():
    info = pygame.display.Info()
    k = 1.0
    if info.current_w > 0 and info.current_h > 0:
        k = min(1.0, 0.88 * info.current_h / H, 0.95 * info.current_w / W)
    return int(W * k), int(H * k)


def main():
    pygame.init()
    size = window_size()
    window = pygame.display.set_mode(size)
    pygame.display.set_caption(TITLE)
    renderer, clock = Renderer(), pygame.time.Clock()
    t, paused = 0.0, False
    screen = renderer.draw(t)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return 0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                paused = not paused
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                t = 0.0
            if e.type == pygame.KEYDOWN and e.key == pygame.K_s:
                pygame.image.save(screen, str(Path(__file__).with_name(f"tinkerbell_{int(time.time())}.png")))
        dt = clock.tick(30) / 1000
        if not paused:
            t += min(dt, 1 / 15)
            if t > LOOP:
                t = 0.0
            screen = renderer.draw(t)
        window.blit(screen if size == (W, H) else pygame.transform.smoothscale(screen, size), (0, 0))
        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())