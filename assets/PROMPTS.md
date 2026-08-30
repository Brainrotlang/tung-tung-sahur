# Art generation prompts

Prompts for generating the game's sprites and parallax layers with ChatGPT's
image model, constrained to what `rayrot` can actually draw.

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

## 4. Boss sprites

The two M2 set pieces (DESIGN.md §12). **Both are drawn from art now**, as are
the bomb and its blast. The `tex >= 0` fallback stays in the code so a missing
file degrades one asset at a time rather than crashing.

### 4.0 What the engine gives them

| | Tralalero Tralala | Bombardiro Crocodilo |
| --- | --- | --- |
| Frame size | **140 × 96** | **120 × 72** |
| Where it lives | on the ground, `y = 560 − 96` | in the air, `y = 90` cruising |
| Faces | **left**, at the player | **left**, at the player |

Both are **wider than they are tall**, unlike every sprite above — Tralalero is
a long shark and Bombardiro is an aircraft. Do not draw them upright.

Tralalero's 96 px is exactly `t_player_h()`, so he stands eye-to-eye with Tung
on the same ground line. That is deliberate: he is a threat at the player's own
height, not a backdrop.

Both face left at the player and are drawn through the mirror, so the preamble's
rule still holds — **author facing right**.

**Two frames each**, and the split is the fight rather than a walk cycle:

| Frame | Phase | On screen for |
| --- | --- | --- |
| 0 | `survive` — the boss owns the pattern and cannot be hit | `t_boss_survive_time()` = 8.0 s per cycle |
| 1 | `open` — over-committed, the bat connects | `t_boss_open_time()` = 1.0 s per cycle |

Three openings kill a boss (`t_boss_bonks()`), so frame 1 is seen three times a
fight for a second each. It carries the whole read of "hit me **now**", and it
is the frame to spend the most effort on.

> Both frames are drawn: `draw_boss()` picks the column from `phase ==
> t_boss_open()`. The gold ring it used to paint around an open boss is now
> drawn only for a boss with **no** art — the open pose is the tell, and the
> ring traces the collision box, so on a wider sprite it cuts through the
> art.

### 4.1 Palette additions

From the placeholder rectangles in `src/draw.brainrot`, so replacing them does
not shift the scene's colour.

| Role | RGB |
| --- | --- |
| Tralalero body | `96,108,120` |
| Tralalero belly | `206,210,214` |
| Tralalero shoes | `70,60,54`, soles `240,240,240` |
| Bombardiro body | `84,124,78` |
| Bombardiro belly | `196,206,170` |
| Bombardiro wings / fuselage metal | `120,120,128` |
| Bombardiro bomb bay | `60,50,44` |
| Both — eye white / pupil | `250,250,250` / `20,20,20` |
| Bomb shell | `34,34,40`, fuse `190,140,60` |
| Blast | `255,148,40`, hot centre `255,226,120` |

### 4.2 Tralalero Tralala — 2 frames ✅ *done*

**Shipped**: `assets/tralalero/tralalero1.jpg` (survive) and `tralalero2.jpg`
(the opening, jaws wide). Processed to a `336 × 96` atlas of `168 × 96` frames,
anchor column 104.

Note the art frame is **168** wide against a **140 × 96** collision box — a
shark's snout and tail overhang what it collides with, the same split Tung has
(112px of art over a 48px box). That is normal and is why `t_shark_frame_w()`
and `t_shark_w()` are separate constants.

He is drawn **unmirrored**, unlike Patapim. He chases from behind, so the art's
own right-facing is toward the player; and once he has leapt past, right-facing
means his back is turned — which is exactly why he is open.

The prompt used, for reference and for regenerating:

He chases from the **left**, along the ground, and the survive phase is pure
obstacle dodging — the player is running away from him while jumping crates. So
frame 0 is seen mostly at the screen's left edge, partly off it, and needs to
read from its **right** end: the head.

