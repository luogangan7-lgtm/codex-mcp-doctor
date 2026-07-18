#!/usr/bin/env python3
"""
codex-mcp-doctor: MCP server health diagnostics.
Pure stdlib, zero dependencies. Python 3.11+ (uses tomllib).

Exit codes (forces model to respond):
  0  - all servers healthy, no issues found
  1  - one or more servers have problems (details in output)
  2  - could not parse config / internal error
  3  - no MCP servers found to diagnose
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import socket
import ssl
import subprocess
import unicodedata
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ── tomllib (3.11+ stdlib); fall back gracefully on older Python ──
try:
    import tomllib
except ModuleNotFoundError:
    print("ERROR: Python 3.11+ required (tomllib not available).", file=sys.stderr)
    sys.exit(2)


# ═══════════════════════════════════════════════════════════════════════
# Data models
# ═══════════════════════════════════════════════════════════════════════

HEALTHY = "healthy"
WARNING = "warning"
ERROR = "error"
DISABLED = "disabled"

# Valid JSON Schema types (draft-07 core set)
VALID_JSON_TYPES = {
    "string", "number", "integer", "boolean", "array", "object", "null"
}

# Read-only tool name patterns - safe to actually call during probes
READONLY_TOOL_HINTS = (
    "list", "get", "search", "read", "fetch", "query", "status", "ping",
    "health", "info", "describe", "show", "view", "inspect", "browse",
)


# Module-level flag: set by main() when --debug is passed. Controls whether
# internal probe warnings (best-effort exceptions) are rendered in the report.
DEBUG = False


@dataclass
class ToolSchemaIssue:
    tool: str
    severity: str  # "error" | "warning"
    kind: str
    message: str
    fix: str = ""


@dataclass
class ProbeResult:
    """Raw results from a successful MCP probe (initialize + listing)."""
    tools: list[dict] = field(default_factory=list)
    resources: list[dict] = field(default_factory=list)
    prompts: list[dict] = field(default_factory=list)
    server_info: dict = field(default_factory=dict)
    protocol_version: str = ""
    capabilities: dict = field(default_factory=dict)
    notifications: list[dict] = field(default_factory=list)
    rpc_error: dict = field(default_factory=dict)  # JSON-RPC error response, if any
    probe_warnings: list[str] = field(default_factory=list)  # best-effort probe exceptions (debug)


@dataclass
class ServerResult:
    name: str
    transport: str          # "stdio" | "http" | "unknown"
    status: str             # HEALTHY | WARNING | ERROR | DISABLED
    tools_found: list[str] = field(default_factory=list)
    resources_found: list[str] = field(default_factory=list)
    prompts_found: list[str] = field(default_factory=list)
    server_info: dict = field(default_factory=dict)
    protocol_version: str = ""
    capabilities: dict = field(default_factory=dict)
    notifications_count: int = 0
    issues: list[dict] = field(default_factory=list)
    schema_issues: list[dict] = field(default_factory=list)
    security_issues: list[dict] = field(default_factory=list)
    health_score: float | None = None
    latency_ms: float | None = None
    raw_config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "transport": self.transport,
            "status": self.status,
            "tools_found": self.tools_found,
            "tool_count": len(self.tools_found),
            "resources_found": self.resources_found,
            "resource_count": len(self.resources_found),
            "prompts_found": self.prompts_found,
            "prompt_count": len(self.prompts_found),
            "server_info": self.server_info,
            "protocol_version": self.protocol_version,
            "capabilities": self.capabilities,
            "notifications_captured": self.notifications_count,
            "issues": self.issues,
            "schema_issues": self.schema_issues,
            "security_issues": self.security_issues,
            "health_score": self.health_score,
            "latency_ms": self.latency_ms,
        }


@dataclass
class DiagnosticsReport:
    config_path: str
    servers: list[ServerResult]
    total_issues: int = 0
    errors: int = 0
    warnings: int = 0
    config_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        healthy = sum(1 for s in self.servers if s.status == HEALTHY)
        config_ok = sum(1 for s in self.servers if s.status == "config-ok")
        scores = [s.health_score for s in self.servers if s.health_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        return {
            "config_path": self.config_path,
            "summary": {
                "total_servers": len(self.servers),
                "healthy": healthy,
                "config_ok": config_ok,
                "warnings": sum(1 for s in self.servers if s.status == WARNING),
                "errors": sum(1 for s in self.servers if s.status == ERROR),
                "disabled": sum(1 for s in self.servers if s.status == DISABLED),
                "total_issues": self.total_issues,
                "avg_health_score": avg_score,
            },
            "health_score": avg_score,
            "config_errors": self.config_errors,
            "servers": [s.to_dict() for s in self.servers],
        }


# ═══════════════════════════════════════════════════════════════════════
# Config discovery
# ═══════════════════════════════════════════════════════════════════════

def find_config() -> Path | None:
    """Find the Codex config.toml, checking CODEX_HOME then default."""
    candidates = []
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home) / "config.toml")
    candidates.append(Path.home() / ".codex" / "config.toml")
    for c in candidates:
        if c.exists():
            return c
    return None


def parse_config(config_path: Path) -> tuple[dict[str, dict], list[str]]:
    """Parse [mcp_servers.*] sections from config.toml.
    Returns (servers_dict, config_errors)."""
    errors: list[str] = []
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        return {}, [f"Failed to parse {config_path}: {e}"]

    raw_servers = data.get("mcp_servers", {})
    if not isinstance(raw_servers, dict):
        errors.append("[mcp_servers] is not a table")
        return {}, errors

    servers: dict[str, dict] = {}
    for name, cfg in raw_servers.items():
        if not isinstance(cfg, dict):
            errors.append(f"[mcp_servers.{name}] is not a table")
            continue
        servers[name] = cfg
    return servers, errors


def classify_transport(cfg: dict) -> str:
    """Determine if a server config is stdio or http."""
    if cfg.get("url"):
        return "http"
    if cfg.get("command"):
        return "stdio"
    return "unknown"


# ═══════════════════════════════════════════════════════════════════════
# Config validation (L2: correctness)
# ═══════════════════════════════════════════════════════════════════════

def validate_codex_config_fields(name: str, cfg: dict) -> list[dict]:
    """Check Codex-specific config fields that the MCP spec doesn't define
    but Codex's config.toml supports: startup_timeout_sec, tool_timeout_sec,
    env, http_headers. These are Codex extensions, not MCP protocol fields."""
    issues: list[dict] = []

    # startup_timeout_sec (default 10s in Codex)
    startup_timeout = cfg.get("startup_timeout_sec")
    if startup_timeout is not None:
        if not isinstance(startup_timeout, (int, float)) or isinstance(startup_timeout, bool):
            issues.append({
                "severity": "warning",
                "code": "invalid_startup_timeout",
                "message": f"startup_timeout_sec must be a number, got {type(startup_timeout).__name__}.",
                "fix": "Use: startup_timeout_sec = 10",
            })
        elif startup_timeout < 1:
            issues.append({
                "severity": "warning",
                "code": "startup_timeout_too_low",
                "message": f"startup_timeout_sec={startup_timeout} is very low; slow servers may not finish initializing.",
                "fix": "Use at least 5s for servers that fetch remote resources at startup.",
            })
        elif startup_timeout > 120:
            issues.append({
                "severity": "warning",
                "code": "startup_timeout_very_high",
                "message": f"startup_timeout_sec={startup_timeout} is very high; a stuck server will block Codex startup for {startup_timeout}s.",
                "fix": "Most servers start in <10s. Investigate why this server needs so long.",
            })

    # tool_timeout_sec
    tool_timeout = cfg.get("tool_timeout_sec")
    if tool_timeout is not None:
        if not isinstance(tool_timeout, (int, float)) or isinstance(tool_timeout, bool):
            issues.append({
                "severity": "warning",
                "code": "invalid_tool_timeout",
                "message": f"tool_timeout_sec must be a number, got {type(tool_timeout).__name__}.",
                "fix": "Use: tool_timeout_sec = 60",
            })
        elif tool_timeout < 5:
            issues.append({
                "severity": "warning",
                "code": "tool_timeout_too_low",
                "message": f"tool_timeout_sec={tool_timeout} is very low; tools doing I/O (DB, network, file ops) may get killed mid-execution.",
                "fix": "Use at least 30s for tools that touch the network or filesystem.",
            })

    # env: check for $VAR references that don't resolve
    env = cfg.get("env", {})
    if env and not isinstance(env, dict):
        issues.append({
            "severity": "error",
            "code": "invalid_env_type",
            "message": f"'env' must be a table (key=value pairs), got {type(env).__name__}.",
            "fix": "env must be a table of key=value pairs.",
        })
    elif isinstance(env, dict):
        for env_key, env_val in env.items():
            # Env values must be strings (MCP servers read them as strings).
            # Non-string values (int, list, dict) will cause Popen env to fail.
            if not isinstance(env_val, str) and not isinstance(env_val, bool):
                if isinstance(env_val, (int, float)):
                    issues.append({
                        "severity": "warning",
                        "code": "env_value_not_string",
                        "message": f"env.{env_key}={env_val!r} is a {type(env_val).__name__}; MCP servers expect string values.",
                        "fix": f"Quote the value: {env_key} = \"{env_val}\".",
                    })
                else:
                    issues.append({
                        "severity": "error",
                        "code": "env_value_not_string",
                        "message": f"env.{env_key} is a {type(env_val).__name__}; env values must be strings.",
                        "fix": f"Use a string value for {env_key}.",
                    })
                continue
            if isinstance(env_val, str) and env_val.startswith("$"):
                var_name = env_val[1:]
                # Also handle ${VAR} form
                if var_name.startswith("{") and var_name.endswith("}"):
                    var_name = var_name[1:-1]
                if var_name and var_name not in os.environ:
                    issues.append({
                        "severity": "warning",
                        "code": "env_var_not_set",
                        "message": f"env.{env_key}={env_val} but environment variable '{var_name}' is not set in your shell.",
                        "fix": f"Export {var_name} in your shell profile, or replace with the literal value.",
                    })

    # http_headers: must be a table if present
    http_headers = cfg.get("http_headers")
    if http_headers is not None and not isinstance(http_headers, dict):
        issues.append({
            "severity": "error",
            "code": "invalid_http_headers_type",
            "message": f"'http_headers' must be a table (key=value pairs), got {type(http_headers).__name__}.",
            "fix": "http_headers must be a table of key=value pairs.",
        })
    elif isinstance(http_headers, dict):
        # Header values must be strings (HTTP headers are always strings).
        for hdr_key, hdr_val in http_headers.items():
            if not isinstance(hdr_val, str):
                issues.append({
                    "severity": "warning",
                    "code": "header_value_not_string",
                    "message": f"http_headers.{hdr_key} is a {type(hdr_val).__name__}; header values must be strings.",
                    "fix": f"Quote the value: {hdr_key} = \"{hdr_val}\".",
                })

    return issues


def _check_http_auth_headers(name: str, cfg: dict) -> list[dict]:
    """Warn about missing auth headers for HTTP servers that likely need them."""
    issues: list[dict] = []
    url = cfg.get("url", "")
    http_headers = cfg.get("http_headers", {})

    if not isinstance(http_headers, dict):
        return issues

    has_auth = any(
        k.lower() in ("authorization", "proxy-authorization")
        for k in http_headers
    )

    # Heuristic: HTTPS URLs with API-like paths often need auth
    looks_like_api = any(p in url.lower() for p in ("/api/", "/v1/", "/rpc/"))
    is_https = url.lower().startswith("https://")

    if looks_like_api and is_https and not has_auth:
        # Check if bearer_token / bearer_token_env_var is set instead (Codex fields)
        has_bearer = "bearer_token" in cfg or "bearer_token_env_var" in cfg
        if not has_bearer:
            issues.append({
                "severity": "warning",
                "code": "missing_auth_header",
                "message": f"HTTP server URL looks like an API endpoint but no Authorization header or bearer_token is set.",
                "fix": "Add [mcp_servers." + name + ".http_headers] with Authorization header, or use bearer_token or bearer_token_env_var.",
            })

    return issues


def validate_stdio_config(name: str, cfg: dict) -> list[dict]:
    issues: list[dict] = []
    cmd = cfg.get("command", "")

    if not cmd:
        issues.append({
            "severity": "error",
            "code": "missing_command",
            "message": f"No 'command' field - stdio server needs an executable path.",
            "fix": f"Add: command = \"/path/to/your/mcp-server\" under [mcp_servers.{name}]",
        })
        return issues

    # Guard against non-string command values (list, int, etc.) that would
    # crash os.path.isabs() and subprocess.Popen with TypeError.
    if not isinstance(cmd, str):
        issues.append({
            "severity": "error",
            "code": "invalid_command_type",
            "message": f"'command' must be a string, got {type(cmd).__name__}: {repr(cmd)[:60]}",
            "fix": "Set command to a string path, e.g. command = \"/usr/bin/python3\".",
        })
        return issues

    if os.path.isabs(cmd):
        if not os.path.exists(cmd):
            issues.append({
                "severity": "error",
                "code": "command_not_found",
                "message": f"Command path does not exist: {cmd}",
                "fix": f"Verify the path or reinstall the MCP server. Check if the binary moved.",
            })
        elif not os.access(cmd, os.X_OK):
            issues.append({
                "severity": "error",
                "code": "command_not_executable",
                "message": f"Command exists but is not executable: {cmd}",
                "fix": f"Run: chmod +x \"{cmd}\"",
            })
    else:
        resolved = shutil.which(cmd)
        if not resolved:
            issues.append({
                "severity": "error",
                "code": "command_not_on_path",
                "message": f"Command '{cmd}' not found on PATH.",
                "fix": f"Install the package, or use an absolute path. Current PATH dirs checked.",
            })

    args = cfg.get("args")
    if args is not None and not isinstance(args, list):
        issues.append({
            "severity": "error",
            "code": "invalid_args",
            "message": f"'args' must be a list of strings, got {type(args).__name__}.",
            "fix": f"Use: args = [\"--flag\", \"value\"]",
        })

    cwd = cfg.get("cwd")
    if cwd is not None and not isinstance(cwd, str):
        issues.append({
            "severity": "error",
            "code": "invalid_cwd_type",
            "message": f"'cwd' must be a string, got {type(cwd).__name__}: {repr(cwd)[:60]}",
            "fix": "Set cwd to a string path, e.g. cwd = \"/path/to/dir\".",
        })
    elif cwd and not os.path.exists(os.path.expanduser(cwd)):
        issues.append({
            "severity": "warning",
            "code": "cwd_missing",
            "message": f"'cwd' directory does not exist: {cwd}",
            "fix": f"Create the directory or remove the cwd field.",
        })

    # Codex-specific config field checks
    issues.extend(validate_codex_config_fields(name, cfg))
    # v1.4: supply-chain (MCP04) + plaintext secrets (NSA)
    issues.extend(check_supply_chain(name, cfg))
    issues.extend(check_config_secrets(name, cfg))

    return issues


def validate_http_config(name: str, cfg: dict) -> list[dict]:
    issues: list[dict] = []
    url = cfg.get("url", "")

    if not url:
        issues.append({
            "severity": "error",
            "code": "missing_url",
            "message": f"No 'url' field - HTTP server needs an endpoint URL.",
            "fix": f"Add: url = \"https://your-server.com/mcp\" under [mcp_servers.{name}]",
        })
        return issues

    # Guard against non-string url values (list, int, etc.) that would
    # crash urlparse() with AttributeError.
    if not isinstance(url, str):
        issues.append({
            "severity": "error",
            "code": "invalid_url_type",
            "message": f"'url' must be a string, got {type(url).__name__}: {repr(url)[:60]}",
            "fix": "Set url to a string, e.g. url = \"https://your-server.com/mcp\".",
        })
        return issues

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        issues.append({
            "severity": "error",
            "code": "invalid_scheme",
            "message": f"URL scheme '{parsed.scheme}' is not http/https.",
            "fix": f"Use: url = \"https://...\" or \"http://...\"",
        })
    if not parsed.netloc:
        issues.append({
            "severity": "error",
            "code": "invalid_url",
            "message": f"URL has no host: {url}",
            "fix": "Provide a valid URL with host and path.",
        })

    # Codex-specific config field checks (timeouts, env)
    issues.extend(validate_codex_config_fields(name, cfg))
    # Auth header heuristic
    issues.extend(_check_http_auth_headers(name, cfg))
    # v1.4: plaintext secrets (NSA) - also scan URL + headers
    issues.extend(check_config_secrets(name, cfg))

    return issues


# ═══════════════════════════════════════════════════════════════════════
# Connectivity probes (L1) - stdio
# ═══════════════════════════════════════════════════════════════════════

def probe_stdio(cfg: dict, timeout: float = 10.0) -> tuple[ProbeResult, list[dict], float]:
    """Spawn the stdio MCP server, do full handshake (initialize + tools/list
    + resources/list + prompts/list). Returns (probe_result, issues, latency_ms)."""
    issues: list[dict] = []
    cmd = cfg["command"]
    args = cfg.get("args", [])
    if isinstance(args, str):
        args = [args]
    env = {**os.environ, **cfg.get("env", {})}
    cwd = cfg.get("cwd")
    if cwd and isinstance(cwd, str):
        cwd = os.path.expanduser(cwd)
    elif cwd and not isinstance(cwd, str):
        cwd = None  # non-string cwd already flagged in validation

    full_cmd = [cmd] + [str(a) for a in args]
    proc = None

    try:
        t0 = time.monotonic()
        proc = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd,
        )

        # Build the full handshake payload (one shot for simplicity + speed)
        payload_parts = [
            _jsonrpc("initialize", {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "mcp-doctor", "version": "1.1.0"},
            }, 1),
            _jsonrpc_notif("notifications/initialized", {}),
            _jsonrpc("tools/list", {}, 2),
            _jsonrpc("resources/list", {}, 3),
            _jsonrpc("prompts/list", {}, 4),
        ]
        payload = "\n".join(payload_parts) + "\n"

        stdout_data, stderr_data = proc.communicate(
            input=payload.encode(), timeout=timeout
        )
        latency = (time.monotonic() - t0) * 1000

        probe = _parse_stdio_responses(stdout_data.decode(errors="replace"))

        if probe.rpc_error:
            err = probe.rpc_error
            issues.append({
                "severity": "error",
                "code": "rpc_error",
                "message": f"Server returned JSON-RPC error {err.get('code','?')}: {err.get('message','?')}",
                "fix": "The server rejected the request. Check protocol version, auth, or server compatibility.",
            })

        if not probe.tools and proc.returncode != 0:
            stderr_text = stderr_data.decode(errors="replace").strip()
            issues.append({
                "severity": "error",
                "code": "process_crashed",
                "message": f"Server process exited with code {proc.returncode}.",
                "stderr": stderr_text[:500],
                "fix": _guess_fix_from_stderr(stderr_text),
            })
        elif not probe.tools and not probe.resources and not probe.prompts:
            stderr_text = stderr_data.decode(errors="replace").strip()
            issues.append({
                "severity": "warning",
                "code": "no_content_returned",
                "message": "Server responded but returned 0 tools, resources, or prompts.",
                "stderr": stderr_text[:300],
                "fix": "The server may be misconfigured internally. Check its logs.",
            })
        elif not probe.tools:
            stderr_text = stderr_data.decode(errors="replace").strip()
            issues.append({
                "severity": "info",
                "code": "resources_only",
                "message": f"Server exposes {len(probe.resources)} resource(s), {len(probe.prompts)} prompt(s), 0 tools.",
                "stderr": stderr_text[:300],
                "fix": "Valid per MCP spec. No action needed unless you expected tools.",
            })

        return probe, issues, round(latency, 1)

    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            proc.communicate()
        issues.append({
            "severity": "error",
            "code": "timeout",
            "message": f"Server did not respond within {timeout}s.",
            "fix": "Check if the server is waiting on a resource (DB, network, auth) or increase startup_timeout_sec.",
        })
        return ProbeResult(), issues, timeout * 1000

    except FileNotFoundError:
        issues.append({
            "severity": "error",
            "code": "command_not_found",
            "message": f"Cannot execute: {cmd}",
            "fix": "Verify the command path or install the MCP server.",
        })
        return ProbeResult(), issues, 0

    except Exception as e:
        issues.append({
            "severity": "error",
            "code": "probe_failed",
            "message": f"Unexpected error during probe: {type(e).__name__}: {e}",
            "fix": "Check server compatibility with MCP protocol.",
        })
        return ProbeResult(), issues, 0


# ═══════════════════════════════════════════════════════════════════════
# Connectivity probes (L1) - HTTP / SSE
# ═══════════════════════════════════════════════════════════════════════

def probe_http(cfg: dict, timeout: float = 10.0) -> tuple[ProbeResult, list[dict], float]:
    """Probe an HTTP or SSE MCP server via full handshake."""
    issues: list[dict] = []
    url = cfg["url"]
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    http_headers = cfg.get("http_headers", {})
    headers.update(http_headers)
    headers.setdefault("User-Agent", "codex-mcp-doctor/1.1")

    # Codex supports bearer_token / bearer_token_env_var as shorthand for
    # http_headers.Authorization. Resolve them so the probe authenticates.
    if "Authorization" not in headers:
        bearer = cfg.get("bearer_token")
        if bearer is None and cfg.get("bearer_token_env_var"):
            bearer = os.environ.get(cfg["bearer_token_env_var"])
            if bearer is None:
                bearer = os.environ.get(cfg["bearer_token_env_var"].lstrip("$"))
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname:
        try:
            socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            issues.append({
                "severity": "error",
                "code": "dns_failure",
                "message": f"DNS resolution failed for {hostname}.",
                "fix": "Check the URL hostname for typos, or your DNS/network.",
            })
            return ProbeResult(), issues, 0

    try:
        t0 = time.monotonic()

        def remaining() -> float:
            """Remaining time budget so sequential RPCs share one timeout."""
            return max(1.0, timeout - (time.monotonic() - t0))

        init_resp = _http_rpc(url, "initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "mcp-doctor", "version": "1.1.0"},
        }, headers, remaining())

        _http_notify(url, "notifications/initialized", {}, headers, remaining())

        probe = ProbeResult()
        # Capture JSON-RPC error if the server returned one instead of a result
        if isinstance(init_resp.get("error"), dict):
            probe.rpc_error = init_resp["error"]
        _raw_result = init_resp.get("result", {})
        init_result = _raw_result if isinstance(_raw_result, dict) else {}
        probe.server_info = init_result.get("serverInfo", {})
        probe.protocol_version = init_result.get("protocolVersion", "")
        probe.capabilities = init_result.get("capabilities", {}) if isinstance(init_result.get("capabilities"), dict) else {}

        # tools/list
        tools_resp = _http_rpc(url, "tools/list", {}, headers, remaining())
        probe.tools = _extract_items_from_rpc(tools_resp, "tools")

        # resources/list (best-effort - not all servers support it)
        try:
            res_resp = _http_rpc(url, "resources/list", {}, headers, remaining())
            probe.resources = _extract_items_from_rpc(res_resp, "resources")
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404, 405, 501):
                raise
        except Exception as e:
            probe.probe_warnings.append(f"resources/list best-effort failed: {type(e).__name__}: {e}")

        # prompts/list (best-effort)
        try:
            pr_resp = _http_rpc(url, "prompts/list", {}, headers, remaining())
            probe.prompts = _extract_items_from_rpc(pr_resp, "prompts")
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404, 405, 501):
                raise
        except Exception as e:
            probe.probe_warnings.append(f"prompts/list best-effort failed: {type(e).__name__}: {e}")

        latency = (time.monotonic() - t0) * 1000

        if probe.rpc_error:
            err = probe.rpc_error
            issues.append({
                "severity": "error",
                "code": "rpc_error",
                "message": f"Server returned JSON-RPC error {err.get('code','?')}: {err.get('message','?')}",
                "fix": "The server rejected the request. Check protocol version, auth, or server compatibility.",
            })

        if not probe.tools and not probe.resources and not probe.prompts:
            issues.append({
                "severity": "warning",
                "code": "no_content_returned",
                "message": "Server connected but returned 0 tools, resources, or prompts.",
                "fix": "The server may be starting up or misconfigured. Retry or check server logs.",
            })
        elif not probe.tools:
            # resources-only or prompts-only server — valid per MCP spec
            issues.append({
                "severity": "info",
                "code": "resources_only",
                "message": f"Server exposes {len(probe.resources)} resource(s), {len(probe.prompts)} prompt(s), 0 tools.",
                "fix": "Valid per MCP spec. No action needed unless you expected tools.",
            })

        return probe, issues, round(latency, 1)

    except urllib.error.HTTPError as e:
        latency = (time.monotonic() - t0) * 1000 if 't0' in locals() else 0
        body = ""
        try:
            body = e.read().decode(errors="replace")[:300]
        except Exception as be:
            # Non-fatal: body is only used for diagnostic context in the error message.
            body = f"<unreadable body: {type(be).__name__}>"
        if e.code in (401, 403):
            issues.append({
                "severity": "error",
                "code": "auth_failed",
                "message": f"Authentication failed: HTTP {e.code}.",
                "body": body,
                "fix": f"Check http_headers - your API key or Bearer token may be invalid or expired.",
            })
        else:
            issues.append({
                "severity": "error",
                "code": "http_error",
                "message": f"HTTP {e.code}: {e.reason}",
                "body": body,
                "fix": f"The server is reachable but returned an error. Check the URL and server health.",
            })
        return ProbeResult(), issues, latency

    except urllib.error.URLError as e:
        latency = (time.monotonic() - t0) * 1000 if 't0' in locals() else 0
        reason = e.reason
        if isinstance(reason, ConnectionRefusedError):
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            issues.append({
                "severity": "error",
                "code": "connection_refused",
                "message": f"Connection refused to {host}:{port}.",
                "fix": f"The server is not running or not listening on that port. Verify the URL or start the server.",
            })
        elif isinstance(reason, socket.timeout):
            issues.append({
                "severity": "error",
                "code": "timeout",
                "message": f"Connection timed out after {timeout}s.",
                "fix": "The server is unreachable or too slow. Check network/firewall/VPN.",
            })
        elif "Name or service not known" in str(reason) or "nodename nor servname" in str(reason):
            issues.append({
                "severity": "error",
                "code": "dns_failure",
                "message": f"DNS resolution failed for {parsed.hostname}.",
                "fix": "Check the URL hostname for typos, or your DNS/network.",
            })
        elif isinstance(reason, ssl.SSLError) or "SSL" in str(reason):
            issues.append({
                "severity": "error",
                "code": "ssl_error",
                "message": f"SSL/TLS error: {reason}",
                "fix": "The server may not support HTTPS, has an invalid certificate, or is not actually an HTTPS endpoint. Try http:// if appropriate, or check the certificate.",
            })
        else:
            issues.append({
                "severity": "error",
                "code": "connection_error",
                "message": f"Connection error: {reason}",
                "fix": "Check network connectivity, URL, and server status.",
            })
        return ProbeResult(), issues, latency

    except json.JSONDecodeError as e:
        latency = (time.monotonic() - t0) * 1000 if 't0' in locals() else 0
        issues.append({
            "severity": "error",
            "code": "invalid_response",
            "message": f"Server returned a non-JSON response (not an MCP server). Parse error at pos {e.pos}.",
            "fix": "The URL may not point to an MCP server endpoint. Verify it serves JSON-RPC over HTTP.",
        })
        return ProbeResult(), issues, round(latency, 1) if latency else 0
    except Exception as e:
        issues.append({
            "severity": "error",
            "code": "probe_failed",
            "message": f"Unexpected error: {type(e).__name__}: {e}",
            "fix": "Check server compatibility or report a bug.",
        })
        return ProbeResult(), issues, 0


# ═══════════════════════════════════════════════════════════════════════
# JSON-RPC helpers
# ═══════════════════════════════════════════════════════════════════════

def _jsonrpc(method: str, params: dict, msg_id: int) -> str:
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": msg_id,
    })


def _jsonrpc_notif(method: str, params: dict) -> str:
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    })


def _http_rpc(url: str, method: str, params: dict, headers: dict, timeout: float) -> dict:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }).encode()
    headers.setdefault("User-Agent", "codex-mcp-doctor/1.1")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        ct = resp.headers.get("Content-Type", "")
        # SSE / Streamable HTTP: response may be event-stream frames
        if "text/event-stream" in ct or "data: " in raw:
            return _parse_sse_payload(raw)
        return json.loads(raw)


def _http_notify(url: str, method: str, params: dict, headers: dict, timeout: float) -> None:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }).encode()
    headers.setdefault("User-Agent", "codex-mcp-doctor/1.1")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()


def _parse_sse_payload(raw: str) -> dict:
    """Parse a Server-Sent Events payload and return the RPC response.

    Handles both `data: {...}` framed responses (Streamable HTTP transport)
    and plain JSON fallbacks. MCP servers using SSE wrap each JSON-RPC message
    in an event frame; we extract the response containing a result or error,
    skipping notifications (which only have a method field).
    """
    fallback: dict = {}
    for block in raw.split("\n\n"):
        data_lines = []
        for line in block.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            candidate = "\n".join(data_lines)
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    # Prefer RPC responses (have result or error) over
                    # notifications (only have method). SSE streams may
                    # contain notifications before the actual response.
                    if "result" in obj or "error" in obj:
                        return obj
                    if not fallback:
                        fallback = obj
            except json.JSONDecodeError:
                continue
    if fallback:
        return fallback
    # Fallback: try the whole thing as JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    return {}


def _parse_stdio_responses(stdout: str) -> ProbeResult:
    """Parse multi-message stdout from a stdio server into a ProbeResult."""
    probe = ProbeResult()
    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:
            # Capture notifications/* messages (log, progress, listChanged, etc.)
            method = msg.get("method", "")
            if method.startswith("notifications/"):
                probe.notifications.append({
                    "method": method,
                    "params": msg.get("params", {}),
                })
            continue
        # JSON-RPC error response: server explicitly returned an error
        if "error" in msg:
            probe.rpc_error = msg["error"]
            continue
        result = msg.get("result", {})
        if not isinstance(result, dict):
            continue
        mid = msg["id"]
        if mid == 1:
            probe.server_info = result.get("serverInfo", {})
            probe.protocol_version = result.get("protocolVersion", "")
            probe.capabilities = result.get("capabilities", {}) if isinstance(result.get("capabilities"), dict) else {}
        elif mid == 2:
            _items = result.get("tools", [])
            probe.tools = _items if isinstance(_items, list) else []
        elif mid == 3:
            _items = result.get("resources", [])
            probe.resources = _items if isinstance(_items, list) else []
        elif mid == 4:
            _items = result.get("prompts", [])
            probe.prompts = _items if isinstance(_items, list) else []
    return probe


def _extract_items_from_rpc(resp: dict, key: str) -> list[dict]:
    """Extract item list from a JSON-RPC response dict."""
    result = resp.get("result", {})
    items = result.get(key, [])
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict)]


def _guess_fix_from_stderr(stderr: str) -> str:
    """Heuristic: guess the fix from common stderr patterns."""
    s = stderr.lower()
    if "connection refused" in s or "econnrefused" in s:
        return "A downstream service (DB, Redis, etc.) is not running. Check if required services are up."
    if "no module named" in s or "modulenotfound" in s:
        return "A Python dependency is missing. Reinstall the MCP server in its virtualenv."
    if "cannot find module" in s or "err_module_not_found" in s or ("require" in s and "is not defined" in s):
        return "A Node.js dependency is missing. Run 'npm install' in the server directory or reinstall the package."
    if "syntaxerror" in s and ".ts" in stderr.lower():
        return "TypeScript compilation error. Check for syntax issues or run 'npm run build'."
    if "no such file or directory" in s:
        return "A required file or binary is missing. Check paths in the server config."
    if "permission denied" in s:
        return "Permission issue. Check file permissions or run with appropriate privileges."
    if "eaddrinuse" in s or "address already in use" in s:
        return "Port conflict. Another process is using the same port."
    if "auth" in s or "unauthorized" in s or "api key" in s or "token" in s:
        return "Authentication failed. Check your API key or token in env/http_headers."
    return "Inspect the stderr output for clues. Common causes: missing deps, wrong paths, auth failures."


# ═══════════════════════════════════════════════════════════════════════
# Schema quality validation (L2.5)
# ═══════════════════════════════════════════════════════════════════════

def validate_tool_schema(tool: dict) -> list[ToolSchemaIssue]:
    """Check a single tool's schema quality. Returns issues found.

    Inspired by destilabs/mcp-doctor and mcp-probe: validates that tools
    have descriptions, valid inputSchema, and well-formed required fields.
    """
    issues: list[ToolSchemaIssue] = []
    name = tool.get("name", "<unnamed>")

    # 1. Missing description
    desc = tool.get("description", "")
    if not desc or not str(desc).strip():
        issues.append(ToolSchemaIssue(
            tool=name, severity="warning", kind="missing_description",
            message=f"Tool '{name}' has no description. Models can't decide when to call it.",
            fix="Add a 'description' field explaining what the tool does and when to use it.",
        ))
    elif len(str(desc).strip()) < 10:
        issues.append(ToolSchemaIssue(
            tool=name, severity="warning", kind="short_description",
            message=f"Tool '{name}' description is very short ({len(str(desc).strip())} chars).",
            fix="Expand the description so a model can reliably pick this tool.",
        ))

    schema = tool.get("inputSchema")
    if schema is None:
        issues.append(ToolSchemaIssue(
            tool=name, severity="warning", kind="missing_input_schema",
            message=f"Tool '{name}' has no inputSchema.",
            fix="Add an inputSchema (JSON Schema) describing the tool's parameters.",
        ))
        return issues

    if not isinstance(schema, dict):
        issues.append(ToolSchemaIssue(
            tool=name, severity="error", kind="invalid_schema_type",
            message=f"Tool '{name}' inputSchema is not an object (got {type(schema).__name__}).",
            fix="inputSchema must be a JSON Schema object.",
        ))
        return issues

    props = schema.get("properties", {})
    if not isinstance(props, dict):
        issues.append(ToolSchemaIssue(
            tool=name, severity="error", kind="invalid_properties",
            message=f"Tool '{name}' inputSchema.properties is not an object.",
            fix="Set properties to a JSON object mapping param names to their schemas.",
        ))
        props = {}

    required = schema.get("required", [])
    if not isinstance(required, list):
        issues.append(ToolSchemaIssue(
            tool=name, severity="error", kind="invalid_required",
            message=f"Tool '{name}' inputSchema.required is not a list.",
            fix="Set required to a list of parameter names.",
        ))
        required = []

    # 2. Each required field must exist in properties
    for req_field in required:
        if req_field not in props:
            issues.append(ToolSchemaIssue(
                tool=name, severity="error", kind="required_not_in_properties",
                message=f"Tool '{name}': required field '{req_field}' is not in properties.",
                fix=f"Add '{req_field}' to properties or remove it from required.",
            ))

    # 2b. object type with no properties and no additionalProperties is vacuous
    schema_type = schema.get("type")
    if (schema_type == "object" and not props
            and not schema.get("additionalProperties")
            and not schema.get("patternProperties")):
        issues.append(ToolSchemaIssue(
            tool=name, severity="warning", kind="object_no_properties",
            message=f"Tool '{name}' inputSchema is type 'object' but declares no "
                    f"properties, additionalProperties, or patternProperties.",
            fix="Either list the expected parameters under 'properties', or set "
                "'additionalProperties: true' if the tool accepts arbitrary keys.",
        ))

    # 3. Each property should have a type and ideally a description
    for prop_name, prop_schema in props.items():
        if not isinstance(prop_schema, dict):
            issues.append(ToolSchemaIssue(
                tool=name, severity="error", kind="invalid_property_schema",
                message=f"Tool '{name}' property '{prop_name}' is not a schema object.",
                fix=f"Define '{prop_name}' as a JSON Schema object.",
            ))
            continue

        ptype = prop_schema.get("type")
        if ptype and ptype not in VALID_JSON_TYPES:
            issues.append(ToolSchemaIssue(
                tool=name, severity="error", kind="invalid_type",
                message=f"Tool '{name}' property '{prop_name}' has invalid type '{ptype}'.",
                fix=f"Use one of: {', '.join(sorted(VALID_JSON_TYPES))}.",
            ))
        elif not ptype and not any(
            k in prop_schema for k in ("$ref", "anyOf", "oneOf", "allOf", "const")
        ):
            # No type and no composition keyword - the model can't tell what
            # kind of value to pass. Skip if a composition keyword or const is
            # present (those are valid JSON Schema alternatives to a flat type).
            issues.append(ToolSchemaIssue(
                tool=name, severity="warning", kind="property_missing_type",
                message=f"Tool '{name}' property '{prop_name}' has no type "
                        f"(and no $ref/anyOf/oneOf/allOf/const).",
                fix=f"Add a 'type' to '{prop_name}' (e.g. string, number, boolean, array, object).",
            ))

        pdesc = prop_schema.get("description", "")
        if not pdesc or not str(pdesc).strip():
            issues.append(ToolSchemaIssue(
                tool=name, severity="warning", kind="property_missing_description",
                message=f"Tool '{name}' property '{prop_name}' has no description.",
                fix=f"Add a description to '{prop_name}' so the model knows what to pass.",
            ))

        # 4. type-specific schema completeness
        if ptype == "array" and "items" not in prop_schema:
            issues.append(ToolSchemaIssue(
                tool=name, severity="warning", kind="array_missing_items",
                message=f"Tool '{name}' property '{prop_name}' is an array without 'items' schema.",
                fix=f"Add 'items' to '{prop_name}' so the model knows the element type.",
            ))
        enum_val = prop_schema.get("enum")
        if enum_val is not None and not isinstance(enum_val, list):
            issues.append(ToolSchemaIssue(
                tool=name, severity="error", kind="invalid_enum",
                message=f"Tool '{name}' property '{prop_name}' enum is not a list (got {type(enum_val).__name__}).",
                fix=f"Set enum to a list of allowed values for '{prop_name}'.",
            ))

    return issues


def schema_issues_to_dicts(issues: list[ToolSchemaIssue]) -> list[dict]:
    return [
        {
            "tool": i.tool,
            "severity": i.severity,
            "kind": i.kind,
            "code": i.kind,
            "message": i.message,
            "fix": i.fix,
        }
        for i in issues
    ]


# ═══════════════════════════════════════════════════════════════════════
# Security analysis (L4) - prompt injection, tool shadowing, hidden Unicode
# ═══════════════════════════════════════════════════════════════════════
#
# Inspired by Snyk agent-scan issue codes (E001, E002, W001, W021) and
# Invariant Labs' MCP tool-poisoning research. Pure stdlib, zero deps.
# These checks protect against: tool description injection (E001),
# cross-server tool shadowing (E002), manipulative language (W001),
# and hidden Unicode attacks like zero-width / bidi override / tag chars (W021).

# --- E001: Prompt injection regex patterns ---
# Each tuple: (pattern, label). Compiled once at import time.
_INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Direct override attempts
    (r"ignore\s+(?:all\s+)?(?:previous|above|prior|earlier)\s+(?:instructions?|prompts?|rules?)", "ignore-previous-instructions"),
    (r"disregard\s+(?:all\s+)?(?:previous|the\s+above)", "disregard-previous"),
    (r"forget\s+(?:everything|all\s+(?:previous|prior))", "forget-previous"),
    # Role hijacking
    (r"\byou\s+(?:must|should|are\s+now|will\s+now|have\s+to)\b", "role-assignment"),
    (r"\bact\s+as\s+(?:a|an)\s+(?:root|admin|developer|system)", "role-impersonation"),
    (r"\bfrom\s+now\s+on\b", "persistent-override"),
    # System prompt reference / token injection
    (r"system\s+prompt", "system-prompt-reference"),
    (r"<\|im_start\|>", "chatgpt-token-injection"),
    (r"<\|/?system\|>", "system-tag-injection"),
    (r"<\|/?assistant\|>", "assistant-tag-injection"),
    # Data exfiltration
    (r"(?:send|transmit|upload|post|exfiltrate|append|write|forward|pipe)\s+.+\bto\b.+\bhttps?://\S+", "exfiltration-command"),
    (r"(?:send|transmit|upload|post|exfiltrate)\s+.*\s+to\s+(?:an?\s+external|a\s+remote|another|a\s+third.party)", "exfiltration-command"),
    # Credential file access (SSH keys, cloud creds, tokens)
    (r"~?/\.ssh/(?:id_rsa|id_ed25519|id_ecdsa|authorized_keys|config|known_hosts)", "credential-file-access"),
    (r"~?/\.aws/(?:credentials|config)", "credential-file-access"),
    (r"~?/\.gnupg/", "credential-file-access"),
    (r"\bid_rsa\b", "credential-file-access"),
    # Bare sensitive-dir mentions in read/copy/backup context
    (r"(?:backup|copy|read|fetch|send|upload|return|include|access)\b.{0,40}\.(?:ssh|aws|gnupg)\b", "credential-file-access"),
    (r"\b\.env\b", "credential-file-access"),
    (r"access\s+(?:the\s+)?(?:user'?s?|file|env|filesystem|home)\s+(?:data|files?|credentials?|secrets?)", "data-access-command"),
    (r"read\s+(?:the\s+)?\.env(?:ironment)?\b", "env-file-access"),
    (r"execute\s+(?:the\s+following\s+)?(?:command|shell|bash)\s*[:\-]", "command-execution"),
    (r"\brun\s+(?:this|the\s+following)\s+(?:command|script|code)\b", "code-execution-prompt"),
    # Hidden instruction markers (model-specific tokens)
    (r"\[INST\]", "llama-inst-marker"),
    (r"</?s>", "bos-eos-marker"),
    # Exfiltration via shell piping (pipe/feed/stream through curl/wget/nc)
    (r"(?:pipe|feed|stream)\s+.+(?:through|via|\|)\s+(?:curl|wget|nc|netcat)\b", "exfiltration-command"),
    # curl/wget to a suspicious endpoint (attacker/evil/c2/exfil/webhook)
    (r"\b(?:curl|wget)\b.{0,40}(?:attacker|evil|c2|exfil|collect|hook|webhook)\b", "exfiltration-command"),
    # Tool poisoning: description contradicts itself ("actually deletes/removes/...")
    (r"\bactually\s+(?:deletes?|removes?|overwrites?|destroys?|wipes?|formats?)\b", "tool-poisoning"),
]
_INJECTION_REGEXES = [(re.compile(p, re.IGNORECASE), label) for p, label in _INJECTION_PATTERNS]

# Patterns that warrant "critical" severity (active exfiltration or token hijack)
_CRITICAL_LABELS = frozenset({
    "exfiltration-command", "chatgpt-token-injection",
    "system-tag-injection", "assistant-tag-injection",
    "command-execution", "env-file-access", "credential-file-access",
})

# --- W001: Suspicious manipulative words ---
# Two tiers: high-confidence manipulation verbs trigger on their own;
# common-but-ambiguous words (must/always/never/important) only trigger
# when >=3 appear together (clustered urgency = likely manipulation).
_W001_HIGH = ["crucial", "vital", "urgent", "immediately", "override", "bypass", "secretly"]
_W001_LOW = ["important", "critical", "must", "always", "never"]
_W001_HIGH_RE = [re.compile(r"\b" + w + r"\b", re.IGNORECASE) for w in _W001_HIGH]
_W001_LOW_RE = [re.compile(r"\b" + w + r"\b", re.IGNORECASE) for w in _W001_LOW]

# --- W021: Hidden Unicode detection ---

# --- W022: Cyrillic homoglyph detection ---
# Cyrillic letters that are visually identical to Latin equivalents.
# Attackers substitute these to hide tool-name or keyword impersonation
# (e.g. "fil\u0435system" looks like "filesystem" but the \u0435 is Cyrillic).
_CYRILLIC_CONFUSABLES = {
    0x0430: "a", 0x0435: "e", 0x043E: "o", 0x0440: "p", 0x0441: "c",
    0x0445: "x", 0x0443: "y", 0x0410: "A", 0x0412: "B", 0x0415: "E",
    0x041A: "K", 0x041C: "M", 0x041D: "H", 0x041E: "O", 0x0420: "P",
    0x0421: "C", 0x0422: "T", 0x0425: "X",
}
_TAG_BLOCK_START = 0xE0000
_TAG_BLOCK_END = 0xE007F
_HIDDEN_CATEGORIES = {"Cf", "Cc", "Co"}

# --- W017-020: Server-level capability-risk patterns ---
_SENSITIVE_DATA_RE = re.compile(
    r"\b(email|dm|message|chat|password|passwd|credentials?|secrets?|tokens?|api[_-]?keys?|financial|bank|credit|ssn)\b",
    re.IGNORECASE,
)
_DESTRUCTIVE_RE = re.compile(
    r"\b(?:shell|exec|execute|\brm\b|delete|destroy|format|kill|truncate|drop\s+table|wipe|overwrite|erase|purge)\b",
    re.IGNORECASE,
)
_UNTRUSTED_CONTENT_RE = re.compile(
    r"\b(?:fetch|browse|crawl|scrape|parse|download|load)\s+(?:url|web|html|page|site|internet)|web\s+search|url\s+fetcher\b",
    re.IGNORECASE,
)

# Remediation suggestions keyed by security issue code. Each security issue
# carries a `fix` string so both JSON consumers and the human report can show
# actionable guidance - matching the `fix` field already present on regular issues.
_SEC_FIXES: dict[str, str] = {
    "E001": "Remove the injection pattern from the tool description, or audit the tool source for malicious intent.",
    "E002": "Review whether this server should reference another server's tool name. Rename or isolate if unintended.",
    "E003": "Verify the tool description change is intentional. Re-run --save-baseline after confirming safety.",
    "W001": "Rewrite the tool description to remove urgency/manipulation language. Tool descriptions should be neutral.",
    "W015": "Ensure external content fetched by this tool is treated as untrusted input and sandboxed appropriately.",
    "W017": "Review whether this tool needs access to sensitive data. Restrict permissions if possible.",
    "W019": "Review destructive operations. Consider adding confirmation prompts or access controls.",
    "W021": "Remove hidden Unicode characters from the tool description. These may hide malicious instructions.",
    "W022": "Replace Cyrillic lookalike characters with their ASCII equivalents in tool names and descriptions.",
}


def _decode_tag_sequence(text: str) -> str | None:
    """Decode Unicode Tag characters (U+E0000-U+E007F) into readable ASCII.

    Tag chars map to ASCII: U+E0041 = 'A', etc. Attackers use these to hide
    instructions invisible to humans but readable by some models. Returns
    decoded printable text if >=3 chars, else None.
    """
    tag_chars = [c for c in text if _TAG_BLOCK_START <= ord(c) <= _TAG_BLOCK_END]
    if not tag_chars:
        return None
    decoded = "".join(chr(ord(c) - _TAG_BLOCK_START) for c in tag_chars)
    printable = "".join(c for c in decoded if 32 <= ord(c) <= 126)
    return printable if len(printable) >= 3 else None


def validate_tool_security(tool: dict) -> list[dict]:
    """Analyze a single tool for security risks in its description and name.

    Checks:
      E001 - prompt injection patterns (regex match against known attack patterns)
      W001 - suspicious manipulative words (urgency / override language)
      W021 - hidden Unicode characters (zero-width, bidi override, tag sequences)
      W022 - Cyrillic homoglyph attacks (mixed Latin/Cyrillic in same word)

    Returns list of issue dicts with keys:
      tool, severity, code, label, message, evidence
    """
    issues: list[dict] = []
    name = tool.get("name", "<unnamed>")
    desc = str(tool.get("description", ""))
    full_text = f"{name} {desc}"  # scan name too - it's also model-visible

    # --- E001: Prompt injection ---
    seen: set[str] = set()
    for regex, label in _INJECTION_REGEXES:
        match = regex.search(desc)
        if match and label not in seen:
            seen.add(label)
            sev = "critical" if label in _CRITICAL_LABELS else "high"
            issues.append({
                "tool": name,
                "severity": sev,
                "code": "E001",
                "label": label,
                "message": f"Prompt injection pattern '{label}' in tool '{name}'.",
                "evidence": match.group()[:120],
                "fix": _SEC_FIXES["E001"],
            })

    # --- W001: Suspicious words (two-tier to reduce false positives) ---
    high_hits: list[str] = []
    for regex in _W001_HIGH_RE:
        m = regex.search(desc)
        if m:
            high_hits.append(m.group())
    low_hits: list[str] = []
    for regex in _W001_LOW_RE:
        m = regex.search(desc)
        if m:
            low_hits.append(m.group())

    word_hits = high_hits + low_hits
    if high_hits:
        # High-confidence manipulation verbs: trigger on their own
        sev = "medium" if len(word_hits) >= 3 else "low"
        issues.append({
            "tool": name,
            "severity": sev,
            "code": "W001",
            "label": "suspicious-words",
            "message": f"Tool '{name}' uses manipulative language: {', '.join(sorted(set(word_hits)))}.",
            "evidence": ", ".join(sorted(set(word_hits))),
            "fix": _SEC_FIXES["W001"],
        })
    elif len(low_hits) >= 3:
        # Common words only flag when clustered (>=3 in one description)
        issues.append({
            "tool": name,
            "severity": "low",
            "code": "W001",
            "label": "suspicious-words",
            "message": f"Tool '{name}' uses manipulative language: {', '.join(sorted(set(low_hits)))}.",
            "evidence": ", ".join(sorted(set(low_hits))),
            "fix": _SEC_FIXES["W001"],
        })

    # --- W021: Hidden Unicode characters ---
    hidden_chars: list[str] = []
    distinct_cats: set[str] = set()
    for ch in full_text:
        cat = unicodedata.category(ch)
        if cat in _HIDDEN_CATEGORIES:
            hidden_chars.append(ch)
            distinct_cats.add(cat)
        if _TAG_BLOCK_START <= ord(ch) <= _TAG_BLOCK_END:
            distinct_cats.add("Tag")
    if hidden_chars:
        decoded = _decode_tag_sequence(full_text)
        if len(distinct_cats) >= 3 or decoded:
            sev = "high"
        else:
            sev = "medium"
        detail = f"{len(hidden_chars)} char(s), types: {', '.join(sorted(distinct_cats))}"
        if decoded:
            detail += f" - hidden message: \"{decoded[:80]}\""
        issues.append({
            "tool": name,
            "severity": sev,
            "code": "W021",
            "label": "hidden-unicode",
            "message": f"Tool '{name}' contains hidden Unicode: {detail}.",
            "evidence": repr("".join(hidden_chars[:10])),
            "fix": _SEC_FIXES["W021"],
        })


    # --- W022: Cyrillic homoglyph (mixed-script word) ---
    # Split on non-alphanumeric to get individual "words", then check each
    # for mixed Latin+Cyrillic script where the Cyrillic chars are confusables.
    for token in re.split(r"[^\w]+", full_text):
        if len(token) < 3:
            continue
        has_latin = any(c.isascii() and c.isalpha() for c in token)
        cyr_positions = [i for i, c in enumerate(token) if 0x0400 <= ord(c) <= 0x04FF]
        if has_latin and cyr_positions:
            # Only flag if at least one Cyrillic char is a known confusable
            confusable_hits = [c for c in token if ord(c) in _CYRILLIC_CONFUSABLES]
            if confusable_hits:
                normalized = "".join(
                    _CYRILLIC_CONFUSABLES.get(ord(c), c) for c in token
                )
                hits_display = ", ".join(
                    f"U+{ord(c):04X}" for c in sorted(set(confusable_hits))
                )
                issues.append({
                    "tool": name,
                    "severity": "high",
                    "code": "W022",
                    "label": "cyrillic-homoglyph",
                    "message": (
                        f"Tool '{name}' contains mixed-script word "
                        f"'{token}' with Cyrillic lookalikes ({hits_display}). "
                        f"Normalizes to '{normalized}'."
                    ),
                    "evidence": token,
                    "fix": _SEC_FIXES["W022"],
                })
    return issues


def validate_server_security(
    server_name: str,
    tools: list[dict],
    all_server_tools: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Detect server-level security risks: cross-server tool shadowing (E002),
    sensitive data exposure (W017/018), destructive capabilities (W019/020),
    and untrusted content handling (W015/016).

    all_server_tools: {server_name: [tool_names]} for E002 cross-reference.
    Pass None to skip shadowing check (e.g., single-server run).
    """
    issues: list[dict] = []
    all_text = " ".join(
        f"{t.get('name','')} {t.get('description','')}" for t in tools if isinstance(t, dict)
    )

    # --- E002: Cross-server tool shadowing ---
    # A tool description mentions a tool name from a DIFFERENT server.
    # This is how a poisoned tool can shadow/override legitimate tools.
    if all_server_tools:
        own_tools = set()
        for sname, tnames in all_server_tools.items():
            if sname == server_name:
                own_tools = set(tnames)
                break
        for other_server, other_tools in all_server_tools.items():
            if other_server == server_name:
                continue
            for otname in other_tools:
                # Skip short names to reduce false positives. Common English
                # words like 'time', 'file', 'list' (4-5 chars) that are also
                # valid tool names cause noise. Most shadowing targets use
                # descriptive names (read_file, delete_file) >= 6 chars.
                if len(otname) < 6:
                    continue
                # Word-boundary match in this server's tool descriptions
                pat = re.compile(r"\b" + re.escape(otname) + r"\b", re.IGNORECASE)
                if pat.search(all_text):
                    issues.append({
                        "tool": "(server)",
                        "severity": "high",
                        "code": "E002",
                        "label": "cross-server-shadow",
                        "message": f"Server '{server_name}' references tool '{otname}' from server '{other_server}' - potential tool shadowing.",
                        "evidence": otname,
                        "fix": _SEC_FIXES["E002"],
                    })

    # --- W017/W018: Sensitive data exposure ---
    if _SENSITIVE_DATA_RE.search(all_text):
        # Determine if this is a shared-infra server (medium) or local (low)
        # Heuristic: if server name suggests multi-user/shared context
        sev = "medium" if any(k in server_name.lower() for k in ("shared", "team", "org")) else "low"
        issues.append({
            "tool": "(server)",
            "severity": sev,
            "code": "W017",
            "label": "sensitive-data-exposure",
            "message": f"Server '{server_name}' tools may access sensitive data (credentials, messages, financial info).",
            "evidence": _SENSITIVE_DATA_RE.search(all_text).group()[:80],
            "fix": _SEC_FIXES["W017"],
        })

    # --- W019/W020: Destructive capabilities ---
    destructive_hits = _DESTRUCTIVE_RE.findall(all_text)
    if destructive_hits:
        sev = "medium" if any(k in server_name.lower() for k in ("shared", "team", "prod")) else "low"
        issues.append({
            "tool": "(server)",
            "severity": sev,
            "code": "W019",
            "label": "destructive-capability",
            "message": f"Server '{server_name}' has tools with destructive capabilities: {', '.join(sorted(set(h.lower() for h in destructive_hits))[:5])}.",
            "evidence": ", ".join(sorted(set(h.lower() for h in destructive_hits))[:5]),
            "fix": _SEC_FIXES["W019"],
        })

    # --- W015/W016: Untrusted content exposure ---
    if _UNTRUSTED_CONTENT_RE.search(all_text):
        issues.append({
            "tool": "(server)",
            "severity": "low",
            "code": "W015",
            "label": "untrusted-content",
            "message": f"Server '{server_name}' fetches/processes external web content - combined with other tools this creates prompt-injection risk.",
            "evidence": _UNTRUSTED_CONTENT_RE.search(all_text).group()[:80],
            "fix": _SEC_FIXES["W015"],
        })

    return issues



