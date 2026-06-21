# R2R Paper Validator - Complete Project Readme

Workspace:

```text
C:\Users\user\Documents\Agent work
```

Repository:

```text
https://github.com/zainkimm-creator/Agent-codex-VAlidation
```

Current working branch:

```text
feature/dashboard-ui
```

This project reproduces and validates a roll-to-roll (R2R) web-tension control and system-identification workflow. It includes the mathematical model, RK4 integration, cascade PI controller, multirate closed-loop simulator, excitation profiles, sensor noise, low-pass filtering, SysID, validation scripts, backend API, and dashboard UI.

## 1. What Has Been Done

### 1.1 Repository and Configuration

- Added project structure under `backend/`, `configs/`, `docs/`, `scripts/`, `frontend/`, `frontend-html/`, `data/`, `reports/`, and `outputs/`.
- Added professor-resolved details and missing-detail tracking:
  - `docs/PROFESSOR_DETAILS_RESOLVED.md`
  - `docs/MISSING_DETAILS.md`
- Added configuration files:
  - `configs/default.yaml`
  - `configs/plants_p01_p10.yaml`
  - `configs/excitation_profiles.yaml`
  - `configs/noise_lpf.yaml`
  - `configs/paper_targets.yaml`

### 1.2 Mathematical Model

- Implemented R2R plant equations in `backend/models/r2r_dynamics.py`.
- Implemented supporting equation summaries in `backend/models/equations.py`.
- State vector:

```text
x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
```

- Input vector:

```text
u = [u_UW, u_Nip, u_RW]
```

- The simulator now consumes `motor_torque_Nm` values directly.
- Legacy `inputs_V` simulator compatibility was removed from the newer multirate simulator path.

### 1.3 RK4 Integrator

- Implemented fixed-step RK4 in `backend/models/rk4.py`.
- RK4 holds the input torque constant over each plant integration step.
- Added tests for finite update behavior and invalid input validation.

### 1.4 Cascade PI and Feedforward Controller

- Implemented cascade PI plus feedforward in `backend/models/controller.py`.
- Outer loop: tension PI correction.
- Inner loop: velocity P feedback plus feedforward torque.
- Feedforward includes web tension-load compensation and friction compensation.
- The feedforward sign convention is isolated in `tension_load_feedforward_terms()`.
- Added tension-consistent steady-state speed helpers:
  - `steady_state_surface_velocities()`
  - `steady_state_omega()`

### 1.5 Closed-Loop Multirate Simulator

- Implemented multirate simulator in `backend/simulation/simulator.py`.
- Uses:
  - plant RK4 step `dt = 1 ms`
  - controller update `Ts = 10 ms`
  - zero-order hold (ZOH) torque between controller updates
  - configurable `Tlog`
  - plant parameters loaded from YAML
  - logged CSV output
- Logged columns:

```text
time_s, T1, T2, T3,
omega_UW, omega_Nip, omega_RW,
v_UW, v_Nip, v_RW,
u_UW, u_Nip, u_RW,
Tref1, Tref2, Tref3,
plant_id, excitation_type, Tlog_ms, Kp_star, noise_enabled
```

### 1.6 Excitation Profiles

- Implemented paper/professor excitation profiles:
  - `ET1`: +20% UW tension-reference step at `t = 2 s`, total `7 s`
  - `ET3`: UW at `2 s`, Nip at `7 s`, RW at `12 s`, total `17 s`
  - `ET6`: up/down sequence, total `32 s`
  - `ET3M`: three ET3 operating points with line-speed multipliers `[0.5, 1.0, 2.0]`
  - `EV1` and `EVR`: skipped in exact reproduction mode
- Simulator logging now records the active tension reference columns `Tref1`, `Tref2`, and `Tref3`.

### 1.7 Noise and Low-Pass Filter

- Implemented tension-only sensor noise in `backend/noise/sensor_noise.py`.
- Implemented first-order low-pass filter in `backend/noise/filters.py`.
- Noise uses:

