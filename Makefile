# Simulation flow for neuro-silicon.
# Usage:
#   make sim  TOP=lif_neuron   compile rtl/*.sv + tb/tb_lif_neuron.sv and run it
#   make wave                  open the last run's waveforms in GTKWave
#   make clean                 delete all generated files

TOP   ?= lif_neuron
BUILD := build

sim:
	mkdir -p $(BUILD)
	iverilog -g2012 -Wall -s tb -o $(BUILD)/$(TOP).vvp rtl/*.sv tb/tb_$(TOP).sv
	cd $(BUILD) && vvp $(TOP).vvp

wave:
	gtkwave $(BUILD)/dump.vcd

clean:
	rm -rf $(BUILD)

.PHONY: sim wave clean
