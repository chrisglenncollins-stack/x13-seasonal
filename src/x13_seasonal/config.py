"""Configuration for X-13ARIMA-SEATS seasonal adjustment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class X13Config:
    """Configuration for the X-13ARIMA-SEATS seasonal adjustment wrapper.

    Attributes:
        binary_path: Path to the x13as binary.
            Defaults to $X13AS_PATH or /usr/local/bin/x13as.
        span_years: Number of recent years of data to use.
        min_observations: Minimum observations required to run X-13.
        interventions: Regression spec string for interventions (e.g. COVID).
            Set to None to disable interventions entirely.
        timeout_seconds: Subprocess timeout for the x13as call.
        transform: Transform function — "auto", "log", or "none".
    """

    binary_path: str = field(
        default_factory=lambda: os.environ.get("X13AS_PATH", "/usr/local/bin/x13as")
    )
    span_years: int = 8
    min_observations: int = 36
    interventions: Optional[str] = (
        "regression{\n"
        "  variables = (Rp2020.03-2020.05 LS2020.06)\n"
        "}\n"
    )
    timeout_seconds: int = 60
    transform: str = "auto"
