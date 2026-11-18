"""AgentUI: a desktop app window as an object. A glass-and-aluminium slab on a stand, a conversation glowing inside.

  --render   the studio still (out/hd/window.png)
  --export   bake the screen to one emissive texture and write apps/site/src/assets/models/window.glb
  --check    re-import the shipped .glb and render out/hd/web/window-check.png
"""
import bpy, bmesh, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
import lawnwin_web as web
from mathutils import Vector, Matrix

MM = 0.001
FONT_WIDE = os.path.join(HERE, '..', 'fonts', 'Archivo-Wide-600.ttf')
FONT_REG = os.path.join(HERE, '..', 'fonts', 'Archivo-Regular-500.ttf')
W, H, T = 0.300, 0.200, 0.0125       # slab: width, height, thickness
RC = 0.013                           # corner radius
RIM = 2.4 * MM                       # aluminium rim visible around the glass
GAIN = 2.7                           # screen brightness against the studio key
SCROLL = 0.0085                      # how far the thread moves up when the follow-up is sent
EXPORT = '--export' in ARGS
CAM = dict(azimuth=-28, elevation=10, lens=85, distance=1.02)
FOCUS, RADIUS = (0.0, 0.01, 0.125), 0.17
_emission = emission


def emission(name, color, strength=1.0):
    """Screen pixels: emissive only, with no specular, so the studio lights do not veil the picture."""
    quiet = name in ('UiBg', 'UiChrome', 'UiSide', 'UiCard')
    mat = _emission(name, color, strength * (0.55 if quiet else GAIN))
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Specular IOR Level'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 1.0
    return mat


def rrect_pts(w, h, r, seg=10):
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def plate(name, w, h, r, cx, cz, y, mat, parent, seg=8):
    """A flat rounded rectangle facing -Y at depth y."""
    bm = bmesh.new()
    r = min(r, w / 2 - 1e-6, h / 2 - 1e-6)
    bm.faces.new([bm.verts.new((cx + x, y, cz + z)) for x, z in reversed(rrect_pts(w, h, r, seg))])
    return assign(mesh_object(name, bm, parent, smooth=False), mat)


