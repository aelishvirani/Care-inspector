from __future__ import annotations

import asyncio
import json
import logging
import os

import websockets

from config import load_configuration
from offline_queue import OfflineQueue
from printers.simulator import (
    SimulatorPrinter,
)
from printers.hitachi_modbus import (
    HitachiModbusPrinter,
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


BACKEND_BASE = os.getenv(
    "CARE_INSPECTOR_BACKEND_WS",
    "ws://127.0.0.1:8000",
).rstrip("/")

BACKEND_RETRY_SECONDS = 5
ACK_TIMEOUT_SECONDS = 10


def build_printer(
    configuration,
):
    mode = configuration[
        "printer_mode"
    ]

    host = configuration[
        "printer_host"
    ]

    port = int(
        configuration[
            "printer_port"
        ]
    )

    device_id = int(
        configuration[
            "device_id"
        ]
    )

    if mode == "simulator":
        return SimulatorPrinter(
            host=host,
            port=port,
            device_id=device_id,
            printer_id=(
                "hitachi-ux2-"
                "simulator-001"
            ),
        )

    if mode == "hitachi_modbus":
        return HitachiModbusPrinter(
            host=host,
            port=port,
            device_id=device_id,
            printer_id=(
                "hitachi-ux2-real-001"
            ),
        )

    raise ValueError(
        f"Unsupported printer mode: "
        f"{mode}"
    )


async def collect_measurements(
    printer,
    queue: OfflineQueue,
    interval: int,
    printer_lock: asyncio.Lock,
):
    while True:
        async with printer_lock:
            measurement = (
                await printer
                .read_measurement()
            )

        queue_id = queue.enqueue(
            measurement
        )

        logging.info(
            "Measurement queued | "
            "queue_id=%s | "
            "source=%s | "
            "status=%s | "
            "prints=%s | "
            "temp=%s C | "
            "pressure=%s MPa | "
            "pending=%s",
            queue_id,
            measurement.get(
                "source"
            ),
            measurement.get(
                "status"
            ),
            measurement.get(
                "print_count"
            ),
            measurement.get(
                "temperature_c"
            ),
            measurement.get(
                "pressure_mpa"
            ),
            queue.count(),
        )

        await asyncio.sleep(
            interval
        )


async def send_pending_measurements(
    backend_ws: str,
    queue: OfflineQueue,
):
    while True:
        try:
            async with websockets.connect(
                backend_ws
            ) as websocket:

                logging.info(
                    "Connected to "
                    "Care-Inspector backend"
                )

                while True:
                    pending = (
                        queue.get_pending(
                            limit=100
                        )
                    )

                    if not pending:
                        await asyncio.sleep(
                            1
                        )

                        continue

                    for (
                        queue_id,
                        measurement,
                    ) in pending:

                        await websocket.send(
                            json.dumps(
                                measurement
                            )
                        )

                        raw_ack = (
                            await asyncio
                            .wait_for(
                                websocket.recv(),
                                timeout=(
                                    ACK_TIMEOUT_SECONDS
                                ),
                            )
                        )

                        ack = json.loads(
                            raw_ack
                        )

                        if (
                            ack.get("status")
                            != "stored"
                        ):
                            raise RuntimeError(
                                "Backend did not "
                                "confirm storage"
                            )

                        queue.delete(
                            queue_id
                        )

                        logging.info(
                            "Measurement delivered | "
                            "queue_id=%s | "
                            "status=%s | "
                            "prints=%s | "
                            "remaining=%s",
                            queue_id,
                            measurement.get(
                                "status"
                            ),
                            measurement.get(
                                "print_count"
                            ),
                            queue.count(),
                        )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            logging.warning(
                "Backend unavailable | "
                "%s",
                exc,
            )

            logging.info(
                "Measurements remain "
                "stored locally | "
                "pending=%s",
                queue.count(),
            )

            await asyncio.sleep(
                BACKEND_RETRY_SECONDS
            )




async def handle_control_commands(
    backend_control_ws: str,
    printer,
    printer_lock: asyncio.Lock,
):
    while True:
        try:
            async with websockets.connect(
                backend_control_ws
            ) as websocket:
                logging.info(
                    "Printer control channel "
                    "connected"
                )

                while True:
                    raw_message = (
                        await websocket.recv()
                    )

                    payload = json.loads(
                        raw_message
                    )

                    if (
                        payload.get("type")
                        != "printer_command"
                    ):
                        continue

                    command_id = payload.get(
                        "command_id"
                    )

                    command = (
                        payload.get(
                            "command",
                            "",
                        )
                        .strip()
                        .lower()
                    )

                    try:
                        async with printer_lock:
                            if command == "start":
                                result = (
                                    await printer.start()
                                )

                            elif command == "stop":
                                result = (
                                    await printer.stop()
                                )

                            else:
                                raise ValueError(
                                    "Unsupported printer "
                                    f"command: {command}"
                                )

                            await asyncio.sleep(
                                1
                            )

                            measurement = (
                                await printer
                                .read_measurement()
                            )

                        status = (
                            measurement.get(
                                "status"
                            )
                        )

                        logging.info(
                            "Printer command completed | "
                            "command=%s | status=%s",
                            command,
                            status,
                        )

                        await websocket.send(
                            json.dumps(
                                {
                                    "type":
                                        "command_result",
                                    "command_id":
                                        command_id,
                                    "success":
                                        True,
                                    "command":
                                        command,
                                    "status":
                                        status,
                                    "message":
                                        result.get(
                                            "message",
                                            (
                                                "Printer command "
                                                "completed"
                                            ),
                                        ),
                                }
                            )
                        )

                    except Exception as exc:
                        logging.error(
                            "Printer command failed | "
                            "command=%s | error=%s",
                            command,
                            exc,
                        )

                        await websocket.send(
                            json.dumps(
                                {
                                    "type":
                                        "command_result",
                                    "command_id":
                                        command_id,
                                    "success":
                                        False,
                                    "command":
                                        command,
                                    "error":
                                        str(exc),
                                }
                            )
                        )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            logging.warning(
                "Control channel unavailable | "
                "%s",
                exc,
            )

            await asyncio.sleep(
                BACKEND_RETRY_SECONDS
            )


async def run_collector():
    while True:
        printer = None

        try:
            configuration = (
                load_configuration()
            )

            interval = int(
                configuration[
                    "collector_interval_seconds"
                ]
            )

            printer = build_printer(
                configuration
            )

            device_name = (
                printer.printer_id
            )

            backend_ws = (
                f"{BACKEND_BASE}/"
                f"ws/collector/"
                f"{device_name}"
            )

            backend_control_ws = (
                f"{BACKEND_BASE}/"
                f"ws/collector-control/"
                f"{device_name}"
            )

            queue = OfflineQueue()
            printer_lock = asyncio.Lock()

            logging.info(
                "Loaded configuration | "
                "mode=%s | host=%s | "
                "port=%s | "
                "device_id=%s | "
                "interval=%ss",
                configuration[
                    "printer_mode"
                ],
                configuration[
                    "printer_host"
                ],
                configuration[
                    "printer_port"
                ],
                configuration[
                    "device_id"
                ],
                interval,
            )

            logging.info(
                "Offline queue ready | "
                "pending=%s",
                queue.count(),
            )

            connected = (
                await printer.connect()
            )

            if connected is False:
                raise ConnectionError(
                    "Could not connect "
                    "to printer"
                )

            logging.info(
                "Connected to printer | "
                "mode=%s | device=%s",
                configuration[
                    "printer_mode"
                ],
                device_name,
            )

            collector_task = (
                asyncio.create_task(
                    collect_measurements(
                        printer,
                        queue,
                        interval,
                        printer_lock,
                    )
                )
            )

            sender_task = (
                asyncio.create_task(
                    send_pending_measurements(
                        backend_ws,
                        queue,
                    )
                )
            )

            control_task = (
                asyncio.create_task(
                    handle_control_commands(
                        backend_control_ws,
                        printer,
                        printer_lock,
                    )
                )
            )

            done, pending = (
                await asyncio.wait(
                    {
                        collector_task,
                        sender_task,
                        control_task,
                    },
                    return_when=(
                        asyncio
                        .FIRST_EXCEPTION
                    ),
                )
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True,
            )

            for task in done:
                exception = (
                    task.exception()
                )

                if exception:
                    raise exception

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            logging.error(
                "Collector runtime "
                "error: %s",
                exc,
            )

            logging.info(
                "Restarting collector "
                "in 5 seconds..."
            )

            await asyncio.sleep(5)

        finally:
            if printer is not None:
                try:
                    await printer.disconnect()

                except Exception:
                    pass


if __name__ == "__main__":
    asyncio.run(
        run_collector()
    )
