import os
import time
from datetime import datetime, timezone

import httpx


INGEST_URL = os.getenv("NUTRIBIN_INGEST_URL", "http://127.0.0.1:8000/api/v1/ingest/v1/readings")
DEVICE_ID = os.getenv("NUTRIBIN_DEVICE_ID", "ESP32_BIN_01")
DEVICE_KEY = os.getenv("NUTRIBIN_DEVICE_KEY", "nutribin-dev-key")
SEND_INTERVAL_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 10


def read_sensor_values() -> tuple[float, float, float]:
    """
    Replace this with real sensor reads on device:
    returns (temperature_c, moisture_pct, gas_ppm).
    """
    return 45.0, 55.0, 300.0


def build_payload() -> dict:
    temperature_c, moisture_pct, gas_ppm = read_sensor_values()
    return {
        "device_id": DEVICE_ID,
        "device_timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": float(temperature_c),
        "moisture_pct": float(moisture_pct),
        "gas_ppm": float(gas_ppm),
    }


def send_once() -> None:
    payload = build_payload()
    headers = {"X-Device-Key": DEVICE_KEY}
    httpx.post(INGEST_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)


def run_forever() -> None:
    next_run = time.monotonic()
    while True:
        now = time.monotonic()
        sleep_for = next_run - now
        if sleep_for > 0:
            time.sleep(sleep_for)

        try:
            send_once()
        except Exception:
            pass

        next_run += SEND_INTERVAL_SECONDS


if __name__ == "__main__":
    run_forever()
