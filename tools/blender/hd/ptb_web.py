"""Bake-and-export helper for pricetag and textbooks (orders R3 + interaction nodes). Owned by the pricetag/textbooks fork.

export_web(name, root, sets, nodes, rig=None)
  sets : [dict(name, mats, size, metal=False, prune=None, tile_normal=None)]  one baked texture set each
  nodes: [dict(name, match, pivot=None, parent=None, group=0, empty=True)]    interaction nodes; first match wins.
         Each node's parts are baked with the node groups pulled apart ("group"), so no part carries the contact
         shadow of a part it can move away from.
  rig  : dict(bones=[(name, head)], weights={node: fn(world_co) -> {bone: w}})  optional skin (joints are glTF nodes)

Check:  Blender --background --python tools/blender/hd/ptb_web.py -- --check <name>   (rest pose, as the still)
        Blender --background --python tools/blender/hd/ptb_web.py -- --pose <name>    (interaction poses + tests)
"""
import bpy, bmesh, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, ARGS, reset, studio, render
from mathutils import Vector, Matrix

WEB = os.path.join(OUT, 'web')
TEX = os.path.join(WEB, 'tex')
os.makedirs(TEX, exist_ok=True)
SPREAD = 1.0          # metres between node groups while baking


def _select(obs, active=None):
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or obs[0]


def _bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def _is_clear(ob):
    return any(m and m.node_tree and _bsdf(m).inputs['Transmission Weight'].default_value > 0 for m in ob.data.materials)


def _mat_of(ob):
    return ob.data.materials[0].name if ob.data.materials and ob.data.materials[0] else ''


def _to_meshes(root, nodes):
    """Replace every renderable object with an applied mesh in world space, tagged with its node index."""
    scene = bpy.context.scene
    srcs = [o for o in scene.objects if o.type in {'MESH', 'CURVE', 'FONT'}]
    nid_of = {}
    for ob in srcs:
        if ob.hide_render:
            continue
        nid_of[ob.name] = next(i for i, n in enumerate(nodes) if n['match'](ob))
        if ob.type == 'FONT':                                   # lettering is most of the triangle count
            ob.data.resolution_u = 3 if ob.data.size < 0.006 else 5
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    made = []
    for ob in srcs:
        if ob.name not in nid_of:
            continue
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
        if not me.polygons:
            continue
        nid = nid_of[ob.name]
        me.transform(Matrix.Translation((nodes[nid].get('group', 0) * SPREAD, 0, 0)) @ ob.matrix_world)
        attr = me.attributes.new('nid', 'INT', 'FACE')
        attr.data.foreach_set('value', [nid] * len(me.polygons))
        new = bpy.data.objects.new(ob.name + '_x', me)
        new['nid'] = nid
        scene.collection.objects.link(new)
        made.append(new)
    for ob in srcs:
        bpy.data.objects.remove(ob, do_unlink=True)
    for ob in list(scene.objects):
        if ob.type == 'EMPTY' and ob is not root:
            bpy.data.objects.remove(ob, do_unlink=True)
    root.matrix_world.identity()
    bpy.context.view_layer.update()
    return made


def _join(obs, name):
    if len(obs) > 1:
        _select(obs, obs[0])
        bpy.ops.object.join()
    obs[0].name = name
    obs[0].data.name = name
    return obs[0]


def _split(ob):
    """Split a joined mesh back into one object per node index. Returns {nid: object}."""
    me = ob.data
    vals = np.zeros(len(me.polygons), dtype=np.int32)
    me.attributes['nid'].data.foreach_get('value', vals)
    out = {}
    for nid in sorted(set(vals.tolist())):
        new = ob.copy()
        new.data = me.copy()
        bpy.context.scene.collection.objects.link(new)
        bm = bmesh.new()
        bm.from_mesh(new.data)
        layer = bm.faces.layers.int['nid']
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[layer] != nid], context='FACES')
        bm.to_mesh(new.data)
        bm.free()
        out[nid] = new
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def _gltf_ao_group():
    g = bpy.data.node_groups.get('glTF Material Output')
    if not g:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        g.nodes.new('NodeGroupInput')
    return g


def _image(name, size, srgb):
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    return img


