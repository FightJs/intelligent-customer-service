from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


CELL_W, CELL_H = 192, 208
COLS, ROWS = 8, 11
OUT = Path(__file__).resolve().parents[1] / "runs" / "node-ball"
ATLAS = OUT / "final" / "spritesheet-extended.png"
FRAMES = OUT / "qa" / "frames"

BG = (0, 0, 0, 0)
BODY = (207, 213, 223, 255)
BODY_HI = (242, 245, 249, 255)
INK = (13, 17, 24, 255)
BLUE = (59, 130, 246, 255)
BLUE_HI = (96, 165, 250, 255)
GREEN = (52, 211, 153, 255)
RED = (248, 113, 113, 255)
MUTED = (115, 115, 115, 255)


def rgba(rgb):
    return rgb


def draw_round(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def frame_canvas():
    return Image.new("RGBA", (CELL_W, CELL_H), BG)


def draw_node(img: Image.Image, *, state: str, t: float = 0.0, look: int = 0, lean: float = 0.0, phase: int = 0):
    """Deterministic vector mascot renderer; one coherent identity across all rows."""
    d = ImageDraw.Draw(img)
    cx = 96 + int(lean * 6)
    cy = 104 + int(math.sin(t * math.pi * 2) * 3)
    if state == "jumping":
        cy -= int(math.sin(t * math.pi) * 18)
    if state == "failed":
        cy += 8
    if state == "waiting":
        cy += 3

    # attached antenna / node
    antenna_dx = int(math.cos(math.radians(look)) * 18 + lean * 8)
    antenna_dy = int(-18 + math.sin(math.radians(look)) * 14)
    d.line((cx, cy - 70, cx + antenna_dx, cy + antenna_dy), fill=BODY_HI, width=7)
    d.ellipse((cx + antenna_dx - 10, cy + antenna_dy - 10, cx + antenna_dx + 10, cy + antenna_dy + 10), fill=BLUE if state not in {"failed", "waiting"} else (RED if state == "failed" else MUTED))

    # body
    r = 62
    body_top = cy - r
    body_bottom = cy + r
    draw_round(d, (cx - r, body_top, cx + r, body_bottom), 34, BODY, BODY_HI, 4)

    # inner core and status ring
    ring_color = BLUE
    if state == "failed":
        ring_color = RED
    elif state in {"idle", "waiting", "review"}:
        ring_color = GREEN if state == "review" else BLUE
    if state == "running":
        ring_color = BLUE_HI
    if state == "jumping":
        ring_color = BLUE_HI
    d.ellipse((cx - 45, cy - 45, cx + 45, cy + 45), fill=INK, outline=ring_color, width=6)

    # expressive eye direction: screen coordinates, 000=up clockwise.
    angle = math.radians(look)
    gaze_x = int(math.cos(angle) * 14)
    gaze_y = int(-math.sin(angle) * 14)
    if state == "failed":
        gaze_y = 9
    if state == "review":
        gaze_y = 6
    if state == "waiting":
        gaze_y = -4
    blink = state == "idle" and phase in {1, 4}
    eye_y = cy - 8
    if blink:
        d.line((cx - 25, eye_y, cx - 8, eye_y), fill=BLUE_HI, width=5)
        d.line((cx + 8, eye_y, cx + 25, eye_y), fill=BLUE_HI, width=5)
    else:
        for ex in (cx - 18, cx + 18):
            d.ellipse((ex - 10, eye_y - 13, ex + 10, eye_y + 13), fill=BODY_HI)
            d.ellipse((ex - 4 + gaze_x // 2, eye_y - 4 + gaze_y // 2, ex + 4 + gaze_x // 2, eye_y + 4 + gaze_y // 2), fill=ring_color)

    # mouth / state cue; no text or detached effects.
    if state == "failed":
        d.arc((cx - 18, cy + 12, cx + 18, cy + 34), 200, 340, fill=RED, width=4)
    elif state == "waiting":
        d.arc((cx - 17, cy + 8, cx + 17, cy + 30), 20, 160, fill=BLUE_HI, width=4)
    elif state == "review":
        d.line((cx - 13, cy + 24, cx + 13, cy + 24), fill=GREEN, width=4)
    else:
        d.arc((cx - 17, cy + 10, cx + 17, cy + 34), 200, 340, fill=ring_color, width=4)

    # small attached side nodes reinforce the system metaphor.
    side = 0 if state == "failed" else 1
    d.ellipse((cx - 71, cy - 7, cx - 55, cy + 9), fill=ring_color if side else RED)
    d.ellipse((cx + 55, cy - 7, cx + 71, cy + 9), fill=GREEN if state == "review" else ring_color)

    # motion state is expressed by body pose only.
    if state in {"running-right", "running-left"}:
        direction = 1 if state == "running-right" else -1
        step = -1 if phase % 2 else 1
        d.line((cx - 26, cy + 55, cx - 35 + step * 8 * direction, cy + 75), fill=BODY_HI, width=10)
        d.line((cx + 26, cy + 55, cx + 35 - step * 8 * direction, cy + 75), fill=BODY_HI, width=10)
    elif state == "waving":
        lift = 23 if phase in {1, 2} else 8
        d.line((cx + 48, cy + 12, cx + 67, cy - lift), fill=BODY_HI, width=13)
        d.ellipse((cx + 58, cy - lift - 8, cx + 76, cy - lift + 10), fill=ring_color)
    elif state == "running":
        d.line((cx - 48, cy + 30, cx - 66, cy + 46 - phase * 2), fill=BODY_HI, width=12)
        d.line((cx + 48, cy + 30, cx + 66, cy + 46 - (5 - phase) * 2), fill=BODY_HI, width=12)
    elif state == "jumping":
        d.line((cx - 42, cy + 46, cx - 55, cy + 70), fill=BODY_HI, width=10)
        d.line((cx + 42, cy + 46, cx + 55, cy + 70), fill=BODY_HI, width=10)


def render_frame(state: str, frame: int) -> Image.Image:
    img = frame_canvas()
    count = {"idle": 6, "running-right": 8, "running-left": 8, "waving": 4, "jumping": 5, "failed": 8, "waiting": 6, "running": 6, "review": 6}.get(state, 8)
    t = frame / max(1, count - 1)
    lean = math.sin(t * math.pi * 2) * 0.85
    if state == "running-right":
        lean = 0.6 + math.sin(t * math.pi * 2) * 0.25
    if state == "running-left":
        lean = -0.6 + math.sin(t * math.pi * 2) * 0.25
    if state == "failed":
        lean = math.sin(t * math.pi) * 0.22
    if state == "waving":
        lean = 0.15
    draw_node(img, state=state, t=t, lean=lean, phase=frame)
    return img


def render_look(frame: int) -> Image.Image:
    img = frame_canvas()
    look = (frame * 22.5) % 360
    draw_node(img, state="idle", t=0.15, look=look, lean=math.cos(math.radians(look)) * 0.14, phase=0)
    return img


def save_frame(img: Image.Image, state: str, frame: int):
    path = FRAMES / state / f"{frame:03d}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def main():
    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), BG)
    standard = [
        ("idle", 6),
        ("running-right", 8),
        ("running-left", 8),
        ("waving", 4),
        ("jumping", 5),
        ("failed", 8),
        ("waiting", 6),
        ("running", 6),
        ("review", 6),
    ]
    for row, (state, count) in enumerate(standard):
        for frame in range(count):
            img = render_frame(state, frame)
            atlas.paste(img, (frame * CELL_W, row * CELL_H), img)
            save_frame(img, state, frame)
        # v2 look-direction fallback uses row 0 column 6 as the neutral/front cell.
        if row == 0:
            neutral = render_frame("idle", 0)
            atlas.paste(neutral, (6 * CELL_W, row * CELL_H), neutral)
    for row, offset in ((9, 0), (10, 8)):
        state = f"look-{row}"
        for frame in range(8):
            img = render_look(offset + frame)
            atlas.paste(img, (frame * CELL_W, row * CELL_H), img)
            save_frame(img, state, frame)
    atlas.save(ATLAS)
    atlas.save(OUT / "final" / "spritesheet-extended.webp", "WEBP", lossless=True, quality=100)


if __name__ == "__main__":
    main()
