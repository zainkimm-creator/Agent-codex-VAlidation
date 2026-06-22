"""Logging-rate validation runner."""

from __future__ import annotations

import csv
import json
import struct
import zlib
from pathlib import Path
from typing import Mapping, Sequence

import yaml

from backend.noise.filters import apply_configured_lpf
from backend.noise.sensor_noise import add_tension_sensor_noise
from backend.simulation.simulator import MultirateSimulationConfig, run_multirate_simulation
from backend.sysid.estimator import estimate_parameters

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs"
DEFAULT_TARGETS_PATH = PROJECT_ROOT / "configs" / "paper_targets.yaml"
VALIDATION_CASES = ("NF", "SN")


def _load_targets(targets_path: Path = DEFAULT_TARGETS_PATH) -> dict[str, object]:
    with Path(targets_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Invalid paper targets config: {targets_path}")
    return dict(payload)


def _ensure_output_dirs(output_root: Path) -> dict[str, Path]:
    paths = {
        "csv": output_root / "csv",
        "figures": output_root / "figures",
        "latest": output_root / "validation_runs" / "latest",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _write_csv(rows: Sequence[Mapping[str, object]], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _write_json(payload: Mapping[str, object], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _write_simple_png(
    path: Path,
    values: Sequence[float],
    *,
    width: int = 720,
    height: int = 420,
    bar_color: tuple[int, int, int] = (47, 111, 115),
) -> str:
    """Write a small valid PNG bar chart using only the standard library."""

    path.parent.mkdir(parents=True, exist_ok=True)
    pixels = bytearray([247, 247, 242] * width * height)

    def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            index = (y * width + x) * 3
            pixels[index : index + 3] = bytes(color)

    axis = (55, 65, 70)
    left, bottom, top, right = 50, height - 42, 28, width - 24
    for x in range(left, right):
        set_pixel(x, bottom, axis)
    for y in range(top, bottom + 1):
        set_pixel(left, y, axis)

    max_value = max([0.0, *[abs(float(value)) for value in values]]) or 1.0
    slot = max(1, (right - left - 12) // max(1, len(values)))
    for idx, value in enumerate(values):
        bar_height = int((abs(float(value)) / max_value) * (bottom - top - 8))
        x0 = left + 8 + idx * slot
        x1 = min(x0 + max(3, int(slot * 0.62)), right - 1)
        y0 = bottom - bar_height
        for x in range(x0, x1):
            for y in range(y0, bottom):
                set_pixel(x, y, bar_color)

    rows = [bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height)]
    raw = b"".join(b"\x00" + row for row in rows)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(data)
    return str(path)


def _paper_logging_targets(targets: Mapping[str, object]) -> dict[str, object]:
    logging_targets = targets.get("logging_targets", {})
    simulation_targets = targets.get("simulation", {})
    if not isinstance(logging_targets, Mapping) or not isinstance(simulation_targets, Mapping):
        raise ValueError("paper_targets.yaml is missing logging_targets or simulation section")
    return {
        "sweep_ms": list(simulation_targets.get("Tlog_sweep_ms", [1, 2, 5, 10, 20, 50, 100])),
        "sn_best_window_ms": list(logging_targets.get("SN_best_Tlog_ms", [10, 20])),
        "sn_reference_rmse_percent_at_20ms": float(
            logging_targets.get("SN_reference_RMSE_theta_percent_at_20ms", 23.2)
        ),
    }


def _with_measured_tensions(
    rows: Sequence[Mapping[str, object]],
    *,
    plant_id: str,
    sample_time_s: float,
    noise_enabled: bool,
) -> list[dict[str, object]]:
    measured = [dict(row) for row in rows]
    if not noise_enabled:
        return measured

    tensions = [[float(row["T1"]), float(row["T2"]), float(row["T3"])] for row in measured]
    noisy = add_tension_sensor_noise(tensions, plant_id, noise_enabled=True)
    filtered = apply_configured_lpf(noisy, sample_time_s=sample_time_s)
    for index, row in enumerate(measured):
        row["T1"] = float(filtered[index][0])
        row["T2"] = float(filtered[index][1])
        row["T3"] = float(filtered[index][2])
        row["noise_enabled"] = True
    return measured


def run_logging_validation(
    *,
    plant_id: str = "P01",
    tlog_ms_values: Sequence[int] | None = None,
    validation_cases: Sequence[str] = VALIDATION_CASES,
    duration_s: float = 0.2,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    targets_path: Path = DEFAULT_TARGETS_PATH,
) -> dict[str, object]:
    """Run logging-rate validation and write CSV, PNG, and JSON artifacts."""

    output_paths = _ensure_output_dirs(output_root)
    targets = _paper_logging_targets(_load_targets(targets_path))
    sweep = list(tlog_ms_values or targets["sweep_ms"])
    rows: list[dict[str, object]] = []

    for case_name_raw in validation_cases:
        case_name = case_name_raw.upper()
        if case_name not in VALIDATION_CASES:
            raise ValueError(f"Unknown validation case '{case_name_raw}'. Valid cases: {', '.join(VALIDATION_CASES)}.")
        noise_enabled = case_name == "SN"

        for tlog_ms in sweep:
            tlog_s = float(tlog_ms) / 1000.0
            sim = run_multirate_simulation(
                MultirateSimulationConfig(
                    plant_id=plant_id,
                    duration_s=duration_s,
                    Tlog_s=tlog_s,
                    noise_enabled=noise_enabled,
                    output_name=f"logging_source_{case_name}_{int(tlog_ms)}ms.csv",
                ),
                output_dir=output_paths["csv"],
            )
            params = sim.plant.controller_params()
            measured_rows = _with_measured_tensions(
                sim.rows,
                plant_id=plant_id,
                sample_time_s=tlog_s,
                noise_enabled=noise_enabled,
            )
            _write_csv(measured_rows, Path(sim.csv_path))
            sysid = estimate_parameters(measured_rows, params, params, summary_name=None)
            rmse_percent = 100.0 * sysid.rmse_theta
            in_paper_window = int(tlog_ms) in {int(value) for value in targets["sn_best_window_ms"]}
            has_paper_numeric_target = case_name == "SN" and int(tlog_ms) == 20
            rows.append(
                {
                    "plant_id": plant_id,
                    "dashboard_case": case_name,
                    "noise_enabled": noise_enabled,
                    "Tlog_ms": int(tlog_ms),
                    "RMSE_theta": sysid.rmse_theta,
                    "RMSE_theta_percent": rmse_percent,
                    "paper_SN_best_window_ms": ",".join(str(value) for value in targets["sn_best_window_ms"]),
                    "paper_SN_reference_RMSE_theta_percent_at_20ms": targets[
                        "sn_reference_rmse_percent_at_20ms"
                    ],
                    "paper_target_percent": targets["sn_reference_rmse_percent_at_20ms"]
                    if has_paper_numeric_target
                    else None,
                    "pass_fail_status": "pass" if case_name == "SN" and in_paper_window else "trend",
                    "trend_status": "paper-window" if case_name == "SN" and in_paper_window else "sweep-only",
                    "source_csv_path": sim.csv_path,
                }
            )

    sn_rows = [row for row in rows if row["dashboard_case"] == "SN"]
    best = min(sn_rows, key=lambda row: float(row["RMSE_theta"])) if sn_rows else None
    best_in_window = bool(best and int(best["Tlog_ms"]) in {int(value) for value in targets["sn_best_window_ms"]})
    csv_path = _write_csv(rows, output_paths["csv"] / "logging_results.csv")
    figure_path = _write_simple_png(
        output_paths["figures"] / "tlog_vs_rmse.png",
        [float(row["RMSE_theta_percent"]) for row in sn_rows or rows],
        bar_color=(47, 111, 115),
    )
    summary = {
        "validation": "logging",
        "plant_id": plant_id,
        "rows": rows,
        "best_SN_Tlog_ms": best["Tlog_ms"] if best else None,
        "best_SN_RMSE_theta": best["RMSE_theta"] if best else None,
        "paper_targets": targets,
        "pass_fail_status": "pass" if best_in_window else "fail",
        "trend_status": "best in paper 10-20 ms window" if best_in_window else "best outside paper 10-20 ms window",
        "csv_path": csv_path,
        "figure_path": figure_path,
    }
    summary_path = _write_json(summary, output_paths["latest"] / "logging_validation.json")
    summary["summary_path"] = summary_path
    return summary
