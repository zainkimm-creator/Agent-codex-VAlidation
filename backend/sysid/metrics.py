"""SysID metrics for parameter-estimation reports."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from backend.models.equations import PARAMETER_NAMES
from backend.sysid.cost import theta_array, theta_dict


def rmse_theta(
    theta_est: Mapping[str, float] | Sequence[float],
    theta_true: Mapping[str, float] | Sequence[float],
) -> float:
    """Return root-mean-square relative parameter error.

    `RMSE_theta = sqrt(mean(((theta_est_i - theta_true_i)/theta_true_i)^2))`
    """

    estimate = theta_array(theta_est)
    truth = theta_array(theta_true)
    denominators = np.where(np.abs(truth) > 1e-12, np.abs(truth), 1.0)
    relative = (estimate - truth) / denominators
    return float(math.sqrt(float(np.mean(relative * relative))))


def parameter_error_table(
    theta_est: Mapping[str, float] | Sequence[float],
    theta_true: Mapping[str, float] | Sequence[float],
) -> list[dict[str, float | str]]:
    """Return per-parameter estimate, truth, absolute error, and relative error."""

    estimates = theta_dict(theta_est)
    truths = theta_dict(theta_true)
    rows: list[dict[str, float | str]] = []
    for name in PARAMETER_NAMES:
        estimate = estimates[name]
        truth = truths[name]
        denom = abs(truth) if abs(truth) > 1e-12 else 1.0
        rows.append(
            {
                "parameter": name,
                "estimate": estimate,
                "truth": truth,
                "absolute_error": estimate - truth,
                "relative_error": (estimate - truth) / denom,
            }
        )
    return rows
