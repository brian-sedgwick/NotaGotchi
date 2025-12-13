#!/usr/bin/env python3
"""
BLE Server (Peripheral) Test for NotaGotchi - Using bluez-peripheral

Tests BLE peripheral (server) role - advertising and accepting connections.
This device will:
1. Advertise as a NotaGotchi device
2. Accept incoming connections
3. Receive messages from clients

Usage:
    python3 test_ble_server.py [device_name]

Example:
    python3 test_ble_server.py notagotchi_testA

Note: Requires bluez-peripheral library
      pip3 install bluez-peripheral
"""

import asyncio
import sys
import json
import time
from typing import Dict, Any, List
import test_ble_config as config

try:
    from bluez_peripheral.gatt.service import Service
    from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags
    from bluez_peripheral.advert import Advertisement
    from bluez_peripheral.agent import NoIoAgent
except ImportError:
    print("ERROR: bluez-peripheral library not installed")
    print("Install with: pip3 install bluez-peripheral")
    sys.exit(1)


class NotaGotchiService(Service):
    """GATT Service for NotaGotchi device"""

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.device_id = device_name.replace(f"{config.DEVICE_NAME_PREFIX}_", "")
        self.received_messages: List[Dict[str, Any]] = []

        # Device info data
        self.device_info = {
            "device_id": self.device_id,
            "device_name": device_name,
            "pet_name": "TestPet",
            "age_days": 1,
            "evolution_stage": 0,
            "online": True,
            "timestamp": time.time()
        }

        # Initialize service with NotaGotchi UUID
        super().__init__(config.NOTAGOTCHI_SERVICE_UUID, True)

    @characteristic(
        config.DEVICE_INFO_CHAR_UUID,
        CharacteristicFlags.READ | CharacteristicFlags.NOTIFY
    )
    def device_info_char(self, options: Dict[str, Any]) -> bytes:
        """
        Device Info characteristic - returns device information as JSON

        Returns:
            JSON device info as bytes
        """
        # Update timestamp
        self.device_info["timestamp"] = time.time()

        info_json = json.dumps(self.device_info)
        print(f"📖 Client read device info")
        return info_json.encode(config.MESSAGE_ENCODING)

    @characteristic(
        config.MESSAGE_INBOX_CHAR_UUID,
        CharacteristicFlags.WRITE | CharacteristicFlags.WRITE_WITHOUT_RESPONSE
    )
    def message_inbox_char(self, options: Dict[str, Any]) -> bytes:
        """
        Message Inbox characteristic - receives messages from clients

        Note: For write characteristics, the write_callback is set below
        """
        return b""

    def message_inbox_write_callback(self, value: bytes):
        """
        Callback when client writes a message

        Args:
            value: The bytes written by client
        """
        try:
            message_str = value.decode(config.MESSAGE_ENCODING)
            message_data = json.loads(message_str)

            print(f"\n📨 Received message:")
            print(f"  From: {message_data.get('from_device_id', 'Unknown')}")
            print(f"  Pet: {message_data.get('from_pet_name', 'Unknown')}")
            print(f"  Content: {message_data.get('content', '')}")
            print(f"  Type: {message_data.get('content_type', 'text')}")
            print(f"  Timestamp: {time.strftime('%H:%M:%S', time.localtime(message_data.get('timestamp', 0)))}")

            # Store message
            self.received_messages.append({
                "message": message_data,
                "received_at": time.time()
            })

            print(f"  Total messages received: {len(self.received_messages)}\n")

        except json.JSONDecodeError as e:
            print(f"❌ Error decoding message JSON: {e}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")


class NotaGotchiServer:
    """BLE Server manager for NotaGotchi"""

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.service: NotaGotchiService = None
        self.advertisement: Advertisement = None
        self.is_running = False

    async def start(self):
        """Start the BLE server with advertising"""
        print(f"\n{'='*60}")
        print(f"Starting NotaGotchi BLE Server")
        print(f"{'='*60}")
        print(f"Device Name: {self.device_name}")
        print(f"Service UUID: {config.NOTAGOTCHI_SERVICE_UUID}")
        print(f"{'='*60}\n")

        try:
            # Register agent for handling pairing (no input/output)
            agent = NoIoAgent()

            # Create GATT service
            print("✅ Creating GATT service...")
            self.service = NotaGotchiService(self.device_name)

            # Register the service with BlueZ
            print("✅ Registering service with BlueZ...")
            await self.service.register()
            print(f"   - Device Info characteristic: {config.DEVICE_INFO_CHAR_UUID}")
            print(f"   - Message Inbox characteristic: {config.MESSAGE_INBOX_CHAR_UUID}")

            # Create advertisement
            print("\n✅ Creating BLE advertisement...")
            self.advertisement = Advertisement(
                self.device_name,
                [config.NOTAGOTCHI_SERVICE_UUID],
                0x0340,  # Appearance: Generic Computer
                60       # Timeout (seconds, 0 = no timeout)
            )

            # Start advertising
            print(f"✅ Starting advertisement as '{self.device_name}'...")
            await self.advertisement.register()

            print(f"\n{'='*60}")
            print(f"✅ SERVER READY!")
            print(f"{'='*60}")
            print(f"💡 Other devices can now discover '{self.device_name}'")
            print(f"💡 Run test_ble_discovery.py on another device to find this server")
            print(f"💡 Run test_ble_client.py on another device to send messages")
            print(f"\nPress Ctrl+C to stop")
            print(f"{'='*60}\n")

            self.is_running = True

            # Keep server running
            while self.is_running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n\nServer interrupted by user")
        except Exception as e:
            print(f"\n❌ Server error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.stop()

    async def stop(self):
        """Stop the server and cleanup"""
        print("\n\nStopping server...")
        self.is_running = False

        try:
            if self.advertisement:
                print("  - Unregistering advertisement...")
                await self.advertisement.unregister()

            if self.service:
                print("  - Unregistering service...")
                await self.service.unregister()

            print("✅ Server stopped cleanly")

            if self.service and self.service.received_messages:
                print(f"\nServer Statistics:")
                print(f"  Device Name: {self.device_name}")
                print(f"  Messages Received: {len(self.service.received_messages)}")

        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")


async def run_server(device_name: str):
    """
    Run BLE server

    Args:
        device_name: Name to advertise as
    """
    server = NotaGotchiServer(device_name)
    await server.start()


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("NotaGotchi BLE Server Test (bluez-peripheral)")
    print("="*60 + "\n")

    # Get device name from command line or use default
    if len(sys.argv) > 1:
        device_name = sys.argv[1]
    else:
        device_name = f"{config.DEVICE_NAME_PREFIX}_testA"

    # Ensure device name has prefix
    if not device_name.startswith(config.DEVICE_NAME_PREFIX):
        device_name = f"{config.DEVICE_NAME_PREFIX}_{device_name}"
        print(f"📝 Using device name: {device_name}")

    # Check if running on Linux
    import platform
    if platform.system() != "Linux":
        print("⚠️  WARNING: bluez-peripheral only works on Linux (Raspberry Pi)")
        print("   This script will fail on macOS/Windows")
        print("   Run this on your Raspberry Pi device\n")
        sys.exit(1)

    # Run server
    try:
        asyncio.run(run_server(device_name))
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
