"""Sensor-noise helpers for professor reproduction settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NOISE_CONFIG = PROJECT_ROOT / "configs" / "noise_lpf.yaml"
DEFAULT_PLANT_CONFIG = PROJECT_ROOT / "configs" / "plants_p01_p10.yaml"


@dataclass(frozen=True)
class SensorNoiseConfig:
    """Noise settings from `configs/noise_lpf.yaml`."""

    seed: int
    sigma_fraction_of_Tmax: float
    per_plant_sigma_N: dict[str, float]
    NF_Tlog_ms: int
    SN_Tlog_ms: int


_NOISE_CACHE: dict[tuple[str, tuple[int, ...], int, float], np.ndarray] = {}


def _load_yaml(path: Path) -> Mapping[str, object]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Invalid YAML mapping: {path}")
    return payload


def load_sensor_noise_config(config_path: Path = DEFAULT_NOISE_CONFIG) -> SensorNoiseConfig:
    """Load seed, sigma fraction, per-plant sigmas, and SN/NF Tlog settings."""

    payload = _load_yaml(config_path)
    sensor_noise = payload.get("sensor_noise", {})
    logging = payload.get("logging", {})
    if not isinstance(sensor_noise, Mapping) or not isinstance(logging, Mapping):
        raise ValueError(f"Invalid noise config: {config_path}")

    per_plant = sensor_noise.get("per_plant_sigma_N", {})
    if not isinstance(per_plant, Mapping):
        per_plant = {}

    return SensorNoiseConfig(
        seed=int(sensor_noise.get("seed", 0)),
        sigma_fraction_of_Tmax=float(sensor_noise.get("sigma_fraction_of_Tmax", 0.003)),
        per_plant_sigma_N={str(key): float(value) for key, value in per_plant.items()},
        NF_Tlog_ms=int(logging.get("NF_Tlog_ms", 5)),
        SN_Tlog_ms=int(logging.get("SN_Tlog_ms", 20)),
    )


def _plant_row(plant_id: str, plant_config_path: Path = DEFAULT_PLANT_CONFIG) -> Mapping[str, object]:
    payload = _load_yaml(plant_config_path)
    plants = payload.get("plants", {})
    if not isinstance(plants, Mapping) or plant_id not in plants:
        valid = ", ".join(sorted(str(key) for key in plants)) if isinstance(plants, Mapping) else ""
        raise ValueError(f"Unknown plant_id '{plant_id}'. Valid plants: {valid}.")
    row = plants[plant_id]
    if not isinstance(row, Mapping):
        raise ValueError(f"Invalid plant row for {plant_id}")
    return row


def sigma_for_plant(
    plant_id: str,
    *,
    noise_config_path: Path = DEFAULT_NOISE_CONFIG,
    plant_config_path: Path = DEFAULT_PLANT_CONFIG,
) -> float:
    """Return `sigma = 0.003*T_max` for one plant."""

    config = load_sensor_noise_config(noise_config_path)
    t_max = float(_plant_row(plant_id, plant_config_path)["T_max_N"])
    return config.sigma_fraction_of_Tmax * t_max


def configured_tlog_ms(
    *,
    noise_enabled: bool,
    config_path: Path = DEFAULT_NOISE_CONFIG,
) -> int:
    """Return professor logging period: SN = 20 ms, NF = 5 ms."""

    config = load_sensor_noise_config(config_path)
    return config.SN_Tlog_ms if noise_enabled else config.NF_Tlog_ms


def generate_tension_noise(
    tensions_N: object,
    plant_id: str,
    *,
    config_path: Path = DEFAULT_NOISE_CONFIG,
    plant_config_path: Path = DEFAULT_PLANT_CONFIG,
) -> np.ndarray:
    """Generate one deterministic iid Gaussian noise realization for tensions.

    Noise is additive, per tension channel, and generated with
    `numpy.default_rng(0)`. Values are cached by plant and shape so repeated
    calls for a plant reuse the same realization.
    """

    tensions = np.asarray(tensions_N, dtype=float)
    if tensions.shape == ():
        raise ValueError("tensions_N must be array-like")

    config = load_sensor_noise_config(config_path)
    sigma = sigma_for_plant(
        plant_id,
        noise_config_path=config_path,
        plant_config_path=plant_config_path,
    )
    cache_key = (plant_id, tuple(tensions.shape), config.seed, sigma)
    if cache_key not in _NOISE_CACHE:
        rng = np.random.default_rng(config.seed)
        _NOISE_CACHE[cache_key] = rng.normal(loc=0.0, scale=sigma, size=tensions.shape)
    return _NOISE_CACHE[cache_key].copy()


def add_tension_sensor_noise(
    tensions_N: object,
    plant_id: str,
    *,
    noise_enabled: bool = True,
    config_path: Path = DEFAULT_NOISE_CONFIG,
    plant_config_path: Path = DEFAULT_PLANT_CONFIG,
) -> np.ndarray:
    """Return measured tensions with additive sensor noise."""

    tensions = np.asarray(tensions_N, dtype=float)
    if not noise_enabled:
        return tensions.copy()
    return tensions + generate_tension_noise(
        tensions,
        plant_id,
        config_path=config_path,
        plant_config_path=plant_config_path,
    )


def add_noise_to_measurements(
    tensions_N: object,
    torques_Nm: object,
    plant_id: str,
    *,
    noise_enabled: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Add noise to measured tensions only; motor torque is returned unchanged."""

    noisy_tensions = add_tension_sensor_noise(
        tensions_N,
        plant_id,
        noise_enabled=noise_enabled,
    )
    return noisy_tensions, np.asarray(torques_Nm, dtype=float).copy()
