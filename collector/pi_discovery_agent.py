"""Run on Raspberry Pi to advertise a *discovery-only* service over LAN.

Example: python collector/pi_discovery_agent.py
Does not expose printer controls, tokens, or a pairing endpoint.
"""
import ipaddress
import platform
import socket
import time
import uuid
from zeroconf import IPVersion, ServiceInfo, Zeroconf

SERVICE_TYPE = "_care-inspector._tcp.local."


def get_mac():
    value = uuid.getnode()
    return ":".join(f"{(value >> (8 * offset)) & 255:02x}" for offset in range(5, -1, -1))


def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(('192.0.2.1', 9))
        return sock.getsockname()[0]


def main():
    hostname = socket.gethostname()
    name = f"{hostname}.{SERVICE_TYPE}"
    info = ServiceInfo(
        SERVICE_TYPE,
        name,
        server=f"{hostname}.local.",
        port=8766,
        addresses=[ipaddress.ip_address(get_local_ip()).packed],
        properties={
            "name": hostname,
            "model": platform.machine(),
            "mac": get_mac(),
        },
    )
    zc = Zeroconf(ip_version=IPVersion.All)
    try:
        zc.register_service(info)
        print(f"Advertising {name} on the local network (discovery only)")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        zc.unregister_service(info)
        zc.close()


if __name__ == "__main__":
    main()
