"""Generators for professor-provided excitation profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .profiles import CHANNEL_INDEX, DEFAULT_CONFIG, OperatingPoint, get_profile, load_profiles


def _tref3(t_ref_N: float | Sequence[float]) -> tuple[float, float, float]:
    if isinstance(t_ref_N, (int, float)):
        value = float(t_ref_N)
        return (value, value, value)
    if len(t_ref_N) != 3:
        raise ValueError("t_ref_N must be a scalar or contain exactly 3 values")
    return tuple(float(value) for value in t_ref_N)  # type: ignore[return-value]


def tension_reference_delta(
    profile_name: str,
    t_s: float,
    t_ref_N: float | Sequence[float],
    *,
    exact_mode: bool = True,
    config_path: Path = DEFAULT_CONFIG,
) -> tuple[float, float, float]:
    """Return `[dTref_UW, dTref_Nip, dTref_RW]` at time `t_s`.

    Active steps are `+20%` of the corresponding channel's `T_ref`.
    """

    profile = get_profile(profile_name, exact_mode=exact_mode, config_path=config_path)
    refs = _tref3(t_ref_N)
    delta = [0.0, 0.0, 0.0]

    for channel, start_s in profile.step_up_times_s.items():
        channel_index = CHANNEL_INDEX[channel]
        stop_s = profile.step_down_times_s.get(channel)
        active = t_s >= start_s if stop_s is None else start_s <= t_s < stop_s
        if active:
            delta[channel_index] = profile.step_fraction_of_Tref * refs[channel_index]

    return (delta[0], delta[1], delta[2])


def generate_et3m_operating_points(
    v_ref_mps: float,
    *,
    config_path: Path = DEFAULT_CONFIG,
) -> list[OperatingPoint]:
    """Return the three ET3M operating points with line-speed multipliers."""

    profiles = load_profiles(config_path)
    raw = profiles["ET3M"]
    if raw.skipped:
        return []

    # Keep these values explicit because they are professor-provided reproduction details.
    multipliers = [0.5, 1.0, 2.0]
    return [
        OperatingPoint(
            profile_name="ET3",
            line_speed_multiplier=multiplier,
            v_ref_mps=float(v_ref_mps) * multiplier,
        )
        for multiplier in multipliers
    ]
