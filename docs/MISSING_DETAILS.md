# Missing Details Status

This file tracks values that were originally missing from the PDFs and what the professor reply resolved.

## Resolved by professor reply

- No separate `b` parameter; use `f_i` as the viscous friction coefficient.
- Full scalar plant values: `EA`, `v_ref`, `T_ref`, `T_max`.
- Full per-roller arrays: `R`, `J`, `f`; span lengths `L`.
- P01-P10 are fixed, not re-sampled.
- ET1/ET3/ET6 amplitudes and timings are defined.
- ET3M operating points are defined as line-speed multipliers `[0.5, 1.0, 2.0]`.
- EVR and EV1 should be skipped for reproduction for now.
- Sensor-noise seed is `0`; noise is `0.3% of T_max`, not `T_ref`.
- SN published figures use `Tlog = 20 ms`; NF uses `Tlog = 5 ms`.

## Still to verify if exact matching is required

- Exact first-order LPF discretization formula.
- SysID optimizer bounds, termination tolerances, and max iterations.
- Whether feedforward sign convention is already encoded exactly in the professor code.
