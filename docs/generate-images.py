#!/usr/bin/env python3
"""Generate marketing images for Devpost/GitHub.

Outputs:
  docs/devpost-cover.png      - 16:9 project card cover (1200x675)
  docs/w022-homoglyph.png     - W022 attack visualization (1200x675)

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

# Terminal palette (matches iTerm2 dark)
BG = (24, 24, 31)          # #18181f
BG_PANEL = (30, 30, 40)    # #1e1e28
FG = (220, 220, 230)       # text
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


def draw_terminal_box(draw, x, y, w, h, title=None):
    """Draw a terminal window frame."""
    # Window frame
    draw.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=BG_PANEL,
                           outline=(55, 55, 70), width=1)
    # Title bar dots
    if title is not None:
        dot_y = y + 18
        for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            draw.ellipse([x + 18 + i * 22, dot_y - 6, x + 30 + i * 22, dot_y + 6], fill=color)
        # Title text
        f = font(SANS, 14)
        draw.text((x + w // 2 - 80, dot_y - 8), title, fill=FG_DIM, font=f)


def make_cover():
    """Devpost project card cover - 16:9, hero composition."""
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Subtle top gradient band (purple-blue tint for visual interest)
    for i in range(120):
        alpha = int(40 * (1 - i / 120))
        draw.line([(0, i), (W, i)], fill=(BG[0] + alpha // 4, BG[1] + alpha // 5, BG[2] + alpha // 2))

    # Left side: title block
    title_f = font(SANS, 56)
    sub_f = font(SANS, 28)
    tag_f = font(MONO, 20)
    bullet_f = font(MONO, 18)

    # Badge row
    badges = [
        ("Codex Plugin", (16, 185, 129)),
        ("Zero Deps", (74, 222, 128)),
        ("285 Tests", (96, 165, 250)),
    ]
    bx = 60
    by = 70
    for label, color in badges:
        tw = draw.textlength(label, font=tag_f)
        draw.rounded_rectangle([bx, by, bx + tw + 24, by + 32], radius=16,
                               fill=(color[0] // 4, color[1] // 4, color[2] // 4),
                               outline=color, width=1)
        draw.text((bx + 12, by + 6), label, fill=color, font=tag_f)
        bx += tw + 36

    # Title
    draw.text((60, 140), "codex-mcp-doctor", fill=FG, font=title_f)
    # Subtitle (tagline)
    draw.text((60, 215), "`npm doctor` for MCP", fill=CYAN, font=sub_f)

    # One-liner
    desc_f = font(SANS, 20)
    draw.text((60, 265), "Diagnose broken servers, malicious tools,", fill=FG_DIM, font=desc_f)
    draw.text((60, 292), "and silent config failures - in one command.", fill=FG_DIM, font=desc_f)

    # Feature bullets (left column, lower)
    features = [
        ("L1-L4", "Connectivity, config, schema, security", BLUE),
        ("W022", "Cyrillic homoglyph attack detection", YELLOW),
        ("E003", "Rug-pull / tool-description drift", RED),
        ("Hook", "Auto-fires on every Codex session", GREEN),
    ]
    fy = 360
    for code, desc, color in features:
        draw.rounded_rectangle([60, fy, 120, fy + 28], radius=6, fill=color)
        draw.text((68, fy + 5), code, fill=(10, 10, 15), font=font(MONO, 15))
        draw.text((135, fy + 5), desc, fill=FG, font=bullet_f)
        fy += 42

    # Right side: mini terminal showing a sample report
    tx, ty, tw, th = 620, 150, 540, 440
    draw_terminal_box(draw, tx, ty, tw, th, "doctor.py --config real.toml")

    # Terminal content
    lines = [
        (">>> Diagnosing 3 servers...", FG_DIM, None),
        ("", None, None),
        ("  Servers: 3 total", FG, None),
        ("  healthy: 1  warnings: 1  broken: 1", FG_DIM, None),
        ("", None, None),
        ("  broken-path  RED 0.0", RED, None),
        ("    [command_not_found]", RED, None),
        ("    -> fix: reinstall server", FG_DIM, None),
        ("", None, None),
        ("  poisoned-fs  YEL 50.0", YELLOW, None),
        ("    [W022] Cyrillic homoglyph", YELLOW, None),
        ("    fil\N{CYRILLIC SMALL LETTER IE}system_read", RED, None),
        ("      -> filesystem_read", GREEN, None),
        ("", None, None),
        ("  filesystem  GRN 98.5", GREEN, None),
        ("    4 tools, all schemas valid", FG_DIM, None),
        ("", None, None),
        ("  RESULT: 1 broken, 1 attack found", RED, None),
    ]
    mono_small = font(MONO, 16)
    ly = ty + 50
    for text, color, _ in lines:
        if text:
            draw.text((tx + 20, ly), text, fill=color or FG, font=mono_small)
        ly += 21

    # Bottom strip
    foot_f = font(MONO, 14)
    draw.text((60, H - 35), "github.com/luogangan7-lgtm/codex-mcp-doctor", fill=FG_DIM, font=foot_f)
    draw.text((W - 200, H - 35), "OpenAI Build Week", fill=PURPLE, font=foot_f)

    out = os.path.join(OUT_DIR, "devpost-cover.png")
    img.save(out, "PNG", optimize=True)
    print(f"Generated {out} ({img.size})")


def make_w022():
    """W022 homoglyph attack visualization - shows the attack visually."""
    W, H = 1200, 675
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Title
    title_f = font(SANS, 36)
    draw.text((60, 40), "W022: Cyrillic Homoglyph Attack", fill=YELLOW, font=title_f)
    sub_f = font(SANS, 18)
    draw.text((60, 85), "Unique to codex-mcp-doctor. No other MCP scanner detects this.",
              fill=FG_DIM, font=sub_f)

    # Two-column comparison
    col_w = 520
    col_h = 380
    y0 = 130

    # Left column: what the attacker sends
    lx = 60
    draw_terminal_box(draw, lx, y0, col_w, col_h, "attacker-server (malicious)")
    big_mono = font(MONO, 42)
    label_f = font(SANS, 16)
    draw.text((lx + 20, y0 + 50), "Tool name the server exposes:", fill=FG_DIM, font=label_f)
    # Cyrillic e version
    cyr_text = "fil\N{CYRILLIC SMALL LETTER IE}system_read"
    draw.text((lx + 20, y0 + 85), cyr_text, fill=RED, font=big_mono)
    # annotation
    ann_f = font(MONO, 14)
    draw.text((lx + 20, y0 + 145), "              ^ this 'e' is U+0435", fill=RED, font=ann_f)
    draw.text((lx + 20, y0 + 165), "              (Cyrillic small ie)", fill=RED, font=ann_f)
    draw.text((lx + 20, y0 + 200), "Looks identical to filesystem_read", fill=FG, font=label_f)
    draw.text((lx + 20, y0 + 225), "in any code review, any terminal,", fill=FG, font=label_f)
    draw.text((lx + 20, y0 + 250), "any model context window.", fill=FG, font=label_f)
    draw.text((lx + 20, y0 + 300), "Intercepts file-read requests.", fill=RED, font=label_f)

    # Right column: what the doctor reports
    rx = 620
    draw_terminal_box(draw, rx, y0, col_w, col_h, "doctor.py output (the catch)")
    mono_med = font(MONO, 18)
    ry = y0 + 50
    report_lines = [
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
    for text, color in report_lines:
        if text:
            draw.text((rx + 20, ry), text, fill=color or FG, font=mono_med)
        ry += 24

    # Bottom: the punchline
    punch_f = font(SANS, 22)
    draw.text((60, H - 90), "The attacker disguised 'filesystem_read'.", fill=FG, font=punch_f)
    draw.text((60, H - 58), "The doctor reveals the normalized form - so you see intent, not cosmetics.",
              fill=CYAN, font=font(SANS, 18))

    out = os.path.join(OUT_DIR, "w022-homoglyph.png")
    img.save(out, "PNG", optimize=True)
    print(f"Generated {out} ({img.size})")


if __name__ == "__main__":
    make_cover()
    make_w022()
    print("Done.")
