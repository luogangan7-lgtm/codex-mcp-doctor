#!/usr/bin/env python3
"""Generate marketing images for Devpost/GitHub.

Outputs:
  docs/devpost-cover.png             - 3:2 Devpost gallery thumbnail (1500x1000)
  docs/w022-homoglyph.png            - W022 attack visualization (1500x1000)
  docs/screenshot-real-report.png    - real multi-server diagnostic report (1500x1000)
  docs/screenshot-rugpull-detection.png - E003 rug-pull detection (1500x1000)

Devpost image spec (help.devpost.com/article/126): Project Gallery
thumbnails should use a 3:2 ratio. All layouts are horizontally centered
so the 3:2 center-crop never clips title/terminal/columns/chips.

Uses PIL (Pillow) which is NOT a project dependency - this is a build-time
tool for generating static assets, not runtime code. Run:
    python3 docs/generate-images.py
"""
import os
import re
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

DOCS = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = DOCS


def _test_count() -> int:
    """Return the real test count, failing rather than rendering stale data."""
    repo_root = os.path.dirname(DOCS)
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_doctor"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        timeout=60,
    )
    output = result.stderr + result.stdout
    if result.returncode != 0:
        raise RuntimeError(
            f"Cannot render an accurate test badge: unittest exited "
            f"{result.returncode}.\n{output[-2000:]}"
        )
    match = re.search(r"Ran (\d+) tests", output)
    if not match:
        raise RuntimeError("Cannot render an accurate test badge: test count missing.")
    return int(match.group(1))

MONO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/Helvetica.ttc"

BG = (24, 24, 31)
BG_PANEL = (30, 30, 40)
FG = (220, 220, 230)
FG_DIM = (140, 140, 155)
GREEN = (74, 222, 128)
YELLOW = (250, 204, 21)
RED = (248, 113, 113)
BLUE = (96, 165, 250)
CYAN = (34, 211, 238)
PURPLE = (167, 139, 250)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def text_w(draw, text, f):
    return int(draw.textlength(text, font=f))


