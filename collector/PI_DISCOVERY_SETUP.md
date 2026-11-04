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
trust before real deployment. Cloud target retrieval is an optional, independently authenticated feature; it does not enable printer control.

## Optional cloud target configuration (not yet hardware-tested)

The existing local JSON target file remains the default. To enable signed
in-memory configuration retrieval for the registered Pi, MFG IT may add:

```ini
CARE_INSPECTOR_PRINTER_CONFIG_SOURCE=cloud
```

A technician or admin first stages targets using
`PUT /api/secure/management/pi-targets/{hardware_id}` with the current
`expected_version`. The Pi obtains its own settings via an Ed25519-signed,
one-use `POST /api/pi-config/fetch` request; it **does not** use a technician
JWT, persist cloud settings locally, or grant monitoring/control permissions.
Invalid or unreachable cloud configuration fails closed: the runner does not
fall back to arbitrary local targets or scan the network. Remove the setting
(or set `local`) to return to the old local-file configuration.

## Experimental single-printer direct Ethernet detection

Care-Inspector now supports an **opt-in** passive direct-link source for a
dedicated Pi-to-Hitachi Ethernet cable:

```ini
CARE_INSPECTOR_PRINTER_CONFIG_SOURCE=direct-link
CARE_INSPECTOR_PRINTER_INTERFACE=eth0
```

The agent reads only Linux's existing neighbor table on the selected interface.
It does not scan subnets, open arbitrary ports or change the Pi's IP settings.
It refuses to operate when that interface has a default route or when more
than one candidate peer is found. A single candidate must then pass the
existing **read-only Hitachi Modbus identity probe** before a signed inventory
announcement is made. No customer assignment or printer controls are enabled.

**Limitations:** A connected printer may not appear in the neighbor table
until the operating system has already exchanged traffic with it. This
method cannot reliably detect an unknown, silent printer on a different IP
subnet. Physical Pi/Hitachi validation and an approved addressing/onboarding
strategy remain necessary; do not enable this experimental mode in production
without MFG IT review. The normal local-file behavior remains unchanged.

## Optional signed Pi telemetry worker (new; **not hardware-tested**)

The separate `collector.pi_telemetry_service` uses the existing single-printer
target selection, confirms the printer identity, constructs an allowlisted
driver, and sends normalized readings over the signed HTTPS telemetry API.
Only the Hitachi Modbus driver is currently approved; further brands need
their own read-only driver and identity probe, **not** a new telemetry service.

The worker is not enabled automatically. It does not run the simulator,
legacy collector WebSocket, or printer start/stop commands.

Before enabling it, MFG must validate the Pi's registered private key,
printer identity/assignment in the backend, verified HTTPS, available
Modbus network addressing, and the hardware with a read-only test.
One Pi can report only its own already-discovered and customer-assigned printer.
Unassigned devices are rejected by the backend and no controls are enabled.

The optional unit `collector/systemd/care-inspector-pi-telemetry.service`
uses the existing `/etc/care-inspector/pi-cloud.env`, with an optional
`CARE_INSPECTOR_PI_TELEMETRY_SECONDS=5` interval. It accepts the same
`CARE_INSPECTOR_PRINTER_CONFIG_SOURCE` sources as printer discovery.
The service currently **does not** implement an offline persistent queue;
it sends one fresh reading at a time, retrying connectivity and printer
disconnections after a delay rather than resending stale samples.
A cloud permission rejection stops the service for technician review.

**Do not deploy or enable this unit on production hardware yet.**
