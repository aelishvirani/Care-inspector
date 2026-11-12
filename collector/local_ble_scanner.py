"""Opt-in read-only local BLE scanner for the Care-Inspector Mac development portal.

Start manually on the technician's Mac. Does not connect, pair, write to a
device, authenticate a Pi, or expose the scan on any non-loopback interface.
Requires "bleak" and macOS Bluetooth permission for the terminal/Python.
"""
from __future__ import annotations

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765
SCAN_SECONDS = 6.0
ALLOWED_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}


async def scan_nearby(seconds: float = SCAN_SECONDS) -> list[dict]:
    """Return advertising BLE devices; no GATT connection or pairing."""
    from bleak import BleakScanner

    seen = {}

    def on_advertisement(device, advertisement):
        # On macOS Bleak reports opaque OS-assigned identifiers, not MAC addresses.
        device_id = str(device.address)
        name = advertisement.local_name or device.name or "Unnamed BLE device"
        rssi = getattr(advertisement, "rssi", None)
        services = [str(uuid).lower() for uuid in (advertisement.service_uuids or [])]
        seen[device_id] = {
            "id": device_id,
            "name": str(name)[:120],
            "rssi": rssi if isinstance(rssi, int) else None,
            "service_uuids": services[:24],
        }

    async with BleakScanner(detection_callback=on_advertisement):
        await asyncio.sleep(seconds)
    return sorted(seen.values(), key=lambda item: item["rssi"] or -999, reverse=True)[:100]


class ScannerHandler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/scan":
            self._json(404, {"detail": "Not found"})
            return
        # Explicit browser gesture via local Vite proxy; reject cross-origin
        # browser requests and plain navigation. No CORS headers are emitted.
        origin = self.headers.get("Origin")
        fetch_site = self.headers.get("Sec-Fetch-Site")
        if (origin and origin not in ALLOWED_ORIGINS) or (
            fetch_site and fetch_site not in {"same-origin", "same-site"}
        ) or self.headers.get("X-Care-Inspector-Local-Scan") != "1":
            self._json(403, {"detail": "Local portal request required"})
            return
        try:
            devices = asyncio.run(scan_nearby())
            self._json(200, {"devices": devices, "scan_seconds": SCAN_SECONDS})
        except Exception as exc:
            # Avoid transmitting sensitive Bluetooth/device details from errors.
            print("BLE scan failed:", type(exc).__name__)
            self._json(503, {"detail": "Local BLE scan unavailable; check macOS Bluetooth permission and scanner logs"})

    def log_message(self, format, *args):
        # Do not log device identifiers or raw requests.
        return


def main():
    print(f"Care-Inspector read-only local BLE scanner at http://{HOST}:{PORT}")
    print("Only start on your own Mac; press Ctrl+C to stop. No pairing or connections.")
    with ThreadingHTTPServer((HOST, PORT), ScannerHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
