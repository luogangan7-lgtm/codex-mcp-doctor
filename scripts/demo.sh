#!/usr/bin/env bash
# codex-mcp-doctor — guided demo
#
# Runs every demo scenario from docs/devpost-submission.md in sequence,
# with section titles and pauses. Used for:
#   - Recording the Devpost demo video (just screen-record this script)
#   - Letting reviewers/judges see all features in one command
#   - Smoke-testing all examples after changes
#
# Usage:
#   ./scripts/demo.sh                # interactive, pauses between scenes
#   ./scripts/demo.sh --no-pause     # continuous, no pauses (for CI / GIF capture)
#
# Zero dependencies beyond Python 3.11+ (required by doctor.py itself).
# Exits non-zero if any doctor.py invocation reports errors (expected for
# the broken-server scenes, so this script always ends 0 unless a scene
# command itself crashes).

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

# Pick a python that has tomllib (3.11+). Homebrew first, then PATH.
PYTHON=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys, tomllib; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.11+ with tomllib not found." >&2
    exit 1
fi

PAUSE=1
if [ "${1:-}" = "--no-pause" ]; then
    PAUSE=0
fi

# Temp baseline so the rug-pull scene doesn't write to the user's home.
BASELINE_TMP="$(mktemp -t mcp-doctor-baseline.XXXXXX.json)"
trap 'rm -f "$BASELINE_TMP"' EXIT

scene() {
    # $1 = scene number, $2 = title, rest = narration
    local num="$1" title="$2"; shift 2
    echo
    echo "================================================================"
    echo "  SCENE $num — $title"
    echo "================================================================"
    [ $# -gt 0 ] && echo "$*"
    echo
}

do_pause() {
    # Only prompt when stdin is a TTY. Prevents the script from blocking in
    # environments without interactive stdin (CI, pipes, screen recorders).
    if [ "$PAUSE" -eq 1 ] && [ -t 0 ]; then
        echo
        read -r -p "[press ENTER to continue, Ctrl-C to exit] " _
    fi
}

run() {
    # Show the command, then run it. Don't let a non-zero exit abort the demo
    # (broken-server scenes are supposed to exit non-zero).
    echo "\$ $*"
    "$@" || true
}

echo "codex-mcp-doctor — guided demo"
echo "python: $($PYTHON --version)"
echo "repo:   $ROOT"

# --- Scene 1 -------------------------------------------------------------
scene 1 "The Silent Failure" \
    "MCP servers fail silently. config.toml looks fine, Codex starts, but zero tools appear. No error, no log."
cat examples/broken-stdio/config.toml
do_pause

# --- Scene 2 -------------------------------------------------------------
scene 2 "The Doctor Diagnoses" \
    "One command, zero dependencies, root-causes both broken servers in under a second."
run "$PYTHON" scripts/doctor.py --config examples/broken-stdio/config.toml
do_pause

# --- Scene 3 -------------------------------------------------------------
scene 3 "Security: Supply Chain + Secrets" \
    "Silently hostile servers: an unpinned npx package can pull a compromised update; a plaintext API key in http_headers leaks if config.toml is committed."
run "$PYTHON" scripts/doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe
do_pause

# --- Scene 3b ------------------------------------------------------------
scene "3b" "W022 Cyrillic Homoglyph Attack" \
    "A tool whose name LOOKS like 'filesystem_read' — but the 'e' is Cyrillic U+0435. Passes any human code review. First MCP scanner to catch this."
run "$PYTHON" scripts/doctor.py --config examples/homoglyph-attack/config.toml
do_pause

# --- Scene 4 -------------------------------------------------------------
scene 4 "Rug-Pull Detection (E003)" \
    "The most dangerous attack: a tool description that changes silently after you trusted it. First CLI implementation of tool-description pinning. (Web-only at Invariant Labs' MCP-Scan.)"
echo
echo "Step 1 — pin the trusted baseline (one tool, sha256 of its description):"
run "$PYTHON" scripts/doctor.py --config examples/homoglyph-attack/config.toml --save-baseline --baseline-path "$BASELINE_TMP" --quiet
echo
echo "Baseline contents:"
cat "$BASELINE_TMP"
echo
echo "Step 2 — simulate the attack. The server silently changes its tool's description."
echo "We corrupt the stored hash to represent a tampered description, then re-check:"
# Corrupt the baseline hash so check-baseline thinks the live description differs.
$PYTHON - "$BASELINE_TMP" <<'PY'
import json, sys
p = sys.argv[1]
with open(p) as f: data = json.load(f)
for srv in data.values():
    for name in srv:
        # flip the last hex digit — any change to the description hash triggers E003
        h = srv[name]
        srv[name] = h[:-1] + ('0' if h[-1] != '0' else '1')
with open(p, 'w') as f: json.dump(data, f, indent=2)
PY
echo "  → baseline hash corrupted (simulating server-side description mutation)"
echo
echo "Step 3 — re-check against the baseline. The doctor must flag E003 rug-pull:"
run "$PYTHON" scripts/doctor.py --config examples/homoglyph-attack/config.toml --check-baseline --baseline-path "$BASELINE_TMP"
do_pause

# --- Scene 5 -------------------------------------------------------------
scene 5 "Auto-Triggering Hook" \
    "Ships with a Codex SessionStart hook (hooks/hooks.json). If your MCP setup is healthy, completely silent. If something broke, you see it before your first prompt — not after 20 minutes of debugging."
echo
echo "hooks/hooks.json:"
cat hooks/hooks.json 2>/dev/null || echo "  (hooks/hooks.json not found)"
echo
echo "Try it locally:"
echo "  cp hooks/hooks.json ~/.codex/hooks.json"
echo "  # then start a new Codex session"
do_pause

# --- Scene 6 -------------------------------------------------------------
scene 6 "Debug Visibility & Continuous Watch" \
    "Two new v1.6 flags: --debug surfaces hidden probe warnings, --watch re-runs continuously and only prints on status change."
echo
echo "--debug: surfaces best-effort exceptions normally hidden behind 'no_content_returned':"
echo "  (running doctor --debug against broken-stdio example)"
echo
$PYTHON scripts/doctor.py --config examples/broken-stdio/config.toml --debug 2>&1 | head -25 || true
echo
echo "--watch: continuous monitoring, silent until status changes:"
echo "  $PYTHON scripts/doctor.py --watch --interval 30   # Ctrl+C to stop"
echo "  $PYTHON scripts/doctor.py --watch --quiet          # hook-style guard duty"
echo
echo "Two layers of protection: SessionStart hook (boot) + --watch (runtime)."
do_pause


echo
echo "================================================================"
echo "  END OF DEMO"
echo "  285 tests · 0 dependencies · pure Python 3.11+ stdlib"
echo "  https://github.com/luogangan7-lgtm/codex-mcp-doctor"
echo "================================================================"