# ═══════════════════════════════════════════════════════════════════════
# Health scoring
# ═══════════════════════════════════════════════════════════════════════

def compute_health_score(server: ServerResult) -> float:
    """Compute a 0-100 health score for a probed server.

    Components (weighted):
      - 50%: connectivity (tools returned > 0)
      - 30%: schema quality (% tools with valid schemas)
      - 20%: description coverage (% tools with descriptions)
    Disabled / errored servers score 0.
    """
    if server.status in (ERROR, DISABLED):
        return 0.0
    if server.status == "config-ok":
        # Config validated but server wasn't probed. Start from 100 and
        # apply config-layer penalties (unpinned packages, plaintext secrets,
        # invalid env types, etc.) so the score reflects real issues.
        score = 100.0
        for i in server.issues:
            if i.get("severity") == "error":
                score -= 25.0
            elif i.get("severity") == "warning":
                score -= 10.0
        sec_critical = sum(1 for i in server.security_issues if i.get("severity") == "critical")
        sec_high = sum(1 for i in server.security_issues if i.get("severity") == "high")
        if sec_critical > 0:
            score = min(score, 20.0)
        elif sec_high > 0:
            score = min(score, 50.0)
        return max(0.0, round(score, 1))
    if not server.tools_found:
        # Not probed (skip-probe or config-only check mode). Score reflects
        # config-layer findings only: start from a neutral baseline and
        # deduct per error/warning so the score is meaningful, not a misleading 0.
        score = 100.0
        for i in server.issues:
            if i.get("severity") == "error":
                score -= 25.0
            elif i.get("severity") == "warning":
                score -= 10.0
        # Security findings on unprobed servers come from config-layer checks
        # (e.g. plaintext secrets). Apply the same caps as probed servers.
        sec_critical = sum(1 for i in server.security_issues if i.get("severity") == "critical")
        sec_high = sum(1 for i in server.security_issues if i.get("severity") == "high")
        if sec_critical > 0:
            score = min(score, 20.0)
        elif sec_high > 0:
            score = min(score, 50.0)
        return max(0.0, round(score, 1))

    total_tools = len(server.tools_found)
    schema_errs = sum(1 for i in server.schema_issues if i["severity"] == "error")
    schema_warns = sum(1 for i in server.schema_issues if i["severity"] == "warning")

    # Schema quality: penalize errors heavily, warnings lightly
    schema_score = max(0.0, 1.0 - (schema_errs * 0.5 + schema_warns * 0.1) / max(total_tools, 1))

    # Description coverage
    desc_missing = sum(
        1 for i in server.schema_issues if i["kind"] == "missing_description"
    )
    desc_score = 1.0 - (desc_missing / max(total_tools, 1))

    # Connectivity: tools exist
    conn_score = 1.0 if total_tools > 0 else 0.0

    score = (conn_score * 0.5 + schema_score * 0.3 + desc_score * 0.2) * 100

    # Security cap: critical/high security issues limit the max achievable score.
    # This prevents a server with active prompt-injection patterns from
    # appearing "healthy" just because its schema is well-formed.
    sec_critical = sum(1 for i in server.security_issues if i.get("severity") == "critical")
    sec_high = sum(1 for i in server.security_issues if i.get("severity") == "high")
    if sec_critical > 0:
        score = min(score, 20.0)   # critical injection → red zone
    elif sec_high > 0:
        score = min(score, 50.0)   # high-risk patterns → yellow zone max

    # v1.4: rug-pull (E003) - a changed tool description is a high-severity
    # trust violation. Cap at 50 like other high findings.
    e003_high = sum(
        1 for i in server.security_issues
        if i.get("code") == "E003" and i.get("severity") == "high"
    )
    if e003_high and sec_critical == 0:
        score = min(score, 50.0)

    # v1.4: latency penalty - slow but functional servers lose a few points
    # so they don't appear pristine. >15s loses 10, >5s loses 5.
    # Guard against NaN (comparisons always False) and negative values.
    lat = server.latency_ms
    if lat is not None and not (isinstance(lat, float) and math.isnan(lat)) and lat >= 0:
        if lat >= LATENCY_ERROR_MS:
            score = max(0.0, score - 10.0)
        elif lat >= LATENCY_WARN_MS:
            score = max(0.0, score - 5.0)

    return round(score, 1)


