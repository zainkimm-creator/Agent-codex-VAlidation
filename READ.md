# R2R Paper Validator - Complete Project Guide

This repository validates a roll-to-roll (R2R) web tension control and system-identification paper. It now contains the backend mathematical model, RK4 integrator, cascade PI controller, multirate simulator, excitation/noise/SysID modules, validation scripts, backend API, and a dashboard UI that reads generated output files.

The project root used in this workspace is:

```text
C:\Users\user\Documents\Agent work
```

## 1. What Has Been Done

### Repository and Config Setup

- Added the project structure under `backend/`, `configs/`, `scripts/`, `docs/`, `frontend/`, `frontend-html/`, `data/`, `reports/`, and `outputs/`.
- Added professor-provided implementation details in `docs/PROFESSOR_DETAILS_RESOLVED.md`.
- Added missing-detail tracking in `docs/MISSING_DETAILS.md`.
- Added plant, excitation, noise/LPF, and paper-target configs:
  - `configs/plants_p01_p10.yaml`
  - `configs/excitation_profiles.yaml`
  - `configs/noise_lpf.yaml`
  - `configs/paper_targets.yaml`
  - `configs/default.yaml`

### Mathematical Model and Integrator

- Implemented the six-state R2R dynamics in `backend/models/r2r_dynamics.py`.
- Implemented fixed-step RK4 integration in `backend/models/rk4.py`.
- Added tests for derivative shape, finite derivatives, velocity/tension coupling, friction, and RK4 finite updates.

### Controller

- Implemented cascade PI plus feedforward controller in `backend/models/controller.py`.
- Outer loop controls tension.
- Inner loop controls roller angular velocity.
- Feedforward compensates tension load and roller friction.
- Controller outputs `motor_torque_Nm`; the old `inputs_V` compatibility path was removed from the newer simulator interface.

### Simulation

- Wired simulation to use `r2r_derivatives()` and `rk4_step()`.
- Implemented closed-loop multirate simulator in `backend/simulation/simulator.py`.
- Uses:
  - RK4 plant integration every `dt = 1 ms`
  - controller update every `Ts = 10 ms`
  - zero-order hold (ZOH) on torque between controller updates
  - configurable logging period `Tlog`
  - YAML plant loading
  - CSV logging

### Excitation Profiles

- Implemented professor-provided exact excitation metadata:
  - `ET1`: UW step at `t = 2 s`, total `7 s`
  - `ET3`: UW at `2 s`, Nip at `7 s`, RW at `12 s`, total `17 s`
  - `ET6`: up/down sequence, total `32 s`
  - `ET3M`: three ET3 operating points with line-speed multipliers `[0.5, 1.0, 2.0]`
  - `EV1` and `EVR`: skipped in exact reproduction mode

### Noise and LPF

- Implemented additive tension-only sensor noise in `backend/noise/sensor_noise.py`.
- Noise uses `numpy.default_rng(0)`.
- Noise standard deviation is:

```text
sigma = 0.003 * T_max
```

- Implemented first-order 100 Hz LPF in `backend/noise/filters.py`.
- Torque is not noised.
- Configured:
  - noise-free `Tlog = 5 ms`
  - sensor-noise `Tlog = 20 ms`

### System Identification

- Implemented seven-parameter SysID estimator in `backend/sysid/estimator.py`.
- Uses one-step prediction residuals and SciPy `least_squares(method="trf")`.
- Estimates:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

- Returns:
  - `theta_est`
  - error table
  - `RMSE_theta`
  - convergence status
  - optimizer success flag
  - cost and number of function evaluations

### Validation Scripts

- Added logging validation:
  - `backend/validation/validate_logging.py`
  - `scripts/run_logging_validation.py`
- Added excitation validation:
  - `backend/validation/validate_excitation.py`
  - `scripts/run_excitation_validation.py`
- Generated outputs go under:
  - `outputs/csv/`
  - `outputs/figures/`
  - `outputs/validation_runs/latest/`

### Backend API

- Added FastAPI routes in `backend/api/main.py`.
- Important routes:
  - `GET /health`
  - `GET /equations`
  - `GET /metadata`
  - `GET /dashboard/outputs`
  - `POST /simulate`
  - `POST /sysid`
  - `POST /validate/logging-rate`
  - `POST /validate/excitation`
  - `POST /validate/drift`
  - `POST /retune`
  - `POST /upload`
