"""The Lawn Guy: a cut block of mown turf with a corrugated-plastic yard sign on a wire H-stake.

  --render   the studio still (out/hd/yardsign.png)
  --export   bake soil, grass and print to textures and write apps/site/src/assets/models/yardsign.glb
  --check    re-import the shipped .glb and render out/hd/web/yardsign-check.png
"""
import bpy, bmesh, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
import lawnwin_web as web
from mathutils import Vector, Matrix

MM = 0.001
FONT_WIDE = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')
FONT_REG = os.path.join(HERE, '..', 'fonts', 'Archivo-Regular-500.ttf')
TW, TD, TH = 0.30, 0.22, 0.062   # turf block: width (x), depth (y), soil height
EXPORT = '--export' in ARGS
CAM = dict(azimuth=-26, elevation=13, lens=85, distance=1.08)
FOCUS, RADIUS = (0.0, 0.0, 0.135), 0.165
SIGN_POS, SIGN_YAW = (0.012, 0.018), math.radians(13)
PX = 0.052                         # half the distance between the stake's prongs


def nodes_of(mat):
    nt = mat.node_tree
    return nt, next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')


def prong_points():
    c, s = math.cos(SIGN_YAW), math.sin(SIGN_YAW)
    return [(SIGN_POS[0] + sx * PX * c, SIGN_POS[1] + sx * PX * s) for sx in (-1, 1)]