# ═══════════════════════════════════════════════════════════════════════
# Main diagnostic flow
# ═══════════════════════════════════════════════════════════════════════

def diagnose(
    config_path: Path | None,
    timeout: float,
    skip_probe: bool,
    only: list[str] | None,
    check_mode: str = "all",
) -> DiagnosticsReport:
    """Run the full diagnostic flow.

    check_mode: "all" (default), "connectivity", "schema", or "security".
      - connectivity: L1+L2 only (probe + config validation)
      - schema: L2.5 only (tool schema quality checks)
      - security: L4 only (prompt injection, tool shadowing, hidden Unicode)
      - all: everything
    """
    if config_path is None:
        config_path = find_config()
        if config_path is None:
            return DiagnosticsReport(
                config_path="(not found)",
                servers=[],
                config_errors=["No config.toml found. Set CODEX_HOME or ensure ~/.codex/config.toml exists."],
            )

    servers_cfg, config_errors = parse_config(config_path)
    report = DiagnosticsReport(
        config_path=str(config_path),
        servers=[],
        config_errors=config_errors,
    )

    if not servers_cfg and not config_errors:
        report.config_errors.append("No [mcp_servers.*] entries found in config.")
        return report

    # Cache probe tool dicts for the cross-server security pass (E002 needs all).
    probe_tool_cache: dict[str, list[dict]] = {}

    for name, cfg in servers_cfg.items():
        if only and name not in only:
            continue

        if cfg.get("enabled") is False:
            report.servers.append(ServerResult(
                name=name, transport=classify_transport(cfg),
                status=DISABLED, raw_config=cfg,
            ))
            continue

        transport = classify_transport(cfg)
        issues: list[dict] = []

        # L2: config validation (always run, even in schema-only mode)
        if transport == "stdio":
            issues.extend(validate_stdio_config(name, cfg))
        elif transport == "http":
            issues.extend(validate_http_config(name, cfg))
        else:
            issues.append({
                "severity": "error",
                "code": "unknown_transport",
                "message": "Cannot determine transport: neither 'command' nor 'url' is set.",
                "fix": f"Add either command=\"...\" (stdio) or url=\"...\" (http) under [mcp_servers.{name}]",
            })

        # L1: connectivity probe
        has_config_error = any(i["severity"] == "error" for i in issues)
        probe = ProbeResult()
        latency: float | None = None
        run_probe = (
            not skip_probe
            and not has_config_error
            and check_mode in ("all", "connectivity", "schema", "security")
        )

        if run_probe:
            if transport == "stdio":
                probe, probe_issues, latency = probe_stdio(cfg, timeout)
            elif transport == "http":
                probe, probe_issues, latency = probe_http(cfg, timeout)
            else:
                probe_issues = []
            issues.extend(probe_issues)
        elif has_config_error:
            issues.append({
                "severity": "info",
                "code": "probe_skipped",
                "message": "Skipping connectivity probe due to config errors above.",
            })

        # L2.5: schema quality checks
        schema_issues_raw: list[ToolSchemaIssue] = []
        if probe.tools and check_mode in ("all", "schema"):
            for tool in probe.tools:
                schema_issues_raw.extend(validate_tool_schema(tool))
        # Resource/prompt schema checks: in schema-only mode, run here
        # (per-server). In all/security mode, they run in the cross-server
        # pass below alongside injection/Unicode scanning.
        if check_mode == "schema":
            for r in probe.resources:
                schema_issues_raw.extend(validate_resource_schema(r))
            for p_item in probe.prompts:
                schema_issues_raw.extend(validate_prompt_schema(p_item))

        # L4: per-tool security analysis (E001 injection, W001 suspicious words,
        # W021 hidden Unicode). Run alongside schema checks or in security-only mode.
        tool_security_issues: list[dict] = []
        if probe.tools and check_mode in ("all", "security"):
            for tool in probe.tools:
                tool_security_issues.extend(validate_tool_security(tool))

        # Determine overall status
        error_count = sum(1 for i in issues if i["severity"] == "error")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        schema_error_count = sum(1 for i in schema_issues_raw if i.severity == "error")
        schema_warning_count = sum(1 for i in schema_issues_raw if i.severity == "warning")

        sec_critical = sum(1 for i in tool_security_issues if i["severity"] == "critical")
        sec_high = sum(1 for i in tool_security_issues if i["severity"] == "high")
        sec_any = len(tool_security_issues) > 0

        if error_count > 0:
            status = ERROR
        elif schema_error_count > 0:
            status = ERROR
        elif sec_critical > 0:
            status = ERROR  # critical security issue = hard fail
        elif warning_count > 0 or schema_warning_count > 0 or sec_high > 0:
            status = WARNING
        elif sec_any:
            status = WARNING  # any security finding (even low) = warning
        elif not run_probe:
            status = "config-ok"
        else:
            status = HEALTHY

        result = ServerResult(
            name=name,
            transport=transport,
            status=status,
            tools_found=[t.get("name", "?") for t in probe.tools if isinstance(t, dict)],
            resources_found=[r.get("uri", r.get("name", "?")) for r in probe.resources],
            prompts_found=[p.get("name", "?") for p in probe.prompts],
            server_info=probe.server_info,
            protocol_version=probe.protocol_version,
            capabilities=probe.capabilities,
            notifications_count=len(probe.notifications),
            issues=issues,
            schema_issues=schema_issues_to_dicts(schema_issues_raw),
            security_issues=tool_security_issues,
            latency_ms=latency,
            raw_config=cfg,
        )
        # Stash probe warnings for --debug rendering (non-fatal best-effort
        # exceptions caught during resources/list, prompts/list, etc.).
        result._probe_warnings = probe.probe_warnings
        # Cache tools for the cross-server security pass
        probe_tool_cache[name] = probe.tools
        # v1.4: stash full tool dicts on the result so the baseline
        # pass can hash tool descriptions without re-probing.
        result._baseline_tools = probe.tools
        result._baseline_resources = probe.resources
        result._baseline_prompts = probe.prompts
        # v1.4: latency threshold issue (GAP5)
        # Skip latency issue if the probe already timed out (redundant).
        already_timed_out = any(i.get("code") == "timeout" for i in result.issues)
        lat_issue = latency_issue(latency) if not already_timed_out else None
        if lat_issue:
            result.issues.append(lat_issue)
        result.health_score = compute_health_score(result)
        report.servers.append(result)

    # L4 cross-server: tool shadowing (E002) + server-level capability risks.
    # E002 needs ALL servers' tool names to detect cross-references, so this
    # runs as a second pass after every server has been probed.
    if check_mode in ("all", "security") and probe_tool_cache:
        all_server_tools = {
            name: [t.get("name", "?") for t in tools if isinstance(t, dict)]
            for name, tools in probe_tool_cache.items()
        }
        for s in report.servers:
            tools = probe_tool_cache.get(s.name, [])
            if not tools:
                continue
            server_sec = validate_server_security(s.name, tools, all_server_tools)
            s.security_issues.extend(server_sec)

            # v1.4 GAP6: scan resources + prompts for injection / Unicode.
            # The probe cache only holds tool dicts, so we pull the full
            # ServerResult to get resources_found / prompts_found names and
            # re-derive their dicts from the probe. We stored them on the
            # result's sibling attribute at probe time.
            res_dicts = getattr(s, "_baseline_resources", None) or []
            for r in res_dicts:
                s.security_issues.extend(validate_resource_security(r))
                s.schema_issues.extend(schema_issues_to_dicts(validate_resource_schema(r)))
            pr_dicts = getattr(s, "_baseline_prompts", None) or []
            for p_item in pr_dicts:
                s.security_issues.extend(validate_prompt_security(p_item))
                s.schema_issues.extend(schema_issues_to_dicts(validate_prompt_schema(p_item)))

            # Recompute health score with security issues included
            s.health_score = compute_health_score(s)

        # v1.4 GAP1: rug-pull baseline comparison (E003). Only runs when a
        # baseline file exists; --save-baseline / --check-baseline drive it
        # from main(). diagnose() just no-ops if there's no baseline.
        if getattr(report, "_check_baseline", False):
            rugpull = check_baseline(report)
            for issue in rugpull:
                # attach to the right server
                tname = issue.get("tool", ":")
                sname = tname.split(":", 1)[0] if ":" in tname else ""
                target = next((x for x in report.servers if x.name == sname), None)
                if target:
                    target.security_issues.append(issue)

    # Aggregate
    for s in report.servers:
        error_count = sum(1 for i in s.issues if i["severity"] == "error")
        warning_count = sum(1 for i in s.issues if i["severity"] == "warning")
        sec_crit = sum(1 for i in s.security_issues if i.get("severity") == "critical")
        sec_high = sum(1 for i in s.security_issues if i.get("severity") == "high")
        sec_med = sum(1 for i in s.security_issues if i.get("severity") == "medium")
        sec_low = sum(1 for i in s.security_issues if i.get("severity") == "low")
        report.total_issues += (
            len(s.issues) + len(s.schema_issues) + len(s.security_issues)
        )
        report.errors += (
            error_count
            + sum(1 for i in s.schema_issues if i["severity"] == "error")
            + sec_crit
        )
        report.warnings += (
            warning_count
            + sum(1 for i in s.schema_issues if i["severity"] == "warning")
            + sec_high + sec_med + sec_low
        )

    # Warn about --only names that matched nothing (likely a typo).
    if only:
        found_names = {s.name for s in report.servers}
        unmatched = [n for n in only if n not in found_names]
        if unmatched:
            report.servers.append(ServerResult(
                name=", ".join(unmatched),
                transport="none",
                status=ERROR,
                issues=[{
                    "severity": "error",
                    "code": "only_filter_no_match",
                    "message": (
                        f"--only {unmatched!r} matched no servers. "
                        f"Available: {sorted(servers_cfg.keys())}."
                    ),
                    "fix": "Check the server name for typos, or run without --only to see all servers.",
                }],
            ))

    return report