```text
numpy.default_rng(0)
sigma = 0.003 * T_max
```

- Noise is added only to measured tensions.
- Torque is not noised.
- LPF is applied after noise.

### 1.8 System Identification

- Implemented seven-parameter SysID estimator in `backend/sysid/estimator.py`.
- Implemented one-step prediction residuals in `backend/sysid/cost.py`.
- Implemented parameter metrics in `backend/sysid/metrics.py`.
- Estimated vector:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

- Optimizer:

```text
scipy.optimize.least_squares(method="trf")
```

- Output includes:
  - `theta_est`
  - error table
  - `RMSE_theta`
  - convergence status
  - success flag
  - final cost
  - function evaluation count

### 1.9 Validation Scripts

- Added logging validation:
  - `backend/validation/validate_logging.py`
  - `scripts/run_logging_validation.py`
- Added excitation validation:
  - `backend/validation/validate_excitation.py`
  - `scripts/run_excitation_validation.py`
- Added paper-comparison artifact generator:
  - `backend/validation/paper_comparison.py`
- Output locations:

```text
outputs/csv/
outputs/figures/
outputs/validation_runs/latest/
```

### 1.10 Backend API

- Added FastAPI backend in `backend/api/main.py`.
- Important routes:

```text
GET  /health
GET  /equations
GET  /metadata
GET  /dashboard/outputs
POST /simulate
POST /sysid
POST /validate/logging-rate
POST /validate/excitation
POST /validate/drift
POST /retune
POST /upload
```

### 1.11 Dashboard UI

- Built React dashboard in `frontend/src/App.jsx`.
- Dashboard reads generated backend outputs.
- Paper targets are not hard-coded in React; backend loads them from `configs/paper_targets.yaml`.
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
- Each page is designed to show:
  - formula
  - input config
  - paper target
  - dashboard result
  - pass/fail or review status
  - plot or table
  - CSV download when available

### 1.12 GitHub Work Completed

Feature branches and draft PRs created:

| Branch | PR | Purpose |
|---|---:|---|
| `feature/multirate-simulator` | #1 | multirate closed-loop simulator |
| `feature/excitation-profiles` | #2 | paper excitation profiles |
| `feature/noise-lpf` | #3 | sensor noise and LPF |
| `feature/sysid-estimator` | #4 | seven-parameter SysID |
| `feature/validation-scripts` | #5 | logging and excitation validation scripts |
| `feature/dashboard-ui` | #6 | dashboard UI and generated-output reading |

## 2. Main Repository Structure

```text
.
|-- AGENTS.md
|-- README.md
|-- READ.md
|-- configs/
|   |-- default.yaml
|   |-- excitation_profiles.yaml
|   |-- noise_lpf.yaml
|   |-- paper_targets.yaml
|   `-- plants_p01_p10.yaml
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
|-- docs/
|-- outputs/
`-- reports/
```

## 3. Mathematical Equations Used

### 3.1 State Vector

```text
x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
```

Definitions:

```text
T1, T2, T3                  span tensions, N
omega_UW, omega_Nip, omega_RW roller angular velocities, rad/s
```

### 3.2 Input Vector

```text
u = [u_UW, u_Nip, u_RW]
```

Definitions:

```text
u_UW, u_Nip, u_RW = motor torque commands, N*m
```

### 3.3 Output Vector

```text
y = [T1, T2, T3]
```

### 3.4 Boundary Conditions

```text
T0 = 0
T4 = 0
v0 = v_ref
```

### 3.5 Roller Surface Speed

```text
v_i = omega_i * R_i
```

where:

```text
v_i     surface speed, m/s
omega_i angular speed, rad/s
R_i     roller radius, m
```

### 3.6 Web Tension Dynamics

For each span `i = 1, 2, 3`:

```text
dT_i/dt = (EA/L_i) * (v_i - v_{i-1})
          + (1/L_i) * (T_{i-1}v_{i-1} - T_i v_i)
```

Step-by-step:

