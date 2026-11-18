"""Work experience: twelve embroidered merit patches on a khaki twill sash panel hung from a brass rail (order R5).
Blender --background --python tools/blender/hd/patches.py -- [--render] [--export] [--check] [--size N] [--samples N]

Nodes: patches > stand, sash, patch_*. Each patch's origin is its centre on the cloth, its face along the node's
local -Y in Blender (+Z in glTF); the cloth folds softly between the patch columns, so each column leans a few degrees."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bp_web import *  # noqa: F401,F403

NAVY, GOLD, CREAM = (0.018, 0.032, 0.085), (0.72, 0.48, 0.10), (0.84, 0.78, 0.62)
GREEN, ORANGE, WHITE = (0.025, 0.11, 0.045), (0.78, 0.27, 0.04), (0.86, 0.85, 0.80)
RED, WINE, SKY = (0.55, 0.025, 0.03), (0.17, 0.018, 0.03), (0.22, 0.42, 0.74)
KHAKI = (0.36, 0.31, 0.21)
CY = 5.0  # icon centre, mm above the patch centre

# name: (ground, border, label colour, label, icon parts). Part: (shape, args..., colour, height_mm, thread angle in degrees)
PATCHES = {
    'patch_sharepoint': (NAVY, GOLD, CREAM, 'SharePoint', [
        ('rect', -4, CY + 3.5, 15, 10, 0, SKY, 0.45, 20), ('rect', 0, CY, 15, 10, 0, CREAM, 0.6, 90), ('rect', 4, CY - 3.5, 15, 10, 0, GOLD, 0.75, 160),
        ('rect', 4, CY - 2, 9, 1.4, 0, NAVY, 0.95, 0), ('rect', 4, CY - 5, 9, 1.4, 0, NAVY, 0.95, 0)]),
    'patch_requirements': (NAVY, GOLD, CREAM, 'Requirements', [
        ('rect', 0, CY, 15, 19, 0, CREAM, 0.5, 90), ('rect', 0, CY + 9.5, 7, 3.2, 0, GOLD, 0.8, 0),
        ('rect', 1.2, CY + 4, 8, 1.5, 0, NAVY, 0.75, 0), ('rect', 1.2, CY, 8, 1.5, 0, NAVY, 0.75, 0), ('rect', 1.2, CY - 4, 8, 1.5, 0, NAVY, 0.75, 0),
        ('circle', -4.6, CY + 4, 0.95, GOLD, 0.8, 0), ('circle', -4.6, CY, 0.95, GOLD, 0.8, 0), ('circle', -4.6, CY - 4, 0.95, GOLD, 0.8, 0)]),
    'patch_permissions': (NAVY, GOLD, CREAM, 'Protection B', [
        ('poly', [(-8.5, CY + 9), (8.5, CY + 9), (8.5, CY - 0.5), (0, CY - 10), (-8.5, CY - 0.5)], CREAM, 0.5, 90),
        ('poly', [(-6.3, CY + 6.8), (6.3, CY + 6.8), (6.3, CY + 0.2), (0, CY - 7), (-6.3, CY + 0.2)], SKY, 0.7, 30),
        ('text', 'B', 8.5, 0, CY + 1.0, CREAM, 0.95)]),
    'patch_powerbi': (NAVY, GOLD, CREAM, 'Power BI', [
        ('rect', -6, CY - 2.5, 4.2, 7, 0, CREAM, 0.55, 90), ('rect', 0, CY, 4.2, 12, 0, GOLD, 0.65, 90), ('rect', 6, CY + 2.5, 4.2, 17, 0, CREAM, 0.75, 90),
        ('rect', 0, CY - 7.2, 19, 1.3, 0, CREAM, 0.5, 0)]),
    'patch_powerapps': (NAVY, GOLD, CREAM, 'Power Apps', [
        ('rect', -4.3, CY + 4.3, 7.4, 7.4, 0, CREAM, 0.6, 45), ('rect', 4.3, CY + 4.3, 7.4, 7.4, 0, SKY, 0.6, 135),
        ('rect', -4.3, CY - 4.3, 7.4, 7.4, 0, GOLD, 0.6, 135), ('rect', 4.3, CY - 4.3, 7.4, 7.4, 0, CREAM, 0.6, 45)]),
    'patch_automate': (NAVY, GOLD, CREAM, 'Power\nAutomate', [
        ('poly', [(-9.5, CY - 4.5), (-6.3, CY - 4.5), (-2.6, CY + 2), (-6.3, CY + 8.5), (-9.5, CY + 8.5), (-5.8, CY + 2)], SKY, 0.55, 60),
        ('poly', [(-3.2, CY - 4.5), (0, CY - 4.5), (3.7, CY + 2), (0, CY + 8.5), (-3.2, CY + 8.5), (0.5, CY + 2)], CREAM, 0.65, 60),
        ('poly', [(3.1, CY - 4.5), (6.3, CY - 4.5), (10, CY + 2), (6.3, CY + 8.5), (3.1, CY + 8.5), (6.8, CY + 2)], GOLD, 0.75, 60)]),
    'patch_sops': (NAVY, GOLD, CREAM, 'SOPs', [
        ('circle', -6.5, CY + 5.5, 1.5, GOLD, 0.7, 0), ('rect', 2, CY + 5.5, 11, 2.0, 0, CREAM, 0.6, 0),
        ('circle', -6.5, CY, 1.5, GOLD, 0.7, 0), ('rect', 2, CY, 11, 2.0, 0, CREAM, 0.6, 0),
        ('circle', -6.5, CY - 5.5, 1.5, GOLD, 0.7, 0), ('rect', 0.5, CY - 5.5, 8, 2.0, 0, CREAM, 0.6, 0)]),
    'patch_counter': (WINE, CREAM, CREAM, 'Meat counter', [
        ('rect', -1.5, CY + 0.5, 14.5, 9.5, 0, CREAM, 0.6, 15), ('rect', 9.2, CY + 3.2, 8.2, 2.8, 0, GOLD, 0.75, 0),
        ('circle', -6.2, CY + 3.2, 1.0, WINE, 0.85, 0), ('rect', -1.5, CY - 6.5, 16, 1.4, 0, GOLD, 0.5, 0)]),
    'patch_firstaid': (WHITE, RED, RED, 'First Aid,\nCPR C', [
        ('rect', 0, CY + 2.5, 5.0, 14.5, 0, RED, 0.65, 90), ('rect', 0, CY + 2.5, 14.5, 5.0, 0, RED, 0.65, 0)]),
}
for year, sun in (('2023', ORANGE), ('2024', GOLD), ('2025', SKY)):
    PATCHES['patch_camp_' + year] = (GREEN, ORANGE, CREAM, 'Camp ' + year, [
        ('circle', 7.2, CY + 6.6, 2.7, sun, 0.5, 0),
        ('poly', [(-9.5, CY - 6), (0, CY + 8), (9.5, CY - 6)], CREAM, 0.6, 65),
        ('poly', [(-2.7, CY - 6), (0, CY + 0.8), (2.7, CY - 6)], GREEN, 0.85, 90),
        ('rect', 0, CY - 7.3, 23, 1.3, 0, ORANGE, 0.5, 0)])
ORDER = ['patch_sharepoint', 'patch_requirements', 'patch_permissions', 'patch_powerbi',
         'patch_powerapps', 'patch_automate', 'patch_sops', 'patch_counter',
         'patch_camp_2023', 'patch_camp_2024', 'patch_camp_2025', 'patch_firstaid']
FRAME, PX = 58.0, 1024           # patch capture frame (mm) and base-colour pixels
RIM_R, RIM_T, RIM_Z = 25.9, 1.6, 1.3   # merrowed rim: ring radius, thread roll radius, height of its centre (mm)

# Sash panel, mm: width, front height, rail wrap radius, back flap, height of the bottom hem above the floor, cloth thickness.
W, HF, RR, FLAP, ZB, T = 312.0, 244.0, 4.3, 20.0, 18.0, 1.6
LEN = HF + math.pi * RR + FLAP
COLS, ROWS = (-99.0, -33.0, 33.0, 99.0), (214.0, 148.0, 82.0)
LEAN = (0.16, -0.12, 0.13, -0.17)    # depth slope of the cloth under each patch column


def author_patch(name):
    """High-detail embroidery, flat on the floor, photographed into textures."""
    ground, border, ink_c, text, parts = PATCHES[name]
    objs = [slab(name + '_ground', pts_circle(0, 0, 26.2, 96), 0.0, thread(name + '_twill', ground, math.radians(45), 3300, 0.55, dark=0.78))]
    rim = lathe(name + '_rim', [((RIM_R - RIM_T - 0.2) * MM, 0.05 * MM), ((RIM_R + RIM_T + 0.2) * MM, 0.05 * MM)], 160)
    objs.append(assign(rim, thread(name + '_merrow', border, relief=1.0, radial=230, dark=0.55)))
    inner = lathe(name + '_run', [((22.9 + 0.32 * math.cos(a)) * MM, (0.2 + 0.32 * math.sin(a)) * MM) for a in [math.tau * i / 10 for i in range(11)]], 128)
    objs.append(assign(inner, thread(name + '_runstitch', ink_c, relief=0.8, radial=64, dark=0.35)))
    for i, part in enumerate(parts):
        kind = part[0]
        if kind == 'text':
            _, body, size, x, y, col, h = part
            objs.append(label(f'{name}_t{i}', body, size, x, y, thread(f'{name}_tm{i}', col, math.radians(90), 2600, 1.0), z_mm=0.55, height_mm=0.4))
            continue
        if kind == 'rect':
            pts, (col, h, ang) = pts_rect(part[1], part[2], part[3], part[4], math.radians(part[5])), part[6:]
        elif kind == 'circle':
            pts, (col, h, ang) = pts_circle(part[1], part[2], part[3]), part[4:]
        else:
            pts, (col, h, ang) = part[1], part[2:]
        objs.append(slab(f'{name}_p{i}', pts, h, thread(f'{name}_pm{i}', col, math.radians(ang), 2300, 1.0, dark=0.66), bev_mm=0.2))
    two = '\n' in text
    size = 4.2 if two else min(4.9, 41.0 / (len(text) * 0.74))
    objs.append(label(name + '_label', text, size, 0, -12.4 if two else -13.2, thread(name + '_lm', ink_c, math.radians(90), 3000, 0.9, dark=0.7), height_mm=0.38))
    return capture(objs, FRAME, FRAME, PX, PX, os.path.join(TEX, name), normal_pct=50)


def patch_mesh(name, tex):
    """A stiff disc with the merrowed edge as a real rolled rim."""
    a0, a1 = math.radians(172), -math.asin(RIM_Z / RIM_T)
    arc = [(RIM_R + RIM_T * math.cos(a), RIM_Z + RIM_T * math.sin(a)) for a in [a0 + (a1 - a0) * i / 9 for i in range(10)]]
    prof = [(0, arc[0][1]), (RIM_R - RIM_T - 2.0, arc[0][1])] + arc + [(0, 0)]
    ob = lathe(name, [(r * MM, z * MM) for r, z in prof], 60)
    planar_uv(ob.data, FRAME, FRAME)
    stand_up(ob.data)
    assign(ob, web_material(name, tex, rough=0.78, sheen=0.35, normal_strength=1.7))
    return ob


# --- the cloth -----------------------------------------------------------------------------------------------------
def _smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def _slope(x):
    if x < COLS[0] - 27.5:
        return LEAN[0] + 0.32 * ((COLS[0] - 27.5 - x) / 28) ** 2
    if x > COLS[3] + 27.5:
        return LEAN[3] - 0.32 * ((x - COLS[3] - 29) / 28) ** 2
    for i in range(3):
        if x <= COLS[i] + 27.5:
            return LEAN[i]
        if x < COLS[i + 1] - 27.5:
            return LEAN[i] + (LEAN[i + 1] - LEAN[i]) * _smooth(COLS[i] + 27.5, COLS[i + 1] - 27.5, x)
    return LEAN[3]


_STEP = 0.25
_FOLD = [0.0]
for _i in range(int(W / _STEP)):
    _FOLD.append(_FOLD[-1] + _slope(-W / 2 + (_i + 0.5) * _STEP) * _STEP)
_MID = _FOLD[len(_FOLD) // 2]


def fold(x):
    f = min(max((x + W / 2) / _STEP, 0.0), len(_FOLD) - 1.001)
    i = int(f)
    return _FOLD[i] + (_FOLD[i + 1] - _FOLD[i]) * (f - i) - _MID


def cloth(u, s):
    """Centre of the cloth at u across and s up from the bottom hem, in mm (rail centre at y = 0)."""
    top = ZB + HF
    if s <= HF:
        amp = min(max((HF - s) / 200.0, 0.0), 1.0)
        curl = 0.0075 * max(0.0, 26.0 - s) ** 2 * (0.65 + 0.35 * math.sin(u / 47.0 + 1.0))
        return Vector((u, -RR + amp * fold(u) - curl, ZB + s))
    if s <= HF + math.pi * RR:
        p = (s - HF) / RR
        return Vector((u, -RR * math.cos(p), top + RR * math.sin(p)))
    d = s - HF - math.pi * RR
    return Vector((u, RR - 0.1 * d, top - d))


def frame(u, s, d=0.5):
    u0, u1, s0, s1 = max(u - d, -W / 2), min(u + d, W / 2), max(s - d, 0.0), min(s + d, LEN)
    tu = (cloth(u1, s) - cloth(u0, s)).normalized()
    tv = (cloth(u, s1) - cloth(u, s0)).normalized()
    n = tu.cross(tv).normalized()
    return tu, n.cross(tu).normalized(), n


def sash_mesh(tex):
    us = [-W / 2 + W * i / 76 for i in range(77)]
    ss = [HF * j / 44 for j in range(45)] + [HF + math.pi * RR * j / 7 for j in range(1, 8)] + [HF + math.pi * RR + FLAP * j / 3 for j in range(1, 4)]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    front, back, coord = [], [], {}
    for s in ss:
        rf, rb = [], []
        for u in us:
            c = cloth(u, s)
            n = frame(u, s)[2]
            hem = max(_smooth(W / 2 - 14.5, W / 2 - 11.5, abs(u)), _smooth(14.5, 11.5, s)) if s <= HF else 0.0
            for row, off in ((rf, T / 2 * (1 + 0.6 * hem)), (rb, -T / 2)):
                v = bm.verts.new((c + n * off) * MM)
                coord[v] = (u / W + 0.5, s / LEN)
                row.append(v)
        front.append(rf); back.append(rb)
    nj, ni = len(ss), len(us)
    for j in range(nj - 1):
        for i in range(ni - 1):
            bm.faces.new((front[j][i], front[j][i + 1], front[j + 1][i + 1], front[j + 1][i]))
            bm.faces.new((back[j][i], back[j + 1][i], back[j + 1][i + 1], back[j][i + 1]))
        for i in (0, ni - 1):
            bm.faces.new((front[j][i], front[j + 1][i], back[j + 1][i], back[j][i]))
    for i in range(ni - 1):
        for j in (0, nj - 1):
            bm.faces.new((front[j][i], front[j][i + 1], back[j][i + 1], back[j][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        for loop in f.loops:
            loop[uv].uv = coord[loop.vert]
    ob = mesh_object('sash', bm)
    assign(ob, web_material('sash', tex, rough=0.9, sheen=0.25, normal_strength=1.5))
    return ob


def author_sash():
    twill = thread('sash_twill', KHAKI, math.radians(62), 900, 1.0, dark=0.74)
    stitch = thread('sash_stitch', (0.78, 0.71, 0.54), math.radians(90), 3000, 1.0, dark=0.6)
    y0 = -LEN / 2
    objs = [slab('sash_ground', pts_rect(0, 0, W + 2, LEN + 2), 0.0, twill)]
    for x in (-W / 2 + 6, W / 2 - 6):   # folded hems read as a second layer
        objs.append(slab('sash_hem', pts_rect(x, y0 + HF / 2, 13.0, HF), 0.35, twill, bev_mm=0.3))
    objs.append(slab('sash_hem', pts_rect(0, y0 + 6, W - 26, 13.0), 0.35, twill, bev_mm=0.3))
    objs.append(slab('sash_sleeve', pts_rect(0, y0 + HF - 5 + 20, W + 2, 30.0), 0.3, twill, bev_mm=0.3))
    x = -W / 2 + 5
    while x < W / 2 - 5:
        for y in (y0 + 10.0, y0 + HF - 9.0):
            objs.append(slab('st', pts_rect(x, y, 3.2, 0.75), 0.4, stitch, bev_mm=0.16))
        x += 4.9
    y = y0 + 14.0
    while y < y0 + HF - 12:
        for x2 in (-W / 2 + 10, W / 2 - 10):
            objs.append(slab('st', pts_rect(x2, y, 0.75, 3.2), 0.4, stitch, bev_mm=0.16))
        y += 4.9
    return capture(objs, W, LEN, 2048, round(2048 * LEN / W), os.path.join(TEX, 'sash'), normal_pct=50)


def build():
    root = link(bpy.data.objects.new('patches', None))
    gold = brass()
    top = (ZB + HF) * MM

    # Stand: a slim rail through the sash sleeve, on two posts with weighted feet.
    px = (W / 2 + 16) * MM
    parts = [tube('rail', [Vector((x, 0, top)) for x in (-px, -px / 2, 0, px / 2, px)], 3.4 * MM, 24)]
    for sx in (-1, 1):
        foot = lathe('foot', [(r * MM, z * MM) for r, z in ((0, 0), (29, 0), (30, 1.0), (30, 4.6), (28.4, 6.6), (9, 7.6), (6.2, 10.5), (4.6, 11.2), (0, 11.2))], 72)
        foot.data.transform(Matrix.Translation((sx * px, 0, 0)))
        bevel(foot, 0.5 * MM, 3)
        parts += [foot, tube('post', [Vector((sx * px, 0, z * MM)) for z in (10, 90, 180, (ZB + HF) + 5)], 3.2 * MM, 20),
                  ball('finial', (sx * px, 0, top + 8.5 * MM), 5.6 * MM)]
    for o in parts:
        assign(o, gold)
    group('stand', (0, 0, 0), parts, root)

    group('sash', (0, 0, top), [sash_mesh(author_sash())], root)

    for i, name in enumerate(ORDER):
        u, s = COLS[i % 4], ROWS[i // 4] - ZB
        tu, tv, n = frame(u, s, 6.0)
        pos = (cloth(u, s) + n * (T / 2 - 0.15)) * MM
        m = Matrix((( tu.x, -n.x, tv.x, pos.x), (tu.y, -n.y, tv.y, pos.y), (tu.z, -n.z, tv.z, pos.z), (0, 0, 0, 1)))
        pivot(name, None, patch_mesh(name, author_patch(name)), root, matrix=m)
        print(f'[web] {name}: glTF position ({pos.x:.4f}, {pos.z:.4f}, {-pos.y:.4f}) normal ({n.x:.3f}, {n.z:.3f}, {-n.y:.3f})')
    return root


VIEW = dict(azimuth=-22, elevation=8, lens=85, distance=1.22)
FOCUS, RADIUS = (0, 0, 0.14), 0.2


def main():
    if '--check' in ARGS:
        check('patches', FOCUS, RADIUS, **VIEW)
        return
    scene = reset()
    root = build()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'patches.blend'))
    if '--export' in ARGS:
        export('patches', root)
    if '--render' in ARGS:
        studio(scene, FOCUS, RADIUS, **VIEW)
        render(scene, os.path.join(OUT, 'patches.png'), arg('--size', 1400), arg('--samples', 256))


main()
