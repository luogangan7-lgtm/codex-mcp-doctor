# codex-mcp-doctor examples

Each subdirectory contains a minimal `config.toml` that demonstrates a
specific MCP misconfiguration. Run the doctor against any of them:

```bash
python3 scripts/doctor.py --config examples/broken-stdio/config.toml
python3 scripts/doctor.py --config examples/broken-http/config.toml
```

Add `--json` for machine-readable output, or `--quiet` to suppress the
banner.

## Example set

| Directory          | What it demonstrates                                     |
|--------------------|----------------------------------------------------------|
| `broken-stdio/`    | A stdio server whose `command` binary does not exist     |
| `broken-http/`     | An HTTP/SSE server pointing at a dead `localhost` port   |

The companion `expected-output.txt` in each folder shows the canonical
report the doctor produces for that config, so you can diff your own
run against the reference.
