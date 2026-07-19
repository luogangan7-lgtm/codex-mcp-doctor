#!/usr/bin/env sh
# Hook wrapper: find a Python >= 3.11 (with tomllib) and run doctor.
# macOS ships Python 3.9 at /usr/bin/python3 (no tomllib); Homebrew
# and python.org installs provide 3.11+. This wrapper probes candidates
# so the hook never silently fails on an older system Python.
#
# Codex injects PLUGIN_ROOT when the plugin is installed. If it's missing
# (e.g. manual test), fall back to the directory containing this script.
# Codex injects PLUGIN_ROOT when the plugin is installed. If it's missing
# (e.g. manual test), fall back to the plugin root (one level above this script).

SCRIPT_DIR=$(cd "$(dirname "$0")/.." && pwd) || exit 0
ROOT="${PLUGIN_ROOT:-$SCRIPT_DIR}"

# Candidates in priority order: version-specific names first, then generic.
for py in python3.14 python3.13 python3.12 python3.11 python3; do
    py_path=$(command -v "$py" 2>/dev/null) || continue
    if "$py_path" -c 'import sys, tomllib; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
        exec "$py_path" "$ROOT/scripts/doctor.py" --quiet --timeout 8
    fi
done

# No suitable Python found — fail silently (hook must not block session start).
exit 0
