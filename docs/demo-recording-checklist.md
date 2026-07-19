# Pre-Recording Checklist

Run this before hitting record on the demo video. Five minutes of prep
saves a re-record.

## Environment

- [ ] **Close everything except Terminal, the Codex desktop window, and this
      checklist.** Slack, browser, editor — all closed. Notifications will
      ruin a take. The Codex desktop window is needed for Scene 2.5 (see below).
- [ ] **Do Not Disturb on.** System Settings → Notifications → Focus →
      Do Not Disturb. Or Control Center → toggle.
- [ ] **Desktop wallpaper clean.** Solid dark color preferred — judges
      see your whole screen, not just the terminal.
- [ ] **Second monitor or phone** with the voiceover script open. You
      cannot alt-tab to read the script mid-take without it showing.

## Terminal Setup

- [ ] **Terminal:** macOS Terminal.app or iTerm2, dark theme (Homebrew or
      similar). Light themes wash out the emoji severity colors.
- [ ] **Font size:** 18pt minimum. Judges watch on laptops, not 4K monitors.
      SF Mono, Menlo, or JetBrains Mono.
- [ ] **Window:** Full-screen or large enough that doctor output doesn't
      wrap awkwardly. Test by running `./scripts/demo.sh --no-pause` once.
- [ ] **Prompt:** Clean. `user@mac codex-mcp-doctor %` or similar. No
      custom ASCII art, no git status plugins that clutter the line.

## Sanity Checks (run all four before recording)

```bash
cd codex-mcp-doctor

# 1. Tests pass (must use -m unittest; running the file directly
#    invokes the doctor CLI, not the test suite)
python3 -m unittest tests.test_doctor 2>&1 | tail -3
# Expect: "Ran 294 tests ... OK"

# 2. Plugin manifest valid
python3 scripts/validate-plugin.py
# Expect: "OK: ... is a valid plugin manifest (codex-mcp-doctor v...)"

# 3. Demo runs end-to-end without prompts
./scripts/demo.sh --no-pause > /dev/null 2>&1; echo "exit=$?"
# Expect: exit=0

# 4. Python is the right version (needs 3.11+ for tomllib in stdlib)
python3 --version
# Expect: Python 3.11 or higher. If your default `python3` is older
#         (e.g. macOS system python3 is 3.9), use python3.11 / python3.12
#         explicitly, or install via homebrew/pyenv.

# 5. Doc metrics match ground truth (LOC, test count)
python3 scripts/check-metrics.py
# Expect: "OK: every numeric metric in active docs matches ground truth"

# 6. No stale version refs in docs
python3 scripts/check-stale-refs.py
# Expect: "OK: every current-release version ref in active docs == v..."
```

If any of the six fails, **stop and fix before recording.** A take that
crashes halfway is worse than no take.

## Scene 2.5 Prep (the one that will bite you)

Scene 2.5 (0:50-1:15) switches the screen recording from Terminal to the
Codex desktop window for 25 seconds. This is the easiest scene to ruin
because the recorder has to manage two windows under time pressure. Set
it up BEFORE hitting record:

- [ ] **Open a second Codex desktop window** with this repo loaded as the
      working directory. It should be open to a session where the repo
      context is visible.
- [ ] **Pre-type but do NOT send** the prompt: `diagnose this repo's own
      MCP setup`. Leave it in the input box, cursor at end, ready to
      press Enter at the 1:06 mark.
