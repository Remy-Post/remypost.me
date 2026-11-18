"""Web-export helpers shared by yardsign.py and window.py (this fork's own file).

capture(): photograph flat artwork (print, screen pixels) straight-on into a texture.
bake_object(): bake a procedural Principled material to base colour / ORM / normal images.
export_glb(): write the raw .glb and run gltf-transform. check_render(): re-import and render the result.
"""
import bpy, bmesh, math, os, subprocess, sys
import numpy as np
from mathutils import Vector, Matrix
from common import OUT, HERE, link, principled, studio, render

WEB = os.path.join(OUT, 'web')
os.makedirs(WEB, exist_ok=True)
MODELS = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models'))


def bsdf_of(mat):
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def capture(scene, objs, centre, width, height, px, path, emissive=False, alpha=False, peak=None):
    """Render `objs` (flat, facing -Y) with an orthographic camera and no lighting. Returns the saved image.

    Non-emissive materials are photographed by their base colour; emissive ones by colour x strength,
    normalised so the brightest pixel is white (the returned gain restores it).
    """
    keep = {o: o.hide_render for o in scene.objects}
    for o in scene.objects:
        o.hide_render = o not in objs
    swapped = []
    if not emissive:
        peak = 1.0
    elif peak is None:
        peak = max(bsdf_of(m).inputs['Emission Strength'].default_value * max(bsdf_of(m).inputs['Emission Color'].default_value[:3])
                   for o in objs for m in o.data.materials)
    cache = {}
    for o in objs:
        for i, m in enumerate(o.data.materials):
            if m.name not in cache:
                b = bsdf_of(m)
                if emissive:
                    col = [c * b.inputs['Emission Strength'].default_value / peak for c in b.inputs['Emission Color'].default_value[:3]]
                else:
                    col = list(b.inputs['Base Color'].default_value[:3])
                flat = bpy.data.materials.new('Flat_' + m.name)
                flat.use_nodes = True
                nt = flat.node_tree
                nt.nodes.clear()
                em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1)
                out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs['Surface'])
                cache[m.name] = flat
            swapped.append((o, i, m))
            o.data.materials[i] = cache[m.name]
    cam = bpy.data.cameras.new('Capture'); cam.type = 'ORTHO'; cam.ortho_scale = max(width, height)
    cam_ob = link(bpy.data.objects.new('Capture', cam))
    cam_ob.location = (centre[0], centre[1] - 1.0, centre[2]); cam_ob.rotation_euler = (math.pi / 2, 0, 0)
    old_cam, old_world = scene.camera, scene.world
    scene.camera = cam_ob
    world = bpy.data.worlds.new('Black'); world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24; scene.cycles.use_denoising = False; scene.cycles.use_adaptive_sampling = False
    scene.cycles.filter_width = 1.2
    scene.render.resolution_x = px; scene.render.resolution_y = max(4, round(px * height / width))
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'Standard'; scene.view_settings.look = 'None'
    scene.render.image_settings.file_format = 'PNG'; scene.render.film_transparent = alpha
    scene.render.image_settings.color_mode = 'RGBA' if alpha else 'RGB'
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    scene.render.film_transparent = False; scene.render.image_settings.color_mode = 'RGB'
    for o, i, m in swapped:
        o.data.materials[i] = m
    for o, h in keep.items():
        o.hide_render = h
    bpy.data.objects.remove(cam_ob)
    scene.camera, scene.world = old_cam, old_world
    img = bpy.data.images.load(path)
    img.pack()
    return img, peak


def quad(name, width, height, centre, parent, y=None):
    """A single textured quad facing -Y with 0-1 UVs."""
    bm = bmesh.new()
    cx, cy, cz = centre
    vs = [bm.verts.new((cx + sx * width / 2, cy if y is None else y, cz + sz * height / 2)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new('UVMap')
    for loop, co in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = co
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me), parent)


