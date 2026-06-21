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

Dashboard PR:

```text
https://github.com/zainkimm-creator/Agent-codex-VAlidation/pull/6
```

This repository validates a roll-to-roll (R2R) web tension control and system-identification workflow. It now includes plant configuration, governing equations, RK4 integration, cascade PI plus feedforward control, closed-loop multirate simulation, excitation profiles, sensor noise, low-pass filtering, seven-parameter SysID, validation scripts, paper-target comparisons, a FastAPI backend, and a React dashboard.

## 1. What Has Been Done

### 1.1 Repository Setup

Added and organized the project under:

```text
backend/
configs/
data/
docs/
frontend/
frontend-html/
outputs/
reports/
scripts/
```

Important documentation and config files:

```text
AGENTS.md
README.md
READ.md
docs/PROFESSOR_DETAILS_RESOLVED.md
docs/MISSING_DETAILS.md
configs/default.yaml
configs/plants_p01_p10.yaml
configs/excitation_profiles.yaml
configs/noise_lpf.yaml
configs/paper_targets.yaml
```

### 1.2 Mathematical Model

Implemented the focused R2R plant model in:

```text
backend/models/r2r_dynamics.py
backend/models/equations.py
```

The main implemented model uses:

```text
x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
u = [u_UW, u_Nip, u_RW]
y = [T1, T2, T3]
```

In the focused model and multirate simulator, `u_UW`, `u_Nip`, and `u_RW` are motor torques in `N*m`.

### 1.3 RK4 Integrator

Implemented fixed-step RK4 in:

```text
backend/models/rk4.py
```

The integrator advances the six-state model and holds the three motor torques constant during each plant step.

### 1.4 Controller

Implemented the cascade PI plus feedforward controller in:

```text
backend/models/controller.py
```

Controller pieces implemented:

- outer tension PI loop
- professor polarity `sigma = [-1, +1, +1]`
- isolated web-speed sign map `rho = [-1, +1, +1]`
- tension-consistent steady-state roller speeds
- inner velocity proportional loop
- velocity gain formula using `alpha = 1.4`
- measured-tension feedforward
- friction feedforward
- output as `motor_torque_Nm`

### 1.5 Simulation

Two simulation surfaces exist:

```text
backend/simulation/simulator.py
backend/models/simulation.py
```

`backend/simulation/simulator.py` is the newer paper-validation simulator. It uses:

```text
dt   = 1 ms
Ts   = 10 ms
Tlog = configurable
ZOH  = held torque between controller updates
```

It loads plant values from `configs/plants_p01_p10.yaml`, uses `r2r_dynamics.r2r_derivatives`, advances with `rk4.rk4_step`, and saves CSV output.

`backend/models/simulation.py` is the older API simulation path. It has also been wired to the same focused dynamics and RK4 step, but some older API field names remain for compatibility in request payloads.

### 1.6 Excitation Profiles

Implemented professor-provided excitation definitions in:

```text
backend/excitation/profiles.py
backend/excitation/generators.py
```

Implemented profiles:

```text
ET1  = +20% UW step at t = 2 s, total 7 s
ET3  = UW step at 2 s, Nip step at 7 s, RW step at 12 s, total 17 s
ET6  = up/down sequence, total 32 s
ET3M = three ET3 runs at v_ref multipliers [0.5, 1.0, 2.0]
EV1  = skipped in exact reproduction mode
EVR  = skipped in exact reproduction mode
```

### 1.7 Noise and LPF

Implemented in:

```text
backend/noise/sensor_noise.py
backend/noise/filters.py
```

Noise and filter rules:

```text
noise target       = measured tensions only
noise type         = additive iid Gaussian
seed               = numpy.default_rng(0)
sigma              = 0.003 * T_max
torque noise       = none
LPF type           = first order
LPF cutoff         = 100 Hz
LPF order          = after noise
NF Tlog            = 5 ms
SN Tlog            = 20 ms
```

