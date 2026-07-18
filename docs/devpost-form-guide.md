# Devpost Submission Form — Field-by-Field Guide

Walks through the Devpost hackathon submission form top to bottom. For each
field: what to paste, character limits, and gotchas. Open this side-by-side
with the Devpost "Submit Project" page and just go down the list.

Source content lives in `docs/devpost-submission.md`; this guide maps that
content to the form fields.

---

## 1. Project Name

**Field:** `Project Name` (required, ~60 char limit on Devpost)

**Paste:**
```
codex-mcp-doctor — `npm doctor` for MCP
```

---

## 2. Short Tagline

**Field:** `Subtitle / Tagline` (required, ~35-60 char limit)

**Paste (two options, pick based on field limit):**

If the field is the Short Description (Devpost card, ~280 char limit):
```
MCP servers fail silently. codex-mcp-doctor is the diagnostic CLI Codex should ship with — one zero-dependency command catches broken servers, prompt injection, silent rug-pulls, and Cyrillic homoglyph attacks that no other MCP scanner detects. Built in Codex with GPT-5.6.
```
(273 chars — problem-first hook + differentiation + dogfooding. The previous version was 303 chars and over the limit.)

If the field is a one-line tagline (~35-60 chars):
```
npm doctor for MCP. Built in Codex with GPT-5.6.
```
(48 chars — uses the established tagline + Build Week dogfooding signal.)

---

## 3. Project Card Thumbnail / Cover Image

**Field:** `Project Image` / `Thumbnail` (required — first thing judges see in the gallery)

**Upload:** `docs/devpost-cover.png` (1500x1000, 3:2 - Devpost recommended Project Gallery thumbnail ratio per help.devpost.com/article/126)

This is the generated cover showing the project title, tagline, feature
matrix, and a mini terminal preview. If you want a different visual, also
consider `docs/screenshot-real-report.png` (a real diagnostic report).

---

## 4. 30-second / 3-minute Demo Video

**Field:** `Demo Video URL` (required — YouTube or Vimeo, public)

**How to produce it:**
1. Clone the repo: `git clone https://github.com/luogangan7-lgtm/codex-mcp-doctor.git`
2. `cd codex-mcp-doctor && ./scripts/demo.sh` — screen-record this run
3. Voice over using `docs/demo-voiceover-script.md` (3:00 hard limit, already timed)
4. Upload to YouTube as **Public** (Unlisted will not embed on Devpost)

**Tip:** `./scripts/demo.sh` walks through every feature scene-by-scene with
titles and narration cues already written. The voiceover script totals
exactly 3:00; if you need a 30s teaser, see the cut-down section at the
bottom of `docs/demo-voiceover-script.md`.

---

## 5. Detailed Description

**Field:** `Project Details / Description` (required, Markdown supported)

**Paste the entire "Long Description" section** from
`docs/devpost-submission.md` — from `### The Problem` through `### What's Next`.
This includes six subsections, all of which map to the four judging criteria:

1. **The Problem** — sets up the "silent failure + silent hostility" hook (Creativity & Originality).
2. **What It Does** — the layer-by-layer feature table + key differentiators (Technological Implementation).
3. **How We Built It** — dogfooded Codex end-to-end: skills as the deployment surface, `SessionStart` hook for auto-trigger, `--watch` for continuous monitoring, Codex's MCP client as the test oracle, memory canvas for multi-session continuity. **This is the strongest answer to "How thoroughly and skillfully does the project use Codex?"** — the central Technological Implementation question. Paste the whole section.
4. **Design Philosophy** — the terminal report IS the UX. Emoji severity, health score transparency, `→ fix:` actionable suggestions, ASCII alignment. **Directly serves the Design & UX judging dimension** — do not trim this.
5. **Why This Matters Now** — MCP ecosystem at inflection point, silent failure is the default, security tooling hasn't caught up. **Directly serves the Potential Impact judging dimension** — this is the section that answers "so what?" Lead the judges to the conclusion that this belongs in Codex's default plugin set.
6. **What's Next** — roadmap (semantic poisoning detection, marketplace publication).

Devpost accepts long Markdown; paste all six subsections verbatim. The
layer table inside "What It Does" renders cleanly on Devpost.

---

## 6. Additional Images / Screenshots

**Field:** `Additional Images` / `Screenshots` (optional but high-value)

Upload these in order — they appear in the project page gallery:

1. `docs/devpost-cover.png` — hero cover (also used as thumbnail)
2. `docs/w022-homoglyph.png` — **W022 Cyrillic attack visualization (unique feature, lead with this)**
3. `docs/screenshot-rugpull-detection.png` — rug-pull / baseline drift detection
4. `docs/screenshot-real-report.png` — a real multi-server diagnostic report

The W022 image is the strongest single asset for differentiation — no other
MCP scanner detects Cyrillic homoglyph attacks.

---

## 7. Built With

**Field:** `Built With` (required — tags for technologies used)

