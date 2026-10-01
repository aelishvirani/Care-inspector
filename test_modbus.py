import asyncio

from pymodbus.client import AsyncModbusTcpClient


async def main():
    client = AsyncModbusTcpClient(
        host="127.0.0.1",
        port=1502,
    )

    connected = await client.connect()

    if not connected:
        print("❌ Could not connect to simulator")
        return

    print("✅ Connected to simulator")

    result = await client.read_input_registers(
        address=0,
        count=7,
        device_id=1,
    )

    if result.isError():
        print("❌ Modbus error:", result)
    else:
        print("✅ Registers:", result.registers)

    client.close()


asyncio.run(main())
