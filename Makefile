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
	rm -f $(GEN) /tmp/tts-*.diff

# ------------------------------------------------------------- checks

check-brainrot:
	@test -x $(BRAINROT) || { \
	    echo "no brainrot interpreter at $(BRAINROT)"; \
	    echo "clone https://github.com/Brainrotlang/brainrot next to this repo and run 'make' in it,"; \
	    echo "or point this one at it:  make BRAINROT_DIR=/path/to/brainrot"; \
	    exit 1; }

check-brainray: check-brainrot
	@test -f $(BRAINRAY)/raylib.so || { \
	    echo "no brainray module at $(BRAINRAY)/raylib.so"; \
	    echo "install raylib, then run 'make brainray' in $(BRAINROT_DIR)"; \
	    echo "setup instructions: $(BRAINROT_DIR)/docs/brainray.md"; \
	    exit 1; }
