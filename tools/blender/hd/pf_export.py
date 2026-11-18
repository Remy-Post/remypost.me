"""Web export for the planner and file box (orders R3 + live nodes): bake procedural materials to one atlas,
keep flat materials and text as geometry, keep named interactive parts as their own nodes with their own pivots,
export a glb with one root. Used by planner.py and filebox.py only."""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, '..', 'out', 'hd', 'web')


def _bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def _kind(mat):
    b = _bsdf(mat)
    if b.inputs['Transmission Weight'].default_value > 0:
        return 'glass'
    if any(n.type == 'TEX_IMAGE' for n in mat.node_tree.nodes):
        return 'image'      # already textured on its own UVs: exported as it is
    return 'baked' if len(mat.node_tree.links) > 1 else 'flat'


def _join(obs, name):
    if not obs:
        return None
    with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs, selected_objects=obs, object=obs[0]):
        bpy.ops.object.join()
    obs[0].name = name
    obs[0].data.name = name
    return obs[0]


def _image(name, res, color=True):
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    return img


def _pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(-1, 4)


def _save(img, path):
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


def _face_parts(me):
    a = np.zeros(len(me.polygons), dtype=np.int32)
    me.attributes['part'].data.foreach_get('value', a)
    return a


def _vert_parts(me):
    fp = _face_parts(me)
    vp = np.zeros(len(me.vertices), dtype=np.int32)
    loops = np.zeros(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', loops)
    starts = np.zeros(len(me.polygons), dtype=np.int32)
    totals = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get('loop_start', starts)
    me.polygons.foreach_get('loop_total', totals)
    vp[loops] = np.repeat(fp, totals)
    return vp


def _explode(me, sign):
    """Move every interactive part 10 m apart (and back) so each is occluded only by itself in the AO bake."""
    vp = _vert_parts(me)
    co = np.zeros(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    co[:, 0] += sign * 10.0 * vp
    me.vertices.foreach_set('co', co.ravel())
    me.update()


def _split(ob):
    """Split a joined mesh into one object per part id; returns {part id: object}."""
    out = {}
    ids = sorted(set(_face_parts(ob.data).tolist()))
    for pid in ids:
        me = ob.data.copy()
        bm = bmesh.new()
        bm.from_mesh(me)
        layer = bm.faces.layers.int['part']
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != pid], context='FACES')
        bm.to_mesh(me)
        bm.free()
        me.attributes.remove(me.attributes['part'])
        o = bpy.data.objects.new(f'{ob.name}_{pid}', me)
        bpy.context.scene.collection.objects.link(o)
        out[pid] = o
    bpy.data.objects.remove(ob)
    return out


