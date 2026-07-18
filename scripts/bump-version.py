#!/usr/bin/env python3
"""Bump all version strings in lockstep.

Usage: python3 scripts/bump-version.py 1.6.7

Updates every place a version number lives so they cannot drift apart:
  - scripts/doctor.py        (--version flag)
  - .codex-plugin/plugin.json (manifest version field)

Does NOT touch CHANGELOG.md (that carries historical versions and must be
hand-edited per release). Does NOT git commit or tag — caller does that.

Idempotent: if the version is already the target everywhere, exits 0.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def bump(target: str) -> None:
    # Validate semver-ish.
    if not re.fullmatch(r"\d+\.\d+\.\d+", target):
        sys.exit(f"not a valid x.y.z version: {target}")

    # 1. doctor.py --version
    doctor = ROOT / "scripts" / "doctor.py"
    text = doctor.read_text()
    new = re.sub(
        r'version="mcp-doctor \d+\.\d+\.\d+"',
        f'version="mcp-doctor {target}"',
        text,
    )
    if new == text:
        print(f"doctor.py: already at {target}")
    else:
        doctor.write_text(new)
        print(f"doctor.py: bumped to {target}")

    # 2. plugin.json version field
    plugin = ROOT / ".codex-plugin" / "plugin.json"
    data = json.loads(plugin.read_text())
    old = data.get("version")
    data["version"] = target
    plugin.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    if old == target:
        print(f"plugin.json: already at {target}")
    else:
        print(f"plugin.json: bumped {old} -> {target}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: bump-version.py <x.y.z>")
    bump(sys.argv[1])
