class ValidationService:
    @staticmethod
    def classify_reading(temperature_c: float, moisture_pct: float, gas_ppm: float) -> tuple[str, list[str]]:
        reasons: list[str] = []
        status = "valid"

        if temperature_c < 0 or temperature_c > 80:
            reasons.append("temperature_out_of_range")
        if moisture_pct < 0 or moisture_pct > 100:
            reasons.append("moisture_out_of_range")
        if gas_ppm < 0 or gas_ppm > 10000:
            reasons.append("gas_out_of_range")

        if reasons:
            status = "invalid"

        return status, reasons
