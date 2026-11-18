"""Links: eight mechanical keycaps on a tilted aluminium plate. Nodes key_<name> (press along local -Z) and plate.

  Blender --background --python tools/blender/hd/keys.py -- --render [--size N --samples N]
  Blender --background --python tools/blender/hd/keys.py -- --export
  Blender --background --python tools/blender/hd/keys.py -- --check
"""
import bpy, bmesh, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
FONT = os.path.join(HERE, '..', 'fonts', 'Archivo-Regular-500.ttf')
WEB = os.path.join(OUT, 'web')
TEX = os.path.join(WEB, 'tex')
os.makedirs(TEX, exist_ok=True)

PITCH = 19.05
KEYS = [  # name, label, column, row (row 0 is the front row)
    ('email', 'Email', 0, 0), ('resume', 'Résumé', 1, 0), ('github', 'GitHub', 2, 0), ('linkedin', 'LinkedIn', 3, 0),
    ('tokens', 'Tokens', 0, 1), ('specs', 'Specs', 1, 1), ('aa', 'AA', 2, 1), ('earnings', 'Earnings', 3, 1),
]
PLATE = (4 * PITCH + 20, 2 * PITCH + 20, 9.0)  # mm
TILT = math.radians(11)
CAP_H = 8.4
PS, PY = 1.12, 2.35  # pictogram scale and centre height on the cap, mm
_bold = [os.path.join(HERE, '..', 'fonts', f) for f in ('Archivo-Bold-700.ttf', 'Archivo-SemiBold-600.ttf', 'Archivo-Regular-500.ttf')]
LABEL_FONT = next((f for f in _bold if os.path.exists(f)), None)


def circle(c, r, n=28, a0=0.0, a1=math.tau):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + (0 if a1 - a0 >= math.tau - 1e-6 else 1))]


def ellipse(c, rx, ry, n=32):
    return [(c[0] + rx * math.cos(math.tau * i / n), c[1] + ry * math.sin(math.tau * i / n)) for i in range(n)]


# Pictograms: ('stroke', points, closed) or ('disc', centre, radius). Units mm, about 6 x 5.
PICTO = {
    'email': [('stroke', [(-3, -2), (3, -2), (3, 2), (-3, 2)], True), ('stroke', [(-3, 2), (0, -0.3), (3, 2)], False)],
    'resume': [('stroke', [(-2, -2.6), (2, -2.6), (2, 1.4), (0.8, 2.6), (-2, 2.6)], True), ('stroke', [(0.8, 2.6), (0.8, 1.4), (2, 1.4)], False)]
              + [('stroke', [(-1.1, y), (1.1, y)], False) for y in (0.3, -0.7, -1.7)],
    'github': [('stroke', [(-1.5, 1.7), (-3.1, 0), (-1.5, -1.7)], False), ('stroke', [(1.5, 1.7), (3.1, 0), (1.5, -1.7)], False), ('stroke', [(0.65, 2.3), (-0.65, -2.3)], False)],
    'linkedin': [('stroke', circle((0, 1.35), 1.1), True), ('stroke', circle((0, -2.4), 2.5, 20, 0, math.pi) , False), ('stroke', [(-2.5, -2.4), (2.5, -2.4)], False)],
    'tokens': [('stroke', ellipse((0, y), 2.5, 0.78), True) for y in (1.7, 0, -1.7)],
    'specs': [('stroke', [(-2.9, y), (2.9, y)], False) for y in (1.7, 0, -1.7)] + [('disc', c, 0.72) for c in ((-1.0, 1.7), (1.3, 0), (-0.2, -1.7))],
    'aa': [('stroke', [(-2.9, -1.2), (2.9, -1.2), (2.9, 1.5), (2.3, 2.2), (-2.3, 2.2), (-2.9, 1.5)], True), ('stroke', [(-2.9, 0.5), (2.9, 0.5)], False),
           ('disc', (-1.6, -1.75), 0.75), ('disc', (1.6, -1.75), 0.75)],
    'earnings': [('stroke', [(-2.9, 2.3), (-2.9, -2.3), (2.9, -2.3)], False), ('stroke', [(-2.0, -1.2), (-0.6, 0.3), (0.5, -0.6), (2.3, 1.7)], False),
                 ('stroke', [(1.05, 1.62), (2.3, 1.7), (2.2, 0.45)], False)],
}


def add_disc(bm, c, r, z, n=14):
    bm.faces.new([bm.verts.new((c[0] + r * math.cos(math.tau * i / n), c[1] + r * math.sin(math.tau * i / n), z)) for i in range(n)])


def add_stroke(bm, pts, closed, w, z):
    seq = pts + [pts[0]] if closed else pts
    for a, b in zip(seq, seq[1:]):
        d = Vector((b[0] - a[0], b[1] - a[1]))
        if d.length < 1e-9:
            continue
        n = Vector((-d.y, d.x)).normalized() * (w / 2)
        bm.faces.new([bm.verts.new((a[0] + n.x, a[1] + n.y, z)), bm.verts.new((b[0] + n.x, b[1] + n.y, z)), bm.verts.new((b[0] - n.x, b[1] - n.y, z)), bm.verts.new((a[0] - n.x, a[1] - n.y, z))])
    for p in pts:
        add_disc(bm, p, w / 2, z, 10)


def superellipse(a, b, z, n=64, p=7.0):
    out = []
    for i in range(n):
        t = math.tau * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2 / p), c), b * math.copysign(abs(s) ** (2 / p), s), z))
    return out


def cap_mesh(name):
    """A sculpted cap: straight skirt, tapered sides, cylindrically dished top. Local origin at mid-height."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    h = CAP_H
    rings = [superellipse(9.0, 9.0, 0), superellipse(9.0, 9.0, 1.1), superellipse(7.9, 8.1, 4.6, p=6.5), superellipse(6.5, 7.0, h, p=6.0)]
    for s in (0.94, 0.82, 0.64, 0.44, 0.22):
        rings.append([(x, y, h - 0.95 * (1 - (abs(x) / 6.5) ** 2 * 0 - s * s)) for x, y, _ in superellipse(6.5 * s, 7.0 * s, 0, p=6.0 - 3 * (1 - s))])
    vr = [[bm.verts.new((x * MM, y * MM, (z - h / 2) * MM)) for x, y, z in ring] for ring in rings]
    n = len(vr[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    centre = bm.verts.new((0, 0, (h - 0.95 - h / 2) * MM))
    for i in range(n):
        bm.faces.new((vr[-1][i], vr[-1][(i + 1) % n], centre))
    bm.faces.new(list(reversed(vr[0])))  # underside
    bm.normal_update()
    for f in bm.faces:  # box-projected UVs for the tiling grain
        ax = max(range(3), key=lambda k: abs(f.normal[k]))
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = [(co.x, co.y), (co.y, co.z), (co.x, co.z)][{2: 0, 0: 1, 1: 2}[ax]]
            l[uv].uv = (l[uv].uv[0] / 0.006, l[uv].uv[1] / 0.006)
    return mesh_object(name, bm)


def grain_normal():
    """A small tiling normal map of fine PBT grain (made once, saved next to the other web textures)."""
    path = os.path.join(TEX, 'keys_grain_normal.png')
    size = 256
    rng = np.random.default_rng(7)
    hgt = rng.random((size, size)).astype(np.float32)
    for _ in range(2):  # wrap-around blur keeps it tileable
        hgt = (hgt + np.roll(hgt, 1, 0) + np.roll(hgt, -1, 0) + np.roll(hgt, 1, 1) + np.roll(hgt, -1, 1)) / 5
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 2.2
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 2.2
    nz = np.ones_like(hgt)
    ln = np.sqrt(dx * dx + dy * dy + nz * nz)
    px = np.ones((size, size, 4), dtype=np.float32)
    px[..., 0], px[..., 1], px[..., 2] = -dx / ln * 0.5 + 0.5, -dy / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5
    img = bpy.data.images.new('keys_grain_normal', size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw, img.file_format = path, 'PNG'
    img.save()
    return img


def cap_material(name, color, img):
    mat = principled(name, color, 0.58)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = 0.55
    nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def legend_mesh(name, key, label, cap):
    bm = bmesh.new()
    z = (CAP_H / 2 + 1.0) * MM
    for item in PICTO[key]:
        if item[0] == 'stroke':
            add_stroke(bm, [(x * PS * MM, (y * PS + PY) * MM) for x, y in item[1]], item[2], 0.72 * MM, z)
        else:
            add_disc(bm, (item[1][0] * PS * MM, (item[1][1] * PS + PY) * MM), (item[2] + 0.12) * PS * MM, z)
    ob = mesh_object(name, bm, cap, smooth=False)
    t = text_mesh(name + '_t', label, 3.3 * MM, LABEL_FONT)
    t.location = (0, -5.0 * MM, z)
    bpy.context.view_layer.update()
    tm = bpy.data.meshes.new_from_object(t.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    tm.transform(t.matrix_world)
    xs = [v.co.x for v in tm.vertices]
    wdt, mid = max(xs) - min(xs), (max(xs) + min(xs)) / 2
    fit = min(1.0, 10.8 * MM / wdt)  # long words shrink to the flat of the cap
    for v in tm.vertices:
        v.co.x = (v.co.x - mid) * fit
        v.co.y = -5.0 * MM + (v.co.y + 5.0 * MM) * fit
    bpy.data.objects.remove(t, do_unlink=True)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.from_mesh(tm)
    bm.to_mesh(ob.data)
    bm.free()
    sw = ob.modifiers.new('Wrap', 'SHRINKWRAP')
    sw.target, sw.wrap_method = cap, 'PROJECT'
    sw.use_project_z, sw.use_negative_direction, sw.use_positive_direction = True, True, False
    sw.offset = 0.03 * MM
    return ob


def box(name, size, loc, parent, bev=0.0, seg=3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=[s * MM for s in size])
    ob = mesh_object(name, bm, parent)
    ob.location = [v * MM for v in loc]
    if bev:
        bevel(ob, bev * MM, seg, 60)
    return ob


def cyl(name, r, h, loc, parent, seg=48, bev=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=r * MM, radius2=r * MM, depth=h * MM, segments=seg)
    ob = mesh_object(name, bm, parent)
    ob.location = [v * MM for v in loc]
    if bev:
        bevel(ob, bev * MM, 3, 60)
    return ob


def build():
    root = link(bpy.data.objects.new('keys', None))
    W, D, T = PLATE
    img = grain_normal()
    alu = principled('Aluminium', (0.74, 0.75, 0.77), 0.36, 1.0)
    roughness_breakup(alu, scale=2600, amount=0.07, bump=0.012)
    housing = principled('Housing', (0.012, 0.012, 0.014), 0.42)
    stem = principled('Stem', (0.55, 0.09, 0.05), 0.4)
    steel = principled('Screw', (0.1, 0.1, 0.11), 0.3, 1.0)
    rubber = principled('Foot', (0.02, 0.02, 0.022), 0.75)
    cap = cap_material('Cap', (0.032, 0.034, 0.04), img)
    cap_accent = cap_material('CapAccent', (0.012, 0.055, 0.52), img)
    ink = principled('Legend', (0.92, 0.93, 0.95), 0.55)
    ink_accent = principled('LegendAccent', (1.0, 1.0, 1.0), 0.55)

    # Plate: tilted toward the reader. Its local frame carries the keys.
    cz = 3.0 + T / 2 * math.cos(TILT) + D / 2 * math.sin(TILT)
    plate = box('plate', (W, D, T), (0, 0, cz), root, bev=1.6, seg=1)
    plate.rotation_euler = (TILT, 0, 0)
    assign(plate, alu)
    # A shallow milled pocket line around the key field.
    rim = box('Pocket', (4 * PITCH + 3.2, 2 * PITCH + 3.2, 0.5), (0, 0, T / 2 - 0.1), plate)
    assign(rim, principled('Pocket', (0.05, 0.052, 0.058), 0.5, 1.0))

    for name, label, col, row in KEYS:
        x, y = (col - 1.5) * PITCH, (row - 0.5) * PITCH
        h = box('Housing_' + name, (14.0, 14.0, 5.2), (x, y, T / 2 + 2.6), plate, bev=0.5)
        assign(h, housing)
        s = box('Stem_' + name, (4.2, 4.2, 4.2), (x, y, T / 2 + 5.2 + 1.2), plate, bev=0.25)
        assign(s, stem)
        k = cap_mesh('key_' + name)
        k.parent = plate
        k.location = (x * MM, y * MM, (T / 2 + 6.6 + CAP_H / 2) * MM)
        bevel(k, 0.45 * MM, 3, 28)
        assign(k, cap_accent if name == 'email' else cap)
        lg = legend_mesh('legend_' + name, name, label, k)
        assign(lg, ink_accent if name == 'email' else ink)

    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = sx * (W / 2 - 4.6), sy * (D / 2 - 4.6)
            head = cyl('Screw', 2.3, 1.5, (px, py, T / 2 + 0.55), plate, bev=0.3)
            assign(head, steel)
            sock = cyl('Socket', 1.15, 0.9, (px, py, T / 2 + 1.0), plate, seg=6)
            assign(sock, housing)
            # Feet stand in the root frame, reaching up into the tilted plate.
            wy = py * math.cos(TILT)
            top = cz + py * math.sin(TILT) - T / 2 * math.cos(TILT) + 0.8
            foot = cyl('Foot', 4.2, top, (px, wy, top / 2), root, bev=0.6)
            assign(foot, rubber)
            pad = cyl('Pad', 4.6, 1.6, (px, wy, 0.8), root, bev=0.5)
            assign(pad, rubber)
    return root


def tri_count(root):
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    for ob in root.children_recursive:
        if ob.type == 'MESH':
            me = ob.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles()
            total += len(me.loop_triangles)
    return total


def export_web():
    import webkit_ct as wk
    scene = reset()
    root = build()
    bpy.context.view_layer.update()
    wk.realize(root)
    plate = bpy.data.objects['plate']
    # Legends join their caps; everything fixed joins the plate and is baked as one texture set.
    for name, *_ in KEYS:
        k, lg = bpy.data.objects['key_' + name], bpy.data.objects['legend_' + name]
        wk._only([lg, k], k)
        bpy.ops.object.join()
        mw = k.matrix_world.copy()
        k.parent = root
        k.matrix_parent_inverse = Matrix.Identity(4)
        k.matrix_world = mw
    fixed = [o for o in root.children_recursive if o.type == 'MESH' and not o.name.startswith('key_') and o is not plate]
    wk._only(fixed + [plate], plate)
    bpy.ops.object.join()
    plate.name = 'plate'
    wk.bake_set(plate, 'keys_plate', 2048)
    for name in ('Cap', 'CapAccent', 'Legend', 'LegendAccent'):
        m = bpy.data.materials[name]
        bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        for sock in bsdf.inputs:  # keep only the grain normal map
            if sock.name != 'Normal':
                for l in list(sock.links):
                    m.node_tree.links.remove(l)
    print('[keys] triangles', wk.tri_count(root))
    wk.export(root, 'keys')


def check():
    """Re-import the shipped file, measure every key's pivot and press axis, render it at rest and with two keys down."""
    import webkit_ct as wk
    scene = wk.check_scene('keys')
    bpy.context.view_layer.update()
    plate = bpy.data.objects['plate']
    rot = plate.matrix_world.to_3x3()
    big = max((f for f in plate.data.polygons if (rot @ f.normal).normalized().z > 0.5), key=lambda f: f.area)
    normal = (plate.matrix_world.to_3x3() @ big.normal).normalized()
    top = plate.matrix_world @ big.center
    print('[pivot] plate top normal (Blender world)', [round(v, 4) for v in normal], 'tilt deg', round(math.degrees(math.acos(normal.z)), 2))
    for name, *_ in KEYS:
        k = bpy.data.objects['key_' + name]
        cos = [v.co for v in k.data.vertices]
        lo = Vector([min(c[i] for c in cos) for i in range(3)])
        hi = Vector([max(c[i] for c in cos) for i in range(3)])
        sc = k.matrix_world.to_scale()
        off = Vector([(lo[i] + hi[i]) / 2 * sc[i] for i in range(3)]) * 1000
        down = -(k.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()  # Blender local -Z is glTF local -Y
        ang = math.degrees(math.acos(max(-1, min(1, down.dot(-normal)))))
        gap = (k.matrix_world.translation - top).dot(normal) * 1000 + lo.z * sc.z * 1000
        print('[pivot] key_%-9s parent=%s origin-to-centre mm=(%.3f, %.3f, %.3f) press-axis-vs-plate-normal deg=%.3f underside above plate mm=%.2f (after 4 mm: %.2f)'
              % (name, k.parent.name if k.parent else None, off.x, off.y, off.z, ang, gap, gap - 4))
    look(scene)
    render(scene, os.path.join(WEB, 'keys-check.png'), 800, 128)
    for name in ('email', 'github'):
        k = bpy.data.objects['key_' + name]
        k.matrix_world = Matrix.Translation(-(k.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized() * 0.004) @ k.matrix_world
    render(scene, os.path.join(WEB, 'keys-check-pressed.png'), 800, 128)


def look(scene):
    studio(scene, (0, 0.0, 0.014), 0.034, azimuth=-27, elevation=34, lens=85, distance=0.285)


def main():
    if '--check' in ARGS:
        return check()
    if '--export' in ARGS:
        return export_web()
    scene = reset()
    root = build()
    bpy.context.view_layer.update()
    print('[keys] triangles', tri_count(root))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'keys.blend'))
    if '--render' in ARGS:
        look(scene)
        render(scene, os.path.join(OUT, 'keys.png'), arg('--size', 1400), arg('--samples', 256))


main()
