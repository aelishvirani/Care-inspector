import asyncio
import logging
import random

from pymodbus.server import StartAsyncTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

HOST = "127.0.0.1"
PORT = 1502
DEVICE_ID = 1


class PrinterState:
    def __init__(self):
        self.print_count = 12_540

    def generate_registers(self):
        self.print_count += random.randint(1, 3)

        temperature = round(random.uniform(23.0, 28.0), 1)
        pressure = round(random.uniform(0.245, 0.262), 3)
        ink_level = random.randint(65, 95)
        makeup_level = random.randint(55, 90)

        high = (self.print_count >> 16) & 0xFFFF
        low = self.print_count & 0xFFFF

        registers = [
            1,                      # 0 READY
            high,                   # 1 print count high
            low,                    # 2 print count low
            int(temperature * 10),  # 3 temperature x10
            int(pressure * 1000),   # 4 pressure x1000
            ink_level,              # 5 ink %
            makeup_level,           # 6 makeup %
        ]

        return (
            registers,
            temperature,
            pressure,
            ink_level,
            makeup_level,
        )


printer = PrinterState()


async def simulator_action(
    function_code,
    start_address,
    address,
    count,
    current_registers,
    set_values,
):
    # We only generate dynamic values for read requests.
    if set_values is not None:
        return None

    (
        registers,
        temperature,
        pressure,
        ink_level,
        makeup_level,
    ) = printer.generate_registers()

    for i, value in enumerate(registers):
        if i < len(current_registers):
            current_registers[i] = value

    logging.info(
        "READ FC=%s | Printer READY | prints=%d | "
        "temp=%.1f C | pressure=%.3f MPa | "
        "ink=%d%% | makeup=%d%%",
        function_code,
        printer.print_count,
        temperature,
        pressure,
        ink_level,
        makeup_level,
    )

    return None


async def main():
    register_block = SimData(
        address=0,
        count=100,
        values=0,
        datatype=DataType.REGISTERS,
        readonly=True,
    )

    device = SimDevice(
        id=DEVICE_ID,
        simdata=[register_block],
        action=simulator_action,
    )

    logging.info(
        "Starting Care-Inspector simulator on %s:%d (device id %d)",
        HOST,
        PORT,
        DEVICE_ID,
    )

    await StartAsyncTcpServer(
        context=device,
        address=(HOST, PORT),
    )


if __name__ == "__main__":
    asyncio.run(main())
