# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.6.32] - 2026-07-19

### Fixed

- **CI workflow now uses the same test invocation every doc uses.** `.github/workflows/test.yml` ran the suite via `python3 tests/test_doctor.py` (direct file execution), while every piece of documentation — README, CONTRIBUTING, form-guide, recording-checklist — had been corrected in v1.6.25/v1.6.28/v1.6.31 to use `python3 -m unittest tests.test_doctor`. The direct invocation only works because `tests/test_doctor.py` happens to have an `if __name__ == "__main__": unittest.main()` block; if that block were ever refactored away, CI would silently break while every doc still claimed the module form was the right way to run tests. CI now uses `python3 -m unittest tests.test_doctor`, matching the docs and removing the fragile dependency on the `__main__` block. Verified locally: same 294 tests pass, same exit code 0.
## [1.6.31] - 2026-07-19

### Fixed

- **CONTRIBUTING.md no longer instructs the wrong test invocation or a stale count.** Two places in CONTRIBUTING.md still said `python3 tests/test_doctor.py` (the same direct-file invocation root cause fixed in v1.6.25 and v1.6.28) and the CI-gates block claimed "currently 285 tests" (actual: 294). A contributor or curious judge copy-pasting from CONTRIBUTING would hit the same trap. Both corrected to `python3 -m unittest tests.test_doctor` and "currently 294 tests". This is the last file in the repo that still carried the wrong invocation — the codebase is now internally consistent.

### Audited (no change needed)

- **SECURITY.md** — threat model, scope, disclosure policy all accurate; no hardcoded numeric claims to drift.
- **scripts/refresh-transcript.sh** — path normalization and latency stripping are correct and consistent with demo-transcript.txt's role as a portable preview.
## [1.6.30] - 2026-07-19

### Fixed

- **Example expected-output files now match what the doctor actually prints.** Running each example command and diffing against its `expected-output.txt` surfaced three classes of drift that a judge running the README's "Try it in 5 seconds" hook would catch immediately:
  - **Latency values were stripped instead of placeheld.** `broken-http/expected-output.txt` stripped all `(Xms)` latency values entirely, while the real output shows them. `broken-stdio` and `homoglyph-attack` simply omitted the latency on lines where the real run includes one. Per the convention documented in `examples/README.md` ("Values marked `<latency>` vary by machine"), all latency-bearing tool-count lines now read `0 tools (<latency>)` / `2 tools (<latency>)`, so a judge can match the structure without being fooled by a non-deterministic number.
  - **homoglyph-attack expected-output had the wrong indentation throughout.** Every line under the server header was indented 2 spaces, but the doctor prints them at 5-space (server-block) indentation. A character-level diff failed on every line. Regenerated from a real run.
  - **broken-http trailing note rewritten.** The old note said latency values are "stripped here"; the new note explains they are shown as `(<latency>)` placeholders because they vary by run and machine.
- **hook.sh comment corrected.** The comment said PLUGIN_ROOT "falls back to the directory containing this script"; it actually falls back to the plugin root (one level above the script, via the `cd $(dirname $0)/..` in SCRIPT_DIR). One-line comment fix, no behavior change.
## [1.6.29] - 2026-07-19

### Fixed

- **Voiceover Scene 3 no longer overclaims what the screen shows.** The narration said "the security layer catches seven classes of attack — prompt injection, tool shadowing, hidden Unicode, Cyrillic homoglyphs, supply-chain tampering, plaintext secrets, baseline drift" — but the on-screen command (`--check secrets --skip-probe`) only surfaces two of them (unpinned package + plaintext secret). A judge counting alerts on screen would think five were missing. Trimmed to "catches seven classes of attack. Two of them fire here —", which is exactly what the screen then shows. The seven-class capability claim is preserved elsewhere (README, submission metrics).
- **Voiceover recording note for Scenes 3b+4 corrected.** The note claimed `homoglyph-attack` "runs once and both W022 and E003 light up together". That is factually wrong: the homoglyph run only fires W022; the three E003 tiers require Scene 4's separate save-baseline → mutate → re-check sequence. A recorder following the old note would wait for E003 in Scene 3b and think the demo was broken. Rewritten to describe the actual three-step Scene 4 flow and explicitly call out that the `homoglyph-attack` command intentionally appears twice (once in 3b, once as Scene 4 step 1).
## [1.6.28] - 2026-07-19

### Fixed

- **Judge-facing docs no longer instruct `python3 tests/test_doctor.py`.** Three places (README Testing section, README judge-verification block, docs/devpost-form-guide.md step 1) told judges to run the test file directly. That invocation only works when the file's `__main__` block happens to call `unittest.main()`; on machines where it doesn't (or for anyone copy-pasting into a different layout) the output is the doctor CLI's `No servers to check`, not the test result line - the exact failure mode v1.6.25 fixed in the recording checklist. All three now use `python3 -m unittest tests.test_doctor`, the invocation CI and every other doc uses.
- **Stale line-count metrics in devpost-submission.md corrected to ground truth.** The metrics table and tech-stack row reported doctor.py as 2,868 lines and tests as 2,629 lines, but the actual counts (after v1.6.26/v1.6.27) are 2,888 and 2,674. A judge running `wc -l` would see a mismatch. Both updated; the 2,674 figure now matches the tech-stack row that was already correct.
- **Scene 2.5 narration in devpost-submission.md synced to the voiceover.** The submission doc's Scene 2.5 still read `Two hundred ninety tests` while the voiceover script (the source of truth for what gets spoken) was updated to `Two hundred ninety-four` in v1.6.27. A judge reading the submission alongside the video would catch the drift. Now aligned.
## [1.6.27] - 2026-07-19

### Added

- **TestNormalizeStderr: 7 new tests covering _normalize_stderr (introduced in v1.6.26).** The v1.6.26 root-cause fix added _normalize_stderr to collapse machine-specific interpreter paths in captured stderr, but shipped without dedicated tests - the function was only exercised indirectly through the broken-stdio demo. These 7 tests cover the three real-world path shapes (Homebrew Apple-Silicon, Linux /usr/bin, pyenv), the empty-string and None defensive paths, a no-python-path passthrough, and a multiline stderr case to confirm only the interpreter prefix is collapsed. Test count: 287 -> 294.

### Fixed

- **Test-count drift同步: 287 -> 294 across all judge-facing docs.** The v1.6.18 anti-drift convention (use ~290 as an approximation in prose, exact numbers only where a count is the point) held - the ~290 references in README and submission needed no change. But the exact '287' in devpost-submission (5 places: metrics block, dogfooding narrative, checklist, tech-stack table, metrics table), devpost-form-guide (2 places), demo-recording-checklist, and the voiceover script (English words 'Two hundred eighty-seven' in Scene 2.5 and Scene 5) all updated to 294. demo.sh needs no change - it uses dynamic AST count (v1.6.21+ anti-drift mechanism). demo-transcript.txt regenerated from a fresh run, now shows '294 tests'.

