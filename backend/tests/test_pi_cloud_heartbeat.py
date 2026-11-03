"""Periodic Pi signature check-in loop with no network or hardware."""
import unittest
from collector.pi_cloud_heartbeat import heartbeat_loop


class PiCloudHeartbeatTests(unittest.TestCase):
    def test_successful_repeating_checkins(self):
        proofs = []
        seen = []
        def auth(url, *, should_stop, on_authenticated):
            proofs.append(url)
            on_authenticated({"authenticated": True, "cloud_session_issued": False})
            return True
        heartbeat_loop(
            "https://example.invalid", interval_seconds=60,
            authenticate_with_retry=auth,
            sleep=seen.append,
            should_stop=lambda: len(proofs) >= 3,
        )
        self.assertEqual(len(proofs), 3)
        self.assertEqual(seen, [60, 60])

    def test_stop_before_first_checkin(self):
        heartbeat_loop(
            "https://example.invalid", interval_seconds=60,
            should_stop=lambda: True,
            authenticate_with_retry=lambda *a, **k: self.fail("should not authenticate"),
        )

    def test_interval_lower_bound(self):
        with self.assertRaises(ValueError):
            heartbeat_loop("https://example.invalid", interval_seconds=5)

    def test_unsuccessful_auth_ends_loop(self):
        calls = []
        heartbeat_loop(
            "https://example.invalid", interval_seconds=60,
            authenticate_with_retry=lambda *a, **k: calls.append(1) or False,
            sleep=lambda n: self.fail("should not sleep"),
        )
        self.assertEqual(calls, [1])


if __name__ == "__main__":
    unittest.main()
