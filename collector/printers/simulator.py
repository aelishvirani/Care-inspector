from datetime import datetime, timezone
from typing import Any, Dict

from pymodbus.client import AsyncModbusTcpClient

from .base import PrinterDriver


class SimulatorPrinter(PrinterDriver):
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1502,
        device_id: int = 1,
        printer_id: str = "hitachi-ux2-simulator-001",
    ):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.printer_id = printer_id

        self.client = AsyncModbusTcpClient(
            host=self.host,
            port=self.port,
        )

        self._control_status = "ready"

    async def connect(self) -> None:
        connected = await self.client.connect()

        if not connected:
            raise ConnectionError(
                f"Could not connect to simulator at "
                f"{self.host}:{self.port}"
            )

    async def disconnect(self) -> None:
        self.client.close()

    async def read_measurement(self) -> Dict[str, Any]:
        result = await self.client.read_input_registers(
            address=0,
            count=7,
            device_id=self.device_id,
        )

        if result.isError():
            raise RuntimeError(
                f"Modbus read failed: {result}"
            )

        registers = result.registers

        status_raw = registers[0]

        print_high = registers[1]
        print_low = registers[2]

        print_count = (
            (print_high << 16)
            | print_low
        )

        temperature = registers[3] / 10.0
        pressure = registers[4] / 1000.0
        ink_level = registers[5]
        makeup_level = registers[6]

        status_map = {
            0: "offline",
            1: "ready",
            2: "printing",
            3: "warning",
            4: "fault",
        }

        measured_status = status_map.get(
            status_raw,
            "unknown",
        )

        status = (
            self._control_status
            if self._control_status
            in {"stopped", "printing"}
            else measured_status
        )

        return {
            "device_id": self.printer_id,
            "source": "simulator",
            "online": True,
            "status": status,
            "print_count": print_count,
            "temperature_c": temperature,
            "pressure_mpa": pressure,
            "ink_level_percent": ink_level,
            "makeup_level_percent": makeup_level,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }


    async def start(self) -> Dict[str, Any]:
        self._control_status = "printing"

        return {
            "success": True,
            "status": self._control_status,
            "message": "Simulator printer started",
        }

    async def stop(self) -> Dict[str, Any]:
        self._control_status = "stopped"

        return {
            "success": True,
            "status": self._control_status,
            "message": "Simulator printer stopped",
        }
