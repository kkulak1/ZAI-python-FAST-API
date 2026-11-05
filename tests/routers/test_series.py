import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from database.models import Series
from schemas import SeriesInput
from routers import series


def series_input(**overrides):
    values = {
        "name": "Temperature",
        "minValue": 0.0,
        "maxValue": 100.0,
        "color": "#123456",
        "icon": "thermometer",
        "unit": "C",
    }
    values.update(overrides)
    return SeriesInput(**values)


class SeriesRouterTests(unittest.TestCase):
    def make_series(self, series_id=1):
        return Series(
            id=series_id,
            name="Temperature",
            min_value=0.0,
            max_value=100.0,
            color="#123456",
            icon="thermometer",
            unit="C",
        )

    def test_list_series_maps_and_returns_items(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = [self.make_series()]

        result = series.list_series(db)

        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].minValue, 0.0)
        db.scalars.assert_called_once()

    def test_get_series_returns_404_for_missing_series(self):
        db = MagicMock()
        db.get.return_value = None

        with self.assertRaisesRegex(HTTPException, "Series not found"):
            series.get_series(10, db)

    def test_create_series_persists_and_sets_location(self):
        db = MagicMock()
        created = self.make_series(4)

        def refresh(item):
            item.id = created.id

        db.refresh.side_effect = refresh
        response = series.create_series(series_input(), db, MagicMock())

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["location"], "/api/series/4")

    def test_update_series_rejects_range_excluding_existing_measurement(self):
        db = MagicMock()
        db.get.return_value = self.make_series()
        db.scalar.return_value = 1

        with self.assertRaisesRegex(HTTPException, "outside the new range"):
            series.update_series(1, series_input(maxValue=10.0), db, MagicMock())

        db.commit.assert_not_called()

    def test_update_series_updates_fields(self):
        db = MagicMock()
        item = self.make_series()
        db.get.return_value = item
        db.scalar.return_value = None

        result = series.update_series(
            1,
            series_input(name="Humidity", minValue=10.0, maxValue=90.0),
            db,
            MagicMock(),
        )

        self.assertEqual(result.name, "Humidity")
        self.assertEqual(item.min_value, 10.0)
        self.assertEqual(item.max_value, 90.0)
        db.commit.assert_called_once()

    def test_delete_series_returns_404_for_missing_series(self):
        db = MagicMock()
        db.get.return_value = None

        with self.assertRaisesRegex(HTTPException, "Series not found"):
            series.delete_series(1, db, MagicMock())

    def test_delete_series_removes_existing_series(self):
        db = MagicMock()
        item = self.make_series()
        db.get.return_value = item

        result = series.delete_series(1, db, MagicMock())

        self.assertIsNone(result)
        db.delete.assert_called_once_with(item)
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
