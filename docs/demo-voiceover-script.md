# Demo Video Voiceover Script (3:00 hard limit)

Pure voiceover script for screen-recording. Read this aloud while
`./scripts/demo.sh` plays on screen. Every timestamp matches the scene
breakdown in `docs/devpost-submission.md`.

**How to use this file:**
1. Open Terminal, `cd codex-mcp-doctor`, run `./scripts/demo.sh`.
2. Start screen recording (QuickTime → File → New Screen Recording).
3. Read each `[VO]` block at the timestamp shown. `[PAUSE]` = let the screen
   speak for itself. `[CLICK]` = perform the action, then resume reading.
4. Total runtime target: 3:00 exactly. Do not exceed.

---

## Pre-roll (before hitting record)

- Terminal: macOS, dark theme, 18pt monospace, full window
- Working dir visible in prompt: `codex-mcp-doctor`
- Close all other apps. Notifications off (Do Not Disturb).
- Mic check: record 5s of silence, play back, confirm no fan noise.
- Have this file open on a second screen or printed out.

---

## Scene 1 — The Silent Failure (0:00 – 0:20)

`[0:00]` `[VO]` MCP servers fail silently. You add one to your config, restart Codex, and — nothing. No tools. No error. No log. You're left guessing what broke.

`[0:12]` `[VO]` codex-mcp-doctor fixes that. Let me show you.

---

## Scene 2 — The Doctor Diagnoses (0:20 – 0:50)

`[0:20]` `[CLICK]` Run: `python3 scripts/doctor.py --config examples/broken-stdio/config.toml`

`[0:21]` `[VO]` One command. Zero dependencies — pure Python stdlib.

`[0:25]` `[VO]` It tells you exactly what's wrong. The binary path doesn't exist. The second server crashes because a Python module is missing. Both root-caused in under a second — red error, exact cause, one-line fix.

`[0:42]` `[VO]` That's the easy part.

## Scene 2.5 — Built with Codex (0:50 – 1:15)  *required by Devpost rules*

> **Why this scene exists:** Devpost rules state the video "must include a
> clear demo with audio that covers what you built **AND how you used Codex
> and GPT-5.6**." Scenes 1-2 show what was built; this scene shows how. Do
> not cut it — without it the video fails a hard submission requirement.

`[0:50]` `[CLICK]` Switch screen recording to the Codex desktop window.

`[0:51]` `[VO]` Here's the thing — this entire tool was built inside Codex.

`[0:55]` `[CLICK]` **Prep BEFORE recording:** open a second Codex desktop window with this repo loaded, and a terminal panel showing `git log --oneline -10` (so the commit history is visible). Have one prompt typed but not sent: `diagnose this repo's own MCP setup`. Do NOT show anything with real secrets.

`[0:56]` `[VO]` Nearly three thousand lines of logic. Two hundred ninety-four tests. Every security analyzer.

`[1:02]` `[VO]` Written, debugged, and hardened through Codex with GPT-5.6.

`[1:06]` `[CLICK]` Press Enter on the pre-typed prompt so the doctor runs on its own repo. Keep the commit-history terminal visible as secondary context.

`[1:07]` `[VO]` The doctor speaks the same MCP protocol Codex speaks. So the test suite hits the exact handshake paths Codex uses.

`[1:13]` `[CLICK]` Switch screen recording back to Terminal for the security demo.

---

## Scene 3 — Security Layer (1:15 – 1:40)

`[1:15]` `[CLICK]` Run: `python3 scripts/doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe`

> **Why `--check secrets --skip-probe` (not the bare config):** the example servers use fake hostnames (`api.example.com`) and a nonexistent npm package, so a live probe crashes both (npx 404 + SSL error) and the screen fills with red crash errors that bury the two config-layer findings the scene is about. `--check secrets --skip-probe` runs only the static config scan, which is where `unpinned_package` and `plaintext_secret_header` live — both servers score 90.0 with exactly the two warnings the VO names. This matches every other doc (README, submission, demo.sh, demo-transcript.txt, examples/README.md) — the bare `--config` form in the v1.6.29 narration rewrite was a typo that would have broken the recording.

`[1:16]` `[VO]` What about servers that are silently hostile? The security layer catches seven classes of attack. Two of them fire here —

`[1:28]` `[VO]` Here — an unpinned npx package that could be republished with malware, and a hardcoded bearer token sitting in an HTTP header. Both flagged, both with severity, both with a fix.

`[1:35]` `[VO]` Every error pairs with the one action that resolves it.

---

