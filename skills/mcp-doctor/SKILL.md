---
name: mcp-doctor
description: Diagnose MCP server health - connectivity, configuration correctness, schema quality, and security (prompt injection, tool poisoning, hidden Unicode, Cyrillic homoglyph attacks, tool shadowing, supply-chain pinning, plaintext secrets, rug-pull baseline). Zero dependencies, pure stdlib. Run when MCP tools are missing, broken, behaving unexpectedly, returning errors, when a new MCP server or plugin is installed, or to check for security risks in tool descriptions.
---

# MCP Doctor

Diagnose MCP server health - like `npm doctor` but for MCP. Zero external dependencies (pure Python 3.11+ stdlib). Checks **all three MCP primitives**: tools, resources, and prompts.

## When to Run This (Automatic Triggers)

Run this skill **without waiting for the user to ask** when any of these happen:

- **A tool that should exist is missing** from the available tools list.
- **A tool call fails** with a connection error, timeout, or "tool not found" error.
- **The user says** anything like: "my MCP is broken", "tools aren't working", "X is not responding", "MCP tools disappeared".
- **At session start** if you notice MCP servers are configured but their tools are absent.
- **The user asks** to check, diagnose, or troubleshoot their MCP setup.
- **A tool exists but behaves oddly** - schema issues may be the cause (missing descriptions, broken required fields).
- **A new MCP server or plugin is installed** - scan for prompt injection and tool shadowing before trusting it.
- **A tool behaves suspiciously** - it might contain hidden Unicode or injection patterns manipulating the model.
- **A tool's behavior changes subtly** - re-run `--check-baseline`; its description may have been silently mutated (rug-pull).
- **Config contains tokens or API keys** - run `--check secrets` to flag plaintext secrets that should be in environment variables.
- **A server uses `npx`/`uvx`/`docker run`** - run `--check supply-chain` to flag unpinned package versions and untagged docker images.

When in doubt, run it. It's fast (≤10s per server), read-only, and has zero side effects.

## How to Run

From the plugin root directory:

```bash
python3 scripts/doctor.py
```

> **Requires Python 3.11+** (uses `tomllib` from the stdlib). If `python3` on
> your system is older, use `python3.11`, `python3.12`, etc. instead. The
> SessionStart hook automatically probes for a compatible interpreter.

Auto-discovers `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`), parses all `[mcp_servers.*]` entries, validates config, probes each server, checks tool schemas, and reports a health score.

### Options

```bash
# Full diagnostic (default)
python3 scripts/doctor.py

# JSON output (for programmatic use)
python3 scripts/doctor.py --json

# Only check specific servers
python3 scripts/doctor.py --only humaux-memory node_repl

# Skip live probes, only validate config syntax
python3 scripts/doctor.py --skip-probe

# Run only connectivity checks (L1+L2, no schema analysis)
python3 scripts/doctor.py --check connectivity

# Run only schema quality checks (L2.5, requires probe)
python3 scripts/doctor.py --check schema

# Run only security analysis (L4: prompt injection, tool shadowing, hidden Unicode)
python3 scripts/doctor.py --check security

# v1.4: Save a trusted baseline of current tool-description hashes
python3 scripts/doctor.py --save-baseline

# v1.4: Detect rug-pull - flag any tool whose description changed since baseline
python3 scripts/doctor.py --check-baseline

# v1.4: Check only supply-chain version pinning (MCP04)
python3 scripts/doctor.py --check supply-chain

# v1.4: Check only plaintext secrets in config (NSA guidance)
python3 scripts/doctor.py --check secrets

# Custom timeout (default 10s)
python3 scripts/doctor.py --timeout 15

# Point to a different config file
python3 scripts/doctor.py --config /path/to/config.toml

# Custom baseline location (default: ~/.codex/mcp-doctor-baseline.json)
python3 scripts/doctor.py --check-baseline --baseline-path /custom/path.json

# Quiet mode — suppress output unless errors found (for hooks/automation)
python3 scripts/doctor.py --quiet
```

## Exit Codes (Why This Skill Has Teeth)

| Code | Meaning | Action |
|------|---------|--------|
| `0` | All servers healthy | Continue normally |
| `1` | Issues found (errors or warnings) | **Must report findings and suggested fixes to user** |
| `2` | Config file unreadable | Report that config.toml is broken |
| `3` | No MCP servers found | Inform user they have no servers configured |

Exit code 1 forces you to report the diagnostic results and the suggested fixes. Do not silently ignore a non-zero exit.