```text
1. Compute upstream and downstream surface speeds.
2. Compute elastic term: (EA/L_i) * (v_i - v_{i-1}).
3. Compute transport term: (T_{i-1}v_{i-1} - T_i v_i) / L_i.
4. Add both terms to get dT_i/dt.
```

Expanded:

```text
dT1/dt = (EA/L1)(v_UW - v0)  + (T0*v0  - T1*v_UW)  / L1
dT2/dt = (EA/L2)(v_Nip - v_UW) + (T1*v_UW - T2*v_Nip) / L2
dT3/dt = (EA/L3)(v_RW - v_Nip) + (T2*v_Nip - T3*v_RW) / L3
```

### 3.7 Roller Velocity Dynamics

For each roller `i`:

```text
dv_i/dt = (R_i^2/J_i) * (T_{i+1} - T_i)
          - (f_i/J_i) * v_i
          + (R_i/J_i) * u_i
```

Because the state uses angular velocity:

```text
domega_i/dt = (dv_i/dt) / R_i
```

Expanded:

```text
dv_UW/dt  = (R_UW^2/J_UW)(T2 - T1) - (f_UW/J_UW)v_UW + (R_UW/J_UW)u_UW
dv_Nip/dt = (R_Nip^2/J_Nip)(T3 - T2) - (f_Nip/J_Nip)v_Nip + (R_Nip/J_Nip)u_Nip
dv_RW/dt  = (R_RW^2/J_RW)(T4 - T3) - (f_RW/J_RW)v_RW + (R_RW/J_RW)u_RW
```

### 3.8 Tension-Consistent Steady Operating Speed

Uniform speed is not exactly steady when target tension is nonzero. At steady state:

```text
0 = (EA/L_i)(v_i - v_{i-1}) + (T_{i-1}v_{i-1} - T_i v_i)/L_i
```

Rearranged:

```text
v_i * (EA - T_i) = v_{i-1} * (EA - T_{i-1})
```

With `T0 = 0` and `v0 = v_ref`:

```text
v_ss,i = v_ss,i-1 * (EA - T_{i-1}) / (EA - T_i)
omega_ss,i = v_ss,i / R_i
```

This is used by the controller helper and the simulator initial condition.

### 3.9 RK4 Integrator

```text
k1 = f(x_n, u, params)
k2 = f(x_n + 0.5*dt*k1, u, params)
k3 = f(x_n + 0.5*dt*k2, u, params)
k4 = f(x_n + dt*k3, u, params)

x_{n+1} = x_n + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
```

### 3.10 Multirate Simulation Timing

```text
dt   = 0.001 s = 1 ms       RK4 plant step
Ts   = 0.010 s = 10 ms      controller update period
Tlog = configurable         logging period
```

With `Ts/dt = 10`:

```text
step 0     controller computes torque u
steps 0-9  plant integrates with held u
step 10    controller computes the next torque u
```

### 3.11 Outer Tension PI Controller

Tension error:

```text
e_i = T_ref_i - T_meas_i
```

Professor-provided polarity used in code:

```text
sigma = [-1, +1, +1]
```

Signed error:

```text
e_signed_i = sigma_i * e_i
```

Integral:

```text
I_i(t + Ts) = I_i(t) + e_signed_i * Ts
```

Velocity correction:

```text
v_corr_i = (L_i / EA) * Kp_star * (e_signed_i + I_i/TI)
```

The controller keeps that paper polarity separate from the web-positive plant state by using:

```text
rho = [-1, +1, +1]
```

Speed reference:

```text
omega_ref_i = omega_ss_i + rho_i * v_corr_i / R_i
```

### 3.12 Inner Velocity Feedback

Natural frequency estimate:

```text
omega_n_i = sqrt(EA * R_i^2 / (J_i * L_i))
```

Velocity gain:

```text
Kvel_i = alpha * J_i * omega_n_i
alpha = 1.4
```

Torque feedback:

```text
u_fb_i = Kvel_i * (omega_ref_i - omega_i)
```

