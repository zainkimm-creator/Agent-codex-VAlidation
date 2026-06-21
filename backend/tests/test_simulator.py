import csv
from math import isfinite
from pathlib import Path

from pytest import approx

from backend.simulation.simulator import (
    REQUIRED_COLUMNS,
    MultirateSimulationConfig,
    run_multirate_simulation,
)


def test_ts_over_dt_is_10_integration_steps(tmp_path: Path):
    result = run_multirate_simulation(
        MultirateSimulationConfig(duration_s=0.03, output_name="steps.csv"),
        output_dir=tmp_path,
    )

    assert result.integration_steps_per_control == 10
    assert result.control_update_steps[:4] == [0, 10, 20, 30]


def test_tlog_20ms_logs_every_020s(tmp_path: Path):
    result = run_multirate_simulation(
        MultirateSimulationConfig(duration_s=0.06, Tlog_s=0.020, output_name="tlog.csv"),
        output_dir=tmp_path,
    )

    times = [float(row["time_s"]) for row in result.rows]
    assert times == [0.0, 0.02, 0.04, 0.06]


def test_output_csv_has_required_columns(tmp_path: Path):
    result = run_multirate_simulation(
        MultirateSimulationConfig(duration_s=0.02, output_name="columns.csv"),
        output_dir=tmp_path,
    )

    with Path(result.csv_path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(REQUIRED_COLUMNS)


def test_p01_baseline_simulation_runs_without_nan(tmp_path: Path):
    result = run_multirate_simulation(
        MultirateSimulationConfig(plant_id="P01", duration_s=0.05, output_name="p01.csv"),
        output_dir=tmp_path,
    )

    assert Path(result.csv_path).exists()
    assert result.plant.plant_id == "P01"
    numeric_columns = [
        "time_s",
        "T1",
        "T2",
        "T3",
        "omega_UW",
        "omega_Nip",
        "omega_RW",
        "v_UW",
        "v_Nip",
        "v_RW",
        "u_UW",
        "u_Nip",
        "u_RW",
        "Tref1",
        "Tref2",
        "Tref3",
        "Tlog_ms",
        "Kp_star",
    ]
    for row in result.rows:
        assert all(isfinite(float(row[column])) for column in numeric_columns)


def test_et1_excitation_changes_logged_reference_after_2s(tmp_path: Path):
    result = run_multirate_simulation(
        MultirateSimulationConfig(
            plant_id="P01",
            duration_s=2.02,
            Tlog_s=1.0,
            excitation_type="ET1",
            Kp_star=100.0,
            output_name="et1_refs.csv",
        ),
        output_dir=tmp_path,
    )

    by_time = {round(float(row["time_s"]), 2): row for row in result.rows}
    assert float(by_time[0.0]["Tref1"]) == 12.0
    assert float(by_time[1.0]["Tref1"]) == 12.0
    assert float(by_time[2.0]["Tref1"]) == 14.4
    assert float(by_time[2.0]["Tref2"]) == 12.0
    assert float(by_time[2.0]["Tref3"]) == 12.0


def test_line_speed_multiplier_scales_initial_logged_velocity(tmp_path: Path):
    baseline = run_multirate_simulation(
        MultirateSimulationConfig(duration_s=0.001, output_name="base_speed.csv"),
        output_dir=tmp_path,
    )
    faster = run_multirate_simulation(
        MultirateSimulationConfig(
            duration_s=0.001,
            line_speed_multiplier=2.0,
            output_name="fast_speed.csv",
        ),
        output_dir=tmp_path,
    )

    assert float(faster.rows[0]["v_UW"]) == approx(2.0 * float(baseline.rows[0]["v_UW"]))
