import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from database.models import Sensor as SensorModel
from database.models import Series
from schemas import SensorInput
from routers import sensors


class SensorsRouterTests(unittest.TestCase):
    def make_series(self):
        return Series(
            id=3,
            name="Temperature",
            min_value=0.0,
            max_value=100.0,
            color="#123456",
        )

    def make_sensor(self):
        return SensorModel(
            id=8,
            name="Living room",
            series_id=3,
            api_key_hash="a" * 64,
            created_at=datetime.now(timezone.utc),
        )

    def test_list_sensors_maps_items(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = [self.make_sensor()]

        result = sensors.list_sensors(db, MagicMock())

        self.assertEqual(result[0].name, "Living room")
        self.assertEqual(result[0].seriesId, 3)

    def test_get_sensor_returns_404_for_missing_sensor(self):
        db = MagicMock()
        db.scalar.return_value = None

        with self.assertRaisesRegex(HTTPException, "Sensor not found"):
            sensors.get_sensor(8, db, MagicMock())

    @patch("routers.sensors.hash_api_key", return_value="b" * 64)
    @patch("routers.sensors.create_sensor_key", return_value="sensor-key-" + "x" * 32)
    def test_register_sensor_returns_api_key_once(self, create_key, hash_key):
        db = MagicMock()
        db.get.return_value = self.make_series()
        db.refresh.side_effect = lambda sensor: setattr(sensor, "id", 12)

        response = sensors.register_sensor(
            SensorInput(name="Living room", seriesId=3),
            db,
            MagicMock(),
        )

        create_key.assert_called_once_with()
        hash_key.assert_called_once_with("sensor-key-" + "x" * 32)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["location"], "/api/sensors/12")
        self.assertIn("apiKey", response.body.decode())

    def test_register_sensor_rejects_unknown_series(self):
        db = MagicMock()
        db.get.return_value = None

        with self.assertRaisesRegex(HTTPException, "Series not found"):
            sensors.register_sensor(
                SensorInput(name="Living room", seriesId=999),
                db,
                MagicMock(),
            )

    def test_unregister_sensor_deletes_existing_sensor(self):
        db = MagicMock()
        sensor = self.make_sensor()
        db.get.return_value = sensor

        result = sensors.unregister_sensor(8, db, MagicMock())

        self.assertIsNone(result)
        db.delete.assert_called_once_with(sensor)
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