### 1.8 SysID

Implemented seven-parameter system identification in:

```text
backend/sysid/estimator.py
backend/sysid/cost.py
backend/sysid/metrics.py
```

Estimated parameter vector:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

Optimizer:

```text
scipy.optimize.least_squares(method="trf")
```

SysID output includes:

```text
theta_est
error_table
RMSE_theta
convergence_status
success
cost
nfev
summary_path
```

### 1.9 Validation Scripts and Outputs

Implemented dashboard-facing validation runners:

```text
backend/validation/validate_logging.py
backend/validation/validate_excitation.py
backend/validation/validate_noise_lpf.py
backend/validation/validate_drift.py
backend/validation/validate_retuning.py
backend/validation/paper_comparison.py
```

Script entry points:

```text
scripts/run_logging_validation.py
scripts/run_excitation_validation.py
scripts/run_noise_lpf_validation.py
scripts/run_validation_drift.py
scripts/run_retuning.py
```

Generated output locations:

```text
outputs/csv/
outputs/figures/
outputs/validation_runs/latest/
```

Current comparison artifacts include:

```text
outputs/csv/logging_paper_comparison.csv
outputs/figures/logging_paper_comparison.svg
outputs/csv/excitation_paper_comparison.csv
outputs/figures/excitation_paper_comparison.svg
outputs/csv/noise_lpf_results.csv
outputs/csv/noise_lpf_paper_comparison.csv
outputs/validation_runs/latest/noise_lpf_validation.json
outputs/csv/drift_paper_comparison.csv
outputs/figures/drift_paper_comparison.svg
outputs/csv/retuning_paper_comparison.csv
outputs/validation_runs/latest/*_paper_comparison.json
```

### 1.10 Backend API

Implemented FastAPI backend in:

```text
backend/api/main.py
```

Main routes:

```text
GET  /
GET  /health
GET  /equations
GET  /plants
GET  /metadata
GET  /validation/parts
GET  /dashboard/outputs
POST /simulate
POST /sysid
POST /validate/part/1
POST /validate/logging-rate
POST /validate/excitation
POST /validate/drift
POST /retune
POST /upload
```

`GET /dashboard/outputs` is the key dashboard manifest endpoint. It reads configs, refreshes comparison artifacts, and returns the pages, result summaries, file links, and table rows consumed by React.

### 1.11 Dashboard UI

Implemented React dashboard in:

```text
frontend/src/App.jsx
frontend/src/api.js
frontend/src/styles.css
frontend/components/
frontend/public/
```

Dashboard pages:

```text
Plant Setup
Model Equations
Controller
SysID Setup
Logging Validation
Excitation Validation
Noise/LPF Validation
Drift Validation
Retuning Validation
Export Report
```

Dashboard rule:

```text
Do not hard-code paper results in frontend.
Read config, paper targets, CSV, JSON, and plot artifacts from backend outputs.
```

### 1.12 GitHub Branches and PRs Created

```text
feature/multirate-simulator   PR #1
feature/excitation-profiles   PR #2
feature/noise-lpf             PR #3
feature/sysid-estimator       PR #4
feature/validation-scripts    PR #5
feature/dashboard-ui          PR #6
```

## 2. Repository Map

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

## 3. End-to-End Data Flow

```text
1. YAML configs define plant, excitation, noise, LPF, and paper targets.
2. Simulator loads one plant, builds controller parameters, and sets initial state.
3. Controller updates every Ts = 10 ms.
4. Motor torque is held by zero-order hold between controller updates.
5. RK4 integrates plant dynamics every dt = 1 ms.
6. Simulation logs rows every Tlog.
7. Optional sensor noise is added to measured tensions only.
8. LPF is applied after tension noise.
9. SysID estimates theta from logged rows.
10. Validation scripts compare dashboard outputs with paper targets.
11. Backend exposes outputs through /dashboard/outputs.
12. React dashboard renders tables, plots, pass/fail, and download links.
```

