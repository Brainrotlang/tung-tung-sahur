# Contributing to TUNG TUNG TUNG SAHUR: RUN

Thanks for wanting to help the wooden guy run east. This is a game written
**entirely in [Brainrot](https://github.com/Brainrotlang/brainrot)**, so
contributing here is mostly writing `.brainrot`, tuning constants, and golden
tests — with one hard rule up front.

## The zero-C rule

**This repository contains no C, and never will.** If the game needs something
the Brainrot interpreter or the `rayrot` raylib binding can't do yet — a new
builtin, a language fix, another raylib primitive — that work happens
*upstream* in [`Brainrotlang/brainrot`](https://github.com/Brainrotlang/brainrot),
and the game consumes it once it lands. The running list of these dependencies
is `DESIGN.md` §15. A PR that adds C, a build step that compiles C, or a vendored
`.so`/`.dll` source here is in the wrong repo — open it against `brainrot`.

## Getting set up

The game runs on the `brainrot` interpreter + the `rayrot` module. Clone
`brainrot` **next to this repo** and build both. `make` probes the interpreter
and tells you (and why) if it's too old — **>= v0.3.0** for the language
features the game uses; the release bundles pin **v0.5.1**, the first with
native Windows:

```bash
git clone https://github.com/Brainrotlang/brainrot ../brainrot
make -C ../brainrot           # interpreter
make -C ../brainrot rayrot    # raylib binding (needs raylib; see brainrot/docs/rayrot.md)

# from this repo:
make play                     # run the game (needs raylib + a display)
```

Prefer not to build? Every [release](https://github.com/Brainrotlang/tung-tung-sahur/releases)
ships a ready-to-run bundle per platform (Linux, macOS, Windows) — see the
README's "Running it".

## Tests are expected

Tests need **neither raylib nor a display**, so they run anywhere the
interpreter builds — there's no excuse to skip them.

```bash
make test          # unit_*.brainrot + the headless frame loop, vs test/expected/ goldens
make lint-native   # type-checks every real rl_* call without opening a window
make check-atlases # generated atlases still agree with tune.brainrot (needs Python + Pillow)
```

When you change the game:

- **Simulation / behavior** — add or extend a `test/unit_*.brainrot`, then
  `make bless` to regenerate the golden files, and **read the diff before you
  commit it**. A moved golden is either exactly your intent or a bug you just
  wrote; the diff is where you tell the difference.
- **Drawing / the raylib seam** (`draw.brainrot`, `platform.brainrot`) — run
  `make lint-native`. The tests swap those layers for fakes, so a wrong `rl_*`
  argument count is otherwise invisible until someone runs the game.
- **Sprite art** — regenerate with `tools/process_sprites.py` and run
  `make check-atlases`.

The headless harness (`src/.headless.gen.brainrot`) is **generated** from
`src/main.brainrot` — never edit it, and never commit it (it's gitignored).

## Where things live

`DESIGN.md` is the single source of truth for tuning, the speed curve, boss
phases, and the architecture; cite the relevant section (`§7.2`, `§12`, …) when
you change behavior. `src/tune.brainrot` is the one place tuning constants live.
`src/main.brainrot` holds the loop's shape; `src/sim.brainrot` does the work;
simulation never draws or plays audio (the headless harness depends on that
split). See `DESIGN.md` §17 for the full repository layout.

## Pull requests

1. Fork, branch, and make your change.
2. `make test` **and** `make lint-native` pass; if you touched art,
   `make check-atlases` too.
3. Golden-file changes: include them, and make sure the diff is intentional.
4. Describe what changed and why, referencing the `DESIGN.md` section it
   affects (or update `DESIGN.md` if the change moves the design).

CI (`.github/workflows/ci.yml`) runs the headless tests and the atlas check on
every PR.

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the GPL (see [LICENSE](LICENSE)); contributions
are made under the same terms.
