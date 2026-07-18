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

**Paste:**
```
Zero-dependency MCP diagnostics for Codex
```

---

## 3. 30-second Demo Video

**Field:** `Demo Video URL` (required — YouTube or Vimeo)

**How to produce it:**
1. Clone the repo: `git clone https://github.com/luogangan7-lgtm/codex-mcp-doctor.git`
2. `cd codex-mcp-doctor && ./scripts/demo.sh` — screen-record this run
3. Trim to ≤30s if Devpost asks for a short one, or keep the full ~3 min run
   if it accepts longer (Build Week allows 2-3 min)

**Tip:** `./scripts/demo.sh` walks through every feature scene-by-scene with
titles and narration cues already written. No need to script anything new.

---

## 4. Detailed Description

**Field:** `Project Details / Description` (required, Markdown supported)

**Paste the entire "Long Description" section** from
`docs/devpost-submission.md` — from `### The Problem` through `### What's Next`.
~4 paragraphs + a layer table. Devpost accepts long descriptions; use the
full version.

---

## 5. Built With

**Field:** `Built With` (required — tags for technologies used)

**Paste these tags (Devpost accepts comma-separated or one-per-line):**
```
Python, Codex, GPT-5.6, MCP (Model Context Protocol), Codex Desktop, GitHub Actions, Pure Python stdlib
```

**Lead with `Codex` and `GPT-5.6`** — this is OpenAI Build Week, judges will
scan for those tags first.

---

## 6. Team

**Field:** `Team Members` (required — solo or team)

**Solo:** Add yourself. No teammates to invite.

---

## 7. Source Code / Repo

**Field:** `Source Code URL` (required for OpenAI Build Week)

**Paste:**
```
https://github.com/luogangan7-lgtm/codex-mcp-doctor
```

**Pin to the v1.5.0 release** (optional but recommended for reproducibility):
```
https://github.com/luogangan7-lgtm/codex-mcp-doctor/releases/tag/v1.5.0
```

---

## 8. Try It Out Link

**Field:** `Try it out` / `Live Demo` (optional)

This is a CLI tool, not a hosted app. Paste the GitHub repo URL again, or
leave blank. The demo video + repo README are the "try it out" surface.

---

## 9. Custom Questions (if Build Week asks any)

OpenAI Build Week may add custom questions like "Which OpenAI product did
you use?" or "Which challenge track are you submitting to?" Check the form
on July 13 when tracks are announced.

**Likely answers:**
- **OpenAI products used:** Codex (Desktop + CLI), GPT-5.6
- **Track:** pick the one closest to "Developer Tools" / "Infrastructure"
  when categories publish July 13
- **How does your project use Codex?** Paste the "How We Built It" paragraph
  from `docs/devpost-submission.md` — emphasize that the entire codebase was
  written through Codex-driven iterative development.

---

## Pre-Submission Verification

Run this checklist before clicking "Submit":

```bash
cd /Volumes/data/codex-mcp-doctor

# 1. Tests green
python3 tests/test_doctor.py

# 2. Plugin manifest valid
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .

# 3. Demo script runs end-to-end
./scripts/demo.sh --no-pause

# 4. HEAD is the v1.5.0 release tag
git describe --tags --exact-match    # should print v1.5.0
```

All four must pass before submitting. If any fails, stop and fix.

---

## Submission Checklist (from devpost-submission.md)

- [x] Public repo: https://github.com/luogangan7-lgtm/codex-mcp-doctor
- [x] Working code with 266 passing tests
- [x] CI green (GitHub Actions, Python 3.11-3.14)
- [x] Zero external dependencies (AST-verified)
- [x] Plugin manifest passes Codex validator
- [x] GitHub Release v1.5.0 published
- [x] Screenshots: `assets/screenshot-real-report.png`, `assets/screenshot-rugpull-detection.png`
- [x] Guided demo script: `./scripts/demo.sh`
- [ ] **Demo video recorded** (run `./scripts/demo.sh` + screen record)
- [ ] **Devpost project page filled** (use this guide)
- [ ] **Challenge category selected** (after July 13 announcement)
- [ ] **Submitted before July 21, 5PM PT**

The four unchecked items are user actions. Everything else is done.