# ═══════════════════════════════════════════════════════════════════════
# Output formatting
# ═══════════════════════════════════════════════════════════════════════

ICONS = {
    HEALTHY: "✅",
    WARNING: "⚠️ ",
    ERROR: "❌",
    DISABLED: "⏸️ ",
    "config-ok": "🔧",
}

SCORE_ICONS = {
    "good": "🟢",
    "fair": "🟡",
    "poor": "🔴",
}


def _score_band(score: float) -> str:
    if score >= 80:
        return "good"
    if score >= 50:
        return "fair"
    return "poor"


def format_report_human(report: DiagnosticsReport) -> str:
    lines: list[str] = []
    summary = report.to_dict()["summary"]

    lines.append("=" * 64)
    lines.append("  MCP DOCTOR - Diagnostic Report")
    lines.append("=" * 64)
    lines.append(f"  Config: {report.config_path}")
    lines.append("")

    if report.config_errors:
        lines.append("  ⚠ Config Parsing Issues:")
        for e in report.config_errors:
            lines.append(f"    • {e}")
        lines.append("")

    config_ok = summary.get("config_ok", 0)
    score_line = ""
    if summary.get("avg_health_score") is not None:
        band = _score_band(summary["avg_health_score"])
        icon = SCORE_ICONS[band]
        score_line = f"  {icon} avg score {summary['avg_health_score']}"
    lines.append(
        f"  Servers: {summary['total_servers']} total"
        f"  ✅ {summary['healthy']} healthy"
        + (f"  🔧 {config_ok} config-ok" if config_ok else "")
        + (f"  ⚠️  {summary['warnings']} warnings" if summary['warnings'] else "")
        + (f"  ❌ {summary['errors']} errors" if summary['errors'] else "")
        + (f"  ⏸️  {summary['disabled']} disabled" if summary['disabled'] else "")
        + score_line
    )
    lines.append("")

    for s in report.servers:
        icon = ICONS.get(s.status, "?")
        tools_str = f"{len(s.tools_found)} tools" if s.tools_found else "0 tools"
        lat_str = f" ({s.latency_ms:.0f}ms)" if s.latency_ms is not None else ""
        score_str = ""
        if s.health_score is not None and s.status not in (DISABLED,):
            band = _score_band(s.health_score)
            score_str = f"  {SCORE_ICONS[band]} {s.health_score}"
        lines.append(f"  {icon} {s.name}{score_str}")
        lines.append(f"     transport: {s.transport}  |  {tools_str}{lat_str}")

        if s.server_info:
            si_name = s.server_info.get("name", "")
            si_ver = s.server_info.get("version", "")
            if si_name:
                lines.append(f"     server: {si_name} v{si_ver}" if si_ver else f"     server: {si_name}")

        # Protocol version + capabilities
        if s.protocol_version:
            cap_parts = []
            caps = s.capabilities if isinstance(s.capabilities, dict) else {}
            if "tools" in caps:
                cap_parts.append("tools")
            if "resources" in caps:
                cap_parts.append("resources")
            if "prompts" in caps:
                cap_parts.append("prompts")
            if "logging" in caps:
                cap_parts.append("logging")
            if "elicitation" in caps:
                cap_parts.append("elicitation")
            if caps.get("prompts", {}).get("listChanged") if isinstance(caps.get("prompts"), dict) else False:
                cap_parts.append("prompts.listChanged")
            if caps.get("resources", {}).get("listChanged") if isinstance(caps.get("resources"), dict) else False:
                cap_parts.append("resources.listChanged")
            if caps.get("tools", {}).get("listChanged") if isinstance(caps.get("tools"), dict) else False:
                cap_parts.append("tools.listChanged")
            cap_str = f" [{', '.join(cap_parts)}]" if cap_parts else " [no capabilities]"
            lines.append(f"     protocol: {s.protocol_version}{cap_str}")

        if s.notifications_count > 0:
            lines.append(f"     notifications: {s.notifications_count} captured during probe")

        # Tool/resource/prompt counts
        if s.resources_found or s.prompts_found:
            parts = []
            if s.resources_found:
                parts.append(f"{len(s.resources_found)} resources")
            if s.prompts_found:
                parts.append(f"{len(s.prompts_found)} prompts")
            lines.append(f"     primitives: {', '.join(parts)}")

        if s.tools_found:
            preview = s.tools_found[:8]
            extra = len(s.tools_found) - len(preview)
            tool_line = ", ".join(preview)
            if extra > 0:
                tool_line += f", +{extra} more"
            lines.append(f"     tools: {tool_line}")

        # Schema issues (compact summary)
        if s.schema_issues:
            serr = sum(1 for i in s.schema_issues if i["severity"] == "error")
            swarn = sum(1 for i in s.schema_issues if i["severity"] == "warning")
            if serr or swarn:
                lines.append(
                    f"     schema: ❌ {serr} error(s), ⚠️  {swarn} warning(s)"
                )
                for si in s.schema_issues[:5]:
                    si_icon = "❌" if si["severity"] == "error" else "⚠️ "
                    lines.append(f"       {si_icon} {si['message']}")
                if len(s.schema_issues) > 5:
                    lines.append(f"       ... +{len(s.schema_issues) - 5} more schema issues")

        # Security issues (L4: injection, shadowing, hidden Unicode)
        if s.security_issues:
            sec_crit = sum(1 for i in s.security_issues if i.get("severity") == "critical")
            sec_high = sum(1 for i in s.security_issues if i.get("severity") == "high")
            sec_med = sum(1 for i in s.security_issues if i.get("severity") == "medium")
            sec_low = sum(1 for i in s.security_issues if i.get("severity") == "low")
            parts = []
            if sec_crit: parts.append(f"🚨 {sec_crit} critical")
            if sec_high: parts.append(f"🔴 {sec_high} high")
            if sec_med: parts.append(f"🟠 {sec_med} medium")
            if sec_low: parts.append(f"🟡 {sec_low} low")
            lines.append(f"     security: {', '.join(parts)}")
            # Sort by severity: critical first, then high, medium, low
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_sec = sorted(s.security_issues, key=lambda x: sev_order.get(x.get("severity", "low"), 4))
            for si in sorted_sec[:8]:
                sev = si.get("severity", "low")
                code = si.get("code", "?")
                icon = {"critical": "🚨", "high": "🔴", "medium": "🟠", "low": "🟡"}.get(sev, "•")
                lines.append(f"       {icon} [{code}] {si.get('message', '')}")
                if si.get("evidence"):
                    lines.append(f"          evidence: {str(si['evidence'])[:100]}")
                if si.get("fix"):
                    lines.append(f"          → fix: {si['fix']}")
            if len(s.security_issues) > 8:
                lines.append(f"       ... +{len(s.security_issues) - 8} more security issues")

        for issue in s.issues:
            level = issue["severity"]
            itype = issue["code"]
            msg = issue["message"]
            fix = issue.get("fix", "")
            level_icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}.get(level, "•")
            lines.append(f"     {level_icon} [{itype}] {msg}")
            if fix:
                lines.append(f"        → fix: {fix}")
            if issue.get("stderr"):
                lines.append(f"        stderr: {issue['stderr'][:200]}")
            if issue.get("body"):
                lines.append(f"        response: {issue['body'][:200]}")
        if DEBUG:
            pw = getattr(s, "_probe_warnings", None) or []
            if pw:
                lines.append(f"     ⚙ debug: {len(pw)} probe warning(s) hidden:")
                for w in pw:
                    lines.append(f"        - {w}")
        lines.append("")

    lines.append("=" * 64)
    config_ok_count = summary.get("config_ok", 0)
    if report.errors > 0:
        lines.append(f"  RESULT: {report.errors} error(s), {report.warnings} warning(s) - issues found.")
        lines.append("  Fix the errors above, then re-run: python3 scripts/doctor.py")
    elif report.warnings > 0:
        lines.append(f"  RESULT: {report.warnings} warning(s) - servers running but check the warnings.")
    elif summary["healthy"] > 0:
        lines.append("  RESULT: All servers healthy. ✅")
    elif config_ok_count > 0:
        lines.append(f"  RESULT: {config_ok_count} server(s) config-valid (not probed). Run without --skip-probe for full diagnostics.")
    else:
        lines.append("  RESULT: No servers to check.")
    lines.append("=" * 64)

    return "\n".join(lines)