## [1.6.26] - 2026-07-19

### Fixed

- **Captured stderr is now machine-path-normalized.** When a stdio server crashes, Python writes its absolute interpreter path into the traceback (e.g. '/opt/homebrew/opt/python@3.14/bin/python3.14: No module named X'). That path is noise for the user and made captured stderr non-deterministic across machines - the same broken-stdio example produced different output on Apple-Silicon-Homebrew vs Linux vs pyenv. Added `_normalize_stderr()` which collapses any leading '/.../python3.x:' prefix to 'python3:', preserving the useful part of the message (the module name, the error class) while making output reproducible. Applied at all three stderr capture sites in doctor.py.
- **expected-output.txt and demo-transcript.txt now match real demo output character-for-character on the stderr line.** Previously expected-output.txt hardcoded '/opt/homebrew/opt/python@3.14/bin/python3.14' (a dev-machine path), so any judge comparing their own run to the expected file would see a diff on that line and suspect a bug. Regenerated both files from a fresh demo run with normalization in place.
- Verified the standalone QUICKSTART.md (the only doc inside the release zip) by extracting the zip to a clean temp dir and running all three commands it teaches - all produce the promised output.

## [1.6.25] - 2026-07-19

### Fixed

- **Recording checklist sanity-check #1 ran the wrong command.** The pre-recording checklist told the user to run `python3 tests/test_doctor.py | tail -3` expecting "Ran 287 tests ... OK". But running the test file directly invokes the doctor CLI entry point (its `if __name__ == "__main__"` block), so the actual output is "No servers to check" - not the test result line. A user following the checklist would think the test suite was broken. Switched to `python3 -m unittest tests.test_doctor`, which is the invocation CI and every other doc uses.
- **Recording checklist leaked the dev machine's Python path.** Sanity-check #4 expected `/opt/homebrew/bin/python3` - a Homebrew-on-Apple-Silicon path that is not true on Linux, Intel Macs, or pyenv setups. Replaced with a version-only check (`python3 --version` expects 3.11+) plus guidance for users whose default python3 is the macOS system 3.9.
- Also tightened sanity-check #2 expected output to match what `validate-plugin.py` actually prints today.

## [1.6.24] - 2026-07-19

### Fixed

- **Submission provenance block updated for accuracy and leak safety.** The "Project Provenance (Submission Period Compliance)" section cited the first commit by its raw hash (48f751c) - the same commit that triggered a GitGuardian secret incident. A judge clicking through could land on the leaked-token diff. Replaced the hash with a date + "Build Week Day 1 of coding" framing. Also bumped three stale facts: "100+ commits" to the actual 118, "through v1.6.21" to v1.6.23, and added /releases as a second evidence link. Separately, "Shipped now (v1.6.21)" in the roadmap section was bumped to v1.6.23. Verified against live Devpost rules: tracks (Developer Tools confirmed), 3-minute video, /feedback Session ID, July 21 5PM PT deadline, and the Dev Tools-specific rule requiring install instructions + supported platforms + judge test path - all already covered in the submission.

## [1.6.23] - 2026-07-19

### Fixed

- **SKILL.md security table now includes W022 (Cyrillic homoglyph).** The table listed E001/E002/W001/W021/W015/W017/W019 but omitted W022, while the frontmatter description, README, Devpost submission, voiceover, and cover image all treat W022 as the headline differentiator. A judge who installed the plugin and read SKILL.md would see seven codes but no W022, then see W022 everywhere else - a documentation-vs-documentation inconsistency in the same family as the v1.6.20 voiceover/output drift. Added the W022 row (high severity, cyrillic-homoglyph label, normalize-to-ASCII fix) to the security table and a dedicated trigger condition to the "When to Run" list.

## [1.6.22] - 2026-07-19

### Fixed

- **Rug-pull demo now triggers all three E003 tiers as documented.** The Scene 4 baseline mutation script claimed to trigger high (changed), medium (new), and low (removed) tiers, but only actually triggered high and low. Root cause: the mock server returned only one tool, so there was no second tool to drop from the baseline for the medium tier. Added a second tool ('safe_config_write') to the mock server and rewrote the mutation logic to flip the first tool's hash (high), drop the second from the baseline (medium), and inject a ghost (low). The voiceover script's 'Three E003 tiers fire at once' claim is now accurate.

### Added

- **CI plugin manifest validation gate.** New `scripts/validate-plugin.py` wired into `.github/workflows/test.yml` across Python 3.11-3.14. Catches a broken manifest before it reaches a judge. Required keys enforced: name/version/description (NOT `id` - verified against official notion/github/latex/sites plugins, none of which have an `id` field; Codex plugin identity is the `name`).

### Fixed

- **demo.sh test-count drift.** The end-of-demo banner was hardcoded at "285 tests" while the actual suite grew to 287 - the same drift class v1.6.18 fixed in docs but missed in demo.sh. Replaced with a static AST count of `test_` methods (~0ms, exact match to unittest output because this suite has no subTest or parametrization). The banner now tracks the suite automatically and can never drift again.

- **Voiceover Scene 2.5 test count.** Said "Two hundred ninety tests" while Scene 5 already said "Two hundred eighty-seven" - same script, two different numbers. Aligned to 287.

- **Voiceover Scene 4 E003 tier count.** Said "Two E003 tiers fire at once" but demo.sh explicitly triggers all three (high=changed, medium=new, low=removed). Fixed to match the actual three-tier output.

- **Submission security-class claim precision.** "7 security check classes" was technically imprecise - a judge counting SKILL.md table rows finds 11 security codes. Refined to "7 attack-vector detection classes" (named with codes E001/E002/W021/W022/E003/supply-chain/secrets) plus explicit "capability-risk signals" for the W0xx series (W001/W015/W017/W019).

- **Stale version anchors in docs.** submission.md "through v1.6.18" and "Shipped now (v1.6.14)" updated to v1.6.21. form-guide "As of this writing: v1.6.19" replaced with version-agnostic instruction.

- **Validator path in pre-flight checklist.** form-guide and recording-checklist referenced the global `~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py`; changed to the repo's own `scripts/validate-plugin.py` (self-contained, same one CI runs, works on a judge's fresh clone).

## [1.6.21] - 2026-07-19

### Fixed

- **Local path leakage in docs.** Three docs (form-guide, recording checklist, submission) hardcoded the developer local path (`/Volumes/data/codex-mcp-doctor`), visible to judges reading the repo. Replaced with relative paths.

- **SKILL.md frontmatter missing the unique differentiator.** The description listed security checks but omitted "Cyrillic homoglyph attacks" - the one detection no other MCP scanner has and the keyword that should trigger the skill. Added.

