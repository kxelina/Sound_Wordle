#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
elif [[ -x "$PROJECT_DIR/venv/bin/python" ]]; then
    PYTHON="$PROJECT_DIR/venv/bin/python"
else
    cat >&2 <<'EOF'
Sound Detective's Python environment was not found.

From this directory, create it and install the Linux dependencies:
  python3.11 -m venv .venv
  .venv/bin/python -m pip install -r requirements-linux.txt

Then install SuperCollider using your Linux distribution's package manager
and run this launcher again.
EOF
    exit 2
fi

exec "$PYTHON" -m sound_detective.launcher "$@"
