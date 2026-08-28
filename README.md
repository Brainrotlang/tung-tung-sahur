# TUNG TUNG TUNG SAHUR: RUN

An endless runner written in [Brainrot](https://github.com/Brainrotlang/brainrot),
rendered through [`brainray`](https://github.com/Brainrotlang/brainrot/blob/main/docs/brainray.md).

It is 03:30 AM. Tung Tung Tung Sahur runs east to wake the village for the
pre-dawn meal. Brr Brr Patapim keeps getting in the way.

> **jump to survive, bonk to score**

```
                          increasing speed →

     TUNG
      🪵
     /|\_🏏       🌲         🐒          📦
_____/ \__________|__________|___________|_______
                  ↑          ↑
              obstacle   Brr Brr Patapim
```

**This repository contains zero C.** Anything the game needs that Brainrot or
raylib can't reach today gets implemented *upstream*, in
[`Brainrotlang/brainrot`](https://github.com/Brainrotlang/brainrot). What lives
here is `.brainrot` and nothing else. See [DESIGN.md](DESIGN.md) for the full
design, the verified engine constraints, and the upstream dependency list.

## Controls

| | |
| --- | --- |
| `SPACE` / `UP` | jump |
| `X` / `Z` | TUNG (bat) |
| `R` / `SPACE` | run again, after a game over |
| `ESC` | quit |

## Running it

You need a [`brainrot`](https://github.com/Brainrotlang/brainrot) checkout with
the `brainray` module built. Clone it next to this repo:

```bash
git clone https://github.com/Brainrotlang/brainrot
cd brainrot
make            # the interpreter
make brainray   # the raylib binding -- needs raylib installed
cd ..
```

raylib setup for your OS is documented once, upstream, in
[`docs/brainray.md`](https://github.com/Brainrotlang/brainrot/blob/main/docs/brainray.md).
This repo will not duplicate it.

Then:

```bash
make play
```

If your `brainrot` checkout lives somewhere else:

```bash
make play BRAINROT_DIR=/path/to/brainrot
```

## Tests

```bash
make test
```

**The tests need neither raylib nor a display** — no window, no GPU, so this
runs anywhere the interpreter builds.

Two layers:

- **Unit** (`test/unit_*.brainrot`) — the pure scalar functions. The PRNG is
  pinned against the published Park–Miller sequence, the fairness clamp is swept
  across every speed, kind pair and jitter value, and the difficulty curve is
  integrated at 60 Hz and checked against the table in DESIGN.md §7.2.
- **Integration** (`make headless`) — the real frame loop, run for 3000 frames
  with a fixed timestep and a scripted input tape.

That second one is worth a note: the harness (`src/.headless.gen.brainrot`,
gitignored) is **generated from `src/main.brainrot`**, not copied from it. Three `sed` edits swap the raylib
platform and drawing layers for the fakes in `test/`; the entity pools, the
spawner, the collision passes and the state machine are the code that ships. A
copy would drift. This cannot.

Output is compared against golden files in `test/expected/`. When you change the
simulation on purpose:

```bash
make bless      # then read the diff before you commit it
```

## Layout

```
src/
  main.brainrot      skibidi main: state, the frame loop, the entity pools
  tune.brainrot      every tuning constant, as accessor functions
  math.brainrot      PRNG, clamp, lerp, abs -- stdrot has no math library
  collide.brainrot   aabb
  curve.brainrot     the difficulty curve, spawn table, fairness clamp
  platform.brainrot  input/time/window seam (raylib)
  draw.brainrot      every rl_draw_* call in the game
test/
  unit_*.brainrot    unit tests
  platform_fake.*    the headless input tape
  draw_fake.*        no-op rendering
  expected/          golden files
```

The whole frame loop is in one `skibidi main`, which looks wrong and isn't:
Brainrot has no globals, no pointer arithmetic on struct pointers, and a
semantic analyser that reverses the parameter list for functions with
struct-pointer parameters. Together those mean a helper cannot walk an entity
pool *and* cannot take both an entity and a world scalar. Everything that can be
extracted has been. See DESIGN.md §14.1 — and §15.2, which lists the upstream
fixes that would let this be structured properly.

## Status

**M0 — "Rectangles at 03:30 AM".** Playable core in primitives, no upstream
dependencies. Sprites, parallax and numeric HUD are M1 and need
`rl_draw_texture_rec` and formatted text upstream; bosses and audio are M2.
Milestones are in DESIGN.md §18.