- **Voiceover Scene 4 overrun.** The [2:23] block was 70 words needing 30s in a 19s window. Trimmed to 39 words (kept the two-tier structure + first-CLI claim; cut the redundant W022 callback Scene 3b already covers). Corrected the pacing assumption from ~140 wpm to ~150 wpm; total VO is now 423 words = 2:49, leaving 11s headroom under 3:00.

- **doctor.py --version 1.6.20 -> 1.6.21.


## [1.6.20] - 2026-07-19

### Fixed

- **Devpost gallery thumbnail image ratio: 5:3 -> 3:2.** All four PIL-rendered images (devpost-cover, w022-homoglyph, screenshot-real-report, screenshot-rugpull-detection) were 1500x900 (5:3), based on a wrong assumption that Devpost gallery thumbnails center-crop to 1:1. Devpost help.devpost.com/article/126 states Project Gallery thumbnails should use a 3:2 ratio. Re-rendered all four at 1500x1000 (3:2). Layout kept horizontally centered (thumbnail crop only affects x-axis); all top-level y anchors shifted +50px to re-center content vertically in the taller canvas. 17/17 signature colors verified present.

- **Voiceover script factual drift (3 errors).** Scene 5 closing line said "Two eighty-five tests" (actual: 287). Scene 3 listed "seven classes" but named only 5, with names that did not match README canonical wording. Scene 3 secret demo described a "plaintext API key in an environment variable" but the actual security-issues example output is an unpinned npx package + hardcoded bearer token in http_headers. All three corrected to match actual code output.

- **Submission text factual claims (3 errors).** Tagline attributed "no other scanner detects" to rug-pulls (Invariant Labs MCP-Scan has web-only rug-pull detection); the unique claim belongs to Cyrillic homoglyphs. Scene 3 description said "API key" instead of "bearer token". Key Metrics table said 8 security check types; README canonical list is 7. All three aligned with README wording so README, voiceover, and submission now agree.

- **Form-guide stale version reference** (v1.6.13 -> v1.6.19/1.6.20).

- **doctor.py --version 1.6.19 -> 1.6.20.


## [1.6.19] - 2026-07-19

### Added

- **Devpost rules compliance audit.** Read the live /rules page (not cached memory) and found three hard requirements the submission did not yet satisfy:

- **Judging Criteria Mapping** (new section in devpost-submission.md). Devpost scores on four equally weighted criteria (Technological Implementation, Design, Potential Impact, Quality of the Idea). The submission now explicitly maps each criterion to where it is evidenced in the project, so judges scoring against the rubric find the evidence without hunting.

- **Project Provenance** (new section in devpost-submission.md). Rules require pre-existing projects to document prior-vs-new work with timestamped evidence. codex-mcp-doctor is 100% new work in the submission window (first commit 2026-07-18, zero commits before July 13), but this was not stated. Now explicitly declared with commit-count evidence (100+ commits, 0 before window).

- **How Codex Contributed** (new section in README.md). Rules require the README to describe Codex collaboration with specific product, engineering, and design decisions, not just "we used Codex." Added concrete decisions: zero-dependency-as-constraint rationale, plugin-over-CLI choice, severity tiers, W022 homoglyph detection origin, plus where GPT-5.6 specifically contributed (long-context review, cross-session memory continuity).

- **Codex Session ID field** documented in devpost-form-guide.md as section 12. Rules require providing the /feedback Session ID for the thread where core functionality was built. This is a user-only action (LLM cannot run /feedback); flagged in the form guide and canvas.

- **doctor.py --version 1.6.18 -> 1.6.19.

### Fixed

- **Documentation test-count drift: README, Devpost submission, form guide, recording checklist, and generated images all still cited 285 tests after v1.6.17 added two regression tests (actual: 287).** A judge reading the README and then running the suite would see inconsistent numbers. Fixed by updating the Key Metrics table to exact values (287 tests / 2,868 lines doctor.py / 2,629 lines tests) and switching narrative paragraphs to a stable approximation (~290 tests, ~2,900 lines, ~2,600 lines) so future test additions no longer require editing nine locations. The cover image was re-rendered so the on-image label matches the new count.

- **doctor.py --version 1.6.17 -> 1.6.18.

### Fixed

- **Rerun hint assumed the clone layout; standalone-zip users got a broken command.** When a server had errors, the human report ended with "Fix the errors above, then re-run: python3 scripts/doctor.py". That path is correct for a git clone, but the standalone release zip ships doctor.py at the repo root (no scripts/ prefix). A judge who downloaded the zip, ran the doctor, saw the hint, and copy-pasted it would get "No such file or directory". Fixed by reading sys.argv[0] so the hint reflects the actual invocation - "python3 scripts/doctor.py" for clone users, "python3 doctor.py" for standalone-zip users. Falls back to "doctor.py" if argv is empty.

### Added

- **Two regression tests covering the rerun-hint path.** test_rerun_hint_uses_argv0 verifies the clone scenario; test_rerun_hint_fallback_when_argv_empty verifies the empty-argv fallback. Brings the suite to 287 tests.

- **doctor.py --version 1.6.16 -> 1.6.17.**

## [1.6.16] - 2026-07-19

### Fixed

