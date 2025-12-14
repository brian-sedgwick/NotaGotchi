#!/usr/bin/env python3
"""
Complete Social System Test Script

Tests friends AND messaging together in one integrated system.

Usage:
    # On Pi 1
    python3 test_social_system.py Pet1

    # On Pi 2
    python3 test_social_system.py Pet2

Interactive commands:
    Friends:
      discover              - Find nearby devices
      request <device_name> - Send friend request
      pending               - Show pending friend requests
      accept <device_name>  - Accept friend request
      reject <device_name>  - Reject friend request
      friends               - List all friends
      ping <device_name>    - Check if friend is online
      remove <device_name>  - Remove friend

    Messaging:
      send <device_name> <message> - Send message to friend
      inbox                        - Show all received messages
      chat <device_name>           - Show conversation with friend
      read <device_name>           - Mark messages as read
      unread                       - Show unread message count
      queue                        - Show message queue status

    Other:
      help                  - Show this help
      quit                  - Exit
"""

import sys
import os
import time
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.wifi_manager import WiFiManager
from modules.friend_manager import FriendManager
from modules.messaging import MessageManager
from modules.social_coordinator import SocialCoordinator
from modules import config


def create_persistent_database(pet_name: str):
    """Create a persistent database for this pet"""
    # Use data directory if it exists, otherwise current directory
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    db_path = os.path.join(data_dir, f"social_test_{pet_name}.db")

    # Create connection and initialize tables
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")

    # Create all tables
    tables = [
        '''CREATE TABLE IF NOT EXISTS pet_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )''',
        '''CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL UNIQUE,
            pet_name TEXT NOT NULL,
            last_ip TEXT,
            last_port INTEGER,
            last_seen REAL,
            friendship_established REAL NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_device_name TEXT NOT NULL,
            from_pet_name TEXT NOT NULL,
            from_ip TEXT NOT NULL,
            from_port INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            request_time REAL NOT NULL,
            response_time REAL,
            expires_at REAL NOT NULL,
            UNIQUE(from_device_name)
        )''',
        '''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            from_device_name TEXT NOT NULL,
            from_pet_name TEXT NOT NULL,
            to_device_name TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'text',
            is_read INTEGER NOT NULL DEFAULT 0,
            received_at REAL NOT NULL,
            read_at REAL
        )''',
        '''CREATE TABLE IF NOT EXISTS message_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL UNIQUE,
            to_device_name TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'text',
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt REAL,
            next_retry REAL,
            created_at REAL NOT NULL,
            delivered_at REAL,
            failed_at REAL,
            error_message TEXT
        )'''
    ]

    for table_sql in tables:
        conn.execute(table_sql)

    # Insert or get pet
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM pet_state WHERE is_active = 1')
    if cursor.fetchone()[0] == 0:
        conn.execute('INSERT INTO pet_state (name, is_active) VALUES (?, 1)', (pet_name,))

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
    print("FRIENDS:")
    print("  discover                - Find nearby NotaGotchi devices")
    print("  request <device_name>   - Send friend request")
    print("  pending                 - Show pending friend requests")
    print("  accept <device_name>    - Accept friend request")
    print("  reject <device_name>    - Reject friend request")
    print("  friends                 - List all friends")
    print("  ping <device_name>      - Check if friend is online")
    print("  remove <device_name>    - Remove friend")
    print()
    print("MESSAGING:")
    print("  send <device_name> <msg> - Send message to friend")
    print("  inbox                    - Show all received messages")
    print("  chat <device_name>       - Show conversation with friend")
    print("  read <device_name>       - Mark messages as read")
    print("  unread                   - Show unread message count")
    print("  queue                    - Show message queue status")
    print()
    print("OTHER:")
    print("  help                     - Show this help")
    print("  quit                     - Exit")


# ============================================================================
# FRIEND COMMANDS
# ============================================================================

