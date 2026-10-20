#!/bin/sh
# Assemble the Cloudflare Workers upload. wrangler runs this before `dev` and `deploy` (see wrangler.jsonc).
#   public/        static assets: the page and its CSS / JS / icons
#   build/worker/  Python modules: worker.py and the Flask app
# wrangler uploads every file under main's directory, so the app is copied into its own folder
# rather than pointing main at the repo root (which would also pull in .venv/ and .venv-workers/).
set -eu
cd "$(dirname "$0")/.."
rm -rf public build/worker
mkdir -p public build/worker
# index.html is a Jinja template ({% raw %} blocks), so save what Flask actually serves for "/".
uv run python - <<'EOF'
from app import app

r = app.test_client().get("/")
assert r.status_code == 200, r.status
with open("public/index.html", "wb") as f:
    f.write(r.data)
EOF
cp -R static public/static
cp -R worker.py app.py routes services parsers utils data build/worker/
find build/worker -name __pycache__ -type d -prune -exec rm -rf {} +
