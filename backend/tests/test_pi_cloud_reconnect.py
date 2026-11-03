"""Cloud retry orchestration tests. No network, Pi hardware or sleeping."""
import unittest

from collector.pi_cloud_reconnect import authenticate_with_retries, retry_delay


class CloudReconnectTests(unittest.TestCase):
    def test_backoff_is_bounded(self):
        self.assertEqual(retry_delay(1, jitter=1), 2)
        self.assertEqual(retry_delay(2, jitter=1), 4)
        self.assertEqual(retry_delay(40, jitter=1), 120)

    def test_transient_failure_then_reauth(self):
        attempts = []
        delays = []

        def auth(url):
            attempts.append(url)
            if len(attempts) <= 2:
                raise ConnectionError("network offline")
            return {"authenticated": True, "cloud_session_issued": False}

        ok = authenticate_with_retries(
            "https://example.invalid", authenticate=auth,
            sleep=delays.append,
        )
        self.assertTrue(ok)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(delays), 2)

    def test_authentication_denied_does_not_retry(self):
        attempts = []
        def auth(url):
            attempts.append(1)
            raise PermissionError("device revoked")

        with self.assertRaises(PermissionError):
            authenticate_with_retries("https://example.invalid", authenticate=auth,
                                      sleep=lambda _: self.fail("unexpected sleep"))
        self.assertEqual(len(attempts), 1)

    def test_missing_key_does_not_retry(self):
        def auth(url):
            raise FileNotFoundError("identity key not found")

        with self.assertRaises(FileNotFoundError):
            authenticate_with_retries("https://example.invalid", authenticate=auth,
                                      sleep=lambda _: self.fail("unexpected sleep"))

    def test_max_attempts(self):
        attempts = []
        def auth(url):
            attempts.append(1)
            raise TimeoutError("unreachable")

        self.assertFalse(authenticate_with_retries(
            "https://example.invalid", authenticate=auth, sleep=lambda _: None,
            max_attempts=3,
        ))
        self.assertEqual(len(attempts), 3)

    def test_stoppable(self):
        self.assertFalse(authenticate_with_retries(
            "https://example.invalid", should_stop=lambda: True,
            authenticate=lambda _: self.fail("should not authenticate"),
        ))

    def test_unexpected_response_rejected(self):
        with self.assertRaises(PermissionError):
            authenticate_with_retries(
                "https://example.invalid",
                authenticate=lambda _: {"authenticated": True, "cloud_session_issued": True},
                sleep=lambda _: self.fail("unexpected retry"),
            )


if __name__ == "__main__":
    unittest.main()
