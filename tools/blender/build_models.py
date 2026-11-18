"""
Builds the 3D assets for remypost.me from nothing: the brand book (cover hero)
and the monogram block (Identity chapter, 404).

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python tools/blender/build_models.py -- [--preview] [--render]

Writes raw .glb files and textures to tools/blender/out/, a .blend you can open,
and (with --render) the fallback posters and the social card. Run
tools/blender/optimize.sh afterwards to produce the compressed files the site ships.

Axes: Blender is Z-up; glTF/three.js is Y-up. The book faces -Y here, which is +Z
(toward the camera) in three.js. Width is X in both.

Material names are the contract with the site: the code looks them up by name and
paints them from the CSS colour tokens, so the object follows the theme.
"""

import math
import os
import sys
from math import radians

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FONTS = os.path.join(HERE, 'fonts')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
os.makedirs(OUT, exist_ok=True)

# Clay & Ink, light and dark (mirrors apps/site/src/styles/base.css).
PALETTE = {
    'light': {'bone': '#f6f1e7', 'paper': '#ece4d4', 'ink': '#211d18', 'stone': '#6b6355', 'clay': '#a8441f', 'pine': '#2e4034'},
    'dark': {'bone': '#17140f', 'paper': '#211c15', 'ink': '#f3ece0', 'stone': '#b6ac9a', 'clay': '#e07a52', 'pine': '#6fa383'},
}
# Which token paints which material.
TOKENS = {
    'Cover': 'ink', 'Foil': 'bone', 'Pages': 'paper', 'Endpaper': 'pine', 'Ribbon': 'clay',
    'Ink': 'ink', 'Bone': 'bone', 'Clay': 'clay',
    'Mark': 'bone',
    'Paper': 'ink', 'Liner': 'pine', 'Sheet': 'bone', 'Lines': 'stone', 'Wax': 'clay',   # an ink envelope, like the book's cloth: it reads on the page in both themes
    'Card': 'ink', 'Print': 'bone', 'Back': 'pine', 'Metal': 'stone',
    'Handle': 'ink', 'Band': 'bone', 'Rubber': 'clay',
    'Face': 'bone', 'Edge': 'bone', 'Leaf': 'bone', 'LeafBack': 'paper', 'Strap': 'clay',
}

# Book dimensions (units are arbitrary; the book is 2.8 tall).
W, H, T = 2.1, 2.8, 0.30      # width, height, total thickness
C = 0.03                      # cover board thickness
G = 0.07                      # groove between spine and board
SQ = 0.06                     # how far the boards overhang the pages
XB0 = -W / 2 + C + G          # spine-side edge of the boards
FRONT = -T / 2                # y of the front cover's outer face
LIFT = 0.0018                 # foil sits this far off the cloth


# ── helpers ────────────────────────────────────────────────────────────────

def srgb(hex_):
    """'#rrggbb' -> linear RGBA, which is what Blender's nodes expect."""
    h = hex_.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'NONE'
    return scene


def save_image(name, rgba, colorspace):
    """rgba: float array (h, w, 4). Saved as PNG next to the models."""
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = colorspace   # before the pixels: changing it resets the buffer
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = os.path.join(OUT, name + '.png')
    img.file_format = 'PNG'
    img.save()
    return img


def cloth_normal(n=128, threads=16, strength=1.6):
    """A tileable bookcloth weave as a tangent-space normal map."""
    u = np.arange(n) / n
    U, V = np.meshgrid(u, u)
    rng = np.random.default_rng(7)
    warp = np.abs(np.sin(np.pi * threads * U))
    weft = np.abs(np.sin(np.pi * threads * V))
    over = (np.floor(threads * U) + np.floor(threads * V)) % 2
    height = np.where(over > 0, warp * (0.55 + 0.45 * weft), weft * (0.55 + 0.45 * warp))
    height += rng.normal(0, 0.035, height.shape)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    nz = np.ones_like(height)
    length = np.sqrt(dx * dx + dy * dy + nz * nz)
    rgba = np.stack([-dx / length * 0.5 + 0.5, -dy / length * 0.5 + 0.5, nz / length * 0.5 + 0.5, nz], axis=-1)
    return save_image('cloth-normal', rgba, 'Non-Color')


def page_edges(rows=64):
    """Near-white stripes, one row per 'sheet'. The material colour tints it."""
    rng = np.random.default_rng(11)
    lum = 0.93 + rng.uniform(-0.05, 0.05, rows)
    lum[rng.choice(rows, 9, replace=False)] -= 0.12   # the odd darker gap between signatures
    lum = np.clip(lum, 0, 1)
    rgba = np.ones((rows, 4, 4))
    rgba[..., :3] = lum[:, None, None]
    return save_image('page-edges', rgba, 'sRGB')


def material(name, scheme, rough, metal=0.0, base_img=None, normal_img=None, normal_strength=1.0, double=False, repeat=None, unlit=False, matte=False):
    if name in bpy.data.materials:   # one material per token name across every model
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    colour = srgb(PALETTE[scheme][TOKENS[name]])
    if unlit:
        # A flat colour that ignores the lights: exported as KHR_materials_unlit, so the face of
        # a board is exactly the element's CSS colour and only its edge and mark take the light.
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        flat_colour = nt.nodes.new('ShaderNodeRGB')   # a bare colour into the output is what the exporter reads as unlit
        flat_colour.outputs['Color'].default_value = colour
        nt.links.new(flat_colour.outputs['Color'], out.inputs['Surface'])
        mat.use_backface_culling = not double
        return mat
    if matte:
        bsdf.inputs['Specular IOR Level'].default_value = 0.0   # no highlight at all: chalk
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if base_img:
        # glTF has no "texture x colour" node graph of its own: the exporter reads a
        # Multiply mix of the texture and a colour as baseColorTexture * baseColorFactor.
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = base_img
        tex.interpolation = 'Linear'
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        # The Mix node has one socket set per data type; 6/7 and output 2 are the colour ones.
        mix.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs['Color'], mix.inputs[6])
        mix.inputs[7].default_value = colour
        nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = colour
    if normal_img:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = normal_img
        if repeat:
            # UVs stay inside 0-1 (mesh compression clamps anything outside); the tiling
            # lives on the texture instead and exports as KHR_texture_transform.
            coord = nt.nodes.new('ShaderNodeTexCoord')
            mapping = nt.nodes.new('ShaderNodeMapping')
            ru, rv = repeat if isinstance(repeat, tuple) else (repeat, repeat)
            mapping.inputs['Scale'].default_value = (ru, rv, 1.0)
            nt.links.new(coord.outputs['UV'], mapping.inputs['Vector'])
            nt.links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    mat.use_backface_culling = not double
    return mat


