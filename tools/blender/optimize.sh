#!/bin/sh
# Compress the raw exports in tools/blender/out/ into the files the site ships.
# Meshopt geometry + WebP textures; nodes and materials keep their names, because
# the site looks them up by name (so no join / flatten / palette / simplify).
set -e
cd "$(dirname "$0")"
DEST=../../apps/site/src/assets/models
mkdir -p "$DEST"
for name in book monogram marks envelope badge stamp board chip leaf straps; do
  npx --yes @gltf-transform/cli@4 optimize "out/$name.glb" "$DEST/$name.glb" \
    --compress meshopt --texture-compress webp --texture-size 256 \
    --join false --flatten false --palette false --simplify false --instance false
done
ls -l "$DEST"
