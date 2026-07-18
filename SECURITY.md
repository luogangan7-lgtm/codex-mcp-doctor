# Security Policy

## Why this file exists

`codex-mcp-doctor` is itself a security tool — it detects prompt injection,
tool shadowing, Cyrillic homoglyph attacks, rug-pulls (tool-description
mutation), supply-chain drift, and plaintext secrets in MCP configs. A
security tool without a security policy would defeat its own purpose.

## Reporting a vulnerability

**Do not open a public GitHub issue for security bugs.**

Email: open a private security advisory instead —
[GitHub Security Advisories](https://github.com/luogangan7-lgtm/codex-mcp-doctor/security/advisories/new).
This keeps the report private until a fix ships, and gives us a CVE if warranted.

Please include:
- A minimal `config.toml` + `mock_server.py` that reproduces the issue
- What the doctor reports vs. what it *should* report
- The doctor version (`python3 scripts/doctor.py --version`)
- Whether it is a false negative (missed a real bug) or a false positive
  (flagged something benign)

You should hear back within 72 hours. If not, ping via the OpenAI Build Week
Discord `#build-week-chat`.

## Scope

**In scope:**
- The doctor's detection logic — a class of attack the doctor claims to
  catch but does not (false negative), or a misclassification that
  undermines trust (false positive).
- Crashes triggered by malformed `config.toml` or a malicious server's
  probe response (the doctor must never crash on untrusted input — that
  is the same trust boundary it is diagnosing).

**Out of scope:**
- The MCP protocol itself — report upstream to the server vendor or the
  MCP spec repo, not here.
- Vulnerabilities in MCP servers that the doctor merely *detects* — the
  doctor is a diagnostic, not a patch layer.
- Theoretical attacks requiring an attacker who already has write access
  to your `config.toml` (at that point the doctor is not your problem).

## Threat model (what the doctor assumes)

The doctor reads `config.toml` and actively probes the servers listed
there. It assumes:

1. **The config file itself is trusted.** The doctor is a static +
   active-probe analyzer, not a filesystem guard. If an attacker can
   rewrite your `config.toml`, they can also just exfiltrate the secrets
   directly.
2. **Probe responses are untrusted.** Doctor parses JSON-RPC responses
   from live servers and treats them as hostile input — it never
   `exec`s a tool, never follows a URL in a tool description, never
   renders markdown from server output. The probe is read-only by
   construction.
3. **The baseline file is a trust anchor.** Rug-pull detection only
   works if the saved baseline was honest at save time. The doctor
   cannot protect you if the first run was already against a poisoned
   server.

## Disclosure policy

- Private advisory first, fix on a branch, release as a patch version.
- Public disclosure ships with the release that fixes it.
- We credit reporters in the CHANGELOG unless they ask to remain
  anonymous.

## What the doctor does *not* do

It is worth being explicit, because security theater helps no one:

- It does **not** block attacks. It reports them. The `SessionStart`
  hook and `--watch` mode surface findings, but enforcement is a
  human decision.
- It does **not** scan the network path between Codex and the MCP
  server — TLS interception, DNS poisoning, and MITM are out of scope.
  Run your own network-layer defenses.
- It does **not** verify that a server's *claimed* identity matches its
  source code. A server can report any version string it wants. The
  supply-chain check pins the declared version; it does not audit the
  binary.

If any of these gaps matter to you, layer another tool on top. The doctor
is one instrument in the panel, not the whole panel.