def add_box(bm, lo, hi, mat, bevel=0.0, segments=2):
    """Axis-aligned box from corner lo to corner hi, optionally with rounded edges."""
    lo, hi = Vector(lo), Vector(hi)
    faces_before = set(bm.faces)
    made = bmesh.ops.create_cube(bm, size=1.0)
    verts = made['verts']
    size = hi - lo
    bmesh.ops.scale(bm, vec=size, verts=verts)
    bmesh.ops.translate(bm, vec=(lo + hi) / 2, verts=verts)
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segments, profile=0.5, affect='EDGES')
    bm.normal_update()
    new = [f for f in bm.faces if f not in faces_before]
    for f in new:
        f.material_index = mat
    return new


def add_quad(bm, corners, mat):
    """One quad; corners counter-clockwise as seen from the side it faces."""
    f = bm.faces.new([bm.verts.new(c) for c in corners])
    f.material_index = mat
    return f


_fonts = {}
_em = {}
CAP_HEIGHT = 0.687   # Archivo's cap height in em (OS/2 sCapHeight)


def font(name):
    if name not in _fonts:
        _fonts[name] = bpy.data.fonts.load(os.path.join(FONTS, name + '.ttf'))
    return _fonts[name]


def text_mesh(body, face, size, tracking=1.0, extrude=0.0, bevel=0.0, resolution=3, fill=None):
    """Text as a mesh lying in XY, facing +Z, baseline at y=0, starting at x=0."""
    cu = bpy.data.curves.new('text', 'FONT')
    cu.body = body
    cu.font = font(face)
    cu.size = size * em_scale(face)
    cu.space_character = tracking
    cu.resolution_u = resolution
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 1
    cu.fill_mode = fill or ('BOTH' if extrude > 0 else 'FRONT')
    ob = bpy.data.objects.new('text', cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    if extrude == 0 and me.polygons and me.polygons[0].normal.z < 0:
        me.flip_normals()
    return me


def em_scale(face):
    """Blender's text size is not the font's em. Calibrate on the cap height of 'R'."""
    if face not in _em:
        _em[face] = 1.0
        probe = text_mesh('R', face, 1.0)
        b = bounds(probe)
        bpy.data.meshes.remove(probe)
        _em[face] = CAP_HEIGHT / (b[3] - b[1])
    return _em[face]


def bounds(me):
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    return min(xs), min(ys), max(xs), max(ys)


def append(bm, me, matrix, mat):
    """Drop a mesh into bm through a matrix, painting it with one material."""
    verts_before = set(bm.verts)
    faces_before = set(bm.faces)
    bm.from_mesh(me)
    bmesh.ops.transform(bm, matrix=matrix, verts=[v for v in bm.verts if v not in verts_before])
    for f in bm.faces:
        if f not in faces_before:
            f.material_index = mat
    bpy.data.meshes.remove(me)


def facing(direction, origin):
    """Matrix that stands XY text up on a face. Text x runs right, y runs up."""
    axes = {
        'front': ((1, 0, 0), (0, 0, 1), (0, -1, 0)),    # faces -Y, reads left to right
        'back': ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),     # faces +Y
        'spine': ((0, 0, -1), (0, -1, 0), (-1, 0, 0)),  # faces -X, reads head to tail
        'spine_up': ((0, -1, 0), (0, 0, 1), (-1, 0, 0)),  # faces -X, upright
    }[direction]
    m = Matrix.Identity(4)
    for col, axis in enumerate(axes):
        for row in range(3):
            m[row][col] = axis[row]
    m.translation = Vector(origin)
    return m


def finish(name, bm, mats, parent=None, origin=(0, 0, 0), uv=None, smooth_angle=38, pivot=False):
    """bmesh -> object. `origin` becomes the object's pivot (geometry is given in book space).

    With pivot=True the mesh hangs under an empty called `name`. Animate the empty: mesh
    compression rewrites the transform of nodes that carry a mesh, which would move the pivot."""
    origin = Vector(origin)
    bmesh.ops.translate(bm, vec=-origin, verts=bm.verts[:])
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=radians(smooth_angle))
    # Text converted from curves arrives with its own UV layer; drop it so ours is the only one.
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    if uv:
        layer = me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co + origin
                layer.data[li].uv = uv(co, p.normal, p.material_index)
    ob = bpy.data.objects.new(name + 'Mesh' if pivot else name, me)
    bpy.context.scene.collection.objects.link(ob)
    holder = empty(name) if pivot else ob
    if pivot:
        ob.parent = holder
    holder.location = origin
    if parent:
        holder.parent = parent
    return holder


def empty(name):
    ob = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(ob)
    return ob


UV_SPAN = 3.0   # the book fits inside +-1.5 on every axis


def unit(value):
    """Book-space coordinate -> 0-1."""
    return value / UV_SPAN + 0.5


def box_uv(co, normal, _mat):
    """Box projection at one scale for every face, kept inside 0-1 (see material's `repeat`)."""
    ax, ay, az = abs(normal.x), abs(normal.y), abs(normal.z)
    if ay >= ax and ay >= az:
        return (unit(co.x), unit(co.z))
    if ax >= az:
        return (unit(co.y), unit(co.z))
    return (unit(co.x), unit(co.y))


