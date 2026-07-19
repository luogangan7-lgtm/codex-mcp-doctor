#!/usr/bin/env python3
"""Build a self-contained release zip for codex-mcp-doctor.

Produces codex-mcp-doctor-<version>-standalone.zip containing:
  doctor.py               - the single-file diagnostic tool
  examples/               - 4 example configs (broken-stdio, broken-http,
                            security-issues, homoglyph-attack)
  QUICKSTART.md           - one-page getting-started

Judges can download this zip, unzip, and run:
  python3 doctor.py --config examples/broken-stdio/config.toml

No git clone, no pip install, no virtualenv. Pure Python 3.11+ stdlib.

Usage:
  python3 scripts/build-release-zip.py [version]

If version is omitted, it is read from doctor.py's __version__ string.
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCTOR = os.path.join(ROOT, "scripts", "doctor.py")
EXAMPLES_DIR = os.path.join(ROOT, "examples")


def read_version():
    """Extract the tool version from doctor.py --version argparse string."""
    src = open(DOCTOR, encoding="utf-8").read()
    m = re.search(r'version="mcp-doctor\s+(\d+\.\d+\.\d+)"', src)
    if not m:
        raise SystemExit("could not find tool version string in doctor.py")
    return m.group(1)


def build_quickstart(version):
    return f"""# codex-mcp-doctor v{version} - Quick Start

`npm doctor` for MCP. Diagnose MCP server connectivity, configuration,
runtime health, tool schema quality, and multi-layer security - zero
dependencies, pure Python stdlib.

## Requirements

Python 3.11 or newer. That is all. No pip install, no virtualenv.

## Try it in 5 seconds

    python3 doctor.py --config examples/broken-stdio/config.toml

You will see a broken MCP server diagnosed in under a second - red error,
root cause, one-line fix.

## See the security layer

    python3 doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe

    python3 doctor.py --config examples/homoglyph-attack/config.toml

The homoglyph example shows the W022 Cyrillic attack - unique to
codex-mcp-doctor, no other MCP scanner detects it.

## Full source

This zip contains only the doctor and 4 example configs. The full source
(tests, hooks, CI, demo script, docs) is on GitHub:

  https://github.com/luogangan7-lgtm/codex-mcp-doctor

## Built with

Codex + GPT-5.6. The entire codebase was written, debugged, and hardened
inside Codex desktop.
"""


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else read_version()
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise SystemExit(f"invalid version: {version}")

    out_name = f"codex-mcp-doctor-{version}-standalone.zip"
    out_path = os.path.join(ROOT, "dist", out_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # doctor.py at zip root
        zf.write(DOCTOR, "doctor.py")
        # examples
        for name in sorted(os.listdir(EXAMPLES_DIR)):
            ex_path = os.path.join(EXAMPLES_DIR, name)
            if os.path.isdir(ex_path):
                for fname in sorted(os.listdir(ex_path)):
                    fpath = os.path.join(ex_path, fname)
                    if os.path.isfile(fpath):
                        arcname = os.path.join("examples", name, fname)
                        zf.write(fpath, arcname)
        # quickstart
        zf.writestr("QUICKSTART.md", build_quickstart(version))

    size_kb = os.path.getsize(out_path) // 1024
    print(f"Built {out_path} ({size_kb} KB)")
    # List contents
    with zipfile.ZipFile(out_path) as zf:
        print("Contents:")
        for info in zf.infolist():
            print(f"  {info.file_size:>8}  {info.filename}")


if __name__ == "__main__":
    main()
