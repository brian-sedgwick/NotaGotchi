#!/usr/bin/env python3
"""
BLE Discovery Test for NotaGotchi

Tests BLE device discovery and scanning functionality.
Run this on both Raspberry Pi devices to verify they can discover each other.

Usage:
    python3 test_ble_discovery.py
    python3 test_ble_discovery.py --continuous  # Keep scanning
"""

import asyncio
import sys
import time
from typing import List, Dict
import test_ble_config as config

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
except ImportError:
    print("ERROR: bleak library not installed")
    print("Install with: pip3 install bleak")
    sys.exit(1)


class DeviceDiscovery:
    """Handles BLE device discovery and filtering"""

    def __init__(self):
        self.discovered_devices: Dict[str, BLEDevice] = {}
        self.notagotchi_devices: List[BLEDevice] = []

    async def scan(self, duration: float = None) -> List[BLEDevice]:
        """
        Scan for BLE devices

        Args:
            duration: Scan duration in seconds (default from config)

        Returns:
            List of discovered NotaGotchi devices
        """
        if duration is None:
            duration = config.SCAN_DURATION_SECONDS

        print(f"\n{'='*60}")
        print(f"Starting BLE scan for {duration} seconds...")
        print(f"Looking for devices with name: {config.DEVICE_NAME_PREFIX}*")
        print(f"{'='*60}\n")

        # Discover all BLE devices
        devices = await BleakScanner.discover(timeout=duration)

        print(f"Found {len(devices)} total BLE devices")

        # Filter for NotaGotchi devices
        self.notagotchi_devices = []
        for device in devices:
            if device.name and config.DEVICE_NAME_PREFIX in device.name:
                self.notagotchi_devices.append(device)
                self.discovered_devices[device.address] = device

        return self.notagotchi_devices

    def display_results(self):
        """Display discovered NotaGotchi devices"""
        if not self.notagotchi_devices:
            print("\n❌ No NotaGotchi devices found")
            print("\nTroubleshooting:")
            print("  1. Ensure other device is powered on")
            print("  2. Verify Bluetooth is enabled: sudo systemctl status bluetooth")
            print("  3. Check device is advertising: sudo hciconfig hci0 up")
            print("  4. Make sure other device is running test_ble_server.py")
            return

        print(f"\n✅ Found {len(self.notagotchi_devices)} NotaGotchi device(s):\n")

        for i, device in enumerate(self.notagotchi_devices, 1):
            print(f"Device {i}:")
            print(f"  Name:    {device.name}")
            print(f"  Address: {device.address}")
            print(f"  RSSI:    {device.rssi} dBm")

            # Estimate distance from RSSI
            distance = self._estimate_distance(device.rssi)
            print(f"  Distance: ~{distance}m (estimated)")
            print()

    def _estimate_distance(self, rssi: int) -> str:
        """
        Estimate distance from RSSI signal strength

        Args:
            rssi: Signal strength in dBm

        Returns:
            Distance estimate as string
        """
        if rssi >= -50:
            return "0-2"
        elif rssi >= -60:
            return "2-5"
        elif rssi >= -70:
            return "5-10"
        elif rssi >= -80:
            return "10-20"
        else:
            return "20+"


async def single_scan():
    """Run a single discovery scan"""
    discovery = DeviceDiscovery()
    await discovery.scan()
    discovery.display_results()


async def continuous_scan(interval: int = 10):
    """
    Continuously scan for devices

    Args:
        interval: Seconds between scans
    """
    print("Starting continuous scanning (Press Ctrl+C to stop)\n")

    try:
        scan_count = 0
        while True:
            scan_count += 1
            print(f"\n--- Scan #{scan_count} ---")

            discovery = DeviceDiscovery()
            await discovery.scan()
            discovery.display_results()

            print(f"\nWaiting {interval} seconds before next scan...")
            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nStopping continuous scan...")


def check_bluetooth():
    """Check if Bluetooth is available on this system"""
    import platform

    system = platform.system()

    print("Checking Bluetooth availability...")
    print(f"Platform: {system}")

    if system == "Linux":
        # Check if bluetoothctl is available
        import subprocess
        try:
            result = subprocess.run(
                ["bluetoothctl", "show"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                print("✅ Bluetooth is available")
                return True
            else:
                print("❌ Bluetooth not available or not enabled")
                print("Enable with: sudo systemctl enable bluetooth && sudo systemctl start bluetooth")
                return False
        except FileNotFoundError:
            print("❌ bluetoothctl not found - Bluetooth may not be installed")
            return False
        except subprocess.TimeoutExpired:
            print("⚠️  bluetoothctl timeout - Bluetooth may be unresponsive")
            return False

    elif system == "Darwin":  # macOS
        print("⚠️  Running on macOS - BLE may work but with limitations")
        print("For best results, run this on Raspberry Pi")
        return True

    elif system == "Windows":
        print("⚠️  Running on Windows - BLE support varies")
        print("For best results, run this on Raspberry Pi")
        return True

    return True


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("NotaGotchi BLE Discovery Test")
    print("="*60 + "\n")

    # Check for continuous mode
    continuous = "--continuous" in sys.argv or "-c" in sys.argv

    # Check Bluetooth availability
    if not check_bluetooth():
        print("\nCannot proceed without Bluetooth")
        sys.exit(1)

    print()

    # Run scan
    try:
        if continuous:
            asyncio.run(continuous_scan())
        else:
            asyncio.run(single_scan())

    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")

    except Exception as e:
        print(f"\n❌ Error during scan: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nDiscovery test complete!")


if __name__ == "__main__":
    main()