def _save(img, name):
    img.filepath_raw = os.path.join(TEX, name + '.png')
    img.file_format = 'PNG'
    img.save()


def _weave():
    """A small tileable cloth-weave normal map: 8 x 8 thread crossings."""
    img = bpy.data.images.get('weave_n')
    if img:
        return img
    n, k = 128, 4
    u = (np.arange(n) + 0.5) / n
    U, V = np.meshgrid(u, u)
    a, b = 2 * math.pi * k * U, 2 * math.pi * k * V
    s = 0.55
    dx = s * (np.cos(a) * np.sin(b) + 0.35 * np.cos(2 * a))
    dy = s * (np.sin(a) * np.cos(b) + 0.35 * np.cos(2 * b))
    nz = 1.0 / np.sqrt(dx * dx + dy * dy + 1.0)
    px = np.ones((n, n, 4), dtype=np.float32)
    px[..., 0], px[..., 1], px[..., 2] = 0.5 - 0.5 * dx * nz, 0.5 - 0.5 * dy * nz, 0.5 + 0.5 * nz
    img = _image('weave_n', n, False)
    img.pixels.foreach_set(px.ravel())
    _save(img, 'weave_n')
    return img


def _uv_per_metre(me):
    me.calc_loop_triangles()
    uv = me.uv_layers['bake'].data
    a_uv = 0.0
    for t in me.loop_triangles:
        p, q, r = (uv[i].uv for i in t.loops)
        a_uv += abs((q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)) / 2
    return math.sqrt(a_uv / sum(p.area for p in me.polygons))


