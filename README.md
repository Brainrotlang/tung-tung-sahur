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

**Your brainrot checkout needs to be recent.** The game depends on three fixes
it turned up itself — `rl_draw_text_int`
([#292](https://github.com/Brainrotlang/brainrot/pull/292)), working `!`
([#296](https://github.com/Brainrotlang/brainrot/pull/296)), and float-to-integer
assignment ([#299](https://github.com/Brainrotlang/brainrot/pull/299)).

`make` probes for all three and tells you to update, because an older
interpreter does not fail — it silently discards every `!` and reinterprets every
float assignment, so the guards run backwards and the HUD reads plausible
nonsense.

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

The pool loops stay in `main`, and that part is still forced: a struct field
can't be an array of structs, and there's no pointer arithmetic on struct
pointers, so a helper can't walk a pool — only act on one already-resolved
`&pool[i]`. It used to be worse. Until
[brainrot#294](https://github.com/Brainrotlang/brainrot/pull/294) a helper
couldn't take both an entity and the world at all, so *everything* lived in
`main`. See DESIGN.md §14.1.

## Status

**M0 — "Rectangles at 03:30 AM"** shipped: the playable core in primitives, with
no upstream dependencies at all. **M1** shipped too — the numeric HUD landed
with B1, B2 (`rl_draw_texture_rec`) unblocked sprites, animation and parallax,
and all of it is drawn from real art now.

**B3 has landed** ([brainrot#302](https://github.com/Brainrotlang/brainrot/pull/302)),
so brainray has audio: a streamed music track and one-shot sounds. The game
plays a title sting, a `TUNG` on every bat hit, a jump, a damage grunt, and a
`bruh` on the run that ends. What's left of **M2** is the bosses. Duck and the
Patapim variants need no engine work at all. Milestones are in DESIGN.md §18.
