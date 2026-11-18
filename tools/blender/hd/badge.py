"""Work experience: three printed ID badges on one woven lanyard with a swivel clip, draped over a brass desk stand (order R5).
Blender --background --python tools/blender/hd/badge.py -- [--render] [--export] [--check] [--size N] [--samples N]

Nodes: badge > stand, lanyard, clip, badge_dnd, badge_camp, badge_food. Each badge pivots at its slot. The strap
carries a second UV set: x = 0 at the bar to 1 at the far end of that run, y = 0 for the front run (bar to clip),
1 for the loop hanging behind."""
import bpy, bmesh, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bp_web import *  # noqa: F401,F403

CW, CH, CT = 54.0, 86.0, 0.76          # card, mm
SLOT_Y = CH / 2 - 6.5                  # slot centre above the card centre
PAPER, INK, GREY = (0.88, 0.88, 0.85), (0.03, 0.035, 0.045), (0.17, 0.19, 0.22)
CREAM = (0.90, 0.86, 0.74)
FAN = 28.0
BADGES = {  # main colour, second colour, header text colour, header lines, role, footer lines, dates, fan, depth mm, footer side
    'badge_dnd': dict(main=(0.016, 0.03, 0.095), second=(0.50, 0.02, 0.03), on=CREAM, head=('Department of National Defence', 'CFB Borden'),
                      role='IT Co-op Student and\nTemporary Unit IMO', foot='National Defence\nCFB Borden', dates='Jun to Aug 2026',
                      fan=0.0, depth=-1.4, side='LEFT'),
    'badge_camp': dict(main=(0.018, 0.13, 0.055), second=(0.08, 0.27, 0.52), on=CREAM, head=('Town of Bradford West Gwillimbury', ''),
                       role='Camp Counsellor', foot='Town of Bradford\nWest Gwillimbury', dates='Summers 2023 to 2025',
                       fan=FAN, depth=0.0, side='LEFT'),
    'badge_food': dict(main=(0.88, 0.60, 0.03), second=(0.02, 0.17, 0.07), on=(0.02, 0.17, 0.07), head=('Food Basics', 'Bradford'),
                       role='Meat Associate', foot='Food Basics\nBradford', dates='Jan to Jun 2023',
                       fan=-FAN, depth=1.4, side='RIGHT'),
}
PIVOT_Z = 97.0    # slot height above the floor, mm
BAR_Z = 205.0     # the stand's cross bar
BASE_Y = 18.0     # stand base centre behind the bar, mm


def barcode(name, cx, cy, w, h, mat, vertical=False, seed=7):
    rnd, out, x = random.Random(seed), [], -w / 2
    while x < w / 2 - 0.9:
        bw = rnd.choice((0.3, 0.3, 0.6, 0.9))
        pts = pts_rect(cx, cy + x + bw / 2, h, bw) if vertical else pts_rect(cx + x + bw / 2, cy, bw, h)
        out.append(slab(name, pts, 0.0, mat, z_mm=0.12))
        x += bw + rnd.choice((0.3, 0.3, 0.6, 0.9))
    return out


