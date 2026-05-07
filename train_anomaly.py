import pandas as pd

from app.services.ai.anomaly_detector import save_model, train_model


def main() -> None:
    data = pd.read_csv("data/anomaly_training.csv")
    model = train_model(data)
    save_model(model)


if __name__ == "__main__":
    main()
