#!/usr/bin/env python3
"""
Simplified BLE Test - Proves BLE Works Between Two Pis

This test verifies:
1. Discovery works between devices
2. Connections can be established
3. Basic BLE communication is functional

Usage:
    # On Device A (Server):
    sudo bluetoothctl
    > power on
    > discoverable on
    > advertise on
    (leave running)

    # On Device B (Client):
    python3 test_ble_simple.py
"""

import asyncio
import sys
from bleak import BleakScanner, BleakClient

async def test_discovery():
    """Test BLE device discovery"""
    print("\n" + "="*60)
    print("BLE Discovery Test")
    print("="*60 + "\n")

    print("Scanning for 5 seconds...")
    devices = await BleakScanner.discover(timeout=5.0)

    print(f"\nFound {len(devices)} BLE devices:\n")

    for i, device in enumerate(devices, 1):
        name = device.name or "(unknown)"
        print(f"{i}. {name}")
        print(f"   Address: {device.address}")
        print(f"   RSSI: {device.rssi} dBm")
        print()

    return devices


async def test_connection(device):
    """Test connecting to a specific device"""
    print(f"\n" + "="*60)
    print(f"Connection Test")
    print("="*60 + "\n")

    print(f"Attempting to connect to {device.name} ({device.address})...")

    try:
        async with BleakClient(device, timeout=10.0) as client:
            connected = await client.is_connected()

            if connected:
                print("✅ Successfully connected!")
                print("\nDiscovering services...")

                services = client.services
                print(f"Found {len(services)} services:")

                for service in services:
                    print(f"\n  Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"    - Characteristic: {char.uuid}")
                        print(f"      Properties: {char.properties}")

                return True
            else:
                print("❌ Failed to connect")
                return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def interactive_test():
    """Interactive test - discover and connect"""
    # Discovery
    devices = await test_discovery()

    if not devices:
        print("No devices found. Make sure other device is advertising.")
        print("\nOn the other Raspberry Pi, run:")
        print("  sudo bluetoothctl")
        print("  > power on")
        print("  > discoverable on")
        print("  > advertise on")
        return

    # Choose device
    print("="*60)
    choice = input("Enter device number to test connection (or 0 to skip): ").strip()

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            device = devices[idx]
            await test_connection(device)
        elif choice == "0":
            print("Skipping connection test")
        else:
            print("Invalid choice")
    except ValueError:
        print("Invalid input")


def main():
    print("\n" + "="*60)
    print("NotaGotchi - Simplified BLE Test")
    print("="*60)
    print("\nThis test verifies basic BLE functionality")
    print("between two Raspberry Pi devices.\n")

    try:
        asyncio.run(interactive_test())
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
