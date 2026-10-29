"""Sensor administration endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import Sensor as SensorModel
from database.models import Series as SeriesModel
from schemas import Sensor, SensorCreated, SensorInput
from services.dependencies import DbSession, get_admin
from services.security import create_sensor_key, hash_api_key

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


def to_schema(sensor: SensorModel) -> Sensor:
    last_measurement = max(
        (measurement.timestamp for measurement in sensor.measurements),
        default=None,
    )
    return Sensor(
        id=sensor.id,
        name=sensor.name,
        seriesId=sensor.series_id,
        createdAt=sensor.created_at,
        lastMeasurementAt=last_measurement,
    )


@router.get("", response_model=list[Sensor])
def list_sensors(db: DbSession, _admin=Depends(get_admin)) -> list[Sensor]:
    sensors = db.scalars(
        select(SensorModel)
        .options(selectinload(SensorModel.measurements))
        .order_by(SensorModel.name)
    ).all()
    return [to_schema(sensor) for sensor in sensors]


@router.get("/{sensorId}", response_model=Sensor)
def get_sensor(sensorId: int, db: DbSession, _admin=Depends(get_admin)) -> Sensor:
    sensor_id = sensorId
    sensor = db.scalar(
        select(SensorModel)
        .options(selectinload(SensorModel.measurements))
        .where(SensorModel.id == sensor_id)
    )
    if sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return to_schema(sensor)


@router.post("", response_model=SensorCreated, status_code=201)
def register_sensor(
    payload: SensorInput,
    db: DbSession,
    _admin=Depends(get_admin),
) -> Response:
    if db.get(SeriesModel, payload.seriesId) is None:
        raise HTTPException(status_code=422, detail="Series not found")
    api_key = create_sensor_key()
    sensor = SensorModel(
        name=payload.name,
        series_id=payload.seriesId,
        api_key_hash=hash_api_key(api_key),
    )
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    result = SensorCreated(**to_schema(sensor).model_dump(), apiKey=api_key)
    response = Response(
        content=result.model_dump_json(),
        status_code=status.HTTP_201_CREATED,
        media_type="application/json",
    )
    response.headers["Location"] = f"/api/sensors/{sensor.id}"
    return response


@router.delete("/{sensorId}", status_code=204)
def unregister_sensor(
    sensorId: int,
    db: DbSession,
    _admin=Depends(get_admin),
) -> None:
    sensor_id = sensorId
    sensor = db.get(SensorModel, sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    db.delete(sensor)
    db.commit()
