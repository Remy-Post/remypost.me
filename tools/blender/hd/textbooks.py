"""STEM Centre Marketplace: three used textbooks, a price sticker, and an Erlenmeyer flask on top."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
FONT_WIDE = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')
FONT_REG = os.path.join(HERE, '..', 'fonts', 'Archivo-Regular-500.ttf')


def box(name, size, centre, parent, bev=0.0, segs=3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=size)
    bmesh.ops.translate(bm, verts=bm.verts, vec=centre)
    ob = mesh_object(name, bm, parent)
    if bev:
        bevel(ob, bev, segs, 40)
    return ob


def quads(name, rects, z, parent):
    bm = bmesh.new()
    for x0, y0, x1, y1 in rects:
        bm.faces.new([bm.verts.new(p) for p in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))])
    return mesh_object(name, bm, parent, smooth=False)


def cloth(name, color, sheen=0.06):
    """Book cloth: fine weave bump, slight colour mottling, a touch of sheen."""
    mat = principled(name, color, 0.78, Sheen_Weight=sheen)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    weave = nt.nodes.new('ShaderNodeTexWave')
    weave.wave_type = 'BANDS'
    weave.bands_direction = 'X'
    weave.inputs['Scale'].default_value = 5200
    weave2 = nt.nodes.new('ShaderNodeTexWave')
    weave2.wave_type = 'BANDS'
    weave2.bands_direction = 'Y'
    weave2.inputs['Scale'].default_value = 5200
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    wear = nt.nodes.new('ShaderNodeTexNoise')
    wear.inputs['Scale'].default_value = 26
    wear.inputs['Detail'].default_value = 9
    wear.inputs['Roughness'].default_value = 0.7
    for n in (weave, weave2, wear):
        nt.links.new(coord.outputs['Object'], n.inputs['Vector'])
    nt.links.new(weave.outputs['Fac'], mul.inputs[0])
    nt.links.new(weave2.outputs['Fac'], mul.inputs[1])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.5
    bump.inputs['Distance'].default_value = 0.00012
    nt.links.new(mul.outputs['Value'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.32, 0.78
    ramp.color_ramp.elements[0].color = (*[c * 0.6 for c in color], 1)
    ramp.color_ramp.elements[1].color = (*[min(1, c * 1.1 + 0.004) for c in color], 1)
    nt.links.new(wear.outputs['Fac'], ramp.inputs['Fac'])
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    edge = nt.nodes.new('ShaderNodeMapRange')
    edge.inputs['From Min'].default_value, edge.inputs['From Max'].default_value = 0.54, 0.60
    nt.links.new(geo.outputs['Pointiness'], edge.inputs['Value'])
    rub = nt.nodes.new('ShaderNodeTexNoise')
    rub.inputs['Scale'].default_value = 120
    rub.inputs['Detail'].default_value = 8
    nt.links.new(coord.outputs['Object'], rub.inputs['Vector'])
    rubr = nt.nodes.new('ShaderNodeMapRange')
    rubr.inputs['From Min'].default_value, rubr.inputs['From Max'].default_value = 0.38, 0.62
    nt.links.new(rub.outputs['Fac'], rubr.inputs['Value'])
    fac = nt.nodes.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    nt.links.new(edge.outputs['Result'], fac.inputs[0])
    nt.links.new(rubr.outputs['Result'], fac.inputs[1])
    worn = nt.nodes.new('ShaderNodeMixRGB')
    worn.inputs['Color2'].default_value = (*[c * 0.35 + 0.42 for c in color], 1)
    nt.links.new(fac.outputs['Value'], worn.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], worn.inputs['Color1'])
    nt.links.new(worn.outputs['Color'], bsdf.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value, rr.inputs['To Max'].default_value = 0.62, 0.9
    nt.links.new(wear.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], bsdf.inputs['Roughness'])
    return mat


def pages_mat():
    """Page block: leaves read as fine horizontal lines on the three open edges, slightly yellowed and uneven."""
    mat = principled('Pages', (0.80, 0.75, 0.63), 0.85)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    lines = nt.nodes.new('ShaderNodeTexWave')
    lines.wave_type = 'BANDS'
    lines.bands_direction = 'Z'
    lines.inputs['Scale'].default_value = 2600          # about 0.4 mm per band
    lines.inputs['Distortion'].default_value = 1.2
    lines.inputs['Detail'].default_value = 2
    lines.inputs['Detail Scale'].default_value = 0.4
    tone = nt.nodes.new('ShaderNodeTexNoise')
    tone.inputs['Scale'].default_value = 14
    tone.inputs['Detail'].default_value = 6
    stretch = nt.nodes.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (1, 1, 30)
    nt.links.new(coord.outputs['Object'], lines.inputs['Vector'])
    nt.links.new(coord.outputs['Object'], stretch.inputs['Vector'])
    nt.links.new(stretch.outputs['Vector'], tone.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.85
    bump.inputs['Distance'].default_value = 0.0003
    nt.links.new(lines.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 0.55
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.62, 0.55, 0.42, 1)
    ramp.color_ramp.elements[1].color = (0.86, 0.82, 0.71, 1)
    nt.links.new(tone.outputs['Fac'], ramp.inputs['Fac'])
    shade = nt.nodes.new('ShaderNodeMapRange')
    shade.inputs['To Min'].default_value, shade.inputs['To Max'].default_value = 0.55, 1.0
    nt.links.new(lines.outputs['Fac'], shade.inputs['Value'])
    nt.links.new(ramp.outputs['Color'], mix.inputs['Color1'])
    nt.links.new(shade.outputs['Result'], mix.inputs['Color2'])
    nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def book(root, name, L, W, T, color, title, sub, z0, yaw, offset, foil, pages, top_title=None):
    """A hardcover lying flat. L runs along X, the spine faces -Y, T is the thickness."""
    b = link(bpy.data.objects.new(name, None), root)
    b['L'], b['W'] = L, W
    board, over, hinge = 2.8 * MM, 3.5 * MM, 7 * MM
    mat = cloth(name + 'Cloth', color)
    # Page block, set in from the boards on the three open sides, with a slightly hollow fore-edge.
    blk = box(name + 'Pages', (L - 2 * over, W - over - 5 * MM, T - 2 * board), (0, (5 * MM - over) / 2, T / 2), b, 0.5 * MM, 2)
    assign(blk, pages)
    for nm, zc in (('Back', board / 2), ('Front', T - board / 2)):
        assign(box(name + nm, (L, W - hinge, board), (0, hinge / 2, zc), b, 0.9 * MM, 4), mat)
    # Rounded spine: half an ellipse swept along the book's length, plus the two hinge strips.
    bm = bmesh.new()
    n, rows = 14, []
    for xi in (-L / 2, L / 2):
        ring = []
        for i in range(n + 1):
            a = math.pi * i / n
            ring.append(bm.verts.new((xi, -W / 2 + hinge - (hinge + 1.6 * MM) * math.sin(a) * 1.0, T / 2 - (T / 2) * math.cos(a))))
        rows.append(ring)
    for i in range(n):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    spine = mesh_object(name + 'Spine', bm, b)
    sol = spine.modifiers.new('Solid', 'SOLIDIFY')
    sol.thickness, sol.offset = 2.2 * MM, -1
    bevel(spine, 0.5 * MM, 3, 50)
    assign(spine, mat)
    # Headbands: the little striped cloth at each end of the spine.
    for sx in (-1, 1):
        hb = box(name + 'Headband', (1.6 * MM, 4 * MM, T - 2 * board - 1 * MM), (sx * (L / 2 - over - 0.2 * MM), -W / 2 + hinge - 1 * MM, T / 2), b, 0.5 * MM, 2)
        assign(hb, principled('Headband', (0.55, 0.08, 0.06), 0.7))

    # Spine lettering in foil, reading along the spine.
    sy = -W / 2 - 1.62 * MM
    def spine_text(body, size, x, font, align):
        t = text_mesh(name + 'SpineText', body, size, font if os.path.exists(font) else None, extrude=0.03 * MM, parent=b, align=align)
        t.rotation_euler = (math.pi / 2, 0, 0)
        t.location = (x, sy, T / 2)
        t.data.materials.append(foil)
    size = min(T * 0.46, 15 * MM, 0.50 * L / (len(title) * 0.80))
    spine_text(title, size, -L / 2 + 25 * MM, FONT_WIDE, 'LEFT')
    spine_text(sub, min(T * 0.2, 0.30 * L / (len(sub) * 0.52)), L / 2 - 25 * MM, FONT_REG, 'RIGHT')
    bands = bmesh.new()
    for x in (-L / 2 + 14 * MM, -L / 2 + 17 * MM, L / 2 - 14 * MM, L / 2 - 17 * MM):
        vs = [bands.verts.new(p) for p in ((x, sy, T * 0.13), (x + 1.1 * MM, sy, T * 0.13), (x + 1.1 * MM, sy, T * 0.87), (x, sy, T * 0.87))]
        bands.faces.new(vs)
    assign(mesh_object(name + 'Bands', bands, b, smooth=False), foil)

    if top_title:
        zt = T + 0.05 * MM
        for body, size, y, font in top_title:
            t = text_mesh(name + 'CoverText', body, size, font if os.path.exists(font) else None, extrude=0.03 * MM, parent=b, align='LEFT')
            t.location = (-L / 2 + 18 * MM, y, zt)
            t.data.materials.append(foil)
        assign(quads(name + 'CoverRule', [(-L / 2 + 18 * MM, W * 0.02, L / 2 - 18 * MM, W * 0.02 + 0.7 * MM)], zt, b), foil)

    b.location = (offset[0], offset[1], z0)
    b.rotation_euler = (0, 0, math.radians(yaw))
    return b


def flask(root, loc):
    f = link(bpy.data.objects.new('Flask', None), root)
    glass = principled('Glass', (1, 1, 1), 0.0, 0.0, Transmission_Weight=1.0, IOR=1.47)
    liquid = principled('Liquid', (0.03, 0.16, 0.85), 0.02, 0.0, Transmission_Weight=0.55, IOR=1.33)
    paint = principled('Enamel', (0.92, 0.92, 0.9), 0.5)
    wall = 1.6
    outer = [(0, 0), (30, 0), (33.5, 1.2), (34.5, 4), (33.6, 8), (13.2, 78), (12.2, 84), (12.2, 104), (13.0, 107), (15.2, 109.2), (15.6, 110.4), (14.6, 111)]
    inner = [(12.6, 110.2), (10.8, 107), (10.6, 84), (11.6, 78.6), (31.9, 8.4), (32.6, 4.6), (31.6, 2.6), (28, wall + 0.6), (0, wall + 1.4)]
    body = lathe('FlaskGlass', [(r * MM, z * MM) for r, z in outer + inner], 128, f)
    assign(body, glass)
    # Liquid: fills the inside to 26 mm with a meniscus, a hair inside the glass.
    def rad(z):  # inner radius at height z (mm) on the cone
        return 31.9 + (11.6 - 31.9) * (z - 8.4) / (78.6 - 8.4)
    top = 27.0
    liq = lathe('Liquid', [(r * MM, z * MM) for r, z in [(0, wall + 1.45), (27.9, wall + 0.66), (31.5, 2.7), (32.5, 4.6), (31.8, 8.4), (rad(top) - 0.08, top), (rad(top) - 1.2, top - 0.9), (0, top - 1.1)]], 128, f)
    assign(liq, liquid)
    # Graduations: white enamel ticks and a label printed on the cone.
    bm = bmesh.new()
    for z_mm, half in ((22, 9), (34, 5), (46, 9), (58, 5)):
        r0 = 34.5 + (13.2 - 34.5) * (z_mm - 4) / (78 - 4) * 1.0
        r0 = 33.6 + (13.2 - 33.6) * (z_mm - 8) / (78 - 8) + 0.06
        h = 0.45
        n = 10
        rows = []
        for i in range(n + 1):
            a = math.radians(-90 - half + 2 * half * i / n)
            rows.append((bm.verts.new((r0 * MM * math.cos(a), r0 * MM * math.sin(a), (z_mm - h) * MM)), bm.verts.new(((r0 - 0.27) * MM * math.cos(a), (r0 - 0.27) * MM * math.sin(a), (z_mm + h) * MM))))
        for p, q in zip(rows, rows[1:]):
            bm.faces.new((p[0], q[0], q[1], p[1]))
    assign(mesh_object('Ticks', bm, f, smooth=False), paint)
    slope = math.atan2(33.6 - 13.2, 70)
    for body_txt, z_mm, size in (('250 ml', 66, 3.4), ('100', 22, 2.4), ('200', 46, 2.4)):
        r0 = 33.6 + (13.2 - 33.6) * (z_mm - 8) / (78 - 8) + 0.1
        t = text_mesh('FlaskText', body_txt, size * MM, FONT_REG if os.path.exists(FONT_REG) else None, parent=f)
        ang = math.radians(-90 + (0 if z_mm == 66 else 26))
        t.matrix_local = Matrix.Rotation(ang + math.pi / 2, 4, 'Z') @ Matrix.Translation((0, -r0 * MM, z_mm * MM)) @ Matrix.Rotation(math.pi / 2 - slope, 4, 'X')
        t.data.materials.append(paint)
    f.location = loc
    return f


def build():
    root = link(bpy.data.objects.new('textbooks', None))
    foil = principled('Foil', (1.0, 0.80, 0.42), 0.44, 1.0)
    roughness_breakup(foil, scale=400, amount=0.06)
    pages = pages_mat()

    t1, t2, t3 = 46 * MM, 36 * MM, 29 * MM
    book(root, 'Calculus', 0.272, 0.212, t1, (0.016, 0.034, 0.105), 'CALCULUS', 'Early Transcendentals  ·  8th edition', 0.0, 4, (0, 0), foil, pages)
    book(root, 'Chemistry', 0.252, 0.196, t2, (0.17, 0.014, 0.022), 'ORGANIC CHEMISTRY', 'Structure and Function', t1, -7, (0.006, 0.004), foil, pages)
    top = book(root, 'DataStructures', 0.236, 0.178, t3, (0.018, 0.085, 0.045), 'DATA STRUCTURES', 'and Algorithms  ·  3rd edition', t1 + t2, 9, (-0.008, -0.002), foil, pages,
               top_title=[('Data', 21 * MM, 0.052, FONT_WIDE), ('Structures', 21 * MM, 0.028, FONT_WIDE), ('and Algorithms', 7.5 * MM, -0.012, FONT_REG), ('Third edition', 5 * MM, -0.062, FONT_REG)])

    # Price sticker on the top cover: a fluorescent paper dot with hand-priced type.
    zt = t3 + 0.06 * MM
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=19 * MM, segments=72)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, zt + 0.05 * MM))
    st = mesh_object('Sticker', bm, top, smooth=False)
    sol = st.modifiers.new('Solid', 'SOLIDIFY')
    sol.thickness = 0.12 * MM
    st.location = (0.066, -0.052, 0)
    st.rotation_euler = (0, 0, math.radians(-14))
    assign(st, principled('StickerPaper', (0.80, 0.21, 0.0), 0.92))
    ink = principled('Ink', (0.012, 0.011, 0.01), 0.9)
    for body, size, y, font in (('$25', 13 * MM, 0.0015, FONT_WIDE), ('USED', 3.6 * MM, -0.0105, FONT_REG), ('STEM Centre', 2.6 * MM, 0.0115, FONT_REG)):
        t = text_mesh('StickerText', body, size, font if os.path.exists(font) else None, parent=st)
        t.location = (0, y, zt + 0.19 * MM)
        t.data.materials.append(ink)

    flask(root, (0.058 - 0.008, 0.028 - 0.002, t1 + t2 + t3 + 0.02 * MM))
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
    print('[hd] textbooks triangles', tris())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'textbooks.blend'))
    if '--export' in ARGS:
        from ptb_web import export_web
        def under(o, nm):
            while o:
                if o.name == nm:
                    return True
                o = o.parent
            return False
        def corner(nm):                                # left end of the spine, at the bottom
            e = bpy.data.objects[nm]
            return e.matrix_world @ Vector((-e['L'] / 2, -e['W'] / 2, 0))
        def inner_faces(bm):                           # the page block's top and bottom sit under the boards: never seen
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9 and f.calc_area() > 0.002], context='FACES')
        book_node = lambda i, nm: dict(name=f'book_{i}', match=lambda o: under(o, nm), pivot=corner(nm), group=i - 1)
        export_web('textbooks', bpy.data.objects['textbooks'],
                   [dict(name='cloth', mats=['CalculusCloth', 'ChemistryCloth', 'DataStructuresCloth'], size=2048, tile_normal=8 * 0.00045),
                    dict(name='pages', mats=['Pages'], size=2048, prune=inner_faces)],
                   [dict(name='flask', match=lambda o: under(o, 'Flask'), pivot=bpy.data.objects['Flask'].matrix_world.translation.copy(), parent='book_3', group=2),
                    book_node(1, 'Calculus'), book_node(2, 'Chemistry'), book_node(3, 'DataStructures')])
        return
    if '--render' in ARGS:
        studio(scene, (0, 0, 0.105), 0.17, azimuth=-30, elevation=17, lens=85, distance=1.02)
        render(scene, os.path.join(OUT, 'textbooks.png'), arg('--size', 1400), arg('--samples', 256))


main()
