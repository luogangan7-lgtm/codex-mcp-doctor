# Pre-Recording Checklist

Run this before hitting record on the demo video. Five minutes of prep
saves a re-record.

## Environment

- [ ] **Close everything except Terminal and this checklist.** Slack,
      browser, editor — all closed. Notifications will ruin a take.
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
cd /Volumes/data/codex-mcp-doctor

# 1. Tests pass
python3 tests/test_doctor.py | tail -3
# Expect: "Ran 285 tests ... OK"

# 2. Plugin manifest valid
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
# Expect: "Plugin validation passed"

# 3. Demo runs end-to-end without prompts
./scripts/demo.sh --no-pause > /dev/null 2>&1; echo "exit=$?"
# Expect: exit=0

# 4. Python is the right version (system python3 is 3.9, no tomllib)
which python3 && python3 --version
# Expect: /opt/homebrew/bin/python3 ... 3.11 or higher
```

If any of the four fails, **stop and fix before recording.** A take that
crashes halfway is worse than no take.

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