def author_face(name):
    st = BADGES[name]
    I = lambda key, col, **kw: ink(f'{name}_{key}', col, **kw)
    main, second, on, paper, dark, grey = I('main', st['main']), I('second', st['second']), I('on', st['on']), I('paper', PAPER), I('ink', INK), I('grey', GREY)
    box, sil = I('box', (0.62, 0.65, 0.69)), I('sil', (0.36, 0.39, 0.43))
    foil = I('foil', (1, 1, 1), rough=0.22, scratch=0.15, metal=0.55, rainbow=260.0)
    foil2 = I('foil2', (1, 1, 1), rough=0.28, scratch=0.15, metal=0.55, rainbow=-410.0)
    flat = dict(height_mm=0.02, bev_mm=0.0)
    S = lambda key, pts, mat, z=0.05: slab(f'{name}_{key}', pts, 0.0, mat, z_mm=z)
    objs = [S('ground', pts_rect(0, 0, CW + 1, CH + 1), paper, 0.0)]

    # Header and footer bands in the employer's colours, the employer named in both.
    if name == 'badge_camp':
        edge = [(27.5 - 55 * i / 40, 21.5 - 3.6 * math.sin(math.pi * i / 40)) for i in range(41)]
        objs += [S('head2', [(-27.5, 43.5), (27.5, 43.5)] + [(x, y - 1.5) for x, y in edge], second),
                 S('head', [(-27.5, 43.5), (27.5, 43.5)] + edge, main, 0.08),
                 S('sun', pts_circle(19.5, 24.6, 2.6), I('sun', (0.85, 0.55, 0.06)), 0.1)]
    else:
        objs += [S('head', pts_rect(0, 31.4, CW + 1, 24.2), main), S('rule', pts_rect(0, 18.7, CW + 1, 1.1), second, 0.08)]
    big = name == 'badge_food'
    objs.append(label(name + '_h1', st['head'][0], 4.3 if big else 2.62, 0, 28.6 if big else 28.9, on, z_mm=0.2,
                      font=FONT_WIDE if big else FONT_TEXT, **flat))
    if st['head'][1]:
        objs.append(label(name + '_h2', st['head'][1], 2.5, 0, 23.6, on, z_mm=0.2, font=FONT_TEXT, **flat))
    objs += [S('foot', pts_rect(0, -38.4, CW + 1, 10.4), main),
             S('footrule', pts_rect(0, -33.0, CW + 1, 0.5), second, 0.08),
             label(name + '_foot', st['foot'], 2.35, -23.6 if st['side'] == 'LEFT' else 23.6, -38.3, on, z_mm=0.2, font=FONT_TEXT,
                   align=st['side'], **flat)]

    # Portrait placeholder, flanked by the security features.
    py = 3.0
    objs += [S('box', rrect(20, 24, 1.8, 0, py), box),
             S('headc', pts_circle(0, py + 3.6, 4.5), sil, 0.1),
             S('body', [(8.8 * math.cos(a), py - 12.0 + 9.2 * math.sin(a)) for a in [math.pi * i / 40 for i in range(41)]], sil, 0.1)]
    if name == 'badge_dnd':   # contact chip and a foil seal
        gold = I('gold', (0.83, 0.64, 0.30), rough=0.3, scratch=0.12, metal=1.0)
        cut = I('cut', (0.28, 0.20, 0.07), rough=0.45, scratch=0.0, metal=1.0)
        cx, cy = -18.6, 7.0
        objs += [S('chip', rrect(10.4, 8.4, 1.5, cx, cy), gold, 0.1), S('c0', pts_rect(cx, cy, 10.4, 0.24), cut, 0.14),
                 S('c1', pts_rect(cx - 2.0, cy, 0.24, 8.4), cut, 0.14), S('c2', pts_rect(cx + 2.0, cy, 0.24, 8.4), cut, 0.14),
                 S('c3', rrect(3.2, 3.0, 0.8, cx, cy), gold, 0.16),
                 S('seal', pts_circle(18.6, 7.0, 4.7), foil, 0.1), S('seal2', pts_circle(18.6, 7.0, 3.1), foil2, 0.12),
                 S('seal3', pts_circle(18.6, 7.0, 1.3), foil, 0.14)]
    elif name == 'badge_camp':  # barcode down one side, foil strip down the other
        objs += barcode(name + '_bar', -18.6, py, 22.0, 5.2, dark, vertical=True, seed=23)
        objs += [S('strip', rrect(4.2, 22.0, 0.6, 18.6, py), foil, 0.1), S('strip2', rrect(1.4, 22.0, 0.4, 18.6, py), foil2, 0.12)]
    else:
        objs += [S('strip', rrect(4.2, 22.0, 0.6, -18.6, py), foil, 0.1), S('strip2', rrect(1.4, 22.0, 0.4, -18.6, py), foil2, 0.12),
                 S('seal', pts_circle(18.6, 9.4, 4.4), foil2, 0.1), S('seal2', pts_circle(18.6, 9.4, 2.8), foil, 0.12)]
        objs += barcode(name + '_bar', 0, -29.9, 38.0, 4.2, dark, seed=41)

    # Name, role, dates, microtext.
    two = '\n' in st['role']
    units = ['REMY POST', st['role'].replace('\n', ' ').upper(), ' '.join(h for h in st['head'] if h).upper()]
    micro = ''
    while len(micro) + len(units[0]) <= 84:
        micro += units[0] + '   '
        units = units[1:] + units[:1]
    micro = micro.strip()
    rows = {'badge_dnd': (-21.4, -30.1, -26.6), 'badge_camp': (-20.0, -25.0, -29.8), 'badge_food': (-19.6, -23.6, -26.3)}[name]
    objs += [label(name + '_name', 'Remy Post', 4.8, 0, -14.3, dark, z_mm=0.2, **flat),
             label(name + '_role', st['role'], 2.7, 0, rows[0], grey, z_mm=0.2, font=FONT_TEXT, **flat),
             label(name + '_micro', micro, 0.82, 0, rows[2], second if name != 'badge_food' else grey, z_mm=0.2, font=FONT_TEXT, **flat)]
    if name == 'badge_camp':
        objs += [S('pill', rrect(44, 4.8, 2.4, 0, rows[1]), second, 0.1),
                 label(name + '_dates', st['dates'], 2.3, 0, rows[1], I('cream', CREAM), z_mm=0.2, **flat)]
    else:
        objs.append(label(name + '_dates', st['dates'], 2.4, 0, rows[1], dark if two else second, z_mm=0.2, **flat))
    return capture(objs, CW, CH, 1280, round(1280 * CH / CW), os.path.join(TEX, name), normal=False, orm=True)


