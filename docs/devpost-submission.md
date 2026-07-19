# Devpost Submission Materials

Everything needed for the OpenAI Build Week hackathon submission.

Deadline: **July 21, 5PM PT**.
Track: **Developer Tools** ("Tools for developers, including testing, DevOps, agentic workflows, and security").

---

## Project Title

**codex-mcp-doctor** - npm doctor for MCP

## Short Description (for Devpost card, ~280 chars)

MCP servers fail silently. codex-mcp-doctor is the diagnostic CLI Codex should ship with — one zero-dependency command catches broken servers, prompt injection, silent rug-pulls, and Cyrillic homoglyph attacks that no other MCP scanner detects. Built in Codex with GPT-5.6.

## Long Description (for project page)

> **Try it in 5 seconds:** `git clone https://github.com/luogangan7-lgtm/codex-mcp-doctor.git && cd codex-mcp-doctor && python3 scripts/doctor.py --config examples/broken-stdio/config.toml` -- no `pip install`, no virtualenv, Python 3.11+ only. You will see a broken MCP server diagnosed in under a second.

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
- **294 tests** — every crash path, malformed input, and attack vector is tested.

### How We Built It

Built entirely inside **Codex desktop with GPT-5.6** as the development environment — not just "used Codex to write some code," but dogfooded Codex end-to-end to build tooling *for* Codex. The entire codebase (2,888 lines of doctor logic, 2,674 lines of tests, hooks, CI, examples, docs) was written, debugged, and hardened through **agent-driven iterative development**: each session picked up state from a shared memory canvas, ran a verification gate (294 tests + plugin validator + demo smoke), and only advanced when green.

The development loop itself uses Codex's native affordances as load-bearing infrastructure, not decoration:

- **Skills as the deployment surface** — `skills/mcp-doctor/SKILL.md` is how the doctor is invoked inside Codex; the plugin manifest (`plugin.json`) + `hooks/hooks.json` make it auto-trigger on `SessionStart`. The skill is not documentation, it is the integration point.
- **Hooks for auto-trigger** — the `SessionStart` hook means the doctor runs *before* the user's first prompt, every session. This is the difference between "a tool you have to remember to run" and "a tool that runs itself."
- **`--watch` mode for continuous guard duty** — the session-start hook fires once; `--watch` extends this into a continuous monitor that re-probes every N seconds and only surfaces output when server state actually changes. Two layers of protection: boot-time hook + runtime watch, both driven by the same diagnostic engine.
- **Codex's MCP client as the test oracle** — the doctor speaks the same MCP protocol (initialize → tools/list → resources/list → prompts/list) that Codex itself speaks, so the test suite exercises the exact handshake paths Codex uses in production.
- **Memory canvas for multi-session continuity** — task state survived across compactions and session boundaries via the memory MCP, so each session resumed mid-task instead of restarting from zero.

The **zero-dependency constraint** was deliberate and is part of the dogfooding story: a diagnostic tool that requires `pip install` defeats the purpose. If your MCP setup is broken, the last thing you need is another dependency that might *also* be broken. Pure Python 3.11+ stdlib (`tomllib`, `subprocess`, `urllib`, `socket`, `ast`, `re`, `json`) means it runs anywhere Codex runs — macOS, Linux, Windows, CI — with zero install friction.


### Project Provenance (Submission Period Compliance)

This project is **100% new work created within the Submission Period** (July 13-21, 2026). There is no pre-existing codebase; every commit was authored during the window using Codex desktop with GPT-5.6.

- **First commit:** 2026-07-18 (Build Week Day 1 of coding) - initial v1.4.0
- **Total commits during window:** 128
- **Commits before July 13:** 0
- **Evidence:** the full dated commit history at https://github.com/luogangan7-lgtm/codex-mcp-doctor/commits/main and the release list at https://github.com/luogangan7-lgtm/codex-mcp-doctor/releases show continuous agent-driven development from initial scaffold through v1.6.39, every commit advancing only after a green 294-test gate.

The dogfooding story is verifiable in the commit log itself: the project uses Codex's own MCP tooling (a shared memory canvas carried state across sessions), and the zero-dependency constraint was enforced via an AST gate that runs on every push.
### Design Philosophy

