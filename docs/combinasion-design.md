# LA GRANDE COMBINASION — design draft

> **Status: implemented and tested — the fight *and* the reveal.** The canonical,
> shipped spec is now `DESIGN.md §12.6`. Code: `t_combi_*` / `t_reveal_*` in
> `src/tune.brainrot`, the `combi_*` functions in `src/sim.brainrot`, the reveal
> state machine + `t_state_win()` in `src/main.brainrot`, `draw_combinasion()` /
> `draw_sky(drain)` / `draw_namecard()` / `draw_win()` in `src/draw.brainrot`,
> `plat_music_load/play/stop` in `src/platform.brainrot`, and the
> winnability/fairness assertions in `test/unit_boss.brainrot`. This document
> remains the fuller design rationale; numbers here were starting points, and the
> shipped values live in `tune.brainrot`.

---

## 12.6 LA GRANDE COMBINASION — the true final

U Din Din is the *story* cap (§12.3). Combinasion is what is behind it: the same
sprite language turned on the player. He wears every boss at once — the shark on
his back, a cactus, the elephant, the frog on a stopwatch, the lobster, the tire
— and swings the same bat Tung does. He is the developer, and the fight tells the
player so without a line of text.

He does **not** trigger on a level threshold like the other three. He triggers on
the U Din Din launch: the frame U Din Din's third bonk lands, the run does *not*
cut to the Sahur win. It keeps going for a beat, and then it stops being the same
game. See §12.6.1 — the silence is the mechanic.

### 12.6.1 The reveal (the silence is the mechanic)

The whole run has been loud and upbeat. The reveal works by taking that away, in
order, on a scripted timeline driven by the frame clock (not by level, not by
score — a fixed sequence of `combi_intro_t` beats):

1. **U Din Din dies.** Normal music keeps playing ~2.0–2.5 s. The run reads as
   won-and-continuing.
2. **Music cuts mid-stream**, deliberately *not* at a loop boundary — `plat`
   stops the stream on a frame the beat did not resolve on. It sounds wrong
   because it is.
3. **Ambient SFX persist ~1 s** — footsteps, wind, one last `TUNG` — then cut too.
4. **The sky drains.** Not the dawn ramp (§10.2): a separate drain keyed on
   `combi_intro_t` that **lerps the current sky RGB toward a dead grey-black**
   over ~2 s — `sky = lerp(sky_rgb(lvl), grey, combi_intro_t)`, per channel. This
   stays inside the existing `draw_sky` seam with no new colour math (a true
   luminance desaturation was the alternative; the grey-lerp reads as the world
   dimming out and costs nothing). Parallax layers (`bg_far..near`) slow to a stop.
5. **The HUD flickers** — hearts/score/lvl blink at a decaying interval, then hold.
6. **No boss bar. No name. Several seconds of near-silence** — this is the load-
   bearing beat. Do not start the track when the screen darkens.
7. **First cue of the new track** — a low guitar scrape / amp hum / count-in —
   arrives *out of the dark*, before he is visible. He walks in from the right.
8. **On full silhouette:** `LA GRANDE COMBINASION`, and the prog track detonates.
   The boss bar appears with it, not before.

`World.combi_intro_t` runs this like `did_dimdim` runs U Din Din's flag. The
simulation does not darken the sky or cut audio — `sim` never draws or plays
audio (§14). `sim` advances `combi_intro_t` and exposes an intro *stage*; `draw`
reads the stage for the desaturation ramp and HUD flicker, `platform` reads it
for the audio cuts. Same seam as everything else.

### 12.6.2 The one new rule: Tung moves horizontally

Every other boss is fought from `t_player_x()` — Tung is pinned, and the entire
game's geometry depends on it (the bomb-column welding in §12.2 is *because* he
cannot sidestep). Combinasion is the one fight that unpins him:

- `LEFT / A`, `RIGHT / D` move Tung between two arena margins.
- `SPACE / UP` jumps (unchanged). `X / Z` is TUNG (unchanged).
- The arena stops scrolling. Tung's `x` becomes **state** (`pl.x`) for the first
  time, clamped to `[t_combi_arena_l(), t_combi_arena_r()]`.

**This is gated to this fight only.** `pl.x` is initialised to `t_player_x()` and
only the Combinasion tick reads movement input into it; every other mode leaves
it at `t_player_x()`, so nothing about the runner or the other three bosses
changes. But collision that used the constant now has to read the field: the
player AABB and the bat hitbox in `sim.brainrot` take `pl.x`, which equals
`t_player_x()` in every mode except this one. That substitution is the real
surface area of this feature, and `unit_collide` / the other bosses' golden files
are the guard that it changed nothing outside the fight.

Horizontal movement is the point: it is what makes a two-verb moveset (teleport +
bat) feel like a different game while still being TUNG TUNG TUNG SAHUR: RUN.

### 12.6.3 The fundamental loop

Every attack is the same four states. There are no projectiles, no cactus/shark/
elephant attacks, no gravity tricks — one bastard teleporting around trying to
cave Tung's skull in.

```
TELEPORT_OUT → TELEPORT_TELL → WINDUP → SWING → chain? ─yes→ TELEPORT_OUT
                                                    │no
                                                    ↓
                                                 RECOVERY → TELEPORT_OUT
```

1. **TELEPORT_OUT.** He vanishes. Never deals damage — teleport changes
   positioning, it is not an unavoidable hit.
2. **TELEPORT_TELL.** A truthful destination marker appears ~`t_combi_tell()`
   (200–250 ms) before he materialises, at one of {left/right of Tung} ×
   {near/far}. Once he actually appears there, the marker never lied — that is
   what keeps it fair (contrast the fakeout, §12.6.6).
3. **WINDUP.** He materialises bat already raised, facing Tung, for
   `t_combi_windup()`. This is the player's *commit* window, not the reaction
   window — see §12.6.5. Answers: move out of the sweep, move behind him, or jump.
4. **SWING.** One huge horizontal sweep. The bat covers a wide arc **in front of
   him, not behind**. Two fundamental dodges: **jump over it**, or **get behind
   him before it lands**. Horizontal movement is what makes "behind" a real option.
5. **RECOVERY.** Only on a **whiff** (the sweep hit nothing) he is locked
   recovering for `t_combi_recovery()`. This is the only window `boss_vulnerable()`
   is true. Close and TUNG. Panic-run to the far margin and you are out of range
   when it opens.

The fight's whole question: *how little can I dodge and still survive, so I am
close enough to punish the whiff?*

### 12.6.4 HP and the parry

**3 TUNG hits.** Same rule as the others, harder to land. He is invulnerable
except during RECOVERY.

`TUNG` while he is **not** recovering does not chip him — it **parries**: `CLANG`,
he blocks with the bat, no damage, tiny knockback/stun. Its job is to *say* "you
cannot unga-bunga this boss," not to punish. Two constraints from §12.4:

- The parry stun must **not** lock Tung through an incoming tell+swing — an input
  that removes your ability to dodge is exactly the un-dodgeable-frame the
  invariant forbids. So the parry costs an attack-cooldown (no TUNG spam) but
  **never a movement/jump lockout**. `t_combi_parry_stun()` < `t_combi_tell()`.
- No instant-death punish. A whiffed player greed is a lost beat, not a heart.

### 12.6.5 Reaction windows (why 180 ms windup is still fair)

The house human floor is ~0.25 s to react (§12.2). The nightmare-phase windup
drops to ~180–220 ms, *below* that — so the **windup is not the reaction window;
the tell is.** Effective warning = `t_combi_tell()` + `t_combi_windup()`. The
invariant is geometric, derived the way `t_bomb_lead_min` and `t_shark_charge_h`
are:

> For every scripted swing, `tell + windup ≥ react_floor + travel`, where
> `travel` is the time to reach the nearest safe answer from the worst
> survivable position of the previous beat — either `jump_rise_time` (clear the
> sweep) or `Δx / t_combi_run_speed()` (get behind him / out of the arc),
> whichever the script leaves available.

So the numbers are *outputs*. Pick `t_combi_run_speed()` and the arena width
first; the minimum legal `tell + windup` per phase falls out, and the phase tables
below must respect it. `unit_boss.brainrot` asserts it (§12.6.7).

### 12.6.6 The three phases (choreography, not randomness)

The fight is a **fixed script**, not the music. Each phase is a `combi_script[]`
loop of beats, each `{ t, action, side, dist }` where `action ∈ {TELL, SWING,
FAKE}` and `t` is the time *within the phase's loop*. That fixed script is the
Sans element on its own — after enough deaths the player is not reading
randomness, they are remembering the *sequence* (Undertale's attacks are not on
Megalovania's beats either; the memorised choreography is what does it). The music
is atmosphere: `finalboss.ogg` plays and loops under the fight, unsynchronised
(§12.6.10). It never gates a beat, so the choreography stays deterministic and
frame-clock-driven, which is also what makes it unit-testable (§12.6.7).

**Phases are HP-gated** — the brief's own structure. HP 3 runs phase 1's loop; the
loop repeats until the player lands the whiff-punish; the bonk drops HP to 2 and
switches to phase 2's loop; and so on. A stuck player re-runs the current phase's
loop, which is exactly how a boss fight should treat someone who has not earned the
next tier. Three bonks and he is launched (§12.6.8's hit-reaction).

So each phase's **trigger is the bonk that ended the previous one**, and its
`t`-columns below (tell/windup/recovery) are the timings inside its loop, tightening
per phase.

| Phase | HP | Teaches | `tell` | `windup` | `recovery` | Shape |
| --- | --- | --- | --- | --- | --- | --- |
| **1 — the rules** | 3→2 | *make him miss, don't attack him* | ~250 ms | ~350 ms | ~550 ms | teleport → windup → swing → recovery, generous positions. One whiff → one TUNG. |
| **2 — teleport chains** | 2→1 | *survive a sequence for one opening* | ~250 ms | ~250 ms | ~400 ms | he does not open after every swing: `tel→swing→tel→tel→swing→recovery`; behind-chains: `tel-behind→swing→tel-ahead→swing→tel-behind→swing→recovery`. |
| **3 — the nightmare** | 1→0 | *nothing new. relentless.* | ~200 ms | ~180–220 ms | short/rare | 20–30 s of chained `tel/swing` with fakeouts, constantly flipping which way the player must go. Same two mechanics. |

Phase 1's on-open prompt (`TUNG HIM — X` via `draw_boss_bar`, §12.5) fires like
the parking bosses'. Phases 2–3 drop it: by then the whiff *is* the cue, same as
U Din Din's charge.

**Fakeouts (the one permitted variation).** He may TELEPORT_OUT, show a tell, drop
it, show another elsewhere — repositioning without attacking. Especially phase 3:
`right-tell → cancel → left-tell → cancel → right-tell → materialise → SWING`.
Still only teleport + bat, still fair because the marker is truthful the instant
he *commits*. A fakeout is a `FAKE` beat in the script; a real one is `TELL`
followed by `SWING`.

### 12.6.7 §12.4 for Combinasion — the invariant, and the test

Restated: *every contact leaves a safe input*, now over **(position × jump-timing)**
instead of jump-timing alone. The scripted choreography is what makes that
brute-forceable, and it is a stronger, better test than the others:

`unit_boss.brainrot` replays `combi_script[]` at the real fight speed and, for
each `SWING`, computes the set of positions/jumps reachable from the previous
beat's *survivable set* (given `t_combi_run_speed()` and the arena), then asserts:

- **Solvability:** every SWING has ≥1 reachable (position, jump-or-behind) input
  that survives it — the un-dodgeable-frames == 0 probe, generalised.
- **Punishability:** every scripted RECOVERY is reachable — from at least one
  surviving position, Tung can close to bat range and land TUNG inside
  `t_combi_recovery()`. A fight whose only openings are unreachable is unwinnable
  exactly like the pre-fix shark (§12.4), so the test asserts reach the way §12.5
  asserts the parking bosses reach the bat.
- **No free hit:** no SWING is survivable by standing still doing nothing (mirrors
  the croc's "none survivable by doing nothing").

Because the script is data, a new beat that breaks winnability fails the golden
test rather than shipping. That is choreography made checkable.

### 12.6.8 How it is built

- **Reuses `gang Boss`.** Add an `xt`/`state` enum (`TELEPORT_OUT` … `RECOVERY`)
  and a `dest_x`/`dest_side` — U Din Din already added `dir` to that struct for
  itself; the others ignore fields they do not use (§12.5). `boss_tick()` routes
  `t_boss_combinasion()` into `combi_move()`, exactly as it routes U Din Din into
  `dindin_move()` before the shared survive/open timer.
- `boss_vulnerable()` is `state == RECOVERY`. TUNG-in-range while vulnerable →
  damage; TUNG anywhere else → parry. That is the entire hit logic.
- Movement is a **pure function of `(state, script_index, elapsed)`** through the
  script table, not a lerp — same reasoning as §12.5 (a lerp never quite arrives,
  and the destination must be exact for the tell to be truthful).
- Player `pl.x` integration is the only cross-cutting change (§12.6.2).

### 12.6.9 Art

`assets/combinacion/attack1..5.png` (448×672, magenta key ~`rgb(226,0,116)`) is a
**windup→swing strip**, bat-low (1) → bat-overhead-raised (5). Native facing is
**right** (like U Din Din), so `draw_boss()` mirrors him when he faces left —
negative source width, anchor flipped, the existing path. Through the `tex >= 0`
fallback (§12.5) the fight can ship on these five frames by mapping states to
them (WINDUP → 5, SWING → 5→1, RECOVERY → 1, idle/tell → a mid frame), then gain
dedicated frames later. **Still needed for the full read:** a teleport-tell
marker vfx, a distinct RECOVERY/vulnerable pose, and a parry/`CLANG` pose. He is
tall and portrait — pick the collision box off the man's body, not the menagerie
(the shark and cactus overhang like Tralalero's snout, §12.5), and split
`t_combi_frame_w()` from `t_combi_w()` so `check_atlases.py` guards it.

### 12.6.10 Audio — the track, unsynchronised

The track is `assets/music/finalboss.ogg` — **127.8 s, 44.1 kHz stereo**. It is
**not** synchronised to the fight: it plays and loops as atmosphere, and the
choreography runs off the frame clock (§12.6.6). No playhead reads, no accent
alignment — the fixed sequence is what makes the fight memorable, not the music.
So the boss track is just the existing `plat_music_open()` path pointed at
`finalboss.ogg` (looping via `rl_set_music_looping`), started on the reveal's
detonation beat (§12.6.1 step 8).

The one audio thing the reveal *does* need is the **mid-stream cut of the normal
track** (§12.6.1 step 2). That needs a `plat_music_stop()` wrapper over
`rl_stop_music`, which the `rayrot` binding already exposes — `platform.brainrot`
just does not wrap it yet (it wraps load/play/loop/volume/update/unload). A volume
ramp to 0 via the existing `rl_set_music_volume` is the fallback if a hard stop
reads too abruptly. Either way it is a local wrapper, not an upstream PR.

### 12.6.11 Where it slots in the run

`§13` gains a branch: the U Din Din launch that used to end the story does not go
straight to `SAHUR`. It runs the §12.6.1 reveal, then the Combinasion fight; the
Sahur win is behind *him*. That is what makes the fakeout land — the player is
several seconds into thinking they won.
