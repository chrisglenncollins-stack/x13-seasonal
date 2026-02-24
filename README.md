# x13-seasonal

Python wrapper for [X-13ARIMA-SEATS](https://www.census.gov/data/software/x13as.html) seasonal adjustment. Pass in a pandas Series with a DatetimeIndex of monthly values and get back a seasonally adjusted Series.

## Prerequisites

You need the **x13as** binary installed on your system. Download it from the [U.S. Census Bureau](https://www.census.gov/data/software/x13as.html).

By default the wrapper looks for the binary at `/usr/local/bin/x13as`. Override this with the `X13AS_PATH` environment variable or via `X13Config.binary_path`.

## Installation

```bash
pip install -e .
```

## Usage

```python
import pandas as pd
from x13_seasonal import seasonal_adjust, X13Config

# Monthly NSA price index with DatetimeIndex
series = pd.Series(
    [100.0, 101.2, 102.5, ...],
    index=pd.date_range("2016-01-31", periods=96, freq="ME"),
)

# Run with defaults (8-year window, auto transform, COVID interventions)
sa = seasonal_adjust(series, series_id="my_index")

# Or customize configuration
config = X13Config(
    span_years=10,
    transform="log",
    interventions=None,  # disable COVID intervention variables
)
sa = seasonal_adjust(series, series_id="my_index", config=config)
```

If X-13 fails for any reason (missing binary, too few observations, model failure), the original series is returned unchanged.

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `binary_path` | `$X13AS_PATH` or `/usr/local/bin/x13as` | Path to x13as binary |
| `span_years` | 8 | Number of recent years to use |
| `min_observations` | 36 | Minimum observations required |
| `interventions` | COVID regressors (2020.03–2020.06) | Regression spec string, or `None` to disable |
| `timeout_seconds` | 60 | Subprocess timeout |
| `transform` | `"auto"` | Transform function: `"auto"`, `"log"`, or `"none"` |

## Testing

```bash
pip install -e ".[test]"
pytest tests/
```
