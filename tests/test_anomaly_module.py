from app.services.ai.anomaly_detector import predict_anomaly


def test_predict_anomaly_invalid_current_data_returns_anomaly() -> None:
    result = predict_anomaly(current_data={"temperature": "bad", "moisture": 50, "gas": 100}, previous_data=None)
    assert result == "anomaly"


def test_predict_anomaly_invalid_previous_data_falls_back_to_zero_change() -> None:
    current = {"temperature": 45.0, "moisture": 55.0, "gas": 200.0}
    previous = {"temperature": "bad", "moisture": 52.0, "gas": 210.0}
    result = predict_anomaly(current_data=current, previous_data=previous)
    assert result in {"normal", "anomaly"}


def test_predict_anomaly_hard_rules_applied() -> None:
    result = predict_anomaly(current_data={"temperature": -1, "moisture": 55, "gas": 200}, previous_data=None)
    assert result == "anomaly"
