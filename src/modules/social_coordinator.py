"""
Social Coordinator Module

Coordinates WiFi communication and friend management for NotaGotchi social features.

This module acts as the glue between:
- WiFiManager (handles network communication)
- FriendManager (manages friend database)

Implements the complete friend request protocol:
1. Device A sends friend request to Device B
2. Device B receives and stores request
3. Device B user accepts request
4. Device B sends acceptance to Device A
5. Both devices are now friends
"""

import time
import json
from typing import Optional, Callable, Dict, Any
from . import config
from .wifi_manager import WiFiManager
from .friend_manager import FriendManager


class SocialCoordinator:
    """
    Coordinates WiFi and friend management for social features

    This is the main interface for social features in NotaGotchi.
    """

    def __init__(self, wifi_manager: WiFiManager, friend_manager: FriendManager,
                 own_pet_name: str):
        """
        Initialize Social Coordinator

        Args:
            wifi_manager: WiFiManager instance
            friend_manager: FriendManager instance
            own_pet_name: This pet's name
        """
        self.wifi = wifi_manager
        self.friends = friend_manager
        self.own_pet_name = own_pet_name

        # Callbacks for UI notifications
        self.on_friend_request_received: Optional[Callable] = None
        self.on_friend_request_accepted: Optional[Callable] = None
        self.on_friend_request_rejected: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None

        # Register WiFi callback
        self.wifi.register_callback(self._handle_incoming_message)

    # ========================================================================
    # FRIEND REQUEST PROTOCOL
    # ========================================================================

    def send_friend_request(self, target_device: Dict[str, Any]) -> bool:
        """
        Send friend request to a discovered device

        Args:
            target_device: Device dict from discover_devices()
                          Must contain: name, address, port

        Returns:
            True if request sent successfully
        """
        target_name = target_device['name']
        target_ip = target_device['address']
        target_port = target_device['port']

        # Check if already friends
        if self.friends.is_friend(target_name):
            print(f"⚠️  Already friends with {target_name}")
            return False

        # Check if at friend limit
        if not self.friends.can_add_more_friends():
            print(f"❌ Friend limit reached ({config.MAX_FRIENDS} friends)")
            return False

        # Build friend request message
        message = {
            "type": "friend_request",
            "from_device_name": self.wifi.device_name,
            "from_pet_name": self.own_pet_name,
            "from_ip": self.wifi._get_local_ip(),
            "from_port": self.wifi.port,
            "timestamp": time.time()
        }

        print(f"Sending friend request to {target_name}...")

        # Send via WiFi
        success = self.wifi.send_message(target_ip, target_port, message)

        if success:
            print(f"✅ Friend request sent to {target_name}")
        else:
            print(f"❌ Failed to send friend request to {target_name}")

        return success

    def accept_friend_request(self, from_device_name: str) -> bool:
        """
        Accept a pending friend request

        This will:
        1. Add friend to local friends list
        2. Send acceptance message to requester
        3. Requester will add us to their friends list

        Args:
            from_device_name: Device name to accept

        Returns:
            True if accepted and acceptance sent
        """
        # Accept in database
        friend_info = self.friends.accept_friend_request(from_device_name)
        if not friend_info:
            return False

        # Send acceptance message back to requester
        message = {
            "type": "friend_request_accepted",
            "from_device_name": self.wifi.device_name,
            "from_pet_name": self.own_pet_name,
            "accepted_device_name": from_device_name,
            "timestamp": time.time()
        }

        success = self.wifi.send_message(
            friend_info['ip'],
            friend_info['port'],
            message
        )

        if success:
            print(f"✅ Acceptance sent to {friend_info['pet_name']}")

            # Notify UI
            if self.on_friend_request_accepted:
                self.on_friend_request_accepted(friend_info)
        else:
            print(f"⚠️  Friend added but couldn't send acceptance to {friend_info['pet_name']}")

        return True

    def reject_friend_request(self, from_device_name: str) -> bool:
        """
        Reject a pending friend request

        Args:
            from_device_name: Device name to reject

        Returns:
            True if rejected successfully
        """
        success = self.friends.reject_friend_request(from_device_name)

        if success and self.on_friend_request_rejected:
            self.on_friend_request_rejected(from_device_name)

        return success

    # ========================================================================
    # DEVICE DISCOVERY
    # ========================================================================

    def discover_nearby_devices(self) -> list:
        """
        Discover NotaGotchi devices on the network

        Returns:
            List of discovered devices (not filtered by friendship)
        """
        return self.wifi.discover_devices()

    def discover_new_devices(self) -> list:
        """
        Discover devices that aren't already friends

        Useful for "Find Friends" screen

        Returns:
            List of discovered devices that aren't friends yet
        """
        all_devices = self.wifi.discover_devices()

        # Filter out devices that are already friends
        new_devices = []
        for device in all_devices:
            if not self.friends.is_friend(device['name']):
                new_devices.append(device)

        return new_devices

    # ========================================================================
    # FRIEND MANAGEMENT
    # ========================================================================

    def get_friends(self, online_only: bool = False) -> list:
        """
        Get friends list

        Args:
            online_only: Only return friends seen recently

        Returns:
            List of friend dicts
        """
        return self.friends.get_friends(online_only=online_only)

    def get_friend(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Get info about a specific friend"""
        return self.friends.get_friend(device_name)

    def remove_friend(self, device_name: str) -> bool:
        """Remove a friend"""
        return self.friends.remove_friend(device_name)

    def is_friend(self, device_name: str) -> bool:
        """Check if device is a friend"""
        return self.friends.is_friend(device_name)

    def get_pending_requests(self) -> list:
        """Get pending friend requests"""
        return self.friends.get_pending_requests()

    # ========================================================================
    # MESSAGE HANDLING (Callback from WiFi Manager)
    # ========================================================================

    def _handle_incoming_message(self, message_data: Dict, sender_ip: str):
        """
        Handle incoming WiFi messages

        This is registered as a callback with WiFi Manager.
        Routes messages based on type.

        Args:
            message_data: Parsed message dict
            sender_ip: IP address of sender
        """
        message_type = message_data.get('type')

        if message_type == 'friend_request':
            self._handle_friend_request(message_data, sender_ip)

        elif message_type == 'friend_request_accepted':
            self._handle_friend_request_accepted(message_data, sender_ip)

        elif message_type == 'message':
            self._handle_chat_message(message_data, sender_ip)

        else:
            print(f"⚠️  Unknown message type: {message_type}")

    def _handle_friend_request(self, message_data: Dict, sender_ip: str):
        """Handle incoming friend request"""
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        from_ip = message_data.get('from_ip', sender_ip)  # Fallback to sender_ip
        from_port = message_data.get('from_port', config.WIFI_PORT)

        print(f"\n{'='*60}")
        print(f"📬 Friend request received!")
        print(f"   From: {from_pet_name} ({from_device_name})")
        print(f"   Address: {from_ip}:{from_port}")
        print(f"{'='*60}\n")

        # Store in database
        success = self.friends.receive_friend_request(
            from_device_name,
            from_pet_name,
            from_ip,
            from_port
        )

        if success:
            # Notify UI
            if self.on_friend_request_received:
                self.on_friend_request_received({
                    'device_name': from_device_name,
                    'pet_name': from_pet_name,
                    'ip': from_ip,
                    'port': from_port
                })

    def _handle_friend_request_accepted(self, message_data: Dict, sender_ip: str):
        """
        Handle friend request acceptance

        When we receive this, it means someone accepted our friend request.
        We need to add them to our friends list.
        """
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        from_port = message_data.get('from_port', config.WIFI_PORT)

        print(f"\n{'='*60}")
        print(f"✅ Friend request accepted!")
        print(f"   {from_pet_name} ({from_device_name}) accepted your request")
        print(f"{'='*60}\n")

        # Get sender IP (may have changed)
        from_ip = sender_ip

        # Add to friends (if not already)
        if not self.friends.is_friend(from_device_name):
            cursor = self.friends.connection.cursor()
            current_time = time.time()

            cursor.execute('''
                INSERT INTO friends
                (device_name, pet_name, last_ip, last_port, last_seen, friendship_established)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (from_device_name, from_pet_name, from_ip, from_port,
                  current_time, current_time))

            self.friends.connection.commit()
            print(f"✅ {from_pet_name} added to friends!")

            # Notify UI
            if self.on_friend_request_accepted:
                self.on_friend_request_accepted({
                    'device_name': from_device_name,
                    'pet_name': from_pet_name,
                    'ip': from_ip,
                    'port': from_port
                })
        else:
            # Update contact info
            self.friends.update_friend_contact(from_device_name, from_ip, from_port)

    def _handle_chat_message(self, message_data: Dict, sender_ip: str):
        """
        Handle incoming chat message

        Placeholder for Phase 2 (Messaging System)
        """
        from_device_name = message_data.get('from_device_name')

        # Verify sender is a friend
        if not self.friends.is_friend(from_device_name):
            print(f"⚠️  Received message from non-friend: {from_device_name}")
            return

        # Update friend's contact info
        from_port = message_data.get('from_port', config.WIFI_PORT)
        self.friends.update_friend_contact(from_device_name, sender_ip, from_port)

        # Notify UI (Phase 2 implementation)
        if self.on_message_received:
            self.on_message_received(message_data, sender_ip)
        else:
            print(f"📬 Message from {message_data.get('from_pet_name')}: {message_data.get('content')}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def ping_friend(self, device_name: str) -> bool:
        """
        Check if a friend is online/reachable

        Args:
            device_name: Friend's device name

        Returns:
            True if friend is reachable
        """
        friend = self.friends.get_friend(device_name)
        if not friend:
            return False

        if not friend['ip'] or not friend['port']:
            return False

        # Quick reachability check
        is_reachable = self.wifi.is_device_reachable(friend['ip'], friend['port'])

        if is_reachable:
            # Update last seen time
            self.friends.update_friend_contact(
                device_name,
                friend['ip'],
                friend['port']
            )

        return is_reachable

    def register_ui_callbacks(self,
                            on_friend_request: Callable = None,
                            on_request_accepted: Callable = None,
                            on_request_rejected: Callable = None,
                            on_message: Callable = None):
        """
        Register callbacks for UI notifications

        Args:
            on_friend_request: Called when friend request received
            on_request_accepted: Called when friend request accepted
            on_request_rejected: Called when friend request rejected
            on_message: Called when message received
        """
        if on_friend_request:
            self.on_friend_request_received = on_friend_request
        if on_request_accepted:
            self.on_friend_request_accepted = on_request_accepted
        if on_request_rejected:
            self.on_friend_request_rejected = on_request_rejected
        if on_message:
            self.on_message_received = on_message
