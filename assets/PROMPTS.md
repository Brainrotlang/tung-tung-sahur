# Art generation prompts

Prompts for generating the game's sprites and parallax layers with ChatGPT's
image model, constrained to what `brainray` can actually draw.

Every number here is read from the source, not chosen for the prompt:
`src/tune.brainrot` (sizes, ground line), `src/curve.brainrot` (entity sizes,
sky palette), `src/draw.brainrot` (the placeholder colours the art must match).

---

## 0. Read this before you paste anything

**The image model cannot produce a game-ready sprite.** It emits ~1024px
images, no alpha channel, and it cannot hold an exact pixel grid. Asking it for
"a 48×96 PNG with transparency" produces a 1024×1024 JPEG-ish image of a sprite
sheet, which is useless to `rl_draw_texture_rec`.

So the prompts below are written for a **three-stage pipeline**, and they are
designed around the model's actual output:

1. **Generate** one frame at a time — not a sheet — large, centred, on flat
   magenta `#FF00FF`. Magenta because nothing in this game's palette is near it,
   so keying it out later can't eat the artwork.
2. **Process** offline: crop to content, resize to the exact target with nearest
   or area sampling, key out the magenta, quantise to the palette, force alpha
   to 0 or 255.
3. **Assemble** the atlas with a script. Frame packing is arithmetic; do not ask
   a language model to do arithmetic with pixels.

Generating one frame per prompt is slower and it is the only thing that works.
A 6-frame sheet asked for in one shot comes back with frames of different sizes,
different character proportions, and a grid that drifts.

### Engine constraints these prompts encode

| Constraint | Consequence for the art |
| --- | --- |
| `rl_draw_texture_rec` has **no scaling** | Sprites must be authored at exact final size. There is no "draw it big and shrink it" at runtime. |
| **No rotation** | Any tilt must be baked into a frame. |
| **Negative source width mirrors** | Author facing **right only**. Left-facing is free at runtime. |
| Tint is **multiplicative RGBA** | Author at full brightness and neutral hue. A tinted sprite can only get darker, never brighter. |
| Sky is `rl_clear_background`, **not art** | Parallax layers need a genuinely transparent upper region so the sky tier shows through. |
| Entities are placed at `y = 560 - height` | The sprite's **bottom row is the contact row**. No drop shadow below the feet — it would float above the ground line. |

### The palette

Anchored to what is already on screen, so new art doesn't fight the HUD and
ground that ship today.

| Role | RGB |
| --- | --- |
| Tung's wood | `196,148,92` |
| Tung's dark detail (eyes, mouth, grain) | `30,22,16` |
| Patapim's fur | `150,80,44` |
| Patapim's eyes | `240,240,240` |
| Patapim's mouth | `40,20,12` |
| Post | `120,110,96`, cap `150,138,120` |
| Crate | `96,92,100`, inner `76,72,80` |
| Ground | `34,28,24`, top stripe `58,48,38` |
| Sky, LVL 1–2 (03:30) | `12,14,34` |
| Sky, LVL 3–4 | `18,20,48` |
| Sky, LVL 5–6 | `38,30,64` |
| Sky, LVL 7 | `78,44,66` |
| Sky, LVL 8 (dawn) | `140,74,60` |
| Warm accent (lamps, HUD) | `240,150,40` |

**Everything is lit for 03:30 AM.** The sky behind it is `12,14,34` — nearly
black. Art that looks good on white will disappear. Every silhouette needs a
warm rim light from a street lamp, or it reads as a hole.

---

## 1. Shared preamble

Paste this **before** every individual asset prompt below.

