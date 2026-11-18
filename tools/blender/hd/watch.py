"""Music for Galaxy Watch: a round smartwatch on a closed strap, the player on its screen."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
FONT = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')


def ring(name, r0, r1, z, a0=0.0, a1=math.tau, steps=160, parent=None):
    """A flat annulus sector at height z (for screen graphics)."""
    bm = bmesh.new()
    n = max(2, int(steps * (a1 - a0) / math.tau))
    rows = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        rows.append((bm.verts.new((r0 * math.sin(a), r0 * math.cos(a), z)), bm.verts.new((r1 * math.sin(a), r1 * math.cos(a), z))))
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    return mesh_object(name, bm, parent, smooth=False)


def disc(name, r, z, cx=0.0, cy=0.0, steps=96, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=r, segments=steps)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(cx, cy, z))
    return mesh_object(name, bm, parent, smooth=False)


def poly(name, pts, z, parent=None):
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, y, z)) for x, y in pts])
    return mesh_object(name, bm, parent, smooth=False)


def build():
    root = link(bpy.data.objects.new('Watch', None))
    head = link(bpy.data.objects.new('Head', None), root)

    # Materials.
    titanium = principled('Titanium', (0.62, 0.61, 0.60), 0.34, 1.0, Anisotropic=0.6)
    roughness_breakup(titanium, scale=900, amount=0.07, stretch=(1, 1, 60))
    polished = principled('Polished', (0.78, 0.78, 0.79), 0.12, 1.0)
    glass = principled('Crystal', (1, 1, 1), 0.0, 0.0, Transmission_Weight=1.0, IOR=1.52)
    black = principled('ScreenBlack', (0.004, 0.004, 0.005), 0.25)
    rubber = principled('Strap', (0.035, 0.037, 0.042), 0.62)
    roughness_breakup(rubber, scale=1800, amount=0.08, bump=0.04)
    ceramic = principled('Back', (0.02, 0.02, 0.022), 0.18, Coat_Weight=1.0)
    accent = emission('UiAccent', (0.16, 0.30, 1.0), 4.0)
    white = emission('UiWhite', (1, 1, 1), 1.6)
    dim = emission('UiDim', (0.5, 0.55, 0.65), 0.5)

    # Case: one lathe profile, bevelled. Radius, height in mm.
    case = lathe('Case', [(r * MM, z * MM) for r, z in [
        (0, -5.6), (15.5, -5.6), (19.8, -4.2), (21.9, -1.6), (22.0, 1.8), (21.3, 3.2), (20.4, 3.9), (19.2, 4.1), (18.75, 3.95), (18.5, 3.3), (0, 3.3)]], 192, head)
    bevel(case, 0.35 * MM, 4, 22)
    assign(case, titanium)

    # Polished chamfer ring on the bezel and a ceramic sensor back.
    bez = lathe('Bezel', [(r * MM, z * MM) for r, z in [(19.25, 4.12), (20.38, 3.93), (20.42, 3.86), (19.2, 4.06)]], 192, head)
    assign(bez, polished)
    back = lathe('SensorBack', [(r * MM, z * MM) for r, z in [(0, -6.9), (9, -6.8), (13.5, -6.2), (15.2, -5.55), (0, -5.55)]], 128, head)
    assign(back, ceramic)

    # Screen stack: black panel, graphics, domed crystal.
    assign(disc('Panel', 18.45 * MM, 3.32 * MM, parent=head), black)
    z = 3.34 * MM
    assign(ring('Track', 15.6 * MM, 16.5 * MM, z, parent=head), dim)
    assign(ring('Progress', 15.6 * MM, 16.5 * MM, z + 0.004 * MM, 0, math.tau * 0.62, parent=head), accent)
    a = math.tau * 0.62
    assign(disc('Knob', 0.95 * MM, z + 0.008 * MM, 16.05 * MM * math.sin(a), 16.05 * MM * math.cos(a), 32, head), white)
    # Album art: concentric discs, like a record sleeve seen from above.
    art = disc('Art', 5.6 * MM, z, 0, 5.2 * MM, parent=head)
    assign(art, emission('UiArt', (0.9, 0.36, 0.1), 1.0))
    assign(ring('ArtRing', 2.2 * MM, 3.6 * MM, z + 0.004 * MM, parent=None), emission('UiArt2', (1.0, 0.74, 0.3), 1.3)).location = (0, 5.2 * MM, 0)
    bpy.data.objects['ArtRing'].parent = head
    # Transport: previous, pause, next.
    y = -6.6 * MM
    for x in (-0.95, 0.35):
        assign(poly('Pause', [(x * MM, y - 1.9 * MM), ((x + 0.6) * MM, y - 1.9 * MM), ((x + 0.6) * MM, y + 1.9 * MM), (x * MM, y + 1.9 * MM)], z, head), white)
    for sgn in (-1, 1):
        x0 = sgn * 4.6 * MM
        for k in (0, 1):
            xa, xb = x0 + sgn * k * 1.45 * MM, x0 + sgn * (k + 1) * 1.45 * MM
            assign(poly('Skip', [(xa, y - 1.45 * MM), (xb, y), (xa, y + 1.45 * MM)], z, head), white)
        xa, xb = x0 + sgn * 2.95 * MM, x0 + sgn * 3.4 * MM
        assign(poly('SkipBar', [(xa, y - 1.45 * MM), (xb, y - 1.45 * MM), (xb, y + 1.45 * MM), (xa, y + 1.45 * MM)], z, head), white)
    for body, size, yy, mat in (('Night Drive', 2.25, -1.6, white), ('2:14', 1.5, -11.2, dim)):
        t = text_mesh('Label', body, size * MM, FONT if os.path.exists(FONT) else None, parent=head)
        t.location = (0, yy * MM, z)
        t.data.materials.append(mat)

    crystal = lathe('Crystal', [(r * MM, z * MM) for r, z in [(0, 4.28), (9, 4.22), (15, 4.02), (17.9, 3.72), (18.42, 3.42), (18.42, 3.36), (0, 3.36)]], 128, head)
    assign(crystal, glass)

    # Bezel minute ticks, printed under the crystal.
    for i in range(60):
        ang = math.tau * i / 60
        r0 = (16.95 if i % 5 == 0 else 17.35) * MM
        w = (0.16 if i % 5 == 0 else 0.09) * MM
        c, s_ = math.cos(ang), math.sin(ang)
        pts = [(s_ * r - c * k, c * r + s_ * k) for r, k in ((r0, -w), (r0, w), (17.95 * MM, w), (17.95 * MM, -w))]
        assign(poly('Tick', pts, z, head), dim)

    # Two side pushers, turned with grip grooves, each in a collar.
    for i, ang in enumerate((math.radians(62), math.radians(118))):
        prof = [(0, 0), (2.0, 0), (2.35, 0.3)]
        for g in range(4):
            z0 = 0.45 + g * 0.5
            prof += [(2.35, z0), (2.1, z0 + 0.12), (2.1, z0 + 0.26), (2.35, z0 + 0.38)]
        prof += [(2.35, 2.6), (2.75, 2.75), (2.75, 3.6), (0, 3.6)]
        b = lathe(f'Button{i}', [(r * MM, (3.6 - h) * MM) for r, h in reversed(prof)], 64, head)
        b.matrix_local = Matrix.Rotation(ang - math.pi / 2, 4, 'Z') @ Matrix.Translation((20.9 * MM, 0, -0.2 * MM)) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
        bevel(b, 0.08 * MM, 2, 30)
        assign(b, polished if i == 0 else titanium)

    # Lugs: four tapered horns sweeping down from the case to the spring bars.
    bar_y, bar_z = 21.5 * MM, -8.2 * MM   # head-local: along the strap, behind the case
    for sy in (-1, 1):
        for sx in (-1, 1):
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, verts=bm.verts, vec=(4.0 * MM, 10.5 * MM, 5.8 * MM))
            for v in bm.verts:          # taper toward the tip, thicken at the root
                k = 0.72 if v.co.y > 0 else 1.12
                v.co.x *= k
                v.co.z *= k
            lug = mesh_object('Lug', bm, head)
            a0 = Vector((sx * 12.6 * MM, sy * 16.6 * MM, -1.2 * MM))
            a1 = Vector((sx * 12.6 * MM, sy * (bar_y + 1.0 * MM), bar_z - 0.4 * MM))
            ydir = (a1 - a0).normalized()
            xdir = Vector((1, 0, 0))
            zdir = xdir.cross(ydir).normalized()
            m = Matrix.Identity(4)
            for c, v in enumerate((xdir, ydir, zdir)):
                m[0][c], m[1][c], m[2][c] = v
            m.translation = (a0 + a1) / 2
            lug.matrix_local = m
            bevel(lug, 1.0 * MM, 6, 80)
            assign(lug, titanium)
            # Spring-bar end: a small polished dimple on the lug's outer face.
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.55 * MM, radius2=0.55 * MM, depth=0.5 * MM, segments=24)
            pip = mesh_object('BarEnd', bm, head)
            pip.matrix_local = Matrix.Translation((sx * 14.15 * MM, sy * bar_y, bar_z)) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
            assign(pip, polished)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.9 * MM, radius2=0.9 * MM, depth=21.0 * MM, segments=24)
        bar = mesh_object('SpringBar', bm, head)
        bar.matrix_local = Matrix.Translation((0, sy * bar_y, bar_z)) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
        assign(bar, polished)

    # Sensor back: a glass lens with four windows.
    assign(lathe('SensorLens', [(r * MM, h * MM) for r, h in [(0, -7.25), (5, -7.15), (8.2, -6.85), (0, -6.85)]], 64, head), principled('SensorGlass', (0.01, 0.012, 0.014), 0.05, Coat_Weight=1.0))
    for k in range(4):
        d = disc('SensorLed', 1.15 * MM, -7.2 * MM, 3.4 * MM * math.cos(k * math.pi / 2), 3.4 * MM * math.sin(k * math.pi / 2), 24, head)
        assign(d, principled('SensorLed', (0.02, 0.22, 0.08), 0.2))

    # The head faces the camera (-Y in the world).
    head.rotation_euler = (math.pi / 2, 0, 0)

    # Strap: a closed loop behind the head, in the world YZ plane, wrapping the two spring bars.
    a_r, b_r = 27 * MM, 35 * MM
    off = 5.2 * MM + a_r * 0.9
    cu = bpy.data.curves.new('StrapCurve', 'CURVE')
    cu.dimensions = '2D'
    sp = cu.splines.new('NURBS')
    n = 64
    sp.points.add(n - 1)
    for i in range(n):
        t = math.tau * i / n
        x = max(-a_r * math.cos(t), -a_r * 0.9)
        sp.points[i].co = (x, b_r * math.sin(t), 0, 1)
    sp.use_cyclic_u = True
    sp.order_u = 4
    cu.resolution_u = 8
    cu.extrude = 9.9 * MM
    cu.bevel_depth = 1.25 * MM
    cu.bevel_resolution = 3
    strap = link(bpy.data.objects.new('Strap', cu), root)
    strap.matrix_world = Matrix(((0, 0, 1, 0), (1, 0, 0, off), (0, 1, 0, 0), (0, 0, 0, 1)))
    strap.data.materials.append(rubber)

    def on_strap(t, lift=0.0):
        """World position, tangent and outward normal on the strap's centre line (back half of the loop)."""
        p = Vector((0, off - a_r * math.cos(t), b_r * math.sin(t)))
        tan = Vector((0, a_r * math.sin(t), b_r * math.cos(t))).normalized()
        nor = Vector((0, -math.cos(t) / a_r, math.sin(t) / b_r)).normalized()
        return p + nor * lift, tan, nor

    def frame(p, x, y, zax):
        m = Matrix.Identity(4)
        for c, v in enumerate((x, y, zax)):
            m[0][c], m[1][c], m[2][c] = v
        m.translation = p
        return m

    def rounded_loop(name, w, h, r, depth, extrude=0.0):
        c = bpy.data.curves.new(name, 'CURVE')
        c.dimensions = '2D'
        s2 = c.splines.new('POLY')
        pts = []
        for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
            for k in range(7):
                a = math.radians(a0 + 90 * k / 6)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        s2.points.add(len(pts) - 1)
        for pt, (px, py) in zip(s2.points, pts):
            pt.co = (px, py, 0, 1)
        s2.use_cyclic_u = True
        c.bevel_depth, c.bevel_resolution, c.extrude = depth, 3, extrude
        return link(bpy.data.objects.new(name, c), root)

    X = Vector((1, 0, 0))
    # Pin buckle: a rounded steel frame around the strap, a tongue through a hole.
    p, tan, nor = on_strap(math.radians(206), 1.5 * MM)
    buckle = rounded_loop('Buckle', 25.5 * MM, 10.5 * MM, 2.4 * MM, 1.05 * MM)
    buckle.matrix_world = frame(p, X, tan, nor)
    buckle.data.materials.append(polished)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.75 * MM, radius2=0.6 * MM, depth=10.2 * MM, segments=20)
    pin = mesh_object('BucklePin', bm, root)
    pin.matrix_world = frame(p + nor * 0.5 * MM, X, nor, tan)
    assign(pin, polished)
    # Two keepers.
    for k, t in enumerate((math.radians(190), math.radians(176))):
        p, tan, nor = on_strap(t, 0)
        keeper = rounded_loop(f'Keeper{k}', 22.6 * MM, 4.6 * MM, 1.6 * MM, 0.75 * MM, extrude=2.3 * MM)
        keeper.matrix_world = frame(p, X, nor, tan)
        keeper.data.materials.append(rubber)
    # Adjustment holes.
    hole = principled('StrapHole', (0.004, 0.004, 0.005), 0.9)
    for k in range(7):
        p, tan, nor = on_strap(math.radians(214 + k * 7.5), 1.27 * MM)
        h = disc(f'Hole{k}', 1.05 * MM, 0, parent=root, steps=24)
        h.matrix_world = frame(p, X, tan, nor)
        assign(h, hole)

    root.location = (0, 0, b_r + 1.3 * MM)
    return root