Controller output:

```text
u_i = u_fb_i + u_ff_i
```

### 3.13 Feedforward Torque

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

### 3.14 SysID Parameters

Estimated vector:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

Definitions:

```text
kt_i = R_i^2 / J_i
kf_i = f_i / J_i
EA   = axial web stiffness, N
```

### 3.15 SysID One-Step Cost

The residual compares observed row-to-row finite differences with model-predicted finite differences.

Roller residual model:

```text
dv_i/dt = kt_i * (T_{i+1} - T_i + u_i/R_i) - kf_i * v_i
```

Tension residual model:

```text
dT_i/dt = EA/L_i * (v_i - v_{i-1})
          + (T_{i-1}v_{i-1} - T_i v_i)/L_i
```

Cost:

```text
J(theta) = 0.5 * sum(residual_i^2)
```

### 3.16 RMSE_theta

Implementation metric:

```text
RMSE_theta = sqrt(mean(((theta_est_i - theta_true_i) / theta_true_i)^2))
```

Percent form:

```text
RMSE_theta_percent = 100 * RMSE_theta
```

### 3.17 Sensor Noise

```text
T_meas = T_true + n
n ~ N(0, sigma^2)
sigma = 0.003 * T_max
```

Noise is generated with:

```text
numpy.default_rng(0)
```

### 3.18 First-Order Low-Pass Filter

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
logging sweep                  = [1, 2, 5, 10, 20, 50, 100] ms
```

### 4.2 Controller Inputs

From `backend/models/controller.py`:

```text
target_tension_N               = [42.0, 44.0, 43.0] default controller config
line_speed_m_s                 = 1.0 default controller config
Kp_star                        = 0.0525 default controller config
TI_s                           = 2.0
alpha                          = 1.4
feedforward_enabled            = true
max_voltage_V                  = 24.0 feedback clamp scale field
```

In the multirate simulator, plant-specific values override generic controller defaults:

```text
target_tension_N = [T_ref_N, T_ref_N, T_ref_N]
line_speed_m_s   = v_ref_mps
Kp_star          = simulation config Kp_star
```

Excitation validation uses:

```text
Kp_star = 100.0
Tlog    = 5 ms
```

### 4.3 P01 Plant Inputs

Default plant `P01` from `configs/plants_p01_p10.yaml`:

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
noise_sigma_N         = 0.120
```

### 4.4 P01-P10 Scalar Plant Table

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

### 4.5 Excitation Inputs

From `configs/excitation_profiles.yaml`:

```text
Kp_star                         = 100
settle_time_s                   = 2.0
episode_duration_s              = 5.0
tension_step_fraction_of_Tref    = 0.20
```

Profiles:

```text
ET1:
  UW step at 2.0 s
  total duration 7.0 s

ET3:
  UW step at 2.0 s
  Nip step at 7.0 s
  RW step at 12.0 s
  total duration 17.0 s

ET6:
  UW up at 2.0 s, down at 17.0 s
  Nip up at 7.0 s, down at 22.0 s
  RW up at 12.0 s, down at 27.0 s
  total duration 32.0 s

ET3M:
  ET3 at speed multipliers [0.5, 1.0, 2.0]

EV1 and EVR:
  skipped in exact reproduction mode
```

### 4.6 Noise and LPF Inputs

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

### 4.7 Paper Targets

From `configs/paper_targets.yaml`:

```text
simulation dt_ms                 = 1
simulation Ts_ms                 = 10
Tlog sweep                       = [1, 2, 5, 10, 20, 50, 100] ms
NF logging rule                  = tau_min / Tlog >= 5
SN best Tlog                     = [10, 20] ms
SN reference RMSE at 20 ms       = 23.2 percent
LPF reproduction cutoff          = 100 Hz
minimum LPF cutoff target        = 50 Hz
Kp_star values                   = [50, 100, 200]
default Kp_star                  = 100
high-noise Kp_star               = 200
```

Excitation targets:

```text
Noise-free:
  ET1       = 2.5 percent
  E_Toggle  = 3.4 percent
  ET6       = 3.4 percent
  ET3       = 3.5 percent

Sensor-noise:
  E_Toggle  = 20.4 percent
  ET6       = 21.0 percent
  ET3       = 22.2 percent
  ET3M      = 22.8 percent
  ET1       = 31.4 percent
```

Drift targets:

```text
EA saturation RMSE range                  = [15, 18] percent
J_UW -30 percent and RW +50 percent       = 26.8 percent
J_UW -50 percent and RW +100 percent      = 39.3 percent
f drift RMSE range                        = [20, 21] percent
```

Retuning targets:

```text
CS-BO(30)     real_evals = 30, median_cost = 0.407
WS-BO(30)     real_evals = 30, median_cost = 0.408
HGS-only      real_evals = 0,  median_cost = 0.403
HGS+BO(5)     real_evals = 5,  median_cost = 0.342
HGS+BO(10)    real_evals = 10, median_cost = 0.337
```

## 5. Step-by-Step Run Workflow

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

### Step 3: Run Backend Tests

```powershell
cd "C:\Users\user\Documents\Agent work"
python -m pytest
```

### Step 4: Build Frontend

```powershell
cd "C:\Users\user\Documents\Agent work\frontend"
npm run build
```

### Step 5: Run Logging Validation

Short smoke run:

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_logging_validation.py --duration-s 0.2
```

Outputs:

```text
outputs/csv/logging_results.csv
outputs/figures/tlog_vs_rmse.png
outputs/validation_runs/latest/logging_validation.json
```

### Step 6: Run Excitation Validation

Full profile timing:

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_excitation_validation.py
```

Outputs:

```text
outputs/csv/excitation_results.csv
outputs/figures/excitation_bar.png
outputs/validation_runs/latest/excitation_validation.json
```

### Step 7: Refresh Paper-Comparison Artifacts

These are generated automatically by `GET /dashboard/outputs`. They can also be refreshed directly:

```powershell
cd "C:\Users\user\Documents\Agent work"
python -c "from pathlib import Path; from backend.validation.paper_comparison import ensure_paper_comparison_outputs; ensure_paper_comparison_outputs(Path('outputs'))"
```

Generated comparison files:

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

### Step 8: Run Backend API

