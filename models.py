from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

import bcrypt
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, event, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, validates

from database import Base


def hash_password(password: str) -> str:
    """Return a bcrypt hash suitable for storing in ``User.password_hash``."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def hash_api_key(api_key: str) -> str:
    """Return the SHA-256 digest of an API key; never persist the clear-text key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Series(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    sensors: Mapped[list[Sensor]] = relationship(
        back_populates="series",
        cascade="all, delete-orphan",
    )


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), nullable=False, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    series: Mapped[Series] = relationship(back_populates="sensors")
    measurements: Mapped[list[Measurement]] = relationship(
        back_populates="sensor",
        cascade="all, delete-orphan",
    )

    @validates("api_key_hash")
    def validate_api_key_hash(self, key: str, value: str) -> str:
        """Allow only a canonical 64-character SHA-256 hexadecimal digest."""
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("api_key_hash must be a lowercase SHA-256 hexadecimal digest")
        return value


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"), nullable=False, index=True)

    sensor: Mapped[Sensor] = relationship(back_populates="measurements")

    @property
    def series_id(self) -> int:
        return self.sensor.series_id


def _validate_measurement_range(
    mapper: Any,
    connection: Any,
    target: Measurement,
) -> None:
    """Reject measurements outside the range configured for their series."""
    bounds = connection.execute(
        select(Series.min_value, Series.max_value)
        .join(Sensor, Sensor.series_id == Series.id)
        .where(Sensor.id == target.sensor_id)
    ).one_or_none()

    if bounds is None:
        raise ValueError(f"Sensor {target.sensor_id} does not exist")
    if not bounds.min_value <= target.value <= bounds.max_value:
        raise ValueError(
            f"Measurement value {target.value} is outside the series range "
            f"[{bounds.min_value}, {bounds.max_value}]"
        )


event.listen(Measurement, "before_insert", _validate_measurement_range)
event.listen(Measurement, "before_update", _validate_measurement_range)
