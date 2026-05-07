from app.services.rules.rule_engine import generate_recommendations


def test_normal_case_returns_default_recommendation() -> None:
    items = generate_recommendations(
        current_data={"temperature": 45.0, "moisture": 55.0, "gas": 300.0},
        anomaly_status="normal",
        reading_id=1,
    )
    assert len(items) == 1
    assert items[0]["type"] == "MAINTAIN_CONDITIONS"
    assert items[0]["severity"] == "LOW"
    assert items[0]["reason"] == "All parameters are within optimal range"
    assert items[0]["impact"] == "Ensures compost continues progressing efficiently"


def test_single_condition_temp_low() -> None:
    items = generate_recommendations(
        current_data={"temperature": 30.0, "moisture": 55.0, "gas": 300.0},
        anomaly_status="normal",
        reading_id=2,
    )
    assert len(items) == 1
    assert items[0]["type"] == "TEMP_LOW"
    assert items[0]["severity"] == "MEDIUM"
    assert items[0]["message"] == "Increase nitrogen-rich material"


def test_multiple_conditions_temp_and_moisture() -> None:
    items = generate_recommendations(
        current_data={"temperature": 65.0, "moisture": 35.0, "gas": 300.0},
        anomaly_status="normal",
        reading_id=3,
    )
    rec_types = {item["type"] for item in items}
    assert rec_types == {"TEMP_HIGH", "MOISTURE_LOW"}


def test_anomaly_only_case() -> None:
    items = generate_recommendations(
        current_data={"temperature": 45.0, "moisture": 55.0, "gas": 300.0},
        anomaly_status="anomaly",
        reading_id=4,
    )
    assert len(items) == 1
    assert items[0]["type"] == "ANOMALY_DETECTED"
    assert items[0]["severity"] == "HIGH"
    assert items[0]["reason"] == "Anomaly detector flagged unusual sensor pattern"


def test_all_conditions_triggered() -> None:
    items = generate_recommendations(
        current_data={"temperature": 65.0, "moisture": 35.0, "gas": 700.0},
        anomaly_status="anomaly",
        reading_id=5,
    )
    rec_types = {item["type"] for item in items}
    assert rec_types == {"TEMP_HIGH", "MOISTURE_LOW", "GAS_HIGH", "ANOMALY_DETECTED"}
