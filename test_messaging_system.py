#!/usr/bin/env python3
"""
Messaging System Test Script

Tests the complete messaging system with friends, queueing, and retry logic.

Run this on two Raspberry Pis that are already friends.

Usage:
    # On Pi 1
    python3 test_messaging_system.py Pet1

    # On Pi 2
    python3 test_messaging_system.py Pet2

Interactive commands:
    - send <device_name> <message>: Send message to friend
    - inbox: Show all received messages
    - conversation <device_name>: Show conversation with friend
    - read <device_name>: Mark all messages from friend as read
    - unread: Show unread message count
    - queue: Show message queue status
    - friends: List all friends
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
from modules.messaging import MessageManager
from modules.social_coordinator import SocialCoordinator
from modules import config


def create_test_database(pet_name: str):
    """Create a test database for this pet"""
    db_path = f"test_messaging_{pet_name}.db"

    # Remove old test database
    if os.path.exists(db_path):
        os.remove(db_path)

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

    # Insert test pet
    conn.execute('''
        INSERT INTO pet_state (name, is_active) VALUES (?, 1)
    ''', (pet_name,))

    conn.commit()
    return db_path, conn


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")


def cmd_send(coordinator: SocialCoordinator, args: list):
    """Send message to friend"""
    if len(args) < 2:
        print("❌ Usage: send <device_name> <message>")
        return

    device_name = args[0]
    message = ' '.join(args[1:])

    print_header(f"Sending Message to {device_name}")

    # Check if friend
    if not coordinator.is_friend(device_name):
        print(f"❌ {device_name} is not your friend")
        print("Use friend system test to add friends first")
        return

    # Send message
    message_id = coordinator.send_message(device_name, message)

    if message_id:
        print(f"✅ Message queued: {message}")
        print(f"   Message ID: {message_id}")
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


def cmd_conversation(coordinator: SocialCoordinator, args: list):
    """Show conversation with friend"""
    if not args:
        print("❌ Usage: conversation <device_name>")
        return

    device_name = ' '.join(args)

    print_header(f"Conversation with {device_name}")

    # Get friend info
    friend = coordinator.get_friend(device_name)
    if not friend:
        print(f"❌ {device_name} is not your friend")
        return

    # Get conversation
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

    # Show per-friend breakdown
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


def cmd_friends(coordinator: SocialCoordinator):
    """List friends"""
    print_header("Friends List")

    friends = coordinator.get_friends()

    if not friends:
        print("No friends yet")
        print("\nUse test_friend_system.py to add friends first")
        return

    print(f"{len(friends)} friend(s):\n")

    for i, friend in enumerate(friends, 1):
        online_status = "🟢 Online" if friend['is_online'] else "⚪ Offline"
        unread = coordinator.get_unread_count(friend['device_name'])
        unread_str = f" ({unread} unread)" if unread > 0 else ""

        print(f"{i}. {friend['pet_name']} ({friend['device_name']})")
        print(f"   Status: {online_status}{unread_str}")
        print(f"   Address: {friend['ip']}:{friend['port']}")
        print()


def print_help():
    """Print available commands"""
    print_header("Available Commands")
    print("send <device_name> <message> - Send message to friend")
    print("inbox                         - Show all received messages")
    print("conversation <device_name>    - Show conversation with friend")
    print("read <device_name>            - Mark all messages from friend as read")
    print("unread                        - Show unread message count")
    print("queue                         - Show message queue status")
    print("friends                       - List all friends")
    print("help                          - Show this help")
    print("quit                          - Exit test")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_messaging_system.py <pet_name>")
        print("\nExample:")
        print("  python3 test_messaging_system.py Pet1")
        sys.exit(1)

    pet_name = sys.argv[1]
    device_name = f"{config.DEVICE_ID_PREFIX}_{pet_name}"

    print_header(f"NotaGotchi Messaging Test - {pet_name}")

    # Create test database
    print("Creating test database...")
    db_path, db_conn = create_test_database(pet_name)
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
    def on_message_received(message_data, sender_ip):
        print(f"\n📬 NEW MESSAGE from {message_data.get('from_pet_name')}:")
        print(f"   {message_data.get('content')}")
        print(f"   Use 'inbox' or 'conversation {message_data.get('from_device_name')}' to view\n")
        print("> ", end='', flush=True)

    def on_message_delivered(message_id, to_device_name):
        print(f"\n✅ Message delivered to {to_device_name}")
        print("> ", end='', flush=True)

    coordinator.register_ui_callbacks(on_message=on_message_received)
    message_mgr.on_message_delivered = on_message_delivered

    # Start WiFi server
    print("\nStarting WiFi server...")
    if not wifi.start_server():
        print("❌ Failed to start WiFi server")
        sys.exit(1)

    # Start message queue processor
    print("Starting message queue processor...")
    message_mgr.start_queue_processor()

    print(f"✅ All systems running")
    print(f"   Device: {device_name}")
    print(f"   Port: {wifi.port}")

    # Interactive mode
    print_header("Interactive Mode")
    print("Type 'help' for available commands")
    print("Type 'quit' to exit")

    # Show friends on startup
    cmd_friends(coordinator)

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
                elif command == 'send':
                    cmd_send(coordinator, args)
                elif command == 'inbox':
                    cmd_inbox(coordinator)
                elif command == 'conversation':
                    cmd_conversation(coordinator, args)
                elif command == 'read':
                    cmd_read(coordinator, args)
                elif command == 'unread':
                    cmd_unread(coordinator)
                elif command == 'queue':
                    cmd_queue(message_mgr)
                elif command == 'friends':
                    cmd_friends(coordinator)
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

        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Test database removed: {db_path}")

        print("✅ Goodbye!")


if __name__ == "__main__":
    main()
