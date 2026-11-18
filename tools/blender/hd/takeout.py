"""Meals App: a folded paper take-out box with a wire handle, a printed mark and a pair of chopsticks."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

BW, BD = 0.074, 0.058      # bottom width (x) and depth (y)
TW, TD = 0.102, 0.086      # top
H = 0.098
T = 0.0009                 # board thickness


def solidify(ob, thickness, offset=0.0):
    m = ob.modifiers.new('Solidify', 'SOLIDIFY')
    m.thickness, m.offset, m.use_even_offset = thickness, offset, True
    m.material_offset_rim = 1   # the cut edge shows the grey board core
    return ob


def panel(name, pts, parent, thickness=T, bev=0.0005):
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in pts])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_object(name, bm, parent, smooth=False)
    solidify(ob, thickness)
    bevel(ob, bev, 2, 40)
    return ob


def wood(name):
    mat = principled(name, (0.62, 0.44, 0.24), 0.48)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (260, 260, 6)
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 1.0
    noise.inputs['Detail'].default_value = 10
    noise.inputs['Roughness'].default_value = 0.62
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.32, (0.36, 0.21, 0.09, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.72, (0.74, 0.55, 0.30, 1)
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.12
    rough = nt.nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value, rough.inputs['To Max'].default_value = 0.38, 0.6
    nt.links.new(coord.outputs['Object'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    nt.links.new(noise.outputs['Fac'], rough.inputs['Value'])
    nt.links.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
    return mat


def chopstick(name, length, parent, mat):
    """Square at the grip, round at the tip, tapered; built along +Z from the tip."""
    bm = bmesh.new()
    rings, n, seg = [], 28, 16
    for i in range(n + 1):
        t = i / n
        z = length * t
        half = 0.0015 + 0.0013 * t ** 0.8
        square = max(0.0, (t - 0.45) / 0.55)          # 0 round .. 1 square
        ring = []
        for k in range(seg):
            a = math.tau * k / seg
            cx, cy = math.cos(a), math.sin(a)
            m = max(abs(cx), abs(cy))
            sx, sy = cx / m, cy / m                      # point on the unit square
            p = square ** 0.6 * 0.82
            ring.append(bm.verts.new((half * (cx * (1 - p) + sx * p), half * (cy * (1 - p) + sy * p), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_object(name, bm, parent)
    bevel(ob, 0.00025, 2, 50)
    assign(ob, mat)
    return ob


def flat(name, pts, parent, mat):
    """A printed shape in the local XZ plane, facing -Y."""
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, 0, z)) for x, z in pts][::-1])
    return assign(mesh_object(name, bm, parent, smooth=False), mat)


def arc(r0, r1, a0, a1, n=64):
    outer = [(r1 * math.sin(a0 + (a1 - a0) * i / n), r1 * math.cos(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    inner = [(r0 * math.sin(a0 + (a1 - a0) * i / n), r0 * math.cos(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    return outer + inner[::-1]


def build():
    root = link(bpy.data.objects.new('takeout', None))

    paper = principled('Board', (0.80, 0.79, 0.76), 0.40, Coat_Weight=0.4, Coat_Roughness=0.2, Sheen_Weight=0.2)
    roughness_breakup(paper, scale=70, amount=0.13, bump=0.02)
    core = principled('BoardCore', (0.42, 0.40, 0.37), 0.8)
    crease = principled('Crease', (0.60, 0.59, 0.56), 0.62)
    noodle = principled('Noodle', (0.78, 0.50, 0.18), 0.3, Coat_Weight=0.5, Coat_Roughness=0.12, Subsurface_Weight=0.3, Subsurface_Scale=0.003)
    roughness_breakup(noodle, scale=200, amount=0.08)
    green = principled('Scallion', (0.16, 0.42, 0.10), 0.35, Coat_Weight=0.3)
    pale = principled('ScallionPale', (0.62, 0.74, 0.42), 0.35, Coat_Weight=0.3)
    dark = principled('Hole', (0.01, 0.01, 0.01), 0.9)
    inner = principled('BoardInner', (0.70, 0.68, 0.63), 0.58)
    roughness_breakup(inner, scale=420, amount=0.08, bump=0.05)
    ink = principled('Ink', (0.50, 0.035, 0.03), 0.42)
    wire = principled('Wire', (0.74, 0.74, 0.75), 0.24, 1.0)
    roughness_breakup(wire, scale=300, amount=0.07)
    stick = wood('Bamboo')

    b = [(-BW / 2, -BD / 2, 0), (BW / 2, -BD / 2, 0), (BW / 2, BD / 2, 0), (-BW / 2, BD / 2, 0)]
    t = [(-TW / 2, -TD / 2, H), (TW / 2, -TD / 2, H), (TW / 2, TD / 2, H), (-TW / 2, TD / 2, H)]

    # Body: four tapered walls and a floor, as board with thickness.
    bm = bmesh.new()
    vb = [bm.verts.new(p) for p in b]
    vt = [bm.verts.new(p) for p in t]
    bm.faces.new(vb[::-1])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = mesh_object('Body', bm, root, smooth=False)
    solidify(body, T, offset=-1.0)
    bevel(body, 0.0011, 4, 30)
    body.data.materials.append(paper)
    body.data.materials.append(core)

    # The folded gussets on both sides: the triangular overlaps that make a pail from one sheet.
    for s in (-1, 1):
        xo_b, xo_t = s * (BW / 2 + 0.0007), s * (TW / 2 + 0.0007)
        for d in (-1, 1):
            pts = [(xo_b, d * BD / 2 * 0.98, 0.002), (xo_t, d * TD / 2 * 0.98, H - 0.002),
                   (s * ((BW + TW) / 4 + 0.0010), 0.0, H * 0.50 + d * 0.002)]
            g = assign(panel(f'Gusset{s}{d}', pts, root, T, 0.0003), paper)
            g.data.materials.append(core)

    # Four top flaps, splayed open, each a warped grid so the board does not read as a flat plane.
    import random
    rng = random.Random(7)
    for i, (theta, length, tip_inset) in enumerate(((132, 0.042, 0.011), (118, 0.034, 0.008), (96, 0.042, 0.011), (112, 0.034, 0.008))):
        p0, p1 = Vector(t[i]), Vector(t[(i + 1) % 4])
        mid = (p0 + p1) / 2
        inward = Vector((0, 0, H)) - mid
        inward.z = 0
        inward.normalize()
        a = math.radians(theta)
        up = inward * math.cos(a) + Vector((0, 0, 1)) * math.sin(a)
        nrm = inward * math.sin(a) - Vector((0, 0, 1)) * math.cos(a)
        edge = p1 - p0
        bow, twist = rng.uniform(0.0012, 0.0026), rng.uniform(-0.0016, 0.0016)
        bm = bmesh.new()
        NU, NV = 14, 10
        grid = []
        for v in range(NV + 1):
            fv = v / NV
            row = []
            for u in range(NU + 1):
                fu = u / NU
                inset = tip_inset * fv / edge.length
                fu2 = inset + fu * (1 - 2 * inset)
                warp = bow * fv * fv * math.sin(math.pi * fu) + twist * fv * (fu - 0.5) * 2 - 0.0009 * math.sin(math.pi * fv)
                row.append(bm.verts.new(p0 + edge * fu2 + up * (length * fv) + nrm * warp + Vector((0, 0, 0.0004))))
            grid.append(row)
        for v in range(NV):
            for u in range(NU):
                bm.faces.new((grid[v][u], grid[v][u + 1], grid[v + 1][u + 1], grid[v + 1][u]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        f = mesh_object(f'Flap{i}', bm, root, smooth=True)
        solidify(f, T)
        bevel(f, 0.0003, 2, 50)
        f.data.materials.append(paper)
        f.data.materials.append(core)
        # the scored fold where the flap meets the wall
        sc = bpy.data.curves.new(f'Score{i}', 'CURVE')
        sc.dimensions = '3D'
        sp_ = sc.splines.new('POLY')
        sp_.points.add(1)
        out = -inward * 0.0003
        sp_.points[0].co = (*(p0 + edge * 0.02 + out), 1)
        sp_.points[1].co = (*(p1 - edge * 0.02 + out), 1)
        sc.bevel_depth = 0.00045
        link(bpy.data.objects.new(f'Score{i}', sc), root).data.materials.append(crease)

    # Soft vertical creases down the four corners and the gusset folds.
    for i in range(4):
        cc = bpy.data.curves.new(f'Corner{i}', 'CURVE')
        cc.dimensions = '3D'
        s_ = cc.splines.new('POLY')
        s_.points.add(1)
        s_.points[0].co = (*(Vector(b[i]) * 1.004 + Vector((0, 0, 0.003))), 1)
        s_.points[1].co = (*(Vector(t[i]) * 1.003 - Vector((0, 0, 0.002))), 1)
        cc.bevel_depth = 0.0004
        link(bpy.data.objects.new(f'Corner{i}', cc), root).data.materials.append(crease)

    # Noodles: a mound for body, then loose strands heaped above the rim.
    mound = lathe('NoodleMound', [(0, H + 0.016), (0.014, H + 0.014), (0.028, H + 0.007), (0.038, H - 0.004), (0.041, H - 0.02), (0, H - 0.02)], 48, root)
    mound.scale = (0.8, 0.66, 0.8)
    assign(mound, noodle)
    nc = bpy.data.curves.new('Noodles', 'CURVE')
    nc.dimensions = '3D'
    clumps = [(rng.uniform(-0.026, 0.026), rng.uniform(-0.02, 0.02), rng.uniform(0.004, 0.013)) for _ in range(6)]

    def heap(x, y):
        r2 = min(1.0, (x / 0.039) ** 2 + (y / 0.031) ** 2)
        lump = sum(h * math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / 0.00012) for cx, cy, h in clumps)
        return H + 0.013 * (1 - r2) ** 0.7 + 0.015 * math.tanh(lump / 0.015)   # overlapping clumps do not pile into a cone

    deep = principled('NoodleDeep', (0.42, 0.24, 0.07), 0.45)
    bm = bmesh.new()
    rings_ = []
    for j in range(12):
        rr = min(j / 10, 1.0)
        rings_.append([bm.verts.new((0.041 * rr * math.cos(math.tau * q / 40), 0.033 * rr * math.sin(math.tau * q / 40), 0)) for q in range(40)])
    for j, ring_ in enumerate(rings_):
        for v in ring_:
            v.co.z = heap(v.co.x, v.co.y) - 0.0045 if j < 11 else H - 0.022
    for a_, b_ in zip(rings_, rings_[1:]):
        for q in range(40):
            bm.faces.new((a_[q], a_[(q + 1) % 40], b_[(q + 1) % 40], b_[q]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign(mesh_object('NoodleMoundTop', bm, root), deep)

    for k in range(134):
        over = k < 7                                   # these few hang over the rim
        sp_ = nc.splines.new('NURBS')
        n = rng.randint(9, 14)
        sp_.points.add(n - 1)
        cx, cy, _h = clumps[k % len(clumps)]
        x, y = cx + rng.uniform(-0.012, 0.012), cy + rng.uniform(-0.01, 0.01)
        if k >= 104:                                   # extra cover toward the rim, where the heap was thin
            a_, q_ = rng.uniform(0, math.tau), rng.uniform(0.5, 0.95)
            x, y = 0.039 * q_ * math.cos(a_), 0.031 * q_ * math.sin(a_)
        heading, turn = rng.uniform(0, math.tau), rng.uniform(-1.2, 1.2)
        if over:
            heading, turn = math.atan2(y, x) + rng.uniform(-0.4, 0.4), 0.0
        for j in range(n):
            heading += turn + rng.uniform(-0.5, 0.5) * (0.3 if over else 1)
            x += math.cos(heading) * 0.0075
            y += math.sin(heading) * 0.0075
            r2 = (x / 0.039) ** 2 + (y / 0.031) ** 2
            if r2 > 1 and not over:
                x, y, heading = x / r2 ** 0.5, y / r2 ** 0.5, heading + 2.4
                r2 = 1
            z = heap(x, y) + rng.uniform(-0.0015, 0.0045) + 0.0015
            if over and r2 > 1:
                rr = min(r2 ** 0.5, 1.28)                 # a short tail lying on the opened flap
                x, y = x / r2 ** 0.5 * rr, y / r2 ** 0.5 * rr
                z = H + 0.0028 + (rr - 1) * 0.035 * 1.05
            sp_.points[j].co = (x, y, z, 1)
        sp_.use_endpoint_u = True
        sp_.order_u = 4
    nc.resolution_u = 5
    nc.bevel_depth = 0.00125
    nc.bevel_resolution = 1
    nc.use_fill_caps = True
    link(bpy.data.objects.new('Noodles', nc), root).data.materials.append(noodle)

    # Scallion: rings of different cuts and greens, a few lying on edge, plus thin slivers.
    greens = [green, pale, principled('ScallionDeep', (0.07, 0.26, 0.06), 0.4, Coat_Weight=0.3)]
    for k in range(13):
        thick, inner_r, outer_r = rng.uniform(0.0006, 0.0016), rng.uniform(0.0011, 0.0019), rng.uniform(0.0023, 0.0032)
        ring_ = lathe(f'Scallion{k}', [(inner_r, -thick), (outer_r, -thick), (outer_r, thick), (inner_r, thick), (inner_r, -thick)], 18, root)
        x, y = rng.uniform(-0.03, 0.03), rng.uniform(-0.023, 0.023)
        ring_.location = (x, y, heap(x, y) + 0.0058)
        tilt = 1.3 if k % 5 == 0 else 0.6
        ring_.rotation_euler = (rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.uniform(0, 3))
        ring_.scale = (rng.uniform(0.8, 1.3), rng.uniform(0.7, 1.1), 1)
        bevel(ring_, 0.00015, 2, 40)
        assign(ring_, greens[rng.choice((0, 0, 1, 2, 2))])
    for k in range(6):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, verts=bm.verts, vec=(rng.uniform(0.006, 0.011), 0.0011, 0.0005))
        sl = mesh_object(f'Sliver{k}', bm, root)
        x, y = rng.uniform(-0.028, 0.028), rng.uniform(-0.02, 0.02)
        sl.location = (x, y, heap(x, y) + 0.0056)
        sl.rotation_euler = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 3))
        bevel(sl, 0.0002, 2, 60)
        assign(sl, greens[k % 3])

    # Wire handle: up from one side, over the top, down the other, with small hooked ends.
    cu = bpy.data.curves.new('HandleCurve', 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('NURBS')
    side_x, hz = TW / 2 * 0.955 + 0.0016, H * 0.80
    pts = [(-side_x + 0.0075, 0, hz + 0.0045), (-side_x + 0.0062, 0, hz + 0.0005), (-side_x + 0.003, 0, hz), (-side_x - 0.0014, 0, hz)]
    for k in range(13):
        a = math.pi * k / 12
        pts.append((-math.cos(a) * (side_x + 0.004), 0.022 * math.sin(a), hz + 0.086 * math.sin(a) ** 0.8))
    pts += [(side_x + 0.0014, 0, hz), (side_x - 0.003, 0, hz), (side_x - 0.0062, 0, hz + 0.0005), (side_x - 0.0075, 0, hz + 0.0045)]
    sp.points.add(len(pts) - 1)
    for p, co in zip(sp.points, pts):
        p.co = (*co, 1)
    sp.use_endpoint_u = True
    sp.order_u = 4
    cu.resolution_u = 16
    cu.bevel_depth = 0.00085
    cu.bevel_resolution = 6
    cu.use_fill_caps = True
    handle = link(bpy.data.objects.new('Handle', cu), root)
    handle.data.materials.append(wire)
    wall_x = BW / 2 + (TW - BW) / 2 * (hz / H)
    for sgn in (-1, 1):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.0021, radius2=0.0021, depth=0.0016, segments=24)
        hole = mesh_object(f'Hole{sgn}', bm, root)
        hole.rotation_euler = (0, math.pi / 2, 0)
        hole.location = (sgn * (wall_x + 0.0002), 0, hz)
        assign(hole, dark)

    # Printed mark on the front wall: a ring, a bowl and three rising lines.
    lean = math.atan2((TD - BD) / 2, H)
    mark = link(bpy.data.objects.new('Mark', None), root)
    mark.location = (0, -(BD + TD) / 4 - 0.00012 - 0.0001, H * 0.47)
    mark.rotation_euler = (lean, 0, 0)
    r = 0.0185
    flat('MarkRing', arc(r * 0.90, r, 0, math.tau, 96), mark, ink)
    bowl = [(r * 0.56 * math.sin(a), -r * 0.16 + r * 0.56 * math.cos(a)) for a in [math.pi / 2 + math.pi * i / 40 for i in range(41)]]
    flat('MarkBowl', bowl, mark, ink)
    flat('MarkFoot', [(-r * 0.2, -r * 0.74), (r * 0.2, -r * 0.74), (r * 0.2, -r * 0.66), (-r * 0.2, -r * 0.66)], mark, ink)
    for k in (-1, 0, 1):
        x = k * r * 0.24
        steam = [(x - r * 0.035 + r * 0.05 * math.sin(v * 5.5), -r * 0.02 + v * r * 0.52) for v in [i / 16 for i in range(17)]]
        steam += [(px + r * 0.07, pz) for px, pz in steam[::-1]]
        flat(f'MarkSteam{k}', steam, mark, ink)
    label = text_mesh('MarkText', 'MEALS', 0.0062, os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf'), parent=mark)
    label.rotation_euler = (math.pi / 2, 0, 0)
    label.location = (0, 0, -r * 1.42)
    label.data.materials.append(ink)

    # Chopsticks: together on one diagonal, tips in the noodles at front-left, resting over the back-right corner.
    tip, far = Vector((-0.020, -0.014, H + 0.004)), Vector((0.047, 0.038, H + 0.050))
    aim = (far - tip).normalized()
    side = aim.cross(Vector((0, 0, 1))).normalized()
    for i in range(2):
        c = chopstick(f'Chopstick{i}', 0.235, root, stick)
        c.rotation_euler = aim.to_track_quat('Z', 'Y').to_euler()
        c.location = tip + side * (i - 0.5) * 0.0062 - aim * 0.012 + Vector((0, 0, i * 0.0006))

    # Lift strands: separate nodes pinched between the chopstick tips, each with a morph target `lifted`
    # (the shape it takes when the Chopsticks node has risen LIFT). Origin = the end that stays in the box.
    lrng = random.Random(21)
    LIFT = Vector((0, 0, 0.06))
    aim_h = Vector((aim.x, aim.y, 0)).normalized()
    base = tip - aim * 0.012 + Vector((0, 0, 0.0003))
    root['chop_pivot'] = tuple(base + aim * 0.013)
    print('[hd] chopsticks pivot (Blender xyz)', [round(v, 4) for v in root['chop_pivot']], 'lift +Z', LIFT.z)

    def rot(v, a):
        return Vector((v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a), 0))

    def clamp(p, lim=0.85):
        r2 = (p.x / 0.039) ** 2 + (p.y / 0.031) ** 2
        return p * (lim / r2) ** 0.5 if r2 > lim else p

    def catmull(ctrl, sub=12):
        c = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
        out = []
        for i in range(1, len(c) - 2):
            p0, p1, p2, p3 = c[i - 1], c[i], c[i + 1], c[i + 2]
            for j in range(sub):
                t = j / sub
                out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
        out.append(ctrl[-1].copy())
        return out

    def length(pts):
        return sum((b_ - a_).length for a_, b_ in zip(pts, pts[1:]))

    def resample(pts, n):
        cum = [0.0]
        for a_, b_ in zip(pts, pts[1:]):
            cum.append(cum[-1] + (b_ - a_).length)
        out, j = [], 0
        for i in range(n):
            d = cum[-1] * i / (n - 1)
            while j < len(pts) - 2 and cum[j + 1] < d:
                j += 1
            f = (d - cum[j]) / max(1e-9, cum[j + 1] - cum[j])
            out.append(pts[j].lerp(pts[j + 1], min(1.0, f)))
        return out

    def surf(q, P):
        w = math.exp(-((Vector((q.x, q.y, 0)) - Vector((P.x, P.y, 0))).length / 0.007) ** 2)
        return Vector((q.x, q.y, (heap(q.x, q.y) + 0.0068) * (1 - w) + P.z * w))

    def zigzag(a_, b_, m, target, P):
        mult = [lrng.uniform(0.6, 1.3) * (1 if i % 2 else -1) for i in range(m)]
        perp = rot((b_ - a_).normalized(), math.pi / 2)
        amp = 0.002
        while True:
            mids = [clamp(a_.lerp(b_, (i + 1) / (m + 1)) + perp * amp * mult[i]) for i in range(m)]
            if length([surf(q, P) for q in catmull([a_] + mids + [b_])]) >= target or amp > 0.02:
                return mids
            amp += 0.001

    def tube(lines, radius=0.00125, sides=8):
        shapes = []
        for line in lines:
            verts, nrm = [], None
            for i, p_ in enumerate(line):
                tan = (line[min(i + 1, len(line) - 1)] - line[max(i - 1, 0)]).normalized()
                if nrm is None:
                    nrm = tan.cross(Vector((0.3, 0.9, 0.2))).normalized()
                nrm = (nrm - tan * nrm.dot(tan)).normalized()
                bin_ = tan.cross(nrm)
                verts += [p_ + (nrm * math.cos(math.tau * q / sides) + bin_ * math.sin(math.tau * q / sides)) * radius for q in range(sides)]
            shapes.append(verts)
        n = len(lines[0])
        faces = [(i * sides + q, i * sides + (q + 1) % sides, (i + 1) * sides + (q + 1) % sides, (i + 1) * sides + q) for i in range(n - 1) for q in range(sides)]
        faces += [tuple(range(sides))[::-1], tuple(range((n - 1) * sides, n * sides))]
        return shapes, faces

    N1, N2 = 40, 26
    for k in range(4):
        P = base + aim * (0.007 + 0.004 * k)
        P2 = Vector((P.x, P.y, 0))
        e = rot(aim_h, (-0.55, 0.2, 0.7, -0.15)[k])
        A2 = clamp(P2 + e * lrng.uniform(0.024, 0.032), 0.8)
        free_len = (0.040, 0.050, 0.036, 0.046)[k]
        E2 = clamp(P2 + rot(aim_h, (1.9, -1.8, 2.3, -2.2)[k]) * 0.02)
        az = heap(A2.x, A2.y) + 0.0068
        need = (Vector((A2.x, A2.y, az)) - (P + LIFT)).length + 0.008
        z1 = zigzag(A2, P2, 5, max(0.07, need), P)
        z2 = zigzag(P2, E2, 3, free_len, P)
        dense, s_ = [], 0.0
        flat_ = catmull([A2] + z1 + [P2] + z2 + [E2])
        for i, q in enumerate(flat_):
            if i:
                s_ += (q - flat_[i - 1]).length
            z = surf(q, P).z
            z -= 0.007 * max(0.0, 1 - s_ / 0.006)            # the anchored end dives into the heap
            dense.append(Vector((q.x, q.y, z)))
        ip = (1 + len(z1)) * 12
        rest = resample(dense[:ip + 1], N1) + resample(dense[ip:], N2)[1:]
        A3, Pl = rest[0], P + LIFT
        up, side_j = Vector((0, 0, 1)), rot(e, math.pi / 2) * lrng.uniform(-0.005, 0.005)
        ctrl = [A3, A3 + up * 0.009 - e * 0.003, A3.lerp(Pl, 0.5) + e * 0.004 + side_j,
                Pl + e * 0.003 - up * 0.012, Pl + e * 0.0022 - up * 0.0035, Pl + up * 0.0012, Pl - e * 0.0022 - up * 0.0035,
                Pl - e * 0.003 - side_j * 0.4 - up * free_len * 0.5, Pl - e * 0.0005 + side_j * 0.5 - up * (free_len - 0.003)]
        dl = catmull(ctrl)
        lifted = resample(dl[:5 * 12 + 1], N1) + resample(dl[5 * 12:], N2)[1:]
        shapes, faces = tube([[p_ - A3 for p_ in rest], [p_ - A3 for p_ in lifted]])
        me = bpy.data.meshes.new(f'noodle_lift_{k + 1}')
        me.from_pydata([tuple(v) for v in shapes[0]], [], faces)
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        ob = link(bpy.data.objects.new(f'noodle_lift_{k + 1}', me), root)
        ob.location = A3
        ob.shape_key_add(name='Basis')
        key = ob.shape_key_add(name='lifted')
        for v, co in zip(key.data, shapes[1]):
            v.co = co
        me.materials.append(noodle)
        key.value = 1.0 if '--lifted' in ARGS else 0.0     # a new key does not start at 0 in this Blender
        ob.active_shape_key_index = 0
        print('[hd] rest length', round(length(rest), 4), 'lifted length', round(length(lifted), 4))
        print(f'[hd] noodle_lift_{k + 1} origin (Blender xyz)', [round(v, 4) for v in A3], 'pinch', [round(v, 4) for v in P])
    if '--lifted' in ARGS:
        for i in range(2):
            bpy.data.objects[f'Chopstick{i}'].location += LIFT
    return root


def tri_count():
    deps = bpy.context.evaluated_depsgraph_get()
    total = 0
    for ob in bpy.context.scene.objects:
        if ob.name == 'Cove' or ob.type not in {'MESH', 'CURVE', 'FONT'}:
            continue
        me = ob.evaluated_get(deps).to_mesh()
        me.calc_loop_triangles()
        total += len(me.loop_triangles)
    return total


def export_web():
    import webkit_ct as wk
    O = bpy.data.objects
    root = O['takeout']
    wk.realize(root)
    names = [o.name for o in root.children_recursive if o.type == 'MESH']
    pick = lambda *pre: [O[n] for n in names if n.startswith(pre)]
    board = wk.join(pick('Body', 'Gusset', 'Flap', 'Score', 'Corner'), 'Board')
    twin = board.copy()
    twin.data = board.data.copy()
    bpy.context.scene.collection.objects.link(twin)
    marks = [o for o in O['Mark'].children if o.type == 'MESH']
    wk.bake_set(board, 'takeout_board', 2048, sources=[twin] + marks, extrusion=0.002, coat=(0.4, 0.2))
    bpy.data.objects.remove(O['Mark'], do_unlink=True)
    sticks = wk.join(pick('Chopstick'), 'Chopsticks')
    bpy.context.view_layer.update()
    piv = Vector(root['chop_pivot'])                     # node origin at the pinch point between the tips
    sticks.data.transform(Matrix.Translation(-piv) @ sticks.matrix_world)
    sticks.matrix_world = Matrix.Translation(piv)
    bpy.context.view_layer.update()

    def pivot_node(ob, name):
        """Compression moves a mesh node's own origin, so the named node is an empty parent at the pivot."""
        ob.name = name + '_mesh'
        holder = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(holder)
        holder.parent = root
        holder.location = ob.location
        ob.parent = holder
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = (0, 0, 0)

    for n in [n for n in names if n.startswith('noodle_lift')]:
        pivot_node(O[n], n)
    wk.bake_set(sticks, 'takeout_sticks', 1024)
    pivot_node(sticks, 'Chopsticks')
    wk.join(pick('NoodleMound', 'Noodles'), 'Noodles')
    wk.join(pick('Scallion', 'Sliver'), 'Scallions')
    wk.join(pick('Handle', 'Hole'), 'Handle')
    for name in ('Noodle', 'NoodleDeep', 'Scallion', 'ScallionPale', 'ScallionDeep', 'Wire', 'Hole'):
        wk.flatten(bpy.data.materials[name])
    print('[web] takeout triangles', wk.tri_count(root))
    wk.export(root, 'takeout')


