#!/usr/bin/env python3
"""
WiFi Manager Test Script

Tests the wifi_manager.py module on actual hardware.
Run this on two Raspberry Pis on the same network.

Usage:
    # On Pi 1 (server mode)
    python3 test_wifi_manager.py server TestPet1

    # On Pi 2 (client mode)
    python3 test_wifi_manager.py client TestPet2

    # Run all tests (server + client + discovery)
    python3 test_wifi_manager.py full TestPet1
"""

import sys
import os
import time
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.wifi_manager import WiFiManager
from modules import config


def test_server(pet_name: str):
    """Test 1: Server starts and accepts connections"""
    print(f"\n{'='*60}")
    print(f"TEST 1: Server Startup")
    print(f"{'='*60}\n")

    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"
    manager = WiFiManager(device_name)

    # Message counter
    messages_received = []

    def on_message(message_data: dict, sender_ip: str):
        print(f"\n✅ Message received from {sender_ip}:")
        print(f"   From: {message_data.get('from_device_name')}")
        print(f"   Content: {message_data.get('content')}")
        print(f"   Type: {message_data.get('content_type')}")
        messages_received.append(message_data)

    # Register callback
    manager.register_callback(on_message)

    # Start server
    print("Starting WiFi server...")
    success = manager.start_server()

    if not success:
        print("❌ Server failed to start")
        return False

    print(f"✅ Server started successfully")
    print(f"   Device: {device_name}")
    print(f"   Port: {manager.port}")
    print("\nServer is now listening for messages...")
    print("Press Ctrl+C to stop\n")

    try:
        # Keep server running
        while True:
            time.sleep(1)
            if messages_received:
                print(f"Total messages received: {len(messages_received)}")
                messages_received.clear()

    except KeyboardInterrupt:
        print("\n\nStopping server...")
        manager.stop_server()
        print("✅ Server stopped cleanly")
        return True


def test_discovery(pet_name: str):
    """Test 2: Device discovery"""
    print(f"\n{'='*60}")
    print(f"TEST 2: Device Discovery")
    print(f"{'='*60}\n")

    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"
    manager = WiFiManager(device_name)

    print("Discovering NotaGotchi devices on network...")
    print(f"(waiting {config.WIFI_DISCOVERY_TIMEOUT} seconds)\n")

    devices = manager.discover_devices()

    if not devices:
        print("⚠️  No devices found")
        print("\nMake sure another NotaGotchi is running in server mode:")
        print("  python3 test_wifi_manager.py server TestPet1")
        return False

    print(f"✅ Found {len(devices)} device(s):\n")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device['name']}")
        print(f"   Address: {device['address']}:{device['port']}")
        print(f"   Properties: {device['properties']}")
        print()

    return True


def test_client(pet_name: str):
    """Test 3: Send message and receive acknowledgment"""
    print(f"\n{'='*60}")
    print(f"TEST 3: Send Message")
    print(f"{'='*60}\n")

    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"
    manager = WiFiManager(device_name)

    # Discover devices
    print("Discovering devices...")
    devices = manager.discover_devices()

    if not devices:
        print("❌ No devices found to send message to")
        print("\nMake sure another NotaGotchi is running in server mode")
        return False

    # Choose first device
    target = devices[0]
    print(f"\n✅ Found target: {target['name']}")
    print(f"   Address: {target['address']}:{target['port']}\n")

    # Send test message
    message_data = {
        "message_id": f"test_{int(time.time()*1000)}",
        "from_device_name": device_name,
        "from_pet_name": pet_name,
        "content": f"Hello from {pet_name}! This is a test message.",
        "content_type": "text",
        "timestamp": time.time()
    }

    print("Sending test message...")
    success = manager.send_message(
        target['address'],
        target['port'],
        message_data
    )

    if success:
        print("✅ Message sent and acknowledged successfully!")
        return True
    else:
        print("❌ Failed to send message")
        return False


