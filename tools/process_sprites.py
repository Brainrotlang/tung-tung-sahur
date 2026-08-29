#!/usr/bin/env python3
"""Turn generated art into the atlases and layers brainray can draw.

The image model emits ~1000px JPEGs on an approximately-magenta background,
with no alpha channel. rl_draw_texture_rec needs exact-size PNGs with real
transparency. This is the bridge.

    python3 tools/process_sprites.py

What it does, and why each step is not optional:

  key      The background is not the flat #FF00FF the prompt asked for, and it
           is not even consistent between batches: the first set of frames came
           back around (228,1,105), a pinkish red, and the second around
           (255,0,255). A key written for one silently passes the entire image
           through for the other -- so this matches the magenta *family*, red
           and blue high with green starved, rather than a colour.

  bleed    Downscaling averages neighbouring pixels. Without pushing foreground
           colour outward into the background first, every edge pixel picks up
           pink and keeps it through thresholding.

  scale    ONE scale factor across an animation, derived from the tallest
           frame, so the character does not change size between frames.

  anchor   Horizontally on the TORSO -- the columns opaque for most of the
           character's height -- not on the bounding box. A bat or a streaming
           tail swings the bounding box by tens of pixels; anchoring on it
           makes the body teleport sideways between frames. Vertically on the
           feet, which pins the character to the ground line.

  alpha    Forced to 0 or 255. Partial alpha over a dark sky reads as grime.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

TORSO_FRACTION = 0.60
BLEED_PASSES = 12
SCREEN_W = 1280          # must equal t_screen_w() in src/tune.brainrot

# name -> (source dir, frames, target height). Order is ANIMATION order.
#
# The swing is deliberately not bat1, bat2, bat3. Tung's attack has no windup
# time: t_attack_total() starts at 0.45s and the hitbox is live while it is
# above t_attack_active() (0.30s), so frame 0 is displayed exactly when the bat
# is hitting. Leading with the windup would be the animation lying about the
# gameplay. Strike, recoil, return.
#
# Heights are the game's own boxes: t_player_h() for Tung, kind_h() for the
# rest. Width falls out of the art's own proportions, which is why the tool
# prints the anchor column -- the draw call needs it.
CHARACTERS = {
    # NOT tung1..tung6. Filename order is not cycle order, and the frames
    # were measured rather than guessed: across the set the body bob
    # (head-top row) and the front foot's distance ahead of the torso both
    # order the same way, which is a real stride --
    #
    #   tung5  front foot +25, head 5   contact, foot planted well ahead
    #   tung6  front foot +23, head 5
    #   tung1  front foot +20, head 6   down, body at its lowest
    #   tung2  front foot +17, head 3   rising
    #   tung4  front foot +17, head 1
    #   tung3  front foot +10, head 0   pass, legs together, body highest
    #
    # then back to tung5 as the body falls into the next contact.
    #
    # Be aware this is ONE step, not two. A run cycle needs two passing
    # poses, one per leg, and this set has exactly one (tung3, the only
    # frame whose feet are together -- spread 10px against 47-61px for
    # every other frame). Ordering makes it a coherent stride instead of a
    # shuffle; it cannot make it a run. That needs the six distinct poses
    # the prompt in assets/PROMPTS.md asks for.
    "tung_run":    ("tung", ["tung5.jpg", "tung6.jpg", "tung1.jpg",
                             "tung2.jpg", "tung4.jpg", "tung3.jpg"], 96),
    "tung_jump":   ("tung", ["jump1.jpg", "jump2.jpg"], 96),
    "tung_swing":  ("tung", ["bat2.jpg", "bat3.jpg", "bat1.jpg"], 96),
    "patapim_run": ("brr-brr-patapim",
                    [f"brr{i}.jpg" for i in range(1, 6)], 64),
    "crate":       ("obstacles", ["crate.jpg"], 48),
    "post":        ("obstacles", ["post.jpg"], 96),
}

# Atlases drawn by the SAME call must share a frame width and anchor, or the
# game needs a different constant per animation and the character jumps size
# and position when it switches. Tung's three are one draw; everything else
# stands alone.
GROUPS = {
    "tung": ["tung_run", "tung_jump", "tung_swing"],
    "patapim": ["patapim_run"],
    "crate": ["crate"],
    "post": ["post"],
}

# Parallax layers, name -> on-screen height in pixels.
#
# Scaled to HEIGHT, not to the screen width, and tiled horizontally in the
# game. Scaling to width is what the first attempt did and it buried the
# scene: the foliage band came out 472px tall against a 96px character, so it
# covered the mountains, the palms, the houses and most of the player. The
# apparent height of a parallax layer is a composition decision; how many
# times it repeats to fill 1280px is not.
BACKGROUNDS = {
    "bg_far":  200,
    "bg_mid":  220,
    "bg_near": 190,
    "bg_fore": 110,
}


def key_background(path):
    """Foreground mask. True where the artwork is."""
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    bg = (r > 140) & (g < 110) & (b > 60) & ((r - g) > 90) & ((b - g) > 20)
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
    solid = alpha > 0
    ys, _ = np.where(solid)
    height = ys.max() - ys.min() + 1
    colsum = solid[ys.min():ys.max() + 1, :].sum(axis=0)
    torso = np.where(colsum > TORSO_FRACTION * height)[0]
    if torso.size == 0:
        _, xs = np.where(solid)
        return (xs.min() + xs.max()) // 2
    return (torso.min() + torso.max()) // 2


def to_rgba(rgb, mask):
    return Image.fromarray(
        np.dstack([bleed_edges(rgb, mask), (mask * 255).astype(np.uint8)]),
        "RGBA")


def binarise(img):
    arr = np.asarray(img).copy()
    arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
    return Image.fromarray(arr, "RGBA")


def render_frames(src_dir, files, frame_h, assets):
    """Key, scale and measure every frame of one animation."""
    frames = []
    for fn in files:
        path = os.path.join(assets, src_dir, fn)
        if not os.path.exists(path):
            sys.exit(f"missing source frame: {path}")
        rgb, mask = key_background(path)
        ys, _ = np.where(mask)
        frames.append(dict(rgb=rgb, mask=mask, h=ys.max() - ys.min() + 1))

    scale = frame_h / max(f["h"] for f in frames)

    out = []
    for f in frames:
        img = to_rgba(f["rgb"], f["mask"])
        small = binarise(img.resize(
            (max(1, round(img.width * scale)),
             max(1, round(img.height * scale))), Image.LANCZOS))
        a = np.asarray(small)[..., 3]
        if not (a > 0).any():
            sys.exit("nothing survived the key")
        ys, xs = np.where(a > 0)
        cx = torso_centre(a)
        out.append(dict(img=small, cx=cx, feet=ys.max(),
                        left=cx - xs.min(), right=xs.max() - cx))
    return out


def write_atlas(name, rendered, frame_w, frame_h, anchor, out_dir):
    sheet = Image.new("RGBA", (frame_w * len(rendered), frame_h), (0, 0, 0, 0))
    for i, f in enumerate(rendered):
        sheet.alpha_composite(f["img"],
                              (i * frame_w + anchor - f["cx"],
                               frame_h - 1 - f["feet"]))
    sheet.save(os.path.join(out_dir, name + ".png"))


def build_background(name, target_h, assets, out_dir):
    path = os.path.join(assets, "backgrounds", name + ".jpg")
    if not os.path.exists(path):
        sys.exit(f"missing background: {path}")
    rgb, mask = key_background(path)
    # Erode the mask by one pixel. JPEG leaves a rim of half-keyed pixels
    # around every edge, and on the dense foliage layer they survived as a
    # purple outline on each leaf tip -- background colour masquerading as
    # art. Losing an outer pixel is cheaper than keeping magenta.
    m = mask
    mask = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) \
             & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    ys, xs = np.where(mask)
    # Crop to the painted band. The upper part of each of these is magenta on
    # purpose: the sky is a cleared colour that changes with the level, not
    # art, so a layer painting its own sky would flatten that away.
    img = to_rgba(rgb, mask).crop(
        (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    w = max(1, round(img.width * target_h / img.height))
    out = binarise(img.resize((w, target_h), Image.LANCZOS))
    out.save(os.path.join(out_dir, name + ".png"))
    # A layer is tiled, so its two vertical edges have to join. Measure it
    # rather than assume it: compare the edge columns against an arbitrary
    # pair from the middle.
    a = np.asarray(out).astype(float)
    seam = np.abs(a[:, 0] - a[:, -1]).mean()
    ref = np.abs(a[:, w // 3] - a[:, 2 * w // 3]).mean()
    return w, target_h, seam, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="assets")
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print("characters and obstacles")
    for group, names in GROUPS.items():
        rendered = {n: render_frames(CHARACTERS[n][0], CHARACTERS[n][1],
                                     CHARACTERS[n][2], args.assets)
                    for n in names}
        every = [f for r in rendered.values() for f in r]
        pad_l = max(f["left"] for f in every)
        pad_r = max(f["right"] for f in every)
        frame_w = pad_l + pad_r + 1
        frame_h = CHARACTERS[names[0]][2]
        for n in names:
            write_atlas(n, rendered[n], frame_w, frame_h, pad_l, args.out)
            print(f"  {n:14s} {frame_w * len(rendered[n]):5d}x{frame_h:<4d}  "
                  f"{len(rendered[n])} frame(s) of {frame_w:3d}x{frame_h:<3d}")
        print(f"    -> group '{group}': frame {frame_w}x{frame_h}, "
              f"anchor col {pad_l}")

    print("\nparallax layers")
    for name, target_h in BACKGROUNDS.items():
        w, h, seam, ref = build_background(name, target_h, args.assets,
                                           args.out)
        verdict = "seamless" if seam < ref * 0.5 else "SEAM VISIBLE"
        print(f"  {name:14s} {w:5d}x{h:<4d}  tiles {SCREEN_W / w:4.1f}x across"
              f"  edge diff {seam:5.1f} vs {ref:5.1f} -> {verdict}")


if __name__ == "__main__":
    main()
