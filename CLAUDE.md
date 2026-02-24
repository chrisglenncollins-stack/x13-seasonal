# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python wrapper for X-13ARIMA-SEATS seasonal adjustment. Takes a pandas Series with a DatetimeIndex (monthly NSA price index) and returns a seasonally adjusted Series by shelling out to the `x13as` binary via temp files.

## Commands

```bash
# Install package in dev mode with test deps
pip install -e ".[test]"

# Run all tests
pytest tests/

# Run a single test
pytest tests/test_core.py::test_config_defaults -v
```

## Architecture

The package has two modules under `src/x13_seasonal/`:

- **config.py** — `X13Config` dataclass. Controls binary path (defaults to `$X13AS_PATH` or `/usr/local/bin/x13as`), span window, min observations, intervention variables, timeout, and transform function.
- **core.py** — Three functions:
  - `seasonal_adjust()` — Public API. Preprocesses the series (sort, dedup, drop NaN, trim to N-year window, interpolate monthly gaps), calls `_run_x13()`, maps results back to the original index. Returns original series unchanged on any failure.
  - `_run_x13()` — Writes `.dat` and `.spc` temp files, runs `x13as` via subprocess, parses the `.d11` output.
  - `_parse_d11()` — Reads X-13's d11 output format (YYYYMM + value lines, supports scientific notation).

Key design decisions:
- Graceful degradation: failures log warnings and return the original series rather than raising.
- Monthly frequency only; gaps are linearly interpolated before passing to X-13.
- Default config includes COVID intervention variables (`Rp2020.03-2020.05 LS2020.06`).