def soil_material():
    mat = principled('Soil', (0.09, 0.06, 0.04), 0.92)
    nt, bsdf = nodes_of(mat)
    N, L = nt.nodes.new, nt.links.new
    coord = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ'); L(coord.outputs['Object'], sep.inputs['Vector'])
    warp = N('ShaderNodeTexNoise'); warp.inputs['Scale'].default_value = 14; warp.inputs['Detail'].default_value = 5
    L(coord.outputs['Object'], warp.inputs['Vector'])
    h = N('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; h.inputs[1].default_value = 1.0 / TH
    wm = N('ShaderNodeMath'); wm.operation = 'MULTIPLY_ADD'; wm.inputs[1].default_value = 0.30; wm.inputs[2].default_value = -0.15
    L(warp.outputs['Fac'], wm.inputs[0]); L(sep.outputs['Z'], h.inputs[0]); L(wm.outputs['Value'], h.inputs[2])
    # Distinct horizons: pale clay subsoil, a sandy seam, brown topsoil, a near-black root mat, straw thatch.
    ramp = N('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.36, 0.25, 0.15, 1)
    cr.elements[1].position, cr.elements[1].color = 0.30, (0.30, 0.20, 0.115, 1)
    for pos, col in ((0.34, (0.46, 0.36, 0.24, 1)), (0.39, (0.42, 0.32, 0.20, 1)), (0.43, (0.13, 0.082, 0.046, 1)), (0.72, (0.105, 0.064, 0.036, 1)),
                     (0.80, (0.030, 0.020, 0.012, 1)), (0.93, (0.036, 0.026, 0.014, 1)), (0.97, (0.20, 0.17, 0.075, 1))):
        e = cr.elements.new(pos); e.color = col
    L(h.outputs['Value'], ramp.inputs['Fac'])
    # Stones: pale pebbles scattered through the lower layers.
    vor = N('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 120; vor.feature = 'F1'; vor.inputs['Randomness'].default_value = 1.0
    L(coord.outputs['Object'], vor.inputs['Vector'])
    stone = N('ShaderNodeMapRange'); stone.inputs['From Min'].default_value = 0.10; stone.inputs['From Max'].default_value = 0.17
    stone.inputs['To Min'].default_value = 1.0; stone.inputs['To Max'].default_value = 0.0
    L(vor.outputs['Distance'], stone.inputs['Value'])
    big = N('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 45; big.inputs['Detail'].default_value = 2
    L(coord.outputs['Object'], big.inputs['Vector'])
    gate = N('ShaderNodeMath'); gate.operation = 'GREATER_THAN'; gate.inputs[1].default_value = 0.60
    L(big.outputs['Fac'], gate.inputs[0])
    low = N('ShaderNodeMath'); low.operation = 'LESS_THAN'; low.inputs[1].default_value = 0.74; L(h.outputs['Value'], low.inputs[0])
    sm = N('ShaderNodeMath'); sm.operation = 'MULTIPLY'; L(stone.outputs['Result'], sm.inputs[0]); L(gate.outputs['Value'], sm.inputs[1])
    sm2 = N('ShaderNodeMath'); sm2.operation = 'MULTIPLY'; L(sm.outputs['Value'], sm2.inputs[0]); L(low.outputs['Value'], sm2.inputs[1])
    mix = N('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['B'].default_value = (0.36, 0.33, 0.29, 1)
    L(sm2.outputs['Value'], mix.inputs['Factor']); L(ramp.outputs['Color'], mix.inputs['A'])
    # Roots: pale threads wandering down from the root mat.
    rw = N('ShaderNodeTexNoise'); rw.inputs['Scale'].default_value = 30; rw.inputs['Detail'].default_value = 3
    L(coord.outputs['Object'], rw.inputs['Vector'])
    rmap = N('ShaderNodeMapping'); rmap.inputs['Scale'].default_value = (1, 1, 0.16)
    radd = N('ShaderNodeMixRGB'); radd.blend_type = 'ADD'; radd.inputs['Fac'].default_value = 0.035
    L(coord.outputs['Object'], radd.inputs['Color1']); L(rw.outputs['Color'], radd.inputs['Color2']); L(radd.outputs['Color'], rmap.inputs['Vector'])
    rv = N('ShaderNodeTexVoronoi'); rv.inputs['Scale'].default_value = 75; rv.feature = 'DISTANCE_TO_EDGE'
    L(rmap.outputs['Vector'], rv.inputs['Vector'])
    rl = N('ShaderNodeMapRange'); rl.inputs['From Min'].default_value = 0.0; rl.inputs['From Max'].default_value = 0.035
    rl.inputs['To Min'].default_value = 1.0; rl.inputs['To Max'].default_value = 0.0
    L(rv.outputs['Distance'], rl.inputs['Value'])
    rz = N('ShaderNodeMapRange'); rz.inputs['From Min'].default_value = 0.42; rz.inputs['From Max'].default_value = 0.80
    L(h.outputs['Value'], rz.inputs['Value'])
    rm = N('ShaderNodeMath'); rm.operation = 'MULTIPLY'; L(rl.outputs['Result'], rm.inputs[0]); L(rz.outputs['Result'], rm.inputs[1])
    rmix = N('ShaderNodeMix'); rmix.data_type = 'RGBA'; rmix.inputs['B'].default_value = (0.50, 0.40, 0.25, 1)
    L(rm.outputs['Value'], rmix.inputs['Factor']); L(mix.outputs['Result'], rmix.inputs['A'])
    fine = N('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 520; fine.inputs['Detail'].default_value = 10
    L(coord.outputs['Object'], fine.inputs['Vector'])
    tone = N('ShaderNodeMix'); tone.data_type = 'RGBA'; tone.blend_type = 'MULTIPLY'; tone.inputs['Factor'].default_value = 0.30
    L(rmix.outputs['Result'], tone.inputs['A']); L(fine.outputs['Color'], tone.inputs['B'])
    L(tone.outputs['Result'], bsdf.inputs['Base Color'])
    bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.9; bump.inputs['Distance'].default_value = 0.0014
    hs = N('ShaderNodeMath'); hs.operation = 'ADD'; L(fine.outputs['Fac'], hs.inputs[0]); L(sm2.outputs['Value'], hs.inputs[1])
    hs2 = N('ShaderNodeMath'); hs2.operation = 'ADD'; L(hs.outputs['Value'], hs2.inputs[0]); L(rm.outputs['Value'], hs2.inputs[1])
    L(hs2.outputs['Value'], bump.inputs['Height']); L(bump.outputs['Normal'], bsdf.inputs['Normal'])
    rr = N('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.72; rr.inputs['To Max'].default_value = 0.98
    L(fine.outputs['Fac'], rr.inputs['Value']); L(rr.outputs['Result'], bsdf.inputs['Roughness'])
    return mat


def srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def ramp_eval(t, stops):
    pos = np.array([p for p, _ in stops]); cols = np.array([c for _, c in stops])
    return np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], -1)


TIP = [(0.0, (0.030, 0.045, 0.012)), (0.45, (0.060, 0.190, 0.030)), (0.92, (0.130, 0.330, 0.060)), (1.0, (0.300, 0.360, 0.150))]
VAR = [(0.0, (0.78, 1.0, 0.72)), (0.86, (1.0, 1.0, 1.0)), (1.0, (1.5, 1.22, 0.62))]


def grass_material():
    if EXPORT:
        # The same two ramps, evaluated into a small texture: u = which blade, v = root to tip.
        u = np.linspace(0, 1, 128)[None, :]; v = np.linspace(0, 1, 128)[:, None]
        # Real-time has no light through the blades: lift the roots and the whole ramp to match the still.
        col = ramp_eval(np.broadcast_to(0.22 + 0.78 * v, (128, 128)), TIP) * ramp_eval(np.broadcast_to(u, (128, 128)), VAR)
        img = web.array_image('yardsign_grass', srgb(col * 1.6).astype(np.float32))
        mat = web.image_material('Grass', base=img, rough=0.5)
        mat.use_backface_culling = False
        return mat
    mat = principled('Grass', (0.10, 0.26, 0.05), 0.48)
    nt, bsdf = nodes_of(mat)
    N, L = nt.nodes.new, nt.links.new
    uv = N('ShaderNodeUVMap'); sep = N('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs['Vector'])
    def ramp(stops, sock):
        r = N('ShaderNodeValToRGB'); cr = r.color_ramp
        cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
        cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
        for p, c in stops[1:-1]:
            e = cr.elements.new(p); e.color = (*c, 1)
        L(sock, r.inputs['Fac']); return r
    tip, var = ramp(TIP, sep.outputs['Y']), ramp(VAR, sep.outputs['X'])
    mul = N('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    L(tip.outputs['Color'], mul.inputs['A']); L(var.outputs['Color'], mul.inputs['B']); L(mul.outputs['Result'], bsdf.inputs['Base Color'])
    trans = N('ShaderNodeBsdfTranslucent'); L(mul.outputs['Result'], trans.inputs['Color'])
    ms = N('ShaderNodeMixShader'); ms.inputs['Fac'].default_value = 0.32
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    L(bsdf.outputs['BSDF'], ms.inputs[1]); L(trans.outputs['BSDF'], ms.inputs[2]); L(ms.outputs['Shader'], out.inputs['Surface'])
    return mat


def value_noise(x, y, scale, seed):
    """Smooth 2D value noise in 0-1 (for clumps and the wandering stripe edge)."""
    r = np.random.default_rng(seed).uniform(0, 1, (64, 64))
    gx, gy = x / scale + 17.3, y / scale + 9.1
    ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
    fx, fy = gx - ix, gy - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    g = lambda a, b: r[a % 64, b % 64]
    return (g(ix, iy) * (1 - fx) + g(ix + 1, iy) * fx) * (1 - fy) + (g(ix, iy + 1) * (1 - fx) + g(ix + 1, iy + 1) * fx) * fy


def build_turf(root, scene):
    # Soil: a rounded, crumbly block.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(TW, TD, TH))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, TH / 2))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    soil = mesh_object('Soil', bm, root)
    s = soil.modifiers.new('Subdiv', 'SUBSURF'); s.subdivision_type = 'SIMPLE'; s.levels = s.render_levels = 4 if EXPORT else 6
    for name, size, strength in (('Lumps', 0.030, 0.007), ('Crumbs', 0.006, 0.0024)):
        tex = bpy.data.textures.new(name, 'CLOUDS'); tex.noise_scale = size; tex.noise_depth = 3
        d = soil.modifiers.new(name, 'DISPLACE'); d.texture = tex; d.strength = strength; d.mid_level = 0.5; d.texture_coords = 'LOCAL'
    assign(soil, soil_material())

    # Stones and root ends standing out of the cut faces.
    rng = np.random.default_rng(11)
    stone_m = principled('Stone', (0.19, 0.175, 0.155), 0.85)
    root_m = principled('Root', (0.50, 0.40, 0.26), 0.85)
    if not EXPORT:
        roughness_breakup(stone_m, scale=400, amount=0.12, bump=0.3)
    for i in range(16):
        face = i % 4
        along = rng.uniform(-0.42, 0.42)
        zz = rng.uniform(0.006, TH * 0.62)
        p = [(along * TW, -TD / 2), (TW / 2, along * TD), (along * TW, TD / 2), (-TW / 2, along * TD)][face]
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        st = mesh_object('Stone', bm, root)
        r = rng.uniform(0.003, 0.007)
        st.scale = (r * rng.uniform(0.8, 1.4), r * rng.uniform(0.8, 1.4), r * rng.uniform(0.4, 0.7))
        st.location = (p[0] * 0.992, p[1] * 0.992, zz); st.rotation_euler = tuple(rng.uniform(0, 3, 3))
        assign(st, stone_m)
    for i in range(22):
        face = i % 4
        along = rng.uniform(-0.45, 0.45)
        zz = rng.uniform(TH * 0.45, TH * 0.88)
        base = [(along * TW, -TD / 2), (TW / 2, along * TD), (along * TW, TD / 2), (-TW / 2, along * TD)][face]
        out = [(0, -1), (1, 0), (0, 1), (-1, 0)][face]
        cu = bpy.data.curves.new('Root', 'CURVE'); cu.dimensions = '3D'
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
        ln = rng.uniform(0.006, 0.020)
        pts = [(base[0] - out[0] * 0.004, base[1] - out[1] * 0.004, zz),
               (base[0] + out[0] * ln * 0.5 + rng.normal(0, 0.003), base[1] + out[1] * ln * 0.5 + rng.normal(0, 0.003), zz - ln * 0.25),
               (base[0] + out[0] * ln * 0.75 + rng.normal(0, 0.004), base[1] + out[1] * ln * 0.75 + rng.normal(0, 0.004), zz - ln * rng.uniform(0.7, 1.3))]
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        cu.bevel_depth = rng.uniform(0.00035, 0.0008); cu.bevel_resolution = 1; cu.resolution_u = 5
        sp.bezier_points[2].radius = 0.25
        ro = link(bpy.data.objects.new('Root', cu), root); ro.data.materials.append(root_m)

    # Grass. Web build: fewer, wider blades with fewer segments, over a dark thatch mat, so it still reads dense.
    rng = np.random.default_rng(7)
    n = 24000 if EXPORT else 46000
    seg = 2 if EXPORT else 5
    wide = 1.8 if EXPORT else 1.0
    x = rng.uniform(-TW / 2 + 0.002, TW / 2 - 0.002, n)
    y = rng.uniform(-TD / 2 + 0.002, TD / 2 - 0.002, n)
    # The stripe edge wanders, and blades near it lean either way.
    edge_x = 0.004 + 0.011 * (value_noise(y, y * 0 + 0.5, 0.035, 3) - 0.5) * 2
    d_edge = x - edge_x
    stripe = np.where(d_edge + rng.normal(0, 0.006, n) < 0.0, 1.0, -1.0)
    clump = value_noise(x, y, 0.022, 5)
    patch = value_noise(x, y, 0.075, 8)
    h = (0.0305 + 0.0075 * (clump - 0.5) + 0.004 * (patch - 0.5) + rng.normal(0, 0.0030, n)).clip(0.017, 0.043)
    tall = rng.uniform(0, 1, n) > 0.985                      # the odd blade the mower missed
    h = np.where(tall, h * rng.uniform(1.25, 1.6, n), h)
    w = rng.uniform(0.0016, 0.0027, n) * wide
    yaw = rng.uniform(0, math.pi, n)
    lean = rng.normal(0.42, 0.16, n) * stripe * (0.75 + 0.5 * clump)
    side = rng.normal(0.0, 0.20, n)
    # Where the stake went in: blades pressed down and outward around each prong.
    press = np.zeros(n); pxo = np.zeros(n); pyo = np.zeros(n)
    for (sx, sy) in prong_points():
        dx, dy = x - sx, y - sy
        dist = np.hypot(dx, dy) + 1e-6
        k = np.clip(1.0 - dist / 0.016, 0, 1)
        press = np.maximum(press, k); pxo += dx / dist * k; pyo += dy / dist * k
    h = h * (1 - 0.45 * press)
    edge = np.minimum.reduce([x + TW / 2, TW / 2 - x, y + TD / 2, TD / 2 - y])
    flop = np.clip(1.0 - edge / 0.012, 0, 1)
    ox = np.sign(x) * (np.abs(x) > TW / 2 - 0.012) * flop * 0.5 + pxo * 1.1
    oy = np.sign(y) * (np.abs(y) > TD / 2 - 0.012) * flop * 0.5 + pyo * 1.1
    t = np.linspace(0, 1, seg + 1)[None, :]
    cx = x[:, None] + (side[:, None] + ox[:, None]) * h[:, None] * t ** 2
    cy = y[:, None] + (lean[:, None] + oy[:, None]) * h[:, None] * t ** 2
    cz = TH - 0.002 + h[:, None] * (t - 0.18 * t ** 2 * (np.abs(lean[:, None]) + flop[:, None] + press[:, None]))
    half = (w[:, None] / 2) * (1 - 0.72 * t ** 1.6)
    sxx, syy = np.cos(yaw)[:, None] * half, np.sin(yaw)[:, None] * half
    verts = np.empty((n, seg + 1, 2, 3))
    verts[:, :, 0] = np.stack([cx - sxx, cy - syy, cz], -1)
    verts[:, :, 1] = np.stack([cx + sxx, cy + syy, cz], -1)
    verts = verts.reshape(-1, 3)
    base = (np.arange(n) * (seg + 1) * 2)[:, None] + (np.arange(seg) * 2)[None, :]
    faces = np.stack([base, base + 1, base + 3, base + 2], -1).reshape(-1, 4)
    me = bpy.data.meshes.new('Grass')
    me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(faces.size); me.loops.foreach_set('vertex_index', faces.ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set('loop_start', np.arange(0, faces.size, 4)); me.polygons.foreach_set('loop_total', np.full(len(faces), 4))
    me.update(calc_edges=True)
    rnd = np.repeat(rng.uniform(0.02, 0.98, n), seg * 4)
    k = np.tile(np.arange(seg), n)
    v = np.stack([k, k, k + 1, k + 1], -1).ravel() / seg
    uv = me.uv_layers.new(name='UVMap')
    uv.data.foreach_set('uv', np.stack([rnd, 0.02 + 0.96 * v], -1).ravel())
    me.polygons.foreach_set('use_smooth', np.ones(len(faces), dtype=bool))
    grass = link(bpy.data.objects.new('Grass', me), root)
    assign(grass, grass_material())

    # Thatch mat under the blades, and two small mounds of soil lifted by the stake.
    bm = bmesh.new()
    g = bmesh.ops.create_grid(bm, x_segments=24, y_segments=18, size=0.5)['verts']
    bmesh.ops.scale(bm, verts=g, vec=(TW - 0.004, TD - 0.004, 1))
    for vtx in g:
        vtx.co.z = TH + 0.0035 + 0.003 * (value_noise(np.array([vtx.co.x]), np.array([vtx.co.y]), 0.02, 5)[0] - 0.5)
    mat_ob = mesh_object('Thatch', bm, root)
    assign(mat_ob, principled('Thatch', (0.040, 0.100, 0.025) if EXPORT else (0.022, 0.050, 0.012), 0.9))
    for (sx, sy) in prong_points():
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        m = mesh_object('Mound', bm, root); m.scale = (0.0075, 0.0065, 0.0042); m.location = (sx + 0.001, sy - 0.001, TH + 0.004)
        assign(m, principled('Loam', (0.085, 0.052, 0.030), 0.95))
    return soil, grass


def cyl(name, p0, p1, r, parent, segments=20):
    p0, p1 = Vector(p0), Vector(p1)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=r, radius2=r, depth=(p1 - p0).length, segments=segments)
    ob = mesh_object(name, bm, parent)
    ob.matrix_world = Matrix.Translation((p0 + p1) / 2) @ (p1 - p0).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    return ob


def build_sign(root, scene):
    rig = link(bpy.data.objects.new('Sign', None), root)
    SW, SH, ST = 0.205, 0.135, 0.004
    z0 = TH + 0.098
    skin, pitch = 0.00028, 0.0041
    art = []                                       # the printed layer

    plastic = principled('Coroplast', (0.86, 0.87, 0.86), 0.42)
    if not EXPORT:
        nt, bsdf = nodes_of(plastic)
        bsdf.inputs['Subsurface Weight'].default_value = 0.25; bsdf.inputs['Subsurface Scale'].default_value = 0.003
        N, L = nt.nodes.new, nt.links.new
        coord = N('ShaderNodeTexCoord'); sep = N('ShaderNodeSeparateXYZ'); L(coord.outputs['Object'], sep.inputs['Vector'])
        ph = N('ShaderNodeMath'); ph.operation = 'MULTIPLY'; ph.inputs[1].default_value = math.tau / pitch; L(sep.outputs['X'], ph.inputs[0])
        sn = N('ShaderNodeMath'); sn.operation = 'COSINE'; L(ph.outputs['Value'], sn.inputs[0])
        ab = N('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L(sn.outputs['Value'], ab.inputs[0])
        sharp = N('ShaderNodeMath'); sharp.operation = 'POWER'; sharp.inputs[1].default_value = 6; L(ab.outputs['Value'], sharp.inputs[0])
        bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35; bump.inputs['Distance'].default_value = 0.0002
        L(sharp.outputs['Value'], bump.inputs['Height']); L(bump.outputs['Normal'], bsdf.inputs['Normal'])

    bm = bmesh.new()
    def box(cx, cy, cz, dx, dy, dz):
        g = bmesh.ops.create_cube(bm, size=1.0)['verts']
        bmesh.ops.scale(bm, verts=g, vec=(dx, dy, dz)); bmesh.ops.translate(bm, verts=g, vec=(cx, cy, cz))
    for s in (-1, 1):
        box(0, s * (ST - skin) / 2, SH / 2, SW, skin, SH)
    ribs = int(SW / pitch)
    for i in range(ribs + 1):
        box(-SW / 2 + skin / 2 + i * (SW - skin) / ribs, 0, SH / 2, skin * 0.9, ST - skin, SH)
    board = mesh_object('Board', bm, rig, smooth=False)
    assign(board, plastic)

    ink_g = principled('InkGreen', (0.020, 0.150, 0.045), 0.36)
    ink_w = principled('InkWhite', (0.90, 0.91, 0.90), 0.40)
    ink_d = principled('InkDark', (0.012, 0.030, 0.014), 0.36)
    yf = -ST / 2

    def plate(name, w, h, cx, cz, mat, lift):
        bm2 = bmesh.new()
        g = bmesh.ops.create_grid(bm2, x_segments=1, y_segments=1, size=0.5)['verts']
        bmesh.ops.scale(bm2, verts=g, vec=(w, h, 1)); bmesh.ops.rotate(bm2, verts=g, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
        bmesh.ops.translate(bm2, verts=g, vec=(cx, yf - lift, cz))
        o = assign(mesh_object(name, bm2, rig, smooth=False), mat); art.append(o); return o

    m = 0.006
    plate('Paper', SW, SH, 0, SH / 2, plastic, 0.00002)
    plate('Field', SW - 2 * m, SH * 0.60, 0, SH - m - SH * 0.30, ink_g, 0.00004)
    plate('Rule', SW - 2 * m, 0.0016, 0, SH * 0.335, ink_d, 0.00004)

    def label(body, size, cx, cz, mat, font, lift=0.00009, tracking=1.0):
        t = text_mesh('Text', body, size, font if os.path.exists(font) else None, parent=rig)
        t.data.space_character = tracking
        t.rotation_euler = (math.pi / 2, 0, 0); t.location = (cx, yf - lift, cz)
        t.data.materials.append(mat); art.append(t); return t

    label('The Lawn', 0.0335, 0, SH * 0.80, ink_w, FONT_WIDE)
    label('Guy', 0.0335, 0, SH * 0.555, ink_w, FONT_WIDE)
    label('Mowing, edging and clean-ups in Bradford', 0.0074, 0, SH * 0.268, ink_d, FONT_REG)
    label('705 555 0142', 0.0200, 0, SH * 0.125, ink_g, FONT_WIDE, tracking=1.04)

    if EXPORT:
        # Photograph the print into one texture; the flutes become a tiling normal map.
        bpy.context.view_layer.update()
        img, _ = web.capture(scene, art, (0, 0, SH / 2), SW, SH, 2048, os.path.join(web.WEB, 'yardsign_print.png'))
        for o in art:
            bpy.data.objects.remove(o)
        xs = np.linspace(0, 1, 64, endpoint=False)
        hgt = np.abs(np.cos(xs * math.tau / 2)) ** 6
        slope = np.gradient(hgt) * 1.6
        nrm = np.zeros((8, 64, 3), dtype=np.float32)
        nrm[..., 0] = 0.5 - 0.5 * slope / np.sqrt(1 + slope ** 2); nrm[..., 1] = 0.5; nrm[..., 2] = 0.5 + 0.5 / np.sqrt(1 + slope ** 2)
        flute = web.array_image('yardsign_flutes', nrm, 'Non-Color')
        face = web.quad('Print', SW, SH, (0, yf - 0.00003, SH / 2), rig)
        face.data.materials.append(web.image_material('Print', base=img, rough=0.40, normal=flute, normal_scale=(SW / pitch / 2, 1)))
    else:
        art[0].hide_render = True                  # the bare board already shows behind the print in the still

    steel = principled('Galvanised', (0.62, 0.63, 0.64), 0.38, 1.0)
    if not EXPORT:
        roughness_breakup(steel, scale=700, amount=0.12, bump=0.05)
    r = 0.0016
    for s in (-1, 1):
        assign(cyl('Prong', (s * PX, 0, TH - 0.045 - z0), (s * PX, 0, SH * 0.72), r, rig), steel)
    for zc in (-0.012, -0.056):
        assign(cyl('Cross', (-PX - 0.004, 0, zc), (PX + 0.004, 0, zc), r, rig), steel)
        for s in (-1, 1):
            bm3 = bmesh.new(); bmesh.ops.create_uvsphere(bm3, u_segments=12, v_segments=8, radius=r * 1.55)
            bead = mesh_object('Weld', bm3, rig); bead.location = (s * PX, 0, zc); bead.scale = (1, 1, 0.8); assign(bead, steel)

    rig.location = (SIGN_POS[0], SIGN_POS[1], z0)
    rig.rotation_euler = (math.radians(-2.2), math.radians(1.2), SIGN_YAW)
    return rig


def build(scene):
    root = link(bpy.data.objects.new('yardsign', None))
    soil, grass = build_turf(root, scene)
    build_sign(root, scene)
    if EXPORT:
        bpy.context.view_layer.update()
        baked = web.apply_to_mesh(soil, root, 'SoilBaked')
        bpy.data.objects.remove(soil)
        web.smart_uv(baked, margin=0.01)
        web.bake_object(scene, baked, 2048, 'yardsign_soil', aux_size=1024)
        baked.name = 'Soil'
    return root


def main():
    if '--check' in ARGS:
        web.check_render('yardsign', FOCUS, RADIUS, **CAM)
        return
    scene = reset()
    root = build(scene)
    bpy.context.view_layer.update()
    print('[hd] yardsign triangles', web.triangles(scene.objects))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'yardsign-web.blend' if EXPORT else 'yardsign.blend'))
    if EXPORT:
        web.export_glb(root, 'yardsign', tangents=False)
    if '--render' in ARGS:
        studio(scene, FOCUS, RADIUS, **CAM)
        render(scene, os.path.join(OUT, 'yardsign.png'), arg('--size', 1400), arg('--samples', 256))


main()