## What It Diagnoses

### L1 - Connectivity (Live Probe)

Probes **all three MCP primitives** in a single handshake:

- **stdio servers**: Spawns the process, sends `initialize` + `tools/list` + `resources/list` + `prompts/list`, checks responses.
- **HTTP/SSE servers**: Sends JSON-RPC requests, handles both plain HTTP and Server-Sent Events (Streamable HTTP) transports.
- Reports latency, server info (name + version), protocol version, tool/resource/prompt counts.
- Connection error root-cause analysis: DNS failure, connection refused, auth failure, timeout, SSL errors.

### L2 - Configuration Correctness

- Missing `command` (stdio) or `url` (http) fields.
- Command path doesn't exist, isn't executable, or isn't on PATH.
- Invalid URL scheme or missing host.
- `args` field that isn't a list.
- `cwd` directory that doesn't exist.
- `enabled = false` (reports as disabled, not an error).

**Codex-specific field validation (v1.2+)**:
- `startup_timeout_sec` - warns if <1s (too short) or >120s (blocks Codex startup).
- `tool_timeout_sec` - warns if <5s (kills I/O tools mid-execution).
- `env` with `$VAR` references - warns if the variable isn't set in your shell.
- `http_headers` - warns about missing `Authorization` on HTTPS API endpoints.

### L2.5 - Schema Quality (Tool Health)

Validates each tool's schema the way competitors (destilabs/mcp-doctor, mcp-probe) do:

- **Missing description** - tool has no description; model can't decide when to call it.
- **Short description** - under 10 chars, too vague for reliable tool selection.
- **Missing inputSchema** - no parameter schema at all.
- **Required field not in properties** - a required param doesn't exist (broken schema).
- **Invalid JSON type** - property type isn't a valid JSON Schema type.
- **Property missing description** - individual parameters lack descriptions.
- **Invalid schema structure** - properties/required not the right shape.

### L2.6 - Server Capabilities (v1.2+)

Extracts and reports the `capabilities` dict from each server's `initialize` response:
- Which primitives the server supports: tools, resources, prompts.
- Advanced features: logging, elicitation (MCP 2025-11-25 spec).
- Change notifications: `tools.listChanged`, `resources.listChanged`, `prompts.listChanged`.
- The negotiated protocol version (doctor advertises `2025-11-25`; server negotiates down if older).

### L3 - Health Score

Each server gets a 0-100 score combining:

- **50% connectivity**: did the probe return tools?
- **30% schema quality**: ratio of valid tool schemas.
- **20% description coverage**: ratio of tools with descriptions.

Score bands: 🟢 80+ (good) · 🟡 50-79 (fair) · 🔴 <50 (poor)

**v1.4 additions to the score**:
- Rug-pull (E003 high) caps the score at 50, like other high-severity findings.
- Latency >15s subtracts 10 points; >5s subtracts 5 points. Slow but functional servers no longer look pristine.

### stdio Notifications Capture (v1.2+)

During stdio probes, the doctor captures `notifications/*` messages emitted by the server (log messages, progress updates, list-changed events). These are reported as a count - a server emitting many log notifications during a simple handshake may indicate verbose logging or startup issues.

### L4 - Root Cause + Fix Suggestions

Every error includes a `fix` field with a concrete suggestion:

- Process crash → stderr analysis (missing deps, wrong paths, auth failures, port conflicts).
- Connection refused → tells you which host:port and suggests starting the server.
- Auth failure (401/403) → points to `http_headers` / API key.
- DNS failure → suggests checking hostname or network.
- Timeout → suggests checking downstream resources (DB, network, VPN).

## What It Does NOT Do

- Does not modify any config files (read-only).
- Does not install or start MCP servers.
- Does not call tools with arguments (only verifies listing + schema).
- Does not require any pip install - pure Python stdlib.

## After Running

1. **Exit 0**: report "All MCP servers healthy" and list tools/resources/prompts found + health scores.
2. **Exit 1**: for each issue, report the server name, error type, root cause, health score, and suggested fix. Group schema issues by server. Offer to help fix.
3. **Exit 2/3**: report the config-level problem.

## Security Analysis (L4)

The doctor scans every tool's name and description for security risks. This
protects against **tool poisoning** - a real attack where a malicious MCP
server's tool description contains hidden instructions that hijack the model.

### What It Detects

