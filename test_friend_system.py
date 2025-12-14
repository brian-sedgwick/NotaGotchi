#!/usr/bin/env python3
"""
Friend System Test Script

Tests the complete friend request protocol with WiFi + Friend Manager + Social Coordinator.

Run this on two Raspberry Pis on the same network to test the friend system.

Usage:
    # On Pi 1
    python3 test_friend_system.py Pet1

    # On Pi 2
    python3 test_friend_system.py Pet2

Interactive commands:
    - discover: Find nearby devices
    - request <device_name>: Send friend request
    - pending: Show pending friend requests
    - accept <device_name>: Accept friend request
    - reject <device_name>: Reject friend request
    - friends: List all friends
    - ping <device_name>: Check if friend is online
    - remove <device_name>: Remove friend
    - quit: Exit
"""

import sys
import os
import time
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.wifi_manager import WiFiManager
from modules.friend_manager import FriendManager
from modules.social_coordinator import SocialCoordinator
from modules import config


def create_test_database(pet_name: str) -> str:
    """Create a test database for this pet"""
    db_path = f"test_friend_{pet_name}.db"

    # Remove old test database
    if os.path.exists(db_path):
        os.remove(db_path)

    # Create connection and initialize tables
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    # Create friends table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL UNIQUE,
            pet_name TEXT NOT NULL,
            last_ip TEXT,
            last_port INTEGER,
            last_seen REAL,
            friendship_established REAL NOT NULL,
            created_at REAL NOT NULL DEFAULT (julianday('now'))
        )
    ''')

    # Create friend_requests table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_device_name TEXT NOT NULL,
            from_pet_name TEXT NOT NULL,
            from_ip TEXT NOT NULL,
            from_port INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            request_time REAL NOT NULL,
            response_time REAL,
            expires_at REAL NOT NULL,
            created_at REAL NOT NULL DEFAULT (julianday('now')),
            UNIQUE(from_device_name)
        )
    ''')

    conn.commit()
    return db_path, conn


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")


def print_help():
    """Print available commands"""
    print_header("Available Commands")
    print("discover              - Find nearby NotaGotchi devices")
    print("request <device_name> - Send friend request to device")
    print("pending               - Show pending friend requests")
    print("accept <device_name>  - Accept friend request")
    print("reject <device_name>  - Reject friend request")
    print("friends               - List all friends")
    print("ping <device_name>    - Check if friend is online")
    print("remove <device_name>  - Remove friend")
    print("help                  - Show this help")
    print("quit                  - Exit test")


def cmd_discover(coordinator: SocialCoordinator):
    """Discover nearby devices"""
    print_header("Discovering Devices")
    print("Scanning network...")

    devices = coordinator.discover_nearby_devices()

    if not devices:
        print("❌ No devices found")
        print("\nMake sure another NotaGotchi is running:")
        print("  python3 test_friend_system.py Pet2")
        return

    print(f"✅ Found {len(devices)} device(s):\n")

    for i, device in enumerate(devices, 1):
        # Check if already friends
        is_friend = coordinator.is_friend(device['name'])
        friend_status = "✅ Friend" if is_friend else "➕ Not a friend"

        print(f"{i}. {device['name']}")
        print(f"   Address: {device['address']}:{device['port']}")
        print(f"   Status: {friend_status}")
        print(f"   Properties: {device.get('properties', {})}")
        print()


def cmd_request(coordinator: SocialCoordinator, args: list):
    """Send friend request"""
    if not args:
        print("❌ Usage: request <device_name>")
        return

    target_name = ' '.join(args)

    print_header(f"Sending Friend Request to {target_name}")

    # Discover to get device info
    devices = coordinator.discover_nearby_devices()
    target = None

    for device in devices:
        if device['name'] == target_name:
            target = device
            break

    if not target:
        print(f"❌ Device '{target_name}' not found")
        print("\nRun 'discover' to see available devices")
        return

    # Send request
    success = coordinator.send_friend_request(target)

    if success:
        print(f"✅ Friend request sent to {target_name}")
        print("Wait for the other device to accept...")
    else:
        print(f"❌ Failed to send friend request")


def cmd_pending(coordinator: SocialCoordinator):
    """Show pending friend requests"""
    print_header("Pending Friend Requests")

    requests = coordinator.get_pending_requests()

    if not requests:
        print("No pending friend requests")
        return

    print(f"{len(requests)} pending request(s):\n")

    for i, req in enumerate(requests, 1):
        hours_left = req['hours_until_expiry']
        print(f"{i}. {req['pet_name']} ({req['device_name']})")
        print(f"   From: {req['ip']}:{req['port']}")
        print(f"   Expires in: {hours_left:.1f} hours")
        print(f"   Received: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(req['request_time']))}")
        print()


def cmd_accept(coordinator: SocialCoordinator, args: list):
    """Accept friend request"""
    if not args:
        print("❌ Usage: accept <device_name>")
        return

    device_name = ' '.join(args)

    print_header(f"Accepting Friend Request from {device_name}")

    success = coordinator.accept_friend_request(device_name)

    if success:
        print(f"✅ Friend request accepted!")
        print(f"   {device_name} is now your friend")
    else:
        print(f"❌ Failed to accept friend request")
        print(f"   No pending request from {device_name}")


def cmd_reject(coordinator: SocialCoordinator, args: list):
    """Reject friend request"""
    if not args:
        print("❌ Usage: reject <device_name>")
        return

    device_name = ' '.join(args)

    print_header(f"Rejecting Friend Request from {device_name}")

    success = coordinator.reject_friend_request(device_name)

    if success:
        print(f"Friend request from {device_name} rejected")
    else:
        print(f"❌ No pending request from {device_name}")