def monogram(bm, matrix, m, mat_letters, extrude=0.0, bevel=0.0, mat_square=None, lift=0.0):
    """The RP monogram inside a square of side m whose lower-left corner is the matrix origin.

    Follows the CSS mark: type at 0.36 m, lines 0.86 apart, P indented 0.32 em, the pair centred."""
    size = 0.36 * m
    pitch = size * 0.86
    r = text_mesh('R', 'Archivo-Wide-600', size, extrude=extrude, bevel=bevel)
    p = text_mesh('P', 'Archivo-Wide-600', size, extrude=extrude, bevel=bevel)
    rb, pb = bounds(r), bounds(p)
    indent = 0.32 * size
    left = min(rb[0], pb[0] + indent)
    right = max(rb[2], pb[2] + indent)
    bottom, top = pb[1], rb[3] + pitch
    ox = (m - (right - left)) / 2 - left
    oy = (m - (top - bottom)) / 2 - bottom
    if mat_square is not None:
        verts_before = set(bm.verts)
        add_quad(bm, [(0, 0, 0), (m, 0, 0), (m, m, 0), (0, m, 0)], mat_square)
        bmesh.ops.transform(bm, matrix=matrix, verts=[v for v in bm.verts if v not in verts_before])
    append(bm, r, matrix @ Matrix.Translation((ox, oy + pitch, lift)), mat_letters)
    append(bm, p, matrix @ Matrix.Translation((ox + indent, oy, lift)), mat_letters)


# ── the book ───────────────────────────────────────────────────────────────

def build_book(scheme='light'):
    cloth = cloth_normal()
    edges = page_edges()
    M = {
        'Cover': material('Cover', scheme, 0.86, normal_img=cloth, normal_strength=0.55, repeat=2.5 * UV_SPAN),
        'Foil': material('Foil', scheme, 0.42),
        'Pages': material('Pages', scheme, 0.92, base_img=edges),
        'Endpaper': material('Endpaper', scheme, 0.8),
        'Ribbon': material('Ribbon', scheme, 0.55, double=True),
    }
    root = empty('Book')
    cloth_uv = box_uv
    title_face = 'Archivo-Wide-560'

    # Body: spine, back board, the two cloth grooves, and the foil on spine and back.
    bm = bmesh.new()
    add_box(bm, (-W / 2, -T / 2, -H / 2), (-W / 2 + C, T / 2, H / 2), 0, bevel=0.009)
    add_box(bm, (XB0, T / 2 - C, -H / 2), (W / 2, T / 2, H / 2), 0, bevel=0.009)
    for side in (-1, 1):
        y0, y1 = sorted((side * (T / 2 - C * 0.3), side * (T / 2 - C * 0.75)))
        add_box(bm, (-W / 2 + C * 0.5, y0, -H / 2 + 0.004), (XB0 + 0.012, y1, H / 2 - 0.004), 0)
    spine_x = -W / 2 - LIFT
    name = text_mesh('Remy Post', title_face, 0.15, tracking=0.98)
    nb = bounds(name)
    append(bm, name, facing('spine', (spine_x, (nb[1] + nb[3]) / 2, H / 2 - 0.26)), 1)
    monogram(bm, facing('spine_up', (spine_x, 0.08, -H / 2 + 0.26)), 0.16, 0, mat_square=1, lift=LIFT)
    monogram(bm, facing('back', (0.13, T / 2 + LIFT, -H / 2 + 0.24)), 0.26, 0, mat_square=1, lift=LIFT)
    finish('Body', bm, [M['Cover'], M['Foil']], parent=root, uv=cloth_uv)

    # Pages: the text block. Its two big faces are the pine flyleaves.
    px0, px1 = -W / 2 + C + 0.012, W / 2 - SQ
    py0, py1 = -T / 2 + C + 0.004, T / 2 - C - 0.004
    pz0, pz1 = -H / 2 + SQ, H / 2 - SQ
    bm = bmesh.new()
    for f in add_box(bm, (px0, py0, pz0), (px1, py1, pz1), 0):
        if abs(f.normal.y) > 0.5:
            f.material_index = 1

    def pages_uv(co, normal, _mat):
        along = co.z if abs(normal.x) > 0.5 else co.x
        return (unit(along), (co.y - py0) / (py1 - py0))

    finish('Pages', bm, [M['Pages'], M['Endpaper']], parent=root, uv=pages_uv, smooth_angle=20)

    # CoverFront: the board that opens. Pivot on its inner, spine-side edge.
    bm = bmesh.new()
    add_box(bm, (XB0, FRONT, -H / 2), (W / 2, FRONT + C, H / 2), 0, bevel=0.009)
    inner = FRONT + C + 0.0012   # pine paste-down, facing the pages
    add_quad(bm, [(W / 2 - 0.035, inner, -H / 2 + 0.035), (XB0 + 0.012, inner, -H / 2 + 0.035),
                  (XB0 + 0.012, inner, H / 2 - 0.035), (W / 2 - 0.035, inner, H / 2 - 0.035)], 2)
    y = FRONT - LIFT
    margin = 0.2
    left, right = XB0 + margin, W / 2 - margin
    # monogram, top left
    mono = 0.44
    monogram(bm, facing('front', (left, y, H / 2 - margin - mono)), mono, 0, mat_square=1, lift=LIFT)
    # edition mark, top right
    ed = text_mesh('v1.0', 'Archivo-Regular-500', 0.085)
    eb = bounds(ed)
    append(bm, ed, facing('front', (right - eb[2], y, H / 2 - margin - eb[3])), 1)
    # title, bottom left, fitted to the measure
    size = 0.3
    probe = text_mesh('Guidelines', title_face, size, tracking=0.98)
    gb = bounds(probe)
    bpy.data.meshes.remove(probe)
    size *= min(1.0, (right - left) / (gb[2] - gb[0]))
    base = -H / 2 + margin + 0.02
    for i, line in enumerate(('Guidelines', 'Identity')):
        me = text_mesh(line, title_face, size, tracking=0.98)
        b = bounds(me)
        append(bm, me, facing('front', (left - b[0], y, base + i * size * 0.96)), 1)
    rule_z = base + size * 0.96 + size * 0.72 + 0.11
    rule_h = 0.013   # thick enough to stay a solid line when the book is drawn ~200 px wide
    add_quad(bm, [(left, y, rule_z), (right, y, rule_z), (right, y, rule_z + rule_h), (left, y, rule_z + rule_h)], 1)
    finish('CoverFront', bm, [M['Cover'], M['Foil'], M['Endpaper']], parent=root,
           origin=(XB0, FRONT + C, 0), uv=cloth_uv, pivot=True)

    # Ribbon: a clay bookmark hanging out of the foot, with a swallowtail end.
    bm = bmesh.new()
    rx, rw, rows, drop = -0.42, 0.1, 14, 0.5
    ry = 0.02
    grid = []
    for r in range(rows + 1):
        t = r / rows
        z = pz0 + 0.12 - t * (drop + 0.12)
        wave = 0.022 * math.sin(t * math.pi * 1.5) * t
        row = []
        for c in range(3):
            x = rx + (c - 1) * rw / 2
            zz = z + (0.06 if (r == rows and c == 1) else 0.0)
            row.append(bm.verts.new((x + 0.02 * t * t, ry + wave, zz)))
        grid.append(row)
    for r in range(rows):
        for c in range(2):
            bm.faces.new([grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]])
    finish('Ribbon', bm, [M['Ribbon']], parent=root, origin=(rx, ry, pz0), smooth_angle=60, pivot=True)
    return root