```text
CANVAS OVERRIDE
Output a wide image with a 3:2 aspect ratio, not a square. The subject is
horizontal.

SUBJECT
A shark, seen in full side view, standing and running on three human legs.
The body is a long muscular shark: blue-grey above (#606C78) with a pale
off-white belly (#CED2D6), a tall dorsal fin, pectoral fins, and a heavy tail
that trails behind. The head is at the RIGHT end of the image, with a black eye
(#141414) ringed in white (#FAFAFA) and a mouth of small triangular teeth. Three
thin human legs come down from the underside of the body, each wearing a chunky
worn trainer with a pale sole (#463C36 with #F0F0F0 soles). The absurdity is the
point: it is a real shark that happens to have legs and shoes.

The silhouette is much longer than it is tall — roughly one and a half times as
wide as high — and it must read as a shark from the outline alone.

POSE
[FRAME 1 of 2: chasing. The body is low and driving forward, all three legs
mid-stride at different phases, tail streaming out behind, mouth closed or
slightly parted in a snarl, eye fixed forward. Menacing but controlled — this is
the pose he holds while he cannot be hit.]

The shark is running to the right. Do not draw water, spray, or a shadow.
```

Frame 2 — the **opening**, and the one that has to be unmistakable:

```text
POSE
[FRAME 2 of 2: over-committed. He has lunged too far forward and is off
balance — mouth thrown wide open showing the full set of teeth, head and neck
extended well ahead of the legs, front leg splayed out, tail whipped up behind
for counterbalance. He is exposed and he looks it. This is the one-second window
in which the player is supposed to swing.]

Same shark, same colours, same size as frame 1 — only the pose changes.
```

### 4.3 Bombardiro Crocodilo — 2 frames ✅ *done*