- Static artifacts are served through `/artifacts/...`.

### Dashboard UI

- Built the React dashboard in `frontend/src/App.jsx`.
- Dashboard reads backend-generated JSON/CSV/PNG outputs through `GET /dashboard/outputs`.
- Paper targets are not hard-coded in React; the backend reads them from `configs/paper_targets.yaml`.
- Dashboard pages:
  - Plant Setup
  - Model Equations
  - Controller
  - SysID Setup
  - Logging Validation
  - Excitation Validation
  - Noise/LPF Validation
  - Drift Validation
  - Retuning Validation
  - Export Report
- Each page shows:
  - formula
  - input config
  - paper target
  - dashboard result
  - pass/fail
  - plot/table
  - CSV download link when the CSV exists

## 2. Repository Structure

```text
.
|-- AGENTS.md
|-- README.md
|-- READ.md
|-- configs/
|   |-- default.yaml
|   |-- plants_p01_p10.yaml
|   |-- excitation_profiles.yaml
|   |-- noise_lpf.yaml
|   `-- paper_targets.yaml
|-- backend/
|   |-- api/
|   |-- excitation/
|   |-- models/
|   |-- noise/
|   |-- simulation/
|   |-- sysid/
|   |-- tests/
|   `-- validation/
|-- frontend/
|   |-- components/
|   |-- public/
|   `-- src/
|-- frontend-html/
|-- scripts/
|-- data/
|   |-- paper_reference/
|   |-- processed/
|   `-- uploads/
|-- reports/
|   |-- figures/
|   `-- validation_summary/
|-- outputs/
|   |-- csv/
|   |-- figures/
|   `-- validation_runs/latest/
`-- docs/
```

## 3. Mathematical Equations Used

### 3.1 State Vector

The model state is:

```text
x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
```

where:

```text
T1, T2, T3              = web tensions in N
omega_UW, omega_Nip,
omega_RW               = roller angular speeds in rad/s
```

### 3.2 Input Vector

The plant input is motor torque:

```text
u = [u_UW, u_Nip, u_RW]
```

where:

```text
u_UW, u_Nip, u_RW = motor torque inputs in N*m
```

### 3.3 Output Vector

The measured output for tension control and SysID is:

```text
y = [T1, T2, T3]
```

### 3.4 Boundary Conditions

The implemented boundaries are:

```text
T0 = 0
T4 = 0
v0 = v_ref
```

`T0` is the upstream boundary tension, `T4` is the downstream boundary tension, and `v0` is the feeder/reference web velocity.

### 3.5 Roller Surface Velocity

Each roller angular speed is converted to surface speed:

```text
v_i = omega_i * R_i
```

where:

```text
v_i     = roller surface velocity, m/s
omega_i = angular speed, rad/s
R_i     = roller radius, m
```

### 3.6 Web Tension Dynamics

For each span `i = 1..3`:

```text
dT_i/dt = (EA/L_i) * (v_i - v_{i-1}) + (1/L_i) * (T_{i-1}v_{i-1} - T_i v_i)
```

Meaning:

```text
(EA/L_i) * (v_i - v_{i-1})                 = elastic stretch effect
(T_{i-1}v_{i-1} - T_i v_i) / L_i           = convective transport effect
```

### 3.7 Roller Velocity Dynamics

For each roller `i = UW, Nip, RW`:

```text
dv_i/dt = (R_i^2/J_i) * (T_{i+1} - T_i) - (f_i/J_i) * v_i + (R_i/J_i) * u_i
```

where:

```text
R_i = roller radius, m
J_i = roller inertia, kg*m^2
f_i = viscous friction coefficient, N*m*s/rad
u_i = motor torque, N*m
```

Because the model state uses `omega_i`, the code converts `dv_i/dt` to `domega_i/dt`:

```text
domega_i/dt = (dv_i/dt) / R_i
```

### 3.8 RK4 Integration

The fixed-step fourth-order Runge-Kutta update is:

```text
k1 = f(x_n, u, params)
k2 = f(x_n + 0.5*dt*k1, u, params)
k3 = f(x_n + 0.5*dt*k2, u, params)
k4 = f(x_n + dt*k3, u, params)

