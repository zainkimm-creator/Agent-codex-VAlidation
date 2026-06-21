"""Low-pass filtering for noisy measured tensions."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NOISE_CONFIG = PROJECT_ROOT / "configs" / "noise_lpf.yaml"


def load_lpf_cutoff_hz(config_path: Path = DEFAULT_NOISE_CONFIG) -> float:
    """Load the first-order LPF cutoff frequency from config."""

    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Invalid noise/LPF config: {config_path}")
    low_pass = payload.get("low_pass_filter", {})
    if not isinstance(low_pass, Mapping):
        raise ValueError(f"Invalid low_pass_filter section: {config_path}")
    return float(low_pass.get("cutoff_Hz", 100.0))


def first_order_lpf(
    data: object,
    *,
    sample_time_s: float,
    cutoff_hz: float = 100.0,
) -> np.ndarray:
    """Apply a causal first-order low-pass filter along axis 0.

    The discretization uses the matched-pole form
    `alpha = 1 - exp(-2*pi*fc*dt)`.
    """

    if sample_time_s <= 0 or not math.isfinite(sample_time_s):
        raise ValueError("sample_time_s must be finite and positive")
    if cutoff_hz <= 0 or not math.isfinite(cutoff_hz):
        raise ValueError("cutoff_hz must be finite and positive")

    values = np.asarray(data, dtype=float)
    if values.shape == ():
        raise ValueError("data must be array-like")
    if values.shape[0] == 0:
        return values.copy()

    filtered = np.empty_like(values, dtype=float)
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz * sample_time_s)
    filtered[0] = values[0]
    for index in range(1, values.shape[0]):
        filtered[index] = filtered[index - 1] + alpha * (values[index] - filtered[index - 1])
    return filtered


def apply_configured_lpf(
    noisy_tensions_N: object,
    *,
    sample_time_s: float,
    config_path: Path = DEFAULT_NOISE_CONFIG,
) -> np.ndarray:
    """Apply the configured 100 Hz first-order LPF after sensor noise."""

    return first_order_lpf(
        noisy_tensions_N,
        sample_time_s=sample_time_s,
        cutoff_hz=load_lpf_cutoff_hz(config_path),
    )
