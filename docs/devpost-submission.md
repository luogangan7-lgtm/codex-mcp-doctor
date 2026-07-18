# Devpost Submission Materials

Everything needed for the OpenAI Build Week hackathon submission.

Deadline: **July 21, 5PM PT**.

---

## Project Title

**codex-mcp-doctor** — `npm doctor` for MCP

## Short Description (for Devpost card, ~280 chars)

Zero-dependency MCP diagnostics for Codex. Detects broken servers, bad config, schema issues, prompt injection, tool shadowing, hidden Unicode attacks, rug-pull (tool-description mutation), supply-chain risks, and plaintext secrets — all in one `python3` command. Pure stdlib, auto-triggering via hooks.

## Long Description (for project page)

### The Problem

MCP servers fail silently. You add a server to `config.toml`, restart Codex, and... nothing. Tools don't appear. No error message. No log. You're left guessing: is the binary missing? Is the URL wrong? Is the API key expired? Did a package update break something?

Worse, MCP servers can be **silently hostile**: a tool description containing `<|im_start|>system` can hijack the model. A `filesystem_read` tool shadowed by a poisoned lookalike can exfiltrate data. A `npx -y pkg@latest` can pull a compromised update. And nobody checks — because there's no tool that does.

### What It Does

`codex-mcp-doctor` is a single-file Python script that diagnoses **every layer** of your MCP setup:

| Layer | What it checks |
|-------|---------------|
| L1 Connectivity | stdio process spawn + HTTP/SSE handshake (initialize → tools/list → resources/list → prompts/list) |
| L2 Config | path existence, executability, URL validity, env var references, timeout sanity |
| L2.5 Schema | missing descriptions, broken required fields, invalid JSON Schema types, property gaps |
| L3 Health Score | 0-100 per server with transparent penalty breakdown |
| L4 Security | prompt injection (E001), tool shadowing (E002), rug-pull/baseline drift (E003), manipulative language (W001), hidden Unicode (W021), Cyrillic homoglyphs (W022), capability risks (W015/017/019) |
| Supply Chain | unpinned npx/npm/uvx/pipx, docker images without sha256 digest |
| Secrets | plaintext API keys in env/headers/URLs (sk-*, ghp_*, AKIA*, mos_*, Bearer tokens, PEM keys) |

