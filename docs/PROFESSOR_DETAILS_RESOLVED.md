# Professor Details Resolved for R2R Paper Validator
This document converts the professor's reply into implementation-ready dashboard details. Use it together with `configs/*.yaml`.
## 1. Corrections and modeling conventions
- There is **no separate `b` parameter** in the model. The only friction term is viscous friction `f_i`; the supplement's `b_i` is a typo for `f_i`.
- Complete per-plant set: scalar `EA`, `v_ref`, `T_ref`, `T_max`; per-roller arrays `R`, `J`, `f`; span lengths `L`.
- Roller order: `[UW, Nip, RW]` = `[0, 1, 2]`.
- Span order for `L`: `[span0, span1, span2]`.
- Feeder is the speed-master boundary: it imposes `v = v_ref` and is not torque-controlled.
- UW and RW share physical model values in each plant because both reels use the same model.
- Note: the parsed professor table showed `HE [N]`; this is interpreted as `EA [N]`. Material labels are normalized to the supplementary table: P01=PE and P09/P10=Cu.

## 2. Plant scalar table
| Plant | Pool ID | Material | Scale | Regime | EA (N) | v_ref (m/s) | T_ref (N) | T_max (N) | zeta_CL_min | OS% |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| P01 | P001 | PE | lab | O-UD | 3,200 | 0.5 | 12.0 | 40.0 | 0.151 | 45.8 |
| P02 | P049 | PET | lab | O-UD | 9,600 | 0.3 | 64.8 | 216.0 | 0.237 | 45.3 |
| P03 | P053 | PET | lab | H-Osc | 40,000 | 0.5 | 270.0 | 900.0 | 0.35 | 28.8 |
| P04 | P060 | PET | pilot | O-UD | 50,000 | 3.0 | 337.5 | 1125.0 | 0.201 | 41.0 |
| P05 | P139 | Paper | prod | O-UD | 144,000 | 3.0 | 216.0 | 720.0 | 0.144 | 50.1 |
| P06 | P158 | Al | lab | H-Damp | 310,500 | 0.3 | 229.5 | 765.0 | 0.515 | 9.8 |
| P07 | P163 | Al | pilot | H-Osc | 414,000 | 2.0 | 306.0 | 1020.0 | 0.357 | 31.8 |
| P08 | P177 | Al | prod | O-UD | 1,242,000 | 5.0 | 918.0 | 3060.0 | 0.179 | 55.3 |
| P09 | P186 | Cu | lab | H-Damp | 351,000 | 0.1 | 360.0 | 1200.0 | 0.53 | 16.1 |
| P10 | P189 | Cu | pilot | O-UD | 351,000 | 3.0 | 360.0 | 1200.0 | 0.21 | 51.9 |

## 3. Per-roller / per-span arrays
| Plant | R_m [UW,Nip,RW] | J_kgm2 [UW,Nip,RW] | f_Nms_per_rad [UW,Nip,RW] | L_m [span0,span1,span2] |
|---|---|---|---|---|
| P01 | [0.15, 0.1, 0.15] | [0.11126, 0.265196, 0.11126] | [0.707698, 1.0, 0.707698] | [2.0, 3.0, 3.0] |
| P02 | [0.2, 0.1, 0.2] | [0.359562, 0.193405, 0.359562] | [3.0, 0.163318, 3.0] | [3.0, 2.0, 2.0] |
| P03 | [0.2, 0.1, 0.2] | [0.445464, 0.097544, 0.445464] | [1.685698, 0.278819, 1.685698] | [2.0, 2.0, 3.0] |
| P04 | [0.25, 0.1, 0.25] | [2.382481, 0.403738, 2.382481] | [10.0, 2.998943, 10.0] | [3.0, 10.0, 5.0] |
| P05 | [0.75, 0.2, 0.75] | [90.373903, 8.416216, 90.373903] | [3.497247, 0.319941, 3.497247] | [5.0, 20.0, 8.0] |
| P06 | [0.2, 0.1, 0.2] | [0.494378, 0.180335, 0.494378] | [3.0, 1.0, 3.0] | [2.0, 3.0, 3.0] |
| P07 | [0.3, 0.1, 0.3] | [5.73936, 0.221068, 5.73936] | [1.052208, 0.125884, 1.052208] | [5.0, 8.0, 5.0] |
| P08 | [0.75, 0.2, 0.75] | [937.741061, 12.177233, 937.741061] | [1.303144, 0.225839, 1.303144] | [8.0, 30.0, 10.0] |
| P09 | [0.15, 0.1, 0.15] | [0.609345, 0.272279, 0.609345] | [3.0, 0.387705, 3.0] | [2.0, 2.0, 2.0] |
| P10 | [0.3, 0.1, 0.3] | [44.902091, 0.472429, 44.902091] | [10.0, 3.0, 10.0] | [5.0, 5.0, 5.0] |

