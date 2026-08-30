# TUNG TUNG TUNG SAHUR: RUN
#
# `make play`  runs the game   (needs raylib + brainray)
# `make test`  runs the tests  (needs neither -- no window, no GPU)

BRAINROT_DIR ?= ../brainrot
BRAINROT     := $(BRAINROT_DIR)/brainrot
# The raylib binding's directory. Upstream is renaming brainray/ -> rayrot/
# (Brainrotlang/brainrot), so take whichever exists rather than breaking on
# the day that merges. The COOKED MODULE is still `<raylib>` either way --
# only the directory and the make target change.
RAYMOD       := $(firstword $(wildcard $(BRAINROT_DIR)/rayrot \
                                       $(BRAINROT_DIR)/brainray) \
                            $(BRAINROT_DIR)/rayrot)

GEN      := src/.headless.gen.brainrot
UNITS    := $(wildcard test/unit_*.brainrot)
EXPECTED := test/expected
PROBE    := /tmp/tts-version-probe.brainrot

.PHONY: all play test units headless bless clean check-brainrot check-brainray \
        lint-native check-atlases

all: test

# ---------------------------------------------------------------- run

play: check-brainray lint-native
	BRAINROT_PATH=$(RAYMOD) $(BRAINROT) src/main.brainrot

# Every rl_* call in the game, checked without opening a window.
#
# `make test` swaps draw.brainrot and platform.brainrot for fakes, which is
# the point -- but it means the REAL rl_* calls are never looked at, and a
# wrong argument count there is invisible until someone runs the game. That
# is how `rl_draw_text_int` shipped with 9 of its 10 arguments.
#
# Semantic analysis runs over every cooked function body before `main`
# executes, so cooking the real modules into an empty `main` type-checks all
# of them and exits immediately. No window, no GPU, no frame loop.
LINT := /tmp/tts-native-lint.brainrot
lint-native: check-brainray
	@printf '#cooked <raylib>\n' > $(LINT)
	@for m in tune math collide curve sim draw platform; do \
	    printf '#cooked "%s/src/%s.brainrot"\n' "$$(pwd)" "$$m" >> $(LINT); \
	done
	@printf 'skibidi main { bussin 0; }\n' >> $(LINT)
	@out=$$(BRAINROT_PATH=$(RAYMOD) $(BRAINROT) $(LINT) 2>&1); rm -f $(LINT); \
	    if [ -n "$$out" ]; then \
	        echo "native call check FAILED:"; echo "$$out"; exit 1; \
	    fi; \
	    echo "ok    native calls" 

# Do the generated atlases still match the constants the game draws with?
# Needs Python + Pillow (same as tools/process_sprites.py), so it is not part
# of `make test`, which deliberately needs nothing but the interpreter.
check-atlases:
	@python3 tools/check_atlases.py

# --------------------------------------------------------------- test

test: units headless
	@echo "all green"

units: check-brainrot
	@fail=0; \
	for f in $(UNITS); do \
	    name=$$(basename $$f .brainrot); \
	    golden=$(EXPECTED)/$$name.txt; \
	    if [ ! -f $$golden ]; then \
	        echo "MISSING GOLDEN  $$name  (run: make bless)"; fail=1; continue; \
	    fi; \
	    if $(BRAINROT) $$f 2>&1 | diff -u $$golden - > /tmp/tts-$$name.diff; then \
	        echo "ok    $$name"; \
	    else \
	        echo "FAIL  $$name"; cat /tmp/tts-$$name.diff; fail=1; \
	    fi; \
	done; \
	exit $$fail

# The headless harness is GENERATED from src/main.brainrot, not a copy
# of it. Three sed edits swap the raylib platform and draw layers for the
# fakes in test/; everything else -- the entity pools, the spawner, the
# collision passes, the state machine -- is the code that ships. A copy
# would drift; this cannot.
$(GEN): src/main.brainrot test/platform_fake.brainrot test/draw_fake.brainrot
	@sed -e '/^#cooked <raylib>$$/d' \
	     -e 's|^#cooked "platform.brainrot"$$|#cooked "../test/platform_fake.brainrot"|' \
	     -e 's|^#cooked "draw.brainrot"$$|#cooked "../test/draw_fake.brainrot"|' \
	     src/main.brainrot > $@
	@grep -q 'platform_fake' $@ || { echo "headless generation failed: platform seam not swapped"; rm -f $@; exit 1; }
	@grep -q 'draw_fake' $@     || { echo "headless generation failed: draw seam not swapped"; rm -f $@; exit 1; }
	@! grep -q '^#cooked <raylib>' $@ || { echo "headless generation failed: raylib still cooked"; rm -f $@; exit 1; }

headless: check-brainrot $(GEN)
	@golden=$(EXPECTED)/headless.txt; \
	if [ ! -f $$golden ]; then \
	    echo "MISSING GOLDEN  headless  (run: make bless)"; exit 1; \
	fi; \
	if $(BRAINROT) $(GEN) 2>&1 | diff -u $$golden - > /tmp/tts-headless.diff; then \
	    echo "ok    headless"; \
	else \
	    echo "FAIL  headless"; cat /tmp/tts-headless.diff; exit 1; \
	fi

