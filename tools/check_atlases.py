#!/usr/bin/env python3
"""Assert the generated atlases still match the constants the game draws with.

process_sprites.py decides the frame size and anchor from the art's own
proportions, and tune.brainrot has to be told. Nothing connected the two, so
regenerating art at a different size silently desynced the draw call from the
atlas -- the sprite reads shifted or clipped, and no test noticed because the
headless harness swaps drawing for a no-op fake.

    python3 tools/check_atlases.py        # or: make check-atlases
"""

import re
import sys

from PIL import Image

TUNE = "src/tune.brainrot"


def const(text, name):
    m = re.search(rf"{name}\(\)\s*{{\s*bussin\s*([0-9.]+);", text)
    if not m:
        sys.exit(f"{TUNE}: no such constant {name}()")
    return float(m.group(1))


def main():
    t = open(TUNE).read()
    tw, th, ta = (const(t, n) for n in
                  ("t_sprite_w", "t_sprite_h", "t_sprite_anchor"))
    pw, ph, pa = (const(t, n) for n in
                  ("t_patapim_w", "t_patapim_h", "t_patapim_anchor"))

    # (atlas, frame w, frame h, frame count) -- the count is also a constant
    # the simulation indexes with, so a mismatch there shows a black frame.
    checks = [
        ("tung_run", tw, th, const(t, "t_run_frames")),
        ("tung_jump", tw, th, 2.0),
        ("tung_swing", tw, th, const(t, "t_swing_frames")),
        ("patapim_run", pw, ph, const(t, "t_patapim_frames")),
    ]

    bad = 0
    for name, fw, fh, n in checks:
        path = f"assets/{name}.png"
        try:
            w, h = Image.open(path).size
        except FileNotFoundError:
            print(f"  MISSING  {path}")
            bad += 1
            continue
        want = (int(fw * n), int(fh))
        if (w, h) != want:
            print(f"  MISMATCH {name}: atlas {w}x{h}, tune.brainrot implies "
                  f"{want[0]}x{want[1]} ({int(fw)}x{int(fh)} x{int(n)})")
            bad += 1
        else:
            print(f"  ok       {name} {w}x{h} ({int(n)} frames)")

    for label, anchor, fw in (("tung", ta, tw), ("patapim", pa, pw)):
        if not 0 <= anchor < fw:
            print(f"  MISMATCH {label} anchor {int(anchor)} outside frame "
                  f"width {int(fw)}")
            bad += 1

    if bad:
        sys.exit(f"\n{bad} problem(s). Re-run tools/process_sprites.py and "
                 f"copy the frame size and anchor it prints into {TUNE}.")
    print("atlases agree with tune.brainrot")


if __name__ == "__main__":
    main()
