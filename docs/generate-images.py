#!/usr/bin/env python3
"""Generate marketing images for Devpost/GitHub.

Outputs:
  docs/devpost-cover.png      - 5:3 project card cover (1500x900)
  docs/w022-homoglyph.png     - W022 attack visualization (1500x900)

Devpost image spec research: main images render at 5:3, and gallery
thumbnails center-crop to 1:1. All layouts are horizontally centered so
nothing important clips in the thumbnail crop.

Uses PIL (Pillow) which is NOT a project dependency - this is a build-time
tool for generating static assets, not runtime code. Run:
    python3 docs/generate-images.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

DOCS = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = DOCS

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
    """Devpost cover - 5:3 (1500x900), centered layout for thumbnail safety."""
    W, H = 1500, 900
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
        ("285 Tests", (96, 165, 250)),
    ]
    widths = [text_w(draw, t, tag_f) + 28 for t, _ in badges]
    total_w = sum(widths) + 24 * (len(badges) - 1)
    bx = cx - total_w // 2
    by = 95
    for (label, color), wd in zip(badges, widths):
        draw.rounded_rectangle([bx, by, bx + wd, by + 38], radius=19,
                               fill=(color[0] // 4, color[1] // 4, color[2] // 4),
                               outline=color, width=1)
        draw.text((bx + 14, by + 7), label, fill=color, font=tag_f)
        bx += wd + 24

    # Title (centered)
    title_f = font(SANS, 72)
    title = "codex-mcp-doctor"
    draw.text((cx - text_w(draw, title, title_f) // 2, 160), title, fill=FG, font=title_f)

    # Tagline
    sub_f = font(SANS, 36)
    tag = "'npm doctor' for MCP"
    draw.text((cx - text_w(draw, tag, sub_f) // 2, 255), tag, fill=CYAN, font=sub_f)

    # One-liner (two lines, centered)
    desc_f = font(SANS, 24)
    for i, line in enumerate([
        "Diagnose broken servers, malicious tools,",
        "and silent config failures - in one command.",
    ]):
        draw.text((cx - text_w(draw, line, desc_f) // 2, 315 + i * 32), line,
                  fill=FG_DIM, font=desc_f)

    # Mini terminal (centered)
    tw, th = 760, 300
    tx, ty = cx - tw // 2, 410
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
    cy = 740
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
    """W022 homoglyph attack visualization - 5:3, centered."""
    W, H = 1500, 900
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    cx = W // 2

    # Title (centered)
    title_f = font(SANS, 48)
    title = "W022: Cyrillic Homoglyph Attack"
    draw.text((cx - text_w(draw, title, title_f) // 2, 60), title, fill=YELLOW, font=title_f)
    sub_f = font(SANS, 22)
    sub = "Unique to codex-mcp-doctor. No other MCP scanner detects this."
    draw.text((cx - text_w(draw, sub, sub_f) // 2, 125), sub, fill=FG_DIM, font=sub_f)

    # Two-column comparison, centered as a unit
    col_w = 420
    col_h = 520
    gap = 60
    total = col_w * 2 + gap
    x0 = cx - total // 2
    lx = x0
    rx = x0 + col_w + gap
    y0 = 180

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


if __name__ == "__main__":
    make_cover()
    make_w022()
    print("Done.")
