from app.services.ai.anomaly_detector import predict_anomaly_result


class InferenceService:
    @staticmethod
    def run(current_data: dict | None = None, previous_data: dict | None = None) -> dict:
        anomaly_label = "anomaly"
        anomaly_score = 1.0
        anomaly_severity = "HIGH"
        if current_data is not None:
            anomaly_result = predict_anomaly_result(current_data=current_data, previous_data=previous_data)
            anomaly_label = str(anomaly_result["anomaly_label"])
            anomaly_score = float(anomaly_result["anomaly_score"])
            anomaly_severity = str(anomaly_result["anomaly_severity"])

        return {
            "anomaly_score": anomaly_score,
            "anomaly_label": anomaly_label,
            "anomaly_severity": anomaly_severity,
            "stage_label": None,
            "stage_confidence": None,
            "time_remaining_hours": None,
            "model_version": "iforest_v1",
        }