def format_report_json(report: DiagnosticsReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


# ═══════════════════════════════════════════════════════════════════════
# v1.4 - Supply chain, secrets, latency, rug-pull baseline, resource/prompt security
# All pure-stdlib. Imported and merged into doctor.py by build step.
# ═══════════════════════════════════════════════════════════════════════

# ─── GAP3 / MCP04: Supply-chain version pinning ─────────────────────
_REGISTRY_COMMANDS = {
    "npx", "npm", "pnpm", "yarn", "bunx", "uvx", "pip", "pipx", "docker",
}
# A pinned package looks like `pkg@1.2.3` or `pkg@^1.2.3` or `pkg@>=1`.
# Unpinned: bare `pkg`, or `pkg@latest`/`pkg@next`/`pkg@*`.
# A pinned version: @1.2.3, @^1.2.3, @~1.2, @>=1.2.0 - anything with a digit after @
# (possibly preceded by a SemVer range operator like ^ ~ > < =).
_PINNED_VERSION_RE = re.compile(r"@[\^~>=<!]*\d+\.\d+", re.IGNORECASE)
_UNPINNED_TAG_RE = re.compile(r"@(?:latest|next|beta|alpha|\*)\b", re.IGNORECASE)
# Flag values that take the next token (so we skip it as a package candidate)
_FLAG_TAKES_VALUE = {"-p", "--prefix", "--package", "-c", "--call",
                     "--registry", "--cache", "--prefix", "-C", "--workdir"}


# docker subcommands that precede the image name and are NOT the image
_DOCKER_SUBCOMMANDS = {"run", "exec", "create", "pull", "push", "build"}


def check_supply_chain(name: str, cfg: dict) -> list[dict]:
    """Flag stdio commands that invoke a registry package without pinning to
    a specific version or content digest. Returns config-style issue dicts
    (level/type/message/fix) so they flow into ServerResult.issues."""
    issues: list[dict] = []
    cmd = str(cfg.get("command", ""))
    args = cfg.get("args", [])
    if not isinstance(args, list):
        args = []
    tokens = [cmd, *[str(a) for a in args]]
    if not tokens:
        return issues
    base = os.path.basename(cmd) if "/" in cmd else cmd

    is_registry = base in _REGISTRY_COMMANDS or any(
        t in _REGISTRY_COMMANDS for t in tokens
    )
    if not is_registry:
        return issues

    # Locate the registry command position so we can walk after it.
    reg_idx = -1
    for i, tok in enumerate(tokens):
        if tok in _REGISTRY_COMMANDS or os.path.basename(tok) in _REGISTRY_COMMANDS:
            reg_idx = i
            break
    if reg_idx < 0:
        return issues
    reg_cmd = tokens[reg_idx]
    reg_base = os.path.basename(reg_cmd) if "/" in reg_cmd else reg_cmd

    # Walk tokens after the registry command, skipping flags (and the values
    # of flags that consume the next token). For docker, identify the
    # subcommand first: only `run` and `pull` pull images from a registry,
    # so only those warrant a version-pin check.
    docker_subcmd = None
    if reg_base == "docker":
        for tok in tokens[reg_idx + 1:]:
            if tok.startswith("-"):
                continue
            if tok in _DOCKER_SUBCOMMANDS:
                docker_subcmd = tok
            break
        if docker_subcmd and docker_subcmd not in ("run", "pull"):
            # exec/create/build/push operate on local state or a Dockerfile,
            # not a registry pull - no pinning concern.
            return issues

    skip_next = False
    candidate: str | None = None
    for tok in tokens[reg_idx + 1:]:
        if skip_next:
            skip_next = False
            continue
        if tok.startswith("-"):
            key = tok.split("=", 1)[0]
            if "=" not in tok and key in _FLAG_TAKES_VALUE:
                skip_next = True
            continue
        # docker subcommands like `run`/`pull` come before the image name
        if reg_base == "docker" and tok in _DOCKER_SUBCOMMANDS:
            continue
        candidate = tok
        break

    if not candidate:
        return issues

    pkg = candidate

    # docker: image should have @sha256: digest OR a non-latest :tag
    if reg_base == "docker":
        if "@sha256:" in pkg:
            return issues
        if ":" in pkg and not pkg.endswith(":latest"):
            return issues  # has a concrete tag
        issues.append({
            "severity": "warning",
            "code": "unpinned_docker_image",
            "message": f"Server '{name}' runs docker image '{pkg}' without a digest pin (@sha256:...).",
            "fix": f"Pin with a digest: {pkg}@sha256:<digest>, or at minimum a specific :tag (not :latest).",
        })
        return issues

    # npm-ish: flag if no @version, or @latest/@next/@*
    if _UNPINNED_TAG_RE.search(pkg):
        issues.append({
            "severity": "warning",
            "code": "unpinned_package",
            "message": f"Server '{name}' uses '{pkg}' - rolling tag, not pinned to a version.",
            "fix": f"Pin to a concrete version, e.g. {pkg.split('@')[0]}@1.2.3.",
        })
    elif "@" not in pkg or not _PINNED_VERSION_RE.search(pkg):
        # bare package name, no version at all
        bare = pkg.lstrip("@")
        issues.append({
            "severity": "warning",
            "code": "unpinned_package",
            "message": f"Server '{name}' uses '{pkg}' without a version pin.",
            "fix": f"Pin to a concrete version, e.g. {bare}@1.2.3, so a republished "
                   f"package can't silently change behavior.",
        })

    return issues


# ─── GAP4 / NSA: Secrets hardcoded in config ────────────────────────
# Common secret prefixes / shapes. We deliberately keep this conservative
# to avoid flagging short opaque IDs or version strings.
_SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"),           # OpenAI-style
    re.compile(r"\bmos_[A-Za-z0-9_]{16,}\b"),            # humaux-style
    re.compile(r"\bAKIA[0-9A-Z]{16,}\b"),                # AWS access key
    re.compile(r"\bgh[ps]_[A-Za-z0-9]{16,}\b"),          # GitHub token
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),    # Slack token
    re.compile(r"\bAIza[0-9A-Za-z_\-]{16,}\b"),          # Google API key
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    # Generic high-entropy-looking bearer token (only in Authorization header)
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{32,}"),
]
_EMBEDDED_CREDS_RE = re.compile(r"https?://[^/\s:@]+:[^/\s:@]+@")
# $VAR / ${VAR} references are fine - they pull from environment
_ENV_VAR_REF_RE = re.compile(r"^\$\{?[A-Z_][A-Z0-9_]*\}?$")