def slab(name, w, h, r, y0, y1, parent, bev=0.0, seg=14):
    """A rounded-rectangle prism from depth y0 (front) to y1 (back)."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y0, z)) for x, z in rrect_pts(w, h, r, seg)]
    back = [bm.verts.new((x, y1, z)) for x, z in rrect_pts(w, h, r, seg)]
    bm.faces.new(list(reversed(front))); bm.faces.new(back)
    n = len(front)
    for i in range(n):
        bm.faces.new((front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_object(name, bm, parent)
    if bev:
        bevel(ob, bev, 4, 50)
    return ob


def loft(name, sections, parent, seg=6):
    """Loft rounded-rectangle sections [(centre xyz, width, thickness, tilt about X)] into one closed solid."""
    bm = bmesh.new()
    rings = []
    for (c, w, t, tilt) in sections:
        rot = Matrix.Rotation(tilt, 3, 'X')
        rings.append([bm.verts.new(Vector(c) + rot @ Vector((x, y, 0))) for x, y in rrect_pts(w, t, min(t * 0.45, w * 0.45), seg)])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_object(name, bm, parent)


def label(body, size, x, z, y, mat, parent, font=FONT_REG, align='LEFT'):
    t = text_mesh('Text', body, size, font if os.path.exists(font) else None, parent=parent, align=align)
    t.rotation_euler = (math.pi / 2, 0, 0)
    t.location = (x, y, z)
    t.data.materials.append(mat)
    return t


def build(scene):
    root = link(bpy.data.objects.new('window', None))
    body = link(bpy.data.objects.new('Slab', None), root)
    groups, cur = {}, ['screen_base']                  # screen pixels, by layer

    def reg(o):
        groups.setdefault(cur[0], []).append(o); return o

    alu = principled('Aluminium', (0.74, 0.75, 0.77), 0.30, 1.0)
    alu_dark = principled('AluminiumDark', (0.18, 0.185, 0.195), 0.36, 1.0)
    polished = principled('AluminiumPolished', (0.86, 0.87, 0.88), 0.10, 1.0)
    if not EXPORT:
        roughness_breakup(alu, scale=1400, amount=0.07, bump=0.012, stretch=(1, 1, 40))
        roughness_breakup(alu_dark, scale=900, amount=0.08)
    # Anti-reflective cover glass: a low index keeps the softbox from washing over the picture.
    glass = principled('Glass', (1, 1, 1), 0.03, 0.0, Transmission_Weight=1.0, IOR=1.16)
    rubber = principled('Foot', (0.02, 0.02, 0.022), 0.7)

    bg = emission('UiBg', (0.030, 0.034, 0.045), 1.0)
    chrome = emission('UiChrome', (0.060, 0.066, 0.084), 1.0)
    side = emission('UiSide', (0.042, 0.047, 0.062), 1.0)
    card = emission('UiCard', (0.085, 0.094, 0.120), 1.0)
    sel = emission('UiSelected', (0.07, 0.11, 0.30), 0.4)
    blue = emission('UiBlue', (0.04, 0.12, 0.90), 0.5)
    text = emission('UiText', (0.92, 0.94, 1.0), 1.7)
    mute = emission('UiMuted', (0.42, 0.46, 0.56), 1.0)
    ok = emission('UiGreen', (0.16, 0.85, 0.40), 1.8)
    bad = emission('UiRed', (1.0, 0.30, 0.25), 1.8)
    dots = [emission('DotRed', (1.0, 0.27, 0.22), 2.0), emission('DotAmber', (1.0, 0.72, 0.12), 2.0), emission('DotGreen', (0.20, 0.86, 0.30), 2.0)]

    def P(*a, **k):
        return reg(plate(*a, **k))

    def Lb(*a, **k):
        return reg(label(*a, **k))

    def dot(name, r, x, z, y, mat):
        bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, radius=r, segments=40)
        d = mesh_object(name, bm, body, smooth=False)
        d.rotation_euler = (math.pi / 2, 0, 0); d.location = (x, y, z)
        reg(assign(d, mat)); return d

    # Frame: an aluminium tub. A polished chamfer runs round the front, and the glass sits inside a visible rim.
    frame = slab('Frame', W, H, RC, 0.0, T, body, bev=1.1 * MM)
    assign(frame, alu)
    lip = slab('Lip', W - 0.6 * MM, H - 0.6 * MM, RC - 0.3 * MM, -0.9 * MM, 0.2 * MM, body, bev=0.45 * MM)
    assign(lip, polished)
    gw, gh, gr = W - 2 * RIM, H - 2 * RIM, RC - RIM     # glass opening
    bz = 3.0 * MM                                       # black border under the glass
    sw, sh = gw - 2 * bz, gh - 2 * bz
    yf = -1.0 * MM                                      # layers step toward the viewer in 0.1 mm; the glass starts at -1.3 mm
    assign(plate('Mask', gw, gh, gr, 0, 0, yf + 0.02 * MM, principled('ScreenMask', (0.004, 0.004, 0.005), 0.4), body, seg=14), bpy.data.materials['ScreenMask'])
    P('Screen', sw, sh, gr - bz, 0, 0, yf, bg, body, seg=14)

    L, Rt, Top, Bot = -sw / 2, sw / 2, sh / 2, -sh / 2
    y1, y2, y3 = yf - 0.03 * MM, yf - 0.06 * MM, yf - 0.09 * MM

    tb = 0.0125
    P('TitleBar', sw, tb, 0.0004, 0, Top - tb / 2, y1, chrome, body)
    for i, m in enumerate(dots):
        dot('Dot', 0.00215, L + 0.0085 + i * 0.0070, Top - tb / 2, y2, m)
    Lb('AgentUI', 0.0050, 0, Top - tb / 2, y2, text, body, FONT_WIDE, 'CENTER')

    sbw = 0.074
    P('Sidebar', sbw, sh - tb, 0.0004, L + sbw / 2, Bot + (sh - tb) / 2, y1, side, body)
    Lb('Conversations', 0.0038, L + 0.0075, Top - tb - 0.0095, y2, mute, body)
    names = ['Fix the upload tests', 'Weekly report draft', 'Refactor auth flow', 'Plan the release', 'Import course data', 'Rename the modules', 'Review the schema']
    whens = ['now', '2 h', 'Tue', 'Mon', 'Nov 9', 'Nov 6', 'Nov 2']
    for i, (nm, wh) in enumerate(zip(names, whens)):
        zc = Top - tb - 0.0230 - i * 0.0165
        if i == 0:
            P('RowSel', sbw - 0.008, 0.0140, 0.0030, L + sbw / 2, zc, y2, sel, body)
            P('RowBar', 0.0012, 0.0080, 0.0006, L + 0.0052, zc, y3, blue, body)
        Lb(nm, 0.0043, L + 0.0090, zc + 0.0019, y3, text if i == 0 else mute, body)
        Lb(wh, 0.0033, L + 0.0090, zc - 0.0034, y3, mute, body)
    P('NewBtn', sbw - 0.012, 0.0115, 0.0030, L + sbw / 2, Bot + 0.0110, y2, card, body)
    Lb('New conversation', 0.0040, L + sbw / 2, Bot + 0.0110, y3, text, body, FONT_REG, 'CENTER')

    cl, cr = L + sbw + 0.010, Rt - 0.010
    rects, lines_of = {'screen_base': (L, Bot, sw, sh)}, {}

    def bubble(name, x0, x1, ztop, lines, mat, tmat, size=0.0046, lead=0.0074, pad=0.0052, radius=0.0046):
        cur[0] = name
        h = pad * 2 + lead * (len(lines) - 1) + size * 0.72
        P('Bubble', x1 - x0, h, radius, (x0 + x1) / 2, ztop - h / 2, y2, mat, body, seg=10)
        lines_of[name] = [Lb(ln, size, x0 + pad, ztop - pad - size * 0.36 - i * lead, y3, tmat, body) for i, ln in enumerate(lines)]
        rects[name] = (x0, ztop - h, x1 - x0, h)
        return ztop - h

    z = Top - tb - 0.0090
    z = bubble('bubble_user', cr - 0.118, cr, z, ['Run the test suite and tell me', 'what broke.'], blue, text) - 0.0060
    z = bubble('bubble_agent_1', cl, cl + 0.092, z, ['Running 214 tests in the repo.'], card, text) - 0.0045
    cur[0] = 'tool_card'
    ch = 0.0300
    P('Tool', 0.136, ch, 0.0040, cl + 0.068, z - ch / 2, y2, chrome, body, seg=10)
    P('ToolHead', 0.136 - 0.0016, 0.0098, 0.0032, cl + 0.068, z - 0.0057, y3, card, body, seg=10)
    Lb('pytest  tests/', 0.0040, cl + 0.0050, z - 0.0057, y3 - 0.00002, mute, body)
    for i, (m, txt) in enumerate(((ok, '212 passed'), (bad, '2 failed'))):
        zc = z - 0.0162 - i * 0.0072
        dot('Status', 0.0013, cl + 0.0064, zc, y3, m)
        Lb(txt, 0.0040, cl + 0.0105, zc, y3, text, body)
    Lb('8.4 s', 0.0038, cl + 0.136 - 0.0052, z - 0.0057, y3 - 0.00002, mute, body, FONT_REG, 'RIGHT')
    rects['tool_card'] = (cl, z - ch, 0.136, ch)
    z -= ch + 0.0045
    z = bubble('bubble_agent_2', cl, cl + 0.128, z, ['Two failures, both in the upload', 'handler: the retry path never fires.'], card, text)
    if EXPORT:
        # The follow-ups, hidden until the visitor sends: placed where they land once the thread has scrolled up by SCROLL.
        z2 = z - 0.0060 + SCROLL
        z2 = bubble('bubble_user_2', cr - 0.072, cr, z2, ['Fix it and run them again.'], blue, text) - 0.0060
        bubble('bubble_agent_3', cl, cl + 0.128, z2, ['Fixed. The retry now fires after a', 'timeout, and I added a test for it.', 'All 215 tests pass.'], card, text)
    bpy.context.view_layer.update()

    def caret_at(name):                                # bottom-left corner of a caret after the last line of a bubble
        t = lines_of[name][-1]
        return (t.location.x + t.dimensions.x + 0.0014, t.location.z - 0.0029)

    caret_at_sent = caret_at('bubble_agent_3') if EXPORT else None
    cur[0] = 'caret'
    cx0, cz0 = caret_at('bubble_agent_2')
    P('Caret', 0.0010, 0.0058, 0.0002, cx0 + 0.0005, cz0 + 0.0029, y3 - 0.00002, text, body)
    rects['caret'] = (cx0, cz0, 0.0010, 0.0058)
    cur[0] = 'screen_base'

    P('Composer', cr - cl, 0.0135, 0.0050, (cl + cr) / 2, Bot + 0.0110, y2, card, body, seg=10)
    Lb('Reply to the agent', 0.0042, cl + 0.0060, Bot + 0.0110, y3, mute, body)
    dot('Send', 0.0042, cr - 0.0068, Bot + 0.0110, y3, blue)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in ((-0.0017, 0, -0.0012), (0.0017, 0, -0.0012), (0, 0, 0.0020))])
    arrow = mesh_object('SendArrow', bm, body, smooth=False); arrow.location = (cr - 0.0068, y3 - 0.00003, Bot + 0.0110)
    reg(assign(arrow, text))

    if EXPORT:
        # Photograph each layer straight-on into its own alpha emissive texture, then replace the pixels with quads.
        # Each layer is an empty at the layer's bottom-left corner (clean transform, so it can scale in) holding one quad.
        import json
        peak = 2.0 * GAIN
        order = ['screen_base', 'bubble_user', 'bubble_agent_1', 'tool_card', 'bubble_agent_2', 'bubble_user_2', 'bubble_agent_3', 'caret']
        imgs = {}
        for name in order:
            x0, zb, w, h = rects[name]
            dens = 7000 if name == 'screen_base' else 14000
            imgs[name], _ = web.capture(scene, groups[name], (x0 + w / 2, 0, zb + h / 2), w, h, max(16, min(2048, round(w * dens))),
                                        os.path.join(web.WEB, f'window_{name}.png'), emissive=True, alpha=True, peak=peak)
        for objs in groups.values():
            for o in objs:
                bpy.data.objects.remove(o)
        manifest = {'parent': 'Slab', 'axes': 'glTF local to Slab: x right, y up the screen, z toward the viewer', 'scroll': SCROLL,
                    'scroll_nodes': ['bubble_user', 'bubble_agent_1', 'tool_card', 'bubble_agent_2'], 'hidden_at_start': ['bubble_user_2', 'bubble_agent_3'],
                    'caret_sent': list(caret_at_sent), 'layers': {}}
        for name in order:
            x0, zb, w, h = rects[name]
            y = yf - (0.0 if name == 'screen_base' else 0.0002 if name == 'caret' else 0.0001)
            node = link(bpy.data.objects.new(name, None), body); node.location = (x0, y, zb)
            q = web.quad(name + '_quad', w, h, (w / 2, 0, h / 2), node)
            mat = web.image_material('Ui_' + name, emissive=imgs[name], strength=peak * 0.55, rough=1.0)
            b = web.bsdf_of(mat); b.inputs['Specular IOR Level'].default_value = 0.0
            tex = next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE')
            mat.node_tree.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
            try:
                mat.blend_method = 'BLEND'
            except Exception:
                pass
            q.data.materials.append(mat)
            manifest['layers'][name] = {'position': [round(x0, 5), round(zb, 5), round(-y, 5)], 'size': [round(w, 5), round(h, 5)]}
        json.dump(manifest, open(os.path.join(web.WEB, 'window-layers.json'), 'w'), indent=1)
        print('[hd] layers', json.dumps(manifest))

    # Cover glass, set inside the rim and standing a hair proud of it.
    cover = slab('CoverGlass', gw - 0.1 * MM, gh - 0.1 * MM, gr, -2.3 * MM, -1.3 * MM, body, bev=0.3 * MM)
    assign(cover, glass)
    assign(slab('BackPanel', W - 0.030, H - 0.030, 0.008, T - 0.0002, T + 0.0006, body, bev=0.25 * MM), alu_dark)

    # Stand: a wide foot, a neck that tapers and sweeps forward, and a hinge barrel between two knuckles on the back.
    tilt = math.radians(9)
    lift = 0.030
    body.rotation_euler = (-tilt, 0, 0)
    body.location = (0, 0, lift + H / 2 * math.cos(tilt) + 0.002)
    foot = slab('Foot', 0.160, 0.078, 0.016, 0, 0.0056, root, bev=1.2 * MM)
    foot.rotation_euler = (math.pi / 2, 0, 0); foot.location = (0, 0.052, 0.0056); assign(foot, alu)
    pad = slab('FootPad', 0.150, 0.068, 0.012, 0, 0.0012, root)
    pad.rotation_euler = (math.pi / 2, 0, 0); pad.location = (0, 0.052, 0.0012); assign(pad, rubber)
    hz = body.location.z - 0.010                      # hinge height: just below the middle of the back
    hy = T * math.cos(tilt) + 0.012 + math.sin(tilt) * 0.010
    secs = []
    for i in range(13):
        u = i / 12
        y = 0.074 + (hy - 0.074) * (3 * u * u - 2 * u ** 3)           # sweeps forward to the hinge
        zz = 0.0056 + (hz - 0.0056) * u
        secs.append(((0, y, zz), 0.060 - 0.026 * u ** 0.8, 0.0085 - 0.002 * u, math.radians(-12) * (1 - u)))
    neck = loft('Neck', secs, root)
    bevel(neck, 0.5 * MM, 3, 60); assign(neck, alu)
    for name, half, r, mat in (('HingeBarrel', 0.019, 0.0062, polished), ('KnuckleL', 0.0, 0.0, None), ('KnuckleR', 0.0, 0.0, None)):
        if mat is None:
            s = -1 if name.endswith('L') else 1
            k = slab(name, 0.014, 0.022, 0.004, 0, 0.014, root, bev=0.6 * MM)
            k.rotation_euler = (-tilt, 0, 0); k.location = (s * 0.028, hy - 0.013, hz); assign(k, alu_dark)
        else:
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, radius1=r, radius2=r, depth=half * 2, segments=48)
            b = mesh_object(name, bm, root); b.rotation_euler = (0, math.pi / 2, 0); b.location = (0, hy, hz)
            bevel(b, 0.5 * MM, 3); assign(b, mat)
    for s in (-1, 1):                                  # hinge end caps
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, radius1=0.0072, radius2=0.0072, depth=0.004, segments=48)
        c = mesh_object('HingeCap', bm, root); c.rotation_euler = (0, math.pi / 2, 0); c.location = (s * 0.037, hy, hz)
        bevel(c, 0.5 * MM, 3); assign(c, alu_dark)
    return root


def check():
    """Re-import the shipped .glb and render it as loaded (follow-ups hidden) and after the visitor sends."""
    import json
    man = json.load(open(os.path.join(web.WEB, 'window-layers.json')))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=os.path.join(web.MODELS, 'window.glb'))
    studio(scene, FOCUS, RADIUS, **CAM)

    def show(name, on):
        for o in [bpy.data.objects[name]] + list(bpy.data.objects[name].children_recursive):
            o.hide_render = not on
    for n in man['hidden_at_start']:
        show(n, False)
    render(scene, os.path.join(web.WEB, 'window-check.png'), 1000, 128)
    for n in man['hidden_at_start']:
        show(n, True)
    for n in man['scroll_nodes']:
        bpy.data.objects[n].location.z += man['scroll']
    c = bpy.data.objects['caret']
    c.location.x, c.location.z = man['caret_sent']
    render(scene, os.path.join(web.WEB, 'window-check-sent.png'), 1000, 128)


def main():
    if '--check' in ARGS:
        check()
        return
    scene = reset()
    root = build(scene)
    bpy.context.view_layer.update()
    print('[hd] window triangles', web.triangles(scene.objects))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'window-web.blend' if EXPORT else 'window.blend'))
    if EXPORT:
        web.export_glb(root, 'window')
    if '--render' in ARGS:
        studio(scene, FOCUS, RADIUS, **CAM)
        render(scene, os.path.join(OUT, 'window.png'), arg('--size', 1400), arg('--samples', 256))


main()
