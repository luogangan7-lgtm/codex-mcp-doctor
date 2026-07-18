# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.2] - 2026-07-18

### Fixed

- **`--check schema` never probed** - schema-only mode skipped the
  connectivity probe entirely, so it could never see tool definitions
  and never detected schema issues. It returned `config-ok` even on
  servers with broken schemas. Now schema mode probes and runs full
  schema validation (tools + resources + prompts).
- **`--check security` misreported `config-ok`** - after a successful
  probe with no security findings, servers were marked `config-ok`
  instead of `healthy`. The status logic only treated `all` and
  `connectivity` modes as probe-worthy. Now any mode that probed
  successfully reports `healthy` when clean.
- **Resource/prompt schema gaps in `--check schema`** - resource and
  prompt schema validation only ran in the cross-server security pass
  (`all`/`security` modes). `--check schema` now validates resource
  and prompt schemas in the per-server loop.

### Fixed

- **SSE parser returned wrong message** - when an SSE stream contained
  a notification before the actual RPC response, the parser returned the
  first valid JSON dict (the notification) instead of continuing to find
  the response with `result` or `error`. Now skips notifications and
  prefers RPC responses.
- **Empty config exit code** - empty config (0 servers, valid file)
  returned exit 2 ("config unreadable") instead of exit 3 ("no servers
  found"). The informational "no entries" message was treated as a
  config error. Now distinguishes parse errors from info messages.
- **Config-ok health score ignored issues** - servers with `config-ok`
  status (not probed) always scored 100, ignoring config-layer issues
  like unpinned packages, plaintext secrets, and invalid env types.
  Now applies per-issue penalties.

### Fixed

- **`const` property false positive** - a JSON Schema property using
  `const` without a `type` field triggered `property_missing_type`.
  `const` is a valid standalone constraint per JSON Schema spec.
- **E002 false positive on common words** - tool names that are also
  common English words (4-5 chars: `time`, `count`, `email`) triggered
  cross-server shadowing false positives when they appeared naturally
  in another server's tool description. Minimum name length raised
  from 4 to 6.

### Added

- 14 regression tests covering all above fixes (221 total).
- `--baseline-path` and `--quiet` flags documented in SKILL.md.

## [1.4.1] - 2026-07-18

### Fixed

- **Baseline silent-skip bug** - `--check-baseline` with a missing baseline
  file silently returned `[]` (exit 0, no output). Now returns an info-level
  message telling the user to run `--save-baseline` first.
- **Duplicate baseline-issue append** - server-level baseline issues were
  appended twice to `security_issues` due to a duplicated `if target:` block
  in `main()`.
- **Baseline-failure exit code** - high-severity baseline problems (corrupted
  /invalid file) now return exit code 2 instead of 0, so hooks notice that
  rug-pull detection silently failed.
- **Docker exec/build/create false positive** - `docker exec`, `docker build`,
  and `docker create` were flagged as unpinned images. Only `docker run` and
  `docker pull` fetch from a registry; others operate on local state.

### Added

- **property_missing_type schema check** - a tool property with no `type`
  and no `$ref`/`anyOf`/`oneOf`/`allOf` leaves the model unable to tell
  what value to pass. Now a warning.
- **object_no_properties schema check** - `type:object` with no properties,
  additionalProperties, or patternProperties is vacuous. Now a warning.
- **Deepened resource + prompt schema validation** - resources now also
  check for missing name/description; prompts check description,
  short-description, and argument structure (invalid/missing-name/
  missing-description). API change: both functions return
  `list[ToolSchemaIssue]` instead of single issue|None.
- **JSON-RPC error detection** - when a server returns a JSON-RPC error
  response (e.g. protocol-version-not-supported), the probe now reports
  an `rpc_error` issue instead of silently showing 'healthy but 0 tools'.
- **Pipe-through-curl exfiltration detection** - catches
  `pipe|feed|stream ... through|via curl|wget|nc` patterns that lack the
  `to <URL>` structure the old regex required.
- **curl/wget to suspicious hostnames** - catches `curl ... evil.com` /
  `curl ... attacker.io` where the hostname itself is the red flag.
- **Tool poisoning self-contradiction** - catches
  `actually deletes|removes|overwrites|destroys|wipes|formats` patterns
  where a tool description contradicts its claimed purpose.
- Synthetic test token replaced with a low-entropy fake to avoid tripping
  GitGuardian-style secret scanners (was a valid-format 36-char PAT).

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
- **Redundant latency warning on timeout** - when a server probe timed out,
  the latency check still ran (latency = timeout*1000 ms) and emitted an
  `elevated_latency` info issue alongside the `timeout` error. The latency
  note is now suppressed when a timeout issue is already present; high
  latency is implied by the timeout itself.
- 14 new tests (149 → 182 total).
- **Resource & prompt schema validation** - resources missing a URI and
  prompts missing a name are now flagged as schema errors (MCP spec
  violations). Previously only security-scanned, not structurally validated.
  New standalone functions validate_resource_schema / validate_prompt_schema.
- **Baseline corruption detection (E003)** - a corrupted, empty, or
  structurally invalid baseline file (valid JSON but not an object) no
  longer causes silent failure or a crash. check_baseline now returns a
  high-severity `baseline-unreadable` / `baseline-invalid-structure`
  warning so the user knows rug-pull detection is not active. The
  warning surfaces in the report header as a config-level error.
- **Credential-file-access detection (E001)** - tool descriptions referencing
  SSH private keys (`~/.ssh/id_rsa`, `id_ed25519`, `authorized_keys`, `config`),
  AWS credentials (`~/.aws/credentials`), GPG keys (`~/.gnupg/`), and `.env`
  files are now flagged as critical-severity credential theft. Bare mentions
  of `.ssh`/`.aws`/`.gnupg` in read/copy/backup contexts are also caught.
  3 new tests cover SSH-key theft, AWS-credential theft, and subtle webhook
  exfiltration (`append ... to webhook at URL`).

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