## 4. Mathematical Equations Used

### 4.1 State Vector

```text
x = [T1, T2, T3, omega_UW, omega_Nip, omega_RW]
```

Units:

```text
T1, T2, T3                  N
omega_UW, omega_Nip, omega_RW rad/s
```

### 4.2 Input Vector

```text
u = [u_UW, u_Nip, u_RW]
```

In the focused model and paper-validation simulator:

```text
u_UW, u_Nip, u_RW = motor torque commands, N*m
```

### 4.3 Output Vector

```text
y = [T1, T2, T3]
```

### 4.4 Boundary Conditions

```text
T0 = 0
T4 = 0
v0 = v_ref
```

### 4.5 Roller Surface Velocity

```text
v_i = omega_i * R_i
```

where:

```text
v_i     roller surface velocity, m/s
omega_i roller angular velocity, rad/s
R_i     roller radius, m
```

Step by step:

```text
1. Read omega_i from state.
2. Read R_i from the active plant.
3. Multiply omega_i by R_i.
4. Use v_i in tension dynamics, roller dynamics, logging, and SysID.
```

### 4.6 Web Tension Dynamics

For span `i = 1, 2, 3`:

```text
dT_i/dt = (EA/L_i) * (v_i - v_{i-1})
          + (T_{i-1}v_{i-1} - T_i v_i) / L_i
```

Step by step:

```text
1. Read current span tension T_i.
2. Read upstream tension T_{i-1}.
3. Read downstream surface velocity v_i.
4. Read upstream surface velocity v_{i-1}.
5. Compute elastic stretch term: (EA/L_i) * (v_i - v_{i-1}).
6. Compute transport term: (T_{i-1}v_{i-1} - T_i v_i) / L_i.
7. Add both terms to produce dT_i/dt.
```

Expanded:

```text
dT1/dt = (EA/L1)(v_UW - v0)      + (T0*v0      - T1*v_UW)  / L1
dT2/dt = (EA/L2)(v_Nip - v_UW)   + (T1*v_UW    - T2*v_Nip) / L2
dT3/dt = (EA/L3)(v_RW - v_Nip)   + (T2*v_Nip   - T3*v_RW)  / L3
```

### 4.7 Roller Velocity Dynamics

For roller `i = UW, Nip, RW`:

```text
dv_i/dt = (R_i^2/J_i) * (T_{i+1} - T_i)
          - (f_i/J_i) * v_i
          + (R_i/J_i) * u_i
```

Because the state uses angular velocity:

```text
domega_i/dt = (dv_i/dt) / R_i
```

Step by step:

```text
1. Compute tension difference T_{i+1} - T_i.
2. Compute web acceleration term: (R_i^2/J_i)(T_{i+1} - T_i).
3. Compute viscous damping term: -(f_i/J_i)v_i.
4. Compute motor torque term: (R_i/J_i)u_i.
5. Add the three terms to get dv_i/dt.
6. Divide by R_i to get domega_i/dt.
```

Expanded:

```text
dv_UW/dt  = (R_UW^2/J_UW)(T2 - T1) - (f_UW/J_UW)v_UW + (R_UW/J_UW)u_UW
dv_Nip/dt = (R_Nip^2/J_Nip)(T3 - T2) - (f_Nip/J_Nip)v_Nip + (R_Nip/J_Nip)u_Nip
dv_RW/dt  = (R_RW^2/J_RW)(T4 - T3) - (f_RW/J_RW)v_RW + (R_RW/J_RW)u_RW
```

with:

```text
T4 = 0
```

### 4.8 Complete State Derivative

```text
dx/dt = [
  dT1/dt,
  dT2/dt,
  dT3/dt,
  domega_UW/dt,
  domega_Nip/dt,
  domega_RW/dt
]
```

### 4.9 Tension-Consistent Steady Speed

