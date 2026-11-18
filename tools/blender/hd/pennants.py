"""Education: two felt school pennants ("Lakehead", "Georgian") on turned sticks in a weighted brass desk stand.

  Blender --background --python tools/blender/hd/pennants.py -- --render [--size N --samples N]
  Blender --background --python tools/blender/hd/pennants.py -- --export      (bake + raw glb in out/hd/web)
  Blender --background --python tools/blender/hd/pennants.py -- --check       (re-import the shipped glb, render)

Nodes in the glb: pennants > stand, pennant_lakehead, pennant_georgian (pivots at the stick's foot), each pennant
holding <name>_stick and <name>_cloth. The cloth carries a second UV set: u = 0 at the hoist, 1 at the tip, v = 0..1
across, so a vertex shader can run a wave along it.
"""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
import numpy as np
from mathutils import Vector, Matrix

MM = 0.001
FONT = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')
WEB = os.path.join(OUT, 'web')
L, H, T = 285 * MM, 112 * MM, 1.7 * MM          # pennant length, hoist height, felt thickness
STICK = 3.2 * MM                                 # stick radius


# ── materials ────────────────────────────────────────────────────────────────
def felt(name, color):
    mat = principled(name, color, 0.94, 0.0, Sheen_Weight=0.55, Sheen_Roughness=0.55)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    fibre = nt.nodes.new('ShaderNodeTexNoise')
    fibre.inputs['Scale'].default_value = 1500
    fibre.inputs['Detail'].default_value = 6
    fibre.inputs['Roughness'].default_value = 0.7
    clump = nt.nodes.new('ShaderNodeTexNoise')
    clump.inputs['Scale'].default_value = 140
    clump.inputs['Detail'].default_value = 4
    nt.links.new(coord.outputs['Object'], fibre.inputs['Vector'])
    nt.links.new(coord.outputs['Object'], clump.inputs['Vector'])
    mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'ADD'
    half = nt.nodes.new('ShaderNodeMath'); half.operation = 'MULTIPLY'; half.inputs[1].default_value = 0.45
    nt.links.new(clump.outputs['Fac'], half.inputs[0])
    nt.links.new(fibre.outputs['Fac'], mix.inputs[0])
    nt.links.new(half.outputs['Value'], mix.inputs[1])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 1.0
    bump.inputs['Distance'].default_value = 0.0011
    nt.links.new(mix.outputs['Value'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    # Mottled colour: fibres catch light unevenly.
    tone = nt.nodes.new('ShaderNodeMixRGB'); tone.blend_type = 'MULTIPLY'
    tone.inputs['Color1'].default_value = (*color, 1)
    ramp = nt.nodes.new('ShaderNodeMapRange')
    ramp.inputs['To Min'].default_value = 0.72
    ramp.inputs['To Max'].default_value = 1.12
    nt.links.new(mix.outputs['Value'], ramp.inputs['Value'])
    grey = nt.nodes.new('ShaderNodeCombineColor')
    for ch in ('Red', 'Green', 'Blue'):
        nt.links.new(ramp.outputs['Result'], grey.inputs[ch])
    tone.inputs['Fac'].default_value = 1.0
    nt.links.new(grey.outputs['Color'], tone.inputs['Color2'])
    nt.links.new(tone.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def wood(name):
    mat = principled(name, (0.42, 0.25, 0.12), 0.42, 0.0, Coat_Weight=0.35, Coat_Roughness=0.25)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (160, 160, 9)       # grain runs along the stick (local Z)
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 1.0
    noise.inputs['Detail'].default_value = 9
    noise.inputs['Distortion'].default_value = 1.6
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.32, (0.24, 0.13, 0.06, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.72, (0.56, 0.36, 0.18, 1)
    nt.links.new(coord.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


# ── geometry ─────────────────────────────────────────────────────────────────
def wave(co, phase):
    """Hang of the cloth: a soft S along the fly and a little droop. Input in pennant space (x along the fly)."""
    u = max(0.0, min(1.0, co.x / L))
    return Vector((co.x, co.y + 21 * MM * math.sin(2.3 * math.pi * u + phase) * u ** 1.1, co.z - 26 * MM * u * u))


def cloth_mesh(name, phase, parent, z0):
    """A tapered felt triangle, 56 x 10 quads, with real thickness; hoist at x = 0, centre line at z0."""
    nx, nz = 56, 10
    bm = bmesh.new()
    rows = []
    for i in range(nx + 1):
        u = i / nx
        hh = (H / 2) * (1 - u) + 1.4 * MM * u
        rows.append([bm.verts.new((u * L, 0, z0 + hh * (2 * j / nz - 1))) for j in range(nz + 1)])
    for a, b in zip(rows, rows[1:]):
        for j in range(nz):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    for v in bm.verts:
        v.co = wave(v.co, phase)
    ob = mesh_object(name, bm, parent)
    sol = ob.modifiers.new('Solidify', 'SOLIDIFY')
    sol.thickness, sol.offset = T, 0
    bev = ob.modifiers.new('Bevel', 'BEVEL')
    bev.width, bev.segments, bev.limit_method, bev.angle_limit = 0.5 * MM, 2, 'ANGLE', math.radians(50)
    return ob


def letters(word, phase, parent, z0, mat):
    """Flocked lettering that tapers continuously with the cloth, as on a real pennant; raised off the felt.

    The word is set once at cap height 1 (the font's own advances, plus a little tracking), then every vertex
    (s, t) is mapped onto the triangle: letter height at x is c * (1 - x / L), so dx/ds = c * (1 - x / L) and
    x(s) = L - (L - x0) * exp(-c * s / L). Heights and spacing shrink together, smoothly, toward the tip."""
    c, xs = 0.54 * H, 24 * MM
    cu = bpy.data.curves.new('word', 'FONT')
    cu.body, cu.size, cu.extrude = word, 1 / 0.687, 0.5
    cu.align_x, cu.align_y = 'LEFT', 'BOTTOM'
    cu.space_character = 1.06
    cu.resolution_u = 4
    if os.path.exists(FONT):
        cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    tmp = bpy.data.objects.new('word', cu)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps), depsgraph=deps)
    bpy.data.objects.remove(tmp)
    bm = bmesh.new()
    bm.from_mesh(me)
    s0 = min(v.co.x for v in bm.verts)
    # Slice the word every 0.2 cap heights so straight strokes follow the taper and the cloth's curve.
    s1 = max(v.co.x for v in bm.verts)
    k = s0 + 0.2
    while k < s1:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(k, 0, 0), plane_no=(1, 0, 0))
        k += 0.2
    for v in bm.verts:
        x = L - (L - xs) * math.exp(-c * (v.co.x - s0) / L)
        cap = c * (1 - x / L)
        # text plane XY, facing +Z  ->  pennant plane XZ, facing -Y; relief 0.28 mm
        p = Vector((x, -(T / 2 + 0.30 * MM) - (0.28 * MM if v.co.z > 0 else -0.28 * MM), z0 + cap * (v.co.y - 0.5)))
        v.co = wave(p, phase)
    ob = mesh_object('lettering', bm, parent, smooth=False)
    assign(ob, mat)
    return [ob]


def box(name, size, loc, parent, mat, bev=0.0, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=size)
    if rot:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, verts=bm.verts, vec=loc)
    ob = mesh_object(name, bm, parent)
    if bev:
        bevel(ob, bev, 3, 60)
    return assign(ob, mat)


def pennant(key, word, body, trim, tilt, foot, stick_len, phase, root, wood_mat):
    """One pennant in its own frame: origin at the stick's foot, stick along +Z, cloth flying toward +X."""
    pivot = link(bpy.data.objects.new('pennant_' + key, None), root)
    pivot.location = foot
    pivot.rotation_euler = (0, tilt, 0)
    felt_a, felt_b = felt('Felt_' + key, body), felt('FeltTrim_' + key, trim)
    thread = principled('Thread_' + key, tuple(min(1.0, c * 1.25 + 0.05) for c in trim), 0.8)

    # Turned stick: a slim dowel with a ball finial and two turned rings.
    r = STICK
    prof = [(0, 0), (r, 0), (r, stick_len - 26 * MM), (r * 1.45, stick_len - 24 * MM), (r * 1.45, stick_len - 22.5 * MM),
            (r * 0.9, stick_len - 21 * MM), (r * 0.9, stick_len - 15 * MM), (r * 1.3, stick_len - 13.5 * MM),
            (r * 0.75, stick_len - 11 * MM)]
    prof += [(r * 1.75 * math.sin(a), stick_len - 5.5 * MM - r * 1.75 * math.cos(a)) for a in [math.radians(d) for d in range(25, 181, 13)]]
    prof.append((0, stick_len - 5.5 * MM + r * 1.75))
    stick = lathe(key + '_stick_mesh', prof, 28, pivot)
    assign(stick, wood_mat)

    z0 = stick_len - 34 * MM - H / 2
    cloth = cloth_mesh(key + '_felt', phase, pivot, z0)
    cloth.location.x = r + 1.0 * MM
    assign(cloth, felt_a)
    parts = [cloth]
    for g in letters(word, phase, pivot, z0, felt_b):
        g.location.x = r + 1.0 * MM
        parts.append(g)

    # Binding strip folded round the hoist, two rows of stitches, and two ties knotted round the stick.
    bind = box(key + '_binding', (15 * MM, T + 1.3 * MM, H + 3 * MM), (r + 7.5 * MM, 0, z0), pivot, felt_b, 0.45 * MM)
    parts.append(bind)
    for row_x in (r + 3.2 * MM, r + 12.6 * MM):
        n = 22
        for i in range(n):
            z = z0 - H / 2 + 3 * MM + (H - 6 * MM) * i / (n - 1)
            parts.append(box(key + '_stitch', (0.55 * MM, 0.5 * MM, 2.7 * MM), (row_x, -(T / 2 + 0.72 * MM), z), pivot, thread))
    for tz in (z0 + H / 2 - 9 * MM, z0 - H / 2 + 9 * MM):
        ring = lathe(key + '_tie', [(r + 0.2 * MM, tz - 2.6 * MM), (r + 1.5 * MM, tz - 2.2 * MM), (r + 1.5 * MM, tz + 2.2 * MM), (r + 0.2 * MM, tz + 2.6 * MM)], 20, pivot)
        assign(ring, felt_b)
        parts.append(ring)
        for s, ang in ((1, 0.5), (-1, -0.35)):
            tail = box(key + '_tietail', (15 * MM, 1.1 * MM, 4.2 * MM), (-r - 6 * MM, s * 1.2 * MM, tz - 3 * MM), pivot, felt_b, 0.3 * MM,
                       Matrix.Rotation(ang, 3, 'Y'))
            parts.append(tail)
    return pivot, stick, parts


def build():
    root = link(bpy.data.objects.new('pennants', None))
    brass = principled('Brass', (0.83, 0.62, 0.30), 0.24, 1.0)
    roughness_breakup(brass, scale=380, amount=0.07, stretch=(1, 1, 30))
    dark = principled('Rubber', (0.02, 0.02, 0.022), 0.8)
    wood_mat = wood('Beech')

    # Weighted stand: a stepped brass disc with a domed boss, on a felt/rubber foot.
    stand = link(bpy.data.objects.new('stand', None), root)
    base = lathe('stand_base', [(r * MM, z * MM) for r, z in [
        (0, 1.2), (44, 1.2), (46, 2.6), (46, 9.5), (44.6, 11), (38, 11.6), (36.5, 13.2), (19, 14.2), (16.5, 16.4), (15, 24),
        (13.2, 27.5), (9.5, 29.6), (0, 30.2)]], 96, stand)
    bevel(base, 0.5 * MM, 3, 25)
    assign(base, brass)
    foot = lathe('stand_foot', [(0, 0), (43 * MM, 0), (44 * MM, 1.2 * MM), (0, 1.2 * MM)], 64, stand)
    assign(foot, dark)

    a = pennant('lakehead', 'LAKEHEAD', (0.012, 0.028, 0.115), (0.80, 0.52, 0.09), math.radians(-7), (-5 * MM, 4 * MM, 22 * MM), 392 * MM, 0.4, root, wood_mat)
    b = pennant('georgian', 'GEORGIAN', (0.012, 0.105, 0.05), (0.70, 0.68, 0.62), math.radians(9), (6 * MM, -5 * MM, 22 * MM), 262 * MM, 2.1, root, wood_mat)
    bpy.context.view_layer.update()
    return root, stand, [base, foot], [a, b]


# ── web export ───────────────────────────────────────────────────────────────
def _bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def _px(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


def _img(name, res, color):
    img = bpy.data.images.new(name, res, res, alpha=False)
    img.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return img


def world_copy(obs, name):
    """Evaluated, world-space, joined copy of a group of objects."""
    scene = bpy.context.scene
    deps = bpy.context.evaluated_depsgraph_get()
    copies = []
    for ob in obs:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
        me.transform(ob.matrix_world)
        for layer in list(me.uv_layers):
            me.uv_layers.remove(layer)
        c = bpy.data.objects.new(name, me)
        scene.collection.objects.link(c)
        copies.append(c)
    with bpy.context.temp_override(active_object=copies[0], selected_editable_objects=copies, selected_objects=copies, object=copies[0]):
        bpy.ops.object.join()
    copies[0].name = copies[0].data.name = name
    copies[0].data.uv_layers.new(name='UVMap')
    return copies[0]


def unwrap(obs):
    for o in bpy.context.scene.objects:
        o.select_set(o in obs)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_set(name, obs, res, sheen=0.0):
    """Bake every material on `obs` into one base colour / ORM / normal set and give them one image material."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = 'GPU'
    except Exception as err:
        print('[web] GPU unavailable:', err)
    scene.render.bake.margin = 10
    scene.render.bake.use_selected_to_active = False
    unwrap(obs)
    mats = []
    for o in obs:
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
    nodes = {}
    for m in mats:
        n = m.node_tree.nodes.new('ShaderNodeTexImage')
        nodes[m.name] = n

    def bake(kind, img, samples):
        scene.cycles.samples = samples
        for m in mats:
            nodes[m.name].image = img
            m.node_tree.nodes.active = nodes[m.name]
        for i, o in enumerate(obs):
            for s in scene.objects:
                s.select_set(s is o)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.bake(type=kind, use_clear=(i == 0))

    img_n = _img(name + '_normal', res, False); bake('NORMAL', img_n, 16)
    img_r = _img(name + '_rough', res, False); bake('ROUGHNESS', img_r, 8)
    img_ao = _img(name + '_ao', res, False); bake('AO', img_ao, 64)
    for m in mats:
        b, nt = _bsdf(m), m.node_tree
        if b.inputs['Base Color'].is_linked:
            nt.links.new(b.inputs['Base Color'].links[0].from_socket, b.inputs['Emission Color'])
        else:
            b.inputs['Emission Color'].default_value = b.inputs['Base Color'].default_value
        b.inputs['Emission Strength'].default_value = 1.0
    img_c = _img(name + '_base', res, True); bake('EMIT', img_c, 8)
    for m in mats:
        b, nt = _bsdf(m), m.node_tree
        for l in list(b.inputs['Emission Color'].links):
            nt.links.remove(l)
        v = b.inputs['Metallic'].default_value
        b.inputs['Emission Color'].default_value = (v, v, v, 1)
    img_m = _img(name + '_metal', res, False); bake('EMIT', img_m, 4)

    orm = _img(name + '_orm', res, False)
    px = np.ones((res * res, 4), dtype=np.float32)
    px[:, 0] = np.clip(_px(img_ao)[:, 0] * 0.8 + 0.2, 0, 1)
    px[:, 1] = _px(img_r)[:, 0]
    px[:, 2] = _px(img_m)[:, 0]
    orm.pixels.foreach_set(px.ravel())
    os.makedirs(os.path.join(WEB, 'tex'), exist_ok=True)
    for img, suffix in ((img_c, 'base'), (orm, 'orm'), (img_n, 'normal')):
        img.filepath_raw = os.path.join(WEB, 'tex', f'{name}_{suffix}.png')
        img.file_format = 'PNG'
        img.save()

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = _bsdf(mat)
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = img_c
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = orm
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img_n
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(tc.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(to.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
        b.inputs['Sheen Roughness'].default_value = 0.55
    grp = bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    if not grp.interface.items_tree:
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = grp
    nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])
    for o in obs:
        o.data.materials.clear()
        o.data.materials.append(mat)
        for p in o.data.polygons:
            p.material_index = 0
    return mat


def export(root, stand, stand_parts, pennant_sets):
    scene = bpy.context.scene
    originals = [o for o in scene.objects if o.type == 'MESH']
    stand_x = world_copy(stand_parts, 'stand_mesh')
    sticks, cloths, frames = [], [], []
    for pivot, stick, parts in pennant_sets:
        key = pivot.name.replace('pennant_', '')
        sticks.append(world_copy([stick], key + '_stick'))
        c = world_copy(parts, key + '_cloth')
        # Second UV set for the wave: distance along the fly and across the hoist, in the pennant's own frame.
        inv = pivot.matrix_world.inverted()
        layer = c.data.uv_layers.new(name='wave')
        zs = [(inv @ v.co).z for v in c.data.vertices]
        zlo, zhi = min(zs), max(zs)
        for loop in c.data.loops:
            p = inv @ c.data.vertices[loop.vertex_index].co
            layer.data[loop.index].uv = (max(0.0, min(1.0, (p.x - STICK) / L)), (p.z - zlo) / (zhi - zlo))
        c.data.uv_layers.active = c.data.uv_layers['UVMap']
        cloths.append(c)
        frames.append(pivot)
    for o in originals:
        o.hide_render = True
        o.hide_set(True)

    bake_set('pennants_hard', [stand_x] + sticks, 1024)
    for c in cloths:
        bake_set(c.name, [c], 2048, sheen=0.5)

    # Hierarchy: every mesh keeps its world position under its named node.
    def adopt(child, parent):
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted()
    adopt(stand_x, stand)
    tris = 0
    for pivot, s, c in zip(frames, sticks, cloths):
        adopt(s, pivot)
        adopt(c, pivot)
    keep = [root, stand, stand_x] + frames + sticks + cloths
    for o in keep:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    for o in scene.objects:
        o.hide_set(False) if o in keep else None
        o.select_set(o in keep)
    bpy.context.view_layer.objects.active = root
    raw = os.path.join(WEB, 'pennants.glb')
    bpy.ops.export_scene.gltf(filepath=raw, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                              export_tangents=True, export_cameras=False, export_lights=False, export_image_format='AUTO')
    print(f'[web] pennants: {tris} triangles, raw {os.path.getsize(raw) / 1e6:.2f} MB -> {raw}')


VIEW = dict(focus=(0.115, 0, 0.205), radius=0.17, azimuth=-26, elevation=8, lens=85, distance=1.2)


def shoot(scene, path, size, samples):
    v = VIEW
    studio(scene, v['focus'], v['radius'], azimuth=v['azimuth'], elevation=v['elevation'], lens=v['lens'], distance=v['distance'])
    render(scene, path, size, samples)


def main():
    scene = reset()
    if '--check' in ARGS:
        bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models', 'pennants.glb'))
        shoot(scene, os.path.join(WEB, 'pennants-check.png'), 1000, 128)
        return
    root, stand, stand_parts, sets = build()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'pennants.blend'))
    if '--render' in ARGS:
        shoot(scene, os.path.join(OUT, 'pennants.png'), arg('--size', 1400), arg('--samples', 256))
    if '--export' in ARGS:
        export(root, stand, stand_parts, sets)


main()