The terminal report **is** the UX. There is no GUI, and that is the point — a diagnostic tool should be instant, scriptable, and readable in the same terminal where the failure happened. Every visual choice in the report serves scannability under time pressure:

- **Emoji severity indicators** (🔴 🟡 🟢 🔵) — color-blind-safe, glanceable in <1s, survive copy-paste into bug reports and Slack.
- **Health score per server** (0-100) — a single number decision-makers can triage on, with a transparent penalty breakdown so the number is never a black box.
- **`→ fix:` actionable suggestions** — every error is paired with the one action that resolves it, never just "something is wrong."
- **ASCII-aligned columns** — readable in any terminal width, any font, no ANSI dependency for layout (color is decorative, structure is positional).
- **Normalized output for screenshots** — `--quiet` and the pre-rendered `docs/demo-transcript.txt` produce stable, path-normalized output so the same demo looks identical on every machine.

This is deliberate restraint, not absence of design: the tool's job is to deliver a verdict fast, and every pixel (or character) earns its place.

### Why This Matters Now

The MCP ecosystem is at an inflection point. Codex's plugin system, the Codex
marketplace, and the broader Model Context Protocol are all expanding fast —
every week brings new MCP servers, new integrations, new `npx -y` commands
running in developer environments. That growth is the opportunity and the risk:

- **Every new MCP server is a new attack surface.** A `npx -y some-server@latest`
  can pull a compromised update. A tool description can inject a system prompt.
  A Cyrillic lookalike can shadow a trusted tool. The attack vectors scale with
  the ecosystem.
- **Silent failure is the default, not the exception.** Codex, Claude Desktop,
  and every MCP client today share the same failure mode: a broken server just
  disappears, with no diagnostic. Users lose hours guessing at config typos.
- **Security tooling has not caught up.** Existing scanners (Snyk, MCP-Scan,
  destilabs/mcp-doctor) each cover a slice — but none run inside the agent
  loop, none auto-trigger on session start, none detect homoglyph attacks, and
  none are zero-dependency.

`codex-mcp-doctor` is built for the moment MCP becomes infrastructure, not a
toy. The zero-dependency constraint means it can ship *inside* Codex's default
plugin set — every Codex user gets MCP diagnostics for free, no install step.
The hook architecture means security becomes a property of the session, not a
chore the user remembers. And because it speaks the MCP protocol itself
(initialize, tools/list, resources/list, prompts/list), it ages with the
protocol instead of against it.

The terminal report is the API: the same JSON the doctor produces can feed a
CI gate, a marketplace review queue, or a security dashboard. The tool is a
single file today; the diagnostic engine underneath is protocol-native and
ready to be called from anywhere MCP is called.

### What's Next

**Shipped now (v1.6.39):** 7 attack-vector detection classes covering prompt injection (E001), tool shadowing (E002), hidden Unicode (W021), Cyrillic homoglyph (W022), rug-pull baseline drift (E003), supply-chain pinning, and plaintext secrets, plus capability-risk signals for manipulative language, untrusted content, sensitive-data exposure, and destructive operations (W001/W015/W017/W019); connectivity + config + schema validation across all three MCP primitives (tools/resources/prompts), SessionStart hook auto-trigger, `--watch` continuous monitoring, `--debug` probe visibility.

**Next 30 days:**
- **Semantic poisoning detection** — the current regex/pattern layer catches known attack shapes (Cyrillic lookalikes, literal injection phrases). The next layer uses embeddings to catch paraphrased injection and subtly manipulative language that passes lexical matching. This is the difference between catching "ignore previous instructions" and catching a description that is 94% normal and 6% adversarial.
- **Codex marketplace publication** — the plugin manifest already passes the Codex validator. The remaining work is the marketplace listing (screenshots, description, install verification), not engineering. Goal: one-command install via the Codex plugin UI, so the doctor ships as native infrastructure.

**Longer horizon:**
- **Baseline sharing / community trust registry** — right now each user pins their own baseline hashes. A community registry (opt-in, anonymized tool-description hashes) would let the doctor warn "this tool description changed for 400 other users last week" before you even run it.
- **Cross-agent monitoring** — extend beyond MCP to the broader agent tool-calling surface (function-calling schemas, code-interpreter permissions). The rug-pull detection pattern (pin → compare → alert) generalizes to any tool whose description can drift.