def cmd_discover(coordinator: SocialCoordinator):
    """Discover nearby devices"""
    print_header("Discovering Devices")
    print("Scanning network...")

    devices = coordinator.discover_nearby_devices()

    if not devices:
        print("❌ No devices found")
        print("\nMake sure another NotaGotchi is running:")
        print("  python3 test_social_system.py Pet2")
        return

    print(f"✅ Found {len(devices)} device(s):\n")

    for i, device in enumerate(devices, 1):
        is_friend = coordinator.is_friend(device['name'])
        friend_status = "✅ Friend" if is_friend else "➕ Not a friend"

        print(f"{i}. {device['name']}")
        print(f"   Address: {device['address']}:{device['port']}")
        print(f"   Status: {friend_status}")
        print()


def cmd_request(coordinator: SocialCoordinator, args: list):
    """Send friend request"""
    if not args:
        print("❌ Usage: request <device_name>")
        return

    target_name = ' '.join(args)
    print_header(f"Sending Friend Request to {target_name}")

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
        unread = coordinator.get_unread_count(friend['device_name'])
        unread_str = f" ({unread} unread)" if unread > 0 else ""

        print(f"{i}. {friend['pet_name']} ({friend['device_name']})")
        print(f"   Status: {online_status}{unread_str}")
        print(f"   Address: {friend['ip']}:{friend['port']}")

        if friend['last_seen'] and not friend['is_online']:
            mins = friend['minutes_since_seen']
            if mins < 60:
                print(f"   Last seen: {mins:.0f} minutes ago")
            elif mins < 1440:
                print(f"   Last seen: {mins/60:.1f} hours ago")
            else:
                print(f"   Last seen: {mins/1440:.1f} days ago")

        print()


def cmd_ping(coordinator: SocialCoordinator, args: list):
    """Ping a friend"""
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


# ============================================================================
# MESSAGING COMMANDS
# ============================================================================

def cmd_send(coordinator: SocialCoordinator, args: list):
    """Send message to friend"""
    if len(args) < 2:
        print("❌ Usage: send <device_name> <message>")
        return

    device_name = args[0]
    message = ' '.join(args[1:])

    print_header(f"Sending Message to {device_name}")

    if not coordinator.is_friend(device_name):
        print(f"❌ {device_name} is not your friend")
        print("Use 'discover' and 'request' to add them first")
        return

    message_id = coordinator.send_message(device_name, message)

    if message_id:
        print(f"✅ Message queued: {message}")
        print(f"   The message will be delivered automatically")
    else:
        print(f"❌ Failed to queue message")


def cmd_inbox(coordinator: SocialCoordinator):
    """Show inbox"""
    print_header("Inbox")

    inbox = coordinator.get_inbox(limit=50)

    if not inbox:
        print("No messages in inbox")
        return

    print(f"{len(inbox)} message(s):\n")

    for i, msg in enumerate(inbox, 1):
        read_status = "📖" if msg['is_read'] else "📬 NEW"
        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['received_at']))

        print(f"{i}. {read_status} From: {msg['from_pet_name']} ({msg['from_device_name']})")
        print(f"   {msg['content']}")
        print(f"   Received: {time_str}")
        print()


def cmd_chat(coordinator: SocialCoordinator, args: list):
    """Show conversation with friend"""
    if not args:
        print("❌ Usage: chat <device_name>")
        return

    device_name = ' '.join(args)
    print_header(f"Chat with {device_name}")

    friend = coordinator.get_friend(device_name)
    if not friend:
        print(f"❌ {device_name} is not your friend")
        return

    messages = coordinator.get_conversation(device_name, limit=50)

    if not messages:
        print(f"No messages with {friend['pet_name']} yet")
        print(f"\nSend a message with: send {device_name} <your message>")
        return

    print(f"{len(messages)} message(s) (newest first):\n")

    for msg in messages:
        time_str = time.strftime('%H:%M:%S', time.localtime(msg['received_at']))

        if msg['direction'] == 'sent':
            print(f"[{time_str}] You: {msg['content']}")
        else:
            read_mark = "" if msg['is_read'] else " [UNREAD]"
            print(f"[{time_str}] {msg['from_pet_name']}: {msg['content']}{read_mark}")

    print()


