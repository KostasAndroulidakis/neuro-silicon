# cocotb simulation flow (Icarus Verilog).
#   make            run all tests at RTL level
#   make GATES=yes  run against the gate-level netlist from the GDS build
#   make clean
#
# Source files are NOT listed here: they are read from ../info.yaml so that
# the list exists in exactly one place.

SIM ?= icarus
FST ?= -fst
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src

PROJECT_SOURCES := $(shell python3 -c "import yaml; print(' '.join(yaml.safe_load(open('$(SRC_DIR)/../info.yaml'))['project']['source_files']))")

ifneq ($(GATES),yes)

# RTL simulation
SIM_BUILD        = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate-level simulation (netlist produced by the gds workflow)
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

COMPILE_ARGS    += -I$(SRC_DIR)
VERILOG_SOURCES += $(PWD)/tb.v

TOPLEVEL = tb
COCOTB_TEST_MODULES = test_smoke

include $(shell cocotb-config --makefiles)/Makefile.sim