def _bake(ob, name, s):
    scene = bpy.context.scene
    size, metal, tile = s['size'], s.get('metal', False), s.get('tile_normal')
    me = ob.data
    if s.get('prune'):
        bm = bmesh.new()
        bm.from_mesh(me)
        s['prune'](bm)
        bm.to_mesh(me)
        bm.free()
    me.uv_layers.new(name='bake')
    me.uv_layers.active = me.uv_layers['bake']       # bake target; the render-active layer stays the source for UV-driven nodes
    _select([ob])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, correct_aspect=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers.active = me.uv_layers['bake']

    imgs = {k: _image(f'{name}_{k}', size, k == 'bc') for k in ('bc', 'rough', 'n', 'ao')}
    nodes, metal_back = [], []
    for mat in me.materials:
        if mat is None:
            continue
        nt = mat.node_tree
        node = nt.nodes.new('ShaderNodeTexImage')
        nt.nodes.active = node
        nodes.append((nt, node))
        metal_back.append((_bsdf(mat), _bsdf(mat).inputs['Metallic'].default_value))

    def run(key, kind, samples, **kw):
        for nt, node in nodes:
            node.image = imgs[key]
            nt.nodes.active = node
        scene.cycles.samples = samples
        _select([ob])
        bpy.ops.object.bake(type=kind, margin=16, use_clear=True, **kw)

    for bsdf, _ in metal_back:                       # a metal has no diffuse colour to bake
        bsdf.inputs['Metallic'].default_value = 0.0
    run('bc', 'DIFFUSE', 8, pass_filter={'COLOR'})
    for bsdf, m in metal_back:
        bsdf.inputs['Metallic'].default_value = m
    run('rough', 'ROUGHNESS', 8)
    if not tile:
        run('n', 'NORMAL', 16)
    run('ao', 'AO', 96)

    n = size * size * 4
    ao = np.empty(n, dtype=np.float32); imgs['ao'].pixels.foreach_get(ao)
    ro = np.empty(n, dtype=np.float32); imgs['rough'].pixels.foreach_get(ro)
    orm = np.ones(n, dtype=np.float32).reshape(-1, 4)
    orm[:, 0] = np.clip(ao.reshape(-1, 4)[:, 0] * 0.85 + 0.15, 0, 1)
    orm[:, 1] = ro.reshape(-1, 4)[:, 0]
    orm[:, 2] = 1.0 if metal else 0.0
    packed = _image(f'{name}_orm', size, False)
    packed.pixels.foreach_set(orm.ravel())
    _save(imgs['bc'], f'{name}_bc')
    _save(packed, f'{name}_orm')
    if not tile:
        _save(imgs['n'], f'{name}_n')

    mat = bpy.data.materials.new(name)               # the web material: textures only
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    def tex(img):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; return t
    nt.links.new(tex(imgs['bc']).outputs['Color'], bsdf.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(tex(packed).outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    grp = nt.nodes.new('ShaderNodeGroup'); grp.node_tree = _gltf_ao_group()
    nt.links.new(sep.outputs['Red'], grp.inputs['Occlusion'])
    nm = nt.nodes.new('ShaderNodeNormalMap')
    if tile:                                         # a repeating weave instead of a baked map: sharper and far smaller
        rep = 1.0 / (_uv_per_metre(me) * tile)
        coord = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (rep, rep, 1)
        t = tex(_weave())
        nt.links.new(coord.outputs['UV'], mp.inputs['Vector'])
        nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
        nm.inputs['Strength'].default_value = 0.6
        print(f'[web] {name} weave repeats {rep:.1f} per UV unit')
    else:
        t = tex(imgs['n'])
    nt.links.new(t.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])

    for l in [l for l in me.uv_layers if l.name != 'bake']:
        me.uv_layers.remove(l)
    me.materials.clear()
    me.materials.append(mat)
    for p in me.polygons:
        p.material_index = 0


def export_web(name, root, sets, nodes, rig=None):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = 'GPU'
    except Exception as err:
        print('[web] GPU unavailable:', err)
    scene.cycles.use_denoising = False

    meshes = _to_meshes(root, nodes)
    groups = {}
    for o in meshes:
        m = _mat_of(o)
        s = next((s for s in sets if m in s['mats']), None)
        key = ('set', s['name']) if s else ('clear', o['nid'], m) if _is_clear(o) else ('plain', o['nid'])
        groups.setdefault(key, []).append(o)
    joined = {key: _join(obs, 'tmp_' + '_'.join(str(k) for k in key)) for key, obs in groups.items()}

    final = []                                        # (object, nid, mesh name)
    for s in sets:
        ob = joined.get(('set', s['name']))
        if not ob:
            print('[web] empty set', s['name']); continue
        _bake(ob, f"{name}_{s['name']}", s)
        print('[web] baked', s['name'], len(ob.data.polygons), 'faces')
        for nid, part in _split(ob).items():
            final.append((part, nid, f"{nodes[nid]['name']}_{s['name']}"))
    for key, ob in joined.items():
        if key[0] == 'plain':
            final.append((ob, key[1], f"{nodes[key[1]]['name']}_parts"))
        elif key[0] == 'clear':
            final.append((ob, key[1], key[2].lower()))

    pivot = lambda n: Vector(n['pivot']) if n.get('pivot') is not None and n.get('empty', True) else Vector((0, 0, 0))
    by_name = {n['name']: n for n in nodes}
    empties = {}
    for n in nodes:
        if n.get('empty', True):
            e = bpy.data.objects.new(n['name'], None)
            scene.collection.objects.link(e)
            empties[n['name']] = e
    for n in nodes:
        if n['name'] in empties:
            par = n.get('parent')
            empties[n['name']].parent = empties[par] if par else root
            empties[n['name']].location = pivot(n) - (pivot(by_name[par]) if par else Vector((0, 0, 0)))

    arm = None
    if rig:
        data = bpy.data.armatures.new('rig')
        arm = bpy.data.objects.new('rig', data)
        scene.collection.objects.link(arm)
        arm.parent = root
        _select([arm])
        bpy.ops.object.mode_set(mode='EDIT')
        for bname, head in rig['bones']:
            b = data.edit_bones.new(bname)
            b.head = Vector(head)
            b.tail = Vector(head) + Vector((0, 0, 0.03))      # straight up, roll 0: the glTF joint's rest rotation is identity
            b.roll = 0
        bpy.ops.object.mode_set(mode='OBJECT')

    tris = 0
    for ob, nid, mname in final:
        n = nodes[nid]
        me = ob.data
        me.transform(Matrix.Translation(-Vector((n.get('group', 0) * SPREAD, 0, 0)) - pivot(n)))
        if 'nid' in me.attributes:
            me.attributes.remove(me.attributes['nid'])
        ob.name = mname
        me.name = mname
        ob.parent = empties.get(n['name'], root)
        if rig and n['name'] in rig['weights']:
            fn = rig['weights'][n['name']]
            vg = {bname: ob.vertex_groups.new(name=bname) for bname, _ in rig['bones']}
            for v in me.vertices:
                for bname, w in fn(v.co).items():
                    if w > 0:
                        vg[bname].add([v.index], w, 'REPLACE')
            ob.modifiers.new('Armature', 'ARMATURE').object = arm
            ob.parent = arm
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        print(f'[web]   {mname}: {len(me.loop_triangles)} tris')
    print(f'[web] {name} triangles', tris)

    bpy.context.view_layer.update()
    _select([o for o in scene.objects], root)
    path = os.path.join(WEB, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_animations=False, export_image_format='AUTO')
    print('[web] wrote', path, os.path.getsize(path))


# ---------------------------------------------------------------- checks

CHECKS = {
    'pricetag': dict(focus=(0, -0.004, 0.052), radius=0.058, azimuth=-27, elevation=13, lens=90, distance=0.52),
    'textbooks': dict(focus=(0, 0, 0.105), radius=0.17, azimuth=-30, elevation=17, lens=85, distance=1.02),
}


def _load(nm):
    sc = reset()
    here = os.path.dirname(os.path.abspath(__file__))
    bpy.ops.import_scene.gltf(filepath=os.path.join(here, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models', nm + '.glb'))
    for o in sc.objects:
        print('[check] node', o.type, o.name, '<-', o.parent.name if o.parent else None, tuple(round(v, 4) for v in o.matrix_world.translation))
    return sc


def _shoot(sc, nm, suffix):
    c = CHECKS[nm]
    studio(sc, c['focus'], c['radius'], azimuth=c['azimuth'], elevation=c['elevation'], lens=c['lens'], distance=c['distance'])
    render(sc, os.path.join(WEB, f'{nm}-{suffix}.png'), 1000, 128)


def _world_bvh(prefix):
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    verts, polys, zmin = [], [], 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o.name.startswith(prefix):
            ev = o.evaluated_get(deps)
            me = ev.to_mesh()
            base = len(verts)
            for v in me.vertices:
                w = ev.matrix_world @ v.co
                verts.append(w)
                zmin = min(zmin, w.z)
            polys += [[base + i for i in p.vertices] for p in me.polygons]
            ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), zmin


def _pose_pricetag(sc):
    rig = next(o for o in sc.objects if o.type == 'ARMATURE')
    pb = rig.pose.bones['card']
    piv = Vector((0, 0, 0.009))
    for label, deg in (('rest', 0), ('back', 8), ('forward', -8)):
        world = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-deg), 4, 'X') @ Matrix.Translation(-piv)
        pb.matrix = rig.matrix_world.inverted() @ world @ rig.matrix_world @ pb.bone.matrix_local
        bpy.context.view_layer.update()
        card, _ = _world_bvh('card_')
        string, zmin = _world_bvh('string_')
        holder, _ = _world_bvh('holder_')
        print(f'[pose] {label:8s} card x holder {len(card.overlap(holder))}  string x card {len(string.overlap(card))}  '
              f'string x holder {len(string.overlap(holder))}  string lowest z {zmin * 1000:.2f} mm')
        if deg:
            _shoot(sc, 'pricetag', 'pose-' + label)
            for o in [o for o in sc.objects if o.type in {'LIGHT', 'CAMERA'} or o.name == 'Cove']:
                bpy.data.objects.remove(o, do_unlink=True)


def _pose_textbooks(sc):
    b = sc.objects['book_3']
    b.rotation_mode = 'XYZ'
    b.rotation_euler.z += math.radians(-16)
    b.location += Vector((0.05, -0.035, 0))
    _shoot(sc, 'textbooks', 'pose')


if '--check' in ARGS:
    nm = ARGS[ARGS.index('--check') + 1]
    _shoot(_load(nm), nm, 'check')
if '--pose' in ARGS:
    nm = ARGS[ARGS.index('--pose') + 1]
    (_pose_pricetag if nm == 'pricetag' else _pose_textbooks)(_load(nm))
