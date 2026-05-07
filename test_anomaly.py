from app.services.ai.anomaly_detector import map_alert_level, predict_anomaly


def _run_case(current_data: dict, expected: str) -> None:
    result = predict_anomaly(current_data=current_data, previous_data=None)
    alert = map_alert_level(result)
    assert result == expected
    assert alert == ("HIGH" if result == "anomaly" else "NORMAL")
    print({"input": current_data, "result": result, "alert": alert})


def main() -> None:
    normal_cases = [
        {"temperature": 45, "moisture": 60, "gas": 300},
        {"temperature": 50, "moisture": 55, "gas": 400},
    ]
    anomaly_cases = [
        {"temperature": 80, "moisture": 60, "gas": 300},
        {"temperature": 40, "moisture": 10, "gas": 200},
        {"temperature": 45, "moisture": 60, "gas": 1200},
    ]

    for case in normal_cases:
        _run_case(case, "normal")

    for case in anomaly_cases:
        _run_case(case, "anomaly")


if __name__ == "__main__":
    main()
