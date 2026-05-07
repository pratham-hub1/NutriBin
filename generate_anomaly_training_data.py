from pathlib import Path

import numpy as np
import pandas as pd


def _sample_anomaly_ranges(
    rng: np.random.Generator,
    low_min: float,
    low_max: float,
    high_min: float,
    high_max: float,
    n_rows: int,
) -> np.ndarray:
    half = n_rows // 2
    low_part = rng.uniform(low_min, low_max, half)
    high_part = rng.uniform(high_min, high_max, n_rows - half)
    values = np.concatenate([low_part, high_part])
    rng.shuffle(values)
    return values


def generate_training_csv(path: str = "data/anomaly_training.csv", total_rows: int = 200, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)

    normal_rows = int(total_rows * 0.80)
    edge_rows = int(total_rows * 0.15)
    anomaly_rows = total_rows - normal_rows - edge_rows

    normal = pd.DataFrame(
        {
            "temperature": rng.uniform(35, 60, normal_rows),
            "moisture": rng.uniform(40, 70, normal_rows),
            "gas": rng.uniform(200, 600, normal_rows),
        }
    )

    edge = pd.DataFrame(
        {
            "temperature": rng.uniform(20, 70, edge_rows),
            "moisture": rng.uniform(20, 90, edge_rows),
            "gas": rng.uniform(100, 800, edge_rows),
        }
    )

    anomaly = pd.DataFrame(
        {
            "temperature": _sample_anomaly_ranges(rng, -10, 19.9, 70.1, 95, anomaly_rows),
            "moisture": _sample_anomaly_ranges(rng, -5, 19.9, 90.1, 120, anomaly_rows),
            "gas": _sample_anomaly_ranges(rng, 0, 99.9, 1000.1, 1500, anomaly_rows),
        }
    )

    df = pd.concat([normal, edge, anomaly], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df = df.round(2)

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False)


if __name__ == "__main__":
    generate_training_csv()
