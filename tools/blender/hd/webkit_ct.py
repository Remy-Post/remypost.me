"""Bake-and-export helpers for the cloche and take-out box (this fork's own file; common.py is not edited).

realize()  : convert every curve/text and apply every modifier
join()     : merge objects into one mesh
bake_set() : unwrap, bake base colour / roughness / metallic / normal / AO from the procedural materials,
             pack ORM, and replace the materials with one glTF-ready textured material
flatten()  : strip procedural links from a material that ships as plain factors
export()   : write the raw .glb for a root
check()    : re-import a .glb for the verification render
"""
import bpy, bmesh, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, '..', 'out', 'hd', 'web')
TEX = os.path.join(WEB, 'tex')
os.makedirs(TEX, exist_ok=True)


def _only(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def realize(root):
    objs = [o for o in root.children_recursive if o.type in {'MESH', 'CURVE', 'FONT'}
            and not (o.type == 'MESH' and o.data.shape_keys)]   # morph-target meshes stay as built
    _only(objs)
    bpy.ops.object.convert(target='MESH')
    return [o for o in root.children_recursive if o.type == 'MESH']


def join(objs, name):
    objs = [o for o in objs if o]
    _only(objs)
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def tri_count(root):
    total = 0
    for ob in root.children_recursive:
        if ob.type == 'MESH':
            ob.data.calc_loop_triangles()
            total += len(ob.data.loop_triangles)
    return total


def unwrap(ob, margin=0.004, angle=66):
    _only([ob])
    for uv in list(ob.data.uv_layers):
        ob.data.uv_layers.remove(uv)
    ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def _bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def _output(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')


class _Emit:
    """Temporarily show one Principled input as emission, so it can be baked with the EMIT pass."""

    def __init__(self, mats, socket):
        self.mats, self.socket, self.made = mats, socket, []

    def __enter__(self):
        for mat in self.mats:
            nt = mat.node_tree
            bsdf, out = _bsdf(mat), _output(mat)
            e = nt.nodes.new('ShaderNodeEmission')
            sock = bsdf.inputs[self.socket]
            if sock.is_linked:
                nt.links.new(sock.links[0].from_socket, e.inputs['Color'])
            else:
                v = sock.default_value
                e.inputs['Color'].default_value = tuple(v) if hasattr(v, '__len__') else (v, v, v, 1)
            nt.links.new(e.outputs['Emission'], out.inputs['Surface'])
            self.made.append((mat, e))

    def __exit__(self, *exc):
        for mat, e in self.made:
            nt = mat.node_tree
            nt.nodes.remove(e)
            nt.links.new(_bsdf(mat).outputs['BSDF'], _output(mat).inputs['Surface'])


def _gltf_output_group():
    g = bpy.data.node_groups.get('glTF Material Output')
    if not g:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        g.nodes.new('NodeGroupInput')
    return g


def bake_set(ob, key, size=2048, sources=None, extrusion=0.0006, ao=True, coat=None, samples_ao=96):
    """Bake `ob`'s procedural materials to <key>_base / _orm / _normal and give it one textured material.

    `sources`: other objects whose surface colour is projected onto `ob` (printed marks); they are not kept.
    """
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception as err:
        print('[web] GPU unavailable:', err)
    scene.render.bake.margin = max(4, size // 128)
    scene.render.bake.use_clear = True

    unwrap(ob)
    mats = [s.material for s in ob.material_slots if s.material]
    src_mats = list({s.material for o in (sources or []) for s in o.material_slots if s.material})

    def image(kind, colour):
        img = bpy.data.images.new(f'{key}_{kind}', size, size, alpha=False, float_buffer=False)
        img.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        return img

    def target(img):
        for mat in mats:
            nt = mat.node_tree
            node = nt.nodes.get('BakeTarget') or nt.nodes.new('ShaderNodeTexImage')
            node.name = 'BakeTarget'
            node.image = img
            for n in nt.nodes:
                n.select = False
            node.select = True
            nt.nodes.active = node

    def run(kind, s2a=False, samples=8):
        scene.cycles.samples = samples
        if s2a:
            _only([ob] + list(sources), ob)
        else:
            _only([ob])
        bpy.ops.object.bake(type=kind, use_selected_to_active=s2a, cage_extrusion=extrusion, max_ray_distance=extrusion * 3,
                            normal_space='TANGENT', margin=scene.render.bake.margin)

    base = image('base', True)
    target(base)
    with _Emit(list(dict.fromkeys(mats + src_mats)), 'Base Color'):
        # With sources (a copy of the object plus its printed marks) every ray lands on something.
        run('EMIT', s2a=bool(sources))
    rough = image('rough', False)
    target(rough)
    run('ROUGHNESS')
    metal = image('metal', False)
    target(metal)
    with _Emit(mats, 'Metallic'):
        run('EMIT')
    normal = image('normal', False)
    target(normal)
    run('NORMAL', samples=16)
    occ = image('ao', False)
    if ao:
        target(occ)
        run('AO', samples=samples_ao)

    def px(img):
        a = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(-1, 4)

    orm = image('orm', False)
    packed = np.ones((size * size, 4), dtype=np.float32)
    packed[:, 0] = px(occ)[:, 0] if ao else 1.0
    packed[:, 1] = px(rough)[:, 0]
    packed[:, 2] = px(metal)[:, 0]
    orm.pixels.foreach_set(packed.ravel())

    for img in (base, orm, normal):
        img.filepath_raw = os.path.join(TEX, img.name + '.png')
        img.file_format = 'PNG'
        img.save()

    # One glTF-ready material.
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    tb = nt.nodes.new('ShaderNodeTexImage'); tb.image = base
    to = nt.nodes.new('ShaderNodeTexImage'); to.image = orm
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = normal
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(tb.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(to.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if ao:
        grp = nt.nodes.new('ShaderNodeGroup')
        grp.node_tree = _gltf_output_group()
        nt.links.new(sep.outputs['Red'], grp.inputs['Occlusion'])
    if coat:
        bsdf.inputs['Coat Weight'].default_value, bsdf.inputs['Coat Roughness'].default_value = coat
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.material_index = 0
    for o in sources or []:
        bpy.data.objects.remove(o, do_unlink=True)
    return mat


def flatten(mat):
    """Ship this material as plain factors: drop every procedural link into the Principled node."""
    nt = mat.node_tree
    bsdf = _bsdf(mat)
    for sock in bsdf.inputs:
        for l in list(sock.links):
            nt.links.remove(l)
    for name in ('Subsurface Weight', 'Sheen Weight', 'Anisotropic'):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = 0.0
    return mat


def export(root, name):
    _only([root] + list(root.children_recursive), root)
    path = os.path.join(WEB, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_animations=False, export_tangents=True)
    print('[web] exported', path, os.path.getsize(path), 'bytes')
    return path


def check_scene(name):
    """A fresh scene holding only the shipped model."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dest = os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models', name + '.glb')
    bpy.ops.import_scene.gltf(filepath=dest)
    return bpy.context.scene
