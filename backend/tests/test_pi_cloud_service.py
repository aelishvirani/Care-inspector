"""Pi heartbeat service configuration and runner tests without Pi/Linux."""
import unittest

from collector.pi_cloud_service import load_service_settings, run_service


class PiCloudServiceTests(unittest.TestCase):
    def test_default_interval(self):
        self.assertEqual(load_service_settings({
            "CARE_INSPECTOR_BACKEND_URL": "https://care.example.org"
        }), ("https://care.example.org", 60))

    def test_custom_interval(self):
        url, seconds = load_service_settings({
            "CARE_INSPECTOR_BACKEND_URL": "https://care.example.org/",
            "CARE_INSPECTOR_PI_HEARTBEAT_SECONDS": "90",
        })
        self.assertEqual((url, seconds), ("https://care.example.org", 90))

    def test_missing_url_rejected(self):
        with self.assertRaises(ValueError):
            load_service_settings({})

    def test_remote_http_rejected(self):
        with self.assertRaises(ValueError):
            load_service_settings({"CARE_INSPECTOR_BACKEND_URL": "http://care.example.org"})

    def test_local_http_allowed_for_development(self):
        self.assertEqual(load_service_settings({
            "CARE_INSPECTOR_BACKEND_URL": "http://127.0.0.1:8000"
        })[1], 60)

    def test_bad_intervals_rejected(self):
        for value in ("abc", "0", "14", "3601"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_service_settings({
                    "CARE_INSPECTOR_BACKEND_URL": "https://care.example.org",
                    "CARE_INSPECTOR_PI_HEARTBEAT_SECONDS": value,
                })

    def test_service_calls_heartbeat(self):
        observed = []
        def fake_heartbeat(url, *, interval_seconds, should_stop, sleep):
            observed.append((url, interval_seconds, should_stop(), callable(sleep)))
        run_service({
            "CARE_INSPECTOR_BACKEND_URL": "https://care.example.org",
            "CARE_INSPECTOR_PI_HEARTBEAT_SECONDS": "120",
        }, heartbeat=fake_heartbeat)
        self.assertEqual(observed, [("https://care.example.org", 120, False, True)])


if __name__ == "__main__":
    unittest.main()
