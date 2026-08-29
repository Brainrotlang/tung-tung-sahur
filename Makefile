# TUNG TUNG TUNG SAHUR: RUN
#
# `make play`  runs the game   (needs raylib + brainray)
# `make test`  runs the tests  (needs neither -- no window, no GPU)

BRAINROT_DIR ?= ../brainrot
BRAINROT     := $(BRAINROT_DIR)/brainrot
BRAINRAY     := $(BRAINROT_DIR)/brainray

GEN      := src/.headless.gen.brainrot
UNITS    := $(wildcard test/unit_*.brainrot)
EXPECTED := test/expected
PROBE    := /tmp/tts-version-probe.brainrot

.PHONY: all play test units headless bless clean check-brainrot check-brainray

all: test

# ---------------------------------------------------------------- run

play: check-brainray
	BRAINROT_PATH=$(BRAINRAY) $(BRAINROT) src/main.brainrot

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
# The game needs logical NOT (brainrot#296) and float-to-int conversion
# (#299). Neither is visible in the binary, so probe for them. An older
# interpreter does not fail -- it discards every `!` and reinterprets every
# float assignment, so the guards run backwards and the HUD reads plausible
# nonsense. That is worth one probe to turn into a sentence.
	@printf 'skibidi main{ cap off = L; chad g = 17.5; rizz k = g; yapping("%%b %%d", !off, k); bussin 0;}' > $(PROBE)
	@got=$$($(BRAINROT) $(PROBE) 2>/dev/null); rm -f $(PROBE); \
	    test "$$got" = "W 17" || { \
	        echo "$(BRAINROT) is too old: probe printed '$$got', expected 'W 17'"; \
	        echo "the game needs logical NOT (brainrot#296) and float-to-int"; \
	        echo "conversion (#299). Update and rebuild:"; \
	        echo "    git -C $(BRAINROT_DIR) pull && make -C $(BRAINROT_DIR)"; \
	        exit 1; }

check-brainray: check-brainrot
	@test -f $(BRAINRAY)/raylib.so || { \
	    echo "no brainray module at $(BRAINRAY)/raylib.so"; \
	    echo "install raylib, then run 'make brainray' in $(BRAINROT_DIR)"; \
	    echo "setup instructions: $(BRAINROT_DIR)/docs/brainray.md"; \
	    exit 1; }
# The HUD needs rl_draw_text_int, which landed in Brainrotlang/brainrot#292.
# Without this check a stale brainray fails at parse time with a bare
# "Undefined function" and a line number, which says nothing about why.
	@grep -q rl_draw_text_int $(BRAINRAY)/raylib.so || { \
	    echo "$(BRAINRAY)/raylib.so predates rl_draw_text_int (brainrot#292)"; \
	    echo "the HUD needs it. Update $(BRAINROT_DIR) and rebuild:"; \
	    echo "    git -C $(BRAINROT_DIR) pull && make -C $(BRAINROT_DIR) brainray"; \
	    exit 1; }
