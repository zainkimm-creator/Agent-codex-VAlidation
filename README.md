# R2R Paper Validator Dashboard

This repository validates a roll-to-roll (R2R) system-identification paper using a reproducible simulation, SysID pipeline, validation scripts, and dashboard.

The goal is to reproduce the paper's major results section by section: 3-span R2R dynamics, cascade PI + feedforward control, 7-parameter SysID, logging-rate validation, excitation-design validation, sensor-noise/LPF validation, drift sensitivity, and digital-twin-assisted retuning.

## Core Model

State vector:

```text
x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
```

Input vector:

```text
u = [u_UW, u_Nip, u_RW]
```

Output vector:

```text
y = [T1, T2, T3]
```

SysID parameter vector:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

Definitions:

```text
kt_i = R_i^2 / J_i
kf_i = f_i / J_i
ku_i = R_i / J_i
```

`ku_i` is derived and is not directly estimated.

## Professor Data Update

The professor reply resolves several missing implementation details:

- There is no separate `b` parameter; the supplement's `b_i` is a typo for `f_i`.
- P01-P10 are fixed representative plants from the 204-plant pool.
- Full plant scalar values and per-roller arrays are now provided in `configs/plants_p01_p10.yaml`.
- ET1, ET3, ET6, and ET3M excitation definitions are now provided in `configs/excitation_profiles.yaml`.
- EVR and EV1 should be skipped for reproduction for now.
- Sensor noise uses seed `0`, `numpy.default_rng(0)`, and sigma equal to `0.3% of T_max`.
- SN figures use `Tlog = 20 ms`; NF figures use `Tlog = 5 ms`.

See `docs/PROFESSOR_DETAILS_RESOLVED.md` for the full implementation-ready details.

## Repository Structure

```text
r2r-paper-validator/
|-- AGENTS.md
|-- README.md
|-- configs/
|   |-- plants_p01_p10.yaml
|   |-- excitation_profiles.yaml
|   |-- noise_lpf.yaml
|   `-- paper_targets.yaml
|-- backend/
|-- frontend/
|-- scripts/
|-- data/
|-- outputs/
`-- docs/
    |-- PROFESSOR_DETAILS_RESOLVED.md
    `-- MISSING_DETAILS.md
```

## Build Order

Do not build the frontend first. Use this order:

```text
1. Config loading
2. R2R equations
3. RK4 integration
4. Cascade PI + feedforward controller
5. Closed-loop simulator
6. Excitation generators
7. Noise + LPF
8. SysID estimator
9. RMSE_theta + FIM metrics
10. Validation scripts
11. Report generator
12. Backend API
13. Frontend dashboard
```

## Validation Modes

### Trend Validation

Use when exact code-level implementation details are still missing.

Checks qualitative agreement:

- E_Toggle / ET6 / ET3 should outperform ET1 under sensor noise.
- Tlog around 10-20 ms should be best under sensor noise.
- J drift should dominate EA drift.
- HGS+BO(5) should reduce real evaluations compared with CS-BO(30).

### Exact Validation

Use when all implementation details are available.

Each result must include:

```text
paper target
computed result
absolute difference
percentage difference
pass/fail
notes
```

## Key Commands

Suggested final commands after implementation:

```bash
pytest
```

```bash
python scripts/run_all_validations.py --mode trend
```

```bash
python scripts/run_all_validations.py --mode exact
```

```bash
python scripts/make_report.py
```

## Config Files

### `configs/plants_p01_p10.yaml`

Contains P01-P10 plant definitions:

- `EA_N`
- `v_ref_mps`
- `T_ref_N`
- `T_max_N`
- `R_m`
- `J_kgm2`
- `f_Nms_per_rad`
- `L_m`
- `regime`
- `zeta_CL_min`
- `overshoot_percent`

### `configs/excitation_profiles.yaml`

Contains reproduction profiles:

- ET1
- ET3
- ET6
- ET3M

EVR and EV1 are disabled for reproduction based on professor guidance.

### `configs/noise_lpf.yaml`

Contains final sensor-noise reproduction settings:

- seed `0`
- `numpy.default_rng(0)`
- sigma = `0.003 * T_max`
- first-order 100 Hz LPF
- SN `Tlog = 20 ms`
- NF `Tlog = 5 ms`

## Definition of Done

A task is done only when:

1. Code is implemented.
2. Tests are added.
3. Tests pass.
4. Output CSV/figures/JSON are produced where applicable.
5. Paper-target comparison is reported.
6. Assumptions and remaining issues are documented.