**Shipped**: `assets/bombardino/bombardino1.jpg` (level cruise) and
`bombardino2.jpg` (the opening). Processed to a `298 × 72` atlas of `149 × 72`
frames, anchor column 60. (Source folder is spelled *bombardino*; the code and
atlas use *bombardiro*, which is the character's name.)

Two things worth knowing before regenerating these:

**They are two VIEWS, not two poses.** Frame 0 is a level side elevation (4.22:1
silhouette); frame 1 is pitched up and banked (1.39:1). That is what an aircraft
pulling up actually looks like, so the shape change is the animation — but it
means no single scale factor makes them "the same size", and the tool's
equal-area correction is doing the best it can rather than something exact.
A replacement pair drawn from the *same* camera would behave more predictably.

**They are centre-aligned, not bottom-aligned.** Everything else in this game
stands on the ground and its bottom row is its contact row. A flier has none,
and bottom-aligning frame 0 (36px of content in a 72px frame) would sink it to
the floor of its own box and then jump 36px the instant the opening starts. See
`ALIGN` in `tools/process_sprites.py`.

The prompt used, for reference:

### 4.3b The original ask — `120 × 72`, 2 frames → atlas `240 × 72`

He does not chase. He flies overhead at `y = 90`, sways across the top of the
screen, and drops bombs — so frame 0 is seen small, high up, against the near-
black sky, and its **silhouette from below** is what identifies it.

```text
CANVAS OVERRIDE
Output a wide image with a 5:3 aspect ratio, not a square. The subject is
horizontal.

SUBJECT
A crocodile fused with a military bomber aircraft, seen in full side view. The
body is a crocodile: scaly olive-green back (#547C4E) with a pale ridged
underbelly (#C4CEAA), a long snout at the RIGHT end of the image with visible
teeth, one eye (#141414 in #FAFAFA), and a thick tapering tail at the left. Grey
metal aircraft parts are bolted onto it (#787880): a straight wing jutting from
the near side, a small tailplane, and a row of dark bomb-bay hatches (#3C322C)
along the belly. Bare metal, riveted, no insignia and no text.

The silhouette is much longer than it is tall — roughly one and two thirds as
wide as high — and it must read as "aircraft" from below at small size.

POSE
[FRAME 1 of 2: cruising level. The body is horizontal and stable, wing extended
straight out, tail streaming behind, snout closed, bomb-bay hatches shut. Calm
and mechanical — this is the pose he holds high up while he cannot be hit.]

The crocodile is flying to the right. Do not draw clouds, motion streaks,
propeller blur, or a shadow.
```

Frame 2 — the **opening**:

```text
POSE
[FRAME 2 of 2: descended and braking. He has dropped to head height and pulled
up hard — nose angled up, body pitched back, wing flared wide and tilted to
brake, jaws open, bomb-bay hatches hanging open and empty. He has stalled out of
his own attack run and is hanging there. This is the one-second window in which
the player is supposed to swing.]

Same crocodile, same colours, same size as frame 1 — only the pose changes.
```

### 4.4 Bomb — single frame ✅ *done*

**Shipped**: `assets/bombardino/bomb.jpg` → an `11 × 26` sprite.

Note what moved: the **hitbox followed the art**, not the other way round.
`t_bomb_w()` was 26 and is now 12. The shell plus its lit fuse keys out to 11px
wide at 26px tall, and a 26×26 box around an 11px sprite is fifteen pixels of
empty air that still takes a heart. A hitbox wider than what the player can see
is not difficulty.

The blast is deliberately the opposite: 77px of art over a 64px box, so the
outer flames are decoration you can stand in. Wide sprite, narrow box, is the
forgiving direction.

The prompt used, for reference:

### 4.4b The original ask — `26 × 26`, single frame

Dropped from Bombardiro's belly and falls under the player's own gravity.

```text
CANVAS OVERRIDE
Output a square image. The subject is small and compact.

SUBJECT
A small cartoon aerial bomb seen from the side: a stubby dark iron shell
(#222228) with a rounded nose pointing DOWN, three small fins at the top, and a
short length of fuse cord (#BE8C3C) sticking up from the tail with a bright warm
spark at its tip (#F09628). A single pale highlight along the upper-left of the
shell so it reads as metal.

The bomb is as wide as it is tall and fills the subject area. It must be legible
at 26 pixels: shape and one bright spark, nothing finer.

POSE
Falling, nose down, upright.
```

The bomb is the one asset where **facing does not matter** — it is drawn
unmirrored and symmetric about its vertical axis. Keep it symmetric.

### 4.5 Blast — single frame ✅ *done*

**Shipped**: `assets/bombardino/blast.jpg` → a `77 × 34` sprite, centred on its
64 × 34 box. The prompt used, for reference:

### 4.5b The original ask — `64 × 34`, single frame

What the bomb becomes on impact: a ground hazard that hurts for
`t_bomb_fuse()` = 0.55 s. Wide and low, sitting **on** the ground line.

```text
CANVAS OVERRIDE
Output a wide image with a 2:1 aspect ratio. The subject is a low horizontal
band, not a ball.

SUBJECT
A burst of fire spreading sideways along the ground: a wide, low fan of flame,
brightest and palest at its centre (#FFE278) grading out to strong orange at the
edges (#FF9428), with a few detached sparks above it. Flat hard-edged shapes, no
smoke, no soft glow, no radial gradient.

The blast is twice as wide as it is tall and spreads HORIZONTALLY. Its bottom
edge is flat and fully opaque — it sits on the ground, and the game places that
bottom row exactly on the ground line. Nothing may be drawn below it.

POSE
A single frozen moment near the peak of the burst, seen from the side.
```

---

## 5. Background — parallax layers

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

## 6. Acceptance checklist

Check each processed asset before it goes in the repo. Most of these are
scriptable, and should be scripted.

**Every sprite**

- [ ] Exact pixel dimensions (`48×96`, `64×64`, `48×48`, `40×96`, `140×96`,
      `120×72`, `26×26`, `64×34`, atlas widths as listed)
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

**Every boss**

- [ ] Wider than tall — both are, and drawing them upright breaks the box
- [ ] Frame 1 (the opening) is unmistakably different from frame 0 at a glance,
      not a small pose tweak. It is on screen for one second, three times a
      fight, and it is the entire signal to swing
- [ ] Tralalero's head is at the RIGHT end of the frame: he is seen entering
      from the screen's left edge, partly off it, so the head is what arrives
- [ ] Bombardiro reads as an aircraft in silhouette from below, small and high
      against a near-black sky
- [ ] `tools/check_atlases.py` passes — and if the atlas size changes, the
      constants it checks live in `src/tune.brainrot`, not in `draw.brainrot`

**In-game**

- [ ] Readable against the LVL 1 sky (`12,14,34`) — the hardest case, and the
      first thing a player sees
- [ ] Still readable against the LVL 8 dawn sky (`140,74,60`)
- [ ] Tung and Patapim are distinguishable by silhouette alone at 900 px/s
- [ ] Tralalero is distinguishable from Patapim at a glance — both are wide,
      ground-level and coming at you, and confusing "bonk the boss when it
      opens" with "bonk this enemy now" costs a heart

---

## 7. What this does not cover

Sprites for the M1 Patapim variants (small, big, jumping, armored) are still out
of scope. Armored Patapim in particular needs a silhouette that reads as
*unbonkable* before it is worth drawing, and that is a design question rather
than a prompting one.

The M2 bosses moved into scope (§4) once both fights were implemented and
playable — the sizes, frame split and placeholder palette in that section are
read from the shipped code, so the prompts describe art the game can already
load rather than art a future version might want.
