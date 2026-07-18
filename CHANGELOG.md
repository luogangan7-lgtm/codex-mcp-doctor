# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] — 2026-07-18

### Added

- **E003 Rug-Pull Detection** — `--save-baseline` stores a sha256 hash of each
  tool's `name + description`; `--check-baseline` flags any tool whose
  description changed since the baseline (high), new tools (medium), or removed
  tools (low). Baseline lives at `~/.codex/mcp-doctor-baseline.json`.
  Inspired by Invariant Labs' MCP-Scan; the first CLI implementation.
- **Supply-Chain Version Pinning (MCP04)** — `--check supply-chain` flags
  `npx`/`npm`/`uvx`/`pipx` commands with unpinned package versions and
  `docker run` images without a `@sha256:` digest or concrete `:tag`.
- **Plaintext Secrets Detection (NSA guidance)** — `--check secrets` scans
  `env`, `http_headers`, and URLs for hardcoded API keys (`sk-*`, `mos_*`,
  `AKIA*`, `ghp_*`, `xox*`, `AIza*`, PEM private keys, long Bearer tokens).
  `$VAR` / `${VAR}` references are correctly recognized and not flagged.
- **Latency Thresholds** — probe latency >15s produces a warning (-10 health
  score points); 5-15s produces an info note (-5 points).
- **Resource & Prompt Security Scanning** — E001/W001/W021 checks extended
  from tools only to also cover resources (URI + description) and prompts
  (description + argument descriptions). Issues are prefixed `resource:` /
  `prompt:`.
- `--baseline-path` option to override the baseline file location.

### Changed

- Health score now applies a latency penalty and an E003 rug-pull cap (max 50
  for high-severity description changes).
- `--check` accepts `supply-chain` and `secrets` in addition to `all`,
  `connectivity`, `schema`, `security`.
- 44 new tests (105 → 149 total).

## [1.3.0] — 2026-07-17

### Added

- **L4 Security Analysis** — scans every tool's name and description for:
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

## [1.2.0] — 2026-07-16

### Added

- **L2.6 Capabilities parsing** — extracts and reports the `capabilities`
  dict (tools/resources/prompts/logging/elicitation) and negotiated protocol
  version.
- **stdio notifications capture** — captures `notifications/*` messages during
  stdio probes.
- Codex-specific config field validation: `startup_timeout_sec`,
  `tool_timeout_sec`, `env` `$VAR` references, `http_headers` auth.

## [1.0.0] — 2026-07-15

### Added

- Initial release.
- L1 connectivity probes (stdio + HTTP/SSE) with full MCP handshake
  (initialize + tools/list + resources/list + prompts/list).
- L2 configuration correctness validation.
- L2.5 schema quality checks (7 issue types).
- L3 health score (0-100).
- Human-readable and JSON output formats.