**Paste these tags (Devpost accepts comma-separated or one-per-line):**
```
Python, Codex, GPT-5.6, MCP (Model Context Protocol), Codex Desktop, GitHub Actions, Pure Python stdlib
```

**Lead with `Codex` and `GPT-5.6`** — this is OpenAI Build Week, judges will
scan for those tags first.

---

## 8. Team

**Field:** `Team Members` (required — solo or team)

**Solo:** Add yourself. No teammates to invite.

---

## 9. Source Code / Repo

**Field:** `Source Code URL` (required for OpenAI Build Week)

**Paste:**
```
https://github.com/luogangan7-lgtm/codex-mcp-doctor
```

**Pin to the latest release** (recommended for reproducibility — points
judges at the tag that matches the video). At submission time, check
https://github.com/luogangan7-lgtm/codex-mcp-doctor/releases/latest
and use that tag URL. As of this writing: v1.6.19 (will be v1.6.20 if the image-ratio fix gets a tag).
```
https://github.com/luogangan7-lgtm/codex-mcp-doctor/releases/latest
```

---

## 10. Try It Out Link

**Field:** `Try it out` / `Live Demo` (optional)

This is a CLI tool, not a hosted app, but each release ships a standalone
zip so judges can try it without cloning. Paste the latest release URL:
```
https://github.com/luogangan7-lgtm/codex-mcp-doctor/releases/latest
```
Judges who click get a one-download try: unzip the standalone zip, run
`python3 doctor.py --config examples/broken-stdio/config.toml`. No git,
no pip, no virtualenv. This is stronger than "leave blank" because it
turns the field into a second conversion point.

---

## 11. Custom Questions (track + Codex usage)

Build Week tracks are now public (confirmed via /rules, 2026-07-19). There
are four categories, each with a 1st and 2nd place prize:

- **Apps for Your Life**
- **Work & Productivity**
- **Developer Tools** -- "Tools for developers, including testing, DevOps,
  agentic workflows, and security". This is codex-mcp-doctor's natural
  track: an MCP diagnostic + security audit tool that Codex itself runs.
- **Education**

Each project is eligible for one prize only, in its selected category.

**Answers to fill in:**
- **Category:** Developer Tools (recommended).
- **OpenAI products used:** Codex (Desktop + CLI), GPT-5.6.
- **How does your project use Codex?** Paste the **entire "How We Built It"**
  section from `docs/devpost-submission.md`. Lead with the dogfooding framing:
  "Built entirely inside Codex desktop with GPT-5.6 as the development
  environment — not just 'used Codex to write some code,' but dogfooded Codex
  end-to-end to build tooling *for* Codex." Then the five load-bearing points:
  skills as deployment surface, SessionStart hook, `--watch` continuous
  monitoring, MCP client as test oracle, memory canvas for multi-session
  continuity. This single answer carries most of the Technological
  Implementation score.

---

## 12. Codex Session ID (REQUIRED by rules)

Devpost rules state: *"Provide /feedback Codex Session ID for your Project
thread where the majority of core functionality was built."*

**Action needed (user only - LLM cannot do this):**
- In Codex desktop, open the thread where most of the doctor logic was built
- Run `/feedback` to get the Session ID
- Paste it into the submission form field

This is a hard requirement - judges use it to verify the Codex collaboration
story. Without it, the Technological Implementation score is at risk.

---

## Pre-Submission Verification

Run this checklist before clicking "Submit":

```bash
cd codex-mcp-doctor

# 1. Tests green (287 tests)
/opt/homebrew/bin/python3 tests/test_doctor.py

# 2. Plugin manifest valid
/opt/homebrew/bin/python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .

# 3. Demo script runs end-to-end
./scripts/demo.sh --no-pause

# 4. HEAD is on a release tag (v1.6.x)
git describe --tags --exact-match    # should print v1.6.x
```

All four must pass before submitting. If any fails, stop and fix.

---

## Submission Checklist (from devpost-submission.md)

- [x] Public repo: https://github.com/luogangan7-lgtm/codex-mcp-doctor
- [x] Working code with 287 passing tests
- [x] CI green (GitHub Actions, Python 3.11-3.14)
- [x] Zero external dependencies (AST-verified)
- [x] Plugin manifest passes Codex validator
- [x] GitHub Release published (latest: https://github.com/luogangan7-lgtm/codex-mcp-doctor/releases/latest)
- [x] Cover image: `docs/devpost-cover.png`
- [x] W022 visualization: `docs/w022-homoglyph.png`
- [x] Screenshots: `docs/screenshot-real-report.png`, `docs/screenshot-rugpull-detection.png`
- [x] Guided demo script: `./scripts/demo.sh`
- [x] Standalone release zip (zero-clone try): attached to latest release
- [ ] **Demo video recorded** (run `./scripts/demo.sh` + screen record + voiceover)
- [ ] **Devpost project page filled** (use this guide)
- [ ] **Challenge category selected** (Developer Tools -- recommended)
- [ ] **Submitted before July 21, 5PM PT**

The four unchecked items are user actions. Everything else is done.
