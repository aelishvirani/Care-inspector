# Raspberry Pi signed cloud heartbeat — deployment draft

Status: macOS unit tests only; not yet installed or tested on real Raspberry Pi hardware.

## Preconditions

- Technician explicitly registered this Pi through Care-Inspector → Raspberry Pi → Connect
- The Pi retains the exact Ed25519 key used during BLE registration
- `/var/lib/care-inspector/pi-ed25519.key` exists and is accessible only to the dedicated service account (0600)
- The Pi has outbound access to the MFG backend over HTTPS with a valid certificate
- The Linux image has Python 3 and `cryptography` installed

**Do not use the developer laptop's localhost URL on a remote Pi.**

## Prepare the Pi

Install the source to `/opt/care-inspector` and configure the service account (`careinspector`) with key-file read permissions. Verify with MFG IT before production installation.

Create `/etc/care-inspector/pi-cloud.env` (root-owned, 0640, readable by the service account):

```ini
CARE_INSPECTOR_BACKEND_URL=https://care.example.org
CARE_INSPECTOR_PI_HEARTBEAT_SECONDS=60
```

Replace the example domain with MFG's actual HTTPS deployment URL. No secret/token is needed in this file; the private key stays on the Pi.

Review `collector/systemd/care-inspector-cloud-heartbeat.service`, then install it to `/etc/systemd/system/`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now care-inspector-cloud-heartbeat.service
sudo systemctl status care-inspector-cloud-heartbeat.service
```

The service begins at boot, makes a fresh key-signed authentication request each minute, and backs off after transient network failures.

## Backend

A successful proof updates `pi_heartbeats.last_authenticated_at`. A Technician/Admin can inspect signed check-in timestamps through `GET /api/pi-auth/devices`.

This is **proof of a recent signed check-in, not a continuously open socket, telemetry session, or printer connection**. It does not yet register discovered printer inventory, receive remote configuration, or authorize commands.

**Never install the service on a production Pi until the BLE registration and cloud pairing flow has been tested on that actual device and its private key can be securely retained.**