```powershell
cd "C:\Users\user\Documents\Agent work"
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

If port `8000` is busy, use another port:

```powershell
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8001
```

Health check:

```text
http://127.0.0.1:8000/health
```

Dashboard output manifest:

```text
http://127.0.0.1:8000/dashboard/outputs
```

### Step 9: Run Frontend Dashboard

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

## 6. Current Validation Status

Latest full excitation validation after the tension-consistent initial-state, controller sign-map, and SN noise/LPF update:

```text
ET1  dashboard NF RMSE_theta_percent = 1.3146, paper NF target = 2.5, status = pass
ET1  dashboard SN RMSE_theta_percent = 9.0127, paper SN target = 31.4, status = review
ET3  dashboard NF RMSE_theta_percent = 1.3587, paper NF target = 3.5, status = pass
ET3  dashboard SN RMSE_theta_percent = 10.4379, paper SN target = 22.2, status = review
ET6  dashboard NF RMSE_theta_percent = 1.3596, paper NF target = 3.4, status = pass
ET6  dashboard SN RMSE_theta_percent = 10.4309, paper SN target = 21.0, status = review
ET3M dashboard SN RMSE_theta_percent = 10.4088, paper SN target = 22.8, status = review
EV1  skipped by exact reproduction rule
EVR  skipped by exact reproduction rule
```

Latest drift validation:

```text
EA drift dashboard RMSE_theta_percent = 4.5335, paper target midpoint = 16.5, status = pass
f drift dashboard RMSE_theta_percent = 5.6117, paper target midpoint = 20.5, status = review
J drift dashboard RMSE_theta_percent = 182.3123, paper target = 39.3, status = review
Dominant dashboard degradation source = J
```

Latest retuning validation:

```text
CS-BO(30) dashboard cost = 37.8384, paper median cost = 0.407, status = review
HGS-only dashboard cost = 37.8384, paper median cost = 0.403, status = review
HGS+BO(5) dashboard cost = 37.8384, paper median cost = 0.342, status = review
HGS+BO(10) dashboard cost = 37.8384, paper median cost = 0.337, status = review
Evaluation-budget trend = HGS+BO(5) uses fewer real evaluations than CS-BO(30)
```

Important sign-convention resolution:

```text
The professor-required controller polarity sigma = [-1, +1, +1] is implemented.
The code also uses rho = [-1, +1, +1] to map the UW actuator correction into the plant's positive web-surface direction.
With that isolated sign map, ET1, ET3, ET6, and ET3M complete without numerical instability.
```

Current comparison rule:

```text
The dashboard excitation comparison now includes NF and SN rows.
NF dashboard rows compare only to paper NF targets.
SN dashboard rows compare only to paper SN targets.
ET3M is now generated as three ET3 operating points with line-speed multipliers [0.5, 1.0, 2.0].
```

## 7. Dashboard Data Flow

```text
configs/*.yaml
      |
      v
backend model / simulation / SysID / validation scripts
      |
      v
outputs/csv/*.csv
outputs/figures/*.png or *.svg
outputs/validation_runs/latest/*.json
      |
      v
GET /dashboard/outputs
      |
      v
React dashboard
```

Dashboard rule:

```text
Do not hard-code paper results in React.
Read paper targets from configs/paper_targets.yaml through the backend.
Read dashboard results from generated outputs.
```

## 8. Tests

Backend tests cover:

- config loading
- R2R dynamics
- RK4 integration
- controller output and integral update
- multirate simulator timing and CSV schema
- excitation profile timing and skip behavior
- sensor noise and LPF
- SysID estimator and metrics
- validation scripts
- API routes
- dashboard output manifest

Useful commands:

```powershell
python -m pytest
python -m pytest backend/tests/test_controller.py backend/tests/test_simulator.py
npm run build
```

Latest verification in this workspace:

```text
python -m pytest  -> 49 passed
npm run build     -> passed
```

## 9. Assumptions

- P01 is the default plant for validation runs.
- `configs/plants_p01_p10.yaml` is the plant source of truth.
- `configs/paper_targets.yaml` is the paper-target source of truth.
- `outputs/` contains generated artifacts and is not treated as source code.
- Exact reproduction skips `EV1` and `EVR`.
- The current code keeps the professor-provided controller polarity and isolates the UW actuator-to-web sign map.

## 10. Remaining Issues

- SN excitation rows are now generated, but their RMSE_theta values are lower than the paper SN targets, so they are marked review rather than pass.
- Noise/LPF dashboard page has a config comparison table, but a full generated output script still needs to be completed.
- Drift now has `outputs/csv/drift_results.csv` and `outputs/validation_runs/latest/drift_validation.json`, but the f/J numeric comparison remains review.
- Retuning now has `outputs/csv/retuning_results.csv` and `outputs/validation_runs/latest/retuning_validation.json`, but the cost-scale numeric comparison remains review.
- Some feature PRs are stacked on earlier branches and may show as draft or not mergeable until the previous branches are merged or rebased.
- The dashboard comparison graphs are available for Logging, Excitation, and Drift; table-first comparison is used where graphing is not yet useful.

## 11. Next Recommended Task

Calibrate the sensor-noise excitation layer before treating the excitation comparison as final:

```text
1. Confirm whether the paper SN targets include additional unmodeled noise, repeated seeds, or physical-log variance.
2. Recheck the SysID aggregation for ET3M against the paper multi-condition cost.
3. Regenerate paper-comparison CSV/SVG artifacts after calibration.
4. Verify the dashboard graph/table pages against the refreshed outputs.
5. Rerun python -m pytest and npm run build.
```