def card(name, tex, pvc):
    """PVC card: rounded corners, a soft edge bevel all round, a punched slot with a bevelled rim."""
    bm = bmesh.new()
    b, bs, T = 0.24, 0.34, CT
    prof = lambda e: [(e, 0.0), (e * 0.3, e * 0.3), (0.0, e), (0.0, T - e), (e * 0.3, T - e * 0.3), (e, T)]
    outer = [[bm.verts.new((x * MM, y * MM, z * MM)) for x, y in rrect(CW - 2 * d, CH - 2 * d, 3.2 - d, n=10)] for d, z in prof(b)]
    slot = [[bm.verts.new((x * MM, y * MM, z * MM)) for x, y in rrect(14.0 + 2 * d, 3.2 + 2 * d, 1.6 + d, 0, SLOT_Y, n=8)] for d, z in prof(bs)]
    for rings in (outer, slot):
        for r0, r1 in zip(rings, rings[1:]):
            n = len(r0)
            for i in range(n):
                bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    for k in (0, -1):
        edges = []
        for ring in (outer[k], slot[k]):
            n = len(ring)
            edges += [bm.edges.get((ring[i], ring[(i + 1) % n])) for i in range(n)]
        bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_object(name, bm)
    me = ob.data
    planar_uv(me, CW, CH)
    me.materials.append(web_material(name, tex, rough=0.2))
    me.materials.append(pvc)
    for p in me.polygons:
        p.material_index = 0 if p.normal.z > 0.9 else 1
    stand_up(me, (0, 0, -SLOT_Y * MM))
    w = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    w.weight, w.keep_sharp = 100, False
    return ob


def smooth_path(ctrl, rounds=4):
    for _ in range(rounds):
        out = [ctrl[0]]
        for (p0, n0), (p1, n1) in zip(ctrl, ctrl[1:]):
            out += [(p0.lerp(p1, 0.25), n0.lerp(n1, 0.25).normalized()), (p0.lerp(p1, 0.75), n0.lerp(n1, 0.75).normalized())]
        ctrl = out + [ctrl[-1]]
    return ctrl


