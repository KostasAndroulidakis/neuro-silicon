# Roadmap: heterogeneous navigation SoC

neuro-silicon is the **neuromorphic unit** of a larger, longer-term design: a
navigation co-processor for GNSS-denied UAVs. This page records what that design is,
what fits in which technology, and the order of steps. It is a roadmap, not a spec.

## Target system (north star)

```ascii
 event camera ──► Neuromorphic unit (SNN)  ──┐
 frame camera ──► INT8 MAC array (CNN)     ──┼──► RISC-V MCU (VIO/EKF fusion) ──► flight controller (PX4)
 IMU ────────────────────────────────────────┘        via UART/CAN
```

The chip is a **co-processor**: it outputs position/velocity estimates and hazard
flags. The flight controller stays a proven commercial one.

## What fits where (honest estimates, 2026)

| Function | Needs | 130 nm, ~2 mm² | Verdict |
| --- | --- | --- | --- |
| MCU: EKF fusion, PID | RISC-V + FPU, 50-100 MHz | fits (CV32E40P/Ibex) | OK as co-processor, not as sole FC |
| CNN terrain matching (TRN) | ~1 GOP/frame, 1-4 MB weights | 16x16 INT8 MAC array ~50 GOPS; weights off-chip | demo at 1-5 fps, acceptable for TRN |
| SNN night TRN / optical flow | thousands of neurons | 32-64 neurons | no; coarse-grid flow only |
| VIO | classical (MSCKF/VINS) on MCU | yes, low rate | OK; SNN-VIO is research |
| SLAM | MB-GB map memory | no | not for this class of drone |
| Obstacle detection (looming, direction) | tens-hundreds of neurons | yes | **the part that works at 130 nm** |

Memory, not logic, is the binding constraint: ~4-5 mm² per Mbit of SRAM at 130 nm,
5-10x denser at 28/22 nm.

## Steps

| # | What | Where | Cost | Proves |
| --- | --- | --- | --- | --- |
| 1 | Neuromorphic unit: 2-64 LIF neurons, SPI, time-multiplexed core (this repo) | simulation, FPGA, optionally Tiny Tapeout 1 tile | 0-200 EUR | the unit + the full flow |
| 2 | Whole heterogeneous system on FPGA with real event-camera data | FPGA | 0-300 EUR | the architecture, and how many neurons/MACs are really needed |
| 3 | ~2 mm² demo SoC: RISC-V + SRAM + SNN + small MAC array | IHP SG13G2 open-source MPW (free, non-commercial, via an institution) or direct (~2.8k EUR/mm²) | 0-6k EUR | silicon of the architecture |
| 4 | Product-grade module | 28/22 nm via Europractice, with funding and a team | 50-150k EUR | the product |

Fabrication options compared (prices as published 2026, verify before ordering):
Tiny Tapeout IHP 6x4 ~1.7k EUR (chips on loan, non-commercial); IHP open-source MPW free
(<2 mm², non-commercial, open-source design, PR to IHP-Open-DesignLib); IHP direct
~2.8k EUR/mm² SG13G2, 20 bare dies; chipIgnite $14,950 for 15 mm² Sky130 with Caravel RISC-V
and 100 packaged parts; Europractice TSMC 65 nm mini@sic ~4.5k EUR per mm², TSMC 28 nm
~10.6k EUR per mm², ST 28 nm FDSOI ~1.5k EUR per academic project. Europractice and TSMC
require a legal entity (company or university) for the PDK NDA.