Uniform speed is not exactly steady when target tension is nonzero. At steady state:

```text
0 = (EA/L_i)(v_i - v_{i-1})
    + (T_{i-1}v_{i-1} - T_i v_i)/L_i
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

Used by:

```text
backend/models/controller.py
backend/simulation/simulator.py
```

### 4.10 RK4 Integrator

```text
k1 = f(x_n, u, params)
k2 = f(x_n + 0.5*dt*k1, u, params)
k3 = f(x_n + 0.5*dt*k2, u, params)
k4 = f(x_n + dt*k3, u, params)

x_{n+1} = x_n + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
```

Step by step:

```text
1. Evaluate derivative at the current state.
2. Evaluate derivative at the midpoint using k1.
3. Evaluate derivative at the midpoint using k2.
4. Evaluate derivative at the endpoint using k3.
5. Combine all slopes with RK4 weights.
6. Return the next six-state vector.
```

### 4.11 Multirate Simulation Timing

```text
dt   = 0.001 s = 1 ms
Ts   = 0.010 s = 10 ms
Tlog = configurable
```

For the paper-validation simulator:

```text
Ts/dt = 10 integration steps per controller update
```

Step by step:

```text
1. At a controller sample, compute motor_torque_Nm.
2. Hold the torque constant with zero-order hold.
3. Run 10 RK4 plant steps at 1 ms.
4. Log rows when the current step matches Tlog.
5. Repeat until duration_s is reached.
```

### 4.12 Outer Tension PI Controller

Tension error:

```text
e_i = T_ref_i - T_meas_i
```

Professor polarity:

```text
sigma = [-1, +1, +1]
```

Signed error:

```text
e_signed_i = sigma_i * e_i
```

Integral update:

```text
I_i[k+1] = I_i[k] + e_signed_i * Ts
```

Velocity correction:

```text
v_corr_i = (L_i / EA) * Kp_star * (e_signed_i + I_i/TI)
```

Web-speed reference polarity:

```text
rho = [-1, +1, +1]
```

Speed reference:

```text
omega_ref_i = omega_ss_i + rho_i * v_corr_i / R_i
```

### 4.13 Inner Velocity Loop

Natural frequency estimate:

```text
omega_n_i = sqrt(EA * R_i^2 / (J_i * L_i))
```

Velocity gain:

```text
Kvel_i = alpha * J_i * omega_n_i
alpha = 1.4
```

Feedback torque:

```text
u_fb_i = Kvel_i * (omega_ref_i - omega_i)
```

### 4.14 Feedforward Torque

Tension-load feedforward:

```text
u_load_i = R_i * (T_i - T_{i+1})
```

Friction feedforward:

```text
u_friction_i = f_i * omega_i
```

Total feedforward:

```text
u_ff_i = u_load_i + u_friction_i
```

Total controller output:

```text
u_i = u_fb_i + u_ff_i
```

### 4.15 SysID Parameters

Estimated vector:

```text
theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]
```

Parameter definitions:

```text
kt_i = R_i^2 / J_i
kf_i = f_i / J_i
EA   = axial web stiffness, N
```

### 4.16 SysID One-Step Prediction Residuals

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

Step by step:

```text
1. Read consecutive logged rows.
2. Compute finite-difference dT_i/dt and dv_i/dt.
3. Predict those derivatives from theta and the same plant equations.
4. Residual = observed derivative - predicted derivative.
5. Stack all residuals.
6. Use scipy least_squares with method="trf".
```

### 4.17 RMSE_theta

Implementation metric:

```text
relative_error_i = (theta_est_i - theta_true_i) / theta_true_i
RMSE_theta = sqrt(mean(relative_error_i^2))
RMSE_theta_percent = 100 * RMSE_theta
```

Note:

```text
configs/paper_targets.yaml still stores the professor/paper text as a mean absolute relative formula.
The implemented metric in backend/sysid/metrics.py is root-mean-square relative error.
```

### 4.18 Sensor Noise

```text
T_meas = T_true + n
n ~ Normal(0, sigma^2)
sigma = 0.003 * T_max
```

Noise generation:

```text
numpy.default_rng(0)
```

Noise is added only to measured tension channels:

```text
T1, T2, T3
```

Noise is not added to:

```text
u_UW, u_Nip, u_RW
```

### 4.19 First-Order Low-Pass Filter

Matched-pole form:

```text
alpha = 1 - exp(-2*pi*fc*dt)
y[k] = y[k-1] + alpha * (x[k] - y[k-1])
```

Current settings:

```text
fc = 100 Hz
dt = sample_time_s
```

### 4.20 Retuning Cost Form

Dashboard retuning uses a cost based on:

```text
tension RMSE
overshoot
t90 or rise-time behavior
control effort
```

Paper targets compare:

```text
CS-BO(30)
HGS-only
HGS+BO(5)
HGS+BO(10)
```

## 5. Input Parameters Used

### 5.1 Default Timing Inputs

From `configs/default.yaml` and simulator defaults:

```text
simulation dt_ms                    = 1
controller_sample_time_ms           = 10
log_sample_time_ms                  = 10
default duration_s                  = 10
paper-validation default duration_s = 0.2 in smoke validation
logging sweep                       = [1, 2, 5, 10, 20, 50, 100] ms
```

### 5.2 Controller Inputs

Controller defaults in `backend/models/controller.py`:

```text
target_tension_N        = [42.0, 44.0, 43.0]
line_speed_m_s          = 1.0
Kp_star                 = 0.0525
TI_s                    = 2.0
alpha                   = 1.4
feedforward_enabled     = true
max_voltage_V           = 24.0
```

Legacy config field still present in `configs/default.yaml`:

```text
Kp_star_m_s_per_N = 0.00001
```

Paper excitation validation overrides:

```text
Kp_star = 100.0
Tlog NF = 5 ms
Tlog SN = 20 ms
```

### 5.3 Plant Parameter Meaning

Plant values come from `configs/plants_p01_p10.yaml`.

```text
EA_N             axial web stiffness, N
v_ref_mps        feeder/reference line speed, m/s
T_ref_N          nominal span tension reference, N
T_max_N          load-cell full scale, N
R_m              roller radii [UW, Nip, RW], m
J_kgm2           roller inertias [UW, Nip, RW], kg*m^2
f_Nms_per_rad    viscous friction [UW, Nip, RW], N*m*s/rad
L_m              span lengths [span1, span2, span3], m
```

### 5.4 Plant Inputs P01-P10

```text
P01: EA=3200,    v_ref=0.5, T_ref=12.0,  T_max=40.0,   R=[0.15,0.1,0.15], J=[0.11126,0.265196,0.11126], f=[0.707698,1.0,0.707698], L=[2.0,3.0,3.0], sigma=0.120
P02: EA=9600,    v_ref=0.3, T_ref=64.8,  T_max=216.0,  R=[0.2,0.1,0.2],   J=[0.359562,0.193405,0.359562], f=[3.0,0.163318,3.0],      L=[3.0,2.0,2.0], sigma=0.648
P03: EA=40000,   v_ref=0.5, T_ref=270.0, T_max=900.0,  R=[0.2,0.1,0.2],   J=[0.445464,0.097544,0.445464], f=[1.685698,0.278819,1.685698], L=[2.0,2.0,3.0], sigma=2.700
P04: EA=50000,   v_ref=3.0, T_ref=337.5, T_max=1125.0, R=[0.25,0.1,0.25], J=[2.382481,0.403738,2.382481], f=[10.0,2.998943,10.0],    L=[3.0,10.0,5.0], sigma=3.375
P05: EA=144000,  v_ref=3.0, T_ref=216.0, T_max=720.0,  R=[0.75,0.2,0.75], J=[90.373903,8.416216,90.373903], f=[3.497247,0.319941,3.497247], L=[5.0,20.0,8.0], sigma=2.160
P06: EA=310500,  v_ref=0.3, T_ref=229.5, T_max=765.0,  R=[0.2,0.1,0.2],   J=[0.494378,0.180335,0.494378], f=[3.0,1.0,3.0],          L=[2.0,3.0,3.0], sigma=2.295
P07: EA=414000,  v_ref=2.0, T_ref=306.0, T_max=1020.0, R=[0.3,0.1,0.3],   J=[5.73936,0.221068,5.73936],   f=[1.052208,0.125884,1.052208], L=[5.0,8.0,5.0], sigma=3.060
P08: EA=1242000, v_ref=5.0, T_ref=918.0, T_max=3060.0, R=[0.75,0.2,0.75], J=[937.741061,12.177233,937.741061], f=[1.303144,0.225839,1.303144], L=[8.0,30.0,10.0], sigma=9.180
P09: EA=351000,  v_ref=0.1, T_ref=360.0, T_max=1200.0, R=[0.15,0.1,0.15], J=[0.609345,0.272279,0.609345], f=[3.0,0.387705,3.0],      L=[2.0,2.0,2.0], sigma=3.600
P10: EA=351000,  v_ref=3.0, T_ref=360.0, T_max=1200.0, R=[0.3,0.1,0.3],   J=[44.902091,0.472429,44.902091], f=[10.0,3.0,10.0],       L=[5.0,5.0,5.0], sigma=3.600
```

### 5.5 Excitation Inputs

From `configs/excitation_profiles.yaml`:

```text
Kp_star                      = 100
settle_time_s                = 2.0
episode_duration_s           = 5.0
tension_step_fraction_of_Tref = 0.20
```

Excitation timing:

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
  UW high from 2.0 s to 17.0 s
  Nip high from 7.0 s to 22.0 s
  RW high from 12.0 s to 27.0 s
  total duration 32.0 s

ET3M:
  ET3 at line-speed multipliers [0.5, 1.0, 2.0]

EV1 and EVR:
  skipped in exact reproduction mode
```