def ribbon(name, path, width, thick, tile, uv2):
    """A flat strap along (point, face normal) pairs; v runs along the length, one tile per `tile` metres."""
    bm = bmesh.new()
    uv, wave = bm.loops.layers.uv.new('UVMap'), bm.loops.layers.uv.new('wave')
    rows, dist = [], 0.0
    for i, (p, nrm) in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)][0] - path[max(i - 1, 0)][0]).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized()
        w = t.cross(nrm).normalized()
        if i:
            dist += (p - path[i - 1][0]).length
        rows.append(([bm.verts.new(p + w * sx * width / 2 + nrm * sz * thick / 2) for sx, sz in ((-1, 1), (1, 1), (1, -1), (-1, -1))], dist / tile, uv2[i]))
    us = (0.0, 1.0, 1.0, 0.0)
    for (a, va, wa), (b, vb, wb) in zip(rows, rows[1:]):
        for k in range(4):
            j = (k + 1) % 4
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            edge = k in (1, 3)
            for loop, uu, vv, ww in zip(f.loops, (us[k], us[j], us[j], us[k]), (va, va, vb, vb), (wa, wa, wb, wb)):
                loop[uv].uv = ((0.03 if edge else uu), vv)
                loop[wave].uv = ww
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


def author_strap():
    navy = thread('strap_weave', (0.02, 0.035, 0.09), math.radians(90), 1500, 1.0, dark=0.55)
    stripe = thread('strap_stripe', (0.80, 0.72, 0.50), math.radians(90), 1500, 1.0, dark=0.7)
    edge = thread('strap_edge', (0.012, 0.02, 0.055), math.radians(90), 3000, 1.0, dark=0.6)
    warp = thread('strap_warp', (0.014, 0.025, 0.07), 0.0, 2400, 1.0, dark=0.6)
    objs = [slab('strap_ground', pts_rect(0, 0, 15.2, 60.4), 0.0, navy),
            slab('strap_stripe', pts_rect(0, 0, 2.6, 60.4), 0.0, stripe, z_mm=0.05)]
    for x in (-3.9, 3.9):
        objs.append(slab('strap_warp', pts_rect(x, 0, 0.9, 60.4), 0.0, warp, z_mm=0.05))
    for x in (-6.9, 6.9):
        objs.append(slab('strap_edge', pts_rect(x, 0, 1.3, 60.4), 0.0, edge, z_mm=0.05))
    return capture(objs, 15.0, 60.0, 384, 1536, os.path.join(TEX, 'lanyard'))


