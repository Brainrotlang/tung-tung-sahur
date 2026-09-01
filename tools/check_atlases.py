#!/usr/bin/env python3
"""Assert every generated image still matches the constants the game draws with.

process_sprites.py decides each atlas's frame size and anchor, and each
parallax layer's tile width, from the art's own proportions. tune.brainrot has
to be *told*. Nothing connected the two, so regenerating art at a different
size silently desynced the draw call from the image -- and no test noticed,
because the headless harness swaps drawing for a no-op fake.

That is not hypothetical twice over. Patapim's frame width was a literal in
draw.brainrot. And regenerating bg_near.png from an updated source took it from
503px to 698px wide while draw_background() kept asking for 503, so 195px of
every house strip was sliced off and the cut edge butted against the next tile.
The layer check below exists because of that.

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
        ("tralalero", const(t, "t_shark_frame_w"),
         const(t, "t_shark_frame_h"), const(t, "t_shark_frames")),
        ("bombardiro", const(t, "t_croc_frame_w"),
         const(t, "t_croc_frame_h"), const(t, "t_croc_frames")),
        ("dindin", const(t, "t_dindin_frame_w"),
         const(t, "t_dindin_frame_h"), const(t, "t_dindin_frames")),
        ("combinacion", const(t, "t_combi_frame_w"),
         const(t, "t_combi_frame_h"), const(t, "t_combi_frames")),
        ("bomb", const(t, "t_bomb_frame_w"),
         const(t, "t_bomb_frame_h"), 1.0),
        ("blast", const(t, "t_blast_frame_w"),
         const(t, "t_blast_frame_h"), 1.0),
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

    for label, anchor, fw in (("tung", ta, tw), ("patapim", pa, pw),
                              ("tralalero", const(t, "t_shark_anchor"),
                               const(t, "t_shark_frame_w")),
                              ("bombardiro", const(t, "t_croc_anchor"),
                               const(t, "t_croc_frame_w")),
                              ("dindin", const(t, "t_dindin_anchor"),
                               const(t, "t_dindin_frame_w")),
                              ("combinacion", const(t, "t_combi_anchor"),
                               const(t, "t_combi_frame_w"))):
        if not 0 <= anchor < fw:
            print(f"  MISMATCH {label} anchor {int(anchor)} outside frame "
                  f"width {int(fw)}")
            bad += 1

    # Parallax layers. draw_layer() passes the width to rl_draw_texture_rec()
    # as BOTH the source rectangle and the tile stride, so it has to be the
    # PNG's exact width -- an approximation crops or pads every single tile.
    for layer in ("far", "mid", "near", "fore"):
        path = f"assets/bg_{layer}.png"
        lw = const(t, f"t_bg_{layer}_w")
        lh = const(t, f"t_bg_{layer}_h")
        try:
            w, h = Image.open(path).size
        except FileNotFoundError:
            print(f"  MISSING  {path}")
            bad += 1
            continue
        if (w, h) != (int(lw), int(lh)):
            lost = w - int(lw)
            how = (f"cropping {lost}px off every tile" if lost > 0
                   else f"padding {-lost}px past the texture on every tile")
            print(f"  MISMATCH bg_{layer}: png {w}x{h}, tune.brainrot says "
                  f"{int(lw)}x{int(lh)} -- {how}")
            bad += 1
        else:
            print(f"  ok       bg_{layer} {w}x{h}")

    if bad:
        sys.exit(f"\n{bad} problem(s). Re-run tools/process_sprites.py and "
                 f"copy the sizes it prints into {TUNE}.")
    print("atlases and parallax layers agree with tune.brainrot")


if __name__ == "__main__":
    main()
