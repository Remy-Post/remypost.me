#!/bin/bash
# Swaps the "remypost" block in the VM's shared ~/n8n/caddy/Caddyfile for deploy/remypost.caddy, validates it
# inside the Caddy container and reloads; a failed validation puts the previous Caddyfile back. Safe to re-run.
# Run it from the Mac: deploy/vm-setup.sh
# Only our block is touched; the tokens and specs blocks belong to their own repos.
# Override the SSH target with REMYPOST_SSH_HOST (default: the "n8n" entry in ~/.ssh/config).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=20 "${REMYPOST_SSH_HOST:-n8n}")

echo "== updating the Caddyfile"
"${SSH[@]}" 'cat > ~/n8n/caddy/remypost.caddy.new' < "$HERE/remypost.caddy"
"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd ~/n8n
backup="caddy/Caddyfile.bak-remypost-$(date -u +%Y%m%d-%H%M%S)"
cp caddy/Caddyfile "$backup"
ls -1t caddy/Caddyfile.bak-remypost-* | tail -n +4 | xargs -r rm -f

# Our block runs from "# BEGIN remypost" to "# END remypost". Before the markers existed it started at the
# "# remypost.me — static build" comment and ended with the preview site's closing brace.
python3 -I - caddy/Caddyfile caddy/remypost.caddy.new <<'PY'
import sys
path, block_path = sys.argv[1], sys.argv[2]
src = open(path).read()
block = open(block_path).read().strip() + "\n"
start = src.find("# BEGIN remypost")
if start >= 0:
    end = src.find("# END remypost", start)
    if end < 0:
        sys.exit("found '# BEGIN remypost' without '# END remypost'; fix the Caddyfile by hand")
    end += len("# END remypost")
else:
    start = src.find("# remypost.me — static build")
    preview = src.find("\npreview.remy-post.duckdns.org {", start)
    close = src.find("\n}\n", preview)
    if start < 0 or preview < 0 or close < 0:
        sys.exit("could not find the unmarked remypost block; add the markers by hand")
    end = close + len("\n}")
before = src[:start]
after = src[end:].lstrip("\n")
open(path, "w").write(before + block + ("\n" + after if after else ""))
PY

# "docker compose exec" reads stdin, which is this script; </dev/null keeps it from eating the lines after it.
if docker compose exec -T caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile </dev/null; then
  docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile </dev/null
  echo "caddy reloaded (backup: ~/n8n/$backup)"
else
  cp "$backup" caddy/Caddyfile
  echo "validation failed; previous Caddyfile restored" >&2
  exit 1
fi
rm -f caddy/remypost.caddy.new
REMOTE
