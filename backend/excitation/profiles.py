"""Professor-provided excitation profile metadata.

The profiles represent tension-reference steps for exact paper reproduction.
Step amplitudes are plant dependent: each active channel receives `+20%` of
that channel's `T_ref`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "excitation_profiles.yaml"

CHANNELS = ("UW", "Nip", "RW")
CHANNEL_INDEX = {name: index for index, name in enumerate(CHANNELS)}


class SkippedExcitationError(ValueError):
    """Raised when a skipped profile is requested for exact reproduction."""


@dataclass(frozen=True)
class ExcitationProfile:
    """One paper excitation profile."""

    name: str
    enabled: bool
    total_duration_s: float | None
    step_fraction_of_Tref: float
    step_up_times_s: Mapping[str, float]
    step_down_times_s: Mapping[str, float]
    skip_reason: str | None = None

    @property
    def skipped(self) -> bool:
        return not self.enabled


@dataclass(frozen=True)
class OperatingPoint:
    """One ET3M operating point."""

    profile_name: str
    line_speed_multiplier: float
    v_ref_mps: float


def _as_float_map(values: object) -> dict[str, float]:
    if not isinstance(values, Mapping):
        return {}
    return {str(key): float(value) for key, value in values.items()}


def load_profiles(config_path: Path = DEFAULT_CONFIG) -> dict[str, ExcitationProfile]:
    """Load excitation profiles from the professor-details YAML config."""

    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Invalid excitation config: {config_path}")

    common = payload.get("common", {})
    if not isinstance(common, Mapping):
        common = {}
    step_fraction = float(common.get("tension_step_fraction_of_Tref", 0.20))

    profiles: dict[str, ExcitationProfile] = {}
    for name in ("ET1", "ET3", "ET6", "ET3M", "EV1", "EVR"):
        raw = payload.get(name, {})
        if not isinstance(raw, Mapping):
            raw = {}
        enabled = bool(raw.get("enabled", False))
        total_duration = raw.get("total_duration_s")
        step_up = _as_float_map(raw.get("step_up_times_s") or raw.get("step_times_s"))
        step_down = _as_float_map(raw.get("step_down_times_s"))

        profiles[name] = ExcitationProfile(
            name=name,
            enabled=enabled,
            total_duration_s=float(total_duration) if total_duration is not None else None,
            step_fraction_of_Tref=step_fraction,
            step_up_times_s=step_up,
            step_down_times_s=step_down,
            skip_reason=str(raw["skip_reason"]) if "skip_reason" in raw else None,
        )
    return profiles


def get_profile(
    name: str,
    *,
    exact_mode: bool = True,
    config_path: Path = DEFAULT_CONFIG,
) -> ExcitationProfile:
    """Return one profile, enforcing exact-mode skip decisions."""

    normalized = name.strip()
    profiles = load_profiles(config_path)
    if normalized not in profiles:
        valid = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown excitation profile '{name}'. Valid profiles: {valid}.")

    profile = profiles[normalized]
    if exact_mode and profile.skipped:
        reason = profile.skip_reason or "Profile is disabled for exact reproduction."
        raise SkippedExcitationError(f"{normalized} is skipped in exact mode: {reason}")
    return profile


def is_skipped_exact(name: str, config_path: Path = DEFAULT_CONFIG) -> bool:
    """Return whether a profile is disabled for exact reproduction."""

    profiles = load_profiles(config_path)
    profile = profiles[name.strip()]
    return profile.skipped