UI_NAMES = ('Track', 'Progress', 'Knob', 'Art', 'ArtRing', 'Pause', 'Skip', 'SkipBar', 'Label', 'Tick')
WEB = os.path.join(OUT, 'web')
SHIFT = Vector((0, -0.0265, 0))   # puts the footprint's centre on the origin
STUDIO = dict(radius=0.036, azimuth=-34, elevation=14, lens=90, distance=0.33)


LIVE_UI = ('Track', 'Progress', 'Knob', 'Pause')   # drawn live on the site, so kept out of the baked screen


def is_ui(ob):
    return ob.name.split('.')[0] in UI_NAMES


def bake_screen(scene, size=2048):
    """Render the screen graphics square-on into one emissive texture."""
    os.makedirs(WEB, exist_ok=True)
    for name, col in (('UiAccent', (0.20, 0.36, 1.0)), ('UiWhite', (0.86, 0.86, 0.86)), ('UiDim', (0.30, 0.33, 0.39)), ('UiArt', (0.80, 0.30, 0.08)), ('UiArt2', (1.0, 0.72, 0.28))):
        b = next(n for n in bpy.data.materials[name].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Emission Color'].default_value = (*col, 1)
        b.inputs['Emission Strength'].default_value = 1.0
    hidden = [o for o in scene.objects if o.type != 'EMPTY' and (not is_ui(o) or o.name.split('.')[0] in LIVE_UI)]
    for o in hidden:
        o.hide_render = True
    world = bpy.data.worlds.new('Black')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
    scene.world = world
    cam = bpy.data.cameras.new('BakeCam')
    cam.type, cam.ortho_scale = 'ORTHO', 2 * 18.45 * MM
    cam_ob = link(bpy.data.objects.new('BakeCam', cam))
    zc = bpy.data.objects['Watch'].location.z
    cam_ob.location = (0, -0.2, zc)
    cam_ob.rotation_euler = (math.pi / 2, 0, 0)
    scene.camera = cam_ob
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.render.image_settings.file_format = 'PNG'
    path = os.path.join(WEB, 'watch-screen.png')
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    bpy.data.objects.remove(cam_ob)
    return path


def noise_orm(name, size, rough, amount, metal, streak):
    """An occlusion-roughness-metallic texture: brushed streaks (constant along U) or fine grain."""
    import numpy as np
    rng = np.random.default_rng(7)
    if streak:
        rows = rng.normal(0, 1, (size, 1)).repeat(size, 1)
        rows = (rows + np.roll(rows, 1, 0) + np.roll(rows, -1, 0)) / 3
        n = rows * 0.85 + rng.normal(0, 0.25, (size, size))
    else:
        n = rng.normal(0, 1, (size, size))
        n = (n + np.roll(n, 1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 0) + np.roll(n, -1, 1)) / 2.2
    g = np.clip(rough + n * amount, 0.02, 1.0)
    px = np.ones((size, size, 4), dtype=np.float32)
    px[..., 1] = g
    px[..., 2] = metal
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(WEB, name + '.png')
    img.file_format = 'PNG'
    img.save()
    return img


def web_material(name, color, rough, metal, orm=None, emissive=None, **inputs):
    mat = bpy.data.materials.new('W_' + name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    for key, value in inputs.items():
        bsdf.inputs[key.replace('_', ' ')].default_value = value
    if orm:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = orm
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(tex.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    if emissive:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = emissive
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 2.2
    return mat


def lathe_uv(ob, tile_u=1.0, tile_v=1.0):
    """Angle around Z to U, a monotonic mix of height and radius to V (for turned parts)."""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    zs = [v.co.z for v in me.vertices]
    rs = [math.hypot(v.co.x, v.co.y) for v in me.vertices]
    z0, z1, r1 = min(zs), max(zs), max(rs) or 1
    for poly_ in me.polygons:
        us = []
        for li in poly_.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            us.append((math.atan2(co.y, co.x) / math.tau) % 1.0)
        wrap = max(us) - min(us) > 0.5
        for li, u in zip(poly_.loop_indices, us):
            co = me.vertices[me.loops[li].vertex_index].co
            if wrap and u < 0.5:
                u += 1.0
            v = 0.5 * (co.z - z0) / ((z1 - z0) or 1) + 0.5 * math.hypot(co.x, co.y) / r1
            uv.data[li].uv = (u * tile_u, v * tile_v)


def box_uv(ob, scale):
    """World-scale box projection, so grain textures tile evenly on small parts."""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    for poly_ in me.polygons:
        n = poly_.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        a, b = [k for k in range(3) if k != ax]
        for li in poly_.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[a] * scale, co[b] * scale)


def flat_mesh(name, faces, parent, uvs):
    """A flat mesh from (x, y, z) faces with explicit per-corner UVs."""
    bm = bmesh.new()
    layer = bm.loops.layers.uv.new('UVMap')
    for pts, uv in zip(faces, uvs):
        f = bm.faces.new([bm.verts.new(p_) for p_ in pts])
        for loop, t in zip(f.loops, uv):
            loop[layer].uv = t
    return mesh_object(name, bm, parent, smooth=False)


def live_nodes(head):
    """The parts the site animates: the progress ring and the play / pause icon, each its own node."""
    zt = 3.34 * MM
    ui = lambda n, c, k: web_material(n, (0, 0, 0), 0.4, 0.0, Emission_Color=(*c, 1), Emission_Strength=k)
    r0, r1, steps = 15.6 * MM, 16.5 * MM, 240
    for name, z, mat in (('ring_track', zt, ui('UiTrack', (0.30, 0.33, 0.39), 1.0)), ('ring_progress', zt + 0.006 * MM, ui('UiProgress', (0.20, 0.36, 1.0), 2.2))):
        faces, uvs = [], []
        for i in range(steps):
            a, b = math.tau * i / steps, math.tau * (i + 1) / steps
            faces.append([(r0 * math.sin(a), r0 * math.cos(a), z), (r1 * math.sin(a), r1 * math.cos(a), z), (r1 * math.sin(b), r1 * math.cos(b), z), (r0 * math.sin(b), r0 * math.cos(b), z)])
            uvs.append([(i / steps, 0), (i / steps, 1), ((i + 1) / steps, 1), ((i + 1) / steps, 0)])
        assign(flat_mesh(name, faces, head, uvs), mat)
    icon = ui('UiIcon', (0.86, 0.86, 0.86), 2.2)
    y, z = -6.6 * MM, zt + 0.006 * MM
    quad = lambda x0, x1, y0, y1: [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    unit = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assign(flat_mesh('icon_pause', [quad(-0.95 * MM, -0.35 * MM, y - 1.9 * MM, y + 1.9 * MM), quad(0.35 * MM, 0.95 * MM, y - 1.9 * MM, y + 1.9 * MM)], head, [unit, unit]), icon)
    assign(flat_mesh('icon_play', [[(-1.25 * MM, y - 1.9 * MM, z), (1.75 * MM, y, z), (-1.25 * MM, y + 1.9 * MM, z)]], head, [[(0, 0), (1, 0.5), (0, 1)]]), icon)


def variant(scene):
    """For check renders: WATCH_STATE=paused|playing, the ring at WATCH_PROGRESS (0..1)."""
    state, prog = os.environ.get('WATCH_STATE', 'playing'), float(os.environ.get('WATCH_PROGRESS', '0.6'))
    for o in scene.objects:
        base = o.name.split('.')[0]
        if base == 'icon_pause':
            o.hide_render = state != 'playing'
        if base == 'icon_play':
            o.hide_render = state == 'playing'
        if base == 'ring_progress':
            bm = bmesh.new()
            bm.from_mesh(o.data)
            layer = bm.loops.layers.uv.active
            gone = [f for f in bm.faces if max(l[layer].uv.x for l in f.loops) > prog + 1e-4]
            bmesh.ops.delete(bm, geom=gone, context='FACES')
            bm.to_mesh(o.data)
            bm.free()


def export(scene):
    screen_path = bake_screen(scene)
    screen = bpy.data.images.load(screen_path)
    brushed = noise_orm('watch-brushed-orm', 512, 0.34, 0.035, 1.0, True)
    polish = noise_orm('watch-polished-orm', 256, 0.14, 0.02, 1.0, False)
    grain = noise_orm('watch-rubber-orm', 512, 0.62, 0.05, 0.0, False)
    swap = {
        'Titanium': web_material('Titanium', (0.62, 0.61, 0.60), 0.34, 1.0, orm=brushed),
        'Polished': web_material('Polished', (0.78, 0.78, 0.79), 0.14, 1.0, orm=polish),
        'Strap': web_material('Strap', (0.035, 0.037, 0.042), 0.62, 0.0, orm=grain),
        'Crystal': web_material('Crystal', (1, 1, 1), 0.0, 0.0, Transmission_Weight=1.0, IOR=1.52),
        'ScreenBlack': web_material('Screen', (0, 0, 0), 0.3, 0.0, emissive=screen),
        'Back': web_material('Back', (0.02, 0.02, 0.022), 0.18, 0.0, Coat_Weight=1.0),
        'SensorGlass': web_material('SensorGlass', (0.01, 0.012, 0.014), 0.05, 0.0, Coat_Weight=1.0),
        'SensorLed': web_material('SensorLed', (0.02, 0.22, 0.08), 0.2, 0.0),
        'StrapHole': web_material('StrapHole', (0.004, 0.004, 0.005), 0.9, 0.0),
    }
    for o in [o for o in scene.objects if is_ui(o)]:
        bpy.data.objects.remove(o)
    live_nodes(bpy.data.objects['Head'])
    geo = [o for o in scene.objects if o.type in {'MESH', 'CURVE', 'FONT'}]
    bpy.ops.object.select_all(action='DESELECT')
    for o in geo:
        o.select_set(True)
    bpy.context.view_layer.objects.active = geo[0]
    bpy.ops.object.convert(target='MESH')
    tris = 0
    for o in [o for o in scene.objects if o.type == 'MESH']:
        me = o.data
        base = o.name.split('.')[0]
        if not base.startswith(('ring_', 'icon_')):
            for layer in list(me.uv_layers):
                me.uv_layers.remove(layer)
        if base.startswith(('ring_', 'icon_')):
            pass
        elif base == 'Panel':
            uv = me.uv_layers.new(name='UVMap')
            for li, loop in enumerate(me.loops):
                co = me.vertices[loop.vertex_index].co
                uv.data[li].uv = (co.x / (2 * 18.45 * MM) + 0.5, co.y / (2 * 18.45 * MM) + 0.5)
        elif base in ('Case', 'Bezel', 'SensorBack', 'Crystal', 'SensorLens') or base.startswith('Button'):
            lathe_uv(o, tile_u=6.0 if base == 'Case' else 2.0, tile_v=1.0)
        else:
            box_uv(o, 60.0)
        for slot in o.material_slots:
            if slot.material and slot.material.name in swap:
                slot.material = swap[slot.material.name]
        for p_ in me.polygons:
            p_.use_smooth = not base.startswith(('ring_', 'icon_'))
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
    body = bpy.data.objects['Watch']
    body.name = 'Body'
    root = link(bpy.data.objects.new('watch', None))
    body.parent = root
    body.location = body.location + SHIFT
    bpy.ops.object.select_all(action='DESELECT')
    for o in scene.objects:
        if o.type in {'MESH', 'EMPTY'}:
            o.select_set(True)
    raw = os.path.join(WEB, 'watch.glb')
    bpy.ops.export_scene.gltf(filepath=raw, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_materials='EXPORT')
    print('[hd] exported', raw, 'triangles', tris)


def check(scene):
    bpy.ops.import_scene.gltf(filepath=os.environ.get('WATCH_GLB') or os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models', 'watch.glb'))
    f = Vector((0, -0.002, 0.037)) + SHIFT
    studio(scene, tuple(f), STUDIO['radius'], azimuth=STUDIO['azimuth'], elevation=STUDIO['elevation'], lens=STUDIO['lens'], distance=STUDIO['distance'])
    tune_lights()
    variant(scene)
    render(scene, os.environ.get('WATCH_OUT') or os.path.join(WEB, 'watch-check.png'), 1000, 128)


def tune_lights():
    """Keep the fill softbox off the crystal: its reflection landed on the transport icons as a white wedge."""
    scene = bpy.context.scene
    coll = bpy.data.collections.new('FillReceivers')
    for o in scene.objects:
        if o.type in {'MESH', 'CURVE', 'FONT'} and not o.name.startswith('Crystal'):
            coll.objects.link(o)
    fill = bpy.data.objects.get('Fill')
    if fill:
        fill.light_linking.receiver_collection = coll


def main():
    scene = reset()
    watch = build()
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'watch.blend'))
    if '--check' in ARGS:
        for o in list(scene.objects):
            bpy.data.objects.remove(o)
        check(scene)
        return
    if '--export' in ARGS:
        export(scene)
        return
    if '--render' in ARGS:
        studio(scene, (0, -0.002, 0.037), 0.036, azimuth=-34, elevation=14, lens=90, distance=0.33)
        if '--noui' in ARGS:
            for o in scene.objects:
                if is_ui(o):
                    o.hide_render = True
        tune_lights()
        render(scene, os.path.join(OUT, 'watch.png'), arg('--size', 1400), arg('--samples', 192))


main()
