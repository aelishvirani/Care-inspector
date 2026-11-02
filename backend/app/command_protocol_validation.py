"""Protocol-aware validation for stored custom printer commands.

This module does not open connections, perform I/O, or execute writes.
Generic hex strings are not sufficient to infer a printer's wire protocol.
"""

import re
from dataclasses import dataclass

HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")


@dataclass(frozen=True)
class CommandValidation:
    valid_hex: bool
    executable: bool
    protocol: str
    reason: str
    byte_count: int = 0


def inspect_custom_command(
    hex_code: str,
    *,
    protocol: str | None = None,
) -> CommandValidation:
    """Validate storage syntax and deliberately deny hardware execution.

    A later manufacturer-specific adapter must validate function code,
    register address, data type, unit ID, and approved command semantics
    before any operation can be enabled.
    """
    normalized = "".join((hex_code or "").split()).upper()
    label = protocol or "unconfigured"

    if (
        not normalized
        or len(normalized) % 2 != 0
        or len(normalized) > 512
        or HEX_RE.fullmatch(normalized) is None
    ):
        return CommandValidation(
            valid_hex=False,
            executable=False,
            protocol=label,
            reason="Invalid hexadecimal byte sequence.",
        )

    if protocol == "modbus_tcp":
        reason = (
            "Modbus TCP requires a verified function code, register "
            "address, data type, unit ID, and model-specific permissions. "
            "A hexadecimal sequence alone is not executable."
        )
    else:
        reason = (
            "No approved protocol adapter is configured for this command. "
            "A hexadecimal sequence alone is not executable."
        )

    return CommandValidation(
        valid_hex=True,
        executable=False,
        protocol=label,
        reason=reason,
        byte_count=len(normalized) // 2,
    )
