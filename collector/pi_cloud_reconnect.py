"""Retry transient Raspberry Pi cloud authentication failures.

This is a transport/auth retry worker, NOT a connected telemetry session.
Successful key proof does not grant API permissions or mark a Pi online.
"""
import random
import time

from .pi_cloud_auth_client import authenticate_from_pi


def retry_delay(attempt: int, base_seconds: float = 2.0,
                max_seconds: float = 120.0, jitter=None) -> float:
    """Bounded exponential backoff with positive jitter to avoid reconnection storms."""
    if attempt < 1 or base_seconds <= 0 or max_seconds < base_seconds:
        raise ValueError("Invalid retry configuration")
    capped = min(max_seconds, base_seconds * (2 ** min(attempt - 1, 16)))
    fraction = random.random() if jitter is None else jitter
    if not 0 <= fraction <= 1:
        raise ValueError("Jitter must be between 0 and 1")
    return capped * (0.75 + 0.25 * fraction)


def authenticate_with_retries(
    backend_url: str,
    *,
    authenticate=authenticate_from_pi,
    sleep=time.sleep,
    should_stop=lambda: False,
    on_authenticated=None,
    on_retry=None,
    max_attempts=None,
) -> bool:
    """Attempt cloud key proof; retry network interruptions only.

    Returns True after proof, False if stopped or retry limit reached.
    Authentication rejection, invalid configuration and missing keys are
    fatal: they require intervention, not an infinite reconnect loop.
    Pass should_stop/sleep callbacks for an agent service or unit tests.
    """
    attempt = 0
    while not should_stop():
        attempt += 1
        try:
            result = authenticate(backend_url)
            if result.get("authenticated") is not True or result.get("cloud_session_issued") is not False:
                raise PermissionError("Unexpected Pi cloud authentication response")
            if on_authenticated is not None:
                on_authenticated(result)
            return True
        except (PermissionError, FileNotFoundError):
            # Both inherit OSError; reject credentials and missing keys immediately.
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            if max_attempts is not None and attempt >= max_attempts:
                return False
            delay = retry_delay(attempt)
            if on_retry is not None:
                on_retry(attempt, delay)
            if should_stop():
                return False
            sleep(delay)
    return False