### 5.6 Noise and LPF Inputs

From `configs/noise_lpf.yaml`:

```text
seed                         = 0
generator                    = numpy.default_rng
noise model                  = additive iid Gaussian per tension channel
sigma_fraction_of_Tmax       = 0.003
noise target                 = measured_tensions
generate_once_up_front       = true
LPF type                     = first_order
LPF cutoff_Hz                = 100
LPF applied_after_noise      = true
NF_Tlog_ms                   = 5
SN_Tlog_ms                   = 20
```

### 5.7 Paper Targets

From `configs/paper_targets.yaml`:

```text
simulation dt_ms                         = 1
simulation Ts_ms                         = 10
Tlog sweep                               = [1, 2, 5, 10, 20, 50, 100] ms
SN best Tlog                             = [10, 20] ms
SN reference RMSE_theta at 20 ms          = 23.2 percent
LPF reproduction cutoff                  = 100 Hz
minimum LPF cutoff target                = 50 Hz
Kp_star values                           = [50, 100, 200]
default Kp_star                          = 100
high-noise Kp_star                       = 200
```

Excitation paper targets:

```text
NF ET1      = 2.5 percent
NF E_Toggle = 3.4 percent
NF ET6      = 3.4 percent
NF ET3      = 3.5 percent

SN E_Toggle = 20.4 percent
SN ET6      = 21.0 percent
SN ET3      = 22.2 percent
SN ET3M     = 22.8 percent
SN ET1      = 31.4 percent
```

