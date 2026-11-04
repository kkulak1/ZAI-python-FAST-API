import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException

from services import measurements


class MeasurementServiceTests(unittest.TestCase):
    def make_sensor(self, minimum=0.0, maximum=100.0):
        sensor = MagicMock()
        sensor.series.min_value = minimum
        sensor.series.max_value = maximum
        return sensor

    def test_validate_measurement_value_accepts_value_in_range(self):
        measurements.validate_measurement_value(self.make_sensor(10.0, 20.0), 15.0)

    def test_validate_measurement_value_rejects_value_below_range(self):
        with self.assertRaisesRegex(HTTPException, "outside the series range"):
            measurements.validate_measurement_value(self.make_sensor(10.0, 20.0), 9.99)

    def test_validate_measurement_value_rejects_value_above_range(self):
        with self.assertRaisesRegex(HTTPException, "outside the series range"):
            measurements.validate_measurement_value(self.make_sensor(10.0, 20.0), 20.01)

    def test_validate_measurement_value_rejects_sensor_without_series(self):
        sensor = MagicMock()
        sensor.series = None

        with self.assertRaisesRegex(HTTPException, "outside the series range"):
            measurements.validate_measurement_value(sensor, 15.0)

    def test_validate_timestamp_defaults_to_current_utc_time(self):
        before = datetime.now(timezone.utc)
        result = measurements.validate_timestamp(None)
        after = datetime.now(timezone.utc)

        self.assertGreaterEqual(result, before)
        self.assertLessEqual(result, after)
        self.assertIsNotNone(result.tzinfo)

    def test_validate_timestamp_assigns_utc_to_naive_timestamp(self):
        timestamp = datetime(2026, 1, 1, 12, 0)

        result = measurements.validate_timestamp(timestamp)

        self.assertEqual(result.tzinfo, timezone.utc)
        self.assertEqual(result.replace(tzinfo=None), timestamp)

    def test_validate_timestamp_accepts_past_timestamp(self):
        timestamp = datetime.now(timezone.utc) - timedelta(days=1)

        self.assertEqual(measurements.validate_timestamp(timestamp), timestamp)

    def test_validate_timestamp_rejects_timestamp_more_than_five_minutes_ahead(self):
        timestamp = datetime.now(timezone.utc) + timedelta(minutes=6)

        with self.assertRaisesRegex(HTTPException, "more than 5 minutes"):
            measurements.validate_timestamp(timestamp)

    def test_validate_timestamp_accepts_timestamp_within_five_minutes_ahead(self):
        timestamp = datetime.now(timezone.utc) + timedelta(minutes=4)

        self.assertEqual(measurements.validate_timestamp(timestamp), timestamp)

    def test_list_measurements_returns_database_results(self):
        db = MagicMock()
        expected = [MagicMock(), MagicMock()]
        db.scalars.return_value.all.return_value = expected

        result = measurements.list_measurements(
            db,
            series_ids=[],
            from_time=None,
            to_time=None,
            descending=False,
            limit=25,
        )

        self.assertEqual(result, expected)
        db.scalars.assert_called_once()
        query = db.scalars.call_args.args[0]
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("LIMIT 25", sql)

    def test_list_measurements_applies_filters_and_descending_order(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        from_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        to_time = datetime(2026, 1, 2, tzinfo=timezone.utc)

        measurements.list_measurements(
            db,
            series_ids=[2, 4],
            from_time=from_time,
            to_time=to_time,
            descending=True,
            limit=10,
        )

        query = db.scalars.call_args.args[0]
        sql = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("measurements.series_id IN (2, 4)", sql)
        self.assertIn("measurements.timestamp >=", sql)
        self.assertIn("measurements.timestamp <=", sql)
        self.assertIn("LIMIT 10", sql)
        self.assertIn("ORDER BY measurements.timestamp DESC", sql)


if __name__ == "__main__":
    unittest.main()