> **Recording note — Scenes 3b and 4 use the same example config but are separate runs.** Scene 3b runs `homoglyph-attack` once and only W022 (the Cyrillic homoglyph) fires. Scene 4 then reuses that same config to demo rug-pull: demo.sh saves a baseline, mutates it (flip one hash, drop one tool, inject a ghost), and re-checks — that third run is what lights up the three E003 tiers. So you WILL see the `homoglyph-attack` command appear twice on screen (once in 3b, once as step 1 of Scene 4). Keep one continuous screen capture across 3b+4 (1:30–2:45); the visible command re-run is intentional and sets up the rug-pull reveal.

## Scene 3b — Cyrillic Homoglyph Attack (1:40 – 2:05)

`[1:40]` `[VO]` Here's one no other MCP scanner catches.

`[1:42]` `[CLICK]` Run: `python3 scripts/doctor.py --config examples/homoglyph-attack/config.toml`

`[1:43]` `[VO]` This server exposes a tool called `filеsystem_read` — but the `е` is Cyrillic, not Latin. It looks identical, it shadows the real filesystem tool, and it would exfiltrate your data.

`[1:58]` `[VO]` The doctor normalizes it — "Normalizes to filesystem_read" — so you see the attack intent, not just the cosmetic difference. Eighteen Cyrillic-to-Latin confusables mapped.

---

## Scene 4 — Rug-Pull Detection (2:05 – 2:45)

`[2:05]` `[VO]` The flagship feature: rug-pull detection.

`[2:08]` `[VO]` First run, the doctor saves a baseline hash of every tool description. Next run, it compares. If anything changed — a description rewritten, a tool added, a tool removed — you get a three-level alert.

`[2:22]` `[CLICK]` Run the check-baseline demo step from `demo.sh`

`[2:23]` `[VO]` Three E003 tiers fire at once: high for a tampered description, medium for a tool that appeared since baseline, low for one that vanished. The doctor names the exact tool, the exact change, and what to do. First CLI implementation of tool-description pinning.

> **Recording note (v1.6.34) — screen shows four findings, not three.** The W022 homoglyph warning from Scene 3b still fires because the config is unchanged, so judges see one W022 high row above the three E003 rows. The VO wording is already correct ("three E003 tiers", not "three findings") so the on-screen W022 is covered — but be ready to improvise "the homoglyph from the last scene still lights up at the top" if you need a beat while the report renders.

`[2:42]` `[VO]` The server you trusted on Monday is not the server you're running on Friday.

---

## Scene 5 — Two Layers of Protection (2:45 – 3:00)

`[2:45]` `[VO]` Best part: you don't run it. Two layers of protection.

`[2:48]` `[CLICK]` Flash `hooks/hooks.json` on screen, then flash `--watch --interval 30`.

`[2:50]` `[VO]` The SessionStart hook fires every session — silent when healthy, loud when broken. Watch mode extends that into continuous runtime monitoring.

`[2:55]` `[VO]` Two hundred ninety-four tests. Zero dependencies. Built entirely inside Codex with GPT-5.6 — the MCP doctor Codex should ship with.

`[3:00]` `[END CARD]` GitHub URL on screen for 2s. Stop recording.

---

## Pacing Notes

- Total target: 3:00. If you finish Scene 5 early, hold the end card — do not start a new sentence.
- If you run long, cut from Scene 2 first (the doctor output speaks for itself, narration can be shorter). Never cut Scene 4 — rug-pull is the flagship.
- Speak at conversational pace, not presentation pace. The timestamps assume ~150 words per minute (conversational pace). At 425 total words that leaves ~10s of breathing room under the 3:00 hard limit.
- The `[PAUSE]` moments matter — let the screen show the report. Judges read the terminal, not just listen to you.


## Beyond the 3:00 Cut — Scene 6 (--debug / --watch)

`./scripts/demo.sh` contains a Scene 6 that demonstrates `--debug` (surfaces hidden probe warnings) and `--watch` (continuous monitoring). These are v1.6.0 features but are deliberately **not** in the 3:00 video cut — the Devpost hard limit leaves no room, and the hook+watch mention in Scene 5 already carries the message. If Devpost asks for a longer director's cut, run `./scripts/demo.sh` in full and narrate Scene 6 live; otherwise leave it as a repo-only extra.

## If You Need a 30-Second Cut

Some hackathons ask for a short teaser in addition to the full demo. Cut to:
- Scene 1 opening hook (0:00–0:12)
- Scene 2 one-line demo + "root-caused in under a second" (0:30–0:45)
- Scene 4 rug-pull punchline (2:21–2:40)
- Scene 5 end card (2:55–3:00)

~28 seconds. Re-record separately — do not try to trim the 3:00 cut.
