# Care-Inspector Raspberry Pi Bluetooth identity protocol (draft)

This is a compatibility contract for the future Raspberry Pi BLE agent. The
browser implementation is in `frontend/src/bluetooth/piIdentity.js`.

## Transport

Use Bluetooth LE GATT, not Bluetooth Classic. The Pi must advertise a
discoverable GATT service (without requiring a special device name):

- Service UUID: `a18d7b10-f0e7-4d5e-8c1b-86e418d85001`
- Read-only Identity characteristic UUID:
  `a18d7b11-f0e7-4d5e-8c1b-86e418d85001`

The characteristic returns UTF-8 JSON, **at most 512 bytes**, e.g.:

```json
{
  "hardware_id": "pi-00000000abcdef12",
  "hostname": "raspberrypi",
  "model": "Raspberry Pi 4 Model B",
  "mac_address": "dc:a6:32:12:34:56",
  "protocol_version": "1"
}
```

Values above are examples only. The MAC is informational, not an authentication
secret, and should correspond to the Pi interface being reported.

A BLE characteristic is typically small; ensure the agent supports reads with
the required ATT long-read behaviour, or reduce the payload. Do not put
credentials, pairing tokens, or Wi-Fi passwords in this read-only characteristic.

## Scope and trust

- The Chrome picker must be triggered by user interaction. Without a filter,
  Chrome may show unrelated nearby Bluetooth devices.
- Browsers do not disclose Bluetooth MAC addresses to webpages. A Pi agent can
  report its own interface addresses, but they must not be treated as proof of
  identity.
- The BLE UUID and the JSON payload are **not proof** that the other device is a
  genuine Pi or belongs to MFG. Both can be copied.
- The UI must not enable `Connect` based on these fields.
- Secure pairing requires a separately designed challenge-response protocol,
  device key provisioning/ownership checks, cloud enrollment, rotation/revocation,
  and authorization. Do not transmit printer commands via this discovery route.
- Bluetooth is used locally to select and enroll hardware. Once securely enrolled,
  the Pi agent will maintain its own authenticated cloud connection over Wi-Fi,
  Ethernet, or 5G. Narrowband suitability must be verified per modem/service.

## Current status

The browser reads the identity characteristic when `Check Pi` is clicked.
**No Raspberry Pi GATT server advertising these UUIDs is installed or available
in this repository yet.** The current `pi_discovery_agent.py` is mDNS-only,
not BLE. This document is an implementation specification, not proof of working
hardware discovery.
