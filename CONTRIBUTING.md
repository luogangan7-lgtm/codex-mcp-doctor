# Contributing

codex-mcp-doctor is a single-developer project built for OpenAI Build Week,
but bug reports, new detection classes, and example configs are welcome.

## The one hard rule: zero dependencies

`scripts/doctor.py` must run on Python 3.11+ stdlib alone. No `pip install`,
no `requirements.txt`, no vendored libraries. This is enforced two ways:

1. **AST gate** — `scripts/verify-zero-deps.py` scans every import in
   `doctor.py` and fails if any module is not in the Python stdlib. This
   runs in CI on every push, across Python 3.11 / 3.12 / 3.13 / 3.14.
2. **Fresh-clone test** — the release zip is unzipped into a clean
   directory and run with no virtualenv. If it needs anything beyond
   `python3`, the release fails.

This rule is load-bearing, not aesthetic: the doctor's job is to diagnose
broken MCP setups. A diagnostic that itself needs `pip install` would fail
on the exact machines that need it most.

`docs/generate-images.py` is the **only** file allowed to use a non-stdlib
import (PIL/Pillow) — it is a build-time asset generator, not runtime code.
If you touch the screenshots, regenerate them with
`python3 docs/generate-images.py` and commit the new PNGs.

## Adding a new detection class

Each detection class is one analyzer function plus one warning code.
Convention:

- **Warning code** — `W` + three digits (e.g. `W022` for the Cyrillic
  homoglyph class). Look at `doctor.py` for the existing range and pick
  the next free number. Error codes (`E0xx`) are for rug-pull / baseline
  drift.
- **Severity** — one of `low`, `medium`, `high`. Reserve `high` for
  "this is almost certainly an attack or a production-breaking bug."
- **Evidence + fix** — every finding must carry a concrete evidence
  string (the exact bytes that triggered it) and a one-line fix. A
  warning without a fix is a complaint, not a diagnosis.
- **Test** — add at least one positive and one negative case to
  `tests/test_doctor.py`. The suite is plain `unittest`, no pytest, no
  fixtures framework. Run with `python3 -m unittest tests.test_doctor`.
- **Example** — if the class is user-visible, add an example config under
  `examples/` with an `expected-output.txt` so CI can regression-check
  the rendered report.

## Adding an example

`examples/<name>/` needs at minimum:

- `config.toml` — the input config (can reference a `mock_server.py`)
- `expected-output.txt` — the doctor's rendered output, used by CI to
  catch silent format drift

If the example needs a live server (for probe-based checks), include a
`mock_server.py` that speaks enough of the MCP handshake to respond to
`tools/list`. See `examples/homoglyph-attack/mock_server.py` for the
pattern.

## CI gates (all must pass)

```
python3 -m unittest tests.test_doctor   # full suite, currently 294 tests
python3 scripts/verify-zero-deps.py       # AST scan — no non-stdlib imports
python3 scripts/doctor.py --config ...    # all 4 examples run without crashing
bash scripts/demo.sh --no-pause           # end-to-end demo smoke

# Doc integrity (run before tagging; these catch the drift classes that
# hand-edits historically missed):
python3 scripts/check-stale-refs.py       # version refs match current release
python3 scripts/check-metrics.py          # LOC + test-count claims match wc/unittest
```

CI runs these on Python 3.11, 3.12, 3.13, and 3.14. A change that passes
on 3.14 but breaks on 3.11 is a broken change.

## Versioning

`scripts/bump-version.py X.Y.Z` bumps the version in lockstep across
`doctor.py`, `plugin.json`, and `CHANGELOG.md`. Use it instead of editing
version strings by hand — manual edits drift.

- **Patch** (1.6.15 → 1.6.16) — bug fixes, doc updates, asset refresh
- **Minor** (1.6.x → 1.7.0) — new detection class or new flag
- **Major** (1.x → 2.0) — breaking change to output format or config schema

## Style

- `doctor.py` is one file, intentionally. It is easier to audit, easier
  to copy into a notebook, and easier for a judge to read top-to-bottom.
  Resist the urge to split it into a package unless there is a real
  reason.
- Em-dashes and curly quotes are fine in prose (README, CHANGELOG, this
  file) but avoid them in `doctor.py` string literals — some terminals
  render them oddly and it complicates test assertions.
- Comments explain *why*, not *what*. The code is the what.

## Reporting a bug that is not a security issue

Open a GitHub issue with:

1. `python3 scripts/doctor.py --version`
2. `python3 --version`
3. The `config.toml` (redact secrets) and the exact doctor output
4. What you expected vs. what you got

If the doctor itself crashed, that is always a bug — it is designed to
report problems, never to crash on them.
