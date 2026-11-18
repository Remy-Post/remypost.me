"""Grocery app: a kraft price tag with a brass eyelet and twine, standing in a brass card holder."""
import bpy, bmesh, math, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
FONT_WIDE = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')
FONT_REG = os.path.join(HERE, '..', 'fonts', 'Archivo-Regular-500.ttf')
W, H, T = 58 * MM, 98 * MM, 1.0 * MM      # tag width, height, thickness
HOLE = (0.0, H - 13 * MM)                 # eyelet centre, tag coordinates (origin = bottom centre)
LEAN = math.radians(11)
SLOT_Z = 9 * MM                           # height of the slot floor inside the holder


def quad(bm, x0, y0, x1, y1, z):
    bm.faces.new([bm.verts.new(p) for p in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))])


def kraft(name):
    mat = principled(name, (0.46, 0.30, 0.165), 0.82)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    fine = nt.nodes.new('ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value = 5200
    fine.inputs['Detail'].default_value = 6
    stretch = nt.nodes.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (1, 9, 1)     # paper fibres run one way
    fibre = nt.nodes.new('ShaderNodeTexNoise')
    fibre.inputs['Scale'].default_value = 900
    fibre.inputs['Detail'].default_value = 10
    mottle = nt.nodes.new('ShaderNodeTexNoise')
    mottle.inputs['Scale'].default_value = 55
    mottle.inputs['Detail'].default_value = 4
    nt.links.new(coord.outputs['Object'], fine.inputs['Vector'])
    nt.links.new(coord.outputs['Object'], stretch.inputs['Vector'])
    nt.links.new(stretch.outputs['Vector'], fibre.inputs['Vector'])
    nt.links.new(coord.outputs['Object'], mottle.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.3, 0.75
    ramp.color_ramp.elements[0].color = (0.34, 0.21, 0.105, 1)
    ramp.color_ramp.elements[1].color = (0.56, 0.385, 0.22, 1)
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.inputs['Fac'].default_value = 0.5
    nt.links.new(fibre.outputs['Fac'], mix.inputs['Color1'])
    nt.links.new(mottle.outputs['Fac'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    b1 = nt.nodes.new('ShaderNodeBump')
    b1.inputs['Strength'].default_value = 0.22
    b1.inputs['Distance'].default_value = 0.0002
    b2 = nt.nodes.new('ShaderNodeBump')
    b2.inputs['Strength'].default_value = 0.35
    b2.inputs['Distance'].default_value = 0.0002
    nt.links.new(fine.outputs['Fac'], b1.inputs['Height'])
    nt.links.new(fibre.outputs['Fac'], b2.inputs['Height'])
    nt.links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    nt.links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value, rr.inputs['To Max'].default_value = 0.72, 0.92
    nt.links.new(fibre.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], bsdf.inputs['Roughness'])
    return mat


def twine_mat():
    mat = principled('Twine', (0.66, 0.55, 0.38), 0.9)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (1, 14, 1)      # along the curve (U runs along it)
    mapping.inputs['Rotation'].default_value = (0, 0, math.radians(38))
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.inputs['Scale'].default_value = 26
    wave.inputs['Distortion'].default_value = 0.6
    fuzz = nt.nodes.new('ShaderNodeTexNoise')
    fuzz.inputs['Scale'].default_value = 9000
    nt.links.new(coord.outputs['UV'], mapping.inputs['Vector'])
    nt.links.new(mapping.outputs['Vector'], wave.inputs['Vector'])
    nt.links.new(coord.outputs['Object'], fuzz.inputs['Vector'])
    b1 = nt.nodes.new('ShaderNodeBump')
    b1.inputs['Strength'].default_value = 0.9
    b1.inputs['Distance'].default_value = 0.0004
    b2 = nt.nodes.new('ShaderNodeBump')
    b2.inputs['Strength'].default_value = 0.3
    b2.inputs['Distance'].default_value = 0.0001
    nt.links.new(wave.outputs['Fac'], b1.inputs['Height'])
    nt.links.new(fuzz.outputs['Fac'], b2.inputs['Height'])
    nt.links.new(b1.outputs['Normal'], b2.inputs['Normal'])
    nt.links.new(b2.outputs['Normal'], bsdf.inputs['Normal'])
    dark = nt.nodes.new('ShaderNodeMixRGB')
    dark.inputs['Color1'].default_value = (0.42, 0.33, 0.21, 1)
    dark.inputs['Color2'].default_value = (0.74, 0.63, 0.45, 1)
    nt.links.new(wave.outputs['Fac'], dark.inputs['Fac'])
    nt.links.new(dark.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def tag_outline():
    """Clipped top corners, rounded bottom corners. Origin at the bottom centre."""
    clip, r = 15 * MM, 3.5 * MM
    pts = []
    for cx, cy, a0 in ((W / 2 - r, r, -90), (0, 0, 0)):
        if cx:
            pts += [(cx + r * math.cos(math.radians(a0 + i * 15)), cy + r * math.sin(math.radians(a0 + i * 15))) for i in range(7)]
    pts += [(W / 2, H - clip), (W / 2 - clip, H), (-W / 2 + clip, H), (-W / 2, H - clip)]
    pts += [(-W / 2 + r + r * math.cos(math.radians(180 + i * 15)), r + r * math.sin(math.radians(180 + i * 15))) for i in range(7)]
    return pts


def build():
    root = link(bpy.data.objects.new('pricetag', None))
    tag = link(bpy.data.objects.new('Tag', None), root)

    paper = kraft('Kraft')
    ink = principled('Ink', (0.018, 0.016, 0.015), 0.55)
    red = principled('RedInk', (0.50, 0.035, 0.03), 0.5)
    brass = principled('Brass', (0.83, 0.62, 0.30), 0.22, 1.0)
    roughness_breakup(brass, scale=700, amount=0.07, stretch=(1, 60, 1))
    brushed = principled('BrassBrushed', (0.86, 0.62, 0.27), 0.27, 1.0, Anisotropic=0.7)
    roughness_breakup(brushed, scale=1400, amount=0.08, stretch=(60, 1, 1))
    felt = principled('Felt', (0.012, 0.012, 0.013), 0.95)

    # Card: a filled 2D curve with the eyelet hole, extruded and edge-rounded.
    cu = bpy.data.curves.new('Card', 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    sp = cu.splines.new('POLY')
    pts = tag_outline()
    sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts):
        p.co = (x, y, 0, 1)
    sp.use_cyclic_u = True
    hole = cu.splines.new('POLY')
    n = 48
    hole.points.add(n - 1)
    for i, p in enumerate(hole.points):
        a = -math.tau * i / n
        p.co = (HOLE[0] + 2.7 * MM * math.cos(a), HOLE[1] + 2.7 * MM * math.sin(a), 0, 1)
    hole.use_cyclic_u = True
    cu.extrude = T / 2 - 0.16 * MM
    cu.bevel_depth = 0.16 * MM
    cu.bevel_resolution = 3
    card = link(bpy.data.objects.new('Card', cu), tag)
    card.data.materials.append(paper)

    # Eyelet: rolled brass flange on both faces.
    eyelet = lathe('Eyelet', [(r * MM, z * MM) for r, z in [
        (2.15, -0.95), (2.15, 0.95), (2.6, 1.12), (3.9, 1.02), (4.55, 0.74), (4.6, 0.56), (2.85, 0.52),
        (2.85, -0.52), (4.6, -0.56), (4.55, -0.74), (3.9, -1.02), (2.6, -1.12), (2.15, -0.95)]], 96, tag)
    eyelet.location = (HOLE[0], HOLE[1], 0)
    bevel(eyelet, 0.06 * MM, 2, 40)
    assign(eyelet, brass)

    # Print, on the front face.
    z = T / 2 + 0.03 * MM

    def label(body, size, x, y, font, mat, align='CENTER'):
        t = text_mesh('Print', body, size, font if os.path.exists(font) else None, parent=tag, align=align)
        t.location = (x, y, z)
        t.data.materials.append(mat)
        return t

    label('Honeycrisp apples', 3.3 * MM, 0, 66.5 * MM, FONT_REG, ink)
    label('per lb', 2.3 * MM, 0, 61.5 * MM, FONT_REG, ink)
    label('$1.99', 15.5 * MM, 0, 47 * MM, FONT_WIDE, ink)
    label('was $3.49', 4.0 * MM, 0, 34.5 * MM, FONT_REG, ink)
    label('SAVE 43%', 4.3 * MM, 0, 27.2 * MM, FONT_WIDE, red)
    bm = bmesh.new()
    quad(bm, -3.0 * MM, 34.1 * MM, 11.6 * MM, 34.55 * MM, z + 0.004 * MM)        # strike through the old price
    quad(bm, -21 * MM, 71.2 * MM, 21 * MM, 71.45 * MM, z)                        # rules
    quad(bm, -21 * MM, 23.2 * MM, 21 * MM, 23.45 * MM, z)
    random.seed(7)
    x = -17.5 * MM
    while x < 17.5 * MM:                                                       # barcode
        w = random.choice((0.28, 0.28, 0.56, 0.84)) * MM
        quad(bm, x, 9.6 * MM, min(x + w, 17.5 * MM), 20.2 * MM, z)
        x += w + random.choice((0.28, 0.28, 0.56)) * MM
    assign(mesh_object('Bars', bm, tag, smooth=False), ink)
    label('0 33383 40106 2', 1.75 * MM, 0, 7.2 * MM, FONT_REG, ink)

    # Stand the tag in the holder: front faces the camera (-Y), leaning back.
    tag.matrix_world = (Matrix.Translation((0, 0, SLOT_Z)) @ Matrix.Rotation(-LEAN, 4, 'X') @ Matrix.Rotation(math.pi / 2, 4, 'X'))

    # Holder: a brushed brass bar with a slot, on a felt pad.
    bw, bd, bh = 74 * MM, 24 * MM, 16 * MM
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(bw, bd, bh))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, bh / 2 + 0.6 * MM))
    bar = mesh_object('Holder', bm, root)
    # The slot flares 9 degrees each side from a 1.3 mm floor, so the card can rock about its bottom edge.
    cut_bm = bmesh.new()
    bmesh.ops.create_cube(cut_bm, size=1.0)
    bmesh.ops.scale(cut_bm, verts=cut_bm.verts, vec=(bw + 4 * MM, 1.3 * MM, 30 * MM))
    for v in cut_bm.verts:
        if v.co.z > 0:
            v.co.y *= (0.65 + 30 * math.tan(math.radians(9))) / 0.65
    cutter = mesh_object('SlotCutter', cut_bm, root, smooth=False)
    cutter.matrix_world = Matrix.Translation((0, 0, SLOT_Z)) @ Matrix.Rotation(-LEAN, 4, 'X') @ Matrix.Translation((0, 0, 14.4 * MM))
    cutter.hide_render = True
    cutter.display_type = 'WIRE'
    boolean = bar.modifiers.new('Slot', 'BOOLEAN')
    boolean.object, boolean.operation, boolean.solver = cutter, 'DIFFERENCE', 'EXACT'
    bevel(bar, 0.7 * MM, 4, 30)
    assign(bar, brushed)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(bw - 3 * MM, bd - 3 * MM, 0.9 * MM))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.45 * MM))
    assign(mesh_object('Pad', bm, root), felt)

    # Twine: a doubled strand through the eyelet, draped to the table on both sides, knotted at the front.
    hole_w = tag.matrix_world @ Vector((HOLE[0], HOLE[1], 0))
    front = tag.matrix_world.to_3x3() @ Vector((0, 0, 1))        # the tag's front normal
    R = 0.72 * MM

    def strand(name, side):
        s = side * 0.75 * MM
        P = lambda x, y, d: tag.matrix_world @ Vector((x, y, d))
        hy = HOLE[1]
        edge = P(-30.8 * MM, hy - 3.2 * MM + s * 0.6, 1.7 * MM)
        pts = [
            Vector((-27 * MM + s, -66 * MM, R)), Vector((-39 * MM + s, -60 * MM, R)), Vector((-50 * MM + s * 1.4, -47 * MM, R)),
            Vector((-53 * MM + s, -30 * MM, R)), Vector((-48 * MM + s, -15 * MM, R + 0.3 * MM)), Vector((-43.5 * MM + s, -7 * MM, 9 * MM)),
            Vector((-39 * MM + s * 0.6, edge.y - 3 * MM, 34 * MM)), Vector((-34 * MM + s * 0.5, edge.y - 1 * MM, 62 * MM)),
            edge + Vector((-1.6 * MM, 0, -5 * MM)), edge,
            P(-19 * MM, hy + 2.4 * MM + s * 0.5, 2.6 * MM), P(-8 * MM, hy + 2.6 * MM + s * 0.4, 3.0 * MM), P(-1.5 * MM, hy + 0.6 * MM, 2.6 * MM),
            hole_w + front * 0.6 * MM + Vector((s * 0.6, 0, -0.5 * MM)),
            hole_w - front * 2.5 * MM + Vector((s, 0, -0.9 * MM)), hole_w - front * 8 * MM + Vector((s, 0, -7 * MM)),
            Vector((4 * MM + s, 34 * MM, 52 * MM)), Vector((11 * MM + s, 44 * MM, 12 * MM)), Vector((19 * MM + s, 52 * MM, R + 0.3 * MM)),
            Vector((33 * MM + s, 57 * MM, R)), Vector((47 * MM + s * 2, 52 * MM, R)), Vector((56 * MM + s * 3, 40 * MM, R)),
        ]
        c = bpy.data.curves.new(name, 'CURVE')
        c.dimensions = '3D'
        spl = c.splines.new('NURBS')
        spl.points.add(len(pts) - 1)
        for p, v in zip(spl.points, pts):
            p.co = (*v, 1)
        spl.order_u = 4
        spl.use_endpoint_u = True
        c.resolution_u = 24
        c.bevel_depth = R
        c.bevel_resolution = 5
        c.use_fill_caps = True
        ob = link(bpy.data.objects.new(name, c), root)
        ob.data.materials.append(tw)
        return ob

    tw = twine_mat()
    strand('TwineA', -1)
    strand('TwineB', 1)
    # Overhand knot near the front ends: a short fat torus the strands run through.
    bm = bmesh.new()
    knot = bpy.data.meshes.new('Knot')
    bpy.ops.mesh.primitive_torus_add(major_radius=1.25 * MM, minor_radius=0.72 * MM, major_segments=40, minor_segments=16)
    k = bpy.context.object
    k.name = 'Knot'
    k.parent = root
    k.location = (-33 * MM, -63.6 * MM, 2.0 * MM)
    k.rotation_euler = (math.radians(80), 0, math.radians(-62))
    for p in k.data.polygons:
        p.use_smooth = True
    assign(k, tw)
    bm.free()
    return root


