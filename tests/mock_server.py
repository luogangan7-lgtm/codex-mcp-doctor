#!/usr/bin/env python3
"""Mock stdio MCP server for testing.

Reads JSON-RPC requests from stdin (one per line), responds with
canned responses. Lets doctor.py probes be tested without real deps.
"""
import json
import sys


def respond(msg_id, result):
    print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)


def notify(method, params):
    print(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}), flush=True)


# Canned tool list with intentional schema issues for testing
TOOLS = [
    {
        "name": "good_tool",
        "description": "A well-documented tool that does something useful.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "no_desc_tool",
        # intentionally missing description
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "string"},
            },
            "required": ["x"],
        },
    },
    {
        "name": "bad_required_tool",
        "description": "Tool with a required field not in properties.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "required": ["a", "nonexistent"],
        },
    },
    {
        "name": "bad_type_tool",
        "description": "Tool with invalid type.",
        "inputSchema": {
            "type": "object",
            "properties": {"v": {"type": "notarealtype"}},
        },
    },
]

RESOURCES = [
    {"uri": "file:///test.txt", "name": "test"},
]

PROMPTS = [
    {"name": "summarize", "description": "Summarize something"},
]


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        mid = msg.get("id")

        if method == "initialize":
            respond(mid, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "mock-test-server", "version": "0.1.0"},
                "capabilities": {},
            })
        elif method == "notifications/initialized":
            pass  # notification, no response
        elif method == "tools/list":
            respond(mid, {"tools": TOOLS})
        elif method == "resources/list":
            respond(mid, {"resources": RESOURCES})
        elif method == "prompts/list":
            respond(mid, {"prompts": PROMPTS})


if __name__ == "__main__":
    main()