def check():
    import webkit_ct as wk
    lifted = '--lifted' in ARGS
    scene = wk.check_scene('takeout')
    O = bpy.data.objects
    print('[web] nodes', sorted(o.name for o in O), 'root children', sorted(o.name for o in O['takeout'].children))
    for o in O:
        if o.name.startswith('noodle_lift') and o.type == 'EMPTY':
            print('[web]', o.name, 'origin', [round(v, 4) for v in o.matrix_world.translation])
        if o.name.startswith('noodle_lift') and o.type == 'MESH':
            print('[web]', o.name, 'targets', [k.name for k in o.data.shape_keys.key_blocks])
            print('[web]', o.name, 'default weight', o.data.shape_keys.key_blocks['lifted'].value)
            o.data.shape_keys.key_blocks['lifted'].value = 1.0 if lifted else 0.0
    print('[web] Chopsticks origin', [round(v, 4) for v in O['Chopsticks'].matrix_world.translation])
    if lifted:
        O['Chopsticks'].location.z += 0.06
        studio(scene, (0.012, 0, 0.13), 0.105, azimuth=-30, elevation=22, lens=90, distance=1.08)
    else:
        studio(scene, (0.012, 0, 0.105), 0.105, azimuth=-30, elevation=22, lens=90, distance=0.84)
    scene.view_settings.exposure = -0.55
    render(scene, os.path.join(OUT, 'web', 'takeout-check-lifted.png' if lifted else 'takeout-check.png'), 1000, 128)


def main():
    if '--check' in ARGS:
        return check()

    scene = reset()
    build()
    bpy.context.view_layer.update()
    print('[hd] takeout triangles', tri_count())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'takeout.blend'))
    if '--export' in ARGS:
        return export_web()
    if '--render' in ARGS:
        studio(scene, (0.012, 0, 0.105), 0.105, azimuth=-30, elevation=22, lens=90, distance=0.84)
        scene.view_settings.exposure = -0.55
        render(scene, os.path.join(OUT, 'takeout.png'), arg('--size', 1400), arg('--samples', 256))


main()
