"""Measurement-series endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select

from database.models import Measurement as MeasurementModel
from database.models import Series as SeriesModel
from schemas import Series, SeriesInput
from services.dependencies import DbSession, get_admin

router = APIRouter(prefix="/api/series", tags=["series"])


def to_schema(series: SeriesModel) -> Series:
    return Series(
        id=series.id,
        name=series.name,
        minValue=series.min_value,
        maxValue=series.max_value,
        color=series.color,
        icon=series.icon,
        unit=series.unit,
    )


@router.get("", response_model=list[Series])
def list_series(db: DbSession) -> list[Series]:
    return [to_schema(item) for item in db.scalars(select(SeriesModel).order_by(SeriesModel.name)).all()]


@router.get("/{seriesId}", response_model=Series)
def get_series(seriesId: int, db: DbSession) -> Series:
    series_id = seriesId
    series = db.get(SeriesModel, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    return to_schema(series)


@router.post("", response_model=Series, status_code=201)
def create_series(
    payload: SeriesInput,
    db: DbSession,
    _admin=Depends(get_admin),
) -> Response:
    series = SeriesModel(
        name=payload.name,
        min_value=payload.minValue,
        max_value=payload.maxValue,
        color=payload.color,
        icon=payload.icon,
        unit=payload.unit,
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    response = Response(
        content=to_schema(series).model_dump_json(),
        status_code=status.HTTP_201_CREATED,
        media_type="application/json",
    )
    response.headers["Location"] = f"/api/series/{series.id}"
    return response


@router.put("/{seriesId}", response_model=Series)
def update_series(
    seriesId: int,
    payload: SeriesInput,
    db: DbSession,
    _admin=Depends(get_admin),
) -> Series:
    series_id = seriesId
    series = db.get(SeriesModel, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    has_out_of_range = db.scalar(
        select(MeasurementModel.id)
        .join(MeasurementModel.sensor)
        .where(
            or_(
                MeasurementModel.value < payload.minValue,
                MeasurementModel.value > payload.maxValue,
            ),
            MeasurementModel.sensor.has(series_id=series_id),
        )
        .limit(1)
    )
    if has_out_of_range is not None:
        raise HTTPException(status_code=409, detail="Existing measurements fall outside the new range")
    series.name = payload.name
    series.min_value = payload.minValue
    series.max_value = payload.maxValue
    series.color = payload.color
    series.icon = payload.icon
    series.unit = payload.unit
    db.commit()
    db.refresh(series)
    return to_schema(series)


@router.delete("/{seriesId}", status_code=204)
def delete_series(
    seriesId: int,
    db: DbSession,
    _admin=Depends(get_admin),
) -> None:
    series_id = seriesId
    series = db.get(SeriesModel, series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    db.delete(series)
    db.commit()