# ── the monogram block ─────────────────────────────────────────────────────

def build_monogram(scheme='light'):
    M = {
        'Ink': material('Ink', scheme, 0.5),
        'Bone': material('Bone', scheme, 0.55),
        'Clay': material('Clay', scheme, 0.7),
    }
    root = empty('Monogram')
    depth = 0.24
    bm = bmesh.new()
    add_box(bm, (-0.5, -depth / 2, -0.5), (0.5, depth / 2, 0.5), 0, bevel=0.035, segments=3)
    # the back is clay: the one accent, found only if you turn it over
    back = depth / 2 + 0.0015
    add_quad(bm, [(0.42, back, -0.42), (-0.42, back, -0.42), (-0.42, back, 0.42), (0.42, back, 0.42)], 1)
    ed = text_mesh('v1.0', 'Archivo-Wide-560', 0.11, tracking=0.98)
    eb = bounds(ed)
    append(bm, ed, facing('back', (0.34, back + 0.0015, -0.34 - eb[1])), 2)
    block = finish('Block', bm, [M['Ink'], M['Clay'], M['Bone']], parent=root, smooth_angle=50)

    bm = bmesh.new()
    monogram(bm, facing('front', (-0.5, -depth / 2 - 0.011, -0.5)), 1.0, 0, extrude=0.012, bevel=0.003)
    finish('Letters', bm, [M['Bone']], parent=root, smooth_angle=30)
    return root


# ── curve helpers (flat shapes with a thickness and a soft edge) ───────────