```text
You are generating a single source image that I will downscale into a pixel-art
sprite for a 2D side-scrolling game. Follow these rules exactly; they are
technical requirements, not style preferences.

CANVAS
- Output one square image, one subject, centred, filling about 80% of the frame.
- Background: flat, uniform magenta #FF00FF. No gradient, no vignette, no
  texture, no shadow cast onto the background. The background must be a single
  exact colour so I can key it out.

STYLE
- Pixel art, chunky and readable at small size, in the spirit of 1990s arcade
  side-scrollers. Hard edges only.
- No anti-aliasing, no soft brushes, no blur, no glow bleed, no gradients.
- Limit the subject to at most 16 distinct colours.
- No outline in a colour that appears in the background.
- No text, no watermark, no signature, no UI, no frame or border.

LIGHTING
- Night scene, roughly 3:30 AM. The subject is lit by a warm orange street lamp
  (#F09628) from the upper right, against a near-black blue sky (#0C0E22).
- Give the subject a distinct warm rim light on its right edge so the silhouette
  separates from a very dark background.
- Do not paint a drop shadow beneath the subject. Ground contact is handled by
  the game.

FRAMING
- The subject must be complete and uncropped, with a few pixels of magenta on
  every side.
- Draw the subject facing RIGHT. I mirror it in the engine; never draw a
  left-facing version.
- Full front-on side view (true side elevation), no perspective, no three-quarter
  angle, no foreshortening.
```

---

## 2. Character sprites

### 2.1 Tung Tung Tung Sahur — run cycle

Final size **48 × 96** per frame, 6 frames → atlas `288 × 96`.

Run once per frame, changing only the bracketed line.

```text
SUBJECT
An anthropomorphic wooden kentongan drum: a tall upright log with a vertical
carved slit down its front, standing on two thin bare legs, with two thin arms.
The wood is warm mid-brown (#C4945C) with darker grain lines (#1E1610). It has
two small dark rectangular eyes and a simple flat dark mouth carved into the
upper third. It carries a pale wooden baseball bat in its right hand, held low
and back, not raised.

The body is tall and narrow: roughly twice as tall as it is wide. Legs are short
and stick-like. The head is not a separate shape — the face is carved into the
top of the log itself.

POSE
[FRAME 1 of a 6-frame run cycle: contact pose, right leg forward and heel just
landing, left leg extended back, body upright, slight forward lean.]

The character is running to the right. Keep the body's size, proportions, colours
and bat identical across every frame of this cycle; only the limbs and vertical
bob change.
```

The six bracketed poses:

1. `contact pose, right leg forward and heel just landing, left leg extended back, body upright, slight forward lean`
2. `down pose, weight fully on the right leg which is bent absorbing impact, body at its lowest point, left leg beginning to swing forward`
3. `pass pose, right leg straight and vertical under the body, left knee lifted and passing forward, body rising`
4. `up pose, body at its highest point, pushing off the right toe, left leg reaching forward`
5. `contact pose mirrored, left leg forward and heel just landing, right leg extended back`
6. `down pose mirrored, weight on the bent left leg, body at its lowest point, right leg swinging forward`

### 2.2 Tung — jump

Final size **48 × 96**, 2 frames → atlas `96 × 96`.

```text
SUBJECT
[same subject paragraph as 2.1]

POSE
[FRAME 1: rising through a jump — both legs tucked up beneath the body, knees
bent, arms slightly raised for balance, bat still held low, body tilted very
slightly back.]

The character is airborne, moving right and upward.
```

Frame 2: `falling from a jump — legs beginning to extend downward and reach for
the ground, arms lowering, body tilted very slightly forward`.

### 2.3 Tung — bat swing

Final size **48 × 96**, 3 frames → atlas `144 × 96`.

The bat's live hitbox is 56 px wide starting 40 px right of Tung's left edge, so
**the bat must visibly extend past the body's right edge in the active frame** —
what the player sees has to match what actually collides.

```text
SUBJECT
[same subject paragraph as 2.1]

POSE
[FRAME 2 of a 3-frame bat swing: the ACTIVE frame. The bat is fully extended
horizontally to the right at mid-body height, arms straight, body braced with
feet planted. The bat must clearly extend well beyond the right edge of the
body — it is the part that hits things.]

The character is standing and swinging to the right.
```

- Frame 1 (windup): `bat drawn back low behind the body to the left, weight
  shifted back onto the rear foot, body coiled`
- Frame 3 (recovery): `bat past full extension and dropping, angled down to the
  right, arms relaxing, body returning upright`

### 2.4 Brr Brr Patapim — run cycle