Drift paper targets:

```text
EA saturation RMSE range             = [15, 18] percent
J UW -30 percent and RW +50 percent  = 26.8 percent
J UW -50 percent and RW +100 percent = 39.3 percent
f drift RMSE range                   = [20, 21] percent
```

Retuning paper targets:

```text
CS-BO(30)  real_evals = 30, median_cost = 0.407
WS-BO(30)  real_evals = 30, median_cost = 0.408
HGS-only   real_evals = 0,  median_cost = 0.403
HGS+BO(5)  real_evals = 5,  median_cost = 0.342
HGS+BO(10) real_evals = 10, median_cost = 0.337
```

## 6. Step-by-Step Run Workflow

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

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_logging_validation.py
```

Outputs:

```text
outputs/csv/logging_results.csv
outputs/figures/tlog_vs_rmse.png
outputs/validation_runs/latest/logging_validation.json
```

### Step 6: Run Excitation Validation

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

### Step 7: Run Noise/LPF Validation

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_noise_lpf_validation.py
```

Outputs:

```text
outputs/csv/noise_lpf_results.csv
outputs/validation_runs/latest/noise_lpf_validation.json
```

### Step 8: Run Drift Validation

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_validation_drift.py
```

Outputs:

```text
outputs/csv/drift_results.csv
outputs/figures/drift_degradation.svg
outputs/validation_runs/latest/drift_validation.json
```

### Step 9: Run Retuning Validation

```powershell
cd "C:\Users\user\Documents\Agent work"
python scripts/run_retuning.py
```

Outputs:

```text
outputs/csv/retuning_results.csv
outputs/figures/retuning_cost.svg
outputs/validation_runs/latest/retuning_validation.json
```

### Step 10: Refresh Paper-Comparison Outputs

The dashboard does this automatically through `GET /dashboard/outputs`. To refresh directly:

```powershell
cd "C:\Users\user\Documents\Agent work"
python -c "from pathlib import Path; from backend.validation.paper_comparison import ensure_paper_comparison_outputs; ensure_paper_comparison_outputs(Path('outputs'))"
```

### Step 11: Run Backend API

```powershell
cd "C:\Users\user\Documents\Agent work"
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/dashboard/outputs
```

### Step 12: Run Frontend Dashboard

```powershell
cd "C:\Users\user\Documents\Agent work\frontend"
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