def curve_mesh(splines, extrude=0.0, bevel=0.0, bevel_res=1, fill=None):
    """Closed 2D outlines -> mesh in XY, thickness along Z. A spline inside another is a hole."""
    cu = bpy.data.curves.new('shape', 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = fill or ('BOTH' if extrude > 0 else 'FRONT')
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = bevel_res
    for pts in splines:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for point, (x, y) in zip(sp.points, pts):
            point.co = (x, y, 0, 1)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new('shape', cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    if extrude == 0 and me.polygons and me.polygons[0].normal.z < 0:
        me.flip_normals()
    return me


def rounded_rect(w, h, r, cx=0.0, cy=0.0, n=6):
    pts = []
    for sx, sy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for i in range(n + 1):
            a = radians(start + 90 * i / n)
            pts.append((cx + sx * (w / 2 - r) + r * math.cos(a), cy + sy * (h / 2 - r) + r * math.sin(a)))
    return pts


def circle(r, cx=0.0, cy=0.0, n=48, start=0.0, sweep=360.0, wobble=None):
    pts = []
    steps = n if sweep == 360.0 else n + 1
    for i in range(steps):
        a = radians(start + sweep * i / n)
        rr = r * (1 + (wobble(a) if wobble else 0))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


# ── plate marks (Work chapter) ─────────────────────────────────────────────

MARKS = {
    'course-hub': 'CH', 'cftdc-sharepoint': 'IM', 'grocery-brand': '¢', 'stem-marketplace': 'SC',
    'lawn-guy': 'LG', 'agentui': 'A/', 'watch-music': '◐', 'restaurant-review': '★', 'meals-app': 'M',
}
MARK_FACE = 'Archivo-Wide-560'
MARK_TRACKING = -0.04      # em, as .plate__mark
MARK_DEPTH = (0.026, 0.006)  # extrude, bevel: the mark stands 0.064 em proud of the board


def advance(ch):
    """Advance width of a glyph in em: where the next letter would start."""
    pair = text_mesh(ch + 'H', MARK_FACE, 1.0)
    alone = text_mesh('H', MARK_FACE, 1.0)
    adv = bounds(pair)[2] - bounds(alone)[2]
    bpy.data.meshes.remove(pair)
    bpy.data.meshes.remove(alone)
    return adv


def build_marks(scheme='light'):
    """One raised mark per project. 1 unit = 1 em of .plate__mark; origin = baseline, left edge
    of the text box; the back of the mark is at z = 0 (three.js axes), so it sits on a board."""
    mat = material('Mark', scheme, 1.0, matte=True)
    root = empty('Marks')
    ex, bv = MARK_DEPTH
    rise = Matrix.Translation((0, 0, ex + bv))
    for slug, text in MARKS.items():
        bm = bmesh.new()
        if text == '◐':
            r, cx, cy = 0.37, 0.43, 0.35
            # a disc with the right half cut out down to a rim: one outline and one hole, no overlap
            hole = circle(r - 0.055, cx + 0.012, cy, n=24, start=-90, sweep=180)
            append(bm, curve_mesh([circle(r, cx, cy), hole], ex, bv, fill='FRONT'), facing('front', (0, 0, 0)) @ rise, 0)
        elif text == '★':
            cx, cy = 0.46, 0.34
            star = [(cx + (0.42 if i % 2 == 0 else 0.17) * math.cos(radians(90 + 36 * i)),
                     cy + (0.42 if i % 2 == 0 else 0.17) * math.sin(radians(90 + 36 * i))) for i in range(10)]
            append(bm, curve_mesh([star], ex, bv, fill='FRONT'), facing('front', (0, 0, 0)) @ rise, 0)
        else:
            x = 0.0
            for ch in text:
                glyph = text_mesh(ch, MARK_FACE, 1.0, extrude=ex, bevel=bv, resolution=3, fill='FRONT')
                append(bm, glyph, facing('front', (x, 0, 0)) @ rise, 0)
                x += advance(ch) + MARK_TRACKING
        finish('Mark_' + slug, bm, [mat], parent=root, smooth_angle=30)
    return root


# ── the envelope (Writing chapter) ─────────────────────────────────────────

def build_envelope(scheme='light'):
    M = {
        'Paper': material('Paper', scheme, 0.92),
        'Liner': material('Liner', scheme, 0.85),
        'Sheet': material('Sheet', scheme, 0.9),
        'Ink': material('Ink', scheme, 0.6),
        'Lines': material('Lines', scheme, 0.9),
        'Wax': material('Wax', scheme, 0.85),   # matte wax: 0.36 and 0.5 both threw a pale flash under the key light as the flap sealed (measured in the site at 0.8: none)
    }
    root = empty('Envelope')
    EW, EH = 2.3, 1.55
    vee = 0.02                 # z of the bottom of the V on the pocket
    reach = EH * 0.63          # how far the flap hangs down from the top edge

    # Body: back panel, pine lining, and the pocket with its V-shaped mouth.
    bm = bmesh.new()
    add_box(bm, (-EW / 2, 0.0, -EH / 2), (EW / 2, 0.012, EH / 2), 0, bevel=0.003)
    add_quad(bm, [(-EW / 2 + 0.02, -0.001, -EH / 2 + 0.02), (EW / 2 - 0.02, -0.001, -EH / 2 + 0.02),
                  (EW / 2 - 0.02, -0.001, EH / 2 - 0.02), (-EW / 2 + 0.02, -0.001, EH / 2 - 0.02)], 1)
    pocket = curve_mesh([[(-EW / 2, -EH / 2), (EW / 2, -EH / 2), (EW / 2, EH / 2), (0, vee), (-EW / 2, EH / 2)]], 0.004, 0.002)
    append(bm, pocket, facing('front', (0, -0.030, 0)), 0)
    finish('Shell', bm, [M['Paper'], M['Liner']], parent=root, smooth_angle=30)

    # Letter: the sheet that rises out of the pocket.
    bm = bmesh.new()
    top = EH / 2 - 0.06
    add_box(bm, (-EW / 2 + 0.1, -0.016, -EH / 2 + 0.06), (EW / 2 - 0.1, -0.012, top), 0)
    y = -0.0175
    monogram(bm, facing('front', (-EW / 2 + 0.24, y, top - 0.14 - 0.22)), 0.22, 0, mat_square=1, lift=0.001)
    for i, width in enumerate((1.25, 1.4, 1.1, 0.7)):
        z = top - 0.2 - i * 0.085
        x0 = -EW / 2 + 0.6
        add_quad(bm, [(x0, y, z), (x0 + width, y, z), (x0 + width, y, z + 0.02), (x0, y, z + 0.02)], 2)
    finish('Letter', bm, [M['Sheet'], M['Ink'], M['Lines']], parent=root, origin=(0, -0.014, -EH / 2 + 0.06), pivot=True)

    # Flap: hinged on the top edge, lined in pine, sealed with clay wax.
    bm = bmesh.new()
    hinge = (0, -0.045, EH / 2)
    outline = [(EW / 2, 0), (-EW / 2, 0), (-0.17, -reach + 0.08), (-0.09, -reach + 0.022), (0, -reach),
               (0.09, -reach + 0.022), (0.17, -reach + 0.08)]
    append(bm, curve_mesh([outline], 0.004, 0.002), facing('front', hinge), 0)
    inset = [(x * 0.95, y * 0.95 - 0.02) for x, y in outline]
    append(bm, curve_mesh([inset]), facing('back', (hinge[0], hinge[1] + 0.0075, hinge[2])), 1)
    # the seal: an uneven puddle of wax with the monogram pressed into a ring
    seal_z = EH / 2 - reach + 0.17
    wob = lambda a: 0.06 * math.sin(3 * a + 1) + 0.04 * math.sin(5 * a + 2) + 0.025 * math.sin(8 * a)
    front = hinge[1] - 0.006
    append(bm, curve_mesh([circle(0.2, wobble=wob)], 0.012, 0.011, bevel_res=3), facing('front', (0, front - 0.023, seal_z)), 2)
    append(bm, curve_mesh([circle(0.142), circle(0.126)], 0.004, 0.003, bevel_res=2), facing('front', (0, front - 0.049, seal_z)), 2)
    monogram(bm, facing('front', (-0.1, front - 0.049, seal_z - 0.1)), 0.2, 2, extrude=0.005, bevel=0.002)
    # The flap is glued to the BACK panel: pivot there, so that when it opens it stands up
    # behind the letter rather than in front of it.
    finish('Flap', bm, [M['Paper'], M['Liner'], M['Wax']], parent=root, origin=(0, 0.006, EH / 2), pivot=True, smooth_angle=40)
    return root


# ── the badge (Resume chapter) ─────────────────────────────────────────────

def build_badge(scheme='light'):
    """A lanyard badge. Origin = the slot it hangs from; the lanyard itself is drawn in code
    and ties on at the top of the clasp (0, 0.34, 0) in three.js axes."""
    M = {
        'Card': material('Card', scheme, 0.55),
        'Print': material('Print', scheme, 0.6),
        'Back': material('Back', scheme, 0.8),
        'Metal': material('Metal', scheme, 0.34, metal=0.85),
    }
    root = empty('Badge')
    BW, BH, half = 1.0, 1.5, 0.0235
    cy = 0.12 - BH / 2          # the slot sits 0.12 below the card's top edge
    bm = bmesh.new()
    card = curve_mesh([rounded_rect(BW, BH, 0.08, cy=cy), rounded_rect(0.26, 0.07, 0.035)], 0.0175, 0.006, bevel_res=2)
    append(bm, card, facing('front', (0, 0, 0)), 0)
    y = -half - 0.0015
    left, right = -BW / 2 + 0.12, BW / 2 - 0.12
    monogram(bm, facing('front', (left, y, 0.12 - 0.3 - 0.3)), 0.3, 0, mat_square=1, lift=0.0012)
    name = text_mesh('Remy Post', 'Archivo-Wide-560', 1.0, tracking=0.98)
    nb = bounds(name)
    scale = (right - left) / (nb[2] - nb[0])
    bpy.data.meshes.remove(name)
    name = text_mesh('Remy Post', 'Archivo-Wide-560', scale, tracking=0.98)
    append(bm, name, facing('front', (left - bounds(name)[0], y, -1.02)), 1)
    add_quad(bm, [(left, y, -0.86), (right, y, -0.86), (right, y, -0.852), (left, y, -0.852)], 1)
    role = text_mesh('Developer, CS student', 'Archivo-Regular-500', 0.066, tracking=1.02)
    append(bm, role, facing('front', (left - bounds(role)[0], y, -1.15)), 1)
    # back: a pine panel with the monogram, for whoever flips it
    back = half + 0.0012
    append(bm, curve_mesh([rounded_rect(BW - 0.14, BH - 0.3, 0.05, cy=cy - 0.05)]), facing('back', (0, back, 0)), 2)
    monogram(bm, facing('back', (0.24, back + 0.0012, cy - 0.05 - 0.24)), 0.48, 1)
    finish('Card', bm, [M['Card'], M['Print'], M['Back']], parent=root, smooth_angle=35)

    bm = bmesh.new()
    bpy.ops.mesh.primitive_torus_add(major_radius=0.09, minor_radius=0.012, major_segments=28, minor_segments=8)
    ring = bpy.context.active_object
    ring_mesh = ring.data
    bpy.data.objects.remove(ring)
    turn = Matrix.Translation((0, 0, 0.07)) @ Matrix.Rotation(radians(90), 4, 'Y')
    append(bm, ring_mesh, turn, 0)
    add_box(bm, (-0.07, -0.022, 0.14), (0.07, 0.022, 0.34), 0, bevel=0.012, segments=2)
    finish('Clip', bm, [M['Metal']], parent=root, smooth_angle=40)
    return root


# ── the date stamp (History chapter) ───────────────────────────────────────

def build_stamp(scheme='light'):
    """A turned hand stamp, standing on its rubber face. Origin = centre of the face, axis = +y
    (three.js), so pressing it is a move along its own axis."""
    M = {
        'Handle': material('Handle', scheme, 0.34),
        'Band': material('Band', scheme, 0.45),
        'Rubber': material('Rubber', scheme, 0.85),
    }
    root = empty('Stamp')
    profile = [(0, 0), (0.42, 0), (0.42, 0.05), (0.46, 0.065), (0.46, 0.2), (0.43, 0.245), (0.17, 0.35),
               (0.125, 0.42), (0.125, 0.5), (0.15, 0.62), (0.21, 0.82), (0.245, 1.02), (0.235, 1.2),
               (0.2, 1.33), (0.255, 1.42), (0.27, 1.5), (0.225, 1.6), (0.12, 1.665), (0, 1.68)]
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=40, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        z = f.calc_center_median().z
        f.material_index = 2 if z < 0.056 else 1 if 0.42 < z < 0.5 else 0
    finish('StampBody', bm, [M['Handle'], M['Band'], M['Rubber']], parent=root, smooth_angle=32)
    return root


# ── sheets the site bends in code: sample board, paper leaf, strap ─────────

def normal_from_height(name, height, strength):
    """Tileable height field (h, w) -> tangent-space normal map image."""
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    nz = np.ones_like(height)
    length = np.sqrt(dx * dx + dy * dy + nz * nz)
    rgba = np.stack([-dx / length * 0.5 + 0.5, -dy / length * 0.5 + 0.5, nz / length * 0.5 + 0.5, nz], axis=-1)
    return save_image(name, rgba, 'Non-Color')


def paper_normal(n=256):
    """Uncoated paper: long soft fibres mostly along the grain, with a fine tooth on top."""
    rng = np.random.default_rng(23)
    fibres = rng.normal(0, 1, (n, n))
    for _ in range(13):                             # smear along the grain (wraps, so it tiles)
        fibres = (fibres + np.roll(fibres, 1, 1) * 0.5) / 1.5
    cross = sum(np.roll(fibres, k, 0) for k in (-1, 0, 1)) / 3
    tooth = rng.normal(0, 1, (n, n))
    tooth = (tooth + np.roll(tooth, 1, 0) + np.roll(tooth, 1, 1)) / 3
    height = cross / (np.abs(cross).max() + 1e-9) * 0.7 + tooth / (np.abs(tooth).max() + 1e-9) * 0.3
    return normal_from_height('paper-normal', height, 1.1)


def grosgrain_normal(n=64, ribs=4):
    """Ribbed ribbon weave: ribs run across the strap, so the height varies along its length."""
    rng = np.random.default_rng(31)
    v = np.arange(n) / n
    rib = np.abs(np.sin(np.pi * ribs * v)) ** 0.7
    height = np.repeat(rib[:, None], n, axis=1) + rng.normal(0, 0.03, (n, n))
    return normal_from_height('grosgrain-normal', height, 1.4)


def build_board(scheme='light', name='Board', thick=0.022, bevel=0.003):
    """A unit sample board: 1 x 1 across, front face at z = 0 (three.js), so a mark from
    marks.glb sits on it. Scale x and y to the element; scale z by the element's width.
    The bevel is a fraction of the unit, so it scales with the element: `Board` (0.003) is cut
    for the ~550 px plates, `Chip` (0.008, a little thicker) for the ~210 px colour chips, which
    puts about 1.7 px of edge on each."""
    M = {'Face': material('Face', scheme, 0.7, unlit=True), 'Edge': material('Edge', scheme, 0.55)}
    root = empty(name)
    bm = bmesh.new()
    for f in add_box(bm, (-0.5, 0.0, -0.5), (0.5, thick, 0.5), 1, bevel=bevel, segments=2):
        if f.normal.y < -0.9 and f.calc_area() > 0.5:
            f.material_index = 0
    finish(name + 'Mesh', bm, [M['Face'], M['Edge']], parent=root, smooth_angle=30)
    return root


def build_leaf(scheme='light'):
    """A sheet of paper to turn: hinge on x = 0, free edge at x = 1, y from -0.5 to 0.5, flat at
    z = 0, facing +z (three.js). 64 x 8 quads so it can bend along its width. Two skins on the
    same shape: Leaf (the side facing the reader) and LeafBack (the underside)."""
    grain = paper_normal()
    M = {
        'Leaf': material('Leaf', scheme, 0.93, normal_img=grain, normal_strength=0.5, repeat=5.0),
        'LeafBack': material('LeafBack', scheme, 0.93, normal_img=grain, normal_strength=0.5, repeat=5.0),
    }
    root = empty('Leaf')
    cols, rows = 64, 8
    bm = bmesh.new()
    for side, (y, mat) in enumerate(((0.0, 0), (0.0004, 1))):
        grid = [[bm.verts.new((c / cols, y, r / rows - 0.5)) for c in range(cols + 1)] for r in range(rows + 1)]
        for r in range(rows):
            for c in range(cols):
                quad = [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
                f = bm.faces.new(quad if side == 0 else quad[::-1])
                f.material_index = mat
    finish('LeafMesh', bm, [M['Leaf'], M['LeafBack']], parent=root, uv=lambda co, n, m: (co.x, co.z + 0.5), smooth_angle=180)
    return root


def build_straps(scheme='light'):
    """Two grosgrain strips, 1 wide, hanging down -y from the origin in rows 1 unit apart
    (40 rows): `RibbonStrip` ends in a swallowtail (the bookmark), `StrapStrip` ends square
    (the lanyard). The site lays the rows along a simulated chain."""
    weave = grosgrain_normal()
    mat = material('Strap', scheme, 0.62, normal_img=weave, normal_strength=0.7, repeat=(1.0, 40.0), double=True)
    root = empty('Straps')
    length = 40
    for name, tail in (('RibbonStrip', 0.62), ('StrapStrip', 0.0)):
        bm = bmesh.new()
        grid = []
        for r in range(length + 1):
            row = []
            for c in range(3):
                z = -r + (tail if (r == length and c == 1) else 0.0)
                row.append(bm.verts.new(((c - 1) * 0.5, 0, z)))
            grid.append(row)
        for r in range(length):
            for c in range(2):
                bm.faces.new([grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]])
        finish(name, bm, [mat], parent=root, uv=lambda co, n, m: (co.x + 0.5, -co.z / length), smooth_angle=180)
    return root


# ── export, preview and renders ────────────────────────────────────────────

def family(root):
    out = [root]
    for child in root.children:
        out.extend(family(child))
    return out


def export(root, filename):
    for ob in bpy.context.scene.objects:
        ob.select_set(False)
    for ob in family(root):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = root
    path = os.path.join(OUT, filename)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
        export_cameras=False, export_lights=False, export_animations=False, export_extras=False,
        export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
        export_image_format='AUTO',
    )
    tris = sum(len(p.vertices) - 2 for ob in family(root) if ob.type == 'MESH' for p in ob.data.polygons)
    print(f'[build] {filename}: {os.path.getsize(path) / 1024:.1f} kB, {tris} triangles')


def studio(scene, scheme, transparent=True, size=(900, 1125), samples=96, gain=1.0, ambient=None):
    """A soft product-shot setup. Standard view transform keeps the brand colours honest."""
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception as err:
        print('[build] GPU unavailable, rendering on CPU:', err)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = transparent
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'

    world = bpy.data.worlds.new('Studio')
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = srgb(PALETTE[scheme]['bone'])
    bg.inputs['Strength'].default_value = ambient if ambient is not None else (0.22 if scheme == 'light' else 0.5)
    scene.world = world

    def area(name, loc, size_, power, colour=(1, 1, 1)):
        data = bpy.data.lights.new(name, 'AREA')
        data.shape = 'RECTANGLE'
        data.size, data.size_y = size_
        data.energy = power
        data.color = colour
        ob = bpy.data.objects.new(name, data)
        ob.location = loc
        direction = Vector((0, 0, 0)) - Vector(loc)
        ob.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(ob)
        return ob

    area('Key', (-4.5, -6.5, 5.5), (5, 5), 1500 * gain, (1.0, 0.97, 0.92))
    area('Fill', (5.5, -5.0, 0.5), (4, 6), 260 * gain, (0.94, 0.96, 1.0))
    area('Rim', (2.5, 4.0, 4.0), (3, 3), 700 * gain)

    cam_data = bpy.data.cameras.new('Camera')
    cam_data.lens = 85
    cam_data.sensor_width = 36
    cam = bpy.data.objects.new('Camera', cam_data)
    cam.location = (0, -11.5, 0.25)
    cam.rotation_euler = (Vector((0, 0, -0.05)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def recolour(scheme):
    """Repaint every token-driven material for a colour scheme."""
    for mat in bpy.data.materials:
        if mat.name not in TOKENS:
            continue
        colour = srgb(PALETTE[scheme][TOKENS[mat.name]])
        mix = next((n for n in mat.node_tree.nodes if n.type == 'MIX'), None)
        if mix:
            mix.inputs[7].default_value = colour
        else:
            next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = colour


def flat(name, hex_):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = srgb(hex_)
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Specular IOR Level'].default_value = 0.0
    return mat


def social_card(scene, book):
    """1200x630 card: the wordmark on bone, the book beside it casting a real shadow."""
    pal = PALETTE['light']
    bm = bmesh.new()
    wall = 0.9
    add_quad(bm, [(-12, wall, -8), (12, wall, -8), (12, wall, 8), (-12, wall, 8)], 0)
    em = 1.02
    left, top = -3.02, 0.62
    for i, (line, indent) in enumerate((('Remy', 0.0), ('Post', 0.62))):
        me = text_mesh(line, 'Archivo-Wide-560', em, tracking=0.965)
        b = bounds(me)
        append(bm, me, facing('front', (left + indent * em - b[0], wall - 0.002, top - i * em * 0.82 - CAP_HEIGHT * em)), 1)
    for i, line in enumerate(('Identity Guidelines', 'Version 1.0')):
        me = text_mesh(line, 'Archivo-Regular-500', 0.115, tracking=1.02)
        append(bm, me, facing('front', (left + i * 1.9, wall - 0.002, 1.2)), 2)
    add_quad(bm, [(left, wall - 0.002, 1.08), (0.72, wall - 0.002, 1.08), (0.72, wall - 0.002, 1.086), (left, wall - 0.002, 1.086)], 2)
    card = finish('Card', bm, [flat('CardBone', pal['bone']), flat('CardInk', pal['ink']), flat('CardStone', pal['stone'])])
    cam = scene.camera
    cam.data.lens = 85
    cam.location = (0, -16.5, 0)
    cam.rotation_euler = (radians(90), 0, 0)
    scene.render.resolution_x, scene.render.resolution_y = 1200, 630
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.quality = 90
    book.location = (2.1, -0.75, 0.12)
    book.scale = (0.86, 0.86, 0.86)
    pose_book(book, turn=-24, tilt=6, roll=-4)
    return card


def pose_book(root, turn=-26, tilt=7, roll=-3, open_=0):
    """Rest pose used for renders. In three.js the same turn is rotation.y (same sign)."""
    root.rotation_euler = (radians(tilt), radians(roll), radians(turn))
    cover = next(c for c in root.children if c.name == 'CoverFront')
    cover.rotation_euler = (0, 0, radians(-open_))


def show(root, visible):
    for ob in family(root):
        ob.hide_render = not visible


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('[build] rendered', path)


def main():
    scene = reset()
    book = build_book('light')
    export(book, 'book.glb')
    mono = build_monogram('light')
    export(mono, 'monogram.glb')
    mono.location = (4, 0, 0)
    marks = build_marks('light')
    export(marks, 'marks.glb')
    envelope = build_envelope('light')
    export(envelope, 'envelope.glb')
    badge = build_badge('light')
    export(badge, 'badge.glb')
    stamp = build_stamp('light')
    export(stamp, 'stamp.glb')
    stamp.location = (20, 0, 0)
    board = build_board('light')
    export(board, 'board.glb')
    board.location = (24, 0, 0)
    chip = build_board('light', name='Chip', thick=0.03, bevel=0.008)
    export(chip, 'chip.glb')
    chip.location = (26, 0, 0)
    leaf = build_leaf('light')
    export(leaf, 'leaf.glb')
    leaf.location = (28, 0, 0)
    straps = build_straps('light')
    export(straps, 'straps.glb')
    straps.location = (32, 0, 0)
    for i, child in enumerate(marks.children):
        child.location = (-2.6 + (i % 3) * 2.2, 0, 1.3 - (i // 3) * 1.1)
    marks.location = (8, 0, 0)
    envelope.location = (12, 0, 0)
    badge.location = (16, 0, 0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'remypost-models.blend'))

    if '--preview2' in ARGS:
        for r in (book, mono, marks, envelope, badge, stamp, board, chip, leaf, straps):
            show(r, False)
        cam = studio(scene, 'light', transparent=False, size=(900, 700), samples=48, ambient=0.3, gain=0.45)

        def shot(root, name, pos=(0, 0, 0), rot=(6, 0, -20), scale=1.0):
            show(root, True)
            root.location, root.scale = pos, (scale,) * 3
            root.rotation_euler = tuple(radians(v) for v in rot)
            render(os.path.join(OUT, name))
            show(root, False)

        shot(marks, 'preview-marks.png', pos=(0, 0, 0), rot=(0, 0, -12), scale=0.62)
        shot(envelope, 'preview-envelope.png', rot=(8, 0, -18), scale=1.25)
        flap = next(c for c in envelope.children if c.name == 'Flap')
        letter = next(c for c in envelope.children if c.name == 'Letter')
        flap.rotation_euler = (radians(-192), 0, 0)
        letter.location.z += 0.55
        shot(envelope, 'preview-envelope-open.png', pos=(0, 0, -0.7), rot=(8, 0, -18), scale=1.0)
        shot(stamp, 'preview-stamp.png', pos=(0, 0, -1.0), rot=(-38, 0, -20), scale=1.5)
        shot(badge, 'preview-badge.png', pos=(0, 0, 0.9), rot=(4, 0, -22), scale=1.6)
        shot(badge, 'preview-badge-back.png', pos=(0, 0, 0.9), rot=(4, 0, 158), scale=1.6)
        return

    if '--render' in ARGS:
        site = os.path.abspath(os.path.join(HERE, '..', '..', 'apps', 'site'))
        models = os.path.join(site, 'src', 'assets', 'models')
        os.makedirs(models, exist_ok=True)
        show(mono, False)
        samples = 32 if '--draft' in ARGS else 256
        for scheme in ('light', 'dark'):
            recolour(scheme)
            studio(scene, scheme, transparent=True, size=(720, 900), samples=samples, gain=1.0 if scheme == 'light' else 0.5)
            scene.render.image_settings.file_format = 'WEBP'
            scene.render.image_settings.color_mode = 'RGBA'
            scene.render.image_settings.quality = 84
            pose_book(book)
            render(os.path.join(models, f'book-poster-{scheme}.webp'))
            for ob in [o for o in scene.objects if o.type in {'LIGHT', 'CAMERA'}]:
                bpy.data.objects.remove(ob)
        recolour('light')
        studio(scene, 'light', transparent=False, samples=samples, gain=0.42, ambient=0.62)
        social_card(scene, book)
        render(os.path.join(site, 'public', 'og.jpg'))
        return

    if '--preview' in ARGS:
        show(mono, False)
        studio(scene, 'light', transparent=False, size=(900, 1125), samples=48)
        pose_book(book)
        render(os.path.join(OUT, 'preview-book.png'))
        pose_book(book, turn=150, tilt=4, roll=0)
        render(os.path.join(OUT, 'preview-book-back.png'))
        show(book, False)
        show(mono, True)
        mono.location = (0, 0, 0)
        mono.scale = (2.2, 2.2, 2.2)
        mono.rotation_euler = (radians(8), 0, radians(-24))
        scene.render.resolution_x, scene.render.resolution_y = 700, 700
        render(os.path.join(OUT, 'preview-monogram.png'))
        mono.rotation_euler = (radians(8), 0, radians(160))
        render(os.path.join(OUT, 'preview-monogram-back.png'))


main()
