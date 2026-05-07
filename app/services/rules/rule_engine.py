from typing import Any


def create_recommendation(
    rec_type: str,
    message: str,
    reason: str,
    impact: str,
    severity: str,
    reading_id: int,
) -> dict[str, Any]:
    return {
        "type": rec_type,
        "message": message,
        "reason": reason,
        "impact": impact,
        "severity": severity,
        "reading_id": reading_id,
    }


def generate_recommendations(
    current_data: dict[str, Any],
    anomaly_status: str,
    reading_id: int,
    stage_label: str | None = None,
    time_remaining_hours: float | None = None,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []

    try:
        temp = float(current_data.get("temperature"))
        moisture = float(current_data.get("moisture"))
        gas = float(current_data.get("gas"))
    except (TypeError, ValueError):
        temp, moisture, gas = None, None, None

    if temp is not None and temp > 60:
        recommendations.append(
            create_recommendation(
                "TEMP_HIGH",
                "Aerate compost to reduce heat buildup",
                "Temperature is high during active decomposition phase",
                "May reduce composting time by 4-6 hours",
                "HIGH",
                reading_id,
            )
        )
    elif temp is not None and temp < 35:
        recommendations.append(
            create_recommendation(
                "TEMP_LOW",
                "Increase nitrogen-rich material",
                "Temperature is too low for active microbial activity",
                "Helps initiate faster decomposition",
                "MEDIUM",
                reading_id,
            )
        )

    if moisture is not None and moisture > 70:
        recommendations.append(
            create_recommendation(
                "MOISTURE_HIGH",
                "Add dry material to balance moisture",
                "Excess moisture is limiting oxygen flow",
                "Improves decomposition efficiency and prevents delays",
                "MEDIUM",
                reading_id,
            )
        )
    elif moisture is not None and moisture < 40:
        recommendations.append(
            create_recommendation(
                "MOISTURE_LOW",
                "Add water and mix compost to distribute moisture evenly",
                "Moisture is below optimal range for microbial activity",
                "Supports consistent decomposition and avoids slowdown",
                "MEDIUM",
                reading_id,
            )
        )

    if gas is not None and gas > 500:
        recommendations.append(
            create_recommendation(
                "GAS_HIGH",
                "Improve aeration immediately",
                "Gas concentration is elevated and indicates low oxygen exchange",
                "Reduces odor risk and restores aerobic composting",
                "HIGH",
                reading_id,
            )
        )

    if anomaly_status == "anomaly":
        recommendations.append(
            create_recommendation(
                "ANOMALY_DETECTED",
                "Inspect compost and sensor setup for abnormal behavior",
                "Anomaly detector flagged unusual sensor pattern",
                "Prevents misleading predictions and reduces process risk",
                "HIGH",
                reading_id,
            )
        )

    if not recommendations:
        recommendations.append(
            create_recommendation(
                "MAINTAIN_CONDITIONS",
                "Maintain current conditions",
                "All parameters are within optimal range",
                "Ensures compost continues progressing efficiently",
                "LOW",
                reading_id,
            )
        )

    # Minor explainability tuning for near-ready batches.
    if stage_label == "CURING" and time_remaining_hours is not None and time_remaining_hours <= 48:
        recommendations.append(
            create_recommendation(
                "MAINTAIN_CONDITIONS",
                "Continue gentle aeration and monitor moisture",
                "Compost is in curing stage and nearing readiness",
                "Helps maintain stability and prevent final-stage delays",
                "LOW",
                reading_id,
            )
        )

    return recommendations