- **Screenshot assets drift: assets/*.png no longer matches docs/*.png.** The PIL-rendered screenshots in docs/ (from v1.6.10) are the canonical versions used by README, devpost-submission.md, and devpost-form-guide.md. But assets/screenshot-real-report.png and assets/screenshot-rugpull-detection.png were still the older hand-drawn v1.4.0 versions (different MD5, different byte size) because plugin.json references assets/ and nobody had refreshed them after the PIL migration. A judge cloning the repo would see two different-looking screenshots for the same logical image. Fixed by regenerating all four docs/*.png via docs/generate-images.py and copying screenshot-real-report.png + screenshot-rugpull-detection.png into assets/. Both locations now hash identical.

### Added

- **SECURITY.md.** A security tool without a security policy defeats its own purpose. The policy covers the private-advisory reporting flow, the explicit threat model (config is trusted, probe responses are untrusted, baseline is a trust anchor), what is in scope vs out of scope (the MCP protocol itself is out; detection-logic false negatives are in), and an honest list of what the doctor does NOT do (it does not block attacks, does not scan the network path, does not verify server binaries match their claimed source).

- **CONTRIBUTING.md.** Documents the zero-dependency rule and how it is enforced (AST gate + fresh-clone test), the convention for adding a new detection class (W-code + severity + evidence + fix + test + example), the CI gates across Python 3.11/3.12/3.13/3.14, and the bump-version.py lockstep workflow. README now links to both CONTRIBUTING.md and SECURITY.md.

- **doctor.py --version 1.6.15 -> 1.6.16.**

## [1.6.15] - 2026-07-19

### Changed

- **What's Next section rewritten from 2 vague bullets to a 3-tier roadmap.** The previous version ("semantic poisoning detection" + "marketplace publication") read as an afterthought. The rewrite has three layers: (1) Shipped now - the full list of 8 security classes and all monitoring modes, so judges see current depth; (2) Next 30 days - two concrete directions each with a technical explanation of the gap between current and next; (3) Longer horizon - baseline sharing registry and cross-agent monitoring, showing the pattern generalizes beyond MCP. This directly serves the Potential Impact dimension by signaling the project has a real product trajectory, not just a hackathon one-off.

- **doctor.py --version 1.6.14 -> 1.6.15.**


## [1.6.14] - 2026-07-19

### Fixed

- **form-guide Source Code pin was stale (v1.6.0).** The form-guide told the submitter to pin the repo URL to the v1.6.0 release tag for judge reproducibility. That tag is 13 versions behind. Changed to point at /releases/latest with a note to verify the tag at submission time.

- **form-guide Try It Out field said leave blank.** Now that each release ships a standalone zip, the Try It Out field is a second conversion point, not a dead field. Updated guidance to paste the latest release URL so judges who click get a one-download try.

- **Both checklists (form-guide + submission.md) updated.** form-guide release ref changed from v1.6.8 to /releases/latest. submission.md checklist gained Plugin manifest line, Cover/W022 image line, and Standalone zip line that were missing.

- **doctor.py --version 1.6.13 -> 1.6.14.**


## [1.6.13] - 2026-07-19

### Fixed

- **Short Description was 303 chars, over Devpost 280 limit.** The Devpost card Short Description field has a hard ~280 character limit. The previous version was 303 chars and would force a truncation or rewrite at submission time. Rewrote to 273 chars with a stronger hook: opens with the pain point ("MCP servers fail silently"), asserts the ambition ("the diagnostic CLI Codex should ship with"), lists the four most visual detections (broken servers, prompt injection, Cyrillic homoglyph, rug-pulls), claims differentiation ("that no other MCP scanner detects"), and closes with dogfooding ("Built in Codex with GPT-5.6").

- **Project Title had backticks that Devpost would render as literal characters.** Devpost title is a plain-text field; backticks do not render as code formatting and would show as raw punctuation. Cleaned to a plain hyphenated title.

- **form-guide tagline section now offers both the 273-char card description and a 48-char one-line tagline**, so the submitter has the right length for whichever Devpost field they are filling.

- **doctor.py --version 1.6.12 -> 1.6.13.**


## [1.6.12] - 2026-07-19

### Changed

- **README now offers a no-clone path.** The "Try it in 5 seconds" section previously only showed the git clone route. Added a "No git?" alternative pointing to the latest release standalone zip, so judges who do not want to clone can still try the tool in one download. This raises the try-it rate for the exact audience (busy hackathon judges) most likely to skip if the first option looks like work.

- **doctor.py --version 1.6.11 -> 1.6.12.**


## [1.6.11] - 2026-07-19

### Added

- **`scripts/build-release-zip.py`** — builds a self-contained release zip (`codex-mcp-doctor-<version>-standalone.zip`) containing `doctor.py`, all 4 example configs, and a one-page `QUICKSTART.md`. Judges can download the zip from the GitHub Release page, unzip, and run `python3 doctor.py --config examples/broken-stdio/config.toml` with no git clone and no pip install. This directly serves the zero-dependency narrative: the release artifact itself proves you can run the tool without any install step. Read version automatically from `doctor.py`'s argparse `--version` string (matching the exact `mcp-doctor X.Y.Z` format to avoid grabbing the MCP clientInfo version).

- **v1.6.10 GitHub Release now has 5 downloadable assets** — the standalone zip plus all 4 Devpost images (`devpost-cover.png`, `w022-homoglyph.png`, `screenshot-real-report.png`, `screenshot-rugpull-detection.png`). Previously the release had zero attached assets, forcing judges to browse the repo tree to find the images.

### Verified

- Standalone zip extracted to `/tmp/mcp-doctor-release-test`; all 3 runnable examples (`broken-stdio`, `security-issues --check secrets --skip-probe`, `homoglyph-attack`) executed successfully with zero install.

- **doctor.py --version 1.6.10 -> 1.6.11.**


## [1.6.10] - 2026-07-19

### Changed

- **Two Devpost screenshots converted from manual captures to deterministic rendered assets.** `screenshot-real-report.png` and `screenshot-rugpull-detection.png` were previously manual terminal screenshots captured on 2026-07-18, which became stale after five subsequent doctor.py commits (version strings changed four times). Replaced with PIL-rendered images generated by `docs/generate-images.py`, the same build-time tool that produces the cover and W022 images. All four Devpost images are now deterministic and regenerate from a single command, so they never drift from the current codebase. Both new images render the actual doctor.py output format: `screenshot-real-report.png` shows a mixed-health 3-server report (1 healthy, 1 broken command_not_found, 1 plaintext-secret warning), `screenshot-rugpull-detection.png` shows the E003 flagship (2 HIGH + 1 LOW from baseline check, plus the W022 carryover).

- **Verified all 4 images survive Devpost 1:1 thumbnail center crop.** Sampled brightness in the crop-removed x-zones [0,300] and [1200,1500]; all four images have <70 brightness in those margins (pure background), confirming no key content clips when Devpost generates the gallery thumbnail.

- **Generation is deterministic.** Two consecutive `generate-images.py` runs produce byte-identical PNGs (MD5 match), so the images do not create noise in version control.

- **doctor.py --version 1.6.9 -> 1.6.10.**


## [1.6.9] - 2026-07-19

### Changed

- **Scene 2.5 voiceover rewritten for recordability.** The original Scene 2.5 narration was a single 60+ word compound sentence crammed into 12 seconds, guaranteeing a stumble on take. Split into three short sentences (6/8/13 words) with distinct breath points. Replaced the vague "show a Codex session" action with a concrete prep checklist: second Codex window, pre-typed prompt, git log panel, secrets-redaction warning. The SessionStart-hook narration beat was dropped (redundant with the How We Built It section). Total Scene 2.5 runtime unchanged at 25 seconds.

- **demo-recording-checklist.md gained a Scene 2.5 Prep section.** The checklist previously said "close everything except Terminal" which directly conflicted with Scene 2.5's requirement to show the Codex desktop window. The Environment line now names the Codex window as an exception, and a new "Scene 2.5 Prep (the one that will bite you)" section walks the recorder through the six setup steps (second window, pre-typed prompt, git log panel, secrets redaction, window-switch rehearsal, cmd-Tab positioning) that must happen BEFORE hitting record.

- **docs/devpost-submission.md Scene 2.5 description block synced** with the restructured voiceover narration and actions.

- **docs/devpost-form-guide.md checklist updated** from stale "GitHub Release v1.6.0" to current "v1.6.8".

- **doctor.py --version 1.6.8 -> 1.6.9.**


## [1.6.8] - 2026-07-19

### Changed

- **Demo video voiceover restructured to satisfy Devpost hard requirement.** Devpost rules state the video must include a clear demo covering what you built AND how you used Codex and GPT-5.6. The previous voiceover was 100 percent terminal output with zero Codex UI exposure, which would fail this hard submission requirement. Added Scene 2.5 (0:50-1:15) showing the Codex desktop window, dogfooding the doctor diagnosing itself, and the SessionStart hook firing. Scene 1 compressed (0:00-0:30 to 0:00-0:20, dropped the silently-hostile beat), Scene 2 compressed (PAUSE 3s removed), Scenes 3/3b/4 renumbered to the new timeline. Total runtime still 3:00. Final narration now reads Built entirely inside Codex with GPT-5.6.

- **docs/devpost-submission.md scene timeline synced** with the restructured voiceover (Scene 2.5 description block inserted, all scene timestamps renumbered, Scene 5 final narration line updated).

- **doctor.py --version 1.6.7 -> 1.6.8.**


## [1.6.7] - 2026-07-19

### Fixed

- **`.codex-plugin/plugin.json` version was 1.6.5 while doctor.py and the release tag were at 1.6.6.** The previous round's manual sed had a pattern-mismatch bug (targeted `1.6.2` but the file was already at `1.6.5`), so plugin.json silently stayed behind. Root cause: version strings lived in two files with no enforcement that they move together.

### Added

- **`scripts/bump-version.py`** — single command (`python3 scripts/bump-version.py 1.6.7`) bumps every version string in lockstep (doctor.py `--version` flag + plugin.json manifest). Idempotent. Refuses non-semver input. Does not touch CHANGELOG (hand-edited per release) and does not git commit (caller's responsibility). Eliminates the drift class of bug that caused this round's plugin.json staleness.

### Changed

- **`scripts/refresh-transcript.sh` now strips non-deterministic timing ms.** Previously `(25ms)`, `(22ms)` etc. leaked into `docs/demo-transcript.txt` and changed on every run, producing noise diffs that obscured real content changes. Verified: two consecutive `refresh-transcript.sh` runs now produce byte-identical output. The transcript only changes when actual diagnostic content changes.
- **doctor.py --version 1.6.6 -> 1.6.7.**

## [1.6.6] - 2026-07-19

### Fixed

- **All four `examples/*/expected-output.txt` regenerated to match current doctor output.** Every expected-output file was stale: they recorded old fix text, old score values, missing the `🔧 config-ok` status indicator, and in one case (broken-http) even referenced a server name (`ssl-mismatch`) that no longer exists in the config (it is now `https-dead-port`). A judge running an example command and diffing against expected-output would have seen substantive differences in every case. All four now match byte-for-byte (after stripping non-deterministic timing ms); broken-http includes a note that its third server probes the real network so the exact error may vary by environment.

- **`.codex-plugin/plugin.json` version 1.6.2 -> 1.6.6.** The manifest version had not been touched since v1.6.2; v1.6.3-v1.6.5 only shipped README/docs/flag fixes so it drifted. Now consistent with the release tag.

- **GitHub repo About description updated**: was "149 tests" (from v1.4.0 era), now "285 tests" with the full feature list. This is the first line a judge sees in search results and the gallery.

- **GitHub repo topics added**: codex, developer-tools, diagnostics, mcp, mcp-server, model-context-protocol, prompt-injection, security. The repo previously had zero topics, making it undiscoverable by tag search.

- **doctor.py --version 1.6.5 -> 1.6.6.**

## [1.6.5] - 2026-07-19

### Fixed

- **README 5-second judge hook: security-issues command was missing `--check secrets --skip-probe`.** The first command (`broken-stdio`) is local-only and worked perfectly, but the second command (`security-issues`) was shown as a bare `doctor.py --config ...` with no flags. On a fresh clone this actually probes the fake npm package and the example.com HTTPS endpoint, producing `process_crashed` (npm 404) and `ssl_error` noise that buries the two warnings the example exists to showcase (`unpinned_package` + `plaintext_secret_header`). The `demo.sh` and `devpost-submission.md` versions of the same command both already carry `--check secrets --skip-probe` — only the README hook was missing it. Verified on a fresh clone: with the flags, the output is exactly 2 warnings and both servers at 90.0, the clean supply-chain + plaintext-secret showcase the comment promises.

- **doctor.py --version bump 1.6.4 -> 1.6.5.**

## [1.6.4] - 2026-07-19

### Changed

- **Submission materials aligned with v1.6.3 + real demo output** - three audit-driven fixes. (1) `docs/devpost-submission.md` now declares the **Developer Tools** track at the top, mirroring the form guide; previously the submission named no track anywhere. (2) A "Try it in 5 seconds" echo was added to the top of the Long Description, mirroring the README hook so judges reading the project page hit the same conversion moment. (3) The stale checklist line "Select challenge category when announced (July 13)" was replaced with the confirmed Developer Tools selection.
- **Voiceover Scene 4 corrected** - said "two severity tiers fire at once" but the real `demo.sh` Scene 4 output is three alerts (W022 high shared with Scene 3b, E003-changed high, E003-removed low). Reworded to name the two E003 tiers explicitly and acknowledge W022 is shared, so a judge counting alerts on screen is not confused by narration saying "two".
- **doctor.py --version bump 1.6.3 -> 1.6.4** - patch release for documentation alignment.

## [1.6.3] - 2026-07-19

### Changed

- **README: "Try it in 5 seconds" block** - a one-line `git clone && cd && python3 scripts/doctor.py` command lands a judge on a real broken-MCP diagnosis (red error, root cause, one-line fix) in under a second, with no `pip install` and no virtualenv. Placed directly after the dogfooding callout so the very first scroll-down takes a judge from "what is this" to "oh, it actually works." Strongest possible conversion hook for the Devpost gallery thumbnail click-through.
- **Devpost tracks confirmed** - `docs/devpost-form-guide.md` section 11 previously said "tracks TBA 7/13". The four real Build Week categories are now documented (sourced from /rules): Apps for Your Life, Work & Productivity, Developer Tools, Education. Developer Tools is recommended as the natural track - an MCP diagnostic + security audit tool that Codex itself runs. The one-prize-per-project rule is noted.
- **doctor.py --version bump 1.6.0 -> 1.6.3** - the version string had not been touched since v1.6.0; v1.6.1 and v1.6.2 only shipped image/docs changes so the string drifted. Now consistent with the release tag.

## [1.6.2] - 2026-07-19

### Changed

- **README first-screen dogfooding signal** — added "Built with Codex + GPT-5.6" and "OpenAI Build Week" badges plus a dogfooding callout paragraph. The dogfooding story was previously buried in devpost-submission.md; judges who only skim the README first screen now see the key differentiator immediately.
- **Fixed LOC claim** — devpost-submission.md claimed "2,725 lines of doctor logic" but doctor.py is actually 2,865 lines. A judge running wc -l would have caught the discrepancy and it would undercut credibility. Fixed both occurrences.
- **Demo Scene 4 now triggers two E003 severity tiers** — was 1 high (description-changed), now 2 high (W022 + E003-changed) + 1 low (E003-removed via ghost-tool injection). Makes the flagship rug-pull scene visually richer in the video.
- **Voiceover aligned with demo.sh** — added a recording note that Scenes 3b+4 share one terminal segment (homoglyph-attack example triggers W022 and E003 in the same run), plus a trailing note that demo.sh Scene 6 (--debug/--watch) is intentionally excluded from the 3:00 cut. Prevents a real recording failure mode.

## [1.6.1] - 2026-07-19

### Changed

- **Devpost cover + W022 image regenerated to 5:3 (1500x900)** - matches Devpost's actual
  main-image aspect ratio. Previous 16:9 (1200x675) cover would crop badly.
  Both images now use a centered layout verified by pixel sampling to survive the
  1:1 thumbnail center-crop Devpost applies in gallery views.
- `docs/generate-images.py` - both `make_cover()` and `make_w022()` rewritten to
  produce centered 5:3 layouts (was 1200x675 left-aligned).

## [1.6.0] - 2026-07-19

### Added

- **`--debug` flag** - surfaces hidden probe warnings. Best-effort exceptions
  caught during `resources/list`, `prompts/list`, and HTTP body reads are now
  recorded on `ProbeResult.probe_warnings` instead of being silently swallowed.
  Default mode hides them (output unchanged); `--debug` renders them per server
  with a `⚙ debug:` block. Addresses the "silent catch hides real bugs behind
  no_content_returned" risk identified in the v1.5.0 audit.
- **`--watch` mode** - continuously re-runs diagnostics every `--interval`
  seconds (default 30). Only prints when server **status changes** (not on
  every tick), so it's safe to leave running during development. Ctrl+C
  stops cleanly with exit code reflecting the last report. Pairs with
  `--quiet` for hook-style guard duty. Closes the "session-start hook only
  fires once" gap — now you get continuous monitoring.
- **`--interval N`** - seconds between watch iterations (default 30, floored
  at 1s).

### Changed

- Three `except Exception: pass` blocks in `probe_http` now capture the
  exception (`as e`) and record it. The fourth (HTTP error body read) now
  records the exception type in the body field instead of returning empty.
- `ProbeResult` dataclass gains a `probe_warnings: list[str]` field (default
  factory). `ServerResult` stashes warnings via `_probe_warnings` private
  attribute (non-polluting, not in `to_dict()`).

### Tests

- 19 new tests (266 → 285): 7 for `--debug` flag (field independence,
  hidden-by-default, shown-when-debug-on, empty-when-no-warnings,
  missing-attr safety, argparse help); 12 for `_watch_signature` stability
  (latency-insensitive, status-change-sensitive, issue-order-insensitive,
  tool-set-sensitive, config-error-sensitive, argparse help).


## [1.5.0] - 2026-07-19


### Added

- **Guided demo script (`scripts/demo.sh`)** - one command walks through every
  demo scene (broken servers, security/secrets, Cyrillic homoglyph, rug-pull,
  auto-triggering hook) with section titles, narration cues, and real
  `doctor.py` output. Used to record the Devpost demo video and as a CI
  end-to-end smoke test (`--no-pause` mode). Scene 4 genuinely triggers E003
  rug-pull by pinning a real sha256 baseline, corrupting one byte to simulate
  description mutation, and re-checking.
- **CI end-to-end demo step** - GitHub Actions now runs `scripts/demo.sh
  --no-pause` on every push, exercising every example plus the save/check
  baseline flow on Python 3.11-3.14.

### Changed

- **README Quick Start** - promote `./scripts/demo.sh` to the first item
  (above the test suite) as the fastest way for reviewers to see the doctor
  in action.
- **README "W022 in action"** - added a rendered terminal block showing the
  actual homoglyph-attack output, including the "Normalizes to
  'filesystem_read'" punchline, so GitHub visitors can see the attack
  without cloning.
- **README Differentiation** - added vs Snyk agent-scan (zero-dep +
  zero-signup vs `pip install` + account) and explicit "homoglyph detection
  is unique to codex-mcp-doctor" claim cross-referenced against MCP-Scan,
  Snyk, destilabs, and Promptfoo.
- **Devpost submission materials** - removed a duplicate Scene 3b block,
  fixed overlapping scene timestamps, added "Expected on-screen" blocks to
  scenes 1/2/3/3b, and updated LOC metrics to actual (2,725 / 2,371).

### Fixed

- **`plugin.json` screenshots schema** - screenshots were GitHub raw URLs
  (object form); the Codex plugin validator requires relative-path strings
  pointing to PNG files under `./assets/`. Added `assets/` directory with
  both screenshots and switched to `./assets/...` paths.
- **`plugin.json` `defaultPrompt` overflow** - the interface spec keeps only
  the first 3 entries; we had 8. Trimmed to the 3 highest-signal starter
  prompts (all under 128 chars).
- **`scripts/demo.sh` non-TTY stdin hang** - screen recorders and other
  environments without interactive stdin blocked indefinitely at `read -p`.
  `do_pause` now checks `[ -t 0 ]` before prompting.

### Added

- **Cyrillic homoglyph detection (W022)** - detects mixed-script words
  where Cyrillic lookalike characters (а="a", е="e", о="o",
  etc.) are substituted into otherwise-Latin identifiers. Attackers use
  this to impersonate trusted tool names (e.g. `filеsystem` looks
  like `filesystem` but the "e" is Cyrillic). Reports the normalized
  ASCII form so the model can understand the intended disguise.
- **Devpost submission materials** - `docs/devpost-submission.md` with
  full demo video script (5 scenes), project description, and submission
  checklist for OpenAI Build Week.

### Fixed

- **Baseline file with non-dict server values** - a corrupted or tampered
  baseline storing a list, int, null, or string as a server's tool map
  caused `TypeError` in `check_baseline`, crashing the doctor and silently
  disabling rug-pull detection. Now emits `baseline-server-invalid-type`
  (high severity) and skips the affected server.
- **Non-string `command` crashes** - `command = ["a","b"]` (list),
  `command = 42` (int), `command = true` (bool), or `command = {a=1}`
  (dict) crashed `os.path.isabs()` with `TypeError` during config
  validation. Now returns `invalid_command_type` error.
- **Non-string `url` crashes** - `url = ["http://x"]` (list), `url = 42`
  (int), `url = {a=1}` (dict), or `url = true` (bool) crashed
  `urlparse()` with `AttributeError` during config validation. Now
  returns `invalid_url_type` error.
- **GitGuardian false positives** - test fixtures using real-format
  fake tokens (`sk-1234...`, `mos_abcdef...`) tripped secret scanners.
  Replaced with low-entropy `TESTFAKE`-marked values that still match
  the doctor's own detection regex.

### Fixed

- **Non-string `cwd` crashes** - `cwd = 42` (int) or `cwd = ["/tmp"]` (list)
  crashed `os.path.expanduser()` with `TypeError` in both config validation
  and the stdio probe path. Now returns `invalid_cwd_type` error.
- **Non-string `env` values** - `env.KEY = 42` (int) warns; `env.KEY = ["a"]`
  (list) or `env.KEY = {nested = true}` (dict) errors. MCP servers expect
  string env values; non-string values cause `Popen` env failures.
- **Non-string `http_headers` values** - `X-Key = 42` (int/list) warns.
  HTTP headers are always strings.

### Fixed

- **JSON-RPC parser crashes on malformed tool/resource/prompt lists** -
  a server returning `"tools": null`, `"tools": 42`, or `"tools": "string"`
  crashed `_parse_stdio_responses` with `TypeError: object of type has no
  len()`. A string value was silently iterated char-by-char, reporting a
  false tool count. Both `_parse_stdio_responses` and
  `_extract_items_from_rpc` now validate that the value is a list before
  use, defaulting to `[]`.

### Fixed

- **NaN/negative latency silently bypassed score penalties** - `float('nan')`
  latency passed all threshold comparisons as `False`, so a NaN-latency server
  appeared perfectly healthy. Negative latency (from clock issues) also
  bypassed checks. Now `latency_issue` and `compute_health_score` explicitly
  guard against NaN and negative values.
- **`--only` with unmatched server name silently returned nothing** - a typo
  in `--only srv-name` produced zero results with no explanation. Now emits a
  synthetic `only_filter_no_match` error listing available server names.

### Changed

- 258 tests (was 250).

## [1.4.2] - 2026-07-18

### Fixed

- **`--check schema` never probed** - schema-only mode skipped the
  connectivity probe entirely, so it could never see tool definitions
  and never detected schema issues. It returned `config-ok` even on
  servers with broken schemas. Now schema mode probes and runs full
  schema validation (tools + resources + prompts).
- **`--check security` misreported `config-ok`** - after a successful
  probe with no security findings, servers were marked `config-ok`
  instead of `healthy`. The status logic only treated `all` and
  `connectivity` modes as probe-worthy. Now any mode that probed
  successfully reports `healthy` when clean.
- **Resource/prompt schema gaps in `--check schema`** - resource and
  prompt schema validation only ran in the cross-server security pass
  (`all`/`security` modes). `--check schema` now validates resource
  and prompt schemas in the per-server loop.

### Fixed

- **SSE parser returned wrong message** - when an SSE stream contained
  a notification before the actual RPC response, the parser returned the
  first valid JSON dict (the notification) instead of continuing to find
  the response with `result` or `error`. Now skips notifications and
  prefers RPC responses.
- **Empty config exit code** - empty config (0 servers, valid file)
  returned exit 2 ("config unreadable") instead of exit 3 ("no servers
  found"). The informational "no entries" message was treated as a
  config error. Now distinguishes parse errors from info messages.
- **Config-ok health score ignored issues** - servers with `config-ok`
  status (not probed) always scored 100, ignoring config-layer issues
  like unpinned packages, plaintext secrets, and invalid env types.
  Now applies per-issue penalties.

### Fixed

- **`const` property false positive** - a JSON Schema property using
  `const` without a `type` field triggered `property_missing_type`.
  `const` is a valid standalone constraint per JSON Schema spec.
- **E002 false positive on common words** - tool names that are also
  common English words (4-5 chars: `time`, `count`, `email`) triggered
  cross-server shadowing false positives when they appeared naturally
  in another server's tool description. Minimum name length raised
  from 4 to 6.

### Added

- 14 regression tests covering all above fixes (221 total).
- `--baseline-path` and `--quiet` flags documented in SKILL.md.

## [1.4.1] - 2026-07-18

### Fixed

- **Baseline silent-skip bug** - `--check-baseline` with a missing baseline
  file silently returned `[]` (exit 0, no output). Now returns an info-level
  message telling the user to run `--save-baseline` first.
- **Duplicate baseline-issue append** - server-level baseline issues were
  appended twice to `security_issues` due to a duplicated `if target:` block
  in `main()`.
- **Baseline-failure exit code** - high-severity baseline problems (corrupted
  /invalid file) now return exit code 2 instead of 0, so hooks notice that
  rug-pull detection silently failed.
- **Docker exec/build/create false positive** - `docker exec`, `docker build`,
  and `docker create` were flagged as unpinned images. Only `docker run` and
  `docker pull` fetch from a registry; others operate on local state.

### Added

- **property_missing_type schema check** - a tool property with no `type`
  and no `$ref`/`anyOf`/`oneOf`/`allOf` leaves the model unable to tell
  what value to pass. Now a warning.
- **object_no_properties schema check** - `type:object` with no properties,
  additionalProperties, or patternProperties is vacuous. Now a warning.
- **Deepened resource + prompt schema validation** - resources now also
  check for missing name/description; prompts check description,
  short-description, and argument structure (invalid/missing-name/
  missing-description). API change: both functions return
  `list[ToolSchemaIssue]` instead of single issue|None.
- **JSON-RPC error detection** - when a server returns a JSON-RPC error
  response (e.g. protocol-version-not-supported), the probe now reports
  an `rpc_error` issue instead of silently showing 'healthy but 0 tools'.
- **Pipe-through-curl exfiltration detection** - catches
  `pipe|feed|stream ... through|via curl|wget|nc` patterns that lack the
  `to <URL>` structure the old regex required.
- **curl/wget to suspicious hostnames** - catches `curl ... evil.com` /
  `curl ... attacker.io` where the hostname itself is the red flag.
- **Tool poisoning self-contradiction** - catches
  `actually deletes|removes|overwrites|destroys|wipes|formats` patterns
  where a tool description contradicts its claimed purpose.
- Synthetic test token replaced with a low-entropy fake to avoid tripping
  GitGuardian-style secret scanners (was a valid-format 36-char PAT).

## [1.4.0] - 2026-07-18

### Added

- **E003 Rug-Pull Detection** - `--save-baseline` stores a sha256 hash of each
  tool's `name + description`; `--check-baseline` flags any tool whose
  description changed since the baseline (high), new tools (medium), or removed
  tools (low). Baseline lives at `~/.codex/mcp-doctor-baseline.json`.
  Inspired by Invariant Labs' MCP-Scan; the first CLI implementation.
- **Supply-Chain Version Pinning (MCP04)** - `--check supply-chain` flags
  `npx`/`npm`/`uvx`/`pipx` commands with unpinned package versions and
  `docker run` images without a `@sha256:` digest or concrete `:tag`.
- **Plaintext Secrets Detection (NSA guidance)** - `--check secrets` scans
  `env`, `http_headers`, and URLs for hardcoded API keys (`sk-*`, `mos_*`,
  `AKIA*`, `ghp_*`, `xox*`, `AIza*`, PEM private keys, long Bearer tokens).
  `$VAR` / `${VAR}` references are correctly recognized and not flagged.
- **Latency Thresholds** - probe latency >15s produces a warning (-10 health
  score points); 5-15s produces an info note (-5 points).
- **Resource & Prompt Security Scanning** - E001/W001/W021 checks extended
  from tools only to also cover resources (URI + description) and prompts
  (description + argument descriptions). Issues are prefixed `resource:` /
  `prompt:`.
- `--baseline-path` option to override the baseline file location.

### Changed

- **Marketplace packaging** - added `.agents/plugins/marketplace.json` so the repo installs via `codex plugin marketplace add` + `codex plugin add`. The old README claimed `codex plugins add .` worked but that command does not exist in any Codex CLI version.
- Fixed installation docs: replaced non-existent `codex plugins add .` with verified `codex plugin marketplace add` + `codex plugin add` flow.
- Removed `UserPromptSubmit` hook trigger: running a full server probe on every user message caused multi-second delays. `SessionStart` (once per session) plus the SKILL.md auto-trigger (on-demand) provides better coverage without latency cost.
- Health score now applies a latency penalty and an E003 rug-pull cap (max 50
  for high-severity description changes).
- `--check` accepts `supply-chain` and `secrets` in addition to `all`,
  `connectivity`, `schema`, `security`.
- 44 new tests (105 → 149 total).

### Fixed (post-1.4.0 hardening)

- **HTTP probe timeout budget** - `probe_http` previously gave each of its 5
  RPC calls the full `--timeout` budget, so `--timeout 8` could take up to 40s
  and blow past the 10s SessionStart hook limit. All calls now share a single
  `remaining()` budget that decrements with elapsed time.
- **`bearer_token` / `bearer_token_env_var` resolution** - the HTTP probe only
  read `http_headers` for Authorization. Codex shorthand fields were ignored,
  causing false `auth_failed` errors on servers configured with `bearer_token`.
  Both fields are now resolved into `Authorization: Bearer <token>` at probe
  time (env vars support `$VAR` and bare names).
- **Unified issue field schema** - probe issues used `level`+`type`, schema
  issues used `severity`+`kind`, security issues used `severity`+`code`. All
  three now expose `severity`+`code` consistently (schema keeps `kind` as
  alias). Top-level JSON `health_score` mirrors `summary.avg_health_score`.
- **Resources-only / prompts-only servers** - a server exposing resources or
  prompts but zero tools was flagged `warning` (`no_tools_returned`), a false
  positive. Per MCP spec this is valid; now downgraded to `info`
  (`resources_only`). Truly empty servers still warn (`no_content_returned`).
- `plaintext_secret_header` fix now recommends `bearer_token_env_var` over
  inlining tokens in `http_headers`.
- Test HTTP servers now call `server_close()` to clear `ResourceWarning`.
- **W001 false-positive reduction** - the manipulative-language word list
  had a single tier including common technical words (`must`, `always`,
  `never`, `important`). These appear constantly in legitimate tool
  descriptions ("the value must be a string"), making the security scan
  feel noisy and unreliable. Now split into two tiers: high-confidence
  verbs (`crucial`, `immediately`, `override`, `bypass`, `secretly`)
  trigger on their own; common words only trigger when >=3 cluster in one
  description. W001 findings on a real 3-server setup dropped from 4 to 2.
- **W019 destructive regex expanded** - added `overwrite`, `erase`, `purge`
  to the destructive-capability detection. A tool description saying
  "Always overwrite existing files without confirmation" was previously
  missed (CLEAN). Now correctly flagged as W019.
- `plugin.json` capabilities now includes `Write` (for `--save-baseline`).
- **Redundant latency warning on timeout** - when a server probe timed out,
  the latency check still ran (latency = timeout*1000 ms) and emitted an
  `elevated_latency` info issue alongside the `timeout` error. The latency
  note is now suppressed when a timeout issue is already present; high
  latency is implied by the timeout itself.
- 14 new tests (149 → 182 total).
- **Resource & prompt schema validation** - resources missing a URI and
  prompts missing a name are now flagged as schema errors (MCP spec
  violations). Previously only security-scanned, not structurally validated.
  New standalone functions validate_resource_schema / validate_prompt_schema.
- **Baseline corruption detection (E003)** - a corrupted, empty, or
  structurally invalid baseline file (valid JSON but not an object) no
  longer causes silent failure or a crash. check_baseline now returns a
  high-severity `baseline-unreadable` / `baseline-invalid-structure`
  warning so the user knows rug-pull detection is not active. The
  warning surfaces in the report header as a config-level error.
- **Credential-file-access detection (E001)** - tool descriptions referencing
  SSH private keys (`~/.ssh/id_rsa`, `id_ed25519`, `authorized_keys`, `config`),
  AWS credentials (`~/.aws/credentials`), GPG keys (`~/.gnupg/`), and `.env`
  files are now flagged as critical-severity credential theft. Bare mentions
  of `.ssh`/`.aws`/`.gnupg` in read/copy/backup contexts are also caught.
  3 new tests cover SSH-key theft, AWS-credential theft, and subtle webhook
  exfiltration (`append ... to webhook at URL`).

## [1.3.0] - 2026-07-17

### Added

- **L4 Security Analysis** - scans every tool's name and description for:
  - E001 prompt injection (18 regex patterns, including `<|im_start|>`,
    "ignore previous instructions", exfiltration commands, role hijacking).
  - E002 cross-server tool shadowing (a tool description referencing a
    different server's tool name).
  - W001 manipulative language (urgency words: "crucial", "immediately",
    "must", "override", "bypass").
  - W021 hidden Unicode (zero-width spaces U+200B, bidi overrides U+202E,
    Unicode Tag sequences U+E0000–U+E007F with decode).
  - W015/W017/W019 capability risks (untrusted content, sensitive data,
    destructive operations).
- Security issues cap the health score: critical → max 20, high → max 50.
- `--check security` CLI mode.

## [1.2.0] - 2026-07-16

### Added

- **L2.6 Capabilities parsing** - extracts and reports the `capabilities`
  dict (tools/resources/prompts/logging/elicitation) and negotiated protocol
  version.
- **stdio notifications capture** - captures `notifications/*` messages during
  stdio probes.
- Codex-specific config field validation: `startup_timeout_sec`,
  `tool_timeout_sec`, `env` `$VAR` references, `http_headers` auth.

## [1.0.0] - 2026-07-15

### Added

- Initial release.
- L1 connectivity probes (stdio + HTTP/SSE) with full MCP handshake
  (initialize + tools/list + resources/list + prompts/list).
- L2 configuration correctness validation.
- L2.5 schema quality checks (7 issue types).
- L3 health score (0-100).
- Human-readable and JSON output formats.