If port `8000` or `5173` is busy, use another port and set `VITE_API_BASE` to the backend port.

## 7. Logged Simulation Columns

The multirate simulator writes:

```text
time_s
T1, T2, T3
omega_UW, omega_Nip, omega_RW
v_UW, v_Nip, v_RW
u_UW, u_Nip, u_RW
Tref1, Tref2, Tref3
plant_id
excitation_type
Tlog_ms
Kp_star
noise_enabled
```

## 8. Current Validation Snapshot

These values are from the current generated comparison CSVs in `outputs/csv/`.

### 8.1 Logging

```text
Tlog 1 ms   dashboard RMSE_theta = 1.3347 percent, status = trend
Tlog 2 ms   dashboard RMSE_theta = 1.6651 percent, status = trend
Tlog 5 ms   dashboard RMSE_theta = 6.1422 percent, status = trend
Tlog 10 ms  dashboard RMSE_theta = 75.8537 percent, status = trend
Tlog 20 ms  dashboard RMSE_theta = 75.6224 percent, paper = 23.2 percent, status = review
Tlog 50 ms  dashboard RMSE_theta = 77.9521 percent, status = trend
Tlog 100 ms dashboard RMSE_theta = 82.4825 percent, status = trend
```

### 8.2 Excitation

```text
ET1  NF dashboard = 1.3146 percent, paper = 2.5 percent,  status = pass
ET1  SN dashboard = 9.0127 percent, paper = 31.4 percent, status = review
ET3  NF dashboard = 1.3587 percent, paper = 3.5 percent,  status = pass
ET3  SN dashboard = 10.4379 percent, paper = 22.2 percent, status = review
ET3M SN dashboard = 10.4088 percent, paper = 22.8 percent, status = review
ET6  NF dashboard = 1.3596 percent, paper = 3.4 percent,  status = pass
ET6  SN dashboard = 10.4309 percent, paper = 21.0 percent, status = review
EV1 and EVR are skipped in exact reproduction mode.
```

