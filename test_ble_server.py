#!/usr/bin/env python3
"""
BLE Server (Peripheral) Test for NotaGotchi

Tests BLE peripheral (server) role - advertising and accepting connections.
This device will:
1. Advertise as a NotaGotchi device
2. Accept incoming connections
3. Receive messages from clients

Usage:
    python3 test_ble_server.py [device_name]

Example:
    python3 test_ble_server.py NotaGotchi_TestA
"""

import asyncio
import sys
import json
import time
from typing import Optional, Dict, Any
import test_ble_config as config

try:
    from bleak import BleakGATTCharacteristic, BleakGATTService Server
    from bleak.backends.characteristic import GATTCharacteristicProperties
except ImportError:
    print("ERROR: bleak library not installed")
    print("Install with: pip3 install bleak")
    sys.exit(1)


class NotaGotchiServer:
    """BLE GATT Server for NotaGotchi device"""

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.server = None
        self.device_info = {
            "device_id": device_name.replace(config.DEVICE_NAME_PREFIX + "_", ""),
            "device_name": device_name,
            "pet_name": "TestPet",
            "age_days": 1,
            "evolution_stage": 0,
            "online": True,
            "timestamp": time.time()
        }
        self.received_messages = []
        self.is_running = False

    def _device_info_read_callback(self, characteristic: BleakGATTCharacteristic) -> bytes:
        """
        Callback when client reads Device Info characteristic

        Returns:
            JSON device info as bytes
        """
        info_json = json.dumps(self.device_info)
        print(f"📖 Client read device info: {info_json[:50]}...")
        return info_json.encode(config.MESSAGE_ENCODING)

    def _message_inbox_write_callback(
        self,
        characteristic: BleakGATTCharacteristic,
        value: bytes
    ):
        """
        Callback when client writes to Message Inbox characteristic

        Args:
            characteristic: The characteristic that was written to
            value: The bytes that were written
        """
        try:
            message_str = value.decode(config.MESSAGE_ENCODING)
            message_data = json.loads(message_str)

            print(f"\n📨 Received message:")
            print(f"  From: {message_data.get('from_device_id', 'Unknown')}")
            print(f"  Content: {message_data.get('content', '')} ")
            print(f"  Type: {message_data.get('content_type', 'text')}")
            print(f"  Timestamp: {message_data.get('timestamp', 0)}")

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

    async def setup_server(self):
        """Set up GATT server with characteristics"""
        print(f"\n{'='*60}")
        print(f"Setting up BLE GATT Server: {self.device_name}")
        print(f"{'='*60}\n")

        # Create GATT service
        service = BleakGATTService(config.NOTAGOTCHI_SERVICE_UUID)

        # Device Info characteristic (Read, Notify)
        device_info_char = BleakGATTCharacteristic(
            uuid=config.DEVICE_INFO_CHAR_UUID,
            properties=GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify,
            value=None,
            read_func=self._device_info_read_callback
        )
        service.add_characteristic(device_info_char)
        print(f"✅ Added Device Info characteristic (Read, Notify)")

        # Message Inbox characteristic (Write, Notify)
        message_inbox_char = BleakGATTCharacteristic(
            uuid=config.MESSAGE_INBOX_CHAR_UUID,
            properties=GATTCharacteristicProperties.write | GATTCharacteristicProperties.notify,
            value=None,
            write_func=self._message_inbox_write_callback
        )
        service.add_characteristic(message_inbox_char)
        print(f"✅ Added Message Inbox characteristic (Write, Notify)")

        # Create server with service
        self.server = Server(
            name=self.device_name,
            services=[service]
        )

        print(f"\n✅ GATT server configured successfully")
        return self.server

    async def start(self):
        """Start advertising and accepting connections"""
        if self.server is None:
            await self.setup_server()

        print(f"\n{'='*60}")
        print(f"Starting BLE Server")
        print(f"{'='*60}")
        print(f"Device Name: {self.device_name}")
        print(f"Service UUID: {config.NOTAGOTCHI_SERVICE_UUID}")
        print(f"Advertising...")
        print(f"\n💡 Other devices can now discover and connect to this device")
        print(f"💡 Run test_ble_discovery.py on another device to find this server")
        print(f"💡 Run test_ble_client.py on another device to send messages")
        print(f"\nPress Ctrl+C to stop\n")
        print(f"{'='*60}\n")

        self.is_running = True

        try:
            async with self.server:
                # Keep server running
                while self.is_running:
                    await asyncio.sleep(1)

                    # Update timestamp in device info
                    self.device_info["timestamp"] = time.time()

        except KeyboardInterrupt:
            print("\n\nServer interrupted by user")
        except Exception as e:
            print(f"\n❌ Server error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False

    def stop(self):
        """Stop the server"""
        print("\n\nStopping server...")
        self.is_running = False

    def get_stats(self):
        """Get server statistics"""
        return {
            "device_name": self.device_name,
            "messages_received": len(self.received_messages),
            "uptime_seconds": time.time() - self.device_info["timestamp"]
        }


async def run_server(device_name: str):
    """
    Run BLE server

    Args:
        device_name: Name to advertise as
    """
    server = NotaGotchiServer(device_name)

    try:
        await server.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        stats = server.get_stats()
        print(f"\nServer Statistics:")
        print(f"  Device Name: {stats['device_name']}")
        print(f"  Messages Received: {stats['messages_received']}")
        print(f"\nServer stopped.")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("NotaGotchi BLE Server Test")
    print("="*60 + "\n")

    # Get device name from command line or use default
    if len(sys.argv) > 1:
        device_name = sys.argv[1]
    else:
        device_name = config.TEST_DEVICE_A_NAME

    # Validate device name
    if not device_name.startswith(config.DEVICE_NAME_PREFIX):
        print(f"⚠️  Device name should start with '{config.DEVICE_NAME_PREFIX}'")
        device_name = f"{config.DEVICE_NAME_PREFIX}_{device_name}"
        print(f"   Using: {device_name}")

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
