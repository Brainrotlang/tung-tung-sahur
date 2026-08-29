#!/usr/bin/env python3
"""Turn generated art into sprite atlases brainray can draw.

The image model emits ~1000px JPEGs on an approximately-magenta background,
with no alpha channel. rl_draw_texture_rec needs exact-size PNGs with real
transparency, laid out in a strip. This is the bridge.

    python3 tools/process_sprites.py assets/tung --out assets

What it does, and why each step is not optional:

  key      The background is nowhere near a flat #FF00FF -- JPEG and model
           drift make it a gradient around (228,1,105) that differs per file.
           So the key is a tolerance on "red-dominant, green-starved" rather
           than an exact colour match.

  bleed    Downscaling averages neighbouring pixels. Without pushing the
           foreground colour outward into the background first, every edge
           pixel picks up pink and the sprite gets a magenta halo that
           survives thresholding.

  scale    ONE scale factor for every frame, derived from the tallest, so the
           character does not change size between frames.

  anchor   Horizontally on the TORSO -- the columns opaque for most of the
           character's height -- not on the bounding box. The bat swings the
           bounding box around by tens of pixels; anchoring on it makes the
           body teleport sideways when the animation changes. Vertically on
           the feet, which pins the character to the ground line.

  alpha    Forced to 0 or 255. Partial alpha over a dark sky reads as grime.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

FRAME_H = 96          # must equal t_player_h() in src/tune.brainrot
TORSO_FRACTION = 0.60  # a column is "torso" if opaque for this much of the height
BLEED_PASSES = 12

# Which files make which atlas. Order is animation order.
ATLASES = {
    "tung_run":   [f"tung{i}.jpg" for i in range(1, 7)],
    "tung_jump":  ["jump1.jpg", "jump2.jpg"],
    "tung_swing": ["bat1.jpg", "bat2.jpg"],
}


def key_background(path):
    """Foreground mask. True where the artwork is."""
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    bg = (r > 140) & (g < 100) & (b < r) & (b > 20) & ((r - g) > 90)
    return rgb.astype(np.uint8), ~bg


def bleed_edges(rgb, mask, passes=BLEED_PASSES):
    out = rgb.astype(np.float32).copy()
    filled = mask.copy()
    for _ in range(passes):
        if filled.all():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(filled.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(out, (dy, dx), (0, 1)) * \
                np.roll(filled, (dy, dx), (0, 1)).astype(np.float32)[..., None]
            cnt += np.roll(filled, (dy, dx), (0, 1)).astype(np.float32)
        new = (~filled) & (cnt > 0)
        out[new] = acc[new] / cnt[new][:, None]
        filled |= new
    return out.astype(np.uint8)


def torso_centre(alpha):
    """Centre column of the character's trunk, ignoring limbs and the bat."""
    solid = alpha > 0
    ys, _ = np.where(solid)
    top, bot = ys.min(), ys.max()
    height = bot - top + 1
    colsum = solid[top:bot + 1, :].sum(axis=0)
    torso = np.where(colsum > TORSO_FRACTION * height)[0]
    if torso.size == 0:                       # fall back to the bbox
        _, xs = np.where(solid)
        return (xs.min() + xs.max()) // 2
    return (torso.min() + torso.max()) // 2


def load_frames(src_dir, files):
    out = []
    for name in files:
        path = os.path.join(src_dir, name)
        if not os.path.exists(path):
            sys.exit(f"missing source frame: {path}")
        rgb, mask = key_background(path)
        ys, xs = np.where(mask)
        out.append(dict(name=name, rgb=rgb, mask=mask,
                        y0=ys.min(), y1=ys.max(), x0=xs.min(), x1=xs.max()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="directory of generated frames")
    ap.add_argument("--out", default="assets", help="where to write atlases")
    args = ap.parse_args()

    every = {n: load_frames(args.src, f) for n, f in ATLASES.items()}
    flat = [f for group in every.values() for f in group]

    # One scale for all of them, so the character never changes size.
    tallest = max(f["y1"] - f["y0"] + 1 for f in flat)
    scale = FRAME_H / tallest

    # Render each frame small, then measure how far it reaches from its torso
    # centre. That decides the frame width -- large enough for the longest
    # bat reach, identical for every atlas so the draw offset is one number.
    rendered = []
    for f in flat:
        rgba = np.dstack([bleed_edges(f["rgb"], f["mask"]),
                          (f["mask"] * 255).astype(np.uint8)])
        img = Image.fromarray(rgba, "RGBA")
        small = img.resize((max(1, round(img.width * scale)),
                            max(1, round(img.height * scale))), Image.LANCZOS)
        arr = np.asarray(small).copy()
        arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
        small = Image.fromarray(arr, "RGBA")
        a = arr[..., 3]
        if not (a > 0).any():
            sys.exit(f"{f['name']}: nothing survived the key")
        ys, xs = np.where(a > 0)
        cx = torso_centre(a)
        f.update(img=small, left=cx - xs.min(), right=xs.max() - cx,
                 feet=ys.max(), cx=cx)
        rendered.append(f)

    pad_l = max(f["left"] for f in rendered)
    pad_r = max(f["right"] for f in rendered)
    frame_w = pad_l + pad_r + 1
    anchor = pad_l

    os.makedirs(args.out, exist_ok=True)
    for atlas, files in ATLASES.items():
        group = every[atlas]
        sheet = Image.new("RGBA", (frame_w * len(group), FRAME_H), (0, 0, 0, 0))
        for i, f in enumerate(group):
            sheet.alpha_composite(f["img"],
                                  (i * frame_w + anchor - f["cx"],
                                   FRAME_H - 1 - f["feet"]))
        path = os.path.join(args.out, atlas + ".png")
        sheet.save(path)
        print(f"{path}  {sheet.width}x{sheet.height}  "
              f"{len(group)} frames of {frame_w}x{FRAME_H}")

    # The engine needs to know where to put it. The hitbox is t_player_w()
    # wide at t_player_x(); the art is wider and centred on the same torso.
    print(f"\nframe size      {frame_w} x {FRAME_H}")
    print(f"torso anchor    column {anchor}")
    print(f"draw offset     x = t_player_x() + t_player_w()/2 - {anchor}")
    print(f"                y = player y  (feet already on the bottom row)")


if __name__ == "__main__":
    main()
