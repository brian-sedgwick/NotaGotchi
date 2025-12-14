#!/usr/bin/env python3
"""
Wi-Fi Client Test for NotaGotchi - TCP Client with mDNS Discovery

Tests TCP client functionality with mDNS service discovery.
This device will:
1. Discover NotaGotchi servers via mDNS
2. Connect to a server via TCP
3. Send messages

Usage:
    # Interactive mode
    python3 test_wifi_client.py

    # Send single message
    python3 test_wifi_client.py <target_device_name> <message>

Example:
    python3 test_wifi_client.py NotaGotchi_TestA "Hello from TestB!"
"""

import socket
import json
import time
import sys
from typing import Dict, Optional
import test_wifi_config as config
from test_wifi_discovery_avahi import discover_via_avahi as discover_devices


def send_message(
    target_address: str,
    target_port: int,
    from_device_name: str,
    message_content: str,
    content_type: str = "text"
) -> bool:
    """
    Send a message to a NotaGotchi device

    Args:
        target_address: IP address of target device
        target_port: TCP port of target device
        from_device_name: Name of this device
        message_content: Message text to send
        content_type: Type of content (text, emoji, etc.)

    Returns:
        True if message sent successfully, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Sending Message")
    print(f"{'='*60}")
    print(f"To: {target_address}:{target_port}")
    print(f"From: {from_device_name}")
    print(f"Content: {message_content}")
    print(f"{'='*60}\n")

    try:
        # Create message
        message = {
            "message_id": f"msg_{int(time.time()*1000)}",
            "from_device_name": from_device_name,
            "from_pet_name": "TestPet",
            "content": message_content,
            "content_type": content_type,
            "timestamp": time.time()
        }

        # Serialize to JSON
        message_json = json.dumps(message)
        message_bytes = message_json.encode(config.MESSAGE_ENCODING)

        print(f"📦 Message size: {len(message_bytes)} bytes")

        if len(message_bytes) > config.MAX_MESSAGE_SIZE:
            print(f"❌ Message too large (max {config.MAX_MESSAGE_SIZE} bytes)")
            return False

        # Connect to server
        print(f"🔌 Connecting to {target_address}:{target_port}...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(config.CONNECTION_TIMEOUT_SECONDS)
        client_socket.connect((target_address, target_port))

        print(f"✅ Connected!")

        # Send message
        print(f"📤 Sending message...")
        client_socket.sendall(message_bytes)

        # Wait for acknowledgment
        print(f"⏳ Waiting for acknowledgment...")
        response_data = client_socket.recv(1024)

        if response_data:
            response = json.loads(response_data.decode(config.MESSAGE_ENCODING))
            if response.get("status") == "received":
                print(f"✅ Message delivered successfully!")
                print(f"   Server acknowledged at: {time.strftime('%H:%M:%S', time.localtime(response.get('timestamp', 0)))}")
                client_socket.close()
                return True
            else:
                print(f"⚠️  Unexpected response: {response}")
                client_socket.close()
                return False
        else:
            print(f"⚠️  No acknowledgment received")
            client_socket.close()
            return False

    except socket.timeout:
        print(f"❌ Connection timeout")
        return False
    except ConnectionRefusedError:
        print(f"❌ Connection refused - is server running?")
        return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        import traceback
        traceback.print_exc()
        return False


def interactive_mode():
    """Interactive client mode - discover and send messages"""
    print(f"\n{'='*60}")
    print(f"NotaGotchi Wi-Fi Client - Interactive Mode")
    print(f"{'='*60}\n")

    # Discover devices
    print("Discovering NotaGotchi devices...")
    devices = discover_devices()

    if not devices:
        print("\n❌ No devices found. Make sure a server is running.")
        print("On another Raspberry Pi, run:")
        print("  python3 test_wifi_server.py NotaGotchi_TestA")
        return

    # Choose device
    print(f"\n{'='*60}")
    print("Select a device to send a message to:")
    print(f"{'='*60}")

    for i, device in enumerate(devices, 1):
        print(f"{i}. {device['name']} ({device['address']}:{device['port']})")

    print()
    choice = input("Enter device number (or 0 to cancel): ").strip()

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(devices):
            print("❌ Invalid choice")
            return

        target_device = devices[idx]

        # Get message
        print()
        message = input("Enter message to send: ").strip()

        if not message:
            print("❌ Empty message")
            return

        # Get sender name
        from_device_name = input("Enter your device name (default: NotaGotchi_TestB): ").strip()
        if not from_device_name:
            from_device_name = config.TEST_DEVICE_B_NAME

        # Send message
        success = send_message(
            target_device['address'],
            target_device['port'],
            from_device_name,
            message
        )

        if success:
            print(f"\n{'='*60}")
            print("✅ Message sent successfully!")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print("❌ Failed to send message")
            print(f"{'='*60}\n")

    except ValueError:
        print("❌ Invalid input")
    except KeyboardInterrupt:
        print("\n\nCancelled by user")


def single_message_mode(target_name: str, message: str, from_name: str = None):
    """Send a single message to a specific device"""
    print(f"\n{'='*60}")
    print(f"NotaGotchi Wi-Fi Client - Single Message Mode")
    print(f"{'='*60}\n")

    # Discover devices
    print(f"Looking for '{target_name}'...")
    devices = discover_devices()

    # Find target device
    target_device = None
    for device in devices:
        if device['name'] == target_name:
            target_device = device
            break

    if not target_device:
        print(f"\n❌ Device '{target_name}' not found")
        print("\nFound devices:")
        for device in devices:
            print(f"  - {device['name']}")
        return False

    # Set default from name
    if from_name is None:
        from_name = config.TEST_DEVICE_B_NAME

    # Send message
    success = send_message(
        target_device['address'],
        target_device['port'],
        from_name,
        message
    )

    return success


def main():
    """Main entry point"""
    print(f"\n{'='*60}")
    print(f"NotaGotchi Wi-Fi Client Test")
    print(f"{'='*60}\n")

    try:
        if len(sys.argv) >= 3:
            # Single message mode
            target_name = sys.argv[1]
            message = sys.argv[2]
            from_name = sys.argv[3] if len(sys.argv) > 3 else None

            success = single_message_mode(target_name, message, from_name)
            sys.exit(0 if success else 1)
        else:
            # Interactive mode
            interactive_mode()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
