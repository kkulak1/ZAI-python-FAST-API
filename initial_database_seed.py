from datetime import datetime, timedelta, timezone

from config import settings
from database.database import SessionLocal, engine
from database.models import Base, Measurement, Series, User, hash_password
from sqlalchemy.orm import Session


SAMPLE_SERIES = (
    ("Temperatura", -40.0, 80.0, "#e4572e", "°C"),
    ("Wilgotność", 0.0, 100.0, "#17bebb", "%"),
    ("Ciśnienie", 800.0, 1200.0, "#3a86ff", "hPa"),
)


def create_initial_admin(db: Session) -> None:
    if db.query(User).filter(User.username == "admin").first() is None:
        db.add(
            User(
                username="admin",
                password_hash=hash_password(settings.ADMIN_PASSWORD),
            )
        )


def seed_sample_data(db: Session) -> None:
    for name, min_value, max_value, color, unit in SAMPLE_SERIES:
        series = db.query(Series).filter(Series.name == name).first()
        if series is None:
            series = Series(
                name=name,
                min_value=min_value,
                max_value=max_value,
                color=color,
                unit=unit,
            )
            db.add(series)
            db.flush()

        existing_measurements = (
            db.query(Measurement)
            .filter(Measurement.series_id == series.id)
            .count()
        )
        for index in range(existing_measurements, 15):
            fraction = (index + 1) / 16
            value = min_value + (max_value - min_value) * fraction
            db.add(
                Measurement(
                    series_id=series.id,
                    value=value,
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=15 * (15 - index)),
                )
            )


def seed_database() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        create_initial_admin(db)
        seed_sample_data(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    seed_database()


if __name__ == "__main__":
    initialize_database()
