from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from printers.base import PrinterDriver


class HitachiModbusPrinter(PrinterDriver):
    """
    Hitachi UX2 Modbus TCP driver.

    Monitoring stays read-only through Input Registers (function 0x04).
    Explicit start/stop commands use the UX2 Remote operation Holding
    Register documented by Hitachi. No print-job data is modified.
    """

    REG_CONNECTION_STATUS = 0x0000
    REG_RECEIVE_STATUS = 0x0001
    REG_OPERATION_STATUS = 0x0002
    REG_WARNING_STATUS = 0x0003
    REG_OPERATION_DETAIL = 0x0008

    REG_MODEL_NAME = 0x0010
    MODEL_NAME_WORDS = 16

    REG_SERIAL_NUMBER = 0x0020
    SERIAL_NUMBER_WORDS = 2

    REG_INK_NAME = 0x0022
    INK_NAME_WORDS = 10

    REG_INK_OPERATING_TIME = 0x0050
    REG_INK_ALARM_TIME = 0x0051

    REG_PRINT_COUNT = 0x0052
    PRINT_COUNT_WORDS = 2

    REG_CUMULATIVE_OPERATION_TIME = 0x0054
    CUMULATIVE_OPERATION_TIME_WORDS = 2

    REG_INK_TYPE = 0x0056
    REG_INK_VISCOSITY = 0x0057
    REG_INK_PRESSURE = 0x0058
    REG_AMBIENT_TEMPERATURE = 0x0059
    REG_DEFLECTION_VOLTAGE = 0x005A
    REG_EXCITATION_VREF = 0x005B
    REG_EXCITATION_FREQUENCY = 0x005C

    REG_INK_REMAINING = 0x0BEB
    REG_MAKEUP_REMAINING = 0x0BEC

    # Hitachi UX2 Communication User's Manual (Modbus):
    # Holding Register 0x2494, Remote operation.
    # 0 = Operation start, 1 = Operation stop.
    REG_REMOTE_OPERATION = 0x2494
    REMOTE_OPERATION_START = 0
    REMOTE_OPERATION_STOP = 1

    def __init__(
        self,
        host: str,
        port: int = 502,
        device_id: int = 1,
        printer_id: str = "hitachi-ux2-real-001",
    ):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.printer_id = printer_id

        self.client = AsyncModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=5,
        )

    async def connect(self) -> bool:
        return await self.client.connect()

    async def disconnect(self) -> None:
        self.client.close()

    async def _read_input_registers(
        self,
        address: int,
        count: int = 1,
    ) -> list[int]:
        response = await self.client.read_input_registers(
            address=address,
            count=count,
            device_id=self.device_id,
        )

        if response.isError():
            raise RuntimeError(
                f"Modbus error at 0x{address:04X}: {response}"
            )

        return response.registers

    @staticmethod
    def _signed_16(value: int) -> int:
        if value & 0x8000:
            return value - 0x10000

        return value

    @staticmethod
    def _uint32_high_low(
        registers: list[int],
    ) -> int:
        if len(registers) != 2:
            raise ValueError(
                "Expected exactly two registers"
            )

        return (
            (registers[0] << 16)
            | registers[1]
        )

    @staticmethod
    def _decode_chars(registers: list[int]) -> str:
        """
        UX2 character registers contain one character per word.
        """
        chars = []

        for value in registers:
            if value == 0:
                continue

            try:
                chars.append(chr(value))
            except ValueError:
                pass

        return "".join(chars).strip()

    @staticmethod
    def _connection_status(value: int) -> str:
        mapping = {
            0x0030: "offline",
            0x0031: "online",
        }

        return mapping.get(
            value,
            f"unknown_0x{value:04X}",
        )

    @staticmethod
    def _receive_status(value: int) -> str:
        mapping = {
            0x0030: "reception_not_possible",
            0x0031: "reception_possible",
        }

        return mapping.get(
            value,
            f"unknown_0x{value:04X}",
        )

    @staticmethod
    def _operation_detail(value: int) -> str:
        mapping = {
            0x0030: "stopped",
            0x00F0: "starting",
            0x00F1: "drop_adjust",
            0x00F2: "cover_open",
            0x00F3: "service",
            0x00F4: "ink_heating",
            0x00F5: "sleep",
        }

        return mapping.get(
            value,
            f"raw_0x{value:04X}",
        )

    @staticmethod
    def _remaining_level(value: int) -> dict[str, Any]:
        if value == 0x0E:
            label = "empty"

        elif value == 0x0F:
            label = "full"

        elif 0x01 <= value <= 0x06:
            label = f"level_{value}"

        else:
            label = f"unknown_0x{value:04X}"

        return {
            "raw": value,
            "label": label,
        }

    async def read_identity(self) -> dict[str, Any]:
        model_regs = await self._read_input_registers(
            self.REG_MODEL_NAME,
            self.MODEL_NAME_WORDS,
        )

        serial_regs = await self._read_input_registers(
            self.REG_SERIAL_NUMBER,
            self.SERIAL_NUMBER_WORDS,
        )

        ink_regs = await self._read_input_registers(
            self.REG_INK_NAME,
            self.INK_NAME_WORDS,
        )

        return {
            "model_name": self._decode_chars(
                model_regs
            ),

            "serial_number_raw_words": serial_regs,

            "serial_number": self._uint32_high_low(
                serial_regs
            ),

            "ink_name": self._decode_chars(
                ink_regs
            ),
        }

    async def read_operation_data(
        self,
    ) -> dict[str, Any]:
        ink_operating_time = (
            await self._read_input_registers(
                self.REG_INK_OPERATING_TIME
            )
        )[0]

        ink_alarm_time = (
            await self._read_input_registers(
                self.REG_INK_ALARM_TIME
            )
        )[0]

        print_count_regs = (
            await self._read_input_registers(
                self.REG_PRINT_COUNT,
                self.PRINT_COUNT_WORDS,
            )
        )

        cumulative_operation_regs = (
            await self._read_input_registers(
                self.REG_CUMULATIVE_OPERATION_TIME,
                self.CUMULATIVE_OPERATION_TIME_WORDS,
            )
        )

        ink_type = (
            await self._read_input_registers(
                self.REG_INK_TYPE
            )
        )[0]

        viscosity = (
            await self._read_input_registers(
                self.REG_INK_VISCOSITY
            )
        )[0]

        pressure_raw = (
            await self._read_input_registers(
                self.REG_INK_PRESSURE
            )
        )[0]

        temperature_raw = (
            await self._read_input_registers(
                self.REG_AMBIENT_TEMPERATURE
            )
        )[0]

        deflection_raw = (
            await self._read_input_registers(
                self.REG_DEFLECTION_VOLTAGE
            )
        )[0]

        excitation_vref = (
            await self._read_input_registers(
                self.REG_EXCITATION_VREF
            )
        )[0]

        excitation_frequency_raw = (
            await self._read_input_registers(
                self.REG_EXCITATION_FREQUENCY
            )
        )[0]

        return {
            "ink_operating_time_hours":
                ink_operating_time,

            "ink_alarm_time_hours":
                ink_alarm_time,

            "print_count_raw_words":
                print_count_regs,

            "print_count":
                self._uint32_high_low(
                    print_count_regs
                ),

            "cumulative_operation_time_raw_words":
                cumulative_operation_regs,

            "cumulative_operation_time_hours":
                self._uint32_high_low(
                    cumulative_operation_regs
                ),

            "ink_type": ink_type,

            "ink_viscosity_raw":
                viscosity,

            "ink_pressure_raw":
                pressure_raw,

            "ink_pressure_mpa":
                pressure_raw / 1000.0,

            "ambient_temperature_raw":
                temperature_raw,

            "ambient_temperature_c":
                self._signed_16(
                    temperature_raw
                ),

            "deflection_voltage_raw":
                deflection_raw,

            "deflection_voltage_kv":
                deflection_raw / 10.0,

            "excitation_vref":
                excitation_vref,

            "excitation_frequency_raw":
                excitation_frequency_raw,

            "excitation_frequency_khz":
                excitation_frequency_raw
                / 10.0,
        }

    async def read_raw_status(
        self,
    ) -> dict[str, Any]:
        connection = (
            await self._read_input_registers(
                self.REG_CONNECTION_STATUS
            )
        )[0]

        receive = (
            await self._read_input_registers(
                self.REG_RECEIVE_STATUS
            )
        )[0]

        operation = (
            await self._read_input_registers(
                self.REG_OPERATION_STATUS
            )
        )[0]

        warning = (
            await self._read_input_registers(
                self.REG_WARNING_STATUS
            )
        )[0]

        operation_detail = (
            await self._read_input_registers(
                self.REG_OPERATION_DETAIL
            )
        )[0]

        ink_remaining_raw = (
            await self._read_input_registers(
                self.REG_INK_REMAINING
            )
        )[0]

        makeup_remaining_raw = (
            await self._read_input_registers(
                self.REG_MAKEUP_REMAINING
            )
        )[0]

        identity = await self.read_identity()

        operation_data = (
            await self.read_operation_data()
        )

        return {
            "connection_status_raw":
                connection,

            "connection_status":
                self._connection_status(
                    connection
                ),

            "receive_status_raw":
                receive,

            "receive_status":
                self._receive_status(
                    receive
                ),

            "operation_status_raw":
                operation,

            "warning_status_raw":
                warning,

            "operation_detail_raw":
                operation_detail,

            "operation_detail":
                self._operation_detail(
                    operation_detail
                ),

            "ink_remaining":
                self._remaining_level(
                    ink_remaining_raw
                ),

            "makeup_remaining":
                self._remaining_level(
                    makeup_remaining_raw
                ),

            **identity,
            **operation_data,
        }


    async def _write_remote_operation(
        self,
        value: int,
    ) -> None:
        connection = (
            await self._read_input_registers(
                self.REG_CONNECTION_STATUS
            )
        )[0]

        if self._connection_status(
            connection
        ) != "online":
            raise RuntimeError(
                "Hitachi printer is offline; "
                "remote operation is not allowed"
            )

        response = await self.client.write_register(
            address=self.REG_REMOTE_OPERATION,
            value=value,
            device_id=self.device_id,
        )

        if response.isError():
            raise RuntimeError(
                "Hitachi remote-operation "
                f"write failed: {response}"
            )

    async def start(self) -> dict[str, Any]:
        await self._write_remote_operation(
            self.REMOTE_OPERATION_START
        )

        return {
            "success": True,
            "message": "Hitachi operation start command accepted",
        }

    async def stop(self) -> dict[str, Any]:
        await self._write_remote_operation(
            self.REMOTE_OPERATION_STOP
        )

        return {
            "success": True,
            "message": "Hitachi operation stop command accepted",
        }

    async def read_measurement(
        self,
    ) -> dict[str, Any]:
        data = await self.read_raw_status()

        online = (
            data["connection_status"]
            == "online"
        )

        return {
            "device_id":
                self.printer_id,

            "source":
                "hitachi_modbus",

            "online":
                online,

            "status":
                data["operation_detail"],

            "print_count":
                data["print_count"],

            "ink_operating_time_hours":
                data[
                    "ink_operating_time_hours"
                ],

            "cumulative_operation_time_hours":
                data[
                    "cumulative_operation_time_hours"
                ],

            "temperature_c":
                data[
                    "ambient_temperature_c"
                ],

            "pressure_mpa":
                data[
                    "ink_pressure_mpa"
                ],

            "ink_level_percent":
                None,

            "makeup_level_percent":
                None,

            "model_name":
                data["model_name"],

            "serial_number_raw_words":
                data[
                    "serial_number_raw_words"
                ],

            "serial_number":
                data[
                    "serial_number"
                ],

            "ink_name":
                data["ink_name"],

            "print_count_raw_words":
                data[
                    "print_count_raw_words"
                ],

            "ink_remaining_raw":
                data[
                    "ink_remaining"
                ]["raw"],

            "ink_remaining_label":
                data[
                    "ink_remaining"
                ]["label"],

            "makeup_remaining_raw":
                data[
                    "makeup_remaining"
                ]["raw"],

            "makeup_remaining_label":
                data[
                    "makeup_remaining"
                ]["label"],

            "warning_status_raw":
                data[
                    "warning_status_raw"
                ],

            "operation_status_raw":
                data[
                    "operation_status_raw"
                ],

            "deflection_voltage_kv":
                data[
                    "deflection_voltage_kv"
                ],

            "excitation_frequency_khz":
                data[
                    "excitation_frequency_khz"
                ],

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }