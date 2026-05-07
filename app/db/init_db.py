from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_api_key
from app.db.base import Base
from app.db.session import engine
from app.models import Alert, Batch, Device, ModelPrediction, Recommendation, SensorReading, SystemLog


def _seed_default_device(db: Session) -> None:
    existing = db.query(Device).filter(Device.device_id == settings.DEFAULT_DEVICE_ID).first()
    if existing:
        return

    db.add(
        Device(
            device_id=settings.DEFAULT_DEVICE_ID,
            name=settings.DEFAULT_DEVICE_NAME,
            api_key_hash=hash_api_key(settings.DEFAULT_DEVICE_API_KEY),
        )
    )
    db.commit()


def init_db() -> None:
    # Import references above ensure all models are registered before create_all.
    _ = (Alert, Batch, Device, ModelPrediction, Recommendation, SensorReading, SystemLog)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        _seed_default_device(db)