x_{n+1} = x_n + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
```

The simulator holds `u` constant during one RK4 step.

### 3.9 Multirate Control Timing

The closed-loop simulator uses:

```text
dt   = 0.001 s = 1 ms       plant RK4 integration step
Ts   = 0.010 s = 10 ms      controller update period
Tlog = configurable         data logging period
```

With default `Ts/dt = 10`, one controller command is held for 10 integration steps:

```text
step 0:      controller computes u
steps 0-9:   RK4 integrates with the same held u
step 10:     controller computes a new u
```

### 3.10 Outer Tension PI Controller

For each tension channel:

```text
e_i = T_ref_i - T_meas_i
```

The controller uses the polarity:

```text
sigma = [-1, +1, +1]
```

Signed error:

```text
e_signed_i = sigma_i * e_i
```

Integral update:

```text
I_i(t + Ts) = I_i(t) + e_signed_i * Ts
```

Velocity correction:

```text
v_corr_i = (L_i / EA) * Kp_star * (e_signed_i + I_i/TI)
```

### 3.11 Roller Speed Reference

Steady-state angular speed:

```text
omega_ss_i = v_ref / R_i
```

Controller reference:

```text
omega_ref_i = omega_ss_i + v_corr_i / R_i
```

### 3.12 Inner Velocity P Controller

Natural frequency estimate:

```text
omega_n_i = sqrt(EA * R_i^2 / (J_i * L_i))
```

Velocity gain:

```text
Kvel_i = alpha * J_i * omega_n_i
alpha = 1.4
```

Velocity feedback torque:

```text
u_fb_i = Kvel_i * (omega_ref_i - omega_i)
```

Final torque command:

```text
u_i = u_fb_i + u_ff_i
```

### 3.13 Feedforward Torque

The feedforward sign convention is isolated in `tension_load_feedforward_terms()`.

Tension load compensation:

```text
u_load_i = R_i * (T_i - T_{i+1})
```

Friction compensation:

```text
u_friction_i = f_i * omega_i
```

Feedforward:

```text
u_ff_i = u_load_i + u_friction_i
```

### 3.14 SysID Parameter Definitions

The seven estimated parameters are:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

Definitions:

```text
kt_i = R_i^2 / J_i
kf_i = f_i / J_i
EA   = axial stiffness, N
```

The input gain is derived but not estimated directly:

```text
ku_i = R_i / J_i
```

### 3.15 SysID Cost

The estimator minimizes one-step prediction residuals:

```text
residual = x_measured[k+1] - x_predicted[k+1]
```

where `x_predicted[k+1]` is computed from one model step using candidate `theta`.

The optimizer is:

```text
scipy.optimize.least_squares(method="trf")
```

### 3.16 RMSE_theta Metric

The parameter error metric is:

```text
RMSE_theta = mean_i(abs((theta_hat_i - theta_true_i) / theta_true_i))
```

Some reports multiply this by 100:

```text
RMSE_theta_percent = 100 * RMSE_theta
```

### 3.17 Sensor Noise

Sensor noise is additive Gaussian noise on measured tensions only:

```text
T_meas = T_true + n
n ~ N(0, sigma^2)
sigma = 0.003 * T_max
```

The configured random generator is:

```text
numpy.default_rng(0)
```

### 3.18 First-Order LPF

The LPF is applied after sensor noise:

```text
y[k] = y[k-1] + alpha * (x[k] - y[k-1])
alpha = 1 - exp(-2*pi*fc*dt)
fc = 100 Hz
```

## 4. Input Parameters Used

### 4.1 Default Simulation Inputs

From `configs/default.yaml` and simulator defaults:

```text
dt_ms                         = 1
controller_sample_time_ms      = 10
log_sample_time_ms             = 10
duration_s                     = 10
state order                    = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
input order                    = [u_UW, u_Nip, u_RW]
validation logging sweep       = [1, 2, 5, 10, 20, 50, 100] ms
```

### 4.2 Default Controller Inputs

From `backend/models/controller.py`:

```text
target_tension_N               = [42.0, 44.0, 43.0] by default controller config
line_speed_m_s                 = 1.0 by default controller config
Kp_star                        = 0.0525 default, often set to 100 in excitation validation config
TI_s                           = 2.0
alpha                          = 1.4
feedforward_enabled            = true
max_voltage_V                  = 24.0
```

In the multirate simulator, plant-specific target tension and speed override the generic controller defaults:

```text
target_tension_N = [T_ref_N, T_ref_N, T_ref_N]
line_speed_m_s   = v_ref_mps
```

### 4.3 Plant Input Parameters

Full plant definitions are in `configs/plants_p01_p10.yaml`.

Each plant contains:

```text
plant_id
pool_id
material
scale
regime
EA_N
v_ref_mps
T_ref_N
T_max_N
zeta_CL_min
overshoot_percent
R_m                  = [R_UW, R_Nip, R_RW]
J_kgm2               = [J_UW, J_Nip, J_RW]
f_Nms_per_rad        = [f_UW, f_Nip, f_RW]
L_m                  = [L1, L2, L3]
noise_sigma_N_0p3pct_Tmax
```

P01, the default plant, uses:

```text
plant_id              = P01
pool_id               = P001
material              = PE
scale                 = lab
regime                = O-UD
EA_N                  = 3200
v_ref_mps             = 0.5
T_ref_N               = 12.0
T_max_N               = 40.0
zeta_CL_min           = 0.151
overshoot_percent     = 45.8
R_m                   = [0.15, 0.1, 0.15]
J_kgm2                = [0.11126, 0.265196, 0.11126]
f_Nms_per_rad         = [0.707698, 1.0, 0.707698]
L_m                   = [2.0, 3.0, 3.0]
noise_sigma_N         = 0.12
```

High-level P01-P10 scalar values:

| Plant | Material | Scale | EA_N | v_ref_mps | T_ref_N | T_max_N |
|---|---|---:|---:|---:|---:|---:|
| P01 | PE | lab | 3200 | 0.5 | 12.0 | 40.0 |
| P02 | PET | lab | 9600 | 0.3 | 64.8 | 216.0 |
| P03 | PET | lab | 40000 | 0.5 | 270.0 | 900.0 |
| P04 | PET | pilot | 50000 | 3.0 | 337.5 | 1125.0 |
| P05 | Paper | prod | 144000 | 3.0 | 216.0 | 720.0 |
| P06 | Al | lab | 310500 | 0.3 | 229.5 | 765.0 |
| P07 | Al | pilot | 414000 | 2.0 | 306.0 | 1020.0 |
| P08 | Al | prod | 1242000 | 5.0 | 918.0 | 3060.0 |
| P09 | Cu | lab | 351000 | 0.1 | 360.0 | 1200.0 |
| P10 | Cu | pilot | 351000 | 3.0 | 360.0 | 1200.0 |

### 4.4 Excitation Inputs

From `configs/excitation_profiles.yaml`:

```text
Kp_star                         = 100 during excitation validation
settle_time_s                   = 2.0
episode_duration_s              = 5.0
tension_step_fraction_of_Tref    = 0.20
```

Profiles:

```text
ET1:
  type                = tension_step_single_channel
  channel             = UW
  step time           = UW at 2.0 s
  total duration      = 7.0 s

