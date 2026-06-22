from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _load_config(name: str) -> dict:
    with (ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict)
    return loaded


def test_professor_plant_config_loads_p01_to_p10():
    config = _load_config("plants_p01_p10.yaml")

    plants = config["plants"]
    assert list(plants) == [f"P{i:02d}" for i in range(1, 11)]
    assert plants["P01"]["pool_id"] == "P001"
    assert plants["P09"]["material"] == "Cu"
    assert len(plants["P08"]["R_m"]) == 3
    assert len(plants["P08"]["J_kgm2"]) == 3
    assert len(plants["P08"]["f_Nms_per_rad"]) == 3
    assert len(plants["P08"]["L_m"]) == 3
    assert plants["P08"]["noise_sigma_N_0p3pct_Tmax"] == 9.18


def test_professor_excitation_noise_and_target_configs_load():
    excitations = _load_config("excitation_profiles.yaml")
    noise_lpf = _load_config("noise_lpf.yaml")
    targets = _load_config("paper_targets.yaml")

    assert excitations["common"]["Kp_star"] == 100
    assert excitations["ET1"]["total_duration_s"] == 7.0
    assert excitations["ET3"]["total_duration_s"] == 17.0
    assert excitations["ET6"]["total_duration_s"] == 32.0
    assert excitations["ET3M"]["line_speed_multipliers"] == [0.5, 1.0, 2.0]
    assert excitations["EVR"]["enabled"] is False
    assert excitations["EV1"]["enabled"] is False

    assert noise_lpf["sensor_noise"]["seed"] == 0
    assert noise_lpf["sensor_noise"]["sigma_fraction_of_Tmax"] == 0.003
    assert noise_lpf["low_pass_filter"]["cutoff_Hz"] == 100
    assert noise_lpf["logging"]["NF_Tlog_ms"] == 5
    assert noise_lpf["logging"]["SN_Tlog_ms"] == 20

    assert targets["simulation"]["dt_ms"] == 1
    assert targets["simulation"]["Ts_ms"] == 10
    assert targets["sysid"]["theta_names"] == [
        "kt_UW",
        "kt_Nip",
        "kt_RW",
        "kf_UW",
        "kf_Nip",
        "kf_RW",
        "EA",
    ]
    assert targets["excitation_targets"]["skipped_for_reproduction"] == ["EVR", "EV1"]