def cmd_read(coordinator: SocialCoordinator, args: list):
    """Mark messages as read"""
    if not args:
        print("❌ Usage: read <device_name>")
        return

    device_name = ' '.join(args)
    print_header(f"Marking Messages Read from {device_name}")

    unread_before = coordinator.get_unread_count(device_name)

    if unread_before == 0:
        print(f"No unread messages from {device_name}")
        return

    coordinator.mark_messages_read(friend_device_name=device_name)

    print(f"✅ Marked {unread_before} message(s) as read")


def cmd_unread(coordinator: SocialCoordinator):
    """Show unread count"""
    print_header("Unread Messages")

    total_unread = coordinator.get_unread_count()

    if total_unread == 0:
        print("No unread messages")
        return

    print(f"Total unread: {total_unread}\n")

    friends = coordinator.get_friends()

    for friend in friends:
        unread = coordinator.get_unread_count(friend['device_name'])
        if unread > 0:
            print(f"  {friend['pet_name']}: {unread} unread")


def cmd_queue(message_manager: MessageManager):
    """Show queue status"""
    print_header("Message Queue Status")

    status = message_manager.get_queue_status()

    print(f"Pending:   {status.get('pending', 0)}")
    print(f"Delivered: {status.get('delivered', 0)}")
    print(f"Failed:    {status.get('failed', 0)}")

    oldest_age = status.get('oldest_pending_age_seconds', 0)
    if oldest_age > 0:
        print(f"\nOldest pending message: {int(oldest_age)}s ago")


# ============================================================================
# MAIN
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_social_system.py <pet_name>")
        print("\nExample:")
        print("  python3 test_social_system.py Pet1")
        sys.exit(1)

    pet_name = sys.argv[1]
    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"

    print_header(f"NotaGotchi Social System Test - {pet_name}")

    # Create persistent database
    print("Initializing database...")
    db_path, db_conn = create_persistent_database(pet_name)
    print(f"✅ Database: {db_path}")

    # Initialize managers
    print("\nInitializing WiFi Manager...")
    wifi = WiFiManager(device_name)

    print("Initializing Friend Manager...")
    friend_mgr = FriendManager(db_conn, device_name)

    print("Initializing Message Manager...")
    message_mgr = MessageManager(db_conn, wifi, friend_mgr, device_name)

    print("Initializing Social Coordinator...")
    coordinator = SocialCoordinator(wifi, friend_mgr, pet_name, message_mgr)

    # Register UI callbacks
    def on_friend_request(request_info):
        print(f"\n🔔 Friend request from {request_info['pet_name']}")
        print("   Use 'pending' and 'accept <device_name>' to accept\n")
        print("> ", end='', flush=True)

    def on_request_accepted(friend_info):
        print(f"\n🔔 {friend_info['pet_name']} accepted your friend request!\n")
        print("> ", end='', flush=True)

    def on_message_received(message_data, sender_ip):
        print(f"\n📬 NEW MESSAGE from {message_data.get('from_pet_name')}:")
        print(f"   {message_data.get('content')}")
        print(f"   Use 'inbox' or 'chat {message_data.get('from_device_name')}' to view\n")
        print("> ", end='', flush=True)

    coordinator.register_ui_callbacks(
        on_friend_request=on_friend_request,
        on_request_accepted=on_request_accepted,
        on_message=on_message_received
    )

    # Start WiFi server
    print("\nStarting WiFi server...")
    if not wifi.start_server():
        print("❌ Failed to start WiFi server")
        sys.exit(1)

    # Start message queue processor
    print("Starting message queue processor...")
    message_mgr.start_queue_processor()

    print(f"\n✅ All systems running")
    print(f"   Device: {device_name}")
    print(f"   Port: {wifi.port}")
    print(f"   Database: {db_path} (persistent)")

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
                elif command == 'send':
                    cmd_send(coordinator, args)
                elif command == 'inbox':
                    cmd_inbox(coordinator)
                elif command == 'chat':
                    cmd_chat(coordinator, args)
                elif command == 'read':
                    cmd_read(coordinator, args)
                elif command == 'unread':
                    cmd_unread(coordinator)
                elif command == 'queue':
                    cmd_queue(message_mgr)
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
        message_mgr.stop_queue_processor()
        wifi.stop_server()
        db_conn.close()
        print(f"✅ Database saved: {db_path}")
        print("✅ Goodbye!")


if __name__ == "__main__":
    main()
