"""FastAPI routes for simulation, SysID, validation, and retuning workflows."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Sequence

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.models.equations import R2RParameters, equation_summary
from backend.models.simulation import DEFAULT_DATA_DIR, SimulationConfig, simulate
from backend.sysid.estimator import estimate_parameters, load_rows_from_csv
from backend.validation.calculations import (
    drift_calculation_payload,
    excitation_calculation_payload,
    logging_rate_calculation_payload,
    part1_calculation_payload,
    retuning_calculation_payload,
    simulation_calculation_payload,
    sysid_calculation_payload,
)
from backend.validation.excitations import excitation_names, get_excitation_profile
from backend.validation.parts import run_part_1_parameter_validation, validation_parts_registry
from backend.validation.paper_comparison import ensure_paper_comparison_outputs
from backend.validation.plants import DEFAULT_PLANT_ID, parameters_for_plant, plant_registry
from backend.validation.studies import (
    drift_study,
    excitation_study,
    logging_rate_study,
    retuning_study,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
CONFIG_DIR = PROJECT_ROOT / "configs"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

app = FastAPI(
    title="R2R System-Identification Dashboard API",
    version="0.1.0",
    description="Backend API for R2R simulation, SysID, validation, and retuning studies.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/artifacts", StaticFiles(directory=str(PROJECT_ROOT)), name="artifacts")


class SimulationRequest(BaseModel):
    plant_id: str | None = DEFAULT_PLANT_ID
    duration_s: float = Field(default=4.0, gt=0)
    dt_ms: float = Field(default=1.0, gt=0)
    controller_sample_time_ms: float = Field(default=10.0, gt=0)
    log_sample_time_ms: float = Field(default=10.0, gt=0)
    line_speed_m_s: float = Field(default=1.0, gt=0)
    excitation: str = "ET3"
    excitation_amplitude_V: float = 0.08
    sensor_noise_tension_N: float = Field(default=0.0, ge=0)
    sensor_noise_omega_rad_s: float = Field(default=0.0, ge=0)
    seed: int = 7
    output_name: str = "api_simulation.csv"


class SysIDRequest(BaseModel):
    plant_id: str | None = DEFAULT_PLANT_ID
    csv_path: str | None = None
    duration_s: float = Field(default=4.0, gt=0)
    log_sample_time_ms: float = Field(default=10.0, gt=0)
    excitation: str = "E_Toggle"
    excitation_amplitude_V: float = 0.08
    sensor_noise_tension_N: float = Field(default=0.0, ge=0)
    sensor_noise_omega_rad_s: float = Field(default=0.0, ge=0)


class LoggingRateRequest(BaseModel):
    plant_id: str | None = DEFAULT_PLANT_ID
    tlog_ms_values: list[int] | None = None


class EmptyRequest(BaseModel):
    plant_id: str | None = DEFAULT_PLANT_ID


def _artifact_url(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value).resolve()
    try:
        rel = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    return f"/artifacts/{rel.as_posix()}"


def _attach_urls(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("csv_path", "xlsx_path", "plot_path", "summary_path", "markdown_path"):
        if key in payload:
            payload[key.replace("_path", "_url")] = _artifact_url(payload.get(key))
    return payload


def _read_yaml_config(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    if not path.exists():
        return {"_missing": str(path)}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def _read_output_json(relative_path: str | None) -> dict[str, Any] | None:
    if not relative_path:
        return None
    path = OUTPUT_DIR / relative_path
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {"value": data}


def _read_output_csv(relative_path: str | None, limit: int = 24) -> list[dict[str, Any]]:
    if not relative_path:
        return []
    path = OUTPUT_DIR / relative_path
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))[:limit]


def _file_descriptor(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"available": False, "path": None, "url": None}
    return {
        "available": path.exists(),
        "path": str(path),
        "url": _artifact_url(str(path)) if path.exists() else None,
    }


def _rows_from_mapping(mapping: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not mapping:
        return []
    return [{"name": key, "value": value} for key, value in mapping.items()]


def _plant_table_rows(plants_config: dict[str, Any]) -> list[dict[str, Any]]:
    plants = plants_config.get("plants", {})
    if not isinstance(plants, dict):
        return []
    return [{"plant_id": plant_id, **values} for plant_id, values in plants.items() if isinstance(values, dict)]


def _dashboard_output_page(
    *,
    page_id: str,
    title: str,
    formula: str,
    input_config: dict[str, Any],
    paper_target: dict[str, Any],
    summary_relative: str | None = None,
    csv_relative: str | None = None,
    plot_relative: str | None = None,
    table_rows: list[dict[str, Any]] | None = None,
    result_points: list[str] | None = None,
    display_mode: str = "table",
) -> dict[str, Any]:
    summary_path = OUTPUT_DIR / summary_relative if summary_relative else None
    csv_path = OUTPUT_DIR / csv_relative if csv_relative else None
    plot_path = OUTPUT_DIR / plot_relative if plot_relative else None
    summary = _read_output_json(summary_relative)
    csv_rows = _read_output_csv(csv_relative)
    available_rows = csv_rows or table_rows or _rows_from_mapping(input_config)
    pass_fail = "ready"
    trend_status = "configuration loaded"
    dashboard_result: dict[str, Any] = {"status": "configuration loaded"}

    if summary_relative:
        if summary:
            pass_fail = str(summary.get("pass_fail_status", "available"))
            trend_status = str(summary.get("trend_status", "summary loaded"))
            dashboard_result = summary
        else:
            pass_fail = "missing"
            trend_status = "output summary not generated yet"
            dashboard_result = {"status": "missing", "expected_summary": str(summary_path)}

    return {
        "id": page_id,
        "title": title,
        "formula": formula,
        "input_config": input_config,
        "paper_target": paper_target,
        "dashboard_result": dashboard_result,
        "pass_fail": pass_fail,
        "trend_status": trend_status,
        "result_points": result_points or [trend_status],
        "display_mode": display_mode,
        "input_rows": _rows_from_mapping(input_config),
        "paper_rows": _rows_from_mapping(paper_target),
        "table_rows": available_rows,
        "output_files": {
            "json": _file_descriptor(summary_path),
            "csv": _file_descriptor(csv_path),
            "plot": _file_descriptor(plot_path),
        },
    }


def _preview_rows(rows: Sequence[dict[str, float]], limit: int = 8) -> list[dict[str, float]]:
    if len(rows) <= limit:
        return list(rows)
    half = max(1, limit // 2)
    return list(rows[:half]) + list(rows[-half:])


def _plant_params_or_400(plant_id: str | None) -> tuple[R2RParameters, dict[str, Any]]:
    try:
        return parameters_for_plant(plant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _run_or_422(label: str, fn: Any) -> Any:
    try:
        return fn()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{label} became numerically invalid: {exc}") from exc


def _assert_finite_numbers(value: Any, label: str) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int | float):
        if not math.isfinite(float(value)):
            raise HTTPException(
                status_code=422,
                detail=f"{label} produced a non-finite value. Reduce excitation amplitude or select a baseline-range plant.",
            )
        return
    if isinstance(value, dict):
        for item in value.values():
            _assert_finite_numbers(item, label)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _assert_finite_numbers(item, label)


def _safe_upload_path(filename: str | None) -> Path:
    safe_name = Path(filename or "").name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    return UPLOAD_DIR / safe_name


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard_redirect() -> RedirectResponse:
    return RedirectResponse("http://127.0.0.1:5173/")


@app.get("/equations")
def equations() -> dict[str, object]:
    return equation_summary()


@app.get("/plants")
def plants_route() -> dict[str, object]:
    return {
        "default_plant_id": DEFAULT_PLANT_ID,
        "plants": plant_registry(),
        "note": "Plant presets come from supplement Table S12. Current extracted data gives plant-specific EA_N and metadata; baseline R, L, J, f, and b arrays are retained until exact per-roller arrays are supplied. High-EA plants outside the baseline range default to zero excitation for numerical safety.",
    }


@app.post("/simulate")
def simulate_route(request: SimulationRequest) -> dict[str, object]:
    params, plant = _plant_params_or_400(request.plant_id)
    config = SimulationConfig(
        duration_s=request.duration_s,
        dt_s=request.dt_ms / 1000.0,
        controller_sample_time_s=request.controller_sample_time_ms / 1000.0,
        log_sample_time_s=request.log_sample_time_ms / 1000.0,
        line_speed_m_s=request.line_speed_m_s,
        sensor_noise_tension_N=request.sensor_noise_tension_N,
        sensor_noise_omega_rad_s=request.sensor_noise_omega_rad_s,
        seed=request.seed,
        output_name=request.output_name,
    )
    result = _run_or_422(
        "Simulation",
        lambda: simulate(
            params,
            config=config,
            excitation=get_excitation_profile(request.excitation, request.excitation_amplitude_V),
            output_dir=DEFAULT_DATA_DIR,
        ),
    )
    _assert_finite_numbers(result.metrics, "Simulation metrics")
    payload: dict[str, Any] = {
        "metrics": result.metrics,
        "csv_path": result.csv_path,
        "xlsx_path": result.xlsx_path,
        "plot_path": None,
        "plant": plant,
        "equation_sample": result.equation_sample,
        "preview_rows": _preview_rows(result.rows),
    }
    payload.update(simulation_calculation_payload(result.metrics, result.rows, config, params))
    return _attach_urls(payload)


@app.post("/sysid")
def sysid_route(request: SysIDRequest) -> dict[str, object]:
    params, plant = _plant_params_or_400(request.plant_id)
    csv_path = request.csv_path
    if csv_path:
        rows = load_rows_from_csv(csv_path)
    else:
        sim = _run_or_422(
            "SysID source simulation",
            lambda: simulate(
                params,
                config=SimulationConfig(
                    duration_s=request.duration_s,
                    log_sample_time_s=request.log_sample_time_ms / 1000.0,
                    sensor_noise_tension_N=request.sensor_noise_tension_N,
                    sensor_noise_omega_rad_s=request.sensor_noise_omega_rad_s,
                    output_name="api_sysid_source.csv",
                ),
                excitation=get_excitation_profile(request.excitation, request.excitation_amplitude_V),
                output_dir=DEFAULT_DATA_DIR,
            ),
        )
        _assert_finite_numbers(sim.metrics, "SysID source simulation metrics")
        rows = sim.rows
        csv_path = sim.csv_path
    result = _run_or_422(
        "SysID estimation",
        lambda: estimate_parameters(rows, params, params, summary_name="api_sysid_result.json"),
    )
    _assert_finite_numbers(result.to_dict(), "SysID result")
    metrics = {"RMSE_theta": result.rmse_theta, "samples": len(rows)}
    payload: dict[str, Any] = {
        "metrics": metrics,
        "estimates": result.estimates,
        "error_table": result.error_table,
        "plant": plant,
        "csv_path": csv_path,
        "plot_path": None,
        "summary_path": result.summary_path,
    }
    payload.update(sysid_calculation_payload(metrics, result.error_table))
    return _attach_urls(payload)


@app.post("/validate/logging-rate")
def logging_rate_route(request: LoggingRateRequest) -> dict[str, object]:
    params, plant = _plant_params_or_400(request.plant_id)
    payload = _run_or_422("Logging-rate study", lambda: logging_rate_study(request.tlog_ms_values, params=params))
    _assert_finite_numbers(payload, "Logging-rate study")
    payload["plant"] = plant
    payload.update(logging_rate_calculation_payload(payload))
    return _attach_urls(payload)


@app.get("/validation/parts")
def validation_parts_route() -> dict[str, object]:
    return {"parts": validation_parts_registry()}


@app.post("/validate/part/1")
def validation_part_1_route(_: EmptyRequest | None = None) -> dict[str, object]:
    request = _ or EmptyRequest()
    params, plant = _plant_params_or_400(request.plant_id)
    payload = _run_or_422(
        "Part 1 parameter validation",
        lambda: run_part_1_parameter_validation(params=params, selected_plant=plant),
    )
    _assert_finite_numbers(payload["metrics"], "Part 1 metrics")
    payload["plant"] = plant
    payload.update(part1_calculation_payload(payload))
    return _attach_urls(payload)


@app.get("/dashboard/outputs")
def dashboard_outputs_route() -> dict[str, object]:
    default_config = _read_yaml_config("default.yaml")
    plants_config = _read_yaml_config("plants_p01_p10.yaml")
    excitation_config = _read_yaml_config("excitation_profiles.yaml")
    noise_config = _read_yaml_config("noise_lpf.yaml")
    paper_targets = _read_yaml_config("paper_targets.yaml")
    equations = equation_summary()
    comparisons = ensure_paper_comparison_outputs(OUTPUT_DIR)

    output_manifest = [
        {
            "label": "logging validation summary",
            "type": "json",
            **_file_descriptor(OUTPUT_DIR / "validation_runs" / "latest" / "logging_validation.json"),
        },
        {
            "label": "logging results",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "logging_results.csv"),
        },
        {
            "label": "logging paper comparison",
            "type": "svg",
            **_file_descriptor(OUTPUT_DIR / "figures" / "logging_paper_comparison.svg"),
        },
        {
            "label": "logging comparison CSV",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "logging_paper_comparison.csv"),
        },
        {
            "label": "excitation validation summary",
            "type": "json",
            **_file_descriptor(OUTPUT_DIR / "validation_runs" / "latest" / "excitation_validation.json"),
        },
        {
            "label": "excitation results",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "excitation_results.csv"),
        },
        {
            "label": "excitation paper comparison",
            "type": "svg",
            **_file_descriptor(OUTPUT_DIR / "figures" / "excitation_paper_comparison.svg"),
        },
        {
            "label": "excitation comparison CSV",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "excitation_paper_comparison.csv"),
        },
        {
            "label": "noise/lpf validation summary",
            "type": "json",
            **_file_descriptor(OUTPUT_DIR / "validation_runs" / "latest" / "noise_lpf_validation.json"),
        },
        {
            "label": "noise/lpf results",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "noise_lpf_results.csv"),
        },
        {
            "label": "noise/lpf comparison CSV",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "noise_lpf_paper_comparison.csv"),
        },
        {
            "label": "drift validation summary",
            "type": "json",
            **_file_descriptor(OUTPUT_DIR / "validation_runs" / "latest" / "drift_validation.json"),
        },
        {
            "label": "drift results",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "drift_results.csv"),
        },
        {
            "label": "drift paper comparison",
            "type": "svg",
            **_file_descriptor(OUTPUT_DIR / "figures" / "drift_paper_comparison.svg"),
        },
        {
            "label": "drift comparison CSV",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "drift_paper_comparison.csv"),
        },
        {
            "label": "retuning comparison CSV",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "retuning_paper_comparison.csv"),
        },
        {
            "label": "retuning validation summary",
            "type": "json",
            **_file_descriptor(OUTPUT_DIR / "validation_runs" / "latest" / "retuning_validation.json"),
        },
        {
            "label": "retuning results",
            "type": "csv",
            **_file_descriptor(OUTPUT_DIR / "csv" / "retuning_results.csv"),
        },
    ]

    validation_config = default_config.get("validation", {}) if isinstance(default_config, dict) else {}
    pages = [
        _dashboard_output_page(
            page_id="plant-setup",
            title="Plant Setup",
            formula="plant = {EA, R, J, f, L, T_ref, T_max, v_ref}",
            input_config=plants_config,
            paper_target={
                "source": "configs/plants_p01_p10.yaml",
                "plant_count": len(plants_config.get("plants", {})) if isinstance(plants_config.get("plants"), dict) else 0,
            },
            table_rows=_plant_table_rows(plants_config),
            result_points=["P01-P10 plant parameters are loaded from YAML.", "Use this page as the plant input table."],
            display_mode="table",
        ),
        _dashboard_output_page(
            page_id="model-equations",
            title="Model Equations",
            formula="dT_i/dt = EA/L_i*(v_i - v_{i-1}) + (T_{i-1}v_{i-1} - T_i v_i)/L_i",
            input_config={
                "state": default_config.get("state"),
                "input": default_config.get("input"),
                "state_vector": equations.get("state_vector"),
                "input_vector": equations.get("input_vector"),
            },
            paper_target=paper_targets.get("simulation", {}) if isinstance(paper_targets, dict) else {},
            table_rows=equations.get("units") if isinstance(equations.get("units"), list) else None,
            result_points=["State and input order match the implemented mathematical model."],
            display_mode="table",
        ),
        _dashboard_output_page(
            page_id="controller",
            title="Controller",
            formula="v_corr_i = (L_i/EA)Kp_star(sigma_i e_i + I_i/TI); omega_ref_i = omega_ss_i + rho_i v_corr_i/R_i; u_i = Kvel_i*(omega_ref_i - omega_i) + u_ff_i",
            input_config=default_config.get("controller", {}) if isinstance(default_config, dict) else {},
            paper_target=paper_targets.get("kp_targets", {}) if isinstance(paper_targets, dict) else {},
            result_points=["Cascade PI plus feedforward is implemented.", "Kp_star targets are read from paper_targets.yaml."],
            display_mode="table",
        ),
        _dashboard_output_page(
            page_id="sysid-setup",
            title="SysID Setup",
            formula="theta = [kt_UW, kt_Nip, kt_RW, kf_UW, kf_Nip, kf_RW, EA]",
            input_config=default_config.get("sysid", {}) if isinstance(default_config, dict) else {},
            paper_target=paper_targets.get("sysid", {}) if isinstance(paper_targets, dict) else {},
            result_points=["Seven-parameter TRF least-squares SysID is implemented."],
            display_mode="table",
        ),
        _dashboard_output_page(
            page_id="logging-validation",
            title="Logging Validation",
            formula="RMSE_theta = mean(abs((theta_hat - theta_true) / theta_true))",
            input_config={"logging_rate_ms": validation_config.get("logging_rate_ms")},
            paper_target=paper_targets.get("logging_targets", {}) if isinstance(paper_targets, dict) else {},
            summary_relative=comparisons["logging"]["relative_summary"],
            csv_relative=comparisons["logging"]["relative_csv"],
            plot_relative=comparisons["logging"]["relative_plot"],
            result_points=comparisons["logging"]["result_points"],
            display_mode=comparisons["logging"]["display_mode"],
        ),
        _dashboard_output_page(
            page_id="excitation-validation",
            title="Excitation Validation",
            formula="T_ref_i(t) = T_ref_i*(1 + 0.20*step_i(t))",
            input_config=excitation_config,
            paper_target=paper_targets.get("excitation_targets", {}) if isinstance(paper_targets, dict) else {},
            summary_relative=comparisons["excitation"]["relative_summary"],
            csv_relative=comparisons["excitation"]["relative_csv"],
            plot_relative=comparisons["excitation"]["relative_plot"],
            result_points=comparisons["excitation"]["result_points"],
            display_mode=comparisons["excitation"]["display_mode"],
        ),
        _dashboard_output_page(
            page_id="noise-lpf-validation",
            title="Noise/LPF Validation",
            formula="T_meas = LPF_100Hz(T_true + N(0, (0.003*T_max)^2))",
            input_config=noise_config,
            paper_target=paper_targets.get("noise_lpf_targets", {}) if isinstance(paper_targets, dict) else {},
            summary_relative=comparisons["noise_lpf"]["relative_summary"],
            csv_relative=comparisons["noise_lpf"]["relative_csv"],
            plot_relative=comparisons["noise_lpf"]["relative_plot"],
            result_points=comparisons["noise_lpf"]["result_points"],
            display_mode=comparisons["noise_lpf"]["display_mode"],
        ),
        _dashboard_output_page(
            page_id="drift-validation",
            title="Drift Validation",
            formula="theta_drift = theta_nominal*(1 + delta)",
            input_config={"drift_scenarios": validation_config.get("drift_scenarios")},
            paper_target=paper_targets.get("drift_targets", {}) if isinstance(paper_targets, dict) else {},
            summary_relative=comparisons["drift"]["relative_summary"],
            csv_relative=comparisons["drift"]["relative_csv"],
            plot_relative=comparisons["drift"]["relative_plot"],
            result_points=comparisons["drift"]["result_points"],
            display_mode=comparisons["drift"]["display_mode"],
        ),
        _dashboard_output_page(
            page_id="retuning-validation",
            title="Retuning Validation",
            formula="S = sum_i w_i*(RMSE_i/1 + OS_i/100 + t90_i/15 + Utotal_i/200)",
            input_config=default_config.get("retuning", {}) if isinstance(default_config, dict) else {},
            paper_target=paper_targets.get("retuning_targets", {}) if isinstance(paper_targets, dict) else {},
            summary_relative=comparisons["retuning"]["relative_summary"],
            csv_relative=comparisons["retuning"]["relative_csv"],
            plot_relative=comparisons["retuning"]["relative_plot"],
            result_points=comparisons["retuning"]["result_points"],
            display_mode=comparisons["retuning"]["display_mode"],
        ),
        _dashboard_output_page(
            page_id="export-report",
            title="Export Report",
            formula="report = configs + paper_targets + output_summaries + csv_tables + figures",
            input_config={"output_root": str(OUTPUT_DIR), "manifest_count": len(output_manifest)},
            paper_target={"source": "configs/paper_targets.yaml", "sections": list(paper_targets.keys())},
            csv_relative="csv/logging_results.csv",
            table_rows=output_manifest,
            result_points=["Use the CSV and plot links on each validation page for export."],
            display_mode="table",
        ),
    ]

    return {
        "output_root": str(OUTPUT_DIR),
        "config_root": str(CONFIG_DIR),
        "pages": pages,
        "manifest": output_manifest,
    }


@app.post("/validate/excitation")
def excitation_route(_: EmptyRequest | None = None) -> dict[str, object]:
    request = _ or EmptyRequest()
    params, plant = _plant_params_or_400(request.plant_id)
    payload = _run_or_422("Excitation study", lambda: excitation_study(params=params))
    _assert_finite_numbers(payload, "Excitation study")
    payload["plant"] = plant
    payload.update(excitation_calculation_payload(payload))
    return _attach_urls(payload)


@app.post("/validate/drift")
def drift_route(_: EmptyRequest | None = None) -> dict[str, object]:
    request = _ or EmptyRequest()
    params, plant = _plant_params_or_400(request.plant_id)
    payload = _run_or_422("Drift study", lambda: drift_study(params=params))
    _assert_finite_numbers(payload, "Drift study")
    payload["plant"] = plant
    payload.update(drift_calculation_payload(payload))
    return _attach_urls(payload)


@app.post("/retune")
def retune_route(_: EmptyRequest | None = None) -> dict[str, object]:
    request = _ or EmptyRequest()
    params, plant = _plant_params_or_400(request.plant_id)
    payload = _run_or_422("Retuning study", lambda: retuning_study(params=params))
    _assert_finite_numbers(payload, "Retuning study")
    payload["plant"] = plant
    payload.update(retuning_calculation_payload(payload))
    return _attach_urls(payload)


@app.get("/metadata")
def metadata() -> dict[str, object]:
    return {
        "excitation_profiles": list(excitation_names()),
        "default_plant_id": DEFAULT_PLANT_ID,
        "plants": plant_registry(),
        "state_vector": equation_summary()["state_vector"],
        "input_vector": equation_summary()["input_vector"],
        "routes": [
            "POST /simulate",
            "POST /sysid",
            "GET /plants",
            "GET /validation/parts",
            "POST /validate/part/1",
            "POST /validate/logging-rate",
            "POST /validate/excitation",
            "POST /validate/drift",
            "POST /retune",
            "POST /upload",
        ],
    }


@app.post("/upload")
async def upload_data_file(file: UploadFile = File(...)) -> dict[str, object]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = _safe_upload_path(file.filename)
    contents = await file.read()
    destination.write_bytes(contents)
    rel_path = destination.relative_to(PROJECT_ROOT)
    return {
        "filename": destination.name,
        "bytes": len(contents),
        "path": str(destination),
        "url": f"/artifacts/{rel_path.as_posix()}",
    }
