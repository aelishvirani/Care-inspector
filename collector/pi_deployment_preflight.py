"""Read-only installed-Pi deployment preflight (no key reads, network, or writes).

For offline tests, pass a temporary filesystem root to check_installation.
This is a *preflight*, not proof of BlueZ/Modbus/cellular functionality.
"""
from __future__ import annotations

import argparse
import os
import pwd
import stat
from pathlib import Path


def check_installation(root: Path = Path("/"), *, service_uid: int | None = None) -> list[str]:
    """Return concise failures without reading or logging secret file contents."""
    root = Path(root)
    failures: list[str] = []
    if service_uid is None:
        try:
            service_uid = pwd.getpwnam("careinspector").pw_uid
        except KeyError:
            failures.append("Service account careinspector is missing")
            return failures

    def mounted(relative: str) -> Path:
        return root / relative.lstrip("/")

    python = mounted("/opt/care-inspector/.venv/bin/python")
    try:
        mode = python.stat().st_mode
        if not stat.S_ISREG(mode) or not (mode & 0o111):
            failures.append("Pi virtualenv Python is not executable")
    except OSError:
        failures.append("Pi virtualenv Python is missing")

    state_dir = mounted("/var/lib/care-inspector")
    try:
        info = state_dir.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != service_uid
                or info.st_mode & 0o077):
            failures.append("Pi key directory requires service ownership and mode 0700")
    except OSError:
        failures.append("Pi key directory is missing")

    for relative, label, expected_mode in (
        ("/var/lib/care-inspector/pi-ed25519.key", "Pi signing key", 0o600),
        ("/etc/care-inspector/pi-cloud.env", "Pi cloud environment", None),
    ):
        try:
            info = mounted(relative).lstat()
            if not stat.S_ISREG(info.st_mode):
                failures.append(f"{label} must be a regular file, not a symlink")
            elif info.st_mode & 0o007 or (expected_mode is not None
                                            and stat.S_IMODE(info.st_mode) != expected_mode):
                failures.append(f"{label} has unsafe permissions")
            elif label == "Pi signing key" and info.st_uid != service_uid:
                failures.append("Pi signing key must belong to the service account")
        except OSError:
            failures.append(f"{label} is missing")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Raspberry Pi filesystem preflight")
    parser.add_argument(
        "--installed", action="store_true",
        help="Check the installed Pi filesystem (not suitable for local Mac testing)",
    )
    args = parser.parse_args()
    if not args.installed:
        parser.error("Explicit --installed is required; nothing was checked")
    failures = check_installation()
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        print("Pi filesystem preflight FAILED (no changes made)")
        return 1
    print("Pi filesystem preflight PASSED; hardware/network checks still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
