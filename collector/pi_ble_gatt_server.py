"""Linux BlueZ BLE identity service for a Raspberry Pi.

Requires Raspberry Pi OS, BlueZ, python3-dbus and python3-gi. This file is
intentionally not imported by the normal Mac collector or the cloud backend.
It provides read-only identification, NOT trusted authentication or pairing.
"""
from __future__ import annotations

import sys
import json

try:
    from collector.pi_identity import (
        collect_pi_identity, SERVICE_UUID, IDENTITY_UUID,
    )
except ModuleNotFoundError:
    from pi_identity import collect_pi_identity, SERVICE_UUID, IDENTITY_UUID

try:
    from collector.pi_pairing_agent import (
        PairingSigner, load_or_create_private_key, public_key_b64,
        PUBLIC_KEY_UUID, CHALLENGE_UUID, PROOF_UUID,
    )
except ModuleNotFoundError:
    from pi_pairing_agent import (
        PairingSigner, load_or_create_private_key, public_key_b64,
        PUBLIC_KEY_UUID, CHALLENGE_UUID, PROOF_UUID,
    )

ROOT = "/com/mfg/careinspector"
BLUEZ = "org.bluez"
OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
PROPERTIES = "org.freedesktop.DBus.Properties"
GATT_MANAGER = "org.bluez.GattManager1"
GATT_SERVICE = "org.bluez.GattService1"
GATT_CHAR = "org.bluez.GattCharacteristic1"
ADV_MANAGER = "org.bluez.LEAdvertisingManager1"
ADV_INTERFACE = "org.bluez.LEAdvertisement1"


