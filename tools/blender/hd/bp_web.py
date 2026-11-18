"""Shared by badge.py and patches.py (order R5): author print and embroidery as high-detail flat geometry,
photograph it straight-on into base-colour, normal and occlusion-roughness-metallic textures, then build light
named meshes that carry them."""
import bpy, bmesh, math, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
WEB = os.path.join(OUT, 'web')
TEX = os.path.join(WEB, 'tex')
os.makedirs(TEX, exist_ok=True)
FONT_WIDE = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')
FONT_TEXT = os.path.join(HERE, '..', 'fonts', 'Archivo-Regular-500.ttf')
MODELS = os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models')
_CAPTURE_MATS = []


def thread(name, color, angle=0.0, scale=2600.0, relief=1.0, radial=0, dark=0.7, rough=0.8, metal=0.0, scratch=0.0, rainbow=0.0):
    """Emission material for the capture. Mode 0: colour (stitched bands of `color`); 1: normal; 2: (1, roughness, metallic)."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    out, em, coord = N('ShaderNodeOutputMaterial'), N('ShaderNodeEmission'), N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ')
    if radial:
        grad = N('ShaderNodeTexGradient')
        grad.gradient_type = 'RADIAL'
        L(coord.outputs['Object'], grad.inputs[0])
        phase = N('ShaderNodeMath'); phase.operation = 'MULTIPLY'; phase.inputs[1].default_value = math.tau * radial
        L(grad.outputs[1], phase.inputs[0])
    else:
        mp = N('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, angle)
        L(coord.outputs['Object'], mp.inputs[0]); L(mp.outputs[0], sep.inputs[0])
        phase = N('ShaderNodeMath'); phase.operation = 'MULTIPLY'; phase.inputs[1].default_value = math.tau * scale
        L(sep.outputs[0], phase.inputs[0])
    sine = N('ShaderNodeMath'); sine.operation = 'SINE'
    h = N('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; h.inputs[1].default_value = 0.5; h.inputs[2].default_value = 0.5
    L(phase.outputs[0], sine.inputs[0]); L(sine.outputs[0], h.inputs[0])
    alb = N('ShaderNodeMix'); alb.data_type = 'RGBA'
    alb.inputs[6].default_value = (color[0] * dark, color[1] * dark, color[2] * dark, 1); alb.inputs[7].default_value = (*color, 1)
    L(h.outputs[0], alb.inputs[0])
    colour = alb.outputs[2]
    if rainbow:  # foil: hue sweeps across the strip
        sx = N('ShaderNodeSeparateXYZ'); L(coord.outputs['Object'], sx.inputs[0])
        a = N('ShaderNodeMath'); a.operation = 'MULTIPLY'; a.inputs[1].default_value = rainbow
        b = N('ShaderNodeMath'); b.operation = 'MULTIPLY_ADD'; b.inputs[1].default_value = rainbow * 0.6
        fr = N('ShaderNodeMath'); fr.operation = 'FRACT'
        L(sx.outputs[0], a.inputs[0]); L(sx.outputs[1], b.inputs[0]); L(a.outputs[0], b.inputs[2]); L(b.outputs[0], fr.inputs[0])
        hsv = N('ShaderNodeCombineColor'); hsv.mode = 'HSV'
        hsv.inputs[1].default_value = 0.42; hsv.inputs[2].default_value = 0.95
        L(fr.outputs[0], hsv.inputs[0])
        colour = hsv.outputs[0]
    bump = N('ShaderNodeBump'); bump.inputs['Strength'].default_value = relief; bump.inputs['Distance'].default_value = 0.00025
    L(h.outputs[0], bump.inputs['Height'])
    enc = N('ShaderNodeVectorMath'); enc.operation = 'MULTIPLY_ADD'
    enc.inputs[1].default_value = (0.5, 0.5, 0.5); enc.inputs[2].default_value = (0.5, 0.5, 0.5)
    L(bump.outputs['Normal'], enc.inputs[0])
    # Roughness, with fine hairline scratches where asked.
    rg = N('ShaderNodeValue'); rg.outputs[0].default_value = rough
    rsock = rg.outputs[0]
    for i, ang in enumerate((0.35, 1.9, 2.75) if scratch else ()):
        mp2 = N('ShaderNodeMapping'); mp2.inputs['Rotation'].default_value = (0, 0, ang); mp2.inputs['Scale'].default_value = (1, 0.012, 1)
        mp2.inputs['Location'].default_value = (i * 0.37, i * 0.11, i * 0.5)
        nz = N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4200; nz.inputs['Detail'].default_value = 1
        gt = N('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.69
        add = N('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = scratch
        L(coord.outputs['Object'], mp2.inputs[0]); L(mp2.outputs[0], nz.inputs['Vector']); L(nz.outputs[0], gt.inputs[0])
        L(gt.outputs[0], add.inputs[0]); L(rsock, add.inputs[2])
        rsock = add.outputs[0]
    orm = N('ShaderNodeCombineColor')
    orm.inputs[0].default_value = 1.0; orm.inputs[2].default_value = metal
    L(rsock, orm.inputs[1])
    m1 = N('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.name = 'Mode'; m1.inputs[0].default_value = 0.0
    m2 = N('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.name = 'Mode2'; m2.inputs[0].default_value = 0.0
    L(colour, m1.inputs[6]); L(enc.outputs[0], m1.inputs[7])
    L(m1.outputs[2], m2.inputs[6]); L(orm.outputs[0], m2.inputs[7])
    L(m2.outputs[2], em.inputs['Color']); L(em.outputs[0], out.inputs['Surface'])
    _CAPTURE_MATS.append(mat)
    return mat


def ink(name, color, rough=0.14, scratch=0.3, metal=0.0, rainbow=0.0):
    """Flat printed ink under laminate, for the capture."""
    return thread(name, color, relief=0.0, dark=1.0, rough=rough, scratch=scratch, metal=metal, rainbow=rainbow)


def pts_rect(cx, cy, w, h, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def pts_circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(math.tau * i / n), cy + r * math.sin(math.tau * i / n)) for i in range(n)]


def rrect(w, h, r, cx=0.0, cy=0.0, n=8):
    pts = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + qx * (w / 2 - r) + r * math.cos(a), cy + qy * (h / 2 - r) + r * math.sin(a)))
    return pts


def slab(name, pts_mm, height_mm, mat, z_mm=0.0, bev_mm=0.12):
    """A flat polygon (mm, in the XY plane) raised to a height, with softened edges."""
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x * MM, y * MM, z_mm * MM)) for x, y in pts_mm])
    bm.normal_update()
    if face.normal.z < 0:
        face.normal_flip()
    if height_mm > 0:
        ext = bmesh.ops.extrude_face_region(bm, geom=[face])
        bmesh.ops.translate(bm, verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, height_mm * MM))
        bmesh.ops.delete(bm, geom=[face], context='FACES')
    ob = mesh_object(name, bm, smooth=False)
    if bev_mm and height_mm > 0:
        bevel(ob, min(bev_mm, height_mm * 0.45) * MM, 3, 40)
    assign(ob, mat)
    return ob


def label(name, body, size_mm, x_mm, y_mm, mat, z_mm=0.0, height_mm=0.25, font=FONT_WIDE, bev_mm=0.07, align='CENTER', rot=0.0):
    t = text_mesh(name, body, size_mm * MM, font if os.path.exists(font) else None, extrude=height_mm * MM / 2, align=align)
    t.data.bevel_depth = bev_mm * MM
    t.data.bevel_resolution = 2
    t.data.space_line = 1.05
    t.location = (x_mm * MM, y_mm * MM, (z_mm + height_mm / 2) * MM)
    t.rotation_euler = (0, 0, rot)
    t.data.materials.append(mat)
    return t


def capture(objs, w_mm, h_mm, px_w, px_h, base, normal=True, normal_pct=100, orm=False):
    """Photograph `objs` straight down into <base>_base.png, _normal.png, _orm.png. Deletes them afterwards."""
    scene = bpy.context.scene
    keep = set(objs)
    hidden = [(o, o.hide_render) for o in scene.objects]
    for o in scene.objects:
        o.hide_render = o not in keep
    world = bpy.data.worlds.get('Black') or bpy.data.worlds.new('Black')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0, 0, 0, 1)
    old_world, old_cam = scene.world, scene.camera
    scene.world = world
    cam = bpy.data.cameras.new('Capture'); cam.type = 'ORTHO'; cam.ortho_scale = max(w_mm, h_mm) * MM
    cam_ob = link(bpy.data.objects.new('Capture', cam)); cam_ob.location = (0, 0, 0.5)
    cam.clip_start, cam.clip_end = 0.01, 2
    scene.camera = cam_ob
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.cycles.filter_width = 1.2
    scene.render.resolution_x, scene.render.resolution_y = px_w, px_h
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.look = 'None'
    paths = {}
    for kind, on, m1, m2, vt, pct in (('base', True, 0, 0, 'Standard', 100), ('normal', normal, 1, 0, 'Raw', normal_pct), ('orm', orm, 0, 1, 'Raw', 50)):
        if not on:
            continue
        for m in _CAPTURE_MATS:
            if m.users:
                m.node_tree.nodes['Mode'].inputs[0].default_value = m1
                m.node_tree.nodes['Mode2'].inputs[0].default_value = m2
        scene.view_settings.view_transform = vt
        scene.render.resolution_percentage = pct
        scene.render.filepath = f'{base}_{kind}.png'
        bpy.ops.render.render(write_still=True)
        paths[kind] = scene.render.filepath
    scene.render.resolution_percentage = 100
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.objects.remove(cam_ob, do_unlink=True)
    for o, h in hidden:
        try:
            o.hide_render = h
        except ReferenceError:
            pass
    scene.world, scene.camera = old_world, old_cam
    return paths


def web_material(name, tex, rough=0.8, sheen=0.0, coat=0.0, normal_strength=1.0):
    """Principled material from captured textures: tex = {'base': path, 'normal': path, 'orm': path}."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Roughness'].default_value = rough
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
        b.inputs['Sheen Roughness'].default_value = 0.5
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.1

    def image(path, space):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(path, check_existing=True)
        n.image.colorspace_settings.name = space
        return n
    nt.links.new(image(tex['base'], 'sRGB').outputs['Color'], b.inputs['Base Color'])
    if tex.get('normal'):
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(image(tex['normal'], 'Non-Color').outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if tex.get('orm'):
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(image(tex['orm'], 'Non-Color').outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    return mat


def brass():
    """The stand metal shared with the pennant stand."""
    return principled('brass', (0.83, 0.62, 0.30), 0.27, 1.0)


def planar_uv(me, w_mm, h_mm):
    """UVs from local X and Y over a w x h frame centred on the origin (call before standing the mesh up)."""
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u, v = co.x / (w_mm * MM) + 0.5, co.y / (h_mm * MM) + 0.5
            uv.data[li].uv = (min(max(u, 0.004), 0.996), min(max(v, 0.004), 0.996))


def stand_up(me, lift=(0, 0, 0)):
    """Local +Z (the printed face) turns to face -Y (the front); local +Y becomes up."""
    me.transform(Matrix.Translation(lift) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
    me.update()


def tube(name, pts, r, seg=14, closed=False):
    """Sweep a circle (radius r, or one radius per point) along points in metres, parallel-transported."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rs = r if isinstance(r, (list, tuple)) else [r] * n
    tans = [((pts[(i + 1) % n] if closed or i < n - 1 else pts[i]) - (pts[i - 1] if closed or i > 0 else pts[i])).normalized() for i in range(n)]
    ref = Vector((0, 1, 0)) if abs(tans[0].y) < 0.9 else Vector((1, 0, 0))
    u = (ref - tans[0] * ref.dot(tans[0])).normalized()
    bm = bmesh.new()
    rings = []
    for i in range(n):
        u = (u - tans[i] * u.dot(tans[i])).normalized()
        v = tans[i].cross(u)
        rings.append([bm.verts.new(pts[i] + (u * math.cos(math.tau * k / seg) + v * math.sin(math.tau * k / seg)) * rs[i]) for k in range(seg)])
    for i in range(n if closed else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if not closed:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm)


def ball(name, centre, r, steps=32):
    ob = lathe(name, [(r * math.sin(math.pi * i / 16), r * math.cos(math.pi * i / 16)) for i in range(17)], steps)
    ob.data.transform(Matrix.Translation(centre))
    return ob


def pivot(name, loc, mesh_ob, parent, matrix=None):
    """An empty carrying the node's clean transform, with the mesh as its child (quantisation rewrites mesh nodes)."""
    mesh_ob.name = name + '_mesh'
    e = link(bpy.data.objects.new(name, None), parent)
    if matrix is not None:
        e.matrix_local = matrix
    else:
        e.location = loc
    mesh_ob.parent = e
    mesh_ob.location = (0, 0, 0)
    return e


def group(name, loc, parts, root):
    """An empty at loc holding several meshes that were built in root space."""
    for i, ob in enumerate(parts):
        ob.name = f'{name}_{i}'
    e = link(bpy.data.objects.new(name, None), root)
    e.location = loc
    for ob in parts:
        ob.data.transform(Matrix.Translation(-Vector(loc)))
        ob.parent = e
    return e


def export(name, root):
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    family = [root] + list(root.children_recursive)
    for o in scene.objects:
        o.select_set(o in family)
    bpy.context.view_layer.objects.active = root
    tris = 0
    deps = bpy.context.evaluated_depsgraph_get()
    for o in family:
        if o.type in {'MESH', 'CURVE', 'FONT'}:
            m = o.evaluated_get(deps).to_mesh()
            m.calc_loop_triangles(); tris += len(m.loop_triangles)
            o.evaluated_get(deps).to_mesh_clear()
    raw = os.path.join(WEB, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=raw, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_tangents=True, export_cameras=False, export_lights=False)
    dest = os.path.abspath(os.path.join(MODELS, name + '.glb'))
    r = subprocess.run(['npx', '--yes', '@gltf-transform/cli@4', 'optimize', raw, dest, '--compress', 'meshopt', '--texture-compress', 'webp',
                        '--texture-size', '2048', '--join', 'false', '--flatten', 'false', '--palette', 'false', '--simplify', 'false',
                        '--instance', 'false', '--prune-attributes', 'false'], capture_output=True, text=True)
    print(r.stdout[-300:], r.stderr[-300:])
    print(f'[web] {name}: {tris} triangles, raw {os.path.getsize(raw) / 1e6:.2f} MB, final {os.path.getsize(dest) / 1e3:.1f} kB -> {dest}')


def check(name, focus, radius, **kw):
    """Fresh scene: import the shipped glb, light it like the still, render the check image."""
    scene = reset()
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(os.path.join(MODELS, name + '.glb')))
    studio(scene, focus, radius, **kw)
    render(scene, os.path.join(WEB, name + '-check.png'), 1000, 128)