def _looks_like_secret(value: str) -> bool:
    if not isinstance(value, str) or len(value) < 12:
        return False
    if _ENV_VAR_REF_RE.match(value):
        return False  # environment variable reference, not a literal
    for pat in _SECRET_PATTERNS:
        if pat.search(value):
            return True
    return False


def check_config_secrets(name: str, cfg: dict) -> list[dict]:
    """GAP4 / NSA guidance: detect plaintext secrets hardcoded in config.

    Scans:
      - env values that look like API keys / tokens / private keys
      - http_headers (Authorization bearer, x-api-key, etc.)
      - URLs with embedded credentials (https://user:pass@host)
    """
    issues: list[dict] = []

    # env block
    env = cfg.get("env", {})
    if isinstance(env, dict):
        for k, v in env.items():
            if _looks_like_secret(str(v)):
                issues.append({
                    "severity": "warning",
                    "code": "plaintext_secret_env",
                    "message": f"Server '{name}' has a hardcoded secret in env['{k}'].",
                    "fix": f"Move it to an environment variable: reference $YOUR_SECRET_VAR from config and export YOUR_SECRET_VAR in your shell."
                })

    # http_headers
    headers = cfg.get("http_headers", {})
    if isinstance(headers, dict):
        for hk, hv in headers.items():
            if _looks_like_secret(str(hv)):
                issues.append({
                    "severity": "warning",
                    "code": "plaintext_secret_header",
                    "message": f"Server '{name}' has a hardcoded secret in http_headers['{hk}'].",
                    "fix": "Prefer bearer_token_env_var (Codex resolves $VAR at launch) over a literal "
                           "token in http_headers; if you must inline, ensure config.toml is gitignored.",
                })

    # URL with embedded credentials
    url = str(cfg.get("url", ""))
    if url and _EMBEDDED_CREDS_RE.search(url):
        issues.append({
            "severity": "warning",
            "code": "embedded_url_credentials",
            "message": f"Server '{name}' URL contains embedded credentials (user:pass@host).",
            "fix": "Remove credentials from the URL; pass them via http_headers instead.",
        })

    return issues


