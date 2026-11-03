"""Passive dedicated Ethernet discovery tests. No real Linux or printer I/O."""
import unittest
from unittest.mock import patch
from collector.pi_direct_link import passive_direct_link_target


class PiDirectLinkTests(unittest.TestCase):
    def network(self, peers, routes=None):
        def read(*args):
            if args == ("route", "show", "default", "dev", "eth0"):
                return routes or []
            if args == ("neigh", "show", "dev", "eth0"):
                return peers
            self.fail("Unexpected network command")
        return read

    def test_one_learned_local_peer(self):
        result = passive_direct_link_target(network_info=self.network([
            {"dev": "eth0", "dst": "169.254.10.25", "state": ["STALE"]},
        ]))
        self.assertEqual(result.host, "169.254.10.25")
        self.assertEqual(result.port, 502)
        self.assertEqual(result.protocol, "modbus")
        self.assertEqual(result.manufacturer, "Hitachi")

    def test_no_peer_returns_none_without_scanning(self):
        self.assertIsNone(passive_direct_link_target(network_info=self.network([])))

    def test_two_peers_fail_closed(self):
        with self.assertRaises(ValueError):
            passive_direct_link_target(network_info=self.network([
                {"dev": "eth0", "dst": "192.168.1.2", "state": "REACHABLE"},
                {"dev": "eth0", "dst": "192.168.1.3", "state": "STALE"},
            ]))

    def test_default_route_interface_rejected(self):
        with self.assertRaises(ValueError):
            passive_direct_link_target(network_info=self.network(
                [{"dev": "eth0", "dst": "192.168.1.2", "state": "REACHABLE"}],
                routes=[{"dst": "default", "dev": "eth0", "gateway": "192.168.1.1"}],
            ))

    def test_failed_and_public_peers_ignored(self):
        result = passive_direct_link_target(network_info=self.network([
            {"dev": "eth0", "dst": "192.168.1.2", "state": "FAILED"},
            {"dev": "eth0", "dst": "8.8.8.8", "state": "REACHABLE"},
            {"dev": "wlan0", "dst": "192.168.1.8", "state": "REACHABLE"},
        ]))
        self.assertIsNone(result)

    def test_invalid_interface_rejected_before_network_call(self):
        with self.assertRaises(ValueError):
            passive_direct_link_target(interface="-evil",
                network_info=lambda *args: self.fail("No network queries expected"))

    def test_invalid_port_rejected(self):
        with self.assertRaises(ValueError):
            passive_direct_link_target(port=True,
                network_info=lambda *args: self.fail("No network queries expected"))

    def test_probe_is_still_required_for_announcement(self):
        from collector.pi_printer_discovery import discover_configured_hitachi
        target = passive_direct_link_target(network_info=self.network([
            {"dev": "eth0", "dst": "192.168.50.20", "state": "REACHABLE"},
        ]))
        result = discover_configured_hitachi(
            "https://example.invalid", [target],
            probe=lambda target: None,
            announce=lambda *args: self.fail("An unidentified peer must never be announced"),
        )
        self.assertTrue(result["announcement_skipped"])


if __name__ == "__main__":
    unittest.main()