# Regenerate every golden file. Read the diff before committing it --
# a moved golden means the simulation changed, which is either the point
# of your commit or a bug you just wrote.
bless: check-brainrot $(GEN)
	@mkdir -p $(EXPECTED)
	@for f in $(UNITS); do \
	    name=$$(basename $$f .brainrot); \
	    $(BRAINROT) $$f > $(EXPECTED)/$$name.txt 2>&1; \
	    echo "blessed $$name"; \
	done
	@$(BRAINROT) $(GEN) > $(EXPECTED)/headless.txt 2>&1
	@echo "blessed headless"

clean:
	rm -f $(GEN) $(PROBE) /tmp/tts-*.diff

# ------------------------------------------------------------- checks

check-brainrot:
	@test -x $(BRAINROT) || { \
	    echo "no brainrot interpreter at $(BRAINROT)"; \
	    echo "clone https://github.com/Brainrotlang/brainrot next to this repo and run 'make' in it,"; \
	    echo "or point this one at it:  make BRAINROT_DIR=/path/to/brainrot"; \
	    exit 1; }
# The game needs brainrot >= v0.2.0 for three fixes, none of which is
# visible in the binary, and none of which FAILS on an older interpreter --
# they all just quietly produce the wrong answer. So: probe.
#
#   !   logical NOT (#296)  -- discarded by the lexer, so every guard
#                              written with `!` ran backwards
#   17  float->int (#299)   -- reinterpreted the bit pattern instead of
#                              converting, so the HUD read plausible nonsense
#   1   call-once (#303)    -- `rizz x = f();` ran f TWICE and kept the
#                              SECOND result. This game has 16 resource
#                              loads written that way, so every texture,
#                              sound and music track was loaded twice and
#                              one of each leaked; and `cap launched =
#                              player_jump(&pl)` reported the second
#                              attempt -- the one that finds itself already
#                              airborne -- so the jump sound never fired
#                              while the jump itself worked.
#   7   rant parameters     -- one loader taking a path instead of twenty
#                              identical ones (#311).
#   9   struct ptr indexing -- `e[1].v`, which is what lets a helper walk
#                              an entity pool instead of every loop living
#                              in `skibidi main` (#311).
#
# The last two DO fail loudly rather than silently, but they fail inside
# whichever cooked file used them, which is a worse place to read the news
# than here. v0.1.8 answers 'L 1099694080 2'; v0.2.0 errors out.
	@printf 'gang E { rizz v; }; rizz plen(rant s){ bussin 7; } rizz pidx(gang E *e){ bussin e[1].v; } rizz p(rizz *n){ *n = *n + 1; bussin *n; } skibidi main{ cap off = L; chad g = 17.5; rizz k = g; rizz c = 0; rizz h = p(&c); gang E pool[2]; pool[0].v = 3; pool[1].v = 9; yapping("%%b %%d %%d %%d %%d", !off, k, c, plen("x"), pidx(&pool[0])); bussin 0;}' > $(PROBE)
	@got=$$($(BRAINROT) $(PROBE) 2>/dev/null); rm -f $(PROBE); \
	    test "$$got" = "W 17 1 7 9" || { \
	        echo "$(BRAINROT) is too old: probe printed '$$got', expected 'W 17 1 7 9'"; \
	        echo "the game needs a brainrot NEWER than v0.2.0 -- logical NOT"; \
	        echo "(brainrot#296), float-to-int conversion (#299), a call running"; \
	        echo "exactly once (#303), rant parameters and struct pointer"; \
	        echo "indexing (both #311). Update and rebuild:"; \
	        echo "    git -C $(BRAINROT_DIR) pull && make -C $(BRAINROT_DIR)"; \
	        exit 1; }

check-brainray: check-brainrot
	@test -f $(RAYMOD)/raylib.so || { \
	    echo "no raylib module at $(RAYMOD)/raylib.so"; \
	    echo "install raylib, then run 'make rayrot (or make brainray on older checkouts)' in $(BRAINROT_DIR)"; \
	    echo "setup instructions: $(BRAINROT_DIR)/docs/brainray.md"; \
	    exit 1; }
# The HUD needs rl_draw_text_int, which landed in Brainrotlang/brainrot#292.
# Without this check a stale brainray fails at parse time with a bare
# "Undefined function" and a line number, which says nothing about why.
	@grep -q rl_draw_text_int $(RAYMOD)/raylib.so || { \
	    echo "$(RAYMOD)/raylib.so predates rl_draw_text_int (brainrot#292)"; \
	    echo "the HUD needs it. Update $(BRAINROT_DIR) and rebuild:"; \
	    echo "    git -C $(BRAINROT_DIR) pull && make -C $(BRAINROT_DIR) brainray"; \
	    exit 1; }
