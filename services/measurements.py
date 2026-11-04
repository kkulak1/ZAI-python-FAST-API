from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from database.models import Measurement, Sensor


def validate_measurement_value(sensor: Sensor, value: float) -> None:
    if not sensor.series or not sensor.series.min_value <= value <= sensor.series.max_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Measurement value is outside the series range",
        )


def validate_timestamp(timestamp: datetime | None) -> datetime:
    current = datetime.now(timezone.utc)
    if timestamp is None:
        return current
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if timestamp > current.replace(microsecond=0):
        from datetime import timedelta

        if timestamp > current + timedelta(minutes=5):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Timestamp cannot be more than 5 minutes in the future",
            )
    return timestamp


def list_measurements(
    db: Session,
    series_ids: list[int],
    from_time: datetime | None,
    to_time: datetime | None,
    descending: bool,
    limit: int,
) -> list[Measurement]:
    query: Select[Measurement] = select(Measurement).options(joinedload(Measurement.sensor))
    if series_ids:
        query = query.where(Measurement.series_id.in_(series_ids))
    if from_time is not None:
        query = query.where(Measurement.timestamp >= from_time)
    if to_time is not None:
        query = query.where(Measurement.timestamp <= to_time)
    ordering = Measurement.timestamp.desc() if descending else Measurement.timestamp.asc()
    return list(db.scalars(query.order_by(ordering).limit(limit)).all())
