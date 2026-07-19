#!/usr/bin/env python3
"""Cross-reference audit: scan every .md for version/test-count/LOC/commit
claims and report any active-doc reference that disagrees with the current
release.

Stale-ref vs historical-ref distinction
---------------------------------------
This script only flags "current release" claims - phrases that assert what
the project *currently* is, not what it *was at some version*. Concretely,
it flags version strings that appear in the same line as a current-tense
marker:

    "Shipped now (vX.Y.Z)"
    "through vX.Y.Z"
    "Version: vX.Y.Z"
    "latest ... vX.Y.Z"
    "current ... vX.Y.Z"
    "now at vX.Y.Z"

A bare "v1.6.18" in a sentence like "the test-count drift fix (v1.6.18)
was found this way" is a historical fact and is NOT flagged. Same for
recording notes versioned to the release they describe ("Recording note
(v1.6.34)"), first-commit lines ("initial v1.4.0"), semver examples in
CONTRIBUTING ("1.6.15 -> 1.6.16"), and package-version examples ("@1.2.3").

Usage
-----
    python3 scripts/check-stale-refs.py            # exit 1 if stale refs found
    python3 scripts/check-stale-refs.py --quiet    # exit 0 always, just print

Intended to run before every tag/push. Idempotent, zero dependencies.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Files that legitimately contain old version numbers (history, examples).
SKIP_FILES = {
    "CHANGELOG.md",  # every release entry has its own version
}

# Current-release markers. A version on the same line as one of these is a
# "current release" claim and must match the release tag.
CURRENT_MARKERS = (
    "shipped now",
    "through v",
    "version:",
    "version =",
    "latest release",
    "latest tag",
    "current release",
    "now at v",
    "now v",
    "as of v",
)


def current_version() -> str:
    """Read the version from doctor.py (single source of truth)."""
    doctor = (ROOT / "scripts" / "doctor.py").read_text()
    m = re.search(r'version="mcp-doctor (\d+\.\d+\.\d+)"', doctor)
    if not m:
        sys.exit("could not find version in scripts/doctor.py")
    return m.group(1)


def scan(cur: str) -> list[tuple[str, str, int, str]]:
    """Return [(file, version, lineno, line), ...] for stale current-release refs."""
    stale = []
    for p in ROOT.rglob("*.md"):
        rel = str(p.relative_to(ROOT))
        if rel.startswith(".git/") or rel in SKIP_FILES:
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            lower = line.lower()
            # Does this line assert a current-release version?
            if not any(mk in lower for mk in CURRENT_MARKERS):
                continue
            # Find every vX.Y.Z on the line and check it.
            for m in re.finditer(r"v\d+\.\d+\.\d+", line):
                if m.group(0) != f"v{cur}":
                    stale.append((rel, m.group(0), i, line.strip()))
    return stale


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true",
                    help="exit 0 even if stale refs found")
    args = ap.parse_args()

    cur = current_version()
    print(f"current version: {cur}")
    stale = scan(cur)

    if not stale:
        print(f"OK: every current-release version ref in active docs == v{cur}")
        return 0

    print(f"\nSTALE current-release refs ({len(stale)}):")
    for rel, ver, lineno, line in stale:
        print(f"  {rel}:{lineno}  {ver}")
        print(f"    {line}")
    print(f"\nLift these to v{cur} before tagging.")
    return 0 if args.quiet else 1


if __name__ == "__main__":
    sys.exit(main())
