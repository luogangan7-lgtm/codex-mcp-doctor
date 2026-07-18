# codex-mcp-doctor examples

Each subdirectory contains a minimal `config.toml` that demonstrates a
specific MCP misconfiguration. Run the doctor against any of them:

```bash
python3 scripts/doctor.py --config examples/broken-stdio/config.toml
python3 scripts/doctor.py --config examples/broken-http/config.toml
python3 scripts/doctor.py --config examples/security-issues/config.toml --check secrets --skip-probe
python3 scripts/doctor.py --config examples/homoglyph-attack/config.toml
```

Add `--json` for machine-readable output, or `--quiet` to suppress the
banner.

## Example set

| Directory           | What it demonstrates                                      | Needs network? |
|---------------------|-----------------------------------------------------------|----------------|
| `broken-stdio/`     | A stdio server whose `command` binary does not exist      | No             |
| `broken-http/`      | An HTTP server pointing at a dead port (127.0.0.1:1)      | Local only     |
| `security-issues/`  | Unpinned packages + plaintext secrets in config           | No             |
| `homoglyph-attack/` | A mock server returning a Cyrillic lookalike tool name    | No (local mock) |

The companion `expected-output.txt` in each folder shows the canonical
report the doctor produces for that config, so you can diff your own
run against the reference. Values marked `<latency>` or `<python_path>`
vary by machine; all error types and messages are stable.
