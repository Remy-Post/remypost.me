"""Course Hub: a tear-off desk day planner on a steel easel, today's plan printed on the top sheet."""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector, Matrix

MM = 0.001
FONTS = os.path.join(HERE, '..', 'fonts')
BOLD = os.path.join(FONTS, 'Archivo-Wide-600.ttf')
REG = os.path.join(FONTS, 'Archivo-Regular-500.ttf')
W, H, T = 100 * MM, 132 * MM, 17 * MM   # paper block: width, height, thickness
TILT = math.radians(17)


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


def cyl(name, r, depth, loc, parent=None, rot=None, seg=48, bev=0.0, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, radius1=r, radius2=r if r2 is None else r2, depth=depth, segments=seg)
    ob = mesh_object(name, bm, parent)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    if bev:
        bevel(ob, bev, 3, 40)
    return ob


def paper_material(name, color, lines=False):
    """Paper: soft fibre bump; with `lines`, the stacked-sheet striations of a block seen edge-on."""
    mat = principled(name, color, 0.82)
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 900
    noise.inputs['Detail'].default_value = 6
    nt.links.new(coord.outputs['Object'], noise.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.06
    bump.inputs['Distance'].default_value = 0.0002
    nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    last = bump
    if lines:
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
        # ~0.1 mm sheets: a saw along the block's thickness, jittered by noise so no two sheets match.
        n2 = nt.nodes.new('ShaderNodeTexNoise')
        n2.inputs['Scale'].default_value = 60
        nt.links.new(coord.outputs['Object'], n2.inputs['Vector'])
        add = nt.nodes.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'
        add.inputs[1].default_value = 1.0 / (0.11 * MM)
        nt.links.new(sep.outputs['Y'], add.inputs[0])
        nt.links.new(n2.outputs['Fac'], add.inputs[2])
        frac = nt.nodes.new('ShaderNodeMath'); frac.operation = 'FRACT'
        nt.links.new(add.outputs['Value'], frac.inputs[0])
        b2 = nt.nodes.new('ShaderNodeBump')
        b2.inputs['Strength'].default_value = 0.55
        b2.inputs['Distance'].default_value = 0.0003
        nt.links.new(frac.outputs['Value'], b2.inputs['Height'])
        nt.links.new(bump.outputs['Normal'], b2.inputs['Normal'])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs[6].default_value = (color[0] * 0.72, color[1] * 0.71, color[2] * 0.68, 1)
        mix.inputs[7].default_value = (*color, 1)
        nt.links.new(frac.outputs['Value'], mix.inputs[0])
        nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
        last = b2
    nt.links.new(last.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


HS = H - 10 * MM                       # a sheet runs from the foot of the block to 2 mm under the clamp
PRINT_PX = (1024, 1249)                # one sheet's printed face in the 2048 print texture
PRINT = {'top': [], 'next': []}        # print geometry per sheet (rendered to a texture for the web model)
_CUR = [None]


def sheet(name, parent, y, curl=0.0, seed=0, color_mat=None, cell=None):
    """One sheet of the block: a grid (24 x 48, so it can curl and tear), printed face mapped to its cell of the
    print texture, blank back face. Local origin is the block's lower front edge; z runs up the sheet."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    nx, nz = 24, 48
    vmax = PRINT_PX[1] / 2048

    def roll(x, z, yy):
        # roll the lower right corner off the stack around a diagonal, as a cylinder of radius R
        L, R = 21 * MM * curl, 26 * MM
        s_ = (x - W / 2) * 0.7071 - z * 0.7071 + L
        yy = yy - 0.02 * MM * math.sin(z * 60 + seed)
        if s_ > 0:
            a_ = s_ / R
            sh = s_ - R * math.sin(a_)
            x, z = x - 0.7071 * sh, z + 0.7071 * sh
            yy -= R * (1 - math.cos(a_))
        return (x, yy, z)

    for back in (False, True):
        grid = [[None] * (nx + 1) for _ in range(nz + 1)]
        for j in range(nz + 1):
            for i in range(nx + 1):
                x, z = -W / 2 + W * i / nx, HS * j / nz
                grid[j][i] = (bm.verts.new(roll(x, z, y + (0.11 * MM if back else 0.0))), (i / nx, j / nz))
        for j in range(nz):
            for i in range(nx):
                q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
                if back:
                    q.reverse()
                f = bm.faces.new([v for v, _ in q])
                for loop, (_, (u, v)) in zip(f.loops, q):
                    if back or cell is None:
                        loop[uv].uv = (0.25, 0.85)
                    else:
                        loop[uv].uv = ((u + cell) * 0.5, v * vmax)
    ob = mesh_object(name, bm, parent)
    ob.data.materials.append(color_mat)
    return ob


def label(body, size, x, z, parent, mat, font=REG, align='LEFT', y=-0.22 * MM, spacing=1.0):
    t = text_mesh('Print', body, size, font if os.path.exists(font) else None, parent=parent, align=align)
    t.data.space_character = spacing
    t.data.resolution_u = 3 if size < 8 * MM else 10
    t.location = (x, y, z)
    t.rotation_euler = (math.pi / 2, 0, 0)
    t.data.materials.append(mat)
    if _CUR[0]:
        PRINT[_CUR[0]].append(t)
    return t


def print_sheet(which, tilt, day, numeral, entries, ticked, inks):
    """The printing on one sheet, as geometry lying just over the paper."""
    ink, blue, rule = inks
    _CUR[0] = which

    def mark(name, size, loc, mat, rot=None):
        o = box(name, size, loc, tilt, rot=rot)
        o.data.materials.append(mat)
        PRINT[which].append(o)

    label(day, 6.2 * MM, 0, 104 * MM, tilt, ink, REG, 'CENTER', spacing=1.06)
    label(numeral, 58 * MM, 0, 71 * MM, tilt, blue, BOLD, 'CENTER', spacing=0.96)
    label('November 2026', 4.6 * MM, 0, 45.5 * MM, tilt, ink, REG, 'CENTER', spacing=1.08)
    for i, (when, what) in enumerate(entries):
        z = (36.5 - i * 7.3) * MM
        label(when, 3.0 * MM, -43 * MM, z + 1.2 * MM, tilt, blue, BOLD)
        label(what, 3.3 * MM, -27 * MM, z + 1.2 * MM, tilt, ink, REG)
        width = 78 * MM if i < 3 else 50 * MM
        mark('Rule', (width, 0.02 * MM, 0.22 * MM), (-43 * MM + width / 2, -0.2 * MM, z - 1.5 * MM), rule)
        cx = 37.6 * MM
        if i < 3:
            for dx, dz, sx, sz in ((0, 1.6, 3.4, 0.25), (0, -1.6, 3.4, 0.25), (-1.6, 0, 0.25, 3.4), (1.6, 0, 0.25, 3.4)):
                mark('Tick', (sx * MM, 0.02 * MM, sz * MM), (cx + dx * MM, -0.2 * MM, z + 1.6 * MM + dz * MM), rule)
    for i in range(ticked):
        for (x0, z0, ln, ang) in ((36.8, 37.6, 1.7, 45), (38.2, 38.5, 3.4, -52)):
            mark('Check', (ln * MM, 0.02 * MM, 0.45 * MM), (x0 * MM, -0.24 * MM, (z0 - i * 7.3) * MM), blue, rot=(0, math.radians(ang), 0))
    _CUR[0] = None


def bake_print(scene, tilt):
    """Render each sheet's print square-on to a texture and put it on the sheet; the print geometry is then removed."""
    import numpy as np
    tex = os.path.join(OUT, 'web', 'tex')
    os.makedirs(tex, exist_ok=True)
    cam = link(bpy.data.objects.new('PrintCam', bpy.data.cameras.new('PrintCam')), tilt)
    cam.data.type, cam.data.ortho_scale = 'ORTHO', HS
    cam.location, cam.rotation_euler = (0, -0.5, HS / 2), (math.pi / 2, 0, 0)
    world = bpy.data.worlds.new('PaperWhite')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.92, 0.91, 0.875, 1)
    scene.world, scene.camera = world, cam
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.use_denoising, scene.cycles.filter_width = 64, False, 1.1
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = PRINT_PX[0], PRINT_PX[1], 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform, scene.view_settings.look = 'Standard', 'None'
    scene.view_settings.exposure, scene.view_settings.gamma = 0.0, 1.0
    scene.render.image_settings.file_format, scene.render.image_settings.color_mode = 'PNG', 'RGB'
    flat = {}

    def emit(mat):
        if mat.name not in flat:
            m = bpy.data.materials.new(mat.name + '_emit')
            m.use_nodes = True
            nt = m.node_tree
            nt.nodes.clear()
            e, o = nt.nodes.new('ShaderNodeEmission'), nt.nodes.new('ShaderNodeOutputMaterial')
            e.inputs['Color'].default_value = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value
            nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
            flat[mat.name] = m
        return flat[mat.name]

    everything = [o for o in scene.objects if o.type in {'MESH', 'FONT', 'CURVE'}]
    atlas = np.zeros((2048, 2048, 4), dtype=np.float32)
    for cell, which in enumerate(('top', 'next')):
        for o in PRINT[which]:
            o.data.materials[0] = emit(o.data.materials[0])
        keep = set(PRINT[which])
        for o in everything:
            o.hide_render = o not in keep
        scene.render.filepath = os.path.join(tex, f'planner_print_{which}.png')
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(scene.render.filepath)
        px = np.empty(PRINT_PX[0] * PRINT_PX[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(PRINT_PX[1], PRINT_PX[0], 4)
        if cell == 0:
            atlas[:, :] = px[2, 2]
        atlas[:PRINT_PX[1], cell * 1024:cell * 1024 + PRINT_PX[0]] = px
    atlas[:, :, 3] = 1.0
    for which in PRINT:
        for o in PRINT[which]:
            bpy.data.objects.remove(o)
    for o in scene.objects:
        o.hide_render = False
    bpy.data.objects.remove(cam)
    out = bpy.data.images.new('planner_sheets', 2048, 2048, alpha=False)
    out.pixels.foreach_set(atlas.ravel())
    out.filepath_raw, out.file_format = os.path.join(tex, 'planner_sheets.png'), 'PNG'
    out.save()
    mat = principled('SheetPrint', (0.92, 0.91, 0.875), 0.82)
    n = mat.node_tree.nodes.new('ShaderNodeTexImage')
    n.image = out
    mat.node_tree.links.new(n.outputs['Color'], next(x for x in mat.node_tree.nodes if x.type == 'BSDF_PRINCIPLED').inputs['Base Color'])
    for name in ('TopSheet', 'Sheet1'):
        bpy.data.objects[name].data.materials[0] = mat


def build():
    root = link(bpy.data.objects.new('planner', None))

    paper = paper_material('Paper', (0.92, 0.91, 0.875))
    edges = paper_material('PaperEdges', (0.84, 0.82, 0.77), lines=True)
    ink = principled('Ink', (0.012, 0.013, 0.016), 0.55)
    blue = principled('InkBlue', (0.02, 0.07, 0.52), 0.5)
    rule = principled('InkRule', (0.32, 0.36, 0.46), 0.6)
    steel = principled('PowderSteel', (0.018, 0.019, 0.022), 0.46)
    roughness_breakup(steel, scale=2600, amount=0.07, bump=0.05)
    alu = principled('Aluminium', (0.80, 0.80, 0.81), 0.28, 1.0, Anisotropic=0.7)
    roughness_breakup(alu, scale=700, amount=0.07, stretch=(60, 1, 1))
    chrome = principled('Chrome', (0.86, 0.86, 0.87), 0.08, 1.0)
    rubber = principled('Foot', (0.02, 0.02, 0.02), 0.8)
    tab_a = principled('TabBlue', (0.03, 0.10, 0.62), 0.38, Coat_Weight=0.4)
    tab_b = principled('TabAmber', (0.85, 0.38, 0.03), 0.38, Coat_Weight=0.4)
    barrel = principled('PenBarrel', (0.015, 0.016, 0.02), 0.22, Coat_Weight=0.8)

    # Base plate with a front lip, rubber feet.
    base_t = 3 * MM
    box('Base', (116 * MM, 128 * MM, base_t), (0, 12 * MM, base_t / 2), root, 1.1 * MM, 4).data.materials.append(steel)
    for sx in (-1, 1):
        for y in (-42, 66):
            cyl('Foot', 5 * MM, 1.2 * MM, (sx * 48 * MM, y * MM, -0.1 * MM), root, bev=0.3 * MM).data.materials.append(rubber)

    # Everything that leans back hangs off this pivot at the block's lower front edge.
    tilt = link(bpy.data.objects.new('Tilt', None), root)
    tilt.location = (0, -6 * MM, base_t + 5 * MM)
    tilt.rotation_euler = (-TILT, 0, 0)

    # Back plate and the ledge the block stands on.
    box('BackPlate', (112 * MM, 3 * MM, 150 * MM), (0, T + 1.6 * MM, 70 * MM), tilt, 1.0 * MM, 4).data.materials.append(steel)
    box('Ledge', (112 * MM, T + 6 * MM, 3 * MM), (0, T / 2 - 1.0 * MM, -1.6 * MM), tilt, 0.9 * MM, 4).data.materials.append(steel)
    box('LedgeLip', (112 * MM, 2.4 * MM, 9 * MM), (0, -2.6 * MM, 1.6 * MM), tilt, 0.8 * MM, 4).data.materials.append(steel)

    # The block: a bevelled stack with striated edges, and three loose sheets on top.
    block = box('Block', (W, T - 0.5 * MM, H), (0, T / 2 + 0.25 * MM, H / 2), tilt, 0.25 * MM, 2)
    block.data.materials.append(edges)
    sheet('Sheet2', tilt, 0.42 * MM, 0.35, 2, paper)
    sheet('Sheet1', tilt, 0.24 * MM, 0.7, 1, paper, cell=1)
    sheet('TopSheet', tilt, 0.06 * MM, 1.0, 0, paper, cell=0)
    inks = (ink, blue, rule)
    print_sheet('top', tilt, 'Monday', '16', [('6:00', 'Plan the day'), ('10:30', 'COMP 3415 lab due'), ('14:00', 'Micro quiz, 20%'), ('21:00', 'Evening check-in')], 1, inks)
    if '--export' in ARGS:
        print_sheet('next', tilt, 'Tuesday', '17', [('8:30', 'ECON 2010 lecture'), ('11:00', 'Group project stand-up'), ('15:30', 'Office hours, lab report'), ('20:00', 'Review flashcards')], 0, inks)

    # Torn stubs of earlier days under the clamp.
    for i in range(5):
        box('Stub', (W - (i % 3) * 0.6 * MM, 0.1 * MM, (4.0 + 1.3 * (i % 2)) * MM), (0.2 * MM * (i - 2), -0.1 * MM * (i + 1), H - 12 * MM - (2.0 + 0.65 * (i % 2)) * MM), tilt).data.materials.append(paper)

    # Aluminium clamp bar with two slotted screws.
    box('Clamp', (W + 8 * MM, T + 7 * MM, 13 * MM), (0, T / 2 - 0.6 * MM, H - 5.5 * MM), tilt, 1.4 * MM, 5).data.materials.append(alu)
    for sx in (-1, 1):
        s = cyl('Screw', 3.1 * MM, 1.6 * MM, (sx * 38 * MM, -4.6 * MM, H - 5.5 * MM), tilt, rot=(math.pi / 2, 0, 0), bev=0.45 * MM)
        s.data.materials.append(chrome)
        box('Slot', (4.6 * MM, 0.5 * MM, 0.7 * MM), (sx * 38 * MM, -5.42 * MM, H - 5.5 * MM), tilt, rot=(0, math.radians(28 * sx), 0)).data.materials.append(ink)

    # Index tabs standing out of the stack.
    for i, (zz, yy, mat) in enumerate(((84, 6.0, tab_a), (58, 11.0, tab_b))):
        box('Tab', (13 * MM, 0.3 * MM, 15 * MM), (W / 2 + 4.0 * MM, yy * MM, zz * MM), tilt, 0.15 * MM, 2).data.materials.append(mat)

    # Rear strut from the back plate down to the base.
    bpy.context.view_layer.update()
    a = tilt.matrix_world @ Vector((0, T + 3.2 * MM, 112 * MM))
    b = Vector((0, 70 * MM, base_t))
    mid, d = (a + b) / 2, (a - b)
    strut = box('Strut', (64 * MM, 3 * MM, d.length + 4 * MM), mid, root, 1.0 * MM, 4)
    strut.rotation_euler = (-(math.atan2(d.y, d.z)), 0, 0)
    strut.data.materials.append(steel)
    # rolled folds where the plates meet
    side_x = (0, math.pi / 2, 0)
    cyl('FoldBase', 2.9 * MM, 64 * MM, (0, b.y + 1.0 * MM, b.z + 0.3 * MM), root, side_x, 32, 0.6 * MM).data.materials.append(steel)
    cyl('FoldTop', 2.9 * MM, 64 * MM, (a.x, a.y + 0.6 * MM, a.z + 0.6 * MM), root, side_x, 32, 0.6 * MM).data.materials.append(steel)
    cyl('FoldLedge', 2.6 * MM, 112 * MM, (0, T + 1.6 * MM, -2.2 * MM), tilt, side_x, 32, 0.6 * MM).data.materials.append(steel)
    cyl('FoldFront', 2.2 * MM, 116 * MM, (0, -51 * MM, base_t / 2 + 0.4 * MM), root, side_x, 32, 0.5 * MM).data.materials.append(steel)

    # A pen resting across the base in front of the block.
    pen = link(bpy.data.objects.new('Pen', None), root)
    pen.location = (4 * MM, -38 * MM, base_t + 4.6 * MM)
    pen.rotation_euler = (0, 0, math.radians(7))
    side = (0, math.pi / 2, 0)
    cyl('Barrel', 4.6 * MM, 104 * MM, (0, 0, 0), pen, side, 64, 0.5 * MM).data.materials.append(barrel)
    cyl('Grip', 4.75 * MM, 22 * MM, (-44 * MM, 0, 0), pen, side, 64, 0.4 * MM).data.materials.append(alu)
    cyl('Cone', 4.5 * MM, 13 * MM, (-61.5 * MM, 0, 0), pen, (0, -math.pi / 2, 0), 64, r2=1.1 * MM).data.materials.append(chrome)
    cyl('Nib', 1.05 * MM, 3 * MM, (-69 * MM, 0, 0), pen, (0, -math.pi / 2, 0), 32, r2=0.35 * MM).data.materials.append(chrome)
    cyl('Cap', 4.75 * MM, 9 * MM, (56 * MM, 0, 0), pen, side, 64, 0.9 * MM).data.materials.append(chrome)
    box('Clip', (38 * MM, 2.6 * MM, 1.0 * MM), (38 * MM, 0, 5.3 * MM), pen, 0.4 * MM, 3).data.materials.append(chrome)
    box('ClipFoot', (4 * MM, 2.6 * MM, 2.2 * MM), (55 * MM, 0, 4.6 * MM), pen, 0.4 * MM, 3).data.materials.append(chrome)
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
    print('[hd] planner triangles', tris())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'planner.blend'))
    if '--render' in ARGS:
        studio(scene, (0, 0.012, 0.074), 0.085, azimuth=-25, elevation=12, lens=85, distance=0.56)
        render(scene, os.path.join(OUT, 'planner.png'), arg('--size', 1400), arg('--samples', 256))
    if '--export' in ARGS:
        from pf_export import export_web
        tilt = bpy.data.objects['Tilt']
        bake_print(scene, tilt)
        bpy.context.view_layer.update()
        parts = [{'name': 'sheet_top', 'objects': [bpy.data.objects['TopSheet']], 'pivot': tilt.matrix_world @ Matrix.Translation((0, 0.06 * MM, HS))},
                 {'name': 'sheet_next', 'objects': [bpy.data.objects['Sheet1']], 'pivot': tilt.matrix_world @ Matrix.Translation((0, 0.24 * MM, HS))}]
        export_web('planner', root, parts)


main()
