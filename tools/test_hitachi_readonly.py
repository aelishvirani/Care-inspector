import asyncio
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_DIR = PROJECT_ROOT / "collector"

sys.path.insert(0, str(COLLECTOR_DIR))

from printers.hitachi_modbus import HitachiModbusPrinter


async def main():
    host = os.getenv("HITACHI_IP", "192.168.50.1")
    port = int(os.getenv("HITACHI_PORT", "502"))
    device_id = int(os.getenv("HITACHI_DEVICE_ID", "1"))

    print()
    print("Care-Inspector Hitachi UX2 read-only test")
    print("-----------------------------------------")
    print(f"Printer IP : {host}")
    print(f"Port       : {port}")
    print(f"Device ID  : {device_id}")
    print("Mode       : READ ONLY")
    print()

    printer = HitachiModbusPrinter(
        host=host,
        port=port,
        device_id=device_id,
        printer_id="hitachi-ux2-real-001",
    )

    try:
        connected = await printer.connect()

        if not connected:
            print("❌ Could not connect to Hitachi UX2.")
            return

        print("✅ TCP connection established.")
        print("📥 Reading UX2 Input Registers...")
        print()

        data = await printer.read_raw_status()

        for key, value in data.items():
            print(f"{key:30} : {value}")

        print()
        print("✅ Read-only Modbus test completed.")

    except Exception as exc:
        print()
        print(f"❌ Test failed: {exc}")

    finally:
        await printer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())