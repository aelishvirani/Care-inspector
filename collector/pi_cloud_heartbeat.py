"""Periodic key-authenticated Pi check-ins; no telemetry or printer commands.

Each check-in performs a fresh server challenge and Ed25519 signature.
The server derives Pi presence from successful proofs, not self-reported status.
Run this agent only after authorized registration and with its original key.
"""
import time

from .pi_cloud_reconnect import authenticate_with_retries


def heartbeat_loop(
    backend_url: str, *,
    interval_seconds: float = 60,
    authenticate_with_retry=authenticate_with_retries,
    sleep=time.sleep,
    should_stop=lambda: False,
    on_checkin=None,
) -> None:
    if interval_seconds < 15:
        raise ValueError("Heartbeat interval must be at least 15 seconds")
    while not should_stop():
        result = {}

        def capture(proof):
            result.update(proof)

        success = authenticate_with_retry(
            backend_url,
            should_stop=should_stop,
            on_authenticated=capture,
        )
        if not success or should_stop():
            return
        if on_checkin:
            on_checkin(result)
        # Service manager can restart the process; no user interaction needed.
        sleep(interval_seconds)
