from __future__ import annotations

import asyncio
import json
import math
import os
from datetime import datetime, timezone

import websockets


BACKEND_BASE = os.getenv(
    "CARE_INSPECTOR_BACKEND_WS",
    "ws://127.0.0.1:8000",
).rstrip("/")

INTERVAL_SECONDS = 5
ACK_TIMEOUT_SECONDS = 10


DEMO_PRINTERS = [
    {
        "device_id": "demo-printer-002",
        "model_name": "UX-D160W",
        "serial_number": 1552607,
        "ink_name": "1072K",
        "start_print_count": 84500,
        "ink_operating_time_hours": 950,
        "cumulative_operation_time_hours": 18200,
        "base_temperature": 23.5,
        "base_pressure": 0.248,
        "ink_remaining_raw": 5,
        "ink_remaining_label": "level_5",
        "makeup_remaining_raw": 4,
        "makeup_remaining_label": "level_4",
        "ink_level_percent": 88,
        "makeup_level_percent": 76,
    },
    {
        "device_id": "demo-printer-003",
        "model_name": "UX-D110W",
        "serial_number": 1552608,
        "ink_name": "1067K",
        "start_print_count": 45210,
        "ink_operating_time_hours": 710,
        "cumulative_operation_time_hours": 12950,
        "base_temperature": 25.2,
        "base_pressure": 0.247,
        "ink_remaining_raw": 2,
        "ink_remaining_label": "level_2",
        "makeup_remaining_raw": 3,
        "makeup_remaining_label": "level_3",
        "ink_level_percent": 35,
        "makeup_level_percent": 48,
    },
]


def utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def build_measurement(
    printer: dict,
    cycle: int,
) -> dict:
    device_id = printer[
        "device_id"
    ]

    temperature_wave = (
        math.sin(
            cycle / 8
        )
        * 0.6
    )

    pressure_wave = (
        math.sin(
            cycle / 5
        )
        * 0.002
    )

    if device_id == "demo-printer-002":
        status = "ready"

        print_count = (
            printer[
                "start_print_count"
            ]
            + cycle * 3
        )

        temperature = (
            printer[
                "base_temperature"
            ]
            + temperature_wave
        )

        pressure = (
            printer[
                "base_pressure"
            ]
            + pressure_wave
        )

    else:
        # Printer 03 intentionally represents
        # a machine that needs attention.
        #
        # It periodically changes between
        # WARNING and READY so the demo has
        # realistic operational behaviour.
        warning_cycle = (
            cycle % 12
        ) < 8

        status = (
            "warning"
            if warning_cycle
            else "ready"
        )

        print_count = (
            printer[
                "start_print_count"
            ]
            + cycle
        )

        temperature = (
            printer[
                "base_temperature"
            ]
            + temperature_wave
        )

        pressure = (
            printer[
                "base_pressure"
            ]
            + pressure_wave
        )

    return {
        "device_id": device_id,
        "source": "demo_fleet",
        "online": True,
        "status": status,

        "timestamp":
            utc_timestamp(),

        "print_count":
            print_count,

        "temperature_c":
            round(
                temperature,
                1,
            ),

        "pressure_mpa":
            round(
                pressure,
                3,
            ),

        # Percent values are useful for
        # the existing alert engine.
        "ink_level_percent":
            printer[
                "ink_level_percent"
            ],

        "makeup_level_percent":
            printer[
                "makeup_level_percent"
            ],

        "model_name":
            printer[
                "model_name"
            ],

        "serial_number":
            printer[
                "serial_number"
            ],

        "ink_name":
            printer[
                "ink_name"
            ],

        "ink_operating_time_hours":
            printer[
                "ink_operating_time_hours"
            ],

        "cumulative_operation_time_hours":
            printer[
                "cumulative_operation_time_hours"
            ],

        "ink_remaining_raw":
            printer[
                "ink_remaining_raw"
            ],

        "ink_remaining_label":
            printer[
                "ink_remaining_label"
            ],

        "makeup_remaining_raw":
            printer[
                "makeup_remaining_raw"
            ],

        "makeup_remaining_label":
            printer[
                "makeup_remaining_label"
            ],
    }


async def wait_for_ack(
    websocket,
) -> None:
    raw = await asyncio.wait_for(
        websocket.recv(),
        timeout=ACK_TIMEOUT_SECONDS,
    )

    ack = json.loads(raw)

    if (
        ack.get("status")
        != "stored"
    ):
        raise RuntimeError(
            "Backend did not confirm "
            "measurement storage"
        )


async def run_demo_printer(
    printer: dict,
) -> None:
    device_id = printer[
        "device_id"
    ]

    websocket_url = (
        f"{BACKEND_BASE}/"
        f"ws/collector/"
        f"{device_id}"
    )

    cycle = 0

    while True:
        try:
            print(
                f"[{device_id}] "
                f"Connecting to "
                f"{websocket_url}"
            )

            async with websockets.connect(
                websocket_url
            ) as websocket:

                print(
                    f"[{device_id}] "
                    "Connected"
                )

                while True:
                    cycle += 1

                    measurement = (
                        build_measurement(
                            printer,
                            cycle,
                        )
                    )

                    await websocket.send(
                        json.dumps(
                            measurement
                        )
                    )

                    await wait_for_ack(
                        websocket
                    )

                    print(
                        f"[{device_id}] "
                        f"status="
                        f"{measurement['status']} | "
                        f"prints="
                        f"{measurement['print_count']} | "
                        f"temp="
                        f"{measurement['temperature_c']} C | "
                        f"pressure="
                        f"{measurement['pressure_mpa']} MPa"
                    )

                    await asyncio.sleep(
                        INTERVAL_SECONDS
                    )

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            print(
                f"[{device_id}] "
                f"Connection error: "
                f"{exc}"
            )

            print(
                f"[{device_id}] "
                "Retrying in 5 seconds..."
            )

            await asyncio.sleep(5)


async def main() -> None:
    print()
    print(
        "Care-Inspector Demo Fleet"
    )
    print(
        "-------------------------"
    )
    print(
        f"Backend: {BACKEND_BASE}"
    )
    print(
        f"Interval: "
        f"{INTERVAL_SECONDS}s"
    )
    print()

    tasks = [
        asyncio.create_task(
            run_demo_printer(
                printer
            )
        )
        for printer
        in DEMO_PRINTERS
    ]

    await asyncio.gather(
        *tasks
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