**Key differentiators:**
- **Zero dependencies** — pure Python 3.11+ stdlib (`tomllib`, `subprocess`, `urllib`, `socket`). No pip install. No virtualenv. Just `python3 scripts/doctor.py`.
- **Auto-triggering** — ships with a Codex hook (`hooks/hooks.json`) that runs diagnostics on `SessionStart`. If something breaks, you see it before your first prompt — not after 20 minutes of debugging.
- **All three MCP primitives** — checks tools, resources, *and* prompts (not just tools like most scanners).
- **Rug-pull detection** — first CLI implementation of tool-description pinning (Inspired by Invariant Labs' MCP-Scan, which is web-only).
- **266 tests** — every crash path, malformed input, and attack vector is tested.

### How We Built It

Built entirely with Codex desktop + GPT-5.6 as the development environment. The entire codebase — 2,725 lines of doctor logic, 2,371 lines of tests, hooks, CI, examples, docs — was written, debugged, and hardened through iterative agent-driven development.

The zero-dependency constraint was deliberate: a diagnostic tool that requires `pip install` defeats the purpose. If your MCP setup is broken, the last thing you need is another dependency that might also be broken.

### What's Next

- Semantic tool-poisoning detection (beyond regex patterns)
- Codex marketplace publication

---

## Demo Video Script (2-3 minutes)

### Setup
- Terminal: macOS, dark theme, 16pt font
- Working directory: `/Volumes/data/codex-mcp-doctor`
- Python: `/opt/homebrew/bin/python3`

### Scene 1: The Silent Failure (0:00 - 0:30)

**Narration:** "MCP servers fail silently. Here's what that looks like."

**Action:** Show a `config.toml` with a broken server, then start Codex and show tools not appearing.

**On-screen:**
```bash
cat examples/broken-stdio/config.toml
# Shows a config with command = "/usr/local/bin/nonexistent-mcp-server"
```

**Narration:** "No error. No log. Just... missing tools."


**Expected on-screen (the failure):**
```
[mcp_servers.broken-path]
command = "/usr/local/bin/nonexistent-mcp-server"
```
→ Codex starts, no error, but `tools/list` returns nothing. The user sees a working chat with zero MCP tools loaded. No log line tells them why.


### Scene 2: The Doctor Diagnoses (0:30 - 1:15)

**Narration:** "Run the doctor. One command, zero dependencies."

**Action:**
```bash
python3 scripts/doctor.py --config examples/broken-stdio/config.toml
```

**On-screen:** The full diagnostic report appears — red errors, root cause, fix suggestion.

**Narration:** "It tells you exactly what's wrong: the binary doesn't exist. And the second server crashes because a Python module is missing. Both root-caused in under a second."

**Expected on-screen (doctor output):**
```
❌ broken-path  🔴 0.0
   ❌ [command_not_found] Command path does not exist: /usr/local/bin/nonexistent-mcp-server
      → fix: Verify the path or reinstall the MCP server.

❌ broken-env  🔴 0.0
   ❌ [process_crashed] Server process exited with code 1.
      → fix: A Python dependency is missing.
      stderr: No module named my_missing_mcp_server
```
Both root-caused in under a second. Red error → exact cause → one-line fix suggestion.


### Scene 3: Security Layer (1:15 - 1:45)

**Narration:** "But finding broken servers is the easy part. What about servers that are silently hostile?"

**Action:**
```bash
python3 scripts/doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe
```

**On-screen:** Shows unpinned npx package warning + plaintext API key detection.

**Narration:** "This server pulls a package without version pinning — a supply-chain risk. And this one has a hardcoded API key in the config. The doctor catches both."

**Expected on-screen:**
```
⚠️  unpinned-npx  🟢 90.0
   ⚠️  [unpinned_package] Server uses 'some-mcp-server' without a version pin.
      → fix: Pin to a concrete version, e.g. some-mcp-server@1.2.3.

⚠️  plaintext-secret  🟢 90.0
   ⚠️  [plaintext_secret_header] Hardcoded secret in http_headers['Authorization'].
      → fix: Prefer bearer_token_env_var over a literal token in http_headers.
```


### Scene 3b: Cyrillic Homoglyph Attack (1:45 - 2:15)

**Narration:** "Here's a subtle attack: a tool named `fil\u0435system_read` — looks like `filesystem_read`, but the 'e' is Cyrillic."

**Action:**
```bash
python3 scripts/doctor.py --config examples/homoglyph-attack/config.toml
```

**On-screen:** W022 warning (high) — mixed-script word with Cyrillic lookalike U+0435, normalizes to 'filesystem_read'.

**Narration:** "The doctor probes the server, sees the tool name, and catches the impersonation. It even shows the normalized form — so you know exactly what the attacker was disguising."

**Expected on-screen:**
```
⚠️  poisoned-fs  🟡 50.0
   tools: filеsystem_read            ← the 'e' is Cyrillic U+0435
   security: 🔴 1 high
     🔴 [W022] Tool 'filеsystem_read' contains mixed-script word with Cyrillic
        lookalikes (U+0435). Normalizes to 'filesystem_read'.
        → fix: Replace Cyrillic lookalike characters with ASCII equivalents.
```
The normalized form `'filesystem_read'` is the punchline — the viewer instantly sees what the attacker was impersonating.


### Scene 4: Rug-Pull Detection (2:15 - 2:45)

**Narration:** "The most dangerous attack: a tool description that changes silently."

**Action:**
```bash
# Save baseline
python3 scripts/doctor.py --save-baseline

# Later: detect mutation
python3 scripts/doctor.py --check-baseline
```

**On-screen:** Shows baseline saved, then a simulated change detected.

**Narration:** "First run pins trusted descriptions. Later runs flag any tool whose description hash changed — a rug-pull attack. This is the first CLI tool to offer this; Invariant Labs' MCP-Scan is web-only."

### Scene 5: Auto-Triggering Hook (2:45 - 3:15)

**Narration:** "Best part: you don't even need to remember to run it."

**Action:** Show the hooks/hooks.json file, then start a new Codex session.

**On-screen:** The hook runs automatically on SessionStart.

**Narration:** "The hook runs on every session start. If your MCP setup is healthy, it's completely silent. If something broke, you see it immediately. 266 tests, zero dependencies, pure Python stdlib."

**End card:** GitHub URL + "codex-mcp-doctor — npm doctor for MCP"

---

## Submission Checklist

- [x] Public repo: https://github.com/luogangan7-lgtm/codex-mcp-doctor
- [x] Working code with 266 passing tests
- [x] CI green (GitHub Actions, Python 3.11-3.14)
- [x] Zero external dependencies (AST-verified)
- [x] Screenshots: `docs/screenshot-real-report.png`, `docs/screenshot-rugpull-detection.png`
- [ ] Demo video (use script above)
- [ ] Devpost project page text (use Long Description above)
- [ ] Select challenge category when announced (July 13)

## Technical Stack

- **Language:** Python 3.11+ (stdlib only: tomllib, subprocess, urllib, socket, hashlib, json, re, argparse)
- **Framework:** None — single-file CLI script
- **Testing:** unittest (stdlib), 266 tests
- **CI:** GitHub Actions (Python 3.11, 3.12, 3.13, 3.14)
- **Dependencies:** literally zero — verified via AST scan
- **Platform:** macOS, Linux, Windows (any OS with Python 3.11+)

## Key Metrics for Judges

| Metric | Value |
|--------|-------|
| Lines of code (doctor.py) | 2,725 |
| Lines of tests | 2,371 |
| Test count | 266 |
| External dependencies | 0 |
| Time to full diagnostic | < 1s (config-only), < 5s (with probe) |
| Security check types | 8 (injection, shadowing, rug-pull, Unicode, Cyrillic homoglyphs, supply-chain, secrets, capability) |
| Config fields validated | 12+ (command, url, args, env, http_headers, cwd, timeouts, etc.) |
| MCP primitives checked | 3 (tools, resources, prompts) |