# ─── GAP5: Latency thresholds ───────────────────────────────────────
LATENCY_WARN_MS = 5000.0   # >5s = warning
LATENCY_ERROR_MS = 15000.0  # >15s = error


def latency_issue(latency_ms: float | None) -> dict | None:
    """Return a config-style issue dict if latency crosses a threshold."""
    if latency_ms is None:
        return None
    # Guard against NaN (all comparisons with NaN return False) and negative
    # values (nonsensical, shouldn't happen but could from clock issues).
    if isinstance(latency_ms, float) and math.isnan(latency_ms):
        return None
    if latency_ms < 0:
        return None
    if latency_ms >= LATENCY_ERROR_MS:
        return {
            "severity": "warning",  # keep as warning so it doesn't hard-fail the server
            "code": "high_latency",
            "message": f"Probe latency {latency_ms:.0f}ms is very high (>{LATENCY_ERROR_MS:.0f}ms).",
            "fix": "Check network path, server load, or whether the server does heavy work "
                   "(e.g. embedding) during listing.",
        }
    if latency_ms >= LATENCY_WARN_MS:
        return {
            "severity": "info",
            "code": "elevated_latency",
            "message": f"Probe latency {latency_ms:.0f}ms is elevated (>{LATENCY_WARN_MS:.0f}ms).",
            "fix": "Usually harmless for servers that compute embeddings on first call.",
        }
    return None


# ─── GAP6: Resource / Prompt security scanning ─────────────────────
def validate_resource_schema(resource: dict) -> list[ToolSchemaIssue]:
    """Check resource structural completeness (MCP spec).

    Resources must have a uri. Name and description are strongly
    recommended - without them the model can't decide when to use
    the resource.
    """
    issues: list[ToolSchemaIssue] = []
    name = resource.get("name", "?")
    label = f"resource:{name}"

    if not resource.get("uri"):
        issues.append(ToolSchemaIssue(
            tool=label, severity="error", kind="resource_missing_uri",
            message=f"Resource '{name}' has no URI.",
            fix="Add a 'uri' field (e.g. file:///path)."))

    if not resource.get("name"):
        issues.append(ToolSchemaIssue(
            tool=label, severity="warning", kind="resource_missing_name",
            message="Resource has no name - the model needs it to reference the resource.",
            fix="Add a 'name' field."))

    desc = str(resource.get("description", ""))
    if not desc.strip():
        issues.append(ToolSchemaIssue(
            tool=label, severity="warning", kind="resource_missing_description",
            message=f"Resource '{name}' has no description.",
            fix="Add a description so the model knows what this resource contains."))
    elif len(desc.strip()) < 10:
        issues.append(ToolSchemaIssue(
            tool=label, severity="warning", kind="resource_short_description",
            message=f"Resource '{name}' description is very short ({len(desc.strip())} chars).",
            fix="Expand the description so the model can reliably decide to use this resource."))
    return issues


def validate_prompt_schema(prompt: dict) -> list[ToolSchemaIssue]:
    """Check prompt structural completeness (MCP spec).

    Prompts must have a name. Description and well-formed arguments
    are strongly recommended for the model to use them correctly.
    """
    issues: list[ToolSchemaIssue] = []
    name = prompt.get("name", "")
    label = f"prompt:{name or '(unnamed)'}"

    if not name:
        issues.append(ToolSchemaIssue(
            tool=label, severity="error", kind="prompt_missing_name",
            message="Prompt has no name.",
            fix="Add a 'name' field to the prompt."))

    desc = str(prompt.get("description", ""))
    if not desc.strip():
        issues.append(ToolSchemaIssue(
            tool=label, severity="warning", kind="prompt_missing_description",
            message=f"Prompt '{name or '?'}' has no description.",
            fix="Add a description so the model knows when to use this prompt."))
    elif len(desc.strip()) < 10:
        issues.append(ToolSchemaIssue(
            tool=label, severity="warning", kind="prompt_short_description",
            message=f"Prompt '{name}' description is very short ({len(desc.strip())} chars).",
            fix="Expand the description so the model can reliably pick this prompt."))

    # Validate arguments structure if present
    args = prompt.get("arguments")
    if args is not None:
        if not isinstance(args, list):
            issues.append(ToolSchemaIssue(
                tool=label, severity="error", kind="prompt_invalid_arguments",
                message=f"Prompt '{name}' arguments is not a list (got {type(args).__name__}).",
                fix="Set arguments to a list of argument objects."))
        else:
            for arg in args:
                if not isinstance(arg, dict):
                    issues.append(ToolSchemaIssue(
                        tool=label, severity="error", kind="prompt_invalid_argument",
                        message=f"Prompt '{name}' has a non-object argument entry.",
                        fix="Each argument must be an object with name/description/required."))
                    continue
                arg_name = arg.get("name", "")
                if not arg_name:
                    issues.append(ToolSchemaIssue(
                        tool=label, severity="warning", kind="prompt_argument_missing_name",
                        message=f"Prompt '{name}' has an argument with no name.",
                        fix="Add a 'name' to each argument."))
                arg_desc = str(arg.get("description", ""))
                if not arg_desc.strip() and arg_name:
                    issues.append(ToolSchemaIssue(
                        tool=label, severity="warning", kind="prompt_argument_missing_description",
                        message=f"Prompt '{name}' argument '{arg_name}' has no description.",
                        fix=f"Add a description to argument '{arg_name}'."))
    return issues


def validate_resource_security(resource: dict) -> list[dict]:
    """Apply E001/W001/W021 to a resource's URI + name + description.

    Reuses validate_tool_security by shimming the resource into a tool-like
    dict, so all 18 injection patterns + suspicious words + Unicode checks
    apply uniformly. Code is prefixed with 'R' so reports distinguish them.
    """
    uri = str(resource.get("uri", ""))
    name = str(resource.get("name", uri))
    desc = str(resource.get("description", ""))
    # Build a synthetic tool so we can reuse the exact same checks
    shim = {"name": name, "description": f"{uri} {desc}"}
    raw = validate_tool_security(shim)
    for i in raw:
        i["tool"] = f"resource:{name}"
    return raw


def validate_prompt_security(prompt: dict) -> list[dict]:
    """Apply E001/W001/W021 to a prompt's name + description + arg descriptions."""
    name = str(prompt.get("name", ""))
    desc = str(prompt.get("description", ""))
    arg_descs: list[str] = []
    args = prompt.get("arguments", [])
    if isinstance(args, list):
        for a in args:
            if isinstance(a, dict):
                arg_descs.append(str(a.get("description", "")))
    shim = {"name": name, "description": f"{desc} {' '.join(arg_descs)}"}
    raw = validate_tool_security(shim)
    for i in raw:
        i["tool"] = f"prompt:{name}"
    return raw


# ─── GAP1 / MCP02: Rug-pull baseline (tool description pinning) ─────
BASELINE_PATH = Path.home() / ".codex" / "mcp-doctor-baseline.json"


def _tool_hash(tool: dict) -> str:
    """Stable hash of a tool's name + description. Args/inputSchema are
    intentionally excluded - attackers mutate the description text, which
    is what the model reads and trusts."""
    name = str(tool.get("name", ""))
    desc = str(tool.get("description", ""))
    payload = f"{name}\x1f{desc}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_baseline(report: "DiagnosticsReport", path: Path | None = None) -> Path:
    """Write the current tool-description hashes as a trusted baseline.

    Only servers that successfully returned tools are recorded. Disabled /
    errored servers are skipped so they don't pollute the baseline.
    """
    target = path or BASELINE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    baseline: dict[str, dict[str, str]] = {}
    for s in report.servers:
        # We need the full tool dicts, not just names - re-derive from the
        # diagnose() probe cache via the report's private channel.
        tools = getattr(s, "_baseline_tools", None) or []
        if not tools:
            continue
        baseline[s.name] = {
            t.get("name", "?"): _tool_hash(t) for t in tools if isinstance(t, dict)
        }
    target.write_text(json.dumps(baseline, indent=2, sort_keys=True))
    return target


