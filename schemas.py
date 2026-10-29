from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Id = int


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict[str, str]] | None = None


class LoginRequest(BaseModel):
    username: Annotated[str, Field(min_length=1)]
    password: Annotated[str, Field(min_length=1, json_schema_extra={"format": "password"})]


class LoginResponse(BaseModel):
    accessToken: str
    tokenType: Literal["bearer"] = "bearer"
    expiresIn: int


class PasswordChange(BaseModel):
    currentPassword: Annotated[str, Field(min_length=1, json_schema_extra={"format": "password"})]
    newPassword: Annotated[
        str,
        Field(min_length=8, json_schema_extra={"format": "password"}),
    ]


class SeriesInput(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    minValue: float
    maxValue: float
    color: Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
    icon: str | None = None
    unit: Annotated[str | None, Field(max_length=20)] = None

    @model_validator(mode="after")
    def validate_bounds(self) -> SeriesInput:
        if self.minValue >= self.maxValue:
            raise ValueError("minValue must be less than maxValue")
        return self


class Series(SeriesInput):
    model_config = ConfigDict(from_attributes=True)

    id: Id


class MeasurementInput(BaseModel):
    value: float
    timestamp: datetime | None = None


class Measurement(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Id
    seriesId: Id
    sensorId: Id | None = None
    value: float
    timestamp: datetime


class SensorInput(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    seriesId: Id


class Sensor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Id
    name: str
    seriesId: Id
    createdAt: datetime | None = None
    lastMeasurementAt: datetime | None = None


class SensorCreated(Sensor):
    apiKey: Annotated[str, Field(min_length=32)]
