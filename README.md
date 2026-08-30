# TUNG TUNG TUNG SAHUR: RUN

An endless runner written in [Brainrot](https://github.com/Brainrotlang/brainrot),
rendered through [`rayrot`](https://github.com/Brainrotlang/brainrot/blob/main/docs/rayrot.md).

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
the `rayrot` module built. Clone it next to this repo:

```bash
git clone https://github.com/Brainrotlang/brainrot
cd brainrot
make            # the interpreter
make rayrot     # the raylib binding -- needs raylib installed
cd ..
```

raylib setup for your OS is documented once, upstream, in
[`docs/rayrot.md`](https://github.com/Brainrotlang/brainrot/blob/main/docs/rayrot.md).
This repo will not duplicate it.

**You need brainrot v0.2.0 or newer.** The game depends on four fixes it turned
up itself — `rl_draw_text_int`
([#292](https://github.com/Brainrotlang/brainrot/pull/292)), working `!`
([#296](https://github.com/Brainrotlang/brainrot/pull/296)), float-to-integer
assignment ([#299](https://github.com/Brainrotlang/brainrot/pull/299)), and a
call running exactly once ([#303](https://github.com/Brainrotlang/brainrot/pull/303)).

`make` probes for them and tells you to update, because an older interpreter
does not *fail* — it silently discards every `!`, reinterprets every float
assignment, and runs every `rizz x = f();` twice while keeping the second
result. The guards run backwards, the HUD reads plausible nonsense, and every
texture and sound loads twice with one of each leaked.

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
  across every speed, kind pair and jitter value, the difficulty curve is
  integrated at 60 Hz and checked against the table in DESIGN.md §7.2, and both
  boss fights are driven through a full three-cycle kill.
- **Integration** (`make headless`) — the real frame loop, run for 3000 frames
  with a fixed timestep and a scripted input tape.

Two more, separate:

```bash
make lint-native     # every rl_* call, type-checked without a window
make check-atlases   # the generated atlases still match tune.brainrot
```

The tests swap `draw.brainrot` and `platform.brainrot` for fakes, which is the
point — but it means the **real** `rl_*` calls are never looked at, and a wrong
argument count there is invisible until someone runs the game. `lint-native`
cooks the real modules into an empty `main`, so semantic analysis type-checks
every native call and exits. No window, no GPU. `make play` runs it first.

`check-atlases` guards the other half of the same seam. `tools/process_sprites.py`
decides each atlas's frame size and anchor from the art's own proportions, and
`tune.brainrot` has to be *told* — nothing connected the two, so regenerating art
at a different size silently desynced the draw call from the atlas. It needs
Python and Pillow, so it is not part of `make test`.

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
assets/
  tung-tung-tung/    Tung's source frames (running/jump/swing)
  patapim/           Patapim's source frames
  obstacles/         crate, post
  backgrounds/       the four parallax layers
  *.png              the generated atlases -- tools/process_sprites.py
src/
  main.brainrot      skibidi main: the state machine, the pools, step order
  sim.brainrot       the simulation: one function per step, over structs
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

`main` holds the frame loop's *shape* — the state machine, the pools, the order
the eleven steps run in — and `sim.brainrot` holds each step's actual work.

The pool loops have left `main` too, now that
[brainrot#316](https://github.com/Brainrotlang/brainrot/pull/316) added indexing
on struct pointers — `sim.brainrot` owns the passes, and each one hands back a
count or a flag so `main` keeps the response (the sound, the scoring, the state
change). Simulation never draws and never plays; that split is what the headless
harness relies on. The only pool loops left in `main` are the three *draw* ones.

It used to be much worse. Until
[brainrot#294](https://github.com/Brainrotlang/brainrot/pull/294) a helper
couldn't take both an entity and the world at all, so *everything* lived in
`main`. See DESIGN.md §14.1.

## Status

**M0 — "Rectangles at 03:30 AM"** shipped: the playable core in primitives, with
no upstream dependencies at all. **M1** shipped too — the numeric HUD landed
with B1, B2 (`rl_draw_texture_rec`) unblocked sprites, animation and parallax,
and all of it is drawn from real art now.

**M2 has shipped.** rayrot got audio in
[brainrot#302](https://github.com/Brainrotlang/brainrot/pull/302), so the game
plays a title sting, a `TUNG` on every bat hit, a jump, a damage grunt, and a
`bruh` on the run that ends. Both bosses are in: **Tralalero Tralala** at LVL 3
and **Bombardiro Crocodilo** at LVL 6, sharing one three-cycle phase machine
and pausing the normal spawner while they own the screen. Both are drawn from
art, as are Bombardiro's bombs and their blasts. They arrive at **LVL 3** and
**LVL 6** — on level rather than score, because score includes bonk bonus and so
brought the boss *sooner* to the player who was playing better.

**M3** is next: the `SAHUR_DISTANCE` win state, the ending card, and Endless
Schizo Mode. Milestones are in DESIGN.md §18.
