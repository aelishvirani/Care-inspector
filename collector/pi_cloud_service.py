"""Entry point for the Pi's periodic cryptographically signed check-ins.

Example:
    CARE_INSPECTOR_BACKEND_URL=https://care.example.org \
      python3 -m collector.pi_cloud_service

No cloud session or printer-control permissions are issued here.
"""
import os
import signal
import threading
from urllib.parse import urlsplit

from .pi_cloud_heartbeat import heartbeat_loop


def load_service_settings(environ=None):
    env = os.environ if environ is None else environ
    backend_url = env.get("CARE_INSPECTOR_BACKEND_URL", "").strip().rstrip("/")
    if not backend_url:
        raise ValueError("CARE_INSPECTOR_BACKEND_URL must be configured")
    parsed = urlsplit(backend_url)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (parsed.scheme != "https" and not (parsed.scheme == "http" and local)
            or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path not in {"", "/"}):
        raise ValueError("Backend URL must be HTTPS (HTTP only for local testing)")

    interval_text = env.get("CARE_INSPECTOR_PI_HEARTBEAT_SECONDS", "60")
    try:
        interval = int(interval_text)
    except ValueError as exc:
        raise ValueError("Heartbeat interval must be a whole number") from exc
    if interval < 15 or interval > 3600:
        raise ValueError("Heartbeat interval must be 15–3600 seconds")
    return backend_url, interval


def run_service(environ=None, *, heartbeat=heartbeat_loop):
    backend_url, interval = load_service_settings(environ)
    stop = threading.Event()

    def handle_shutdown(signum, frame):
        stop.set()

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

    # Waits between successful check-ins can be interrupted on shutdown.
    heartbeat(
        backend_url, interval_seconds=interval,
        should_stop=stop.is_set, sleep=stop.wait,
    )


def main():
    run_service()


if __name__ == "__main__":
    main()
