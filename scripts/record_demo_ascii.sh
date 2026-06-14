#!/usr/bin/env bash
# Pure-terminal fallback for the 3-minute demo.
# Requires: asciinema (brew install asciinema | pip install asciinema)
# Optional: svg-term (npm install -g svg-term) for GIF export.
#
# Usage:
#   bash scripts/record_demo_ascii.sh           # interactive recording
#   bash scripts/record_demo_ascii.sh --no-act  # just print the script (dry run)
#
# Output:
#   docs/videos/demo_3min.cast   (asciicast v2 format)
#   docs/videos/demo_3min.gif    (if svg-term is installed)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VIDEO_DIR="${PROJECT_ROOT}/docs/videos"
mkdir -p "${VIDEO_DIR}"

DRY_RUN=0
for arg in "$@"; do
  case "${arg}" in
    --no-act) DRY_RUN=1 ;;
  esac
done

# === Scene 1: cold open (5s) ===
cat <<'EOF'

================================================================
   ERP AI Copilot — built on MACS
   github.com/blank5this/MACS
   MIT licensed · 256 tests passing
================================================================

EOF
sleep 3

# === Scene 2: framework demo (no DB needed) ===
export MINIMAX_API_KEY="${MINIMAX_API_KEY:-sk-cp-dummy-key-for-dry-run}"
cat <<'EOF'

--- Demonstrating RAG over 18 Chinese ERP policy documents ---

EOF

if [ "${DRY_RUN}" -eq 0 ]; then
  pushd "${PROJECT_ROOT}" > /dev/null
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python examples/demo_for_client.py || true
  popd > /dev/null
fi

sleep 2

# === Scene 3: Text2SQL on the bundled SQLite demo ===
cat <<'EOF'

--- Text2SQL: ask "哪些商品库存低于安全库存？" ---

EOF

if [ "${DRY_RUN}" -eq 0 ]; then
  pushd "${PROJECT_ROOT}" > /dev/null
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python - <<'PY'
from macs_pkg.erp.demo import run
r = run("哪些商品库存低于安全库存？")
print(r.summary)
print()
print(r.rows_text)
PY
  popd > /dev/null
fi

# === Scene 4: closing (60s, intentional pause for viewer to click through) ===
cat <<'EOF'

----------------------------------------------------------------
  🔗  github.com/blank5this/MACS
  📧  blank5this [at] example.com
  💼  Hiring AI Application Engineers — DM via LinkedIn
----------------------------------------------------------------

EOF

# === Record with asciinema ===
if command -v asciinema >/dev/null 2>&1 && [ "${DRY_RUN}" -eq 0 ]; then
  echo "Recording via asciinema (Ctrl-D to stop) …"
  asciinema rec "${VIDEO_DIR}/demo_3min.cast" -c "bash $0 --no-act"
  if command -v svg-term >/dev/null 2>&1; then
    svg-term --in "${VIDEO_DIR}/demo_3min.cast" \
             --out "${VIDEO_DIR}/demo_3min.gif" \
             --width 960 --height 540
    echo "GIF: ${VIDEO_DIR}/demo_3min.gif"
  fi
else
  echo "(asciinema not installed — printed demo script only)"
  echo "Install: brew install asciinema"
fi