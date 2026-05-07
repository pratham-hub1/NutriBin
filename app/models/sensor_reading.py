from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=True, index=True)
    server_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    device_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    moisture_pct: Mapped[float] = mapped_column(Float, nullable=False)
    gas_ppm: Mapped[float] = mapped_column(Float, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(24), nullable=False, default="valid")
    quality_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