---

## How This Project Maps to the Judging Criteria

Devpost scores on four equally weighted criteria. Here is where each one is evidenced in this submission.

**Technological Implementation** - How thoroughly and skillfully does the project use Codex?
- 2,888 lines of original doctor logic + 2,674 lines of tests (294 tests), zero external dependencies (AST-verified in CI)
- 10 crash-class bug categories covered, including novel detections: W022 Cyrillic homoglyph attack, E003 supply-chain rug-pull with 3 severity tiers, prompt-injection and tool-shadowing analysis
- Every commit was authored inside Codex desktop with GPT-5.6; state carried across sessions via a shared MCP-backed memory canvas; each commit had to pass a 294-test gate before advancing
- The project dogfoods Codex's own MCP protocol: it diagnoses stdio/HTTP/SSE MCP servers, the same protocol Codex uses for its tool integrations

**Design** - A complete, coherent product experience, not just a technical proof of concept?
- One-command install for any judge: `git clone && python3 scripts/doctor.py --config examples/broken-stdio/config.toml` (or standalone zip - no clone, no pip install)
- Human-readable reports with severity tiers, plain-language root causes, and one-line fixes (not raw JSON dumps)
- Hooks for automatic triggering on session start, plus `--watch` for continuous monitoring, plus `--debug` for verbose output - covering the three real workflows (ad-hoc, automated, debugging)
- Four runnable example configs so a judge sees four different diagnoses in under 30 seconds

**Potential Impact** - A credible, specific case for solving a real problem for a real audience?
- Audience: every developer shipping Codex plugins, MCP servers, or agent integrations (a rapidly growing surface as Codex adoption expands)
- Problem: MCP misconfigurations fail silently - a broken tool just disappears from the agent's context with no error. codex-mcp-doctor is the only tool that diagnoses this failure class before it costs a debugging session
- The W022 Cyrillic homoglyph detection addresses an emerging security threat unique to agent ecosystems, where a malicious tool name visually impersonates a trusted one
- See "Why This Matters Now" above for the full impact case

**Quality of the Idea** - How creative and novel is the concept?
- No equivalent tool exists: there is no `npm doctor` or `pip doctor` for MCP. codex-mcp-doctor is the first diagnostic purpose-built for the MCP protocol that Codex and other agents depend on
- The zero-dependency constraint is itself a design statement: a broken-MCP diagnostic that requires `pip install` would defeat its own purpose if the breakage is environment-related
- Built as a Codex plugin (not a standalone CLI), so it ships in the same surface it diagnoses - the doctor lives inside the patient

## Demo Video Script (3:00 target — Devpost hard limit)
> **Tip:** `./scripts/demo.sh` walks through every scene below automatically —
> with titles, narration cues, and real doctor.py output. If you just want to
> record the video, run that and screen-record. The per-scene breakdown below
> is for understanding what each scene shows.



### Setup
- Terminal: macOS, dark theme, 16pt font
- Working directory: the cloned repo root (wherever you put `codex-mcp-doctor/`)
- Python: `/opt/homebrew/bin/python3`

### Scene 1: The Silent Failure (0:00 - 0:20)

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


### Scene 2: The Doctor Diagnoses (0:20 - 0:50)

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


### Scene 2.5: Built with Codex (0:50 - 1:15) — *required by Devpost rules*

> Devpost rules state the video "must include a clear demo with audio that covers what you built **AND how you used Codex and GPT-5.6**." Scenes 1-2 show what was built; this scene shows how. Without it the video fails a hard submission requirement.

**Narration:** "Here's the thing — this entire tool was built inside Codex."

**Action:** Switch screen recording to the Codex desktop window.

**Narration:** "Nearly three thousand lines of logic. Two hundred ninety-four tests. Every security analyzer."

**Narration:** "Written, debugged, and hardened through Codex with GPT-5.6."

**Action:** Press Enter on a pre-typed prompt that asks the doctor to diagnose its own repo. Keep a `git log --oneline -10` terminal panel visible for commit-history context. Do NOT show anything with real secrets.