def build():
    root = link(bpy.data.objects.new('badge', None))
    steel = principled('badge_steel', (0.80, 0.81, 0.83), 0.2, 1.0)
    pvc = principled('badge_pvc', (0.86, 0.86, 0.84), 0.3)
    gold = brass()
    pz = PIVOT_Z * MM

    for name, st in BADGES.items():
        e = pivot(name, (0, st['depth'] * MM, pz), card(name, author_face(name), pvc), root)
        e.rotation_euler = (0, math.radians(st['fan']), 0)

    # Clip: a lobster hook through the three slots, turned so it reads from the front, under a swivel.
    a, b, wire = 5.6 * MM, 10.5 * MM, 1.05 * MM
    cz = pz + b - wire * 0.3
    turn = Matrix.Rotation(math.radians(52), 4, 'Z')
    th = [math.tau * i / 96 for i in range(96)]
    oval = [turn @ Vector((a * math.cos(t) * (1 - 0.22 * math.sin(t)), 0, b * math.sin(t))) + Vector((0, 0, cz)) for t in th]
    rad = [wire * (1 + 0.5 * max(0.0, math.sin(t)) ** 1.5) for t in th]
    ring = assign(tube('ring', oval, rad, 16, closed=True), steel)
    gi = list(range(4, 22))
    gate = assign(tube('gate', [oval[i] for i in gi], [rad[i] * 1.42 for i in gi], 16), steel)
    bevel(gate, 0.25 * MM, 2)
    nub = lathe('nub', [(0, 0), (1.5 * MM, 0), (1.5 * MM, 1.5 * MM), (1.0 * MM, 2.4 * MM), (0, 2.4 * MM)], 24)
    nub.data.transform(Matrix.Translation(oval[10] + (turn @ Vector((1, 0, 0))) * wire * 1.3) @ turn @ Matrix.Rotation(math.radians(70), 4, 'Y'))
    assign(bevel(nub, 0.22 * MM, 2), steel)
    top = cz + b
    sw = lathe('swivel', [(r * MM, z * MM) for r, z in ((0, -0.8), (2.4, -0.8), (3.3, 0.2), (3.3, 1.4), (2.9, 1.8), (2.9, 3.4), (3.3, 3.8),
                                                        (3.3, 4.6), (2.3, 5.8), (1.3, 6.2), (1.3, 7.6), (2.2, 8.2), (2.2, 9.4), (0, 9.4))], 48)
    sw.data.transform(Matrix.Translation((0, 0, top)))
    assign(bevel(sw, 0.22 * MM, 2), steel)
    joint = top + 9.4 * MM
    group('clip', (0, 0, joint), [ring, gate, nub, sw], root)

    # Lanyard: a metal crimp over the stitched strap ends; the strap runs up over the bar and its loop hangs behind.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(17.2 * MM, 4.0 * MM, 11.0 * MM))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, joint + 5.2 * MM))
    crimp = assign(bevel(mesh_object('crimp', bm, smooth=False), 0.8 * MM, 4), steel)
    parts = [crimp]
    for x in (-4.8, 4.8):
        rv = lathe('rivet', [(0, 1.0 * MM), (0.9 * MM, 0.85 * MM), (1.5 * MM, 0.4 * MM), (1.7 * MM, 0), (0, 0)], 24)
        rv.data.transform(Matrix.Translation((x * MM, -2.0 * MM, joint + 5.2 * MM)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        parts.append(assign(rv, steel))
    s0, hb, rr, sx = joint / MM + 9.0, BAR_Z, 4.7, 11.5
    half = [((-1.5, -0.7, s0), (0, -1, 0)), ((-2.3, -0.8, s0 + 15), (0, -1, 0)), ((-6.5, -2.6, s0 + 36), (0, -1, 0)), ((-sx, -rr, hb - 12), (0, -1, 0))]
    half += [((-sx, -rr * math.cos(t), hb + rr * math.sin(t)), (0, -math.cos(t), math.sin(t))) for t in [math.pi * k / 8 for k in range(9)]]
    half += [((-sx, rr + 0.2, hb - 30), (0, 1, 0)), ((-sx - 1, rr + 1, hb - 100), (0, 1, 0)), ((-sx + 0.5, 7, hb - 124), (-0.5, 0.6, -0.6)),
             ((-5.5, 9.5, hb - 136), (-0.25, 0.3, -0.92))]
    ctrl = half + [((0, 10.5, hb - 139), (0, 0.2, -1))] + [((-p[0], p[1], p[2]), (-n[0], n[1], n[2])) for p, n in reversed(half)]
    ctrl[-1] = ((1.5, 0.7, s0), (0, -1, 0)); ctrl[-2] = ((2.3, 0.8, s0 + 15), (0, -1, 0))
    path = smooth_path([(Vector(p) * MM, Vector(n).normalized()) for p, n in ctrl])
    n = len(path)
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + (path[i][0] - path[i - 1][0]).length)
    ia = max(range(n // 2), key=lambda i: path[i][0].z)
    ib = max(range(n // 2, n), key=lambda i: path[i][0].z)
    back = (cum[ib] - cum[ia]) / 2
    uv2 = [(1 - cum[i] / cum[ia], 0.0) if i <= ia else ((cum[i] - cum[ib]) / (cum[-1] - cum[ib]), 0.0) if i >= ib
           else (min(cum[i] - cum[ia], cum[ib] - cum[i]) / back, 1.0) for i in range(n)]
    strap = ribbon('strap', path, 15.0 * MM, 0.9 * MM, 0.060, uv2)
    assign(strap, web_material('lanyard', author_strap(), rough=0.72, sheen=0.3, normal_strength=1.4))
    parts.insert(0, strap)
    bm = bmesh.new()   # two rows of bar-tack stitches where the strap ends are sewn together above the crimp
    for row, z in enumerate((s0 + 4.2, s0 + 9.6)):
        for i in range(7):
            geo = bmesh.ops.create_cube(bm, size=1.0)
            m = (Matrix.Translation(((-5.1 + 1.55 * i - 0.9) * MM, -1.32 * MM, z * MM)) @ Matrix.Rotation(math.radians(24 if row else -24), 4, 'Y')
                 @ Matrix.Diagonal((1.5 * MM, 0.34 * MM, 0.42 * MM, 1)))
            bmesh.ops.transform(bm, matrix=m, verts=geo['verts'])
    stitches = mesh_object('stitches', bm, smooth=False)
    bevel(stitches, 0.1 * MM, 2)
    parts.append(assign(stitches, principled('badge_thread', (0.80, 0.72, 0.50), 0.85)))
    group('lanyard', (0, 0, joint), parts, root)

    # Stand: weighted brass base, a post rising behind and reaching forward to a cross bar the strap drapes over.
    hz, py = BAR_Z * MM, (BASE_Y + 28) * MM
    base = lathe('base', [(r * MM, z * MM) for r, z in ((0, 0), (43, 0), (44, 1.0), (44, 5.2), (42.2, 7.4), (33, 8.2), (31.5, 9.6), (0, 9.6))], 96)
    base.data.transform(Matrix.Translation((0, BASE_Y * MM, 0)))
    collar = lathe('collar', [(r * MM, z * MM) for r, z in ((0, 0), (7.5, 0), (7.5, 1.6), (5.6, 4.6), (4.4, 5.2), (4.4, 7.0), (0, 7.0))], 48)
    collar.data.transform(Matrix.Translation((0, py, 9.6 * MM)))
    arc = 17 * MM
    post_pts = [Vector((0, py, 9 * MM)), Vector((0, py, 60 * MM)), Vector((0, py, hz - arc))]
    post_pts += [Vector((0, py - arc + arc * math.cos(t), hz - arc + arc * math.sin(t))) for t in [math.pi / 2 * k / 12 for k in range(1, 13)]]
    post_pts.append(Vector((0, 1.5 * MM, hz)))
    post = tube('post', post_pts, 3.1 * MM, 20)
    bar = tube('bar', [Vector((x * MM, 0, hz)) for x in (-29, -10, 10, 29)], 4.0 * MM, 28)
    hub = lathe('hub', [(r * MM, z * MM) for r, z in ((0, 0), (5.0, 0), (5.0, 3.0), (4.2, 3.6), (0, 3.6))], 32)
    hub.data.transform(Matrix.Translation((0, 6.8 * MM, hz)) @ Matrix.Rotation(-math.pi / 2, 4, 'X'))
    stand = [base, collar, post, bar, hub, ball('finial_l', (-30.5 * MM, 0, hz), 5.4 * MM), ball('finial_r', (30.5 * MM, 0, hz), 5.4 * MM)]
    for o in (base, collar, hub):
        bevel(o, 0.5 * MM, 3)
    for o in stand:
        assign(o, gold)
    group('stand', (0, BASE_Y * MM, 0), stand, root)

    # Root at the centre of the stand's footprint on the floor.
    for o in root.children:
        o.location.y -= BASE_Y * MM
    bpy.context.view_layer.update()
    for o in root.children:
        print(f'[web] node {o.name}: pivot (Blender m) {tuple(round(c, 4) for c in o.location)} rotY {round(math.degrees(o.rotation_euler.y), 1)}')
    return root


VIEW = dict(azimuth=-18, elevation=7, lens=85, distance=0.66)
FOCUS, RADIUS = (0, -0.01, 0.112), 0.13


def main():
    if '--check' in ARGS:
        check('badge', FOCUS, RADIUS, **VIEW)
        return
    scene = reset()
    root = build()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'badge.blend'))
    if '--export' in ARGS:
        export('badge', root)
    if '--render' in ARGS:
        studio(scene, FOCUS, RADIUS, **VIEW)
        render(scene, os.path.join(OUT, 'badge.png'), arg('--size', 1400), arg('--samples', 256))


main()
