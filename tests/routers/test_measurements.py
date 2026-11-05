import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from database.models import Sensor as SensorModel
from schemas import MeasurementInput
from routers import measurements


class MeasurementsRouterTests(unittest.TestCase):
    def make_sensor(self):
        sensor = SensorModel(
            id=5,
            name="Living room",
            series_id=2,
            api_key_hash="a" * 64,
        )
        sensor.series = MagicMock(min_value=0.0, max_value=100.0)
        return sensor

    def test_parse_series_filter_accepts_comma_separated_ids(self):
        self.assertEqual(measurements.parse_series_filter("1, 3,5"), [1, 3, 5])
        self.assertEqual(measurements.parse_series_filter(None), [])

    def test_parse_series_filter_rejects_invalid_ids(self):
        with self.assertRaisesRegex(HTTPException, "comma-separated"):
            measurements.parse_series_filter("1,nope")
        with self.assertRaisesRegex(HTTPException, "positive"):
            measurements.parse_series_filter("0,2")

    @patch("routers.measurements.list_measurements", return_value=[])
    def test_get_measurements_passes_filters_to_service(self, list_items):
        db = MagicMock()
        from_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        to_time = datetime(2026, 1, 2, tzinfo=timezone.utc)

        result = measurements.get_measurements(
            db,
            series="1,2",
            from_=from_time,
            to=to_time,
            sort="-timestamp",
            limit=25,
        )

        self.assertEqual(result, [])
        list_items.assert_called_once_with(
            db, [1, 2], from_time, to_time, descending=True, limit=25
        )

    def test_get_measurements_rejects_reversed_time_range(self):
        from_time = datetime(2026, 1, 2, tzinfo=timezone.utc)
        to_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        with self.assertRaisesRegex(HTTPException, "must not be later"):
            measurements.get_measurements(MagicMock(), from_=from_time, to=to_time)

    def test_get_measurement_returns_404_for_missing_measurement(self):
        db = MagicMock()
        db.scalar.return_value = None

        with self.assertRaisesRegex(HTTPException, "Measurement not found"):
            measurements.get_measurement(9, db)

    @patch("routers.measurements.validate_measurement_value")
    @patch("routers.measurements.validate_timestamp", return_value=datetime(2026, 1, 1, tzinfo=timezone.utc))
    @patch("routers.measurements.verify_sensor_api_key")
    def test_create_measurement_uses_sensor_identity(self, verify_key, validate_time, validate_value):
        db = MagicMock()
        sensor = self.make_sensor()
        sensor.series_id = 2
        verify_key.return_value = sensor
        db.refresh.side_effect = lambda item: setattr(item, "id", 10)

        response = measurements.create_measurement(
            MeasurementInput(value=42.0),
            db,
            api_key="sensor-key",
        )

        verify_key.assert_called_once_with(db, "sensor-key")
        validate_time.assert_called_once()
        validate_value.assert_called_once_with(sensor, 42.0)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["location"], "/api/measurements/10")

    def test_create_measurement_requires_api_key(self):
        with self.assertRaisesRegex(HTTPException, "X-API-Key header is required"):
            measurements.create_measurement(
                MeasurementInput(value=42.0),
                MagicMock(),
                api_key=None,
            )


if __name__ == "__main__":
    unittest.main()
