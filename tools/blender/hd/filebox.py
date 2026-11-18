"""CFTDC SharePoint: an open archive box of tabbed hanging folders, one document drawn half out."""
import bpy, bmesh, math, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
FONTS = os.path.join(HERE, '..', 'fonts')
BOLD = os.path.join(FONTS, 'Archivo-Wide-600.ttf')
REG = os.path.join(FONTS, 'Archivo-Regular-500.ttf')
BW, BD, BH, WALL = 352 * MM, 236 * MM, 262 * MM, 3.2 * MM   # box: width (X), depth (Y), height, board


def box(name, size, loc, parent=None, bev=0.0, seg=3, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=size)
    ob = mesh_object(name, bm, parent)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    if bev:
        bevel(ob, bev, seg, 40)
    return ob


def cyl(name, r, depth, loc, parent=None, rot=None, seg=40, bev=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=r, radius2=r, depth=depth, segments=seg)
    ob = mesh_object(name, bm, parent)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    if bev:
        bevel(ob, bev, 3, 40)
    return ob


def board_material(name, color, weave=0.5, scale=1400.0, rough=0.78):
    """Cloth-covered board or card stock: a fine weave bump and uneven roughness."""
    mat = principled(name, color, rough)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    hs = []
    for axis in ((1, 0.02, 0.02), (0.02, 0.02, 1), (0.02, 1, 0.02)):
        m = nt.nodes.new('ShaderNodeMapping')
        m.inputs['Scale'].default_value = axis
        w = nt.nodes.new('ShaderNodeTexWave')
        w.inputs['Scale'].default_value = scale
        w.inputs['Distortion'].default_value = 1.5
        w.inputs['Detail'].default_value = 2
        nt.links.new(coord.outputs['Object'], m.inputs['Vector'])
        nt.links.new(m.outputs['Vector'], w.inputs['Vector'])
        hs.append(w)
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
    add2 = nt.nodes.new('ShaderNodeMath'); add2.operation = 'ADD'
    nt.links.new(hs[0].outputs['Fac'], add.inputs[0]); nt.links.new(hs[1].outputs['Fac'], add.inputs[1])
    nt.links.new(add.outputs['Value'], add2.inputs[0]); nt.links.new(hs[2].outputs['Fac'], add2.inputs[1])
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 14
    noise.inputs['Detail'].default_value = 8
    nt.links.new(coord.outputs['Object'], noise.inputs['Vector'])
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value, rr.inputs['To Max'].default_value = rough - 0.1, min(1.0, rough + 0.1)
    nt.links.new(noise.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], bsdf.inputs['Roughness'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = weave
    bump.inputs['Distance'].default_value = 0.00025
    nt.links.new(add2.outputs['Value'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    # slight colour mottling
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (color[0] * 0.82, color[1] * 0.82, color[2] * 0.82, 1)
    mix.inputs[7].default_value = (min(1, color[0] * 1.1), min(1, color[1] * 1.1), min(1, color[2] * 1.1), 1)
    nt.links.new(noise.outputs['Fac'], mix.inputs[0])
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    return mat


def label(body, size, loc, parent, mat, font=REG, align='CENTER', rot=(math.pi / 2, 0, 0)):
    t = text_mesh('Print', body, size, font if os.path.exists(font) else None, parent=parent, align=align)
    t.location = loc
    t.data.resolution_u = 2 if size < 8 * MM else 8
    t.rotation_euler = rot
    t.data.materials.append(mat)
    return t


def leaf(name, parent, width, height, y_top, y_bottom, z_top, z_bottom, seed, mat, thick=0.42 * MM):
    """One leaf of a folder: a gently wavy sheet from the fold up to its rod."""
    rnd = random.Random(seed)
    ph, amp = rnd.uniform(0, 6), rnd.uniform(1.2, 3.0) * MM
    if seed >= 90:
        amp *= 0.1   # loose pages stay nearly flat so their print sits on them
    bm = bmesh.new()
    nx, nz = 18, 10
    grid = []
    for j in range(nz + 1):
        v = j / nz
        row = []
        for i in range(nx + 1):
            u = i / nx
            x = -width / 2 + width * u
            y = y_bottom + (y_top - y_bottom) * v + amp * math.sin(u * 5.2 + ph) * math.sin(v * math.pi) + 0.5 * amp * math.sin(u * 13 + ph * 2) * v * (1 - v) * 3
            row.append(bm.verts.new((x, y, z_bottom + (z_top - z_bottom) * v)))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    ob = mesh_object(name, bm, parent)
    s = ob.modifiers.new('Solid', 'SOLIDIFY')
    s.thickness, s.offset = thick, 0
    ob.data.materials.append(mat)
    return ob


PARTS = []   # interactive nodes for the web model: name, pivot (world matrix), parent empty


def build():
    root = link(bpy.data.objects.new('filebox', None))
    PARTS.clear()
    rnd = random.Random(7)

    cloth = board_material('BoxCloth', (0.030, 0.036, 0.050), 0.6, 1500)
    liner = board_material('BoxLiner', (0.50, 0.47, 0.41), 0.25, 900, 0.85)
    green = board_material('FolderGreen', (0.10, 0.20, 0.13), 0.18, 700, 0.7)
    kraft = board_material('FolderKraft', (0.52, 0.38, 0.22), 0.22, 700, 0.74)
    slate = board_material('FolderSlate', (0.13, 0.17, 0.25), 0.18, 700, 0.7)
    paper = board_material('Paper', (0.90, 0.89, 0.86), 0.08, 900, 0.8)
    ink = principled('Ink', (0.015, 0.016, 0.02), 0.55)
    faint = principled('InkFaint', (0.30, 0.32, 0.36), 0.6)
    blue = principled('InkBlue', (0.02, 0.07, 0.52), 0.5)
    steel = principled('Steel', (0.74, 0.75, 0.76), 0.26, 1.0, Anisotropic=0.6)
    roughness_breakup(steel, scale=600, amount=0.08, stretch=(50, 1, 1))
    brass = principled('Brass', (0.83, 0.62, 0.30), 0.24, 1.0)
    roughness_breakup(brass, scale=300, amount=0.08)
    clear = principled('TabPlastic', (0.92, 0.95, 1.0), 0.06, Transmission_Weight=0.92, IOR=1.46)

    # The box: bottom and four cloth-covered walls with a liner inside, bevelled as wrapped board.
    box('Bottom', (BW, BD, WALL), (0, 0, WALL / 2), root, 1.0 * MM, 3).data.materials.append(cloth)
    for name, size, loc in (
        ('Front', (BW, WALL, BH), (0, -BD / 2 + WALL / 2, BH / 2)), ('Rear', (BW, WALL, BH), (0, BD / 2 - WALL / 2, BH / 2)),
        ('Left', (WALL, BD, BH), (-BW / 2 + WALL / 2, 0, BH / 2)), ('Right', (WALL, BD, BH), (BW / 2 - WALL / 2, 0, BH / 2))):
        box(name, size, loc, root, 1.1 * MM, 4).data.materials.append(cloth)
    il = 0.5 * MM
    for name, size, loc in (
        ('LinerF', (BW - 2 * WALL, il, BH - 9 * MM), (0, -BD / 2 + WALL + il / 2, BH / 2 - 2 * MM)), ('LinerR', (BW - 2 * WALL, il, BH - 9 * MM), (0, BD / 2 - WALL - il / 2, BH / 2 - 2 * MM)),
        ('LinerL', (il, BD - 2 * WALL, BH - 9 * MM), (-BW / 2 + WALL + il / 2, 0, BH / 2 - 2 * MM)), ('LinerRt', (il, BD - 2 * WALL, BH - 9 * MM), (BW / 2 - WALL - il / 2, 0, BH / 2 - 2 * MM)),
        ('LinerB', (BW - 2 * WALL, BD - 2 * WALL, il), (0, 0, WALL + il / 2))):
        box(name, size, loc, root).data.materials.append(liner)

    # Steel hanging rails along the top of the left and right walls.
    rail_z = BH - 7 * MM
    for sx in (-1, 1):
        box('Rail', (2.0 * MM, BD - 2 * WALL - 2 * MM, 9 * MM), (sx * (BW / 2 - WALL - 1.6 * MM), 0, rail_z - 2.5 * MM), root, 0.5 * MM, 3).data.materials.append(steel)

    # Brass corner guards on the four top corners.
    for sx in (-1, 1):
        for sy in (-1, 1):
            g = link(bpy.data.objects.new('Guard', None), root)
            g.location = (sx * BW / 2, sy * BD / 2, BH)
            box('GuardA', (26 * MM, 1.0 * MM, 26 * MM), (-sx * 12.5 * MM, sy * 0.45 * MM, -12.5 * MM), g, 0.3 * MM, 2).data.materials.append(brass)
            box('GuardB', (1.0 * MM, 26 * MM, 26 * MM), (sx * 0.45 * MM, -sy * 12.5 * MM, -12.5 * MM), g, 0.3 * MM, 2).data.materials.append(brass)
            box('GuardTop', (27 * MM, 27 * MM, 1.0 * MM), (-sx * 12.6 * MM, -sy * 12.6 * MM, 0.45 * MM), g, 0.3 * MM, 2).data.materials.append(brass)
            for dx, dz in ((-19, -8), (-8, -19)):
                cyl('Rivet', 1.5 * MM, 1.2 * MM, (sx * dx * -1 * MM if False else -sx * abs(dx) * MM, sy * 1.1 * MM, dz * MM), g, (math.pi / 2, 0, 0), 20, 0.4 * MM).data.materials.append(brass)

    # Label holder on the front: brass frame, card insert, finger pull below.
    fy = -BD / 2
    lz = BH * 0.56
    box('HolderCard', (96 * MM, 0.5 * MM, 34 * MM), (0, fy - 0.6 * MM, lz), root).data.materials.append(paper)
    for name, size, loc in (('HT', (104 * MM, 1.6 * MM, 4 * MM), (0, fy - 1.0 * MM, lz + 19 * MM)), ('HB', (104 * MM, 1.6 * MM, 4 * MM), (0, fy - 1.0 * MM, lz - 19 * MM)),
                            ('HL', (4 * MM, 1.6 * MM, 42 * MM), (-50 * MM, fy - 1.0 * MM, lz)), ('HR', (4 * MM, 1.6 * MM, 42 * MM), (50 * MM, fy - 1.0 * MM, lz))):
        box(name, size, loc, root, 0.5 * MM, 3).data.materials.append(brass)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cyl('HRivet', 1.3 * MM, 1.2 * MM, (sx * 50 * MM, fy - 2.0 * MM, lz + sz * 19 * MM), root, (math.pi / 2, 0, 0), 20, 0.35 * MM).data.materials.append(brass)
    label('Unit records', 11.5 * MM, (0, fy - 0.95 * MM, lz + 4.5 * MM), root, ink, BOLD)
    label('Information management, 2026', 5.2 * MM, (0, fy - 0.95 * MM, lz - 8.0 * MM), root, ink, REG)
    # finger pull: a brass ring plate
    bm = bmesh.new()
    n = 48
    ring = [[bm.verts.new((r * math.cos(a), 0, r * math.sin(a))) for a in [math.tau * i / n for i in range(n)]] for r in (9 * MM, 14 * MM)]
    for i in range(n):
        bm.faces.new((ring[0][i], ring[0][(i + 1) % n], ring[1][(i + 1) % n], ring[1][i]))
    pull = mesh_object('Pull', bm, root)
    pull.location = (0, fy - 0.2 * MM, BH * 0.3)
    s = pull.modifiers.new('Solid', 'SOLIDIFY'); s.thickness = 1.4 * MM
    bevel(pull, 0.4 * MM, 3)
    pull.data.materials.append(brass)
    cyl('PullHole', 9 * MM, 0.4 * MM, (0, fy + 0.1 * MM, BH * 0.3), root, (math.pi / 2, 0, 0), 48).data.materials.append(principled('Shadow', (0.004, 0.004, 0.005), 0.9))

    # Hanging folders.
    fw = BW - 2 * WALL - 9 * MM
    names = ['Policies', 'SOPs', 'Training', 'Classrooms', 'Forms', 'Permissions', 'Archive']
    mats = [green, green, kraft, green, slate, green, kraft]
    count = len(names)
    y0, y1 = -BD / 2 + 30 * MM, BD / 2 - 30 * MM
    doc_at = 2
    for k in range(count):
        yc = y0 + (y1 - y0) * k / (count - 1) + rnd.uniform(-2.5, 2.5) * MM
        gap = rnd.uniform(5.5, 9.0) * MM
        lean = rnd.uniform(-3.0, 3.0) * MM
        zb = WALL + 9 * MM + rnd.uniform(0, 5) * MM
        fold = link(bpy.data.objects.new(f'Folder{k}', None), root)
        PARTS.append({'name': f'folder_{k + 1}', 'empty': fold, 'pivot': Matrix.Translation((0, yc + lean, zb))})
        for side, sgn in (('F', -1), ('B', 1)):
            yt = yc + sgn * gap / 2
            leaf(f'Leaf{k}{side}', fold, fw, 0, yt, yc + lean, rail_z, zb, k * 10 + (sgn > 0), mats[k])
            # the rod: a steel strip folded into the top edge, hooked over the rails
            box('Rod', (fw + 13 * MM, 0.9 * MM, 6.5 * MM), (0, yt, rail_z + 1.0 * MM), fold, 0.3 * MM, 2).data.materials.append(steel)
            box('RodWrap', (fw, 1.5 * MM, 8.5 * MM), (0, yt, rail_z - 0.5 * MM), fold, 0.5 * MM, 2).data.materials.append(mats[k])
        # plastic index tab on the front leaf, stepped across the width
        tx = (-0.36 + 0.72 * ((k * 3) % 7) / 6) * fw
        ty = yc - gap / 2 - 0.9 * MM
        tz = rail_z + 13.5 * MM
        box('Tab', (62 * MM, 1.3 * MM, 19 * MM), (tx, ty, tz), fold, 0.8 * MM, 4, rot=(math.radians(-14), 0, 0)).data.materials.append(clear)
        box('TabInsert', (56 * MM, 0.25 * MM, 13.5 * MM), (tx, ty + 0.05 * MM, tz + 0.6 * MM), fold, rot=(math.radians(-14), 0, 0)).data.materials.append(paper)
        t = label(names[k], 7.2 * MM, (tx, ty - 0.28 * MM, tz + 0.55 * MM), fold, ink, BOLD)
        t.rotation_euler = (math.pi / 2 - math.radians(14), 0, 0)
        if k in (0, 3, 5):
            for i in range(3):
                pg = leaf(f'Filed{k}{i}', fold, 214 * MM, 0, yc + (i - 1) * 1.1 * MM, yc + lean * 0.6 + (i - 1) * 0.5 * MM, rail_z + rnd.uniform(5, 24) * MM, zb + 5 * MM, 300 + k * 7 + i, paper, 0.11 * MM)
                pg.location.x = rnd.uniform(-26, 26) * MM
                pg.rotation_euler = (0, math.radians(rnd.uniform(-2.2, 2.2)), 0)
        if k == doc_at:
            dw, dh = 216 * MM, 279 * MM
            doc = link(bpy.data.objects.new('Document', None), root)
            # sits in the folder with its heading showing; slides straight up (world z) to come out
            doc.location = (-18 * MM, yc + 0.4 * MM, rail_z + 66 * MM)
            doc.rotation_euler = (0, math.radians(-2.0), 0)
            PARTS.append({'name': 'document', 'empty': doc, 'pivot': Matrix.Translation((-18 * MM, yc + 0.4 * MM, rail_z + 66 * MM - dh))})
            for i in range(3):
                leaf(f'Page{i}', doc, dw, 0, 0.9 * MM * i + 0.3 * MM * i, 0.9 * MM * i, 0, -dh, 90 + i, paper, 0.11 * MM).rotation_euler = (0, math.radians(0.8 * i), 0)
            py = -0.35 * MM
            label('Standard operating procedure', 7.2 * MM, (-dw / 2 + 20 * MM, py, -24 * MM), doc, ink, BOLD, 'LEFT')
            label('SharePoint library permissions', 5.0 * MM, (-dw / 2 + 20 * MM, py, -35 * MM), doc, blue, REG, 'LEFT')
            box('DocRule', (dw - 40 * MM, 0.02 * MM, 0.5 * MM), (0, py, -42 * MM), doc).data.materials.append(ink)
            lr = random.Random(3)
            body = ['1. Purpose. This procedure sets who may read, edit and share each',
                    'library on the unit site, and how access is asked for and removed.',
                    '2. Scope. All departments of the training centre and their staff.',
                    '3. Each library has one owner, named on its home page. The owner',
                    'approves requests through the access form within two working days.',
                    '4. Protected folders inherit nothing. Members are added by name,',
                    'never by group, and the list is reviewed at the start of each term.',
                    '5. When a member is posted out, the owner removes them the same week.',
                    '6. Questions go to the unit information management officer.']
            for i, line in enumerate(body):
                label(line, 3.25 * MM, (-dw / 2 + 20 * MM, py, (-50 - i * 6.0) * MM), doc, ink, REG, 'LEFT')
            # the back of the last page is printed too
            by = 0.9 * MM * 2 + 0.3 * MM * 2 + 0.3 * MM
            back = (math.pi / 2, 0, math.pi)
            label('Record of changes', 6.0 * MM, (dw / 2 - 20 * MM, by, -24 * MM), doc, ink, BOLD, 'LEFT', back)
            box('DocRuleB', (dw - 40 * MM, 0.02 * MM, 0.5 * MM), (0, by, -31 * MM), doc).data.materials.append(ink)
            for i, line in enumerate(['Version 3, approved by the unit information management officer.',
                                      'Version 2, added the protected folders rule and the term review.',
                                      'Version 1, first issue to all departments.',
                                      'Filed under SOPs. Review at the start of each term.']):
                label(line, 3.25 * MM, (dw / 2 - 20 * MM, by, (-39 - i * 6.0) * MM), doc, ink, REG, 'LEFT', back)
            # paper clip
            cu = bpy.data.curves.new('Clip', 'CURVE'); cu.dimensions = '3D'
            sp = cu.splines.new('POLY')
            pts = [(0, 0, -30), (0, 0, 0), (2.5, 0, 3), (5, 0, 0), (5, 0, -24), (3.2, 0, -26.5), (1.5, 0, -24), (1.5, 0, -6)]
            sp.points.add(len(pts) - 1)
            for p, c in zip(sp.points, pts):
                p.co = (c[0] * MM, c[1] * MM, c[2] * MM, 1)
            cu.bevel_depth = 0.45 * MM; cu.bevel_resolution = 3
            clip = link(bpy.data.objects.new('PaperClip', cu), doc)
            clip.location = (dw / 2 - 34 * MM, -0.6 * MM, 6 * MM)
            clip.data.materials.append(steel)
    return root


def tris():
    deps = bpy.context.evaluated_depsgraph_get()
    n = 0
    for ob in bpy.context.scene.objects:
        if ob.type in {'MESH', 'FONT', 'CURVE'} and ob.name != 'Cove':
            me = ob.evaluated_get(deps).to_mesh()
            n += sum(len(p.vertices) - 2 for p in me.polygons)
    return n


def main():
    scene = reset()
    root = build()
    bpy.context.view_layer.update()
    print('[hd] filebox triangles', tris())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'filebox.blend'))
    if '--render' in ARGS:
        studio(scene, (0, 0, 0.19), 0.14, azimuth=-33, elevation=19, lens=85, distance=1.42)
        render(scene, os.path.join(OUT, 'filebox.png'), arg('--size', 1400), arg('--samples', 256))
    if '--export' in ARGS:
        from pf_export import export_web

        def under(e):
            out = []
            for c in e.children:
                out += ([c] if c.type != 'EMPTY' else []) + under(c)
            return out
        parts = [{'name': p['name'], 'objects': under(p['empty']), 'pivot': p['pivot']} for p in PARTS]
        export_web('filebox', root, parts)


main()