| Code | Severity | What |
|------|----------|------|
| **E001** | critical/high | **Prompt injection** - patterns like "ignore previous instructions", `<|im_start|>`, "send data to https://", "execute command:", role hijacking |
| **E002** | high | **Cross-server tool shadowing** - a tool description references a tool name from a *different* server, potentially overriding legitimate tools |
| **W001** | low/medium | **Manipulative language** - two-tier: high-confidence verbs (crucial, immediately, override, bypass, secretly) trigger on their own; common words (must, always, never, important) only trigger when >=3 appear clustered. Designed to minimize false positives on legitimate technical descriptions. |
| **W021** | medium/high | **Hidden Unicode** - zero-width spaces (U+200B), bidirectional overrides (U+202E), private-use chars, and Unicode Tag sequences (U+E0000–U+E007F) that encode invisible messages |
| **W015** | low | **Untrusted content** - tools that fetch/parse web content (prompt-injection entry point) |
| **W017** | low/medium | **Sensitive data exposure** - tools accessing credentials, tokens, financial data |
| **W019** | low/medium | **Destructive capabilities** - tools with delete/exec/destroy/rm operations |

### Health Score Impact

Security issues cap the achievable health score:
- **Critical** (E001 exfiltration/token injection) → max **20** (red zone)
- **High** (E001 override, E002 shadowing, W021 tag decode) → max **50** (yellow zone)
- **Medium/Low** → no score cap, but reported as a warning

This means a server with a well-formed schema but an active prompt-injection
pattern will show a low score - not a false "healthy" green.

## v1.4 - Extended Security & Supply Chain

v1.4 adds five new check layers, all aligned with the OWASP MCP Top 10
(2025 draft) and NSA AI security guidance. All are pure stdlib.

### E003 - Rug-Pull Detection (Tool Description Pinning)

Inspired by Invariant Labs' MCP-Scan. A "rug pull" is when a previously-trusted
tool silently changes its description to inject new malicious instructions.
The doctor stores a sha256 hash of each tool's `name + description` as a
baseline, then on subsequent runs flags any tool whose hash differs.

| Label | Severity | Trigger |
|-------|----------|---------|
| `tool-description-changed` | **high** | A tool's description hash differs from baseline |
| `new-tool-since-baseline` | medium | A tool appeared that wasn't in the baseline |
| `tool-removed-since-baseline` | low | A baseline tool is no longer listed |

Baseline is stored at `~/.codex/mcp-doctor-baseline.json`. Override with
`--baseline-path`. Workflow: install a new server → `--save-baseline` →
trust it → later run `--check-baseline` to detect silent mutations.

### Supply-Chain Version Pinning (MCP04)

Flags stdio commands that pull packages from registries without pinning:

- `npx`/`npm`/`pnpm`/`yarn`/`bunx`/`uvx`/`pipx` with a bare package name or
  `@latest`/`@next`/`@*` - a republished package can change behavior at any time.
- `docker run <image>` with no `@sha256:` digest and no concrete `:tag` (or
  `:latest`) - supply-chain risk.

Caret/tilde ranges (`@^1.2.3`, `@~1.2`) count as pinned. Scoped packages
(`@scope/pkg@1.2.3`) are handled correctly.

### Plaintext Secrets Detection (NSA Guidance)

Scans config for hardcoded secrets that should live in environment variables:

- `env` values matching known key shapes: `sk-*` (OpenAI), `mos_*` (humaux),
  `AKIA*` (AWS), `ghp_*`/`ghs_*` (GitHub), `xox*` (Slack), `AIza*` (Google),
  PEM private key blocks, and generic long Bearer tokens.
- `http_headers` values (e.g. `Authorization: Bearer <long-string>`).
- URLs with embedded credentials (`https://user:pass@host`).

`$VAR` and `${VAR}` references are correctly recognized as environment
variable indirections and not flagged.

### Latency Thresholds

| Latency | Severity | Score Impact |
|---------|----------|--------------|
| > 15s | warning (`high_latency`) | -10 points |
| 5-15s | info (`elevated_latency`) | -5 points |
| < 5s | none | none |

Servers that do heavy work during `tools/list` (e.g. embedding computation
on first call) will show elevated latency - this is informational, not a failure.

### Resource & Prompt Security Scanning

v1.3 only scanned **tool** descriptions for E001/W001/W021. v1.4 extends the
same checks to **resources** (URI + name + description) and **prompts**
(name + description + argument descriptions). Issues are prefixed
`resource:` or `prompt:` so you can tell which primitive was poisoned.
