# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- 14 new tests (149 → 163 total).

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
