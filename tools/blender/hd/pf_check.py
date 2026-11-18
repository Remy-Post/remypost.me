"""Re-import a compressed glb and render it in the same studio as its still, optionally with nodes moved:
-- <name> <radius> <focus_z> <azimuth> <elevation> <distance> <focus_y> [<out suffix> <moves json>]
moves: {"node": {"loc": [x, y, z] metres in root space, "rot": [x, y, z] degrees about the node's own axes}}"""
import bpy, os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
from mathutils import Matrix, Euler
name, r, fz, az, el, dist = ARGS[0], float(ARGS[1]), float(ARGS[2]), float(ARGS[3]), float(ARGS[4]), float(ARGS[5])
off = float(ARGS[6]) if len(ARGS) > 6 else 0.0
suffix = ARGS[7] if len(ARGS) > 7 else 'check'
moves = json.loads(ARGS[8]) if len(ARGS) > 8 else {}
scene = reset()
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, '..', '..', '..', 'apps', 'site', 'src', 'assets', 'models', name + '.glb'))
root = bpy.data.objects[name]
print('[check] nodes', sorted(o.name for o in root.children))
bpy.context.view_layer.update()
for node, mv in moves.items():
    o = bpy.data.objects[node]
    m = o.matrix_local.copy()
    m = Matrix.Translation(mv.get('loc', (0, 0, 0))) @ m @ Euler([math.radians(a) for a in mv.get('rot', (0, 0, 0))]).to_matrix().to_4x4()
    o.matrix_local = m
studio(scene, (0, off, fz), r, azimuth=az, elevation=el, lens=85, distance=dist)
render(scene, os.path.join(OUT, 'web', f'{name}-{suffix}.png'), 1000, 128)