## 4. Fixed plant selection
P01-P10 are fixed, hand-picked representative plants from the 204-plant pool. Nothing is re-sampled at run time. Pool ID mapping: P01=P001, P02=P049, P03=P053, P04=P060, P05=P139, P06=P158, P07=P163, P08=P177, P09=P186, P10=P189.

## 5. Excitation profiles for reproduction
- Every tension step in ET1/ET3/ET6 is `+20%` of that channel's `T_ref`.
- Absolute step size is plant-dependent, e.g., P01 = 2.4 N and P08 = 183.6 N.
- Common timing: 2 s settle, then 5 s per episode, with `Kp_star = 100` during excitation.

| Excitation | Reproduce? | Definition | Total duration |
|---|---|---|---:|
| ET1 | Yes | One +20% step on UW at t=2 s, held to end | 7 s |
| ET3 | Yes | Cumulative steps: UW at 2 s, Nip at 7 s, RW at 12 s; each held | 17 s |
| ET6 | Yes | ET3 up-steps, then back to base in same order: UW down 17 s, Nip down 22 s, RW down 27 s | 32 s |
| ET3M | Yes | Three independent ET3 runs with line speed multipliers v0 x {0.5, 1.0, 2.0}, identified jointly | 3 x 17 s |
| EVR | No | Skip for reproduction; professor says published EVR numbers were not true ramp-only | - |
| EV1 | No | Skip for reproduction; same issue in second segment | - |

## 6. Noise and LPF settings for reproduction
- Final dataset uses **one noise realization per plant**, not three seeds.
- Seed: `numpy.default_rng(0)`.
- Noise model: additive i.i.d. Gaussian per tension channel.
- Noise sigma: `0.3% of T_max`, the load-cell full scale, **not** T_ref.
- Add noise to measured tensions, then apply a first-order 100 Hz low-pass filter.
- SN figures use `Tlog = 20 ms`; NF uses `Tlog = 5 ms`.

| Plant | T_max (N) | sigma = 0.003*T_max (N) |
|---|---:|---:|
| P01 | 40.0 | 0.120 |
| P02 | 216.0 | 0.648 |
| P03 | 900.0 | 2.700 |
| P04 | 1125.0 | 3.375 |
| P05 | 720.0 | 2.160 |
| P06 | 765.0 | 2.295 |
| P07 | 1020.0 | 3.060 |
| P08 | 3060.0 | 9.180 |
| P09 | 1200.0 | 3.600 |
| P10 | 1200.0 | 3.600 |

## 7. What is now resolved vs still missing
Resolved: P01-P10 scalar values, per-roller arrays, excitation definitions for ET1/ET3/ET6/ET3M, noise seed/model, SN/NF logging periods, and EVR/EV1 skip decision.
Still implementation-sensitive: exact first-order LPF discretization formula and optimizer tolerances/bounds, unless these already exist in the code or professor later provides them.