def tris():
    deps = bpy.context.evaluated_depsgraph_get()
    total = 0
    for ob in bpy.context.scene.objects:
        if ob.type in {'MESH', 'CURVE', 'FONT'} and not ob.hide_render and ob.name != 'Cove':
            me = ob.evaluated_get(deps).to_mesh()
            total += sum(len(p.vertices) - 2 for p in me.polygons)
    return total


def main():
    scene = reset()
    build()
    bpy.context.view_layer.update()
    print('[hd] pricetag triangles', tris())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'pricetag.blend'))
    if '--export' in ARGS:
        from ptb_web import export_web
        def under(o, nm):
            while o:
                if o.name == nm:
                    return True
                o = o.parent
            return False
        step = lambda t: max(0.0, min(1.0, t)) ** 2 * (3 - 2 * max(0.0, min(1.0, t)))
        def hang(co):                                  # string: still on the table, rigid with the card near it
            w = step((co.z - 0.004) / 0.054)
            return {'card': w, 'base': 1 - w}
        export_web('pricetag', bpy.data.objects['pricetag'],
                   [dict(name='paper', mats=['Kraft', 'Twine'], size=2048), dict(name='brass', mats=['BrassBrushed', 'Brass'], size=1024, metal=True)],
                   [dict(name='card', match=lambda o: under(o, 'Tag'), empty=False),
                    dict(name='string', match=lambda o: o.name.startswith(('Twine', 'Knot')), empty=False),
                    dict(name='holder', match=lambda o: True, empty=False)],
                   rig=dict(bones=[('card', (0, 0, SLOT_Z)), ('base', (0, 0, 0))],
                            weights={'card': lambda co: {'card': 1.0}, 'string': hang}))
        return
    if '--render' in ARGS:
        studio(scene, (0, -0.004, 0.052), 0.058, azimuth=-27, elevation=13, lens=90, distance=0.52)
        render(scene, os.path.join(OUT, 'pricetag.png'), arg('--size', 1400), arg('--samples', 256))


main()