def image_material(name, base=None, emissive=None, strength=1.0, rough=0.5, metal=0.0, normal=None, normal_scale=(1, 1), orm=None, base_color=(0, 0, 0)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = bsdf_of(mat)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['Base Color'].default_value = (*base_color, 1)
    def tex(img, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = img; img.colorspace_settings.name = cs
        return n
    if base:
        nt.links.new(tex(base, 'sRGB').outputs['Color'], b.inputs['Base Color'])
    if emissive:
        nt.links.new(tex(emissive, 'sRGB').outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = strength
    if orm:
        t = tex(orm, 'Non-Color')
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], b.inputs['Roughness']); nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    if normal:
        t = tex(normal, 'Non-Color')
        if normal_scale != (1, 1):
            uv = nt.nodes.new('ShaderNodeUVMap'); mp = nt.nodes.new('ShaderNodeMapping')
            mp.inputs['Scale'].default_value = (normal_scale[0], normal_scale[1], 1)
            nt.links.new(uv.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return mat


def array_image(name, arr, colorspace='sRGB'):
    """An (h, w, 3|4) float array in 0-1 display values -> a packed Blender image."""
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :arr.shape[2]] = arr
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = colorspace
    # Blender stores sRGB images' pixels linearised; convert display values so the saved file holds `arr`.
    if colorspace == 'sRGB':
        c = rgba[..., :3]
        rgba[..., :3] = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    img.pixels.foreach_set(rgba[::-1].ravel() if False else rgba.ravel())
    path = os.path.join(WEB, name + '.png')
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    img.pack()
    return img


def apply_to_mesh(ob, parent=None, name=None):
    """An export copy of `ob` with modifiers applied (curves and text become meshes)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    new = link(bpy.data.objects.new(name or ob.name, me), parent if parent is not None else ob.parent)
    new.matrix_world = ob.matrix_world.copy()
    return new


def smart_uv(ob, margin=0.02, angle=66):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_object(scene, ob, size, tag, metal=0.0, aux_size=None):
    """Bake ob's (procedural) material to base colour, ORM and normal images on its UVs; swap in an image material."""
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12; scene.cycles.use_denoising = False
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'; prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception:
        pass
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    out = {}
    for kind, cs in (('DIFFUSE', 'sRGB'), ('ROUGHNESS', 'Non-Color'), ('NORMAL', 'Non-Color')):
        ksize = size if kind == 'DIFFUSE' else (aux_size or size)
        img = bpy.data.images.new(f'{tag}_{kind.lower()}', ksize, ksize, alpha=False)
        img.colorspace_settings.name = cs
        for m in ob.data.materials:
            n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; n.name = 'BAKE_TARGET'
            m.node_tree.nodes.active = n
        if kind == 'DIFFUSE':
            scene.render.bake.use_pass_direct = False; scene.render.bake.use_pass_indirect = False; scene.render.bake.use_pass_color = True
        scene.render.bake.margin = 16
        bpy.ops.object.bake(type=kind)
        for m in ob.data.materials:
            m.node_tree.nodes.remove(m.node_tree.nodes['BAKE_TARGET'])
        out[kind] = img
    size = aux_size or size
    r = np.empty(size * size * 4, dtype=np.float32); out['ROUGHNESS'].pixels.foreach_get(r)
    r = r.reshape(size, size, 4)
    orm = np.ones((size, size, 3), dtype=np.float32); orm[..., 1] = r[..., 0]; orm[..., 2] = metal
    orm_img = array_image(f'{tag}_orm', orm, 'Non-Color')
    for k in ('DIFFUSE', 'NORMAL'):
        p = os.path.join(WEB, f'{tag}_{k.lower()}.png')
        out[k].filepath_raw = p; out[k].file_format = 'PNG'; out[k].save(); out[k].pack()
    mat = image_material(tag, base=out['DIFFUSE'], orm=orm_img, normal=out['NORMAL'])
    ob.data.materials.clear(); ob.data.materials.append(mat)
    return mat


def strip_procedural(mat):
    """Reduce a Principled material to constants the glTF exporter carries (drops noise-driven roughness/bump)."""
    nt = mat.node_tree
    b = bsdf_of(mat)
    for sock in ('Roughness', 'Normal', 'Base Color'):
        for l in list(b.inputs[sock].links):
            nt.links.remove(l)
    return mat


def triangles(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for ob in objs:
        if ob.type in ('MESH', 'FONT', 'CURVE'):
            me = ob.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles(); n += len(me.loop_triangles)
            ob.evaluated_get(dg).to_mesh_clear()
    return n


def export_glb(root, name, tangents=True):
    raw = os.path.join(WEB, name + '.glb')
    dest = os.path.join(MODELS, name + '.glb')
    bpy.ops.object.select_all(action='DESELECT')
    objs = [root] + list(root.children_recursive)
    for o in objs:
        o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=raw, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_animations=False, export_image_format='AUTO',
                              export_tangents=tangents)
    cmd = ['npx', '--yes', '@gltf-transform/cli@4', 'optimize', raw, dest, '--compress', 'meshopt', '--texture-compress', 'webp', '--texture-size', '2048',
           '--join', 'false', '--flatten', 'false', '--palette', 'false', '--simplify', 'false', '--instance', 'false']
    res = subprocess.run(cmd, capture_output=True, text=True)
    print('[hd] gltf-transform', res.returncode, (res.stdout + res.stderr).strip().splitlines()[-1:] )
    print('[hd] exported', dest, os.path.getsize(dest), 'bytes; raw', os.path.getsize(raw))
    return dest


def check_render(name, focus, radius, **cam):
    """Fresh scene: import the shipped .glb, light it like the still, render 1000 px."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, name + '.glb'))
    studio(scene, focus, radius, **cam)
    render(scene, os.path.join(WEB, name + '-check.png'), 1000, 128)