def check_baseline(report: "DiagnosticsReport", path: Path | None = None) -> list[dict]:
    """Compare current tool-description hashes against the stored baseline.

    Returns a flat list of TOOL_CHANGED security-style issue dicts (one per
    changed/added/removed tool). Missing baseline file → returns [].
    """
    target = path or BASELINE_PATH
    if not target.exists():
        # User explicitly asked for --check-baseline but no baseline exists.
        # Don't silently skip - tell them to create one first.
        return [{
            "tool": "(baseline)",
            "severity": "info",
            "code": "E003",
            "label": "baseline-missing",
            "message": f"No baseline file found at {target}. Rug-pull detection cannot run "
                       f"until you save one.",
            "evidence": "file does not exist",
            "fix": f"Run with --save-baseline to create {target}, then re-run with --check-baseline.",
        }]
    try:
        stored = json.loads(target.read_text())
    except (json.JSONDecodeError, OSError) as e:
        # Baseline is unreadable - warn loudly so the user knows
        # rug-pull detection is NOT active (silent failure is dangerous).
        return [{
            "tool": "(baseline)",
            "severity": "high",
            "code": "E003",
            "label": "baseline-unreadable",
            "message": f"Baseline file {target} is corrupted or unreadable ({type(e).__name__}). "
                       "Rug-pull detection cannot run. Re-run with --save-baseline.",
            "evidence": "invalid JSON or I/O error",
            "fix": "Delete the baseline file and re-run with --save-baseline to recreate it.",
        }]
    if not isinstance(stored, dict):
        return [{
            "tool": "(baseline)",
            "severity": "high",
            "code": "E003",
            "label": "baseline-invalid-structure",
            "message": f"Baseline file {target} is valid JSON but not an object "
                       f"(got {type(stored).__name__}). Rug-pull detection cannot run.",
            "evidence": f"type: {type(stored).__name__}",
            "fix": "Delete the baseline file and re-run with --save-baseline to recreate it.",
        }]

    issues: list[dict] = []
    for s in report.servers:
        tools = getattr(s, "_baseline_tools", None) or []
        if not tools:
            continue
        current = {t.get("name", "?"): _tool_hash(t) for t in tools if isinstance(t, dict)}
        # Use sentinel to distinguish 'server not in baseline' (skip silently)
        # from 'server present but value is None/wrong-type' (warn).
        _MISSING = object()
        known = stored.get(s.name, _MISSING)
        if known is _MISSING:
            continue  # server not in baseline - skip (user should re-save)
        # Defensive: a corrupted/tampered baseline may store a non-dict
        # value for a server (list, int, null). Guard against TypeError.
        if not isinstance(known, dict):
            issues.append({
                "tool": f"{s.name}:(baseline)",
                "severity": "high",
                "code": "E003",
                "label": "baseline-server-invalid-type",
                "message": (
                    f"Baseline entry for server '{s.name}' is not a dict "
                    f"(got {type(known).__name__}). Rug-pull detection "
                    f"skipped for this server. Re-run with --save-baseline."
                ),
                "evidence": f"type: {type(known).__name__}",
                "fix": "Delete the baseline file and re-run with --save-baseline.",
            })
            continue
        for tname, thash in current.items():
            if tname not in known:
                issues.append({
                    "tool": f"{s.name}:{tname}",
                    "severity": "medium",
                    "code": "E003",
                    "label": "new-tool-since-baseline",
                    "message": f"Tool '{s.name}:{tname}' appeared since the last baseline. "
                               f"Verify it's legitimate before trusting it.",
                    "evidence": "new tool",
                    "fix": _SEC_FIXES["E003"],
                })
            elif known[tname] != thash:
                issues.append({
                    "tool": f"{s.name}:{tname}",
                    "severity": "high",
                    "code": "E003",
                    "label": "tool-description-changed",
                    "message": f"Tool '{s.name}:{tname}' description changed since the last "
                               f"baseline - possible rug-pull. Re-run with --save-baseline "
                               f"only after verifying the new description is safe.",
                    "evidence": "description hash mismatch",
                    "fix": _SEC_FIXES["E003"],
                })
        for tname in known:
            if tname not in current:
                issues.append({
                    "tool": f"{s.name}:{tname}",
                    "severity": "low",
                    "code": "E003",
                    "label": "tool-removed-since-baseline",
                    "message": f"Tool '{s.name}:{tname}' was removed since the last baseline.",
                    "evidence": "tool removed",
                    "fix": _SEC_FIXES["E003"],
                })
    return issues


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def _watch_signature(report: "DiagnosticsReport") -> tuple:
    """Build a hashable signature of report state, ignoring volatile fields.

    Only stable fields are included: per-server status, sorted issue codes,
    sorted security issue codes. Latency and timestamps are excluded so the
    watch loop doesn't spam on every tick.
    """
    sig = []
    for s in report.servers:
        issue_codes = tuple(sorted(
            (i.get("code", ""), i.get("severity", ""))
            for i in s.issues
        ))
        schema_codes = tuple(sorted(
            (i.get("code", ""), i.get("severity", ""))
            for i in s.schema_issues
        ))
        sec_codes = tuple(sorted(
            (i.get("code", ""), i.get("severity", ""))
            for i in s.security_issues
        ))
        sig.append((
            s.name, s.status, s.transport,
            tuple(sorted(s.tools_found)), tuple(sorted(s.resources_found)), tuple(sorted(s.prompts_found)),
            issue_codes, schema_codes, sec_codes,
        ))
    return (tuple(report.config_errors), tuple(sig))


def _watch_loop(args, first_report: "DiagnosticsReport") -> int:
    """Continuous monitoring: re-run diagnose every --interval seconds.

    Prints the full report on the first iteration, then only prints when the
    watch signature changes (status transition, new/lost issue, tool list
    change). Ctrl+C exits cleanly with exit code reflecting last report.
    """
    import time as _time

    interval = max(args.interval, 1.0)  # floor at 1s to avoid hammering servers
    prev_sig = _watch_signature(first_report)
    iteration = 1
    report = first_report

    # First iteration's report was already printed by the normal flow above.
    # Just announce watch mode.
    print("", flush=True)
    print(f"  \U0001F441 watching (every {interval:.0f}s) - Ctrl+C to stop", flush=True)
    print("", flush=True)

    try:
        while True:
            _time.sleep(interval)
            iteration += 1
            report = diagnose(
                config_path=args.config,
                timeout=args.timeout,
                skip_probe=args.skip_probe,
                only=args.only,
                check_mode=args.check,
            )
            if args.check_baseline:
                report._check_baseline = True
                rugpull = check_baseline(report, args.baseline_path)
                for issue in rugpull:
                    tname = issue.get("tool", ":")
                    sname = tname.split(":", 1)[0] if ":" in tname else ""
                    target = next((x for x in report.servers if x.name == sname), None)
                    if target:
                        target.security_issues.append(issue)
                        target.health_score = compute_health_score(target)

            sig = _watch_signature(report)
            if sig != prev_sig:
                ts = _time.strftime("%H:%M:%S")
                print("", flush=True)
                print(f"  \U000026A1 [{ts}] status changed (iteration {iteration}):", flush=True)
                print("", flush=True)
                if args.json:
                    print(format_report_json(report))
                else:
                    print(format_report_human(report))
                prev_sig = sig
            # else: silent - no change, no spam
    except KeyboardInterrupt:
        ts = _time.strftime("%H:%M:%S")
        print("", flush=True)
        print(f"  \U0001F441 watch stopped at {ts} after {iteration} iterations.", flush=True)
        # Exit code reflects the LAST report's status so a hook/script can
        # detect a degraded state that existed when watch was interrupted.
        last = report
        if last.errors > 0:
            return 1
        if last.config_errors and not last.servers:
            return 2
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mcp-doctor",
        description="Diagnose MCP server health for Codex. Zero dependencies.",
    )
    parser.add_argument("--version", action="version", version="mcp-doctor 1.6.11")
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to config.toml (default: auto-discover CODEX_HOME or ~/.codex/config.toml)",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0,
        help="Probe timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON instead of human-readable report",
    )
    parser.add_argument(
        "--skip-probe", action="store_true",
        help="Only validate config, don't attempt connectivity probes",
    )
    parser.add_argument(
        "--only", nargs="+", default=None,
        help="Only diagnose these server names (space-separated)",
    )
    parser.add_argument(
        "--check", choices=["all", "connectivity", "schema", "security",
                            "supply-chain", "secrets"],
        default="all",
        help="What to check: 'connectivity' (L1+L2), 'schema' (L2.5 quality), "
             "'security' (L4 injection/shadowing/unicode), "
             "'supply-chain' (MCP04 version pinning), 'secrets' (NSA plaintext), "
             "or 'all' (default).",
    )
    parser.add_argument(
        "--save-baseline", action="store_true",
        help="Save current tool-description hashes as a trusted baseline "
             "(~/.codex/mcp-doctor-baseline.json). Re-run after verifying tools.",
    )
    parser.add_argument(
        "--check-baseline", action="store_true",
        help="Compare current tool descriptions against the saved baseline. "
             "Flags any tool whose description changed (E003 rug-pull).",
    )
    parser.add_argument(
        "--baseline-path", type=Path, default=None,
        help="Override baseline file location (default: ~/.codex/mcp-doctor-baseline.json).",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Continuously re-run diagnostics every --interval seconds. Only "
             "prints when server status CHANGES (not on every tick), so it's "
             "safe to leave running. Ctrl+C stops cleanly. Pairs with --quiet "
             "for hook-style guard duty during development.",
    )
    parser.add_argument(
        "--interval", type=float, default=30.0,
        help="Seconds between --watch iterations (default: 30). Ignored without --watch.",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Show internal probe warnings (best-effort exceptions caught during "
             "resources/list, prompts/list, etc.). Useful when a server returns "
             "0 content and you suspect a probe-level issue rather than an empty server.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress all output unless errors are found (for hooks). Exit code still reflects health.",
    )
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    # Rug-pull baseline needs a full probe (to see tool descriptions), so we
    # normalize the check mode and flip a flag the diagnose() flow reads.
    check_mode = args.check
    if args.check_baseline or args.save_baseline:
        if check_mode == "all":
            check_mode = "all"
        elif check_mode not in ("all", "security"):
            check_mode = "all"  # baseline implies probing tools

    report = diagnose(
        config_path=args.config,
        timeout=args.timeout,
        skip_probe=args.skip_probe,
        only=args.only,
        check_mode=check_mode,
    )

    # v1.4 GAP1: rug-pull baseline
    if args.check_baseline:
        report._check_baseline = True
        rugpull = check_baseline(report, args.baseline_path)
        for issue in rugpull:
            tname = issue.get("tool", ":")
            sname = tname.split(":", 1)[0] if ":" in tname else ""
            target = next((x for x in report.servers if x.name == sname), None)
            if target:
                target.security_issues.append(issue)
                target.health_score = compute_health_score(target)
            elif not sname:
                # Baseline-level issue (missing/corrupted/invalid file) has no
                # server target. Surface it as a config-level message so the user
                # sees it in the report. Track severity for exit-code decisions.
                sev = issue.get("severity", "info")
                report.config_errors.append(
                    f"[{issue.get('label','baseline')}] ({sev}) {issue.get('message','')}"
                )
                # High-severity baseline problems (corrupted/invalid) mean
                # rug-pull detection silently failed - that deserves a non-zero
                # exit code so the user notices. Info-level (missing baseline)
                # is expected on first run, so don't hard-fail.
                if sev == "high":
                    report._baseline_failed = True


    if args.quiet and report.errors == 0 and not report.config_errors:
        pass  # hooks: silent when no server errors, exit code still reflects status
    elif args.json:
        print(format_report_json(report))
    else:
        print(format_report_human(report))

    if report.config_errors and not report.servers:
        # Distinguish real config errors (TOML parse failure, bad structure)
        # from the informational "no entries" message. Only real errors
        # warrant exit 2 (config unreadable); empty config is exit 3.
        real_errors = [e for e in report.config_errors
                       if "No [mcp_servers.*] entries" not in e]
        if real_errors:
            return 2

    # Baseline save confirmation - after the report, before exit codes.
    if args.save_baseline:
        tool_count = sum(len(getattr(s, '_baseline_tools', []) or []) for s in report.servers)
        bpath = save_baseline(report, args.baseline_path)
        print(f"Baseline saved: {bpath} ({tool_count} tools)")
        if tool_count == 0:
            print("WARNING: baseline is empty - no tools were probed.")
            print("         Re-run without --skip-probe and with running servers to capture tool hashes.")
    # --watch mode: continuously re-run, only print on status change.
    if args.watch:
        return _watch_loop(
            args=args,
            first_report=report,
        )

    # High-severity baseline failure (corrupted/invalid baseline file) means
    # rug-pull detection silently failed. Treat as a warning-level exit so
    # scripts/hooks notice something is off, even with healthy servers.
    if getattr(report, "_baseline_failed", False) and report.errors == 0:
        return 2
    if not report.servers:
        return 3
    if report.errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
