from datetime import datetime

from sqlalchemy import Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    ts: Mapped[datetime] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(Text, primary_key=True)
    temp_f: Mapped[float | None] = mapped_column(Numeric)
    hdd: Mapped[float | None] = mapped_column(Numeric)
    cdd: Mapped[float | None] = mapped_column(Numeric)
    precip_in: Mapped[float | None] = mapped_column(Numeric)
    anomaly_f: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="mock")


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    ts: Mapped[datetime] = mapped_column(primary_key=True)
    issued_at: Mapped[datetime] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(Text, primary_key=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    temp_f: Mapped[float | None] = mapped_column(Numeric)
    hdd: Mapped[float | None] = mapped_column(Numeric)
    cdd: Mapped[float | None] = mapped_column(Numeric)
    anomaly_f: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="mock")