ET3:
  type                = cumulative_round_robin_tension_steps
  step times          = UW at 2.0 s, Nip at 7.0 s, RW at 12.0 s
  total duration      = 17.0 s

ET6:
  type                = up_then_down_tension_steps
  step up times       = UW at 2.0 s, Nip at 7.0 s, RW at 12.0 s
  step down times     = UW at 17.0 s, Nip at 22.0 s, RW at 27.0 s
  total duration      = 32.0 s

ET3M:
  type                = multi_operating_point_ET3
  multipliers         = [0.5, 1.0, 2.0]
  base profile        = ET3

EV1, EVR:
  enabled             = false for exact reproduction
```

### 4.5 Noise and LPF Inputs

From `configs/noise_lpf.yaml`:

```text
seed                            = 0
generator                       = numpy.default_rng
noise model                     = additive iid Gaussian per tension channel
sigma_fraction_of_Tmax          = 0.003
added_to                        = measured_tensions
generate_once_up_front          = true
LPF type                        = first_order
LPF cutoff_Hz                   = 100
LPF applied_after_noise         = true
NF_Tlog_ms                      = 5
SN_Tlog_ms                      = 20
```

Per-plant tension-noise sigma:

| Plant | sigma_N |
|---|---:|
| P01 | 0.120 |
| P02 | 0.648 |
| P03 | 2.700 |
| P04 | 3.375 |
| P05 | 2.160 |
| P06 | 2.295 |
| P07 | 3.060 |
| P08 | 9.180 |
| P09 | 3.600 |
| P10 | 3.600 |

### 4.6 Paper Target Inputs

From `configs/paper_targets.yaml`:

```text
simulation:
  dt_ms                 = 1
  Ts_ms                 = 10
  Tlog_sweep_ms         = [1, 2, 5, 10, 20, 50, 100]