### 8.3 Noise and LPF

```text
P01-P10 sigma       paper = 0.003*T_max, dashboard = 10/10 pass, status = pass
seed reproducibility paper = numpy.default_rng(0), dashboard = seed 0, status = pass
tension-only noise   paper = no torque noise, dashboard = unchanged, status = pass
LPF cutoff           paper = 100 Hz, dashboard = 100 Hz, status = pass
LPF minimum          paper = >= 50 Hz, dashboard = 100 Hz, status = pass
NF Tlog              paper = 5 ms, dashboard = 5 ms, status = pass
SN Tlog              paper = 20 ms, dashboard = 20 ms, status = pass
```

### 8.4 Drift

```text
EA drift dashboard = 4.5335 percent, paper midpoint = 16.5 percent, status = pass
f drift  dashboard = 5.6117 percent, paper midpoint = 20.5 percent, status = review
J drift  dashboard = 182.3123 percent, paper = 39.3 percent, status = review
Dominant dashboard degradation source = J
```

### 8.5 Retuning

```text
CS-BO(30)  dashboard cost = 37.8384, paper median cost = 0.407, status = review
HGS-only   dashboard cost = 37.8384, paper median cost = 0.403, status = review
HGS+BO(5)  dashboard cost = 37.8384, paper median cost = 0.342, status = review
HGS+BO(10) dashboard cost = 37.8384, paper median cost = 0.337, status = review
Budget trend: HGS+BO(5) uses fewer real evaluations than CS-BO(30).
```

## 9. Tests

Backend tests cover:

```text
config loading
R2R dynamics
RK4 integration
controller output and integral state
multirate simulator timing and CSV schema
excitation profile timing and skip behavior
sensor noise and LPF
SysID estimator and metrics
logging validation
excitation validation
noise/LPF validation
drift validation
retuning validation
API routes
dashboard output manifest
```

Useful commands:

```powershell
python -m pytest
python -m pytest backend/tests/test_r2r_dynamics.py backend/tests/test_rk4.py
python -m pytest backend/tests/test_controller.py backend/tests/test_simulator.py
npm run build
```

Latest verification in this workspace:

```text
python -m pytest -> 54 passed
npm run build    -> passed
```

## 10. Assumptions

```text
P01 is the default plant for most validation runs.
configs/plants_p01_p10.yaml is the plant source of truth.
configs/paper_targets.yaml is the paper-target source of truth.
Exact reproduction skips EV1 and EVR.
Sensor noise uses one deterministic seed: numpy.default_rng(0).
Noise is tension-only; no torque noise is added.
The professor sigma polarity is preserved, and the UW actuator sign is isolated in rho.
The dashboard reads backend-generated outputs rather than hard-coding paper values in React.
```

## 11. Remaining Issues

```text
SN excitation errors are much lower than paper SN targets, so SN rows are marked review.
Logging 20 ms currently differs from the paper 23.2 percent target and is marked review.
Drift f and J numeric comparisons remain review.
Retuning cost scale is provisional and remains review against paper median costs.
Some older API comments and request fields still carry voltage-style naming, while the focused paper-validation simulator uses motor_torque_Nm.
Stacked feature PRs may need rebase or previous branch merges before final merge.
```

## 12. Next Recommended Task

```text
1. Reconcile implemented RMSE_theta with the paper-target YAML formula text.
2. Calibrate sensor-noise excitation so SN comparisons reproduce the paper scale more closely.
3. Revisit logging validation at 10-20 ms and confirm whether the paper target assumes repeated trials or physical-log variance.
4. Normalize retuning cost scale against the paper score definition before calling retuning final.
5. Rerun python -m pytest and npm run build after each calibration change.
```
