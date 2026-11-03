# Raspberry Pi BLE identity agent — installation draft

Status: Implemented in source, **not yet tested on a Raspberry Pi**.
The agent does not pair with the cloud or detect printers. It exposes
read-only hardware identity to a Chrome laptop nearby.

## Hardware/OS requirements
- Raspberry Pi with working BLE adapter and Raspberry Pi OS with BlueZ
- The agent is Linux-only; do not run it on the Mac
- Chrome on the technician's laptop, on HTTPS or localhost

## First-time setup on Raspberry Pi

Review the software and permissions with MFG IT first. Example Debian/Raspberry
Pi OS packages:

```bash
sudo apt update
sudo apt install bluez python3-dbus python3-gi python3-cryptography
```

Install the project source at `/opt/care-inspector` and create a dedicated
`careinspector` service account with the required system D-Bus permission.
Don't grant unrestricted system-bus access. The systemd unit template is in
`collector/systemd/care-inspector-ble.service`; review its account/path
settings before copying it to `/etc/systemd/system/`.

After review and installation:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now care-inspector-ble.service
sudo systemctl status care-inspector-ble.service
```

## Browser check

1. Open Care-Inspector → Raspberry Pi on the technician laptop.
2. Click Search Nearby, select the nearby Pi from Chrome's picker.
3. Click Check Pi. If GATT works, the Info popup displays the **untrusted**
   hardware information read through Bluetooth.

The code does not require the Pi to be named `CareInspector-`. Browser MAC
addresses remain unavailable; a matching BLE service alone does not prove
hardware ownership.

## Security and operational notes

- No pairing credentials, cloud secrets, or printer commands are exposed
  via this BLE service.
- Identity fields may be impersonated; don't enable the Connect button based
  solely on BLE identity.
- Cloud enrollment must include cryptographic device authentication, key
  provisioning, credential revocation, authorization and auditing.
- A successful initial setup should be followed by separate agent software
  for reporting printer metadata and measurements over an authenticated
  outbound cloud connection.
- Hardware discovery and compatibility remain to be tested. Bluetooth
  advertisement support, adapter configuration, DBus permissions, and
  long GATT reads vary between images.


## Development pairing proof transport (not cloud enrollment)

The BLE service now exposes additional GATT characteristics within the same
Care-Inspector service UUID:

- `a18d7b12-f0e7-4d5e-8c1b-86e418d85001`: read Ed25519 public key (base64)
- `a18d7b13-f0e7-4d5e-8c1b-86e418d85001`: write UTF-8 JSON pairing challenge
- `a18d7b14-f0e7-4d5e-8c1b-86e418d85001`: read response signature (base64)

The challenge JSON has exactly `pairing_id`, `hardware_id`, and
`challenge_b64` keys. The signing bytes match the server-side
`backend/app/pi_pairing_crypto.py` contract.

The key is generated on the Pi at
`/var/lib/care-inspector/pi-ed25519.key`, mode 0600.
Provision `/var/lib/care-inspector` as a directory owned by the dedicated
service account, mode 0700, before starting the service. Keep this key
outside Git and never expose it to the browser.

This implementation is a development bridge only. It signs remote challenges
even for unauthenticated BLE clients. Without a physical presence confirmation,
trusted public-key enrollment, and stronger Bluetooth session isolation, it must
not permit cloud registration, remote control, or access to production secrets.
The proof characteristic is shared per running agent and may be overwritten by
concurrent connections; production implementation must bind challenge/proof to
each authorized BLE connection, limit attempts, and implement suitable rate
limits. This code has not been tested on real Pi Bluetooth hardware.
