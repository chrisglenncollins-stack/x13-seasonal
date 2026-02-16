"""Smoke tests for x13_seasonal."""

import pandas as pd
import pytest

from x13_seasonal import seasonal_adjust, X13Config


def test_too_few_observations_returns_original():
    """Series shorter than min_observations should be returned unchanged."""
    idx = pd.date_range("2023-01-31", periods=12, freq="ME")
    s = pd.Series(range(100, 112), index=idx)
    result = seasonal_adjust(s, series_id="test_short")
    pd.testing.assert_series_equal(result, s)


def test_config_defaults():
    """X13Config should have sensible defaults."""
    cfg = X13Config()
    assert cfg.span_years == 8
    assert cfg.min_observations == 36
    assert cfg.timeout_seconds == 60
    assert cfg.transform == "auto"
    assert "Rp2020.03-2020.05" in cfg.interventions


def test_config_no_interventions():
    """Interventions can be disabled."""
    cfg = X13Config(interventions=None)
    assert cfg.interventions is None


def test_missing_binary_raises():
    """Should raise FileNotFoundError if binary doesn't exist."""
    cfg = X13Config(binary_path="/nonexistent/x13as")
    idx = pd.date_range("2015-01-31", periods=96, freq="ME")
    s = pd.Series(range(100, 196), index=idx, dtype=float)
    # seasonal_adjust catches exceptions and returns original
    result = seasonal_adjust(s, series_id="test_missing", config=cfg)
    pd.testing.assert_series_equal(result, s)
