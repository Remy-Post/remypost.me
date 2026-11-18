"""Restaurant Review App: a polished steel cloche tipped open on a porcelain plate, a five-star card under its edge."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix


def solidify(ob, thickness, offset=-1.0):
    m = ob.modifiers.new('Solidify', 'SOLIDIFY')
    m.thickness, m.offset, m.use_even_offset = thickness, offset, True
    return ob


def star_points(r_out, r_in, n=5):
    return [((r_out if i % 2 == 0 else r_in) * math.sin(math.pi * i / n), (r_out if i % 2 == 0 else r_in) * math.cos(math.pi * i / n)) for i in range(2 * n)]


def star(name, r, depth, hollow=False, parent=None):
    """An extruded five-point star in the XZ plane facing -Y; hollow leaves only an outline."""
    bm = bmesh.new()
    outer = [bm.verts.new((x, 0, z)) for x, z in star_points(r, r * 0.42)]
    if hollow:
        inner = [bm.verts.new((x, 0, z)) for x, z in star_points(r * 0.72, r * 0.3)]
        n = len(outer)
        for i in range(n):
            bm.faces.new((outer[i], outer[(i + 1) % n], inner[(i + 1) % n], inner[i]))
    else:
        bm.faces.new(outer)
    geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    bmesh.ops.translate(bm, verts=[v for v in geom['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, -depth, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_object(name, bm, parent, smooth=False)
    bevel(ob, depth * 0.3, 3, 20)
    return ob


def build():
    root = link(bpy.data.objects.new('cloche', None))

    steel = principled('Steel', (0.80, 0.80, 0.81), 0.07, 1.0)
    roughness_breakup(steel, scale=14, amount=0.035)
    brushed = principled('SteelBrushed', (0.72, 0.72, 0.73), 0.26, 1.0, Anisotropic=0.7)
    roughness_breakup(brushed, scale=500, amount=0.06, stretch=(1, 1, 40))
    porcelain = principled('Porcelain', (0.86, 0.85, 0.82), 0.16, 0.0, Coat_Weight=0.6, Coat_Roughness=0.05,
                           Subsurface_Weight=0.15, Subsurface_Scale=0.004)
    roughness_breakup(porcelain, scale=25, amount=0.05)
    card = principled('Card', (0.045, 0.047, 0.052), 0.68)
    roughness_breakup(card, scale=900, amount=0.08, bump=0.03)
    gold = principled('Gold', (0.95, 0.70, 0.30), 0.22, 1.0)
    roughness_breakup(gold, scale=120, amount=0.06)

    # Plate: rim, well and foot ring in one lathe (radius, height in metres).
    plate = lathe('Plate', [
        (0, 0.0045), (0.062, 0.0045), (0.066, 0.0), (0.074, 0.0), (0.078, 0.0045), (0.092, 0.0075), (0.118, 0.0165),
        (0.140, 0.0215), (0.1455, 0.0235), (0.1465, 0.0262), (0.1445, 0.0285), (0.139, 0.0272), (0.118, 0.0215),
        (0.094, 0.0128), (0.080, 0.0102), (0, 0.0098)], 192, root)
    bevel(plate, 0.0012, 4, 28)
    assign(plate, porcelain)

    line = lathe('RimLine', [(0.1405, 0.02795), (0.1425, 0.0286), (0.1432, 0.02862), (0.1412, 0.02797)], 192, root)
    assign(line, gold)

    # Dome: a full, slightly tall hemisphere with a rolled rim, tipped open on its back edge.
    dome_root = link(bpy.data.objects.new('DomePivot', None), root)
    R, H = 0.104, 0.098
    prof = [(0, H)]
    for i in range(1, 41):
        a = (math.pi / 2) * i / 40
        prof.append((R * math.sin(a) ** 0.92, H * math.cos(a) ** 0.86))
    prof += [(R + 0.0005, -0.004), (R + 0.0042, -0.0062), (R + 0.0068, -0.0045), (R + 0.0072, -0.002)]
    dome = lathe('Dome', prof, 192, dome_root)
    solidify(dome, 0.0014)
    bevel(dome, 0.0005, 3, 30)
    assign(dome, steel)
    dome.location = (0, -R, 0.0062)

    # A brushed band above the rim, and the knob on a stepped boss.
    band = lathe('Band', [(R + 0.0006, 0.004), (R + 0.0016, 0.0045), (R + 0.0016, 0.0105), (R - 0.0002, 0.011)], 192, dome_root)
    assign(band, brushed)
    band.location = dome.location
    knob = lathe('Knob', [
        (0, 0.040), (0.0075, 0.0396), (0.0125, 0.0372), (0.0152, 0.0325), (0.0150, 0.0275), (0.0118, 0.0232), (0.0074, 0.0205),
        (0.0058, 0.0165), (0.0062, 0.0105), (0.0105, 0.0062), (0.0165, 0.0038), (0.0185, 0.0012), (0.0185, -0.0015), (0, -0.0015)], 96, dome_root)
    bevel(knob, 0.0004, 3, 30)
    assign(knob, steel)
    knob.location = (0, -R, 0.0062 + H)

    # Pivot on the back of the rim (world +Y), lifting the front toward the camera.
    dome_root.location = (0, R, 0.0105)
    dome_root.rotation_euler = (math.radians(-21), 0, math.radians(-10))

    # The rating card: heavy black stock on a small folded foot, five stars, four of them gold.
    card_root = link(bpy.data.objects.new('CardPivot', None), root)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(0.104, 0.0009, 0.038))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.019))
    face = mesh_object('Card', bm, card_root, smooth=False)
    bevel(face, 0.0003, 2, 40)
    assign(face, card)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(0.104, 0.020, 0.0009))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0.010, 0.00045))
    foot = mesh_object('CardFoot', bm, card_root, smooth=False)
    bevel(foot, 0.0003, 2, 40)
    assign(foot, card)
    for i in range(5):
        s = star(f'Star{i}', 0.0080, 0.0011, hollow=(i == 4), parent=card_root)
        s.location = ((i - 2) * 0.0188, -0.00045, 0.0195)
        assign(s, gold)
    card_root.location = (0.006, -0.064, 0.0102)
    card_root.rotation_euler = (math.radians(-14), 0, math.radians(7))
    return root


def reflectors():
    """Softbox panels seen only in reflections: they give the polished dome its shape."""
    for name, loc, size, strength, tint in (
        ('PanelLeft', (-0.62, -0.42, 0.34), (0.50, 0.95), 2.6, (1.0, 0.97, 0.93)),
        ('PanelRight', (0.70, -0.20, 0.30), (0.16, 1.10), 3.4, (0.88, 0.93, 1.0)),
        ('PanelTop', (0.05, 0.10, 0.78), (0.90, 0.34), 1.8, (1, 1, 1)),
        ('PanelBack', (-0.15, 0.85, 0.40), (1.3, 0.10), 2.2, (0.9, 0.95, 1.0)),
    ):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bmesh.ops.scale(bm, verts=bm.verts, vec=(size[0], size[1], 1))
        ob = mesh_object(name, bm, smooth=False)
        ob.location = loc
        ob.rotation_euler = (Vector((0, -0.01, 0.06)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        assign(ob, emission('Mat' + name, tint, strength))
        ob.visible_camera = False
        ob.visible_shadow = False
        ob.visible_diffuse = False


def tri_count():
    deps = bpy.context.evaluated_depsgraph_get()
    total = 0
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH' and ob.name != 'Cove':
            me = ob.evaluated_get(deps).to_mesh()
            me.calc_loop_triangles()
            total += len(me.loop_triangles)
    return total


def export_web():
    """Bake what is procedural, keep plain metals as factors, write the raw .glb."""
    import webkit_ct as wk
    O = bpy.data.objects
    root = O['cloche']
    wk.realize(root)
    plate = wk.join([O['Plate'], O['RimLine']], 'Plate')
    wk.bake_set(plate, 'cloche_plate', 2048, coat=(0.6, 0.05))
    card = wk.join([O['Card'], O['CardFoot']] + [O[f'Star{i}'] for i in range(5)], 'Card')
    wk.bake_set(card, 'cloche_card', 1024)
    for name in ('Steel', 'SteelBrushed'):
        wk.flatten(bpy.data.materials[name])
    print('[web] cloche triangles', wk.tri_count(root))
    wk.export(root, 'cloche')


def check():
    import webkit_ct as wk
    scene = wk.check_scene('cloche')
    studio(scene, (0, -0.012, 0.062), 0.15, azimuth=-26, elevation=13, lens=85, distance=0.98)
    reflectors()
    render(scene, os.path.join(OUT, 'web', 'cloche-check.png'), 1000, 128)


def main():
    if '--check' in ARGS:
        return check()

    scene = reset()
    build()
    bpy.context.view_layer.update()
    print('[hd] cloche triangles', tri_count())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'cloche.blend'))
    if '--export' in ARGS:
        return export_web()
    if '--render' in ARGS:
        studio(scene, (0, -0.012, 0.062), 0.15, azimuth=-26, elevation=13, lens=85, distance=0.98)
        reflectors()
        render(scene, os.path.join(OUT, 'cloche.png'), arg('--size', 1400), arg('--samples', 256))


main()