def export_web(name, root, parts=(), res=2048, ao_samples=96):
    """parts: [{'name': node name, 'objects': [source objects], 'pivot': world Matrix of the node}]"""
    os.makedirs(os.path.join(WEB, 'tex'), exist_ok=True)
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    part_of = {}
    for i, p in enumerate(parts):
        for o in p['objects']:
            part_of[o.name] = i + 1

    # 1. Evaluated, world-space copies of everything, grouped by what their material needs, tagged with their part.
    groups = {'baked': [], 'flat': [], 'glass': [], 'image': []}
    originals = [o for o in scene.objects if o.type in {'MESH', 'FONT', 'CURVE'}]
    for ob in originals:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
        me.transform(ob.matrix_world)
        if not me.polygons or not me.materials or me.materials[0] is None:
            continue
        att = me.attributes.new('part', 'INT', 'FACE')
        att.data.foreach_set('value', np.full(len(me.polygons), part_of.get(ob.name, 0), dtype=np.int32))
        copy = bpy.data.objects.new(ob.name + '_x', me)
        copy['part'] = part_of.get(ob.name, 0)
        scene.collection.objects.link(copy)
        groups[_kind(me.materials[0])].append(copy)
    for ob in originals:
        ob.hide_render = True
        ob.hide_set(True)
    baked = _join(groups['baked'], name + '_baked')
    flat = _join(groups['flat'], name + '_flat')
    glass = _join(groups['glass'], name + '_glass')
    for o in [glass] + groups['image']:
        if o:
            o.hide_render = True

    # 2. One atlas for the baked mesh.
    bpy.context.view_layer.objects.active = baked
    for o in scene.objects:
        o.select_set(o is baked)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 3. Bake. Base colour and metallic go through emission (a metal's diffuse colour pass is black).
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
    scene.render.bake.margin = 12
    scene.render.bake.use_selected_to_active = False
    mats = [m for m in baked.data.materials]
    nodes = {}
    for m in mats:
        n = m.node_tree.nodes.new('ShaderNodeTexImage')
        m.node_tree.nodes.active = n
        nodes[m.name] = n

    def bake(kind, img, samples, **kw):
        for m in mats:
            nodes[m.name].image = img
            m.node_tree.nodes.active = nodes[m.name]
        scene.cycles.samples = samples
        bpy.ops.object.bake(type=kind, **kw)

    img_n = _image(name + '_normal', res, False)
    bake('NORMAL', img_n, 16)
    img_r = _image(name + '_rough', res, False)
    bake('ROUGHNESS', img_r, 8)
    img_ao = _image(name + '_ao', res, False)
    if flat:
        flat.hide_render = True
    _explode(baked.data, 1)
    bake('AO', img_ao, ao_samples)
    _explode(baked.data, -1)
    if flat:
        flat.hide_render = False

    saved = {}
    for m in mats:
        b, nt = _bsdf(m), m.node_tree
        saved[m.name] = b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].is_linked else None
        if saved[m.name]:
            nt.links.new(saved[m.name], b.inputs['Emission Color'])
        else:
            b.inputs['Emission Color'].default_value = b.inputs['Base Color'].default_value
        b.inputs['Emission Strength'].default_value = 1.0
    img_c = _image(name + '_base', res, True)
    bake('EMIT', img_c, 8)
    for m in mats:
        b, nt = _bsdf(m), m.node_tree
        for l in list(b.inputs['Emission Color'].links):
            nt.links.remove(l)
        v = b.inputs['Metallic'].default_value
        b.inputs['Emission Color'].default_value = (v, v, v, 1)
    img_m = _image(name + '_metal', res, False)
    bake('EMIT', img_m, 4)

    # 4. Pack occlusion, roughness, metallic and save.
    orm = _image(name + '_orm', res, False)
    px = np.ones((res * res, 4), dtype=np.float32)
    px[:, 0] = np.clip(_pixels(img_ao)[:, 0] * 0.85 + 0.15, 0, 1)
    px[:, 1] = _pixels(img_r)[:, 0]
    px[:, 2] = _pixels(img_m)[:, 0]
    orm.pixels.foreach_set(px.ravel())
    tex = os.path.join(WEB, 'tex')
    for img, suffix in ((img_c, 'base'), (orm, 'orm'), (img_n, 'normal')):
        _save(img, os.path.join(tex, f'{name}_{suffix}.png'))

    # 5. One image-based material for the baked mesh.
    mat = bpy.data.materials.new(name + '_baked')
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
    grp = bpy.data.node_groups.get('glTF Material Output') or bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    if not grp.interface.items_tree:
        grp.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = grp
    nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])
    baked.data.materials.clear()
    baked.data.materials.append(mat)
    for p in baked.data.polygons:
        p.material_index = 0

    # 6. Split each merged mesh by part; pieces[part id] = [(suffix, object)].
    pieces = {}
    for suffix, ob in (('baked', baked), ('flat', flat), ('glass', glass)):
        if ob:
            for pid, o in _split(ob).items():
                pieces.setdefault(pid, []).append((suffix, o))
    for o in groups['image']:
        o.data.attributes.remove(o.data.attributes['part'])
        pieces.setdefault(o['part'], []).append(('print', o))
    everything = [o for lst in pieces.values() for _, o in lst]

    # 7. One root at the centre of the footprint; each part a node at its pivot.
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in everything:
        for v in o.data.vertices:
            for i in range(3):
                lo[i], hi[i] = min(lo[i], v.co[i]), max(hi[i], v.co[i])
    shift = Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z if lo.z < -1e-5 else 0.0))
    root.name = name + '_source'
    new_root = bpy.data.objects.new(name, None)
    scene.collection.objects.link(new_root)
    tris, report = 0, []
    for pid, lst in sorted(pieces.items()):
        for _, o in lst:
            o.data.transform(shift)
            o.hide_render = False
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
        if pid == 0:
            for suffix, o in lst:
                o.name = o.data.name = f'{name}_{suffix}'
                o.parent = new_root
            continue
        part = parts[pid - 1]
        node_m = shift @ part['pivot']
        inv = node_m.inverted()
        for _, o in lst:
            o.data.transform(inv)
        if len(lst) == 1:
            node = lst[0][1]
            node.name = node.data.name = part['name']
            node.parent = new_root
            node.matrix_world = node_m
        else:
            node = bpy.data.objects.new(part['name'], None)
            scene.collection.objects.link(node)
            node.parent = new_root
            node.matrix_world = node_m
            for suffix, o in lst:
                o.name = o.data.name = f"{part['name']}_{suffix}"
                o.parent = node
                o.matrix_parent_inverse = Matrix.Identity(4)
        everything.append(node)
        t = node_m.to_translation()
        report.append(f"{part['name']}: pivot (Blender, root space) ({t.x * 1000:.1f}, {t.y * 1000:.1f}, {t.z * 1000:.1f}) mm, "
                      f"rot {[round(math.degrees(a), 1) for a in node_m.to_euler()]} deg, children {[s for s, _ in lst]}")
    bpy.context.view_layer.update()
    for o in scene.objects:
        o.select_set(o is new_root or o in everything)
    bpy.context.view_layer.objects.active = new_root
    raw = os.path.join(WEB, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=raw, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                              export_tangents=True, export_cameras=False, export_lights=False, export_image_format='AUTO')
    for line in report:
        print('[web] node', line)
    print(f'[web] {name}: {tris} triangles, raw {os.path.getsize(raw) / 1e6:.2f} MB -> {raw}')
    return raw
