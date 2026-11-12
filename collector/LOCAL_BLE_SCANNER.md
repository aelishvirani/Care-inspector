# Local BLE Scanner (Mac development only)

An optional read-only scanner shows advertising Bluetooth Low Energy devices
inside Care-Inspector's **Raspberry Pi** page instead of using Chrome's chooser
for *discovery*. Its scan is **not pairing, trusted identity or enrollment**.
The existing Chrome Web Bluetooth selection remains available via
**Select Pi for Verification** for the secure BLE verification process.

This service is manually launched on the *technician's Mac*. It binds only
`127.0.0.1:8765` and is exposed to the React development page through Vite's
`/local-ble` proxy. Do not deploy this helper on the cloud backend or expose
the port to a LAN/public network. The feature works only when the Vite frontend
and scanner are on the **same Mac**.

## Local setup (additional terminal)

From the repository root in your existing Mac virtual environment:

```bash
python -m pip install bleak
python -m collector.local_ble_scanner
```

When macOS asks for Bluetooth access, allow the terminal/Python process.
Restart the Vite frontend after pulling the updated `vite.config.js`.
Visit `http://localhost:5173/raspberry-pi` and click **Search Nearby**.
Results appear under **Nearby Bluetooth Devices (Mac Scanner)**.
Press Ctrl+C in the scanner terminal when finished.

A scan lasts around six seconds. Only devices advertising via BLE and detectable
by macOS at scan time can appear; some devices may be unnamed, undiscoverable,
or not advertising. macOS returns opaque UUID-like identifiers, not reliable
hardware MAC addresses. Signal strength is approximate. No device is
automatically connected, trusted or registered, and there is no BLE control
channel in this scanner.

To validate without Bluetooth hardware:

```bash
python -m unittest backend.tests.test_local_ble_scanner -v
```

No password, signing key, JWT or printer credentials are required by the
scanner. Use only with a trusted local development setup.