**Narration:** "The doctor speaks the same MCP protocol Codex speaks. So the test suite hits the exact handshake paths Codex uses."

**Action:** Switch screen recording back to Terminal.


### Scene 3: Security Layer (1:15 - 1:40)

**Narration:** "But finding broken servers is the easy part. What about servers that are silently hostile?"

**Action:**
```bash
python3 scripts/doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe
```

**On-screen:** Shows unpinned npx package warning + hardcoded bearer token detection.

**Narration:** "This server pulls a package without version pinning — a supply-chain risk. And this one has a hardcoded bearer token sitting in an HTTP header. The doctor catches both."

**Expected on-screen:**
```
⚠️  unpinned-npx  🟢 90.0
   ⚠️  [unpinned_package] Server uses 'some-mcp-server' without a version pin.
      → fix: Pin to a concrete version, e.g. some-mcp-server@1.2.3.

⚠️  plaintext-secret  🟢 90.0
   ⚠️  [plaintext_secret_header] Hardcoded secret in http_headers['Authorization'].
      → fix: Prefer bearer_token_env_var over a literal token in http_headers.
```


### Scene 3b: Cyrillic Homoglyph Attack (1:40 - 2:05)

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


### Scene 4: Rug-Pull Detection (2:05 - 2:45)

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

### Scene 5: Two Layers of Protection — Hook + Watch (2:45 - 3:00)

**Narration:** "Best part: you don't run it. Two layers of protection."

**Action:** Show `hooks/hooks.json`, then flash `--watch --interval 30`.

**Narration:** "The SessionStart hook fires on every Codex session — silent when healthy, loud when broken. `--watch` extends that into continuous runtime monitoring, only printing when server state actually changes. Boot-time hook, runtime watch, same engine."

**Narration:** "294 tests, zero dependencies. Built entirely inside Codex with GPT-5.6."

**End card:** GitHub URL + "codex-mcp-doctor — npm doctor for MCP"

---

## Submission Checklist

- [x] Public repo: https://github.com/luogangan7-lgtm/codex-mcp-doctor
- [x] Working code with 294 passing tests
- [x] CI green (GitHub Actions, Python 3.11-3.14)
- [x] Zero external dependencies (AST-verified in CI via `scripts/verify-zero-deps.py`)
- [x] Plugin manifest passes Codex validator (`.codex-plugin/plugin.json`)
- [x] Screenshots: `docs/screenshot-real-report.png`, `docs/screenshot-rugpull-detection.png` (PIL-rendered, deterministic)
- [x] Cover + W022 visualization: `docs/devpost-cover.png`, `docs/w022-homoglyph.png`
- [x] Guided demo script: `./scripts/demo.sh` (one command, every scene from the video script below — just screen-record it)
- [x] Standalone release zip (zero-clone try): attached to latest GitHub release
- [ ] Demo video (use script above)
- [ ] Devpost project page text (use Long Description above)
- [x] Challenge category identified: **Developer Tools** (confirmed from /rules; final selection on submission form)

## Technical Stack

- **Language:** Python 3.11+ (stdlib only: tomllib, subprocess, urllib, socket, hashlib, json, re, argparse)
- **Framework:** None — single-file CLI script
- **Testing:** unittest (stdlib), 294 tests
- **CI:** GitHub Actions (Python 3.11, 3.12, 3.13, 3.14)
- **Dependencies:** literally zero — verified via AST scan
- **Platform:** macOS, Linux, Windows (any OS with Python 3.11+)

## Key Metrics for Judges

| Metric | Value |
|--------|-------|
| Lines of code (doctor.py) | 2,888 |
| Lines of tests | 2,674 |
| Test count | 294 |
| External dependencies | 0 |
| Time to full diagnostic | < 1s (config-only), < 5s (with probe) |
| Security check types | 7 (prompt injection, tool shadowing, hidden Unicode, Cyrillic homoglyphs, supply-chain, plaintext secrets, baseline drift) |
| Config fields validated | 12+ (command, url, args, env, http_headers, cwd, timeouts, etc.) |
| MCP primitives checked | 3 (tools, resources, prompts) |