def cmd_friends(coordinator: SocialCoordinator):
    """List all friends"""
    print_header("Friends List")

    friends = coordinator.get_friends()

    if not friends:
        print("No friends yet")
        print("\nUse 'discover' and 'request' to find and add friends")
        return

    print(f"{len(friends)} friend(s):\n")

    for i, friend in enumerate(friends, 1):
        online_status = "🟢 Online" if friend['is_online'] else "⚪ Offline"

        print(f"{i}. {friend['pet_name']} ({friend['device_name']})")
        print(f"   Status: {online_status}")
        print(f"   Address: {friend['ip']}:{friend['port']}")

        if friend['last_seen']:
            if friend['is_online']:
                print(f"   Last seen: Just now")
            else:
                mins = friend['minutes_since_seen']
                if mins < 60:
                    print(f"   Last seen: {mins:.0f} minutes ago")
                elif mins < 1440:
                    print(f"   Last seen: {mins/60:.1f} hours ago")
                else:
                    print(f"   Last seen: {mins/1440:.1f} days ago")

        print(f"   Friends since: {time.strftime('%Y-%m-%d %H:%M', time.localtime(friend['friendship_established']))}")
        print()


def cmd_ping(coordinator: SocialCoordinator, args: list):
    """Ping a friend to check if online"""
    if not args:
        print("❌ Usage: ping <device_name>")
        return

    device_name = ' '.join(args)

    print_header(f"Pinging {device_name}")

    friend = coordinator.get_friend(device_name)
    if not friend:
        print(f"❌ {device_name} is not in your friends list")
        return

    print(f"Checking if {friend['pet_name']} is online...")

    is_online = coordinator.ping_friend(device_name)

    if is_online:
        print(f"✅ {friend['pet_name']} is online!")
    else:
        print(f"⚪ {friend['pet_name']} is offline")


def cmd_remove(coordinator: SocialCoordinator, args: list):
    """Remove a friend"""
    if not args:
        print("❌ Usage: remove <device_name>")
        return

    device_name = ' '.join(args)

    print_header(f"Removing Friend: {device_name}")

    friend = coordinator.get_friend(device_name)
    if not friend:
        print(f"❌ {device_name} is not in your friends list")
        return

    confirm = input(f"Are you sure you want to remove {friend['pet_name']}? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled")
        return

    success = coordinator.remove_friend(device_name)

    if success:
        print(f"✅ {friend['pet_name']} removed from friends")
    else:
        print(f"❌ Failed to remove friend")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_friend_system.py <pet_name>")
        print("\nExample:")
        print("  python3 test_friend_system.py Pet1")
        sys.exit(1)

    pet_name = sys.argv[1]
    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"

    print_header(f"NotaGotchi Friend System Test - {pet_name}")

    # Create test database
    print("Creating test database...")
    db_path, db_conn = create_test_database(pet_name)
    print(f"✅ Database: {db_path}")

    # Initialize managers
    print("\nInitializing WiFi Manager...")
    wifi = WiFiManager(device_name)

    print("Initializing Friend Manager...")
    friend_mgr = FriendManager(db_conn, device_name)

    print("Initializing Social Coordinator...")
    coordinator = SocialCoordinator(wifi, friend_mgr, pet_name)

    # Register UI callbacks
    def on_request_received(request_info):
        print(f"\n🔔 NOTIFICATION: Friend request received from {request_info['pet_name']}")
        print("   Use 'pending' to see pending requests")
        print("   Use 'accept <device_name>' to accept\n")
        print("> ", end='', flush=True)

    def on_request_accepted(friend_info):
        print(f"\n🔔 NOTIFICATION: {friend_info['pet_name']} accepted your friend request!")
        print("   You are now friends!")
        print(f"   Use 'friends' to see all friends\n")
        print("> ", end='', flush=True)

    coordinator.register_ui_callbacks(
        on_friend_request=on_request_received,
        on_request_accepted=on_request_accepted
    )

    # Start WiFi server
    print("\nStarting WiFi server...")
    if not wifi.start_server():
        print("❌ Failed to start WiFi server")
        sys.exit(1)

    print(f"✅ WiFi server running")
    print(f"   Device: {device_name}")
    print(f"   Port: {wifi.port}")

    # Interactive mode
    print_header("Interactive Mode")
    print("Type 'help' for available commands")
    print("Type 'quit' to exit")

    try:
        while True:
            try:
                cmd_input = input("\n> ").strip()

                if not cmd_input:
                    continue

                parts = cmd_input.split()
                command = parts[0].lower()
                args = parts[1:]

                if command == 'quit' or command == 'exit':
                    break
                elif command == 'help':
                    print_help()
                elif command == 'discover':
                    cmd_discover(coordinator)
                elif command == 'request':
                    cmd_request(coordinator, args)
                elif command == 'pending':
                    cmd_pending(coordinator)
                elif command == 'accept':
                    cmd_accept(coordinator, args)
                elif command == 'reject':
                    cmd_reject(coordinator, args)
                elif command == 'friends':
                    cmd_friends(coordinator)
                elif command == 'ping':
                    cmd_ping(coordinator, args)
                elif command == 'remove':
                    cmd_remove(coordinator, args)
                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n\nUse 'quit' to exit")
                continue

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n\nShutting down...")
        wifi.stop_server()
        db_conn.close()

        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Test database removed: {db_path}")

        print("✅ Goodbye!")


if __name__ == "__main__":
    main()