- [ ] **Open a terminal panel** (Codex's built-in or a split) running
      `git log --oneline -10` so the commit history is visible as
      secondary context. This shows the judges the depth of the project
      without you having to narrate it.
- [ ] **Redact or close anything with real secrets.** No real API keys,
      no tokens, no production config. If your Codex config has real
      credentials, use a throwaway config for the recording.
- [ ] **Practice the window switch.** Screen-record Terminal for Scenes
      1-2, switch to Codex desktop at 0:50, switch back at 1:13. The
      switch itself takes ~1s — account for it in your timing.
- [ ] **Position the two windows** so you can cmd-Tab between them
      cleanly. Don't rely on Mission Control mid-take.

If you forget any of the above, you will see it in playback and have to
re-record. This scene is required by Devpost rules — it cannot be cut.

## Audio

- [ ] **Mic:** Use a real mic if you have one — AirPods are fine, built-in
      MacBook mic is acceptable but not great. Avoid Bluetooth headsets
      with latency.
- [ ] **Room:** Quiet. No AC hum, no fridge, no traffic. 5 seconds of
      room tone recorded at the start makes editing easier.
- [ ] **Levels:** QuickTime shows input level — peaks around -12dB to
      -6dB when speaking normally. If it's hitting 0dB (red), turn down.

## Recording

- [ ] **Tool:** QuickTime Player → File → New Screen Recording → choose
      the Terminal window (not full screen if you want the end card as a
      separate clip). Or OBS if you prefer.
- [ ] **Resolution:** 1920×1080 minimum. 4K is overkill and makes the
      file huge. Devpost re-encodes anyway.
- [ ] **Format:** QuickTime default (.mov) is fine. YouTube accepts it.
- [ ] **Count in:** Leave 2 seconds of silence at the start before
      speaking. Easier to trim than to fix a clipped first word.

## After Recording

- [ ] **Watch it back at 1x.** Yes, the whole thing. Yes, even if you
      think it's fine. You will find a stumble.
- [ ] **Check total runtime.** Must be ≤3:00. If 3:01–3:05, trim a pause
      in Scene 2. If longer, re-record — do not speed up the audio.
- [ ] **Upload to YouTube as Public.** Unlisted will not be judged.
- [ ] **Thumbnail:** YouTube auto-generates one from the Terminal output.
      That's actually fine for this project — the report IS the product.
- [ ] **Caption the YouTube video.** Even auto-captions help judges who
      watch with sound off (many do).

## The One Thing That Will Go Wrong

Your first take will have a stumble around Scene 3b (the Cyrillic attack is
fiddly to explain live). Budget for three takes. The third take is almost
always the keeper.


## Appendix: Screen vs VO Cheat Sheet (print this, put it on screen 2)

The single most common re-record cause is the screen showing something the
mouth did not describe (or vice versa). This table lists, for every scene,
the exact command to type, the lines that MUST appear on screen, and the
VO keywords that must match them. Glance at this table at each scene
boundary while recording.

| Scene | Time | Type this | Screen MUST show | VO must say |
|-------|------|-----------|------------------|-------------|
| 1 | 0:00-0:20 | `cat examples/broken-stdio/config.toml` | the broken config text | "MCP servers fail silently" |
| 2 | 0:20-0:50 | `python3 scripts/doctor.py --config examples/broken-stdio/config.toml` | 2x `🔴 0.0`, `[command_not_found]`, `[process_crashed]` | "root-caused in under a second" |
| 2.5 | 0:50-1:15 | (switch to Codex window, Enter on pre-typed prompt) | Codex desktop + `git log --oneline -10` panel | "built inside Codex" + "Two hundred ninety-four tests" |
| 3 | 1:15-1:40 | `python3 scripts/doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe` | 2x `🟢 90.0`, `[unpinned_package]`, `[plaintext_secret_header]` | "seven classes" + "Two of them fire here" |
| 3b | 1:40-2:05 | `python3 scripts/doctor.py --config examples/homoglyph-attack/config.toml` | `🟡 50.0`, `[W022] ... Normalizes to 'filesystem_read'` | "Cyrillic" + "Normalizes to filesystem_read" |
| 4 | 2:05-2:45 | (run check-baseline step from `./scripts/demo.sh`) | 4 rows: 1x W022 high + 3x E003 (high/medium/low) | "three E003 tiers" (NOT "three findings" — there are 4 rows on screen) |
| 5 | 2:45-3:00 | (flash `hooks/hooks.json` + `--watch --interval 30`) | the hook JSON text | "Two layers of protection" + "Two hundred ninety-four tests" |

### Scene-by-scene gotchas

- **Scene 2:** both servers fail in under a second (sub-200ms total). The
  report appears instantly — read the VO at conversational pace, there is
  no crash-delay to wait for.
- **Scene 3:** the command MUST include `--check secrets --skip-probe`.
  Without those flags, the doctor live-probes fake hostnames and both
  servers crash with npx 404 + SSL errors, burying the two config-layer
  warnings. See voiceover script Scene 3 recording note.
- **Scene 3b:** the tool name on screen (`filеsystem_read`) looks identical
  to `filesystem_read` — that is the whole point. Do not try to "fix" it
  on camera. Say "the e is Cyrillic" and let the doctor's `Normalizes to`
  line do the reveal.
- **Scene 4:** four rows fire, not three. The VO correctly says "three
  E003 tiers" (there are three E003 rows). The fourth row is the W022
  from Scene 3b re-firing on the same config. See voiceover script Scene
  4 recording note. If you need a beat while the report renders, the
  ready-to-use line is: "the homoglyph from the last scene still lights
  up at the top".
- **Scene 5:** `--watch` is not actually run in the demo (it blocks). The
  VO mentions it; the screen just flashes the command text. Do not run it
  for real or the recording hangs.

### Numbers that must match across all surfaces

These appear in the VO, the submission, the README, and the checklist. If
any one of them drifts, a cross-reading judge will catch it:

- **Test count:** 294 (VO says "Two hundred ninety-four")
- **LOC:** 2,888 doctor + 2,776 tests
- **Commits in submission window:** 128 (since 2026-07-13)
- **Version:** v1.6.40 (or whatever the latest release tag is at record time)
- **Attack-vector classes:** 7 (E001/E002/W021/W022/E003/supply-chain/secrets)
- **E003 severity tiers:** 3 (high=changed, medium=new, low=removed)
- **Cyrillic confusables mapped:** 18
