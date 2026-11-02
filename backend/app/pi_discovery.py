"""Read-only LAN discovery of Care-Inspector Raspberry Pi agents via DNS-SD.

Discovery advertisements are untrusted; do not use addresses or MACs for
authentication, backend connections, or control.
"""
import asyncio
import ipaddress

from fastapi import APIRouter, Depends, HTTPException

from .auth import get_current_user, require_technician
from .models import User

router = APIRouter(prefix="/api/secure/management/raspberry-pis", tags=["raspberry-pi"])
SERVICE_TYPE = "_care-inspector._tcp.local."


def _scan_lan_sync() -> list[dict]:
    try:
        from zeroconf import ServiceBrowser, Zeroconf
    except ImportError as exc:
        raise RuntimeError("zeroconf dependency not installed") from exc

    import time

    zc = Zeroconf()
    candidates = set()

    class Listener:
        def add_service(self, zc, type_, name):
            candidates.add(name)
        def update_service(self, zc, type_, name):
            candidates.add(name)
        def remove_service(self, zc, type_, name):
            candidates.discard(name)

    try:
        browser = ServiceBrowser(zc, SERVICE_TYPE, Listener())
        time.sleep(2.0)
        result = []
        for name in sorted(candidates):
            info = zc.get_service_info(SERVICE_TYPE, name, timeout=800)
            if info is None:
                continue
            properties = {
                key.decode(errors="replace"): value.decode(errors="replace")
                for key, value in info.properties.items()
            }
            ip_candidates = []
            for address in info.parsed_addresses():
                try:
                    ip = ipaddress.ip_address(address)
                    if ip.is_private or ip.is_link_local:
                        ip_candidates.append(str(ip))
                except ValueError:
                    continue
            if not ip_candidates:
                continue
            result.append({
                "service_name": name,
                "display_name": properties.get("name", name.split(".")[0])[:100],
                "hostname": (info.server or "").rstrip(".")[:255],
                "ip_addresses": ip_candidates,
                "port": info.port,
                "mac_address": properties.get("mac", ""),
                "model": properties.get("model", ""),
                "pairing_status": "unverified",
            })
        return result
    finally:
        zc.close()


@router.get("/nearby")
async def nearby_raspberry_pis(user: User = Depends(get_current_user)):
    require_technician(user)
    try:
        devices = await asyncio.to_thread(_scan_lan_sync)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    return {"devices": devices, "discovery": "local-network-mdns", "pairing_available": False}
