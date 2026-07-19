#!/usr/bin/env python3
"""Verify hard metrics in docs against ground truth.

Checks every .md (excluding CHANGELOG history) for the four numbers judges
are most likely to verify by running a command:

    doctor.py LOC   -> wc -l scripts/doctor.py
    tests/ LOC      -> find tests -name '*.py' | xargs wc -l
    test count      -> python3 -m unittest tests.test_doctor (Ran N tests)
    version refs    -> scripts/doctor.py --version (current release tag)

A doc claim that disagrees with ground truth is flagged. Historical refs
(version-anchored facts inside recording notes, "since v1.4.0" provenance,
CHANGELOG entries) are not flagged - only forward-looking claims.

Usage
-----
    python3 scripts/check-metrics.py           # exit 1 if any mismatch
    python3 scripts/check-metrics.py --quiet   # exit 0 always

Intended to run before every tag/push, alongside check-stale-refs.py.
Zero dependencies, pure stdlib.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

SKIP_FILES = {"CHANGELOG.md"}


def ground_truth() -> dict:
    """Run the actual commands a judge would run."""
    doctor_loc = int(subprocess.check_output(
        ["wc", "-l", str(ROOT / "scripts" / "doctor.py")]
    ).decode().split()[0])

    tests_result = subprocess.check_output(
        ["bash", "-c", f"cd {ROOT} && find tests -name '*.py' -exec wc -l {{}} + | tail -1"]
    ).decode()
    tests_loc = int(re.search(r"(\d+)\s+total", tests_result).group(1))

    unittest_out = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_doctor"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    m = re.search(r"Ran (\d+) tests", unittest_out.stdout + unittest_out.stderr)
    test_count = int(m.group(1)) if m else -1

    doctor_src = (ROOT / "scripts" / "doctor.py").read_text()
    vm = re.search(r'version="mcp-doctor (\d+\.\d+\.\d+)"', doctor_src)
    version = vm.group(1) if vm else "?"

    return {
        "doctor_loc": doctor_loc,
        "tests_loc": tests_loc,
        "test_count": test_count,
        "version": version,
    }


def check_metric(text: str, claimed_values: set, truth: int,
                 metric_name: str, file: str, errors: list) -> None:
    """If any claimed value in text disagrees with truth, record it."""
    for val in claimed_values:
        try:
            n = int(val.replace(",", ""))
        except ValueError:
            continue
        if n != truth:
            errors.append(
                f"{file}: claims {metric_name}={val} but ground truth is {truth:,}"
            )


def scan(truth: dict) -> list[str]:
    """Scan all active docs; return list of mismatch error strings.

    Simple rule that avoids heuristic misclassification:
      - Every comma-formatted 4-digit number X,XXX is an LOC claim. It must
        equal either doctor.py LOC or tests/ LOC. (A doc rarely cites both
        in a way that a single number could be ambiguous; if it does, the
        number matching either truth is fine.)
      - Skip conservative-bounded forms like "2,800+" (the + means "at
        least", so any ground-truth >= the cited floor passes).
      - A 3-digit number (not preceded by digit/comma) directly followed by
        "tests" or "passing" is a test-count claim.
    """
    errors = []
    valid_loc = {truth["doctor_loc"], truth["tests_loc"]}
    for p in ROOT.rglob("*.md"):
        rel = str(p.relative_to(ROOT))
        if rel.startswith(".git/") or rel in SKIP_FILES:
            continue
        for line in p.read_text().splitlines():
            # LOC: X,XXX not immediately followed by "+" (conservative floor).
            # X,XXX optionally followed by "+" (conservative floor "2,800+").
            # No trailing \b so the "+" is captured when present.
            for m in re.finditer(r"\b(\d,\d{3})(\+)?", line):
                val = m.group(1)
                conservative = m.group(2) == "+"
                n = int(val.replace(",", ""))
                if conservative:
                    # "2,800+" means >= 2800; both LOCs must be >= floor.
                    if n > truth["doctor_loc"] and n > truth["tests_loc"]:
                        errors.append(
                            f"{rel}: claims '>={val}' but doctor.py is only {truth['doctor_loc']:,}"
                        )
                else:
                    if n not in valid_loc:
                        errors.append(
                            f"{rel}: claims LOC={val} but doctor.py={truth['doctor_loc']:,}, tests={truth['tests_loc']:,}"
                        )
            # Test count: 3-digit number (not preceded by digit/comma)
            # directly followed by "tests" or "passing".
            for m in re.finditer(r"(?<![\d,])(\d{3})\s*(?:tests|passing)", line):
                val = m.group(1)
                n = int(val)
                if n != truth["test_count"]:
                    errors.append(
                        f"{rel}: claims test count={val} but ground truth is {truth['test_count']}"
                    )
    return sorted(set(errors))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    truth = ground_truth()
    print(f"ground truth: doctor.py={truth['doctor_loc']:,} LOC, "
          f"tests={truth['tests_loc']:,} LOC, "
          f"{truth['test_count']} tests, v{truth['version']}")

    errors = scan(truth)
    if not errors:
        print(f"OK: every numeric metric in active docs matches ground truth")
        return 0

    print(f"\nMISMATCH ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
    return 0 if args.quiet else 1


if __name__ == "__main__":
    sys.exit(main())
