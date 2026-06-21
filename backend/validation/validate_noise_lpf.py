"""Noise and low-pass-filter validation runner for dashboard artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

from backend.noise.filters import apply_configured_lpf, load_lpf_cutoff_hz
from backend.noise.sensor_noise import (
    DEFAULT_NOISE_CONFIG,
    DEFAULT_PLANT_CONFIG,
    add_noise_to_measurements,
    configured_tlog_ms,
    generate_tension_noise,
    load_sensor_noise_config,
    sigma_for_plant,
)
from backend.validation.validate_logging import DEFAULT_OUTPUT_ROOT, _ensure_output_dirs, _write_csv, _write_json


def _load_yaml(path: Path) -> Mapping[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Invalid YAML mapping: {path}")
    return payload


def _plant_rows(plant_config_path: Path) -> Mapping[str, Mapping[str, Any]]:
    payload = _load_yaml(plant_config_path)
    plants = payload.get("plants", {})
    if not isinstance(plants, Mapping):
        raise ValueError(f"Invalid plant config: {plant_config_path}")
    return {str(key): value for key, value in plants.items() if isinstance(value, Mapping)}


def _close(left: float, right: float, *, tolerance: float = 1e-9) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def _row(
    *,
    section: str,
    check: str,
    paper_value: object,
    dashboard_value: object,
    status: str,
    plant_id: str | None = None,
    note: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "check": check,
        "plant_id": plant_id or "",
        "paper_value": paper_value,
        "dashboard_value": dashboard_value,
        "status": status,
        "note": note,
    }


def run_noise_lpf_validation(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    plant_config_path: Path = DEFAULT_PLANT_CONFIG,
    noise_config_path: Path = DEFAULT_NOISE_CONFIG,
) -> dict[str, object]:
    """Validate professor noise/LPF settings and write CSV/JSON artifacts."""

    output_paths = _ensure_output_dirs(output_root)
    plants = _plant_rows(plant_config_path)
    config = load_sensor_noise_config(noise_config_path)
    cutoff_hz = load_lpf_cutoff_hz(noise_config_path)
    rows: list[dict[str, object]] = []

    for plant_id, plant in sorted(plants.items()):
        t_max = float(plant["T_max_N"])
        expected_sigma = config.sigma_fraction_of_Tmax * t_max
        computed_sigma = sigma_for_plant(
            plant_id,
            noise_config_path=noise_config_path,
            plant_config_path=plant_config_path,
        )
        configured_sigma = config.per_plant_sigma_N.get(plant_id)
        sigma_matches = _close(computed_sigma, expected_sigma)
        config_matches = configured_sigma is not None and _close(configured_sigma, expected_sigma)
        rows.append(
            _row(
                section="sigma",
                check="per-plant sigma",
                plant_id=plant_id,
                paper_value=f"0.003*T_max = {expected_sigma:.6g} N",
                dashboard_value=f"{computed_sigma:.6g} N",
                status="pass" if sigma_matches and config_matches else "review",
                note=f"config table sigma={configured_sigma:.6g} N" if configured_sigma is not None else "missing config sigma",
            )
        )

    tensions = np.ones((5, 3), dtype=float) * float(next(iter(plants.values()))["T_ref_N"])
    first_noise = generate_tension_noise(
        tensions,
        "P01",
        config_path=noise_config_path,
        plant_config_path=plant_config_path,
    )
    second_noise = generate_tension_noise(
        tensions,
        "P01",
        config_path=noise_config_path,
        plant_config_path=plant_config_path,
    )
    rows.extend(
        [
            _row(
                section="noise",
                check="seed reproducibility",
                paper_value="numpy.default_rng(0)",
                dashboard_value=f"seed {config.seed}",
                status="pass" if config.seed == 0 and np.array_equal(first_noise, second_noise) else "review",
                note="same plant and shape returns the same realization",
            ),
            _row(
                section="noise",
                check="noise shape",
                paper_value="same shape as tension data",
                dashboard_value=str(tuple(first_noise.shape)),
                status="pass" if first_noise.shape == tensions.shape else "review",
                note="noise generated for measured tensions",
            ),
        ]
    )

    torques = np.arange(15, dtype=float).reshape(5, 3) / 10.0
    noisy_tensions, unchanged_torques = add_noise_to_measurements(tensions, torques, "P01", noise_enabled=True)
    rows.append(
        _row(
            section="noise",
            check="torque unchanged",
            paper_value="no torque noise",
            dashboard_value="unchanged" if np.array_equal(unchanged_torques, torques) else "changed",
            status="pass" if np.array_equal(unchanged_torques, torques) else "review",
            note="noise helper returns motor torque copy without additive noise",
        )
    )

    filtered = apply_configured_lpf(noisy_tensions, sample_time_s=config.SN_Tlog_ms / 1000.0, config_path=noise_config_path)
    rows.extend(
        [
            _row(
                section="lpf",
                check="LPF cutoff",
                paper_value="100 Hz",
                dashboard_value=f"{cutoff_hz:g} Hz",
                status="pass" if _close(cutoff_hz, 100.0) else "review",
                note="reproduction cutoff",
            ),
            _row(
                section="lpf",
                check="LPF minimum",
                paper_value=">= 50 Hz",
                dashboard_value=f"{cutoff_hz:g} Hz",
                status="pass" if cutoff_hz >= 50.0 else "review",
                note="meets paper minimum",
            ),
            _row(
                section="lpf",
                check="LPF shape",
                paper_value="preserve measured tension shape",
                dashboard_value=str(tuple(filtered.shape)),
                status="pass" if filtered.shape == noisy_tensions.shape else "review",
                note="first-order filter applied after noise",
            ),
        ]
    )

    rows.extend(
        [
            _row(
                section="logging",
                check="NF Tlog",
                paper_value="5 ms",
                dashboard_value=f"{configured_tlog_ms(noise_enabled=False, config_path=noise_config_path)} ms",
                status="pass" if configured_tlog_ms(noise_enabled=False, config_path=noise_config_path) == 5 else "review",
                note="noise-free published excitation logging",
            ),
            _row(
                section="logging",
                check="SN Tlog",
                paper_value="20 ms",
                dashboard_value=f"{configured_tlog_ms(noise_enabled=True, config_path=noise_config_path)} ms",
                status="pass" if configured_tlog_ms(noise_enabled=True, config_path=noise_config_path) == 20 else "review",
                note="sensor-noise published excitation logging",
            ),
        ]
    )

    sigma_rows = [row for row in rows if row["section"] == "sigma"]
    sigma_passed = sum(1 for row in sigma_rows if row["status"] == "pass")
    pass_fail_status = "pass" if all(row["status"] == "pass" for row in rows) else "review"
    csv_path = _write_csv(rows, output_paths["csv"] / "noise_lpf_results.csv")
    summary = {
        "validation": "noise_lpf",
        "rows": rows,
        "sigma_plants_checked": len(sigma_rows),
        "sigma_plants_passed": sigma_passed,
        "cutoff_Hz": cutoff_hz,
        "NF_Tlog_ms": config.NF_Tlog_ms,
        "SN_Tlog_ms": config.SN_Tlog_ms,
        "pass_fail_status": pass_fail_status,
        "trend_status": "noise sigma, LPF, Tlog, and torque checks pass"
        if pass_fail_status == "pass"
        else "one or more noise/LPF checks need review",
        "result_points": [
            f"P01-P10 sigma checks: {sigma_passed}/{len(sigma_rows)} pass.",
            f"LPF cutoff: {cutoff_hz:g} Hz.",
            f"Logging: NF {config.NF_Tlog_ms} ms, SN {config.SN_Tlog_ms} ms.",
            "Torque channels remain un-noised.",
        ],
        "csv_path": csv_path,
        "figure_path": None,
    }
    summary_path = _write_json(summary, output_paths["latest"] / "noise_lpf_validation.json")
    summary["summary_path"] = summary_path
    return summary
