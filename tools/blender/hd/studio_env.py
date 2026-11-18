"""The studio's softboxes as a small equirectangular HDR for the site's environment map (no objects).

Panels: the key, fill, rim and top lights of common.studio() plus the four reflection panels of cloche.py,
on a dark surround. Oriented for three.js: Blender +Z up, the image centre looks down Blender +X.
"""
import bpy, bmesh, math, os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: F401,F403
from mathutils import Vector

scene = reset()
world = bpy.data.worlds.new('Dark')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.012, 0.013, 0.016, 1)
scene.world = world

r = 0.15
f = Vector((0, 0, 0))
panels = [
    ('Key', (-5.5 * r, -6.5 * r, 7.5 * r), (6 * r, 6 * r), 9.0, (1.0, 0.97, 0.93)),
    ('Fill', (7 * r, -5 * r, 2.5 * r), (8 * r, 8 * r), 0.9, (0.86, 0.92, 1.0)),
    ('Rim', (4.5 * r, 7 * r, 5 * r), (3 * r, 9 * r), 10.0, (0.9, 0.95, 1.0)),
    ('Top', (0, 1.5 * r, 9 * r), (10 * r, 3 * r), 2.2, (1, 1, 1)),
    ('PanelLeft', (-0.62, -0.42, 0.28), (0.50, 0.95), 2.6, (1.0, 0.97, 0.93)),
    ('PanelRight', (0.70, -0.20, 0.24), (0.16, 1.10), 3.4, (0.88, 0.93, 1.0)),
    ('PanelTop', (0.05, 0.10, 0.72), (0.90, 0.34), 1.8, (1, 1, 1)),
    ('PanelBack', (-0.15, 0.85, 0.34), (1.3, 0.10), 2.2, (0.9, 0.95, 1.0)),
]
for name, loc, size, strength, tint in panels:
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(size[0], size[1], 1))
    ob = mesh_object(name, bm, smooth=False)
    ob.location = loc
    ob.rotation_euler = (f - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    assign(ob, emission('Mat' + name, tint, strength))

# A faint floor glow below the horizon, as the dark studio floor returns a little of the key.
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, radius=2.2, segments=64)
floor = mesh_object('Floor', bm, smooth=False)
floor.location = (0, 0, -0.06)
assign(floor, principled('FloorEnv', (0.03, 0.032, 0.036), 0.5))

cam = bpy.data.cameras.new('Pano')
cam.type = 'PANO'
cam.panorama_type = 'EQUIRECTANGULAR'
cam_ob = link(bpy.data.objects.new('Pano', cam))
cam_ob.location = f
cam_ob.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
scene.camera = cam_ob

scene.render.engine = 'CYCLES'
scene.cycles.samples = 256
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1024, 512
scene.render.image_settings.file_format = 'HDR'
path = os.path.join(OUT, 'web', 'studio.hdr')
scene.render.filepath = path
bpy.ops.render.render(write_still=True)
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = os.path.join(OUT, 'web', 'studio-preview.png')
bpy.data.images['Render Result'].save_render(scene.render.filepath)
shutil.copyfile(path, os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'env', 'studio.hdr'))
print('[hd] wrote', path)
