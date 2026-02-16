"""X-13ARIMA-SEATS seasonal adjustment wrapper.

Calls the X-13 binary to seasonally adjust NSA time series.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from x13_seasonal.config import X13Config

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = X13Config()


def seasonal_adjust(
    index_series: pd.Series,
    series_id: str = "",
    config: X13Config | None = None,
) -> pd.Series:
    """Seasonally adjust an NSA price index using X-13ARIMA-SEATS.

    Writes a temporary .dat + .spc file, runs x13as, and parses the
    X-11 d11 (seasonally adjusted) output.

    Args:
        index_series: DatetimeIndex-indexed Series of raw index levels.
        series_id: Optional identifier for logging.
        config: X13Config with tuning parameters. Uses defaults if None.

    Returns:
        Seasonally adjusted Series with the same index.
        On failure, returns the original series unchanged.
    """
    if config is None:
        config = _DEFAULT_CONFIG

    if len(index_series) < config.min_observations:
        logger.debug(
            "X-13: too few observations (%d) for %s, skipping",
            len(index_series), series_id,
        )
        return index_series

    s = index_series.sort_index().copy()

    # Drop NaN and deduplicate (keep last value for each date)
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")]

    # Use most recent N years
    cutoff = s.index.max() - pd.DateOffset(years=config.span_years)
    s = s[s.index >= cutoff]

    if len(s) < config.min_observations:
        logger.debug(
            "X-13: too few observations after %dyr trim (%d) for %s",
            config.span_years, len(s), series_id,
        )
        return index_series

    # X-13 requires contiguous monthly data — fill gaps via interpolation
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq="ME")
    if len(full_idx) > len(s):
        n_gaps = len(full_idx) - len(s)
        s = s.reindex(full_idx).interpolate(method="linear")
        logger.debug("X-13: interpolated %d missing months for %s", n_gaps, series_id)

    try:
        sa_values = _run_x13(s, series_id, config)
    except Exception as e:
        logger.warning("X-13 failed for %s: %s — using unadjusted", series_id, e)
        return index_series

    # Map SA values back to the original full index
    # sa_values covers the N-yr window; for dates outside it, keep original
    result = index_series.copy()
    for dt in sa_values.index:
        if dt in result.index:
            result[dt] = sa_values[dt]

    return result


def _run_x13(series: pd.Series, series_id: str, config: X13Config) -> pd.Series:
    """Execute X-13 and parse the d11 output."""
    if not Path(config.binary_path).exists():
        raise FileNotFoundError(f"X-13 binary not found at {config.binary_path}")

    with tempfile.TemporaryDirectory(prefix="x13_") as tmpdir:
        base = Path(tmpdir) / "input"

        # Write data file (free format: one value per line, chronological)
        dat_path = base.with_suffix(".dat")
        with open(dat_path, "w") as f:
            for val in series.values:
                f.write(f"  {val:.6f}\n")

        # Determine span
        start_ym = f"{series.index.min().year}.{series.index.min().month}"

        # Build intervention block
        intervention_block = config.interventions if config.interventions else ""

        # Write spec file
        spc_path = base.with_suffix(".spc")
        spc_content = (
            f"series{{\n"
            f"  file = \"{dat_path}\"\n"
            f"  period = 12\n"
            f"  start = {start_ym}\n"
            f"}}\n"
            f"transform{{\n"
            f"  function = {config.transform}\n"
            f"}}\n"
            f"automdl{{}}\n"
            f"{intervention_block}"
            f"x11{{\n"
            f"  save = (d11)\n"
            f"}}\n"
        )
        with open(spc_path, "w") as f:
            f.write(spc_content)

        # Run X-13
        result = subprocess.run(
            [config.binary_path, str(base)],
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=tmpdir,
        )

        if result.returncode != 0:
            logger.debug("X-13 stderr for %s: %s", series_id, result.stderr[:500])

        # Parse d11 output
        d11_path = base.with_suffix(".d11")
        if not d11_path.exists():
            raise RuntimeError(
                f"X-13 did not produce d11 output for {series_id}. "
                f"stderr: {result.stderr[:300]}"
            )

        return _parse_d11(d11_path)


def _parse_d11(path: Path) -> pd.Series:
    """Parse X-13 d11 file (seasonally adjusted series).

    Format: lines of "YYYYMM  value" after a header section.
    Values are in scientific or fixed-point notation.
    """
    dates = []
    values = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            # Match lines like "202301  123.456789" or "202301  1.234568E+02"
            m = re.match(r"(\d{4})(\d{2})\s+([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)", line)
            if m:
                year, month, val = int(m.group(1)), int(m.group(2)), float(m.group(3))
                if 1 <= month <= 12:
                    dt = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
                    dates.append(dt)
                    values.append(val)

    if not dates:
        raise RuntimeError(f"No data parsed from d11 file: {path}")

    return pd.Series(values, index=pd.DatetimeIndex(dates), name="sa_value")