Final size **64 × 64** per frame, 4 frames → atlas `256 × 64`.

Squat and wide, unlike Tung. That silhouette contrast is the point: the player
has to tell "jump it" from "bonk it" in a fraction of a second at 900 px/s.

```text
SUBJECT
A squat, wide, four-limbed forest creature: a brown monkey-like body (#96502C)
with a broad chest, long arms, short legs, and a long curling tail. It has an
angry expression with two large white eyes (#F0F0F0) and a wide dark open mouth
(#281410) showing teeth. Small tufts of dark green foliage sprout from its
shoulders and the top of its head, as if it is part animal and part bush.

The body is as wide as it is tall — a compact square silhouette, deliberately
unlike a tall thin character.

POSE
[FRAME 1 of a 4-frame charge cycle: front limbs reaching forward and down, rear
legs pushed back, body low and lunging, tail streaming behind.]

The creature is charging to the right on all fours, aggressive and fast.
```

The four bracketed poses:

1. `front limbs reaching forward and down, rear legs pushed back, body low and lunging, tail streaming behind`
2. `front limbs planted, body compressed over them at its lowest, rear legs gathering underneath`
3. `body extended and airborne at the top of the bound, all four limbs off the ground, tail arced up`
4. `rear legs driving off, front limbs beginning to reach forward again, body rising`

---

## 3. Obstacle sprites

### 3.1 Crate — `48 × 48`, single frame

```text
SUBJECT
A small square shipping crate seen from the side, made of grey-brown planks
(#605C64) with a darker recessed centre panel (#4C4850) and visible plank seams
and corner brackets. Weathered and slightly battered. It sits flat on the ground.

The crate is a perfect square in silhouette and completely fills the frame's
subject area.
```

### 3.2 Post — `40 × 96`, single frame

Deliberately tall and narrow, so it reads as "jump" from a distance.

```text
SUBJECT
A tall narrow wooden fence post standing upright, pale weathered grey-brown
timber (#786E60) with a slightly lighter flat cap on top (#968A78), visible
vertical wood grain, and a couple of rusted nails. It is planted in the ground.

The post is roughly two and a half times taller than it is wide, a simple
vertical column.
```

---

## 4. Background — parallax layers

Four layers, each **1280 px wide** and **horizontally tileable**: the right edge
must continue seamlessly into the left edge, because the layer is drawn twice
side by side and scrolled.

The sky is **not** art — it is a solid `rl_clear_background` colour that changes
with the level. Each layer's upper region must therefore be genuinely empty
(magenta), not painted with a sky.

| Layer | Size | Scroll rate | Content |
| --- | --- | --- | --- |
| `bg_far` | 1280 × 200 | 0.10 × world | Distant mountains |
| `bg_mid` | 1280 × 220 | 0.25 × world | Palm treeline |
| `bg_near` | 1280 × 180 | 0.50 × world | Village houses |
| `bg_fore` | 1280 × 72 | 1.00 × world | Foreground foliage |

Each layer's **bottom row sits on the ground line** at y = 560, except
`bg_fore`, which overlaps the ground band.

Generate these as **wide** images, not square — override the preamble's canvas
rule with the one in each prompt.

### 4.1 `bg_far` — mountains

```text
CANVAS OVERRIDE
Output a wide panoramic image with a 16:2.5 aspect ratio. The top 45% must be
flat uniform magenta #FF00FF with nothing drawn in it. The subject occupies the
lower portion only.

SUBJECT
A distant mountain range silhouette at night, seen from far away. Very low
contrast and desaturated — deep blue-grey (#1E2340), barely lighter than the
night sky, with the faintest warm hint (#3A2F3E) on the right-facing slopes.
No detail, no trees, no texture: these are distant shapes, almost flat.

The bottom edge of the image must be solid mountain base, not magenta.

TILING
The image must tile seamlessly when repeated horizontally: the terrain silhouette
at the extreme left edge must continue exactly into the terrain at the extreme
right edge, with no seam, no repeated landmark, and no peak cut in half at either
edge.
```

### 4.2 `bg_mid` — palm treeline

