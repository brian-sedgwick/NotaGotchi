#!/usr/bin/env python3
"""
BLE Bidirectional Chat Test for NotaGotchi

Tests full bidirectional BLE communication between two devices.
Each device acts as BOTH server (peripheral) and client (central).

Features:
- Discover nearby devices
- Accept incoming connections
- Send messages to other devices
- Receive messages from other devices
- Simple terminal-based chat interface

Usage:
    python3 test_ble_chat.py [your_device_name]

Examples:
    # On Device A:
    python3 test_ble_chat.py NotaGotchi_Alice

    # On Device B:
    python3 test_ble_chat.py NotaGotchi_Bob
"""

import asyncio
import sys
import json
import time
import uuid
from typing import Optional, Dict, List
import test_ble_config as config

try:
    from bleak import BleakClient, BleakScanner, BleakGATTCharacteristic, BleakGATTService, Server
    from bleak.backends.device import BLEDevice
    from bleak.backends.characteristic import GATTCharacteristicProperties
except ImportError:
    print("ERROR: bleak library not installed")
    print("Install with: pip3 install bleak")
    sys.exit(1)


class BidirectionalChat:
    """
    Handles bidirectional BLE chat combining server and client roles
    """

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.device_id = device_name.replace(f"{config.DEVICE_NAME_PREFIX}_", "")

        # Server (Peripheral) components
        self.server = None
        self.received_messages = []

        # Client (Central) components
        self.discovered_devices: Dict[str, BLEDevice] = {}
        self.connected_client: Optional[BleakClient] = None
        self.current_peer: Optional[str] = None

        # State
        self.is_running = False
        self.server_ready = False

    # ========================================================================
    # SERVER (PERIPHERAL) METHODS
    # ========================================================================

    def _device_info_read_callback(self, characteristic: BleakGATTCharacteristic) -> bytes:
        """Callback when client reads device info"""
        info = {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "pet_name": "ChatPet",
            "timestamp": time.time()
        }
        return json.dumps(info).encode(config.MESSAGE_ENCODING)

    def _message_inbox_write_callback(
        self,
        characteristic: BleakGATTCharacteristic,
        value: bytes
    ):
        """Callback when client writes a message"""
        try:
            message_str = value.decode(config.MESSAGE_ENCODING)
            message = json.loads(message_str)

            # Display received message
            from_name = message.get("from_pet_name", "Unknown")
            content = message.get("content", "")
            timestamp = time.strftime("%H:%M:%S", time.localtime(message.get("timestamp", time.time())))

            print(f"\n[{timestamp}] {from_name}: {content}")
            print(f"You: ", end="", flush=True)  # Re-prompt

            # Store message
            self.received_messages.append({
                "message": message,
                "received_at": time.time()
            })

        except Exception as e:
            print(f"\n❌ Error receiving message: {e}")

    async def setup_server(self):
        """Set up GATT server"""
        # Create service
        service = BleakGATTService(config.NOTAGOTCHI_SERVICE_UUID)

        # Device Info characteristic
        device_info_char = BleakGATTCharacteristic(
            uuid=config.DEVICE_INFO_CHAR_UUID,
            properties=GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify,
            value=None,
            read_func=self._device_info_read_callback
        )
        service.add_characteristic(device_info_char)

        # Message Inbox characteristic
        message_inbox_char = BleakGATTCharacteristic(
            uuid=config.MESSAGE_INBOX_CHAR_UUID,
            properties=GATTCharacteristicProperties.write | GATTCharacteristicProperties.notify,
            value=None,
            write_func=self._message_inbox_write_callback
        )
        service.add_characteristic(message_inbox_char)

        # Create server
        self.server = Server(
            name=self.device_name,
            services=[service]
        )

        self.server_ready = True

    async def run_server(self):
        """Run the server (advertising and accepting connections)"""
        if not self.server_ready:
            await self.setup_server()

        print(f"📡 Advertising as {self.device_name}...")

        try:
            async with self.server:
                while self.is_running:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Server error: {e}")

    # ========================================================================
    # CLIENT (CENTRAL) METHODS
    # ========================================================================

    async def discover_peers(self) -> List[BLEDevice]:
        """Discover other NotaGotchi devices"""
        devices = await BleakScanner.discover(timeout=config.SCAN_DURATION_SECONDS)

        peers = []
        for device in devices:
            if (device.name and
                config.DEVICE_NAME_PREFIX in device.name and
                device.name != self.device_name):  # Exclude self
                peers.append(device)
                self.discovered_devices[device.name] = device

        return peers

    async def connect_to_peer(self, peer_name: str) -> bool:
        """Connect to a peer device"""
        if peer_name not in self.discovered_devices:
            print(f"❌ Device '{peer_name}' not found. Run discovery first.")
            return False

        device = self.discovered_devices[peer_name]

        try:
            if self.connected_client and self.connected_client.is_connected:
                await self.connected_client.disconnect()

            self.connected_client = BleakClient(device.address, timeout=config.CONNECTION_TIMEOUT_SECONDS)
            await self.connected_client.connect()

            if self.connected_client.is_connected:
                self.current_peer = peer_name
                return True

        except Exception as e:
            print(f"❌ Connection error: {e}")

        return False

    async def send_message_to_peer(self, content: str) -> bool:
        """Send message to connected peer"""
        if not self.connected_client or not self.connected_client.is_connected:
            print("❌ Not connected to any peer")
            return False

        try:
            message = {
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "from_device_id": self.device_id,
                "from_pet_name": self.device_name.split("_")[-1],
                "content": content,
                "content_type": "text",
                "timestamp": time.time()
            }

            message_bytes = json.dumps(message).encode(config.MESSAGE_ENCODING)

            await self.connected_client.write_gatt_char(
                config.MESSAGE_INBOX_CHAR_UUID,
                message_bytes
            )

            return True

        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

    # ========================================================================
    # CHAT INTERFACE
    # ========================================================================

    async def chat_loop(self):
        """Main chat interface loop"""
        print("\n" + "="*60)
        print("Chat Interface")
        print("="*60)
        print("Commands:")
        print("  /discover   - Discover nearby devices")
        print("  /connect <name> - Connect to a device")
        print("  /disconnect - Disconnect from current peer")
        print("  /status     - Show connection status")
        print("  /quit       - Exit chat")
        print("="*60 + "\n")

        while self.is_running:
            try:
                # Show prompt
                if self.current_peer:
                    prompt = f"You (→ {self.current_peer}): "
                else:
                    prompt = "You (not connected): "

                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, prompt
                )

                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    await self.handle_command(user_input)
                else:
                    # Send message
                    if self.current_peer:
                        success = await self.send_message_to_peer(user_input)
                        if success:
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] Sent ✓")
                    else:
                        print("❌ Not connected. Use /connect <device_name>")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def handle_command(self, command: str):
        """Handle chat commands"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/discover":
            print("🔍 Discovering nearby devices...")
            peers = await self.discover_peers()

            if peers:
                print(f"\n✅ Found {len(peers)} device(s):")
                for i, peer in enumerate(peers, 1):
                    print(f"  {i}. {peer.name} (RSSI: {peer.rssi} dBm)")
                print(f"\nUse /connect <device_name> to connect")
            else:
                print("❌ No devices found")

        elif cmd == "/connect":
            if len(parts) < 2:
                print("Usage: /connect <device_name>")
                return

            peer_name = " ".join(parts[1:])
            print(f"🔗 Connecting to {peer_name}...")

            success = await self.connect_to_peer(peer_name)
            if success:
                print(f"✅ Connected to {peer_name}")
            else:
                print(f"❌ Failed to connect to {peer_name}")

        elif cmd == "/disconnect":
            if self.connected_client and self.connected_client.is_connected:
                await self.connected_client.disconnect()
                print(f"✅ Disconnected from {self.current_peer}")
                self.current_peer = None
            else:
                print("Not connected to any device")

        elif cmd == "/status":
            print(f"\nStatus:")
            print(f"  Your Name: {self.device_name}")
            print(f"  Server: {'Running' if self.server_ready else 'Not running'}")
            print(f"  Connected to: {self.current_peer or 'None'}")
            print(f"  Messages received: {len(self.received_messages)}")
            print(f"  Discovered devices: {len(self.discovered_devices)}")

        elif cmd == "/quit":
            print("\nExiting chat...")
            self.is_running = False

        else:
            print(f"Unknown command: {cmd}")

    async def start(self):
        """Start bidirectional chat"""
        print(f"\n{'='*60}")
        print(f"Starting Bidirectional Chat")
        print(f"{'='*60}")
        print(f"Device: {self.device_name}")
        print(f"{'='*60}\n")

        self.is_running = True

        # Start server in background
        server_task = asyncio.create_task(self.run_server())

        # Give server time to start
        await asyncio.sleep(2)

        if not self.server_ready:
            print("❌ Failed to start server")
            self.is_running = False
            return

        print("✅ Server started successfully\n")

        # Run chat interface
        try:
            await self.chat_loop()
        except KeyboardInterrupt:
            print("\n\nChat interrupted")
        finally:
            self.is_running = False
            server_task.cancel()

            if self.connected_client and self.connected_client.is_connected:
                await self.connected_client.disconnect()

    def stop(self):
        """Stop chat"""
        self.is_running = False


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("NotaGotchi BLE Bidirectional Chat Test")
    print("="*60 + "\n")

    # Get device name
    if len(sys.argv) > 1:
        device_name = sys.argv[1]
    else:
        device_name = input(f"Enter your device name (e.g., {config.TEST_DEVICE_A_NAME}): ").strip()
        if not device_name:
            device_name = config.TEST_DEVICE_A_NAME

    # Ensure name has prefix
    if not device_name.startswith(config.DEVICE_NAME_PREFIX):
        device_name = f"{config.DEVICE_NAME_PREFIX}_{device_name}"

    # Create and start chat
    chat = BidirectionalChat(device_name)

    try:
        asyncio.run(chat.start())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nChat ended. Goodbye!")


if __name__ == "__main__":
    main()
