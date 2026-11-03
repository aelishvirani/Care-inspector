# Periodic Raspberry Pi printer discovery — deployment draft

Status: **not yet tested on physical Raspberry Pi/Hitachi hardware**.
This is a separate read-only inventory task. It does not provide printer
telemetry, enable remote controls or discover unknown network hosts.

## Preconditions

- Raspberry Pi identity has been registered through technician Connect
- Pi retains the BLE-registration private key at `/var/lib/care-inspector/pi-ed25519.key` (0600)
- MFG's FastAPI service is reachable over verified HTTPS
- `careinspector` account can read the Pi key and configured printer targets
- Python dependencies include pymodbus and cryptography

In `/etc/care-inspector/pi-cloud.env`, use the actual MFG URL and target file:

```ini
CARE_INSPECTOR_BACKEND_URL=https://care.example.org
CARE_INSPECTOR_PRINTER_TARGETS=/etc/care-inspector/printers.json
```

Provision `/etc/care-inspector/printers.json` with explicitly authorized IPs:

```json
{
  "printers": [
    {
      "host": "192.168.10.50",
      "port": 502,
      "protocol": "modbus",
      "manufacturer": "Hitachi"
    }
  ]
}
```

The IP is an **example**, not a known real printer address. Make the file
readable by the service account and protect the containing directory from
unapproved modifications. Do not store passwords or tokens in it.

After MFG IT approves and installs the service/timer unit files from
`collector/systemd/`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now care-inspector-printer-discovery.timer
sudo systemctl list-timers care-inspector-printer-discovery.timer
```

The timer triggers 90 seconds after boot, then around five minutes after
each completed run, with up to 30 seconds of randomized delay.

Each run reads only configured printer identities and signs the announcement.
An unavailable printer does **not** cause deletion or reassignment.
Existing GmbH assignment is preserved on repeat announcements.

**Do not install on a production Pi yet.** Validate the hardware, manufacturer
register mapping, service account permissions, outbound HTTPS and enrollment
trust before real deployment. Remote configuration is a separate feature.