def test_thread_safety(pet_name: str):
    """Test 4: Thread safety with concurrent messages"""
    print(f"\n{'='*60}")
    print(f"TEST 4: Thread Safety (Concurrent Messages)")
    print(f"{'='*60}\n")

    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"
    manager = WiFiManager(device_name)

    # Discover devices
    print("Discovering devices...")
    devices = manager.discover_devices()

    if not devices:
        print("❌ No devices found")
        return False

    target = devices[0]
    print(f"✅ Target: {target['name']}\n")

    # Send multiple messages concurrently
    num_messages = 5
    results = []

    def send_concurrent_message(i: int):
        message_data = {
            "message_id": f"concurrent_{i}_{int(time.time()*1000)}",
            "from_device_name": device_name,
            "from_pet_name": pet_name,
            "content": f"Concurrent message #{i}",
            "content_type": "text",
            "timestamp": time.time()
        }
        success = manager.send_message(
            target['address'],
            target['port'],
            message_data
        )
        results.append(success)
        print(f"   Message {i}: {'✅' if success else '❌'}")

    print(f"Sending {num_messages} concurrent messages...\n")

    threads = []
    for i in range(num_messages):
        thread = threading.Thread(target=send_concurrent_message, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    success_count = sum(results)
    print(f"\n{'='*60}")
    print(f"Results: {success_count}/{num_messages} messages succeeded")
    print(f"{'='*60}\n")

    return success_count == num_messages


def test_reachability(pet_name: str):
    """Test 5: Device reachability check"""
    print(f"\n{'='*60}")
    print(f"TEST 5: Device Reachability")
    print(f"{'='*60}\n")

    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"
    manager = WiFiManager(device_name)

    # Discover devices
    print("Discovering devices...")
    devices = manager.discover_devices()

    if not devices:
        print("⚠️  No devices to test")
        return False

    print(f"\nTesting reachability of {len(devices)} device(s):\n")

    for device in devices:
        is_reachable = manager.is_device_reachable(
            device['address'],
            device['port']
        )
        status = "✅ Reachable" if is_reachable else "❌ Unreachable"
        print(f"{device['name']}: {status}")

    return True


def run_full_test(pet_name: str):
    """Run all tests in sequence"""
    print(f"\n{'='*60}")
    print(f"FULL TEST SUITE")
    print(f"Pet Name: {pet_name}")
    print(f"{'='*60}\n")

    tests = [
        ("Discovery", lambda: test_discovery(pet_name)),
        ("Reachability", lambda: test_reachability(pet_name)),
        ("Send Message", lambda: test_client(pet_name)),
        ("Thread Safety", lambda: test_thread_safety(pet_name)),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            print(f"\nRunning {test_name} test...")
            results[test_name] = test_func()
            time.sleep(2)  # Brief pause between tests
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}\n")

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")

    passed_count = sum(results.values())
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    return passed_count == total_count


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Server mode:  python3 test_wifi_manager.py server <pet_name>")
        print("  Client mode:  python3 test_wifi_manager.py client <pet_name>")
        print("  Full test:    python3 test_wifi_manager.py full <pet_name>")
        print("\nExamples:")
        print("  python3 test_wifi_manager.py server TestPet1")
        print("  python3 test_wifi_manager.py client TestPet2")
        print("  python3 test_wifi_manager.py full TestPet1")
        sys.exit(1)

    mode = sys.argv[1]
    pet_name = sys.argv[2]

    if mode == "server":
        test_server(pet_name)
    elif mode == "client":
        test_client(pet_name)
    elif mode == "full":
        success = run_full_test(pet_name)
        sys.exit(0 if success else 1)
    elif mode == "discovery":
        test_discovery(pet_name)
    else:
        print(f"❌ Unknown mode: {mode}")
        print("Valid modes: server, client, full, discovery")
        sys.exit(1)


if __name__ == "__main__":
    main()
