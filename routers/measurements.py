"""Measurement ingestion and public query endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.models import Measurement as MeasurementModel
from schemas import Measurement, MeasurementInput
from services.dependencies import DbSession
from services.measurements import (
    list_measurements,
    validate_measurement_value,
    validate_timestamp,
)
from services.security import verify_sensor_api_key

router = APIRouter(prefix="/api/measurements", tags=["measurements"])


def to_schema(measurement: MeasurementModel) -> Measurement:
    return Measurement(
        id=measurement.id,
        seriesId=measurement.sensor.series_id,
        sensorId=measurement.sensor_id,
        value=measurement.value,
        timestamp=measurement.timestamp,
    )


def parse_series_filter(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        series_ids = [int(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="series must be comma-separated IDs") from exc
    if any(series_id <= 0 for series_id in series_ids):
        raise HTTPException(status_code=400, detail="series IDs must be positive")
    return series_ids


@router.get("", response_model=list[Measurement])
def get_measurements(
    db: DbSession,
    series: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    sort: Literal["timestamp", "-timestamp"] = Query(default="timestamp"),
    limit: int = Query(default=1000, ge=1, le=10000),
) -> list[Measurement]:
    if from_ is not None and to is not None and from_ > to:
        raise HTTPException(status_code=400, detail="from must not be later than to")
    results = list_measurements(
        db,
        parse_series_filter(series),
        from_,
        to,
        descending=sort == "-timestamp",
        limit=limit,
    )
    return [to_schema(item) for item in results]


@router.get("/{measurementId}", response_model=Measurement)
def get_measurement(measurementId: int, db: DbSession) -> Measurement:
    measurement_id = measurementId
    measurement = db.scalar(
        select(MeasurementModel)
        .options(joinedload(MeasurementModel.sensor))
        .where(MeasurementModel.id == measurement_id)
    )
    if measurement is None:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return to_schema(measurement)


@router.post("", response_model=Measurement, status_code=201)
def create_measurement(
    payload: MeasurementInput,
    db: DbSession,
    api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Response:
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")
    sensor = verify_sensor_api_key(db, api_key)
    timestamp = validate_timestamp(payload.timestamp)
    validate_measurement_value(sensor, payload.value)
    measurement = MeasurementModel(
        value=payload.value,
        timestamp=timestamp,
        sensor_id=sensor.id,
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    result = to_schema(measurement)
    response = Response(
        content=result.model_dump_json(),
        status_code=status.HTTP_201_CREATED,
        media_type="application/json",
    )
    response.headers["Location"] = f"/api/measurements/{measurement.id}"
    return response
