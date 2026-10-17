<!--- This file becomes the project's page in the Tiny Tapeout datasheet. -->

## How it works

Two leaky integrate-and-fire neurons detect the direction of an object passing
between two sensors. Each neuron receives one sensor's spike directly and the
other sensor's spike through a delay line, so it fires only when the object
moves in "its" direction. Threshold, leak, weights and delay are set over SPI.

## How to test

Connect two digital sensors (e.g. IR break-beam) to `ui[0]` and `ui[1]`,
configure the registers over SPI from the demo board's RP2040, and watch
`uo[0]` / `uo[1]` pulse as an object passes left-to-right or right-to-left.

## External hardware

Two IR break-beam sensors (or push buttons for a manual demo), two LEDs.
