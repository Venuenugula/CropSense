"""
Fetch historical weather (Meteostat) and build ``forecast/weather_dataset.csv`` for ML training.

Run:
  python forecast/build_dataset.py

Requires: ``pip install meteostat pandas numpy``
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
from meteostat import Daily, Hourly, Point

# Telangana — Hyderabad (aligned with ``weather.py`` default)
DEFAULT_LAT = 17.3850
DEFAULT_LON = 78.4867

START = datetime(2022, 1, 1)
END = datetime(2024, 12, 31)

OUT_CSV = os.path.join(os.path.dirname(__file__), "weather_dataset.csv")


def generate_risk(row: pd.Series) -> int:
    """Rule labels (0=LOW, 1=MEDIUM, 2=HIGH) — same idea as original snippet."""
    if row["humidity_avg_3"] > 80 and row["rain_sum_7"] > 20:
        return 2
    if row["humidity_avg_3"] > 60:
        return 1
    return 0


def main() -> None:
    lat = float(os.environ.get("METEOSTAT_LAT", DEFAULT_LAT))
    lon = float(os.environ.get("METEOSTAT_LON", DEFAULT_LON))
    location = Point(lat, lon)

    daily = Daily(location, START, END).fetch()
    if daily is None or daily.empty:
        raise SystemExit("No daily Meteostat data — check coordinates / network.")

    daily = daily.reset_index()
    # Meteostat uses 'time' as first column after reset_index
    time_col = "time" if "time" in daily.columns else daily.columns[0]
    daily = daily.rename(columns={time_col: "time"})
    daily["time"] = pd.to_datetime(daily["time"])

    if "tavg" not in daily.columns:
        raise SystemExit("Expected column 'tavg' in Meteostat Daily — schema changed?")

    daily = daily.rename(columns={"tavg": "temp", "prcp": "rain"})
    daily["rain"] = daily["rain"].fillna(0.0)

    hourly = Hourly(location, START, END).fetch()
    if hourly is not None and not hourly.empty and "rhum" in hourly.columns:
        rhum_d = hourly["rhum"].resample("D").mean()
        daily = daily.set_index("time")
        daily["humidity"] = rhum_d.reindex(daily.index)
        daily = daily.reset_index()
    else:
        # Coarse proxy when hourly rhum unavailable
        t = daily["temp"].astype(float)
        daily["humidity"] = (72 - (t - 22) * 1.2).clip(35, 98)

    daily["temp"] = daily["temp"].astype(float)
    daily["humidity"] = daily["humidity"].astype(float)

    daily = daily.ffill().bfill()

    daily["temp_avg_3"] = daily["temp"].rolling(3, min_periods=1).mean()
    daily["humidity_avg_3"] = daily["humidity"].rolling(3, min_periods=1).mean()
    daily["rain_sum_7"] = daily["rain"].rolling(7, min_periods=1).sum()
    daily["temp_trend"] = daily["temp"].diff()
    daily["humidity_trend"] = daily["humidity"].diff()

    daily = daily.dropna(subset=["temp", "humidity", "rain", "temp_trend", "humidity_trend"])
    daily["risk"] = daily.apply(generate_risk, axis=1)

    keep = [
        "time",
        "temp",
        "humidity",
        "rain",
        "temp_avg_3",
        "humidity_avg_3",
        "rain_sum_7",
        "temp_trend",
        "humidity_trend",
        "risk",
    ]
    daily = daily[keep]
    daily.to_csv(OUT_CSV, index=False)
    print("Dataset created:", daily.shape, "→", OUT_CSV)
    print(daily["risk"].value_counts().sort_index())


if __name__ == "__main__":
    main()
