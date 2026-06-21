"""Paper excitation profile definitions and generators."""

from .generators import (
    generate_et3m_operating_points,
    tension_reference_delta,
)
from .profiles import (
    CHANNELS,
    ExcitationProfile,
    OperatingPoint,
    SkippedExcitationError,
    get_profile,
    is_skipped_exact,
)

__all__ = [
    "CHANNELS",
    "ExcitationProfile",
    "OperatingPoint",
    "SkippedExcitationError",
    "generate_et3m_operating_points",
    "get_profile",
    "is_skipped_exact",
    "tension_reference_delta",
]
