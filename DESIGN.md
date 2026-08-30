# TUNG TUNG TUNG SAHUR: RUN — Design Document

> An endless runner written in [Brainrot](https://github.com/Brainrotlang/brainrot),
> rendered through [`rayrot`](https://github.com/Brainrotlang/brainrot/blob/main/docs/rayrot.md).
>
> **The game repository contains zero C.** Anything the game needs that raylib
> can't reach from Brainrot today gets implemented *upstream*, in `brainrot` or
> `rayrot`. This repo is `.brainrot` files and assets, nothing else.

---

## 1. Pitch

Canabalt + Chrome Dino + a baseball bat, at 03:30 AM in an Indonesian
neighbourhood. Tung Tung Tung Sahur runs east to wake the village for the
pre-dawn meal. Brr Brr Patapim keeps getting in the way.

One rule, learned in ten seconds:

> **Jump to survive. Bonk to score.**

A crate has to be jumped. Brr Brr Patapim *can* be jumped — the arc clears him
comfortably — but jumping him pays nothing, and the bat pays up to ×8. So the
safe line through the level is always available and always worth less than the
greedy one, which is the whole tension: every Patapim is a small bet on your own
timing.

Then, from LVL 4 onward, armored Patapim arrives and takes the bat away, so the
one answer you'd been rewarded for stops working.

The goal is not "an infinite score counter". The goal is **SURVIVE UNTIL SAHUR** —
a fixed distance, roughly five minutes, after which the sky turns orange and you
unlock **ENDLESS SCHIZO MODE**, where the acceleration never stops.

## 2. Design pillars

1. **One number drives everything.** `speed` scrolls the world, spawns entities,
   picks the sky colour, and sets the LVL. There are no difficulty *levels*, only
   a difficulty *curve* that the HUD quantises for readability.
2. **Small mechanical core, deep tail.** Jump, bonk, and a rising number. Every
   later mechanic is a variation on those three. Jumping always survives;
   bonking is what scores. The safe line is never removed, only made poorer.
3. **Hard, never unfair.** Spacing is measured in *seconds of reaction time*, not
   pixels, so the game stays reactable as it accelerates. Unavoidable spawns are
   a bug, not a difficulty setting.
4. **Deterministic.** A seeded PRNG means a run is reproducible, a bug report is
   a seed, and the simulation is testable in CI without a window.
5. **The game proves the language.** Real-time state, entity pools, collision,
   input, and tens of thousands of consecutive frames without exploding. If
   Brainrot can't do something, that's an upstream issue, not a workaround.

---

## 3. Platform constraints

This section is not background reading. Brainrot has sharp edges that shape the
architecture, and every claim below was verified by running the interpreter on
`main` @ `3ce8a3a` with raylib 6.0.0 and the raylib binding built. (That
binding lived in `brainray/` until
[brainrot#318](https://github.com/Brainrotlang/brainrot/pull/318) renamed the
directory to `rayrot/`; the cooked module is `<raylib>` either way.)

### 3.1 What works, and is load-bearing

| Feature | Status | Used for |
| --- | --- | --- |
| `gang Ent pool[16];` — **arrays of structs** | ✅ ([#287](https://github.com/Brainrotlang/brainrot/pull/287)) | Entity pools |
| `pool[i].field = v;` read and write by index | ✅ | Entity update loops |
| `cap` struct fields in conditions (`edgy (pool[i].alive)`) | ✅ | Liveness checks |
| Scalar-only functions with many params, returning `cap` / `chad` / `rizz` | ✅ | `aabb`, `clampf`, `rng_next` |
| `gang X *` parameters, several of **different** types, called as `helper(&pool[i], &world)` | ✅ ([#294](https://github.com/Brainrotlang/brainrot/pull/294)) | Every step function in `src/sim.brainrot` |
| `!` on a `cap`, and float→integer assignment | ✅ ([#296](https://github.com/Brainrotlang/brainrot/pull/296), [#299](https://github.com/Brainrotlang/brainrot/pull/299)) | Guards read forwards; no `truncf()` |
| `chad` → `int` coercion at the **native call boundary** | ✅ | `rl_draw_rectangle(px, py, ...)` with `chad` args |
| `#cooked "file.brainrot"` splicing | ✅ | Splitting the source |
| Seeded PRNG (Park–Miller / Schrage) | ✅ | Spawn tables |

### 3.2 What does not work

Each of these is an upstream issue (§15.2), and each has a workaround the game
uses until it lands.

Three that used to be here have since been fixed upstream, all of them found by
writing this game: the struct-pointer parameter reversal
([#294](https://github.com/Brainrotlang/brainrot/pull/294)), `!` being discarded
by the lexer ([#296](https://github.com/Brainrotlang/brainrot/pull/296)), and
float-to-integer assignment reinterpreting bits
([#299](https://github.com/Brainrotlang/brainrot/pull/299)). The workarounds
they forced — `== L` everywhere, a `truncf()` helper, and the whole frame loop
in one function — are gone with them.

| Limitation | Verified behaviour | Workaround in this design |
| --- | --- | --- |
| **A struct field cannot be an array of structs** | `gang Game { gang Enemy es[4]; };` → parse error | No "God struct". Pools are `skibidi main` locals |
| **No pointer arithmetic on struct pointers** | `gang E *p = &es[0]; p = p + 1;` → *"type-erased pointer — pointee size is unknown"* | Iterate with an index in `main`; helpers take one already-resolved `&pool[i]` |
| **No top-level globals** | `rizz g_score = 0;` at file scope → parse error | All state is local to `skibidi main` |
| **No `*(p + i) = v` or `p[i] = v` through a pointer param** | Both rejected | `rizz *q = p + i; *q = v;` |
| **No math library** | `stdrot/` is `yapping`, `yappin`, `baka`, `ragequit`, `chill`, `slorp`, `bet` | Hand-rolled `rng_next`, `clampf`, `absf` in `src/math.brainrot` |
| **Signed overflow aborts** | The interpreter is built `-fsanitize=address,undefined`; `42 * 1103515245` kills the run | PRNG uses Schrage's method, which provably never leaves int32 |
| **`W` and `L` are keywords** | `gang W { ... }` → parse error | Never name anything `W` or `L` |

### 3.3 The `rayrot` surface

Twenty-five functions total:

```
rl_init_window          rl_window_should_close  rl_close_window
rl_set_target_fps       rl_get_screen_width     rl_get_screen_height
rl_begin_drawing        rl_end_drawing          rl_clear_background
rl_get_frame_time       rl_draw_fps             rl_measure_text
rl_draw_circle          rl_draw_rectangle       rl_draw_line
rl_draw_text            rl_is_key_down          rl_is_key_pressed
rl_load_texture         rl_draw_texture         rl_unload_texture
rl_draw_text_int        rl_measure_text_int     rl_draw_texture_rec
```

**B1** ([#292](https://github.com/Brainrotlang/brainrot/pull/292)) added the two
text-with-a-number wrappers; **B2**
([#293](https://github.com/Brainrotlang/brainrot/pull/293)) added
`rl_draw_texture_rec`, so sprite atlases, animation strips and tiled parallax
are all reachable — and a negative source width mirrors a sprite, which is the
only way to face Tung the other direction until `DrawTexturePro`'s rotation is
exposed.

One gap remains:

- **No audio at all.** → **B3**.

M0 was designed to need none of them.

---

## 4. Screen and coordinates

1280×720, fixed, non-resizable, `rl_set_target_fps(60)`. There is no
`DrawTexturePro`, so there is no clean way to upscale a smaller internal
resolution; native it is.

```
 (0,0)
   ┌────────────────────────────────────────────────────────────────┐
   │ ♥♥♥                                        SPEED ▓▓▓▓▓░░░       │  HUD band, y 0..80
   │ SCORE ──────                                     LVL ─          │
   │                                                                 │
   │        sky (colour is a function of LVL)                        │
   │                                                                 │
   │          ▓▓                                                     │
   │          ▓▓ ← Tung, x fixed at 200                              │
   │          ▓▓            ██          ▓▓▓                          │
   ├──────────▓▓────────────██──────────▓▓▓──────────────────────────┤  GROUND_Y = 560
   │                     ground                                      │
   └────────────────────────────────────────────────────────────────┘
                                                            (1280,720)
```

The camera does not exist. Tung's `x` never changes; the world moves toward him.
Every entity is `x = x - speed * dt`, and the difficulty curve is one variable.

---

## 5. Tuning constants

Declared as `deadass` locals at the top of `skibidi main`. Every number here is
a starting point to be felt out in playtesting, not a law.

```c
🚽 --- screen ---
SCREEN_W          1280
SCREEN_H          720
GROUND_Y          560.0

🚽 --- player ---
PLAYER_X          200.0
PLAYER_W          48.0
PLAYER_H          96.0
GRAVITY           2600.0     🚽 px/s^2
JUMP_V           -1000.0     🚽 px/s  -> apex 192px, air time 0.77s
HEARTS_MAX        3
IFRAME_TIME       1.2        🚽 s

🚽 --- bat ---
ATTACK_TOTAL      0.45       🚽 s; timer counts down
ATTACK_ACTIVE     0.30       🚽 hitbox live while atk_t > this, i.e. first 0.15s
HITBOX_DX         40.0       🚽 relative to player x
HITBOX_DY         16.0
HITBOX_W          56.0
HITBOX_H          56.0

🚽 --- world ---
SPEED_START       260.0      🚽 px/s
SPEED_ACCEL       3.0        🚽 px/s^2
SPEED_MAX_STORY   900.0      🚽 uncapped in endless mode
SAHUR_DISTANCE    200000.0   🚽 px  (~5 min)

🚽 --- spawning ---
SPAWN_X           1340.0     🚽 just off the right edge
GAP_BASE          1.55       🚽 s
GAP_SLOPE         0.0011     🚽 gap = GAP_BASE - speed * GAP_SLOPE
GAP_MIN           0.55       🚽 s
GAP_JITTER        0.20       🚽 s, +/-
FAIR_JUMP_JUMP    0.95       🚽 s, minimum between two jump-required spawns
FAIR_ANY          0.60       🚽 s, absolute minimum between any two spawns

🚽 --- pools ---
MAX_OBSTACLES     16
MAX_ENEMIES       16
MAX_PROJECTILES   32         🚽 reserved for M2 (Bombardiro's bombs)
```

**Jump geometry.** With `GRAVITY = 2600` and `JUMP_V = -1000`, apex is
`1000² / (2·2600) ≈ 192 px` and total air time is `2·1000 / 2600 ≈ 0.77 s`. A
64 px crate clears comfortably; a 96 px tall obstacle needs a timely jump. Those
two numbers set `FAIR_JUMP_JUMP` (§8.2) and must be changed together.

---

## 6. The player

### 6.1 State

```c
gang Player {
    chad y;          🚽 top edge; x is fixed at PLAYER_X
    chad vy;
    cap  grounded;
    chad atk_t;      🚽 attack timer, counts down; 0 = idle
    chad iframe_t;   🚽 invulnerability timer
    rizz hearts;
};
```

### 6.2 Jump

Fixed arc, M0. No variable height, no double jump.

- `SPACE` or `UP`, edge-triggered *and* gated on `grounded`, so holding the key
  does not autohop.
- `vy = vy + GRAVITY * dt; y = y + vy * dt;`
- Landing clamps: `edgy (y > GROUND_Y - PLAYER_H) { y = GROUND_Y - PLAYER_H; vy = 0.0; grounded = W; }`

**Duck** (`DOWN`) is deferred to M1. It only becomes meaningful once flying
Patapim variants exist to duck under.

### 6.3 Bat

`X` or `Z`, edge-triggered via `rl_is_key_pressed`, refused while `atk_t > 0.0`.

```
atk_t = ATTACK_TOTAL (0.45s)
├── 0.45 → 0.30 : ACTIVE   — hitbox live, 0.15s
└── 0.30 → 0.00 : COOLDOWN — no hitbox, no re-swing, 0.30s
```

The hitbox is a rectangle in front of Tung, not an arc:
`(x + 40, y + 16, 56 × 56)`. Because it is relative to `y`, it rises with him —
**you can swing mid-air, and it hits exactly the same.** That is deliberate: it
keeps the airborne bonk available without a separate air-attack to balance.

### 6.4 Damage

Colliding with a live entity while `iframe_t <= 0.0`:

1. `hearts = hearts - 1`
2. `iframe_t = IFRAME_TIME` (1.2 s; player flashes, drawn on alternate 0.1 s ticks)
3. combo resets to zero
4. the entity that hit you is despawned, so one obstacle cannot drain three hearts

**Damage does not touch `speed`.**

An earlier version knocked the world speed back by a quarter on every hit,
described as a mercy and a punishment at once. It was neither, and it is worth
recording why it went.

At 900 px/s it handed back 225 px/s, which takes **75 seconds** to climb again
— a quarter of a whole run spent easier, bought for one of three hearts. That
makes deliberately eating a hit the *correct* play at the top of the curve,
which is not a strategy this game should reward.

The mercy was redundant as well. 1.2 s of invulnerability is 1080 px of
clearance at that speed, most of a screen width, and that is what actually
saves you from a second hit — not the speed change.

Mostly, though, it fought §2's first pillar. The whole game is one number
rising; a hit that pushes it back down makes the curve non-monotonic and turns
failure into relief. Losing a third of your health and up to an ×8 combo is
punishment enough.

Three hearts total; at zero, game over.

---

## 7. The speed curve

One variable, integrated every frame:

```c
speed = speed + SPEED_ACCEL * dt;
edgy (speed > SPEED_MAX_STORY) { speed = SPEED_MAX_STORY; }   🚽 story mode only
dist  = dist + speed * dt;
```

`SPEED_ACCEL = 3.0` takes `speed` from 260 to the 900 cap in about 213 seconds,
which is *after* both bosses. Endless mode simply removes the clamp.

### 7.1 LVL is a display, not a state

The HUD in the mockup shows `LVL 1` and a segmented SPEED bar, which implies
discrete tiers. It does not. **The underlying value is continuous; the HUD
quantises it:**

```c
rizz lvl = 1 + (speed - SPEED_START) / 90.0;
edgy (lvl > 8) { lvl = 8; }
```

Eight segments, eight levels, matching the eight-segment bar. Nothing in the
simulation ever branches on `lvl` except the sky palette (§10.2) and the
enemy-variant gate (§9.3) — and both of those are cosmetic-tier decisions that
*want* to be steppy.

### 7.2 The feel target

Measured, not estimated — `test/unit_curve.brainrot` integrates the curve at
60 Hz and prints this table, so it cannot drift away from the code:

| Elapsed | speed | LVL | gap | Intent |
| --- | --- | --- | --- | --- |
| 0:00 | 260 | 1 | 1.26 s | tung.... tung.... tung.... |
| 1:00 | 440 | 2 | 1.07 s | okay |
| 2:00 | 620 | 4 | 0.87 s | concentration required |
| 3:00 | 800 | 6 | 0.67 s | TUNGTUNGTUNGTUNGTUNG |
| 3:30 | 890 | 8 | 0.56 s | last tier |
| 3:33 | 900 | 8 | 0.56 s | story cap |
| 4:58 | 900 | 8 | 0.56 s | **SAHUR** — 200,000 px |
| endless | ∞ | 8 | 0.55 s | humanly questionable |

A clean run reaches Sahur at 4:58. Note that the LVL boundaries land a hair
*after* the round speed numbers — at 1:00 the integrated speed is 439.96, just
under the 440 needed for tier 3 — which is why the column reads 2 rather than 3.
That is the code being precise, not the table being wrong.

---

## 8. Entities and spawning

### 8.1 Pools

No allocator, no globals, no struct-typed array fields (§3.2). Pools are
fixed-size arrays of structs, declared in `skibidi main`:

```c
gang Ent {
    chad x; chad y; chad w; chad h;
    rizz kind;
    cap  alive;
};

skibidi main {
    gang Ent obstacles[16];
    gang Ent enemies[16];
    ...
}
```

Spawning is a linear scan for the first `alive == L` slot. Sixteen is generous:
at `SPEED_MAX_STORY` with `GAP_MIN`, at most ~4 obstacles are on screen at once.
A full pool silently skips the spawn — which is correct behaviour, not an error.

**Kinds, M0:**

| kind | Entity | Size | Answer |
| --- | --- | --- | --- |
| 0 | Crate | 48 × 48, grounded | jump |
| 1 | Post | 40 × 96, grounded | jump |
| 2 | Brr Brr Patapim | 64 × 64, grounded | bonk |

### 8.2 Spacing is measured in time

This is the difference between "hard" and "unfair", and it is the single most
important rule in the document. Spacing is **never** a pixel constant, because a
pixel gap that is generous at 260 px/s is lethal at 900 px/s.

```c
chad gap = GAP_BASE - speed * GAP_SLOPE;      🚽 1.26s at LVL1 -> 0.56s at LVL8
edgy (gap < GAP_MIN) { gap = GAP_MIN; }
gap = gap + jitter;                            🚽 +/- GAP_JITTER, from the PRNG
```

Then the fairness clamp, applied *after* jitter:

- Two consecutive **jump-required** spawns: `gap >= FAIR_JUMP_JUMP` (0.95 s).
  Derived directly from air time (0.77 s) plus a reaction buffer (0.18 s) — you
  must be able to land before the next thing arrives.
- Any two spawns: `gap >= FAIR_ANY` (0.60 s).

Because both are in seconds and the clamp runs every spawn, the curve tightens
until it hits the floor and then *stops getting harder in spacing* — the
remaining difficulty comes from raw scroll speed shrinking the reaction window
inside a fixed gap. That is the correct place for the difficulty to live.

**Any spawn the player cannot avoid is a bug.** File it as such.

### 8.3 Determinism

`stdrot` has no `rand()`, and the naive LCG overflows int32 and aborts under
UBSan. Park–Miller with Schrage's method stays in range by construction —
`16807 * lo` where `lo < 127773` is at most 2,147,469,111, just under 2³¹:

```c
rizz rng_next(rizz s) {
    rizz hi = s / 127773;
    rizz lo = s % 127773;
    rizz v = 16807 * lo - 2836 * hi;
    edgy (v < 0) { v = v + 2147483647; }
    bussin v;
}
```

The seed is fixed per run and **printed on the game-over screen**, so a bug
report is a seed and a frame number. It is also what makes §12 possible.

---

## 9. Combat and scoring

### 9.1 Collision

Axis-aligned bounding boxes, scalars only — no struct params, so this sidesteps
the reversal bug entirely:

```c
cap aabb(chad ax, chad ay, chad aw, chad ah,
         chad bx, chad by, chad bw, chad bh) {
    edgy (ax + aw < bx) { bussin L; }
    edgy (bx + bw < ax) { bussin L; }
    edgy (ay + ah < by) { bussin L; }
    edgy (by + bh < ay) { bussin L; }
    bussin W;
}
```

Resolution order per entity, per frame — **bat before body**, so a frame-perfect
swing always beats the collision:

1. If the entity is bonkable and the bat is active → test bat hitbox. On hit:
   despawn, award, bump combo. **Stop.**
2. Otherwise test the player body. On hit and `iframe_t <= 0.0` → damage (§6.4).

### 9.2 Score

```
score = dist / 10  +  sum of bonk awards
bonk award = 100 * combo_multiplier
```

`combo_multiplier` is the count of consecutive bonks without taking damage,
clamped to 8: ×1, ×2, ×3 … ×8. It resets to zero on any heart lost. Missing a
bonk does not reset it — only getting hit does, which keeps the incentive
aggressive rather than cautious.

### 9.3 Jumping an enemy is allowed, and that's the point

The jump apex is 192 px and Patapim is 64 px tall, so hopping an enemy clears
him cleanly. This is deliberate, not an oversight — `unit_collide.brainrot`
asserts the geometry both ways, that a grounded swing connects over 121 px of
approach and that an apex swing misses.

The alternative — a hidden damage box taller than the sprite, or a 192 px enemy
— would make the safe line unavailable and turn every Patapim into a pure
execution check. Instead the safe line stays open and costs you the combo. A
player who only jumps finishes a run; a player who bonks finishes it with four
times the score. That is a better arcade shape than "do the one correct thing",
and it means the difficulty curve, not the enemy design, is what eventually
kills you.

### 9.4 Breaking the rule

The bargain above is taught for three levels, then withdrawn. Variants unlock at
`lvl >= 4` (M1):

| Variant | Twist |
| --- | --- |
| Small Patapim | Faster closing speed; the bonk window is genuinely tight |
| Big Patapim | Two bonks; the first staggers, the second kills |
| Jumping Patapim | Leaps on approach — bonk on the ground or duck the leap |
| Armored Patapim | **Cannot be bonked.** Jumping is the only answer, so the greedy line is the one that kills you |

Armored Patapim is deliberately introduced *alone*, on a wide gap, the first
time it appears. The lesson has to be survivable.

### 9.5 Enemy motion

Enemies scroll with the world *plus* a small closing speed, so they arrive
sooner than the geometry suggests and can't be pattern-memorised purely by
spacing:

```c
enemies[i].x = enemies[i].x - (speed + ENEMY_CLOSE) * dt;   🚽 ENEMY_CLOSE = 40.0
```

---

## 10. Presentation

### 10.1 M0 renders in primitives

Per §3.3, sprite atlases need upstream **B2**, and one-PNG-per-animation-frame
would mean six `rl_load_texture` handles for a run cycle alone. M0 therefore
ships in `rl_draw_rectangle`:

| Thing | Primitive |
| --- | --- |
| Sky | `rl_clear_background` in the LVL palette |
| Ground | one rectangle, `0, 560, 1280, 160` |
| Tung | 48 × 96 wood-brown rectangle |
| Bat swing | 56 × 56 pale-yellow rectangle, drawn only while active |
| Patapim | 64 × 64 rectangle |
| Crate / post | grey rectangles |
| Hearts | 20 × 20 red rectangles |
| Speed bar | 8 segment rectangles |

This is not a placeholder to be ashamed of — it is a playable game that proves
the loop before a single asset exists, and it keeps M0 free of upstream blockers.

Parallax (mountains / palms / houses / foreground foliage, per the concept art)
is **M1**, and needs **B2** to tile without a texture per screen-width.

### 10.2 Sky palette

Discrete per LVL tier — the 03:30 → 05:00 progression. A smooth lerp needs no
new API and can replace this later; steps are chosen because they make the
player *notice* they survived another tier.

| LVL | Time | RGB |
| --- | --- | --- |
| 1–2 | 03:30 | `12, 14, 34` deep night |
| 3–4 | 04:00 | `18, 20, 48` |
| 5–6 | 04:30 | `38, 30, 64` pre-dawn purple |
| 7 | 04:50 | `78, 44, 66` |
| 8 | 05:00 | `140, 74, 60` dawn |

### 10.3 HUD

Numbers arrived with **B1**, so the HUD is complete:

```
♥♥♥                                    SPEED ▓▓▓▓▓░░░
SCORE 000450                           LVL 3
```

Score is zero-padded to six columns via `rl_draw_text_int`'s `pad` argument,
which is a *field width* rather than a digit count — the point being that the
HUD does not reflow every time the score crosses a power of ten. `LVL` is
unpadded because it is a single digit by construction (§7.1).

The game-over card centres the final score and the run's seed with
`rl_measure_text_int`. The seed is on screen rather than in the terminal
because a run is reproducible from it (§8.3): a bug report is a seed and a
frame number, and nobody ever went to read their console for it.

- Hearts: `hearts` red rectangles at `(20 + i*28, 20)`.
- Speed bar: 8 segments at `(1130 + i*14, 30)`; filled while `i < lvl`.
- `rl_draw_fps` bottom-right, debug builds only.

---

## 11. Input

| Action | Keys | Codes | Trigger |
| --- | --- | --- | --- |
| Jump | `SPACE`, `UP` | 32, 265 | `is_key_down`, gated on `grounded` |
| Bat | `X`, `Z` | 88, 90 | `is_key_pressed`, gated on `atk_t <= 0` |
| Duck (M1) | `DOWN` | 264 | `is_key_down` |
| Restart | `R`, `SPACE` | 82, 32 | `is_key_pressed`, game-over screen only |
| Quit | `ESC` | 256 | raylib default + `rl_window_should_close` |

No pause. It's an arcade runner.

---

## 12. Bosses (M2)

Tralalero and Bombardiro are too good to spend as generic enemies. They are set
pieces. When a boss is active **the normal spawner pauses** — the boss owns the
pattern — and **you can still die**, hearts and all.

Both use the same three-cycle shape: *survive a phase → an opening appears →
one bonk → repeat ×3*.

**They trigger on LEVEL, not score**, and that is a correctness fix rather than
a preference. Level is `speed_to_lvl()`, and speed is a pure function of elapsed
run time — so a level threshold means the same moment for every player. Score is
`dist × 0.1` *plus bonus*, and `award_bonk()` pays up to 800 a bonk at an ×8
combo, so score measures how well you are playing rather than how far you have
got. Tralalero was set at score 5,000: LVL 5 for a player who never bonks, LVL 2
for one who does. The better you played, the sooner the boss arrived and the
slower the world was when it did.

Tralalero at **LVL 3** (1:00) and Bombardiro at **LVL 6** (2:30).
`unit_curve.brainrot` prints the level timeline with both marked, so the pacing
is a table rather than a claim.

### 12.1 TRALALERO TRALALA — LVL 3

The three-legged shark, characterised by speed, chases from the left. The game
becomes pure obstacle survival: an unbroken sequence of jump obstacles with no
bonkable enemies, the shark closing a little with each mistake.

**"Unbroken", not "denser".** The boss's gaps go through the same
`fair_clamp()` every other spawn does, because §7.3's rule — *any spawn the
player cannot avoid is a bug, not a difficulty setting* — is not suspended for
a boss. What makes the phase hard is that **every** obstacle needs a jump, with
no Patapim to break the rhythm and a shark closing behind on each mistake.

It shipped the other way and the fight was unclearable. `t_boss_gap()` was a
flat 0.72s that `main` set directly, never calling `fair_clamp()` — against a
jump airtime of `2 × |t_jump_v()| / t_gravity()` = **0.769s**. The next obstacle
arrived 49ms *before* the player landed from the last one, and since the boss
spawns only crates and posts, every single gap was jump-to-jump. There was no
frame on which the jump could be made.

`boss_spawn_gap()` exists as a function for one reason: a unit test can call it
and a line inside `main`'s frame loop cannot. `unit_boss.brainrot` now sweeps
every kind pair and asserts each jump-to-jump gap exceeds the airtime, and
`unit_curve.brainrot` asserts the same of every gap the world spawner can
produce.

```
                         🦈👟  ← closes on every obstacle you clip
 🪵    █       █
 /|\  █ █     █ █
_/ \____________________________
```

After each survival phase he over-commits and drifts into bat range for a
1.0 s window. Three of those and he's out. Then the run resumes, faster.

### 12.2 BOMBARDIRO CROCODILO — LVL 6

He does not chase. He flies overhead and bombs, so the whole vertical axis
becomes hostile while you're still running:

```
                🐊✈️
            💣       💣
                💣
 🪵
 /|\       💥
_/ \____________________
```

Bombs are the `bombs[32]` pool: spawned at his `x`, exploding into a ground
hazard on impact. Between volleys he descends to bat height for the opening.
Three bonks.

**They do not fall under the player's gravity, and he does not fly at a fixed
column.** Both were wrong, and together they made the fight an instant kill:

- At `t_gravity()` the drop took **0.535 s**. A jump lasts **0.769 s**, so a
  jump started the instant the bomb appeared finished *after* it had already
  detonated. The player could not react, only pre-empt — and there was nothing
  to pre-empt from, because an 11px shell of `rgb(34,34,40)` against a
  `rgb(12,14,34)` sky is invisible.
- So **`t_bomb_fall_time()` is the tuned number** (1.0 s) and the gravity that
  produces it is derived. A player needs ~0.25 s to react plus ~0.385 s to reach
  jump apex; 0.635 s is the floor and `unit_boss.brainrot` asserts it.
- **A falling bomb does not scroll.** Tung is fixed at `t_player_x()` and the
  croc is drawn at a screen `x`, so both are stationary in the camera's frame
  and the croc is flying at exactly Tung's speed. A bomb released from him keeps
  that speed and falls *straight down*, landing where it was dropped. It only
  becomes part of the world, and starts scrolling, once it lands.

  `bomb_tick()` scrolled it the whole way down, which was wrong twice: the
  impact point drifted by `speed × fall_time`, and a longer fall needed the croc
  further and further ahead to compensate — past the right edge of the screen at
  anything over about 1.0 s. That coupling is why the first attempt at a fix
  could only afford 1.0 s. Falling straight removes it, so the fall time is free,
  and the croc **hovers over** Tung rather than leading him — which is also what
  *"I can't see where the bombs are coming from"* wanted.
- Every falling bomb draws a **guide line straight down to a ground marker**,
  from the moment it is dropped. The marker sits *on* the ground band, fully
  opaque, and its bright core widens as impact nears so "how soon" reads without
  a number. The first version straddled the ground line at 35% alpha — half over
  the foliage layer, half over the ground — which is a washed-out colour across
  a boundary between two backgrounds, and could not be read.

### 12.3 Neither boss deals contact damage

The player is pinned at `t_player_x()` and can only jump. A boss that
*positions itself* is therefore not dodgeable, and contact damage from one is
damage nobody can avoid — which is not difficulty, it is a coin the game takes.

Both fights shipped with exactly that bug and it made them unwinnable. The
openings have to be in **front** of the player, because the bat only reaches
forward (`t_hitbox_dx()` onward). They were placed to overlap the bat and
nothing else was checked — and a 140px shark at `x = 150` spans 150–290, which
covers the bat box *and* Tung's own 200–248. So every opening cost a heart,
three openings win a fight, and the player has three hearts.

What each boss damages the player *with* is the thing it produces and the player
can read coming: Tralalero's obstacle barrage, Bombardiro's bombs. Those are
dodgeable, so those are the fight. `boss_hits_body()` survives as an
**invariant** — `test/unit_boss.brainrot` replays both fights and asserts it is
false on every frame.

That invariant is what forces the movement rule in §12.4.

### 12.4 How it is built

`gang Boss` is a single value in `skibidi main`, not a slot in `enemies[]`. It
has phases, a bonk count and scripted movement that no generic `Ent` wants, and
putting it in the pool would drag all of that through the shared collision
passes. `gang Bomb` is its own pool for the same reason — it needs `vy` and a
fuse, and a landed bomb is the same slot with a wider box rather than a second
pool.

Movement is a pure function of `(kind, phase, hits, dist)` fed through
`approach()`, not a lerp. Lerp's step depends on the distance left, so a boss
would ease in and never quite arrive, and the opening would land at a different
`x` every cycle — which matters because the bat ranges in `tune.brainrot`
(`t_shark_open_x`, `t_croc_open_y`) are chosen to overlap the hitbox exactly.
`unit_boss.brainrot` asserts the boss actually *reaches* bat range inside the
window, since the fight is unwinnable if it does not.

**The leap leads the crossing.** Tralalero chases from behind and his opening is
in front, so he has to cross Tung — and per §12.3 he must never occupy Tung's
space while doing it. Two rules get that:

1. `boss_move()` moves **vertically first**.
2. `boss_may_advance()` gates every horizontal move on either being clear above
   Tung's head, or already being on the side it is heading for.

So he rises in place, crosses overhead, and comes down on the far side — and
the same rule carries the return trip and the launched exit of a beaten boss,
both of which slid straight back through the player before it existed.

Moving both axes together cannot work: at `t_boss_move_speed()` a boss climbs
exactly as fast as it advances, so it is only half-way up when it arrives. Nor
can the airborne test be "while `boss_may_advance()` is false" — that is
circular. Rising makes it true, which returns the target to the ground, which
drops him, which makes it false. He hovers and never crosses.

Tralalero's closing is clamped by `boss_lurk_x()` to stop `t_shark_close_min()`
short of Tung's back, so it stays dread rather than becoming damage however many
mistakes are made or however many hearts a future `t_hearts_max()` hands out.

A missed opening costs time, not health: the phase returns to `survive` and the
cycle repeats. The fight is long rather than unfair.

**The opening's clock starts on arrival, not on the phase.** Tralalero spends
0.78s of his lunge rising, crossing over Tung and coming down. When the timer
ran from the start of the phase, he was inside bat reach for the *last 14
frames of 61* — so a player reacting to "he's open!" swung immediately, hit
nothing, and spent the only part that counted inside `t_attack_total()`'s 0.45s
cooldown. `boss_in_position()` gates the tick, which buys the whole
`t_boss_open_time()` with him actually there: 1.17s of real reach for
Tralalero, 1.10s for Bombardiro.

`unit_boss.brainrot` measures that reach directly. The old test only asked
whether the bat *could* reach the boss at all, which is why it passed on a
fight nobody could win.

**And the game says so.** `draw_boss_bar()` puts `TUNG HIM — X` on screen while
the boss is open *and has arrived*. Those two conditions differ by exactly the
leap, and prompting during it would teach the same too-early swing.

**Both bosses are drawn from art**, as are the bomb and its blast. They go
through the same `tex >= 0` fallback every other draw uses, so a missing file
degrades one asset at a time and the simulation does not know either way.

Tralalero's atlas is two frames — survive and opening — and `draw_boss()` picks
the column from the phase. His art frame is 168px wide against a 140×96
collision box, because a shark's snout and tail overhang what it collides with;
that is the same split Tung has (112px of art over a 48px box), which is why
`t_shark_frame_w()` and `t_shark_w()` are separate constants that
`tools/check_atlases.py` checks independently.

He is drawn **unmirrored**, unlike Patapim, and that is not an oversight: he
chases from behind, so the art's own right-facing is toward the player — and
once he has leapt past, right-facing means his back is turned, which is exactly
why he is open.

Bombardiro's two frames are two *views* rather than two poses — a level side
elevation and a pitched, banked three-quarter — which is what an aircraft
pulling up looks like. He is also **centre-aligned** in his frame rather than
bottom-aligned: he flies, so he has no contact row, and bottom-aligning a 36px
frame inside a 72px box would sink him to its floor and then jump him 36px when
the opening starts.

The **bomb's hitbox follows its art**: `t_bomb_w()` went 26 → 12 because the
shell keys out 11px wide, and a 26px box around an 11px sprite is empty air that
still takes a heart. The blast is deliberately the reverse — 77px of art over a
64px box, so its outer flames are decoration you can stand in. Wide sprite,
narrow box, is the forgiving direction.

**Coverage.** The headless input tape dies within about ten seconds, so it never
reaches LVL 3 — the golden file proves the boss code does not disturb an
ordinary run (it is byte-identical), and `test/unit_boss.brainrot` drives the
fights directly, including a scripted frame loop that calls what `main` calls in
the order `main` calls it. Both bosses were additionally verified in the real
frame loop by temporarily lowering the thresholds.

---

## 13. Run structure

```
TITLE ──SPACE──► RUN ──dist >= SAHUR_DISTANCE──► SAHUR (win) ──► unlocks ENDLESS
                  │
                  └──hearts == 0──► GAME OVER ──R/SPACE──► RUN
```

- **Title.** Literal text, so it's M0. The `TUNG... TUNG... TUNG... SAHUR` beat
  plays out on a timer — four words, then he starts running. It's the best joke
  in the concept and it costs four `rl_draw_text` calls.
- **Sahur.** At `SAHUR_DISTANCE`, the sky finishes its turn and the run ends on
  `SAHUR SAVED / NEIGHBOURHOOD WOKEN / W`.
- **Endless Schizo Mode.** Unlocked by a Sahur clear, selectable from the title
  thereafter. Identical simulation with `SPEED_MAX_STORY` removed.
- **High score** is in-session only. Brainrot has no file I/O, so persistence is
  a known gap, not an oversight — noted in §15.

---

## 14. Architecture

### 14.1 `main` holds the shape; `sim.brainrot` holds the work

M0 shipped with the entire frame loop in `skibidi main`, because three
constraints acted together to make anything else impossible:

- No globals, so all state is a `main` local.
- No struct pointer arithmetic, so a helper cannot walk a pool.
- **At most one struct type per function signature**, so a helper could not take
  both `gang Ent *e` and a `gang World *w`.

That last one was decisive, and it was a bug rather than a design: the semantic
analyser checked struct-pointer parameters against a *reversed* parameter list,
so it rejected the correct call and accepted the swapped one — which the runtime
then bound positionally, writing one struct's field offsets through the other's
pointer. Silent cross-type corruption, reached by trusting the error message.
Fixed in [#294](https://github.com/Brainrotlang/brainrot/pull/294).

So the extraction this section promised would be mechanical has happened.
`src/sim.brainrot` holds the per-entity and per-player steps —
`world_advance`, `player_physics`, `ent_scroll`, `ent_hits_body`,
`player_take_hit`, `award_bonk` — each taking what it acts on plus the world.
`main` holds the loop's *shape*: the state machine, the pools, and the order the
eleven steps run in.

**The pool loops have left `main` too.** They were forced there by C5 — no
pointer arithmetic or indexing on struct pointers, so a helper could only ever
be handed one already-resolved `&pool[i]` and the iteration had to live at the
call site. That landed upstream
([brainrot#316](https://github.com/Brainrotlang/brainrot/pull/316), from #311),
so `sim.brainrot` now owns the passes: `pool_scroll`, `pool_bat_pass`,
`pool_body_pass`, `pool_free_slot`, and the `bombs_*` set for the other pool
type.

Each pass owns the **iteration and the geometry**; `main` keeps the **response**
— the sound, the scoring, the state change. That is why they hand back a count
or a flag rather than reaching for the audio seam: simulation never draws and
never plays, and that split is what the headless harness relies on.

`main` went 477 → 411 lines. The only pool loops left in it are the three
*draw* loops, and those belong there — `sim.brainrot` must not draw.

C4 (a struct field as an array of structs) landed at the same time
([#315](https://github.com/Brainrotlang/brainrot/pull/315)), so a God-struct is
now possible. It is deliberately **not** used: passing `(pool, n, world)` says
what a pass needs, while nesting the pools inside `World` would hand every
helper everything and call it an improvement.

The evidence that the extraction was behaviour-preserving is that
`test/expected/headless.txt` did not move by a single byte: 3000 frames of
spawns, collisions, combos, deaths and restarts produce identical output before
and after. That is what the golden files are for.

### 14.2 What *can* be extracted today

Pure functions over scalars, and single-struct-type helpers. These are also
exactly the parts worth testing (§16):

| File | Contents |
| --- | --- |
| `src/math.brainrot` | `rng_next`, `clampf`, `absf`, `lerpf` |
| `src/collide.brainrot` | `aabb` (8 `chad` params, returns `cap`) |
| `src/curve.brainrot` | `speed_to_lvl`, `spawn_gap`, `fair_clamp` |
| `src/draw.brainrot` | HUD helpers — scalar params, `rl_*` calls |
| `src/main.brainrot` | `skibidi main`: state, frame loop, pools |

### 14.3 Frame loop order

Order matters; this is the contract:

```
1.  dt = rl_get_frame_time(), clamped to 0.05      🚽 don't let a hitch teleport entities
2.  speed integration, dist, score, lvl
3.  input sample (jump, bat)
4.  player physics + ground clamp
5.  timers tick down (atk_t, iframe_t)
6.  spawn tick -> gap -> fairness clamp -> pool slot
7.  entity scroll + despawn offscreen
8.  collision: bat pass, then body pass
9.  state transitions (sahur reached? hearts zero?)
10. draw: sky, ground, entities, player, bat, HUD
11. rl_window_should_close
```

Step 1's clamp is not optional. `rl_get_frame_time` after a window drag or a
first-frame shader compile can return a large `dt`, and at 900 px/s an unclamped
spike tunnels every entity straight through the player.

### 14.4 Verified skeleton

This compiles and runs against `main` @ `3ce8a3a`. Note `pool[i].alive == L`
rather than `!pool[i].alive`, and `chad` values passed directly into the
int-typed `rl_draw_rectangle`:

```c
#cooked <raylib>

gang Ent { chad x; chad y; chad w; chad h; rizz kind; cap alive; };

skibidi main {
    rl_init_window(1280, 720, "TUNG TUNG TUNG SAHUR: RUN");
    rl_set_target_fps(60);

    chad px = 200.0;  chad py = 464.0;  chad pvy = 0.0;
    cap  grounded = W;
    chad speed = 260.0;
    chad dist  = 0.0;

    gang Ent pool[16];
    flex (rizz i = 0; i < 16; i = i + 1) { pool[i].alive = L; }

    cap running = W;
    goon (running) {
        chad dt = rl_get_frame_time();
        edgy (dt > 0.05) { dt = 0.05; }

        speed = speed + 3.0 * dt;
        dist  = dist + speed * dt;

        cap jump = rl_is_key_down(32);
        edgy (jump) { edgy (grounded) { pvy = 0.0 - 1000.0; grounded = L; } }

        pvy = pvy + 2600.0 * dt;
        py  = py + pvy * dt;
        edgy (py > 560.0 - 96.0) { py = 560.0 - 96.0; pvy = 0.0; grounded = W; }

        flex (rizz i = 0; i < 16; i = i + 1) {
            edgy (pool[i].alive) {
                pool[i].x = pool[i].x - speed * dt;
                edgy (pool[i].x < 0.0 - pool[i].w) { pool[i].alive = L; }
            }
        }

        rl_begin_drawing();
        rl_clear_background(12, 14, 34, 255);
        rl_draw_rectangle(0, 560, 1280, 160, 34, 28, 24, 255);
        rl_draw_rectangle(px, py, 48.0, 96.0, 196, 148, 92, 255);
        rl_end_drawing();

        cap wants_close = rl_window_should_close();
        edgy (wants_close) { running = L; }
    }

    rl_close_window();
    bussin 0;
}
```

---

## 15. Upstream dependencies

The zero-C rule means every gap below is a PR to `Brainrotlang/brainrot`. **M0
depends on none of them.**

### 15.1 `rayrot` additions

| ID | Ask | Unblocks | Milestone |
| --- | --- | --- | --- |
| ~~**B1**~~ | ~~`rl_draw_text_int` / `rl_measure_text_int`~~ — **landed**, [brainrot#292](https://github.com/Brainrotlang/brainrot/pull/292) | SCORE / LVL / final-score digits, i.e. all numeric HUD | ✅ |
| ~~**B2**~~ | ~~`rl_draw_texture_rec`~~ — **landed**, [brainrot#293](https://github.com/Brainrotlang/brainrot/pull/293). Negative source width/height mirrors a sprite | Sprite atlases, animation frames, tiled parallax | ✅ |
| ~~**B3**~~ | ~~`rl_init_audio_device`, `rl_load_sound`, `rl_play_sound`, `rl_unload_sound`, `rl_close_audio_device`~~ — **landed**, [brainrot#302](https://github.com/Brainrotlang/brainrot/pull/302). Music streams too. Initialise the audio device *before* the window; see `src/platform.brainrot` | The `TUNG` on every bat hit. The entire joke | ✅ |
| **B4** | `rl_draw_texture_pro` (scale / flip / rotate), `rl_draw_rectangle_lines`, `rl_get_time` | Facing flips, debug hitbox overlays | M3 |

B1 was the smallest change with the largest payoff and went first. Formatting
is fixed at one literal prefix plus one integer rather than a general format
string: a Brainrot-supplied `"%s"` would make the host read an argument that
isn't there, and nothing can check a user-supplied format against the single
`rizz` actually passed. B2 and B3 followed; **B4** is next.

#### Road B does not replace this yet

brainrot v0.2.0 shipped a *generated* raylib binding
([#307](https://github.com/Brainrotlang/brainrot/pull/307)) alongside the
hand-written one this game uses. It passes real aggregates by value —
`rl_draw_circle_v(pos, 60.0, orb)` with a `gang Vector2` and a `gang Color`,
rather than Road A's flattened `rl_draw_circle(640, 360, 100.0, 255, 0, 255,
255)`. It would delete most of `draw.brainrot`'s scalar shuffling.

**The game cannot move to it.** By-value structs cross the boundary as
*arguments* only; struct *returns* are rejected outright (ownership is
unresolved — ROADMAP Appendix B Q6). Every loader this game needs returns a
struct: `LoadTexture` → `Texture2D`, `LoadSound` → `Sound`,
`LoadMusicStream` → `Music`. So the generated binding has `rl_draw_texture_rec`
but no `rl_load_texture`, and there is no way to obtain the `gang Texture` it
wants. The two modules cannot be mixed either — same `rl_*` names, different
signatures.

Road A's integer handle tables are what make loading expressible at all, so
they stay until struct returns land. **B5**: struct returns across the native
ABI, which is what actually unblocks Road B for this game.

### 15.2 `brainrot` core bugs

Filed with the reproductions from §3.2. C3 is the one that changes this
document's architecture; C9 is the one that was silently wrong rather than
loudly broken, and the reason `make` probes the interpreter's version.

C4, C5 and `rant` parameters — the three filed as
[#311](https://github.com/Brainrotlang/brainrot/issues/311) after the v0.2.0
audit — all landed, and §14.1 records what they bought.

C14 replaced them as the limitation that shapes code here. It is why
`pool_free_slot()` scans the whole pool and keeps the first index instead of
returning the moment it finds one.

**C10 and C11 both shape code that looks like style.** Every `cap`-returning
call in this game lands in a local before it is tested — `cap show =
player_visible(&pl); edgy (show)` — because the direct form silently takes the
wrong branch. And `sim.brainrot` names its parameters `w`, `p`, `b`, `e`, `bm`
while `main` names its locals `wd`, `pl`, `bo`: that non-collision is
load-bearing and nothing enforces it. Both were found writing the bosses.

| ID | Bug | Severity |
| --- | --- | --- |
| ~~**C1**~~ | ~~`!` on `cap` returns the operand unchanged~~ — **fixed**, [#296](https://github.com/Brainrotlang/brainrot/pull/296). It had no lexer token at all; the catch-all discarded it | ✅ |
| ~~**C2**~~ | ~~`rizz k = someChad;` reinterprets the float's bits~~ — **fixed**, [#299](https://github.com/Brainrotlang/brainrot/pull/299). Array elements and pointer targets were broken too, in both directions | ✅ |
| ~~**C3**~~ | ~~Parameter list reversed for struct-pointer params~~ — **fixed**, [#294](https://github.com/Brainrotlang/brainrot/pull/294). The parser stores parameters backwards and the runtime compensated; the analyser did not | ✅ |
| ~~**C9**~~ | ~~A user-defined call in a value position runs twice and keeps the SECOND result~~ — **fixed**, [#303](https://github.com/Brainrotlang/brainrot/pull/303). `ast_accept()`'s pre-visit executed the call, then the statement's own visitor executed it again | ✅ |
| **C10** | A `cap`-returning call cannot be used directly as a condition — `edgy (f())` errors and takes the FALSE branch ([#313](https://github.com/Brainrotlang/brainrot/issues/313)) | **High** |
| **C11** | A caller's local shadows a callee's *parameter name* during analysis, so a correct call is rejected ([#312](https://github.com/Brainrotlang/brainrot/issues/312)) | **High** |
| **C12** | A bare `bussin;` is a parse error, so a `skibidi` cannot return early ([#283](https://github.com/Brainrotlang/brainrot/issues/283)) | Medium |
| ~~**C4**~~ | ~~A struct field cannot be an array of structs~~ — **fixed**, [#315](https://github.com/Brainrotlang/brainrot/pull/315) | ✅ |
| ~~**C5**~~ | ~~No pointer arithmetic on struct pointers~~ — **fixed**, [#316](https://github.com/Brainrotlang/brainrot/pull/316). This is the one that let the pool loops leave `main` | ✅ |
| ~~**C13**~~ | ~~`rant` parameters on user-defined functions~~ — **fixed**, [#314](https://github.com/Brainrotlang/brainrot/pull/314). Twenty one-per-file loaders became two | ✅ |
| **C14** | A `bussin` inside a loop is caught by the loop's own jump buffer, so it runs as `break` and then kills the process with "No scope to exit" and no output ([#319](https://github.com/Brainrotlang/brainrot/issues/319)) | **High** |
| **C6** | No top-level globals | Medium |
| **C7** | No `*(p + i) = v` / `p[i] = v` through a pointer parameter | Low — workaround is fine |
| **C8** | No math builtins (`sqrt`, `floor`, `abs`, `min`, `max`, `rand`) | Low — hand-rolled |

---

## 16. Testing

A game loop cannot run headlessly in CI. The simulation can — and making that
true is a design requirement, not a nicety.

**Rule: no `rl_*` call may appear outside step 10 of the frame loop (§14.3) or
`src/draw.brainrot`.** Simulation never draws; drawing never mutates state.

That split is enforced by two seams, both of which ship in the real game:

- `src/platform.brainrot` — `plat_dt`, `plat_jump_down`, `plat_bat_pressed`,
  `plat_should_close`, and a `plat_trace` that does nothing.
- `src/draw.brainrot` — every `rl_draw_*` call in the game.

`test/platform_fake.brainrot` and `test/draw_fake.brainrot` implement the same
signatures with a fixed timestep, a scripted input tape, and no rendering.
Every seam takes the frame number even where it doesn't need it, purely so the
two implementations stay interchangeable.

**The harness is generated, not copied.** `make headless` produces
`src/.headless.gen.brainrot` from `src/main.brainrot` with three `sed` edits
that swap those two `#cooked` lines and drop `<raylib>`. The entity pools, the
spawner, the fairness clamp, both collision passes and the state machine are the
code that ships — a hand-written copy would drift, and this cannot. The
generation step asserts that all three substitutions actually landed.

Two layers, both pure Brainrot, mirroring the upstream `test_cases/*.brainrot`
+ `tests/expected_results.json` convention. Neither needs raylib or a display:

1. **Unit** (`test/unit_*.brainrot`). `rng_next` pinned against the *published*
   Park–Miller sequence from seed 1, plus 10,000 draws to prove Schrage's method
   never leaves int32. `aabb` overlap/miss/edge-touch, and the real bat geometry
   — the grounded swing window measured in pixels of approach, the proof that
   the bat reaches further right than the body, and that an apex swing correctly
   misses a grounded enemy. `speed_to_lvl` at tier boundaries, `spawn_gap`
   monotonicity and floor, `pick_kind`'s level gate, the sky palette.
2. **Integration** (`make headless`). 3000 frames at a fixed `dt`, with the
   state sampled every 250 frames into the golden file. The tape's periods were
   swept rather than guessed, so one run covers the combo path, the damage path,
   the restart path and the attack cooldown.

### 16.1 What each layer can and cannot reach

The blind tape dies roughly every ten seconds, so `speed` never leaves LVL 1 in
the integration run and the difficulty curve is **not** covered there. Making
the tape a better player is not possible — the seams give it the frame number,
not the game state.

So the curve is covered at unit level instead: `unit_curve.brainrot` integrates
`speed` and `dist` at the same 60 Hz the game steps at and prints the feel table
in §7.2 directly, including the measured 4:58 to Sahur. That table is generated
from the code, so the two cannot disagree.

The fairness invariant gets the treatment it deserves — a sweep over every speed
from 260 to 1200, all nine kind pairs, and the full jitter range, asserting that
no combination produces a gap shorter than one jump arc. The arc is *derived*
from `t_gravity()` and `t_jump_v()` rather than hardcoded, so retuning gravity
without retuning `FAIR_JUMP_JUMP` fails in CI instead of in someone's run.

Because the interpreter is built with ASan and UBSan, a leak, an overflow or a
stray write is a loud test failure rather than a silent corruption.

---

## 17. Repository layout

```
tung-tung-sahur/
├── DESIGN.md
├── README.md
├── Makefile              🚽 `make play`, `make test`
├── src/
│   ├── main.brainrot     🚽 skibidi main: state + frame loop
│   ├── math.brainrot     🚽 rng_next, clampf, absf, lerpf
│   ├── collide.brainrot  🚽 aabb
│   ├── curve.brainrot    🚽 speed_to_lvl, spawn_gap, fair_clamp
│   └── draw.brainrot     🚽 HUD + entity draw helpers
├── test/
│   ├── unit_*.brainrot
│   ├── headless.brainrot
│   └── expected/
└── assets/               🚽 empty until B2 lands
```

`#cooked` splices, so every file under `src/` other than `main.brainrot` holds
definitions only — no second `skibidi main`.

### 17.1 Build and run

The game does not vendor Brainrot. It expects a `brainrot` checkout with
`rayrot` built, as a sibling directory by default and overridable:

```bash
# once, in the brainrot checkout
make && make rayrot

# here
make play
# == BRAINROT_PATH=$(BRAINROT_DIR)/rayrot $(BRAINROT_DIR)/brainrot src/main.brainrot
```

`BRAINROT_PATH` must point at a directory containing `raylib.so`, or
`#cooked <raylib>` cannot resolve. See
[`docs/rayrot.md`](https://github.com/Brainrotlang/brainrot/blob/main/docs/rayrot.md)
for raylib installation — it is the single source of truth and this repo will
not duplicate it.

---

## 18. Milestones

### M0 — "Rectangles at 03:30 AM" *(no upstream dependencies)*

Playable core, primitives only. Title card, run, game over, restart.

- [x] Fixed-arc jump, gravity, ground clamp
- [x] Bat: 0.15 s active / 0.30 s cooldown, works airborne
- [x] Obstacle + Patapim pools (16 each), spawn, scroll, despawn
- [x] AABB collision, bat pass before body pass
- [x] Continuous speed curve; LVL derived for display
- [x] Time-based spawn gaps with the fairness clamp
- [x] 3 hearts, i-frames
- [x] Score + combo multiplier
- [x] Seeded PRNG; seed shown on game over
- [x] HUD: hearts, 8-segment speed bar, literal labels
- [x] Sky palette stepping with LVL
- [x] Title screen with the `TUNG... TUNG... TUNG... SAHUR` beat
- [x] Headless test harness + golden files

### M1 — "Sprites and sky" *(needs B2)*

- [x] Numeric HUD (B1)
- [ ] Sprite sheets and the run cycle (B2)
- [ ] Parallax: mountains, palms, houses, foreground foliage
- [ ] Duck
- [ ] Patapim variants; armored breaks the rule at LVL 4

### M2 — "Bosses and noise"

- [x] Tralalero Tralala at LVL 3
- [x] Bombardiro Crocodilo at LVL 6, projectile pool
- [x] Audio: the `TUNG`, the jump, damage, the opening sting, and a `bruh`
- [ ] Boss art — both fights ship in primitives, like M0 did

### M3 — "Sahur"

- [ ] `SAHUR_DISTANCE` win state and ending card
- [ ] Endless Schizo Mode unlock
- [ ] Facing flips, debug hitbox overlay (B4)

---

## 19. Non-goals and known gaps

- **No persistence.** Brainrot has no file I/O; high scores are in-session.
  Revisit if a `stdrot` file API ever lands.
- **No pause, no menus beyond title/game-over.** It's an arcade runner.
- **No resolution scaling.** 1280×720 fixed until B4.
- **No meme canon fidelity.** Tung Tung Sahur has no unified continuity —
  characters are allies in one fan version and enemies in another. Patapim as
  the recurring rival is a design choice grounded in how the two are commonly
  powerscaled against each other, not a claim about lore. Variants are invented
  freely and that's fine.
- **No C in this repository.** If the game needs something the engine can't do,
  the engine gets better. That constraint is the point: this game is a forcing
  function for Brainrot, and every gap in §15 is a gap the language had anyway.
