from pathlib import Path

from backend.models.simulation import SimulationConfig, simulate
from backend.sysid.estimator import estimate_parameters, load_rows_from_csv
from backend.validation.excitations import get_excitation_profile


def test_simulation_produces_csv(tmp_path: Path):
    result = simulate(
        config=SimulationConfig(duration_s=0.5, output_name="test_sim.csv"),
        excitation=get_excitation_profile("ET3", 0.04),
        output_dir=tmp_path,
    )
    assert result.csv_path is not None
    assert Path(result.csv_path).exists()
    assert result.metrics["samples"] > 0
    loaded = load_rows_from_csv(result.csv_path)
    assert len(loaded) == len(result.rows)


def test_simulation_uses_focused_r2r_dynamics_and_rk4(monkeypatch):
    import backend.models.simulation as simulation

    calls = {"rk4": 0, "dynamics": 0}
    real_rk4_step = simulation.rk4_step
    real_r2r_derivatives = simulation.r2r_derivatives

    def counted_derivatives(state, inputs, params):
        calls["dynamics"] += 1
        return real_r2r_derivatives(state, inputs, params)

    def counted_rk4_step(f, state, inputs, params, dt):
        calls["rk4"] += 1
        assert f is counted_derivatives
        return real_rk4_step(f, state, inputs, params, dt)

    monkeypatch.setattr(simulation, "r2r_derivatives", counted_derivatives)
    monkeypatch.setattr(simulation, "rk4_step", counted_rk4_step)

    result = simulate(config=SimulationConfig(duration_s=0.01), write_output=False)

    assert calls["rk4"] > 0
    assert calls["dynamics"] > 0
    assert result.metrics["samples"] > 0


def test_sysid_recovers_synthetic_parameters_with_reasonable_error():
    sim = simulate(
        config=SimulationConfig(duration_s=2.0, log_sample_time_s=0.010),
        excitation=get_excitation_profile("E_Toggle", 0.08),
        write_output=False,
    )
    result = estimate_parameters(sim.rows, summary_name=None)
    assert set(result.estimates) == {"kt_UW", "kt_Nip", "kt_RW", "kf_UW", "kf_Nip", "kf_RW", "EA"}
    assert result.rmse_theta < 0.20
    assert len(result.error_table) == 7