logging_targets:
  NF_rule               = tau_min / Tlog >= 5
  NF_Tlog_ms            = 5
  SN_Tlog_ms            = 20
  SN_best_Tlog_ms       = [10, 20]
  SN_reference_RMSE_at_20ms_percent = 23.2

excitation_targets:
  NF_RMSE_theta_percent:
    ET1                 = 2.5
    E_Toggle            = 3.4
    ET6                 = 3.4
    ET3                 = 3.5
  SN_RMSE_theta_percent:
    E_Toggle            = 20.4
    ET6                 = 21.0
    ET3                 = 22.2
    ET3M                = 22.8
    ET1                 = 31.4
  skipped_for_reproduction = [EVR, EV1]

noise_lpf_targets:
  min_LPF_Hz            = 50
  reproduction_LPF_Hz   = 100

kp_targets:
  Kp_star_values        = [50, 100, 200]
  default_Kp_star       = 100
  high_noise_Kp_star    = 200
```

## 5. Step-by-Step Workflow

### Step 1: Install Backend Dependencies

```powershell
cd "C:\Users\user\Documents\Agent work"
pip install -r requirements.txt
```

### Step 2: Install Frontend Dependencies

```powershell
cd "C:\Users\user\Documents\Agent work\frontend"
npm ci
```

Use `npm install` only if the lockfile must be updated.

### Step 3: Run Backend Tests

```powershell
cd "C:\Users\user\Documents\Agent work"
python -m pytest
```

The latest checked result was:

```text
48 passed
```

### Step 4: Build Frontend

```powershell
cd "C:\Users\user\Documents\Agent work\frontend"
npm run build
```

### Step 5: Generate Logging Validation Outputs

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_logging_validation.py --duration-s 0.2
```

This creates:

```text
outputs/csv/logging_results.csv
outputs/figures/tlog_vs_rmse.png
outputs/validation_runs/latest/logging_validation.json
```

### Step 6: Generate Excitation Validation Outputs

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_excitation_validation.py --duration-s 0.2
```

This creates:

```text
outputs/csv/excitation_results.csv
outputs/figures/excitation_bar.png
outputs/validation_runs/latest/excitation_validation.json
```

### Step 7: Run the Backend API

If port `8000` is free:

```powershell
cd "C:\Users\user\Documents\Agent work"
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

If another backend is already using `8000`, run the fresh backend on `8001`:

```powershell
cd "C:\Users\user\Documents\Agent work"
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8001
```

Health check:

```text
http://127.0.0.1:8001/health
```

Dashboard manifest:

```text
http://127.0.0.1:8001/dashboard/outputs
```

### Step 8: Run the Frontend Dashboard

If backend is on `8000`:

```powershell
cd "C:\Users\user\Documents\Agent work\frontend"
npm run dev -- --host 127.0.0.1 --port 5173
```

If backend is on `8001`:

```powershell
cd "C:\Users\user\Documents\Agent work\frontend"
$env:VITE_API_BASE="http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

## 6. Logged CSV Columns

The multirate simulator logs:

```text
time_s
T1
T2
T3
omega_UW
omega_Nip
omega_RW
v_UW
v_Nip
v_RW
u_UW
u_Nip
u_RW
Tref1
Tref2
Tref3
plant_id
excitation_type
Tlog_ms
Kp_star
noise_enabled
```

## 7. API and Dashboard Data Flow

### Backend Data Flow

```text
configs/*.yaml
      |
      v
backend models / simulator / SysID / validation scripts
      |
      v
outputs/csv/*.csv
outputs/figures/*.png
outputs/validation_runs/latest/*.json
      |
      v
GET /dashboard/outputs
      |
      v
React dashboard
```

### Dashboard Rule

The frontend must not hard-code paper results. It reads:

```text
paper targets     -> backend loads configs/paper_targets.yaml
input configs     -> backend loads configs/*.yaml
dashboard results -> backend loads outputs/**/*.json and outputs/**/*.csv
plots             -> backend serves outputs/**/*.png through /artifacts
```

## 8. Current Dashboard Pages

| Page | Reads | Shows |
|---|---|---|
| Plant Setup | `plants_p01_p10.yaml` | plant table and config |
| Model Equations | backend equation summary and `default.yaml` | model formula and state/input definitions |
| Controller | `default.yaml`, controller config | controller formula and gains |
| SysID Setup | `default.yaml`, `paper_targets.yaml` | theta definition and SysID targets |
| Logging Validation | `outputs/.../logging_validation.json`, `logging_results.csv`, `tlog_vs_rmse.png` | logging sweep status, table, plot |
| Excitation Validation | `outputs/.../excitation_validation.json`, `excitation_results.csv`, `excitation_bar.png` | excitation status, table, plot |
| Noise/LPF Validation | expected `outputs/.../noise_lpf_validation.json` etc. | shows missing until generated |
| Drift Validation | expected `outputs/.../drift_validation.json` etc. | shows missing until generated |
| Retuning Validation | expected `outputs/.../retuning_validation.json` etc. | shows missing until generated |
| Export Report | output manifest | artifact availability table |

## 9. Output Files

Generated validation outputs:

```text
outputs/csv/logging_results.csv
outputs/csv/excitation_results.csv
outputs/figures/tlog_vs_rmse.png
outputs/figures/excitation_bar.png
outputs/validation_runs/latest/logging_validation.json
outputs/validation_runs/latest/excitation_validation.json
```

Generated paper-comparison outputs:

```text
outputs/csv/logging_paper_comparison.csv
outputs/figures/logging_paper_comparison.svg
outputs/csv/excitation_paper_comparison.csv
outputs/figures/excitation_paper_comparison.svg
outputs/csv/noise_lpf_paper_comparison.csv
outputs/csv/drift_paper_comparison.csv
outputs/figures/drift_paper_comparison.svg
outputs/csv/retuning_paper_comparison.csv
outputs/validation_runs/latest/*_paper_comparison.json
```

Dashboard display rules:

```text
Graph pages: Logging Validation, Excitation Validation, Drift Validation
Table pages: Plant Setup, Model Equations, Controller, SysID Setup, Noise/LPF Validation, Retuning Validation, Export Report
```

Older or API-generated reports may also exist under:

```text
data/processed/
reports/figures/
reports/validation_summary/
```

## 10. Tests Added

Backend tests cover:

- config loading
- R2R derivatives
- RK4 integration
- controller output and integral update
- multirate simulator timing and CSV schema
- excitation profile timing and skip behavior
- sensor noise and LPF
- SysID estimator and metrics
- validation scripts
- API routes
- dashboard output manifest

Frontend build:

```text
npm run build
```

## 11. GitHub Branches and PRs Created

The work was split into feature branches and draft PRs:

| Branch | PR | Purpose |
|---|---|---|
| `feature/multirate-simulator` | PR #1 | multirate closed-loop simulator |
| `feature/excitation-profiles` | PR #2 | paper excitation profiles |
| `feature/noise-lpf` | PR #3 | sensor noise and LPF |
| `feature/sysid-estimator` | PR #4 | seven-parameter SysID |
| `feature/validation-scripts` | PR #5 | logging and excitation validation scripts |
| `feature/dashboard-ui` | PR #6 | dashboard UI reading generated outputs |

These PRs are draft and not merged.

## 12. Assumptions and Remaining Issues

### Assumptions

- P01 is the default plant.
- `configs/plants_p01_p10.yaml` is the source of truth for plant parameters.
- `configs/paper_targets.yaml` is the source of truth for paper target values.
- `outputs/` is generated output and is ignored by git.
- The dashboard reads generated outputs rather than embedding paper results in React.

### Remaining Issues

- Noise/LPF, Drift, and Retuning dashboard pages are wired to expected output files, but their new `outputs/` artifacts still need generator scripts.
- Excitation validation currently records profile metadata and runs representative simulations; full exact physical excitation still needs simulator-level tension-reference profile wiring.
- Several PRs are stacked on earlier feature branches, so they are draft and may show not mergeable until prior backend branches are merged or rebased.
- Full paper reproduction still needs final exact-run comparison after all generated outputs exist.

## 13. Recommended Next Task

Generate complete validation output scripts for:

```text
Noise/LPF Validation
Drift Validation
Retuning Validation
```

Then rerun:

```powershell
python -m pytest
npm run build
python scripts/run_logging_validation.py --duration-s 0.2
python scripts/run_excitation_validation.py --duration-s 0.2
```

Finally refresh the dashboard at:

```text
http://127.0.0.1:5173/
```