```text
CANVAS OVERRIDE
Output a wide panoramic image with a 16:2.75 aspect ratio. The top 40% must be
flat uniform magenta #FF00FF with nothing drawn in it.

SUBJECT
A row of coconut palm trees at night, seen in near-silhouette. Dark blue-green
trunks and fronds (#1A2B28) with a thin warm rim light (#8A5A2E) on the right
edge of each trunk from a distant street lamp. Palms of varying heights and
lean, some clustered, some isolated, with low scrubby undergrowth between them.

The bottom edge must be solid undergrowth, not magenta.

TILING
The image must tile seamlessly when repeated horizontally: the left and right
edges must join with no visible seam and no palm cut in half at either edge.
```

### 4.3 `bg_near` — village houses

Where the warm light lives — every lit window is a reason to keep running east.

```text
CANVAS OVERRIDE
Output a wide panoramic image with a 16:2.25 aspect ratio. The top 35% must be
flat uniform magenta #FF00FF with nothing drawn in it.

SUBJECT
A row of small Indonesian village houses at night: simple single-storey timber
buildings with steep pitched terracotta roofs (#4A2A22), dark plank walls
(#2A2018), and small square windows glowing warm orange (#F09628) as if lamps
are lit inside. A few narrow gaps between houses. One tall street lamp on a thin
post casting a warm pool of light. Low, modest, quiet — a sleeping neighbourhood.

The bottom edge must be solid house bases and ground, not magenta.

TILING
The image must tile seamlessly when repeated horizontally: the left and right
edges must join with no visible seam and no house cut in half at either edge.
```

### 4.4 `bg_fore` — foreground foliage

```text
CANVAS OVERRIDE
Output a wide panoramic image with a 16:0.9 aspect ratio. The top 30% must be
flat uniform magenta #FF00FF with nothing drawn in it.

SUBJECT
A low band of dark tropical foliage seen close up: broad banana-leaf and fern
shapes in near-black green (#141E18), with occasional warm orange edge highlights
(#8A5A2E) catching lamp light. Almost silhouette — this sits closest to the
camera and must never compete with the character for attention.

The bottom edge must be solid dense foliage, not magenta.

TILING
The image must tile seamlessly when repeated horizontally, with no visible seam
and no leaf cut in half at either edge.
```

---

## 5. Acceptance checklist

Check each processed asset before it goes in the repo. Most of these are
scriptable, and should be scripted.

**Every sprite**

- [ ] Exact pixel dimensions (`48×96`, `64×64`, `48×48`, `40×96`, atlas widths as listed)
- [ ] Every pixel's alpha is exactly 0 or 255 — no partial transparency
- [ ] No magenta survives anywhere, including single fringe pixels
- [ ] ≤ 16 distinct RGB values
- [ ] Subject faces right
- [ ] Bottom row contains opaque pixels — the character stands on it, and a
      one-pixel gap makes everything hover above the ground line
- [ ] Nothing painted below the feet

**Every animation atlas**

- [ ] Width is exactly `frame_width × frame_count`
- [ ] Every frame's subject occupies the same vertical band — flipbook them; if
      the character jitters, the frames are misaligned, not "lively"
- [ ] Colours identical across frames of one cycle

**Every parallax layer**

- [ ] Exactly 1280 px wide
- [ ] Tiles seamlessly: concatenate the image with itself and confirm no seam
- [ ] Upper region fully transparent, so the sky tier shows through
- [ ] Bottom row fully opaque

**In-game**

- [ ] Readable against the LVL 1 sky (`12,14,34`) — the hardest case, and the
      first thing a player sees
- [ ] Still readable against the LVL 8 dawn sky (`140,74,60`)
- [ ] Tung and Patapim are distinguishable by silhouette alone at 900 px/s

---

## 6. What this does not cover

Sprites for the M1 Patapim variants (small, big, jumping, armored) and the M2
bosses — Tralalero Tralala and Bombardiro Crocodilo — are deliberately out of
scope until the base set is in the game and proven. Armored Patapim in particular
needs a silhouette that reads as *unbonkable* before it is worth drawing, and
that is a design question rather than a prompting one.
