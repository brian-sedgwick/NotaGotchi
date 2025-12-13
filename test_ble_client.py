#!/usr/bin/env python3
"""
BLE Client (Central) Test for NotaGotchi

Tests BLE central (client) role - discovering and connecting to servers.
This device will:
1. Scan for NotaGotchi servers
2. Connect to a specific server
3. Read device info
4. Send messages to the server

Usage:
    python3 test_ble_client.py [target_device_name] [message]

Examples:
    python3 test_ble_client.py                          # Discover and choose
    python3 test_ble_client.py NotaGotchi_TestA         # Connect to specific device
    python3 test_ble_client.py NotaGotchi_TestA "Hello!" # Send custom message
"""

import asyncio
import sys
import json
import time
import uuid
from typing import Optional, List
import test_ble_config as config

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
except ImportError:
    print("ERROR: bleak library not installed")
    print("Install with: pip3 install bleak")
    sys.exit(1)


class NotaGotchiClient:
    """BLE GATT Client for connecting to NotaGotchi devices"""

    def __init__(self, source_device_name: str = "NotaGotchi_Client"):
        self.source_device_name = source_device_name
        self.source_device_id = source_device_name.replace(f"{config.DEVICE_NAME_PREFIX}_", "")
        self.connected_device: Optional[BLEDevice] = None
        self.client: Optional[BleakClient] = None

    async def discover_devices(self, duration: float = None) -> List[BLEDevice]:
        """
        Discover NotaGotchi BLE devices

        Args:
            duration: Scan duration in seconds

        Returns:
            List of discovered NotaGotchi devices
        """
        if duration is None:
            duration = config.SCAN_DURATION_SECONDS

        print(f"🔍 Scanning for NotaGotchi devices ({duration}s)...")

        devices = await BleakScanner.discover(timeout=duration)

        # Filter for NotaGotchi devices
        notagotchi_devices = [
            d for d in devices
            if d.name and config.DEVICE_NAME_PREFIX in d.name
        ]

        if notagotchi_devices:
            print(f"✅ Found {len(notagotchi_devices)} NotaGotchi device(s):\n")
            for i, device in enumerate(notagotchi_devices, 1):
                print(f"  {i}. {device.name} ({device.address}) - RSSI: {device.rssi} dBm")
        else:
            print("❌ No NotaGotchi devices found")
            print("\nMake sure a server is running: python3 test_ble_server.py")

        return notagotchi_devices

    async def connect(self, device: BLEDevice, timeout: float = None) -> bool:
        """
        Connect to a BLE device

        Args:
            device: Device to connect to
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully
        """
        if timeout is None:
            timeout = config.CONNECTION_TIMEOUT_SECONDS

        print(f"\n🔗 Connecting to {device.name} ({device.address})...")

        try:
            self.client = BleakClient(device.address, timeout=timeout)
            await self.client.connect()

            if self.client.is_connected:
                self.connected_device = device
                print(f"✅ Connected to {device.name}")
                return True
            else:
                print(f"❌ Failed to connect to {device.name}")
                return False

        except asyncio.TimeoutError:
            print(f"❌ Connection timeout after {timeout}s")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    async def disconnect(self):
        """Disconnect from current device"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print(f"✅ Disconnected from {self.connected_device.name}")
            self.connected_device = None
            self.client = None

    async def read_device_info(self) -> Optional[dict]:
        """
        Read device info from connected device

        Returns:
            Device info dict or None if failed
        """
        if not self.client or not self.client.is_connected:
            print("❌ Not connected to any device")
            return None

        try:
            print(f"\n📖 Reading device info...")

            # Read Device Info characteristic
            data = await self.client.read_gatt_char(config.DEVICE_INFO_CHAR_UUID)
            info_str = data.decode(config.MESSAGE_ENCODING)
            info = json.loads(info_str)

            print(f"✅ Device Info:")
            print(f"  Device ID: {info.get('device_id', 'Unknown')}")
            print(f"  Pet Name: {info.get('pet_name', 'Unknown')}")
            print(f"  Age: {info.get('age_days', 0)} days")
            print(f"  Stage: {info.get('evolution_stage', 0)}")
            print(f"  Online: {info.get('online', False)}")

            return info

        except Exception as e:
            print(f"❌ Error reading device info: {e}")
            return None

    async def send_message(self, content: str, content_type: str = "text") -> bool:
        """
        Send a message to the connected device

        Args:
            content: Message content
            content_type: Type of message (text, emoji, preset)

        Returns:
            True if sent successfully
        """
        if not self.client or not self.client.is_connected:
            print("❌ Not connected to any device")
            return False

        try:
            # Create message
            message = {
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "from_device_id": self.source_device_id,
                "from_pet_name": "TestPet",
                "to_device_id": self.connected_device.name.replace(f"{config.DEVICE_NAME_PREFIX}_", ""),
                "content": content,
                "content_type": content_type,
                "timestamp": time.time()
            }

            message_json = json.dumps(message)
            message_bytes = message_json.encode(config.MESSAGE_ENCODING)

            # Check message size
            if len(message_bytes) > config.MAX_MESSAGE_SIZE:
                print(f"❌ Message too large: {len(message_bytes)} bytes (max {config.MAX_MESSAGE_SIZE})")
                return False

            print(f"\n📤 Sending message...")
            print(f"  To: {self.connected_device.name}")
            print(f"  Content: {content}")
            print(f"  Size: {len(message_bytes)} bytes")

            # Write to Message Inbox characteristic
            await self.client.write_gatt_char(
                config.MESSAGE_INBOX_CHAR_UUID,
                message_bytes
            )

            print(f"✅ Message sent successfully")
            return True

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False


async def interactive_mode(client: NotaGotchiClient):
    """Run interactive client mode"""
    print("\n" + "="*60)
    print("Interactive Mode")
    print("="*60)

    # Discover devices
    devices = await client.discover_devices()
    if not devices:
        return

    # Choose device
    if len(devices) == 1:
        chosen_device = devices[0]
        print(f"\nAuto-selecting only device: {chosen_device.name}")
    else:
        print("\nSelect a device:")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device.name}")

        try:
            choice = int(input("\nEnter device number: "))
            if 1 <= choice <= len(devices):
                chosen_device = devices[choice - 1]
            else:
                print("Invalid choice")
                return
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled")
            return

    # Connect
    connected = await client.connect(chosen_device)
    if not connected:
        return

    try:
        # Read device info
        await client.read_device_info()

        # Send messages
        print("\n" + "="*60)
        print("Message Sending (type 'quit' to exit)")
        print("="*60 + "\n")

        while True:
            try:
                message = input("Enter message: ").strip()
                if message.lower() in ['quit', 'exit', 'q']:
                    break

                if message:
                    await client.send_message(message)
                    await asyncio.sleep(0.5)  # Small delay

            except KeyboardInterrupt:
                break

    finally:
        await client.disconnect()


async def send_single_message(
    client: NotaGotchiClient,
    target_name: str,
    message: str
):
    """Send a single message to a specific device"""
    print(f"\n{'='*60}")
    print(f"Sending Single Message")
    print(f"{'='*60}")
    print(f"Target: {target_name}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")

    # Discover devices
    devices = await client.discover_devices()
    if not devices:
        print("\n❌ No devices found")
        return

    # Find target device
    target_device = None
    for device in devices:
        if device.name == target_name:
            target_device = device
            break

    if not target_device:
        print(f"\n❌ Device '{target_name}' not found")
        print(f"Available devices: {[d.name for d in devices]}")
        return

    # Connect
    connected = await client.connect(target_device)
    if not connected:
        return

    try:
        # Read device info
        await client.read_device_info()

        # Send message
        await client.send_message(message)
        await asyncio.sleep(1)  # Give time for delivery

    finally:
        await client.disconnect()


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("NotaGotchi BLE Client Test")
    print("="*60 + "\n")

    # Parse command line arguments
    target_device = None
    message = None

    if len(sys.argv) > 1:
        target_device = sys.argv[1]
    if len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])

    # Create client
    client = NotaGotchiClient()

    # Run appropriate mode
    try:
        if target_device and message:
            # Send single message
            asyncio.run(send_single_message(client, target_device, message))
        else:
            # Interactive mode
            asyncio.run(interactive_mode(client))

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nClient test complete!")


if __name__ == "__main__":
    main()
