#!/usr/bin/env python3
"""Turn generated art into the atlases and layers rayrot can draw.

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

# name -> (source dir, frames, target height). Order is ANIMATION order, and
# in no case is it filename order -- see each entry for what was measured.
#
# Heights are the game's own boxes: t_player_h() for Tung, kind_h() for the
# rest. Width falls out of the art's own proportions, which is why the tool
# prints the frame size and anchor column -- tune.brainrot needs both
# (t_sprite_w/t_sprite_anchor, t_patapim_w/t_patapim_anchor).
CHARACTERS = {
    # Ordered by MEASUREMENT, not by filename.
    #
    # The property that matters in a runner is that the planted foot's
    # contact point sweeps monotonically BACKWARD relative to the torso.
    # If it does not, the feet skate. In every frame but running6 the
    # frontmost foot is the planted one, so its offset from the torso
    # centre is the contact point, and sorting on it descending gives:
    #
    #   running4  +60   full reach, foot furthest ahead
    #   running1  +36   planted forward
    #   running3  +34
    #   running5   +7   gathering
    #   running2   +5   passing
    #   running6  -65   toe-off -- the only frame with the BACK foot
    #                   planted, and the lowest hip of the six
    #
    # running5/running2 differ by only 674 pixels, so the cycle holds
    # very briefly at the passing pose. That is the art, not the order.
    "tung_run":    ("tung-tung-tung",
                    ["running4.jpg", "running1.jpg", "running3.jpg",
                     "running5.jpg", "running2.jpg", "running6.jpg"], 96),

    # jump1 is the tuck (hip 19px above the feet), jump2 the extension
    # (24px) -- rising then falling, which is the order jump_frame()
    # asks for: index 0 while vy < 0.
    "tung_jump":   ("tung-tung-tung", ["jump1.jpg", "jump2.jpg"], 96),

    # Strike first, and not for tidiness: t_attack_total() is 0.45s and
    # the hitbox is live while atk_t is above t_attack_active() (0.30s),
    # so frame 0 is on screen exactly when the bat is connecting. Leading
    # with a windup would be the animation lying about the gameplay.
    # Measured by how far the bat reaches past the torso:
    #
    #   swing2  bat tip +130   the strike
    #   swing3  bat tip -112   follow-through, swung across the body
    #   swing1  bat tip  +91   returning to rest at the side
    "tung_swing":  ("tung-tung-tung",
                    ["swing2.jpg", "swing3.jpg", "swing1.jpg"], 96),

    # A quadruped bound, ordered on the same contact-sweep rule:
    # patapim4 +29 (body up, limbs gathered), patapim2 +13 (forelimbs
    # planting, spread at its widest 201), patapim1 +13 (all fours down),
    # patapim3 -60 (push-off, spread collapsed to 101).
    "patapim_run": ("patapim",
                    ["patapim4.jpg", "patapim2.jpg",
                     "patapim1.jpg", "patapim3.jpg"], 64),

    # The two boss poses, not a locomotion cycle: frame 0 is the survive
    # phase (8s per cycle, cannot be hit), frame 1 the opening (1s, three
    # times a fight, the bat connects). tralalero2's jaws are wide open --
    # that IS the tell, and it is the whole reason the fight is readable.
    #
    # Target height is t_shark_h(). The art comes out WIDER than the 140px
    # collision box because a shark's snout and tail overhang it, which is
    # the same split Tung already has (112px of art over a 48px box).
    "tralalero":   ("tralalero", ["tralalero1.jpg", "tralalero2.jpg"], 96),

    # Bombardiro. Frame 0 is level cruise seen side-on, frame 1 the opening:
    # pitched up and banked with the jaws open. Those are different VIEWS,
    # not different poses, so their silhouettes have very different aspect
    # ratios (4.22 vs 1.39) -- see ALIGN below for the consequence.
    # ALIGN "centre", not the default "feet". Everything else in this game
    # stands on the ground, so its bottom row is its contact row. A flying
    # boss has no contact row, and bottom-aligning these two would be
    # actively wrong: frame 0 is 36px of content in a 72px frame, so the
    # plane would sit in the box's lower half and then jump 36px upward the
    # instant the opening starts.
    "bombardiro":  ("bombardino",
                    ["bombardino1.jpg", "bombardino2.jpg"], 72, "centre"),

    # U DIN DIN -- the final-level boss. A six-frame charge animation (a buff
    # orange sprinter). draw.brainrot cycles the frames while he charges and
    # MIRRORS the whole sprite by charge direction so he always faces the way
    # he is going; the "trembling" tell reuses the frames with a shake. He is
    # bonkable throughout the charge, not in a separate open window, so there
    # is no closed/open pose split like the other two bosses. Height
    # t_dindin_h().
    "dindin":      ("dimdim", ["dindin1.png", "dindin2.png", "dindin3.png",
                               "dindin4.png", "dindin5.png", "dindin6.png"], 96),

    "bomb":        ("bombardino", ["bomb.jpg"], 26),
    "blast":       ("bombardino", ["blast.jpg"], 34),

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
    "tralalero": ["tralalero"],
    "bombardiro": ["bombardiro"],
    "dindin": ["dindin"],
    "bomb": ["bomb"],
    "blast": ["blast"],
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


# A frame whose character is more than this far from the animation's median
# size was drawn at a different zoom, and is corrected before the shared
# scale is applied. Below it, the difference is pose (a crouch is genuinely
# shorter) and must NOT be corrected -- that would make the character
# breathe.
ZOOM_TOLERANCE = 0.12


def render_frames(src_dir, files, frame_h, assets):
    """Key, scale and measure every frame of one animation."""
    frames = []
    for fn in files:
        path = os.path.join(assets, src_dir, fn)
        if not os.path.exists(path):
            sys.exit(f"missing source frame: {path}")
        rgb, mask = key_background(path)
        ys, _ = np.where(mask)
        # sqrt(area), not bounding-box height, as the character's size: area
        # barely moves between poses, while a crouch shortens the box by a
        # third. That is what makes the outlier test below safe to apply.
        frames.append(dict(rgb=rgb, mask=mask, h=ys.max() - ys.min() + 1,
                           size=float(np.sqrt(mask.sum()))))

    # ONE scale across an animation, so the character does not change size
    # between frames -- with one exception. The generator does not always
    # return the same canvas: patapim1.jpg came back 784x1168 where its
    # siblings were 1152x1712, framed identically but 0.72x as many pixels.
    # A single scale derived from the tallest frame then rendered it
    # visibly smaller than the rest of its own run cycle. Frames far enough
    # from the median get brought to it first; everything else is untouched.
    median = float(np.median([f["size"] for f in frames]))
    for f in frames:
        ratio = f["size"] / median
        f["zoom"] = 1.0 / ratio if abs(ratio - 1.0) > ZOOM_TOLERANCE else 1.0

    scale = frame_h / max(f["h"] * f["zoom"] for f in frames)

    out = []
    for f in frames:
        img = to_rgba(f["rgb"], f["mask"])
        fs = scale * f["zoom"]
        small = binarise(img.resize(
            (max(1, round(img.width * fs)),
             max(1, round(img.height * fs))), Image.LANCZOS))
        a = np.asarray(small)[..., 3]
        if not (a > 0).any():
            sys.exit("nothing survived the key")
        ys, xs = np.where(a > 0)
        cx = torso_centre(a)
        out.append(dict(img=small, cx=cx, feet=ys.max(),
                        left=cx - xs.min(), right=xs.max() - cx))
    return out


def write_atlas(name, rendered, frame_w, frame_h, anchor, out_dir,
                align="feet"):
    """Pack frames into one row.

    `align` is "feet" for anything that stands on the ground -- its bottom
    row is its contact row, and a one-pixel gap makes it hover. "centre" is
    for things that fly, which have no contact row; bottom-aligning those
    makes a short frame sink to the floor of its own box.
    """
    sheet = Image.new("RGBA", (frame_w * len(rendered), frame_h), (0, 0, 0, 0))
    for i, f in enumerate(rendered):
        if align == "centre":
            top = (frame_h - f["img"].height) // 2
        else:
            top = frame_h - 1 - f["feet"]
        sheet.alpha_composite(f["img"], (i * frame_w + anchor - f["cx"], top))
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
        align = {n: (CHARACTERS[n][3] if len(CHARACTERS[n]) > 3 else "feet")
                 for n in names}
        every = [f for r in rendered.values() for f in r]
        pad_l = max(f["left"] for f in every)
        pad_r = max(f["right"] for f in every)
        frame_w = pad_l + pad_r + 1
        frame_h = CHARACTERS[names[0]][2]
        for n in names:
            write_atlas(n, rendered[n], frame_w, frame_h, pad_l, args.out,
                        align[n])
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
