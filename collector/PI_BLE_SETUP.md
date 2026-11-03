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
sudo apt install bluez python3-dbus python3-gi
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
