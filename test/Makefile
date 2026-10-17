# cocotb simulation flow (Icarus Verilog).
#
#   make                  top level (tb.v wrapper) with test_smoke
#   make BLOCK=tick_gen   one block, driven directly by cocotb (no Verilog tb),
#                         with test_<block>.py
#   make blocks           every block in BLOCKS, one after the other
#   make GATES=yes        top level against the gate-level netlist (after gds)
#   make clean
#
# Source files are read from ../info.yaml so the list exists in exactly one place.

SIM ?= icarus
FST ?= -fst
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src

PROJECT_SOURCES := $(shell python3 -c "import yaml; print(' '.join(yaml.safe_load(open('$(SRC_DIR)/../info.yaml'))['project']['source_files']))")

# Blocks that have their own test_<block>.py
BLOCKS = tick_gen edge_detect delay_line neuron_seq

ifneq ($(GATES),yes)

SIM_BUILD        = sim_build/rtl$(if $(BLOCK),_$(BLOCK),)
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

SIM_BUILD        = sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DUSE_POWER_PINS
COMPILE_ARGS    += -DSIM
COMPILE_ARGS    += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

COMPILE_ARGS += -I$(SRC_DIR)

ifeq ($(BLOCK),)
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb
COCOTB_TEST_MODULES = test_smoke
else
TOPLEVEL = $(BLOCK)
COCOTB_TEST_MODULES = test_$(BLOCK)
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: blocks
blocks:
	@for b in $(BLOCKS); do \
	  echo "=== block: $$b ==="; \
	  $(MAKE) --no-print-directory BLOCK=$$b || exit 1; \
	  python3 -m cocotb_tools.check_results results.xml || exit 1; \
	done
