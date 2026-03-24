"""
Train XGBoost on ``forecast/weather_dataset.csv`` → ``forecast/risk_model.pkl``.

Run:
  python forecast/build_dataset.py
  python forecast/train_model.py
"""
from __future__ import annotations

import os

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ROOT = os.path.dirname(__file__)
DATA_CSV = os.path.join(ROOT, "weather_dataset.csv")
MODEL_PATH = os.path.join(ROOT, "risk_model.pkl")

FEATURES = [
    "temp",
    "humidity",
    "rain",
    "temp_avg_3",
    "humidity_avg_3",
    "rain_sum_7",
    "temp_trend",
    "humidity_trend",
]


def main() -> None:
    if not os.path.isfile(DATA_CSV):
        raise SystemExit(f"Missing {DATA_CSV} — run python forecast/build_dataset.py first.")

    data = pd.read_csv(DATA_CSV)
    X = data[FEATURES]
    y = data["risk"]

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        random_state=42,
    )
    model.fit(X_train, y_train)
    acc = float((model.predict(X_test) == y_test).mean())
    print(f"Holdout accuracy: {acc:.3f}")

    joblib.dump(model, MODEL_PATH)
    print("Saved:", MODEL_PATH)


if __name__ == "__main__":
    main()
