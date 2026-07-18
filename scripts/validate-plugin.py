#!/usr/bin/env python3
"""Validate .codex-plugin/plugin.json as a Codex plugin manifest.

CI gate for the plugin manifest. Runs on every push alongside the
zero-dependency AST scan. Fails CI if:
  - plugin.json is missing or not valid JSON
  - required keys are absent (id, name, version, description)
  - version is not a semver string

This catches a broken manifest before it reaches a judge who tries to
install the plugin.

Usage: python3 scripts/validate-plugin.py [path/to/plugin.json]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT = ROOT / ".codex-plugin" / "plugin.json"

# Codex plugin manifests do NOT require an id field: identity is the name.
# Verified against notion/github/latex/sites official plugins (none have id).
REQUIRED_KEYS = ["name", "version", "description"]


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"FAIL: plugin manifest not found at {path}", file=sys.stderr)
        return 1

    try:
        with open(path) as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FAIL: {path} is not valid JSON: {e}", file=sys.stderr)
        return 1

    missing = [k for k in REQUIRED_KEYS if k not in manifest]
    if missing:
        print(f"FAIL: {path} missing required keys: {missing}", file=sys.stderr)
        return 1

    version = manifest.get("version", "")
    if not isinstance(version, str) or not version[0].isdigit():
        print(
            f"FAIL: version must be a semver string starting with a digit, "
            f"got: {version!r}",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: {path} is a valid plugin manifest "
        f"({manifest['name']} v{manifest['version']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
