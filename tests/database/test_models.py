import unittest
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import (
    Base,
    Measurement,
    Sensor,
    Series,
    User,
    hash_api_key,
    hash_password,
)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def make_series(self, *, minimum=0.0, maximum=100.0):
        series = Series(
            name="Temperature",
            min_value=minimum,
            max_value=maximum,
            color="#ff0000",
            icon="thermometer",
            unit="°C",
        )
        self.session.add(series)
        self.session.flush()
        return series

    def test_password_hash_can_be_verified_and_is_not_plaintext(self):
        password = "correct horse battery staple"

        password_hash = hash_password(password)

        self.assertNotEqual(password_hash, password)
        self.assertTrue(bcrypt.checkpw(password.encode(), password_hash.encode()))

    def test_api_key_hash_is_sha256_hex_digest(self):
        api_key_hash = hash_api_key("test-api-key")

        self.assertEqual(
            api_key_hash,
            "4c806362b613f7496abf284146efd31da90e4b16169fe001841ca17290f427c4",
        )
        self.assertEqual(len(api_key_hash), 64)

    def test_user_has_unique_username(self):
        self.session.add_all(
            [
                User(username="alice", password_hash="hash"),
                User(username="alice", password_hash="another-hash"),
            ]
        )

        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_sensor_accepts_lowercase_sha256_digest(self):
        series = self.make_series()
        sensor = Sensor(
            name="Living room",
            series=series,
            api_key_hash=hash_api_key("sensor-key"),
        )

        self.session.add(sensor)
        self.session.commit()

        self.assertEqual(sensor.series, series)
        self.assertIsNotNone(sensor.created_at)
        self.assertIsInstance(sensor.created_at, datetime)

    def test_sensor_rejects_invalid_api_key_hash(self):
        with self.assertRaises(ValueError):
            Sensor(
                name="Living room",
                series_id=1,
                api_key_hash="not-a-sha256-digest",
            )

    def test_measurement_within_series_range_is_persisted(self):
        series = self.make_series(minimum=10.0, maximum=20.0)
        measurement = Measurement(
            timestamp=datetime.now(timezone.utc),
            value=15.0,
            series=series,
        )

        self.session.add(measurement)
        self.session.commit()

        self.assertIsNotNone(measurement.id)
        self.assertEqual(measurement.series, series)

    def test_measurement_outside_series_range_is_rejected(self):
        series = self.make_series(minimum=10.0, maximum=20.0)
        self.session.add(Measurement(value=25.0, series=series))

        with self.assertRaisesRegex(ValueError, "outside the series range"):
            self.session.commit()

    def test_measurement_update_is_checked_against_series_range(self):
        series = self.make_series(minimum=10.0, maximum=20.0)
        measurement = Measurement(value=15.0, series=series)
        self.session.add(measurement)
        self.session.commit()

        measurement.value = 25.0
        with self.assertRaisesRegex(ValueError, "outside the series range"):
            self.session.commit()

    def test_measurement_requires_existing_series(self):
        self.session.add(Measurement(value=15.0, series_id=999))

        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.session.commit()

    def test_series_delete_cascades_to_measurements_and_sensors(self):
        series = self.make_series()
        sensor = Sensor(
            name="Living room",
            series=series,
            api_key_hash=hash_api_key("delete-test-sensor-key"),
        )
        measurement = Measurement(value=50.0, series=series, sensor=sensor)
        self.session.add_all([sensor, measurement])
        self.session.commit()

        self.session.delete(series)
        self.session.commit()

        self.assertIsNone(self.session.get(Series, series.id))
        self.assertIsNone(self.session.get(Sensor, sensor.id))
        self.assertIsNone(self.session.get(Measurement, measurement.id))


if __name__ == "__main__":
    unittest.main()
