import io
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import MagicMock, patch

from generator import iot_generator


class GenerateValueTests(unittest.TestCase):
    def test_random_value_stays_within_range(self):
        with patch("generator.iot_generator.random.uniform", return_value=12.345):
            result = iot_generator.generate_value("random", 10.0, 20.0)

        self.assertEqual(result, 12.35)

    def test_sine_value_starts_at_midpoint(self):
        result = iot_generator.generate_value("sine", 0.0, 100.0, step_index=0)

        self.assertEqual(result, 50.0)

    def test_sine_value_reaches_upper_bound_at_quarter_period(self):
        result = iot_generator.generate_value("sine", 0.0, 100.0, step_index=5)

        self.assertEqual(result, 100.0)

    def test_constant_value_is_the_range_midpoint(self):
        result = iot_generator.generate_value("constant", -10.0, 30.0)

        self.assertEqual(result, 10.0)

    def test_unknown_mode_falls_back_to_random(self):
        with patch("generator.iot_generator.random.uniform", return_value=7.0) as uniform:
            result = iot_generator.generate_value("unsupported", 0.0, 10.0)

        self.assertEqual(result, 7.0)
        uniform.assert_called_once_with(0.0, 10.0)


class SendMeasurementTests(unittest.TestCase):
    def make_response(self, status_code, text="response"):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        return response

    @patch("generator.iot_generator.requests.post")
    def test_send_measurement_posts_value_and_api_key(self, post):
        post.return_value = self.make_response(201)

        iot_generator.send_measurement(
            "http://localhost:8000/",
            "sensor-key",
            42.5,
            timestamp="2026-01-01T12:00:00Z",
        )

        post.assert_called_once_with(
            "http://localhost:8000/api/measurements",
            json={"value": 42.5, "timestamp": "2026-01-01T12:00:00Z"},
            headers={
                "X-API-Key": "sensor-key",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

    @patch("generator.iot_generator.requests.post")
    def test_send_measurement_omits_timestamp_when_not_provided(self, post):
        post.return_value = self.make_response(200)

        iot_generator.send_measurement("http://api.example", "key", 12.0)

        self.assertEqual(post.call_args.kwargs["json"], {"value": 12.0})

    @patch("generator.iot_generator.requests.post")
    def test_send_measurement_reports_api_error(self, post):
        post.return_value = self.make_response(401, "invalid key")
        output = io.StringIO()

        with redirect_stdout(output):
            iot_generator.send_measurement("http://api.example", "key", 12.0)

        self.assertIn("401", output.getvalue())
        self.assertIn("invalid key", output.getvalue())

    @patch("generator.iot_generator.requests.post")
    def test_send_measurement_reports_network_error(self, post):
        post.side_effect = iot_generator.requests.exceptions.Timeout("timed out")
        output = io.StringIO()

        with redirect_stdout(output):
            iot_generator.send_measurement("http://api.example", "key", 12.0)

        self.assertIn("BŁĄD SIECI", output.getvalue())
        self.assertIn("timed out", output.getvalue())


class MainTests(unittest.TestCase):
    @patch("generator.iot_generator.send_measurement")
    @patch("generator.iot_generator.generate_value", return_value=25.0)
    @patch("generator.iot_generator.datetime")
    def test_main_history_mode_sends_requested_number_of_measurements(
        self, datetime_class, generate_value, send_measurement
    ):
        datetime_class.utcnow.return_value = datetime(2026, 1, 1, 12, 0, 0)
        argv = [
            "iot_generator.py",
            "--url",
            "http://localhost:8000",
            "--key",
            "sensor-key",
            "--history-count",
            "3",
            "--step-seconds",
            "60",
        ]

        with patch.object(sys, "argv", argv):
            iot_generator.main()

        self.assertEqual(send_measurement.call_count, 3)
        self.assertEqual(generate_value.call_count, 3)
        self.assertEqual(
            send_measurement.call_args_list[0].kwargs["timestamp"],
            "2026-01-01T11:57:00Z",
        )
        self.assertEqual(
            send_measurement.call_args_list[-1].kwargs["timestamp"],
            "2026-01-01T11:59:00Z",
        )

    @patch("generator.iot_generator.time.sleep", side_effect=KeyboardInterrupt)
    @patch("generator.iot_generator.send_measurement")
    @patch("generator.iot_generator.generate_value", return_value=50.0)
    def test_main_continuous_mode_stops_after_keyboard_interrupt(
        self, generate_value, send_measurement, sleep
    ):
        argv = [
            "iot_generator.py",
            "--url",
            "http://localhost:8000",
            "--key",
            "sensor-key",
            "--mode",
            "constant",
            "--interval",
            "5",
        ]
        output = io.StringIO()

        with patch.object(sys, "argv", argv), redirect_stdout(output):
            iot_generator.main()

        send_measurement.assert_called_once_with(
            "http://localhost:8000", "sensor-key", 50.0
        )
        sleep.assert_called_once_with(5.0)
        self.assertIn("Zatrzymano generator", output.getvalue())

    def test_main_requires_one_operating_mode(self):
        argv = [
            "iot_generator.py",
            "--url",
            "http://localhost:8000",
            "--key",
            "sensor-key",
        ]

        with patch.object(sys, "argv", argv), self.assertRaises(SystemExit) as error:
            iot_generator.main()

        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
