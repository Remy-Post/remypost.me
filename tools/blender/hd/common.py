"""Shared helpers for the high-definition project objects (Blender 5.2, headless).

Run an object script with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/hd/<object>.py -- [--render] [--samples N] [--size N]
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', 'hd')
os.makedirs(OUT, exist_ok=True)


def arg(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    return scene


def link(ob, parent=None):
    bpy.context.scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def mesh_object(name, bm, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me), parent)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


def lathe(name, profile, steps=128, parent=None):
    """Spin a (radius, height) profile around Z. Points at radius 0 are welded."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=steps, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm, parent)


def bevel(ob, width, segments=3, angle=35):
    m = ob.modifiers.new('Bevel', 'BEVEL')
    m.width, m.segments, m.limit_method, m.angle_limit = width, segments, 'ANGLE', math.radians(angle)
    m.harden_normals = True
    m.miter_outer = 'MITER_ARC'
    w = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL')
    w.keep_sharp = True
    return ob


def subsurf(ob, levels=2):
    m = ob.modifiers.new('Subsurf', 'SUBSURF')
    m.levels = m.render_levels = levels
    return ob


def principled(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **inputs):
    """A Principled material; extra keyword inputs use the socket name with underscores."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = mat.node_tree
    if nt is None:
        mat.use_nodes = True
        nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    for key, value in inputs.items():
        sock = bsdf.inputs[key.replace('_', ' ')]
        sock.default_value = (*value, 1) if isinstance(value, tuple) and len(value) == 3 and sock.type == 'RGBA' else value
    return mat


def emission(name, color, strength=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0, 0, 0, 1)
    bsdf.inputs['Roughness'].default_value = 0.4
    bsdf.inputs['Emission Color'].default_value = (*color, 1)
    bsdf.inputs['Emission Strength'].default_value = strength
    return mat


def roughness_breakup(mat, scale=40.0, amount=0.08, bump=0.0, stretch=(1, 1, 1)):
    """Vary roughness with noise (and optionally a fine bump), so surfaces do not read as CG-flat."""
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    base = bsdf.inputs['Roughness'].default_value
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = stretch
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 8
    ramp = nt.nodes.new('ShaderNodeMapRange')
    ramp.inputs['To Min'].default_value = max(0.0, base - amount)
    ramp.inputs['To Max'].default_value = min(1.0, base + amount)
    nt.links.new(coord.outputs['Object'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Value'])
    nt.links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])
    if bump:
        b = nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump
        nt.links.new(noise.outputs['Fac'], b.inputs['Height'])
        nt.links.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def text_mesh(name, body, size, font=None, extrude=0.0, parent=None, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body, cu.size, cu.extrude, cu.align_x, cu.align_y = body, size, extrude, align, 'CENTER'
    if font:
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    return link(bpy.data.objects.new(name, cu), parent)


def area_light(name, loc, target, size, power, color=(1, 1, 1), size_y=None):
    li = bpy.data.lights.new(name, 'AREA')
    li.energy, li.color, li.size = power, color, size
    if size_y:
        li.shape, li.size_y = 'RECTANGLE', size_y
    ob = link(bpy.data.objects.new(name, li))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def studio(scene, focus, radius, ground_z=0.0, dark=True, lens=85, azimuth=-32, elevation=16, distance=None):
    """A dark (or light) infinity-cove studio scaled to the subject: key, fill, rim, top strip, camera with DOF."""
    r = radius
    world = bpy.data.worlds.new('Studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.012, 0.013, 0.016, 1) if dark else (0.55, 0.56, 0.58, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    scene.world = world

    # Cove: floor sweeping up into a back wall.
    bm = bmesh.new()
    prof = [(-60 * r, 0)] + [(8 * r + 6 * r * math.sin(a), 6 * r - 6 * r * math.cos(a)) for a in [i * math.pi / 2 / 24 for i in range(25)]] + [(14 * r, 60 * r)]
    rows = [[bm.verts.new((x, y, z + ground_z)) for x in (-80 * r, 80 * r)] for y, z in prof]
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    cove = mesh_object('Cove', bm)
    floor = principled('StudioFloor', (0.028, 0.030, 0.034) if dark else (0.62, 0.63, 0.65), 0.34 if dark else 0.6)
    roughness_breakup(floor, scale=3.0 / r, amount=0.06)
    assign(cove, floor)

    f = Vector(focus)
    area_light('Key', f + Vector((-5.5 * r, -6.5 * r, 7.5 * r)), f, 6 * r, 22 * r * r * 60, (1.0, 0.97, 0.93))
    area_light('Fill', f + Vector((7 * r, -5 * r, 2.5 * r)), f, 8 * r, 22 * r * r * 9, (0.86, 0.92, 1.0))
    area_light('Rim', f + Vector((4.5 * r, 7 * r, 5 * r)), f, 3 * r, 22 * r * r * 55, (0.9, 0.95, 1.0), size_y=9 * r)
    area_light('Top', f + Vector((0, 1.5 * r, 9 * r)), f, 10 * r, 22 * r * r * 12, size_y=3 * r)

    cam = bpy.data.cameras.new('Camera')
    cam.lens = lens
    cam_ob = link(bpy.data.objects.new('Camera', cam))
    d = distance or r * 9.0
    az, el = math.radians(azimuth), math.radians(elevation)
    cam_ob.location = f + Vector((math.sin(az) * math.cos(el) * d, -math.cos(az) * math.cos(el) * d, math.sin(el) * d))
    cam_ob.rotation_euler = (f - cam_ob.location).to_track_quat('-Z', 'Y').to_euler()
    cam.dof.use_dof = True
    cam.dof.focus_distance = (f - cam_ob.location).length
    cam.dof.aperture_fstop = 11
    cam.clip_start, cam.clip_end = d * 0.05, d * 40
    scene.camera = cam_ob
    return cam_ob


def render(scene, path, size=1600, samples=256, aspect=1.0):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = 'GPU'
    except Exception as err:  # CPU fallback
        print('[hd] GPU unavailable:', err)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_x, scene.render.resolution_y = int(size * aspect), size
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('[hd] rendered', path)