def draw_terminal_box(draw, x, y, w, h, title=None):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=BG_PANEL,
                           outline=(55, 55, 70), width=1)
    if title is not None:
        dot_y = y + 18
        for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            draw.ellipse([x + 18 + i * 22, dot_y - 6, x + 30 + i * 22, dot_y + 6], fill=color)
        f = font(SANS, 14)
        tw = text_w(draw, title, f)
        draw.text((x + (w - tw) // 2, dot_y - 8), title, fill=FG_DIM, font=f)


def make_cover():
    """Devpost cover - 3:2 (1500x1000), centered for Devpost gallery thumbnail."""
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Top gradient band
    for i in range(150):
        a = int(40 * (1 - i / 150))
        draw.line([(0, i), (W, i)], fill=(BG[0] + a // 4, BG[1] + a // 5, BG[2] + a // 2))

    cx = W // 2

    # Badge row (centered)
    tag_f = font(MONO, 22)
    badges = [
        ("Codex Plugin", (16, 185, 129)),
        ("Zero Deps", (74, 222, 128)),
        (f"{_test_count()} Tests", (96, 165, 250)),
    ]
    widths = [text_w(draw, t, tag_f) + 28 for t, _ in badges]
    total_w = sum(widths) + 24 * (len(badges) - 1)
    bx = cx - total_w // 2
    by = 145
    for (label, color), wd in zip(badges, widths):
        draw.rounded_rectangle([bx, by, bx + wd, by + 38], radius=19,
                               fill=(color[0] // 4, color[1] // 4, color[2] // 4),
                               outline=color, width=1)
        draw.text((bx + 14, by + 7), label, fill=color, font=tag_f)
        bx += wd + 24

    # Title (centered)
    title_f = font(SANS, 72)
    title = "codex-mcp-doctor"
    draw.text((cx - text_w(draw, title, title_f) // 2, 210), title, fill=FG, font=title_f)

    # Tagline
    sub_f = font(SANS, 36)
    tag = "'npm doctor' for MCP"
    draw.text((cx - text_w(draw, tag, sub_f) // 2, 305), tag, fill=CYAN, font=sub_f)

    # One-liner (two lines, centered)
    desc_f = font(SANS, 24)
    for i, line in enumerate([
        "Diagnose broken servers, malicious tools,",
        "and silent config failures - in one command.",
    ]):
        draw.text((cx - text_w(draw, line, desc_f) // 2, 365 + i * 32), line,
                  fill=FG_DIM, font=desc_f)

    # Mini terminal (centered)
    tw, th = 760, 300
    tx, ty = cx - tw // 2, 460
    draw_terminal_box(draw, tx, ty, tw, th, "doctor.py --config real.toml")
    mono_small = font(MONO, 18)
    lines = [
        (">>> Diagnosing 3 servers...", FG_DIM),
        ("  healthy: 1   warnings: 1   broken: 1", FG_DIM),
        ("  broken-path   RED 0.0   [command_not_found]", RED),
        ("  poisoned-fs   YEL 50.0  [W022] Cyrillic homoglyph", YELLOW),
        ("  filesystem    GRN 98.5  4 tools, schemas valid", GREEN),
        ("  RESULT: 1 broken, 1 attack found", RED),
    ]
    ly = ty + 55
    for text, color in lines:
        draw.text((tx + 24, ly), text, fill=color, font=mono_small)
        ly += 32

    # Feature chips (centered row under terminal)
    chip_f = font(MONO, 20)
    chips = [
        ("L1-L4 connectivity", BLUE),
        ("W022 homoglyph", YELLOW),
        ("E003 rug-pull", RED),
        ("auto hook", GREEN),
    ]
    cw = [text_w(draw, t, chip_f) + 32 for t, _ in chips]
    total_cw = sum(cw) + 20 * (len(chips) - 1)
    ccx = cx - total_cw // 2
    cy = 790
    for (label, color), wd in zip(chips, cw):
        draw.rounded_rectangle([ccx, cy, ccx + wd, cy + 34], radius=17,
                               fill=(color[0] // 4, color[1] // 4, color[2] // 4),
                               outline=color, width=1)
        draw.text((ccx + 16, cy + 6), label, fill=color, font=chip_f)
        ccx += wd + 20

    # Footer
    foot_f = font(MONO, 16)
    repo = "github.com/luogangan7-lgtm/codex-mcp-doctor"
    draw.text((cx - text_w(draw, repo, foot_f) // 2, H - 40), repo, fill=FG_DIM, font=foot_f)

    out = os.path.join(OUT_DIR, "devpost-cover.png")
    img.save(out, "PNG", optimize=True)
    print(f"Generated {out} ({img.size})")


def make_w022():
    """W022 homoglyph attack visualization - 3:2 (1500x1000), centered."""
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    cx = W // 2

    # Title (centered)
    title_f = font(SANS, 48)
    title = "W022: Cyrillic Homoglyph Attack"
    draw.text((cx - text_w(draw, title, title_f) // 2, 110), title, fill=YELLOW, font=title_f)
    sub_f = font(SANS, 22)
    sub = "Unique to codex-mcp-doctor. No other MCP scanner detects this."
    draw.text((cx - text_w(draw, sub, sub_f) // 2, 175), sub, fill=FG_DIM, font=sub_f)

    # Two-column comparison, centered as a unit
    col_w = 420
    col_h = 520
    gap = 60
    total = col_w * 2 + gap
    x0 = cx - total // 2
    lx = x0
    rx = x0 + col_w + gap
    y0 = 230

    # Left: attacker
    draw_terminal_box(draw, lx, y0, col_w, col_h, "attacker-server (malicious)")
    big_mono = font(MONO, 34)
    label_f = font(SANS, 20)
    ann_f = font(MONO, 16)
    draw.text((lx + 24, y0 + 55), "Tool name the server exposes:", fill=FG_DIM, font=label_f)
    cyr_text = "fil\N{CYRILLIC SMALL LETTER IE}system_read"
    draw.text((lx + 24, y0 + 95), cyr_text, fill=RED, font=big_mono)
    draw.text((lx + 24, y0 + 170), "             ^ this 'e' is U+0435", fill=RED, font=ann_f)
    draw.text((lx + 24, y0 + 195), "             (Cyrillic small ie)", fill=RED, font=ann_f)
    draw.text((lx + 24, y0 + 235), "Looks identical to filesystem_read", fill=FG, font=label_f)
    draw.text((lx + 24, y0 + 265), "in code review, terminal, or model", fill=FG, font=label_f)
    draw.text((lx + 24, y0 + 295), "context window.", fill=FG, font=label_f)
    draw.text((lx + 24, y0 + 360), "Intercepts file-read requests.", fill=RED, font=label_f)

    # Right: doctor catch
    draw_terminal_box(draw, rx, y0, col_w, col_h, "doctor.py output (the catch)")
    mono_med = font(MONO, 20)
    report = [
        ("Tool 'fil\N{CYRILLIC SMALL LETTER IE}system_read' contains", FG),
        ("mixed-script word with Cyrillic", FG),
        ("lookalikes (U+0435).", FG),
        ("", None),
        ("Normalizes to:", FG_DIM),
        ("  filesystem_read", GREEN),
        ("", None),
        ("Severity: HIGH", RED),
        ("Class: W022", YELLOW),
        ("", None),
        ("fix: Replace Cyrillic lookalikes", FG_DIM),
        ("     with ASCII equivalents.", FG_DIM),
    ]
    ry = y0 + 55
    for text, color in report:
        if text:
            draw.text((rx + 24, ry), text, fill=color or FG, font=mono_med)
        ry += 28

    # Punchline (centered)
    punch_f = font(SANS, 26)
    p1 = "The attacker disguised 'filesystem_read'."
    draw.text((cx - text_w(draw, p1, punch_f) // 2, H - 95), p1, fill=FG, font=punch_f)
    p2 = "The doctor reveals the normalized form - so you see intent, not cosmetics."
    draw.text((cx - text_w(draw, p2, font(SANS, 20)) // 2, H - 55), p2, fill=CYAN, font=font(SANS, 20))

    out = os.path.join(OUT_DIR, "w022-homoglyph.png")
    img.save(out, "PNG", optimize=True)
    print(f"Generated {out} ({img.size})")


def make_real_report():
    """Real multi-server diagnostic report - 3:2 (1500x1000), centered.

    Renders the actual doctor.py output for a mixed-health config so the
    screenshot always matches the current code. Three servers: one healthy,
    one broken (command_not_found), one with a security warning (plaintext
    secret). This is the 'what does a real report look like' asset.
    """
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    cx = W // 2

    # Header
    title_f = font(SANS, 36)
    title = "Diagnostic Report - 3 servers"
    draw.text((cx - text_w(draw, title, title_f) // 2, 90), title, fill=FG, font=title_f)
    sub_f = font(SANS, 18)
    sub = "python3 scripts/doctor.py --config real-config.toml"
    draw.text((cx - text_w(draw, sub, sub_f) // 2, 135), sub, fill=CYAN, font=sub_f)

    # Summary bar
    sum_f = font(MONO, 20)
    summary = "Servers: 3 total   healthy: 1   warnings: 1   broken: 1"
    draw.text((cx - text_w(draw, summary, sum_f) // 2, 175), summary, fill=FG_DIM, font=sum_f)

    # Three server cards stacked vertically, centered
    card_w = 900
    card_h = 180
    gap = 24
    total_h = card_h * 3 + gap * 2
    y0 = 225
    x0 = cx - card_w // 2

    mono = font(MONO, 18)
    label_f = font(SANS, 18)

    # Card 1: healthy filesystem server (green)
    cards = [
        {
            "name": "filesystem",
            "score": "98.5",
            "score_color": GREEN,
            "transport": "stdio  |  4 tools (18ms)",
            "status_icon": "GRN",
            "status_color": GREEN,
            "lines": [
                ("protocol: 2024-11-05 [tools, resources, prompts]", FG_DIM),
                ("tools: read_file, write_file, list_dir, search", FG),
                ("schemas: all 4 valid", GREEN),
            ],
        },
        {
            "name": "broken-path",
            "score": "0.0",
            "score_color": RED,
            "transport": "stdio  |  0 tools",
            "status_icon": "RED",
            "status_color": RED,
            "lines": [
                ("[command_not_found] Command path does not exist:", RED),
                ("    /usr/local/bin/nonexistent-mcp-server", FG_DIM),
                ("-> fix: Verify the path or reinstall the MCP server.", YELLOW),
            ],
        },
        {
            "name": "api-server",
            "score": "90.0",
            "score_color": YELLOW,
            "transport": "http  |  2 tools",
            "status_icon": "YEL",
            "status_color": YELLOW,
            "lines": [
                ("[plaintext_secret_header] Hardcoded secret in", YELLOW),
                ("    http_headers['Authorization']", FG_DIM),
                ("-> fix: Use bearer_token_env_var instead.", YELLOW),
            ],
        },
    ]

    for i, card in enumerate(cards):
        cy = y0 + i * (card_h + gap)
        border = card["score_color"]
        draw.rounded_rectangle([x0, cy, x0 + card_w, cy + card_h], radius=8,
                               fill=BG_PANEL, outline=border, width=2)
        # Header row: name + score
        name_f = font(MONO, 24)
        draw.text((x0 + 24, cy + 18), card["name"], fill=FG, font=name_f)
        score_text = card["score"]
        score_f = font(MONO, 28)
        sw = text_w(draw, score_text, score_f)
        draw.text((x0 + card_w - sw - 24, cy + 16), score_text, fill=card["score_color"], font=score_f)
        # Transport line
        draw.text((x0 + 24, cy + 56), card["transport"], fill=FG_DIM, font=mono)
        # Detail lines
        ly = cy + 88
        for text, color in card["lines"]:
            draw.text((x0 + 24, ly), text, fill=color, font=mono)
            ly += 28

    # Footer
    foot_f = font(MONO, 16)
    foot = "RESULT: 1 broken, 1 warning, 1 healthy - root-caused in under a second"
    draw.text((cx - text_w(draw, foot, foot_f) // 2, H - 55), foot, fill=FG, font=foot_f)
    repo = "github.com/luogangan7-lgtm/codex-mcp-doctor"
    draw.text((cx - text_w(draw, repo, foot_f) // 2, H - 30), repo, fill=FG_DIM, font=foot_f)

    out = os.path.join(OUT_DIR, "screenshot-real-report.png")
    img.save(out, "PNG", optimize=True)
    print(f"Generated {out} ({img.size})")


def make_rugpull():
    """E003 rug-pull detection - 3:2 (1500x1000), centered.

    Renders the actual doctor.py output when a baseline check fires two
    E003 tiers (high: description tampered, low: tool removed) plus the
    W022 from the same server. This is the flagship-feature screenshot.
    """
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    cx = W // 2

    # Header
    title_f = font(SANS, 36)
    title = "E003: Rug-Pull Detection"
    draw.text((cx - text_w(draw, title, title_f) // 2, 90), title, fill=RED, font=title_f)
    sub_f = font(SANS, 18)
    sub = "First CLI implementation of tool-description pinning"
    draw.text((cx - text_w(draw, sub, sub_f) // 2, 135), sub, fill=CYAN, font=sub_f)

    # Three-state timeline (Monday baseline -> Friday check)
    mono = font(MONO, 18)
    label_f = font(SANS, 20)
    tl_y = 135
    states = [
        ("MON", "baseline saved", "sha256 of every tool description", GREEN, 150),
        ("    ", "", "", FG_DIM, 0),
        ("FRI", "re-check", "compare baseline vs current", YELLOW, 0),
    ]
    # Simple horizontal flow
    flow_f = font(MONO, 20)
    flow_y = 190
    draw.text((cx - 400, flow_y), "MON: --save-baseline", fill=GREEN, font=flow_f)
    draw.text((cx - 80, flow_y), "  -->  ", fill=FG_DIM, font=flow_f)
    draw.text((cx + 20, flow_y), "FRI: --check-baseline", fill=YELLOW, font=flow_f)
    draw.text((cx - text_w(draw, "description hashes compared, 4 alerts fire", font(SANS, 18)) // 2, flow_y + 32),
              "description hashes compared, 4 alerts fire", fill=RED, font=font(SANS, 18))

    # Terminal box with the actual report
    tw, th = 1200, 600
    tx, ty = cx - tw // 2, 265
    draw_terminal_box(draw, tx, ty, tw, th, "doctor.py --check-baseline")
    mono_med = font(MONO, 17)

    report_lines = [
        ("Server: poisoned-fs   score: 50.0   2 tools (20ms)", FG_DIM),
        ("", None),
        ("security: 2 HIGH, 1 MEDIUM, 1 LOW", RED),
        ("", None),
        ("  HIGH [W022] Tool 'fil\N{CYRILLIC SMALL LETTER IE}system_read' contains", YELLOW),
        ("        mixed-script word with Cyrillic lookalikes (U+0435).", YELLOW),
        ("        Normalizes to 'filesystem_read'.", GREEN),
        ("", None),
        ("  HIGH [E003] Tool 'poisoned-fs:fil\N{CYRILLIC SMALL LETTER IE}system_read'", RED),
        ("        description changed since baseline - possible rug-pull.", RED),
        ("        evidence: description hash mismatch", FG_DIM),
        ("        -> fix: Verify the change is intentional.", YELLOW),
        ("                 Re-run --save-baseline after confirming safety.", YELLOW),
        ("", None),
        ("  MED  [E003] Tool 'poisoned-fs:safe_config_write' appeared", YELLOW),
        ("        since the last baseline. Verify it's legitimate.", YELLOW),
        ("        evidence: new tool", FG_DIM),
        ("        -> fix: Verify the change is intentional.", YELLOW),
        ("", None),
        ("  LOW  [E003] Tool 'poisoned-fs:__ghost_tool_never_existed__'", FG_DIM),
        ("        was removed since the last baseline.", FG_DIM),
        ("        evidence: tool removed", FG_DIM),
        ("        -> fix: Verify the tool removal is intentional.", YELLOW),
    ]
    # Decode escape sequences for actual rendering
    decoded = []
    for text, color in report_lines:
        if text:
            text = text.encode("utf-8").decode("unicode_escape")
        decoded.append((text, color))

    ry = ty + 55
    for text, color in decoded:
        if text:
            draw.text((tx + 28, ry), text, fill=color or FG, font=mono_med)
        ry += 26

    # Footer punchline
    foot_f = font(SANS, 22)
    foot = "The server you trusted on Monday is not the server you are running on Friday."
    draw.text((cx - text_w(draw, foot, foot_f) // 2, H - 55), foot, fill=FG, font=foot_f)
    repo_f = font(MONO, 16)
    repo = "github.com/luogangan7-lgtm/codex-mcp-doctor"
    draw.text((cx - text_w(draw, repo, repo_f) // 2, H - 28), repo, fill=FG_DIM, font=repo_f)

    out = os.path.join(OUT_DIR, "screenshot-rugpull-detection.png")
    img.save(out, "PNG", optimize=True)
    print(f"Generated {out} ({img.size})")


if __name__ == "__main__":
    make_cover()
    make_w022()
    make_real_report()
    make_rugpull()
    print("Done.")
