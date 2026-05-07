from pathlib import Path
from typing import Any

MODEL_PATH = Path("models/anomaly_model.pkl")
REQUIRED_KEYS = ("temperature", "moisture", "gas")
FEATURE_COLUMNS = ["temperature", "moisture", "gas", "temp_change", "moisture_change"]
CALIBRATED_NORMAL_BOUNDS = {
    "temperature": (25.0, 65.0),
    "moisture": (15.0, 85.0),
    "gas": (100.0, 800.0),
}

_cached_model: Any | None = None


def _load_joblib_module():
    try:
        import joblib  # type: ignore
    except ImportError:
        return None
    return joblib


def _to_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_valid_current_data(current_data: dict) -> bool:
    for key in REQUIRED_KEYS:
        if key not in current_data or _to_float(current_data[key]) is None:
            return False
    return True


def _is_valid_previous_data(previous_data: dict | None) -> bool:
    if previous_data is None:
        return False
    for key in REQUIRED_KEYS:
        if key not in previous_data or _to_float(previous_data[key]) is None:
            return False
    return True


def _build_features(current_data: dict, previous_data: dict | None) -> list[float] | None:
    if not _is_valid_current_data(current_data):
        return None

    current_temp = _to_float(current_data["temperature"])
    current_moisture = _to_float(current_data["moisture"])
    current_gas = _to_float(current_data["gas"])
    if current_temp is None or current_moisture is None or current_gas is None:
        return None

    if _is_valid_previous_data(previous_data):
        prev_temp = _to_float(previous_data["temperature"])
        prev_moisture = _to_float(previous_data["moisture"])
        if prev_temp is None or prev_moisture is None:
            temp_change = 0.0
            moisture_change = 0.0
        else:
            temp_change = current_temp - prev_temp
            moisture_change = current_moisture - prev_moisture
    else:
        temp_change = 0.0
        moisture_change = 0.0

    return [current_temp, current_moisture, current_gas, temp_change, moisture_change]


def _passes_hard_rules(current_temp: float, current_moisture: float, current_gas: float) -> bool:
    if current_temp < 0 or current_temp >= 80:
        return False
    if current_moisture < 0 or current_moisture > 100:
        return False
    if current_gas < 0:
        return False
    return True


def _gas_hard_anomaly(gas_ppm: float) -> tuple[str, float, str] | None:
    if gas_ppm > 2000:
        return "anomaly", 0.9, "HIGH"
    if gas_ppm > 1000:
        return "anomaly", 0.7, "MEDIUM"
    return None


def train_model(data: Any) -> Any:
    import pandas as pd
    from sklearn.ensemble import IsolationForest

    frame = data.copy()
    for col in REQUIRED_KEYS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=list(REQUIRED_KEYS))

    normal_mask = (
        (frame["temperature"] >= CALIBRATED_NORMAL_BOUNDS["temperature"][0])
        & (frame["temperature"] <= CALIBRATED_NORMAL_BOUNDS["temperature"][1])
        & (frame["moisture"] >= CALIBRATED_NORMAL_BOUNDS["moisture"][0])
        & (frame["moisture"] <= CALIBRATED_NORMAL_BOUNDS["moisture"][1])
        & (frame["gas"] >= CALIBRATED_NORMAL_BOUNDS["gas"][0])
        & (frame["gas"] <= CALIBRATED_NORMAL_BOUNDS["gas"][1])
    )
    normal_frame = frame.loc[normal_mask].copy()
    if not normal_frame.empty:
        frame = normal_frame

    frame["temp_change"] = frame["temperature"].diff().fillna(0.0)
    frame["moisture_change"] = frame["moisture"].diff().fillna(0.0)

    feature_frame = frame[FEATURE_COLUMNS]
    model: Any = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        max_samples="auto",
    )
    model.fit(feature_frame)
    return model


def save_model(model: Any) -> None:
    joblib = _load_joblib_module()
    if joblib is None:
        raise RuntimeError("joblib is required to save the anomaly model")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)


def load_model() -> Any | None:
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    if not MODEL_PATH.exists():
        return None
    joblib = _load_joblib_module()
    if joblib is None:
        return None
    _cached_model = joblib.load(MODEL_PATH)
    return _cached_model


def predict_anomaly(current_data: dict, previous_data: dict | None = None) -> str:
    return predict_anomaly_result(current_data=current_data, previous_data=previous_data)["anomaly_label"]


def predict_anomaly_result(current_data: dict, previous_data: dict | None = None) -> dict[str, str | float]:
    import pandas as pd

    features = _build_features(current_data, previous_data)
    if features is None:
        return {"anomaly_label": "anomaly", "anomaly_score": 1.0, "anomaly_severity": "HIGH"}

    current_temp, current_moisture, current_gas = features[0], features[1], features[2]
    if not _passes_hard_rules(current_temp, current_moisture, current_gas):
        return {"anomaly_label": "anomaly", "anomaly_score": 1.0, "anomaly_severity": "HIGH"}

    gas_hard_result = _gas_hard_anomaly(current_gas)
    if gas_hard_result is not None:
        label, score, severity = gas_hard_result
        return {"anomaly_label": label, "anomaly_score": score, "anomaly_severity": severity}

    model = load_model()
    if model is None:
        return {"anomaly_label": "anomaly", "anomaly_score": 1.0, "anomaly_severity": "HIGH"}

    feature_frame = pd.DataFrame([features], columns=FEATURE_COLUMNS)
    prediction = model.predict(feature_frame)[0]
    if prediction == -1:
        return {"anomaly_label": "anomaly", "anomaly_score": 1.0, "anomaly_severity": "HIGH"}
    return {"anomaly_label": "normal", "anomaly_score": 0.0, "anomaly_severity": "LOW"}


def map_alert_level(result: str) -> str:
    if result == "anomaly":
        return "HIGH"
    return "NORMAL"