def run() -> None:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("BlueZ BLE GATT server runs only on Linux Raspberry Pi OS")

    try:
        import dbus
        import dbus.service
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib
    except ImportError as exc:
        raise RuntimeError(
            "Install Raspberry Pi OS packages python3-dbus, python3-gi, bluez"
        ) from exc

    # Fail closed before registering anything if the hardware is unsupported.
    payload = collect_pi_identity()
    hardware_id = json.loads(payload)["hardware_id"]
    key = load_or_create_private_key()
    signer = PairingSigner(key, hardware_id)
    key_payload = public_key_b64(key).encode("ascii")

    class Application(dbus.service.Object):
        def __init__(self, bus):
            self.path = ROOT
            super().__init__(bus, self.path)
            self.service = IdentityService(bus)
            self.characteristic = IdentityCharacteristic(bus, self.service)
            self.public_key = PublicKeyCharacteristic(bus, self.service)
            self.challenge = ChallengeCharacteristic(bus, self.service)
            self.proof = ProofCharacteristic(bus, self.service)

        @dbus.service.method(OBJECT_MANAGER, out_signature="a{oa{sa{sv}}}")
        def GetManagedObjects(self):
            return {
                self.service.path: {
                    GATT_SERVICE: self.service.properties(),
                },
                self.characteristic.path: {
                    GATT_CHAR: self.characteristic.properties(),
                },
                self.public_key.path: {GATT_CHAR: self.public_key.properties()},
                self.challenge.path: {GATT_CHAR: self.challenge.properties()},
                self.proof.path: {GATT_CHAR: self.proof.properties()},
            }

    class IdentityService(dbus.service.Object):
        def __init__(self, bus):
            self.path = ROOT + "/service0"
            super().__init__(bus, self.path)

        def properties(self):
            return {
                "UUID": dbus.String(SERVICE_UUID),
                "Primary": dbus.Boolean(True),
                "Includes": dbus.Array([], signature="o"),
            }

        @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            if interface != GATT_SERVICE:
                raise dbus.exceptions.DBusException(
                    "Unknown interface", name="org.freedesktop.DBus.Error.InvalidArgs"
                )
            return self.properties()

    class IdentityCharacteristic(dbus.service.Object):
        def __init__(self, bus, service):
            self.path = service.path + "/char0"
            self.service = service
            super().__init__(bus, self.path)

        def properties(self):
            return {
                "UUID": dbus.String(IDENTITY_UUID),
                "Service": dbus.ObjectPath(self.service.path),
                "Flags": dbus.Array(["read"], signature="s"),
            }

        @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            if interface != GATT_CHAR:
                raise dbus.exceptions.DBusException(
                    "Unknown interface", name="org.freedesktop.DBus.Error.InvalidArgs"
                )
            return self.properties()

        @dbus.service.method(GATT_CHAR, in_signature="a{sv}", out_signature="ay")
        def ReadValue(self, options):
            # ATT long reads use the offset option to obtain bytes beyond MTU.
            offset = int(options.get("offset", 0))
            if offset < 0 or offset > len(payload):
                raise dbus.exceptions.DBusException(
                    "Invalid offset", name="org.bluez.Error.InvalidOffset"
                )
            return dbus.Array([dbus.Byte(byte) for byte in payload[offset:]],
                              signature="y")

    class PublicKeyCharacteristic(dbus.service.Object):
        def __init__(self, bus, service):
            self.path = service.path + "/char1"
            self.service = service
            super().__init__(bus, self.path)

        def properties(self):
            return {
                "UUID": dbus.String(PUBLIC_KEY_UUID),
                "Service": dbus.ObjectPath(self.service.path),
                "Flags": dbus.Array(["read"], signature="s"),
            }

        @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            if interface != GATT_CHAR:
                raise dbus.exceptions.DBusException(
                    "Unknown interface", name="org.freedesktop.DBus.Error.InvalidArgs"
                )
            return self.properties()

        @dbus.service.method(GATT_CHAR, in_signature="a{sv}", out_signature="ay")
        def ReadValue(self, options):
            offset = int(options.get("offset", 0))
            if offset < 0 or offset > len(key_payload):
                raise dbus.exceptions.DBusException(
                    "Invalid offset", name="org.bluez.Error.InvalidOffset"
                )
            return dbus.Array([dbus.Byte(x) for x in key_payload[offset:]], signature="y")

    class ChallengeCharacteristic(dbus.service.Object):
        def __init__(self, bus, service):
            self.path = service.path + "/char2"
            self.service = service
            super().__init__(bus, self.path)

        def properties(self):
            return {
                "UUID": dbus.String(CHALLENGE_UUID),
                "Service": dbus.ObjectPath(self.service.path),
                "Flags": dbus.Array(["write"], signature="s"),
            }

        @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            if interface != GATT_CHAR:
                raise dbus.exceptions.DBusException(
                    "Unknown interface", name="org.freedesktop.DBus.Error.InvalidArgs"
                )
            return self.properties()

        @dbus.service.method(GATT_CHAR, in_signature="aya{sv}", out_signature="")
        def WriteValue(self, value, options):
            if int(options.get("offset", 0)) != 0:
                raise dbus.exceptions.DBusException(
                    "Invalid offset", name="org.bluez.Error.InvalidOffset"
                )
            try:
                signer.accept_challenge(bytes(value))
            except ValueError as exc:
                raise dbus.exceptions.DBusException(
                    "Invalid challenge", name="org.bluez.Error.InvalidValueLength"
                ) from exc

    class ProofCharacteristic(dbus.service.Object):
        def __init__(self, bus, service):
            self.path = service.path + "/char3"
            self.service = service
            super().__init__(bus, self.path)

        def properties(self):
            return {
                "UUID": dbus.String(PROOF_UUID),
                "Service": dbus.ObjectPath(self.service.path),
                "Flags": dbus.Array(["read"], signature="s"),
            }

        @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            if interface != GATT_CHAR:
                raise dbus.exceptions.DBusException(
                    "Unknown interface", name="org.freedesktop.DBus.Error.InvalidArgs"
                )
            return self.properties()

        @dbus.service.method(GATT_CHAR, in_signature="a{sv}", out_signature="ay")
        def ReadValue(self, options):
            try:
                value = signer.read_proof(int(options.get("offset", 0)))
            except ValueError as exc:
                raise dbus.exceptions.DBusException(
                    "Pairing proof not available", name="org.bluez.Error.NotPermitted"
                ) from exc
            return dbus.Array([dbus.Byte(x) for x in value], signature="y")

    class Advertisement(dbus.service.Object):
        def __init__(self, bus):
            self.path = ROOT + "/advertisement0"
            super().__init__(bus, self.path)

        def properties(self):
            return {
                "Type": dbus.String("peripheral"),
                "ServiceUUIDs": dbus.Array([SERVICE_UUID], signature="s"),
                # Name is optional; no rename/prefix is required.
            }

        @dbus.service.method(PROPERTIES, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            if interface != ADV_INTERFACE:
                raise dbus.exceptions.DBusException(
                    "Unknown interface", name="org.freedesktop.DBus.Error.InvalidArgs"
                )
            return self.properties()

        @dbus.service.method(ADV_INTERFACE, in_signature="", out_signature="")
        def Release(self):
            print("BLE advertisement released")

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object(BLUEZ, "/"), OBJECT_MANAGER)
    adapters = manager.GetManagedObjects()
    adapter_path = next((
        path for path, props in adapters.items()
        if GATT_MANAGER in props and ADV_MANAGER in props
    ), None)
    if adapter_path is None:
        raise RuntimeError("No BlueZ adapter with GATT and LE advertising support")

    props = dbus.Interface(bus.get_object(BLUEZ, adapter_path), PROPERTIES)
    if not bool(props.Get("org.bluez.Adapter1", "Powered")):
        raise RuntimeError("Bluetooth adapter is off; enable it before starting the agent")

    app = Application(bus)
    advertisement = Advertisement(bus)
    gatt_manager = dbus.Interface(bus.get_object(BLUEZ, adapter_path), GATT_MANAGER)
    adv_manager = dbus.Interface(bus.get_object(BLUEZ, adapter_path), ADV_MANAGER)
    loop = GLib.MainLoop()
    registered = {"gatt": False, "adv": False}

    def failed(error):
        print("BlueZ registration failed:", error, file=sys.stderr)
        loop.quit()

    def gatt_ok():
        registered["gatt"] = True
        print("Read-only Care-Inspector BLE identity GATT registered")

    def adv_ok():
        registered["adv"] = True
        print("Care-Inspector BLE advertisement registered; waiting for browser reads")

    try:
        gatt_manager.RegisterApplication(
            dbus.ObjectPath(app.path), {},
            reply_handler=gatt_ok, error_handler=failed,
        )
        adv_manager.RegisterAdvertisement(
            dbus.ObjectPath(advertisement.path), {},
            reply_handler=adv_ok, error_handler=failed,
        )
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        if registered["adv"]:
            try:
                adv_manager.UnregisterAdvertisement(dbus.ObjectPath(advertisement.path))
            except dbus.DBusException:
                pass
        if registered["gatt"]:
            try:
                gatt_manager.UnregisterApplication(dbus.ObjectPath(app.path))
            except dbus.DBusException:
                pass


if __name__ == "__main__":
    run()
