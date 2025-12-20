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
from typing import Optional, Callable, Dict, Any, List
from . import config
from .wifi_manager import WiFiManager
from .friend_manager import FriendManager
from .message_handlers import (
    MessageHandlerRegistry,
    MessageHandlerContext,
    create_default_registry
)


class SocialCoordinator:
    """
    Coordinates WiFi and friend management for social features

    This is the main interface for social features in NotaGotchi.
    """

    def __init__(self, wifi_manager: WiFiManager, friend_manager: FriendManager,
                 own_pet_name: str, message_manager=None,
                 message_registry: MessageHandlerRegistry = None):
        """
        Initialize Social Coordinator

        Args:
            wifi_manager: WiFiManager instance
            friend_manager: FriendManager instance
            own_pet_name: This pet's name
            message_manager: MessageManager instance (optional)
            message_registry: MessageHandlerRegistry for routing messages (optional)
        """
        self.wifi = wifi_manager
        self.friends = friend_manager
        self.own_pet_name = own_pet_name
        self.messages = message_manager  # Optional MessageManager

        # Message handler registry (uses Strategy pattern)
        self._message_registry = message_registry or create_default_registry()

        # Callbacks for UI notifications
        self.on_friend_request_received: Optional[Callable] = None
        self.on_friend_request_accepted: Optional[Callable] = None
        self.on_friend_request_rejected: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None

        # Register WiFi callback
        self.wifi.register_callback(self._handle_incoming_message)

    @property
    def message_registry(self) -> MessageHandlerRegistry:
        """Get the message handler registry for registering custom handlers."""
        return self._message_registry

    def register_message_handler(self, handler) -> None:
        """
        Register a custom message handler.

        This enables extensibility - new message types can be handled
        by registering a handler without modifying SocialCoordinator.

        Args:
            handler: A MessageHandler instance
        """
        self._message_registry.register(handler)

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
            List of discovered devices (not filtered by friendship, excludes self)
        """
        all_devices = self.wifi.discover_devices()

        # Filter out ourselves
        return [d for d in all_devices if d['name'] != self.wifi.device_name]

    def discover_new_devices(self) -> list:
        """
        Discover devices that aren't already friends

        Useful for "Find Friends" screen

        Returns:
            List of discovered devices that aren't friends yet (excludes self)
        """
        all_devices = self.wifi.discover_devices()

        # Filter out ourselves and devices that are already friends
        new_devices = []
        for device in all_devices:
            if device['name'] != self.wifi.device_name and not self.friends.is_friend(device['name']):
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

    def _create_handler_context(self) -> MessageHandlerContext:
        """
        Create a MessageHandlerContext for passing to handlers.

        Returns:
            Configured MessageHandlerContext
        """
        return MessageHandlerContext(
            friend_manager=self.friends,
            message_manager=self.messages,
            wifi_manager=self.wifi,
            own_pet_name=self.own_pet_name,
            on_friend_request_received=self.on_friend_request_received,
            on_friend_request_accepted=self.on_friend_request_accepted,
            on_friend_request_rejected=self.on_friend_request_rejected,
            on_message_received=self.on_message_received
        )

    def _handle_incoming_message(self, message_data: Dict, sender_ip: str):
        """
        Handle incoming WiFi messages using the Strategy pattern.

        This is registered as a callback with WiFi Manager.
        Routes messages to the appropriate handler via the registry.

        Args:
            message_data: Parsed message dict
            sender_ip: IP address of sender
        """
        context = self._create_handler_context()
        self._message_registry.handle_message(message_data, sender_ip, context)

    # ========================================================================
    # MESSAGING (if MessageManager available)
    # ========================================================================

    def send_message(self, to_device_name: str, content: str,
                    content_type: str = "text") -> Optional[str]:
        """
        Send a message to a friend

        Args:
            to_device_name: Friend's device name
            content: Message content
            content_type: Type (text, emoji, preset)

        Returns:
            Message ID if queued, None if error
        """
        if not self.messages:
            print("❌ MessageManager not initialized")
            return None

        return self.messages.send_message(to_device_name, content, content_type)

    def get_conversation(self, friend_device_name: str, limit: int = 50) -> List[Dict]:
        """Get conversation history with a friend"""
        if not self.messages:
            return []
        return self.messages.get_conversation_history(friend_device_name, limit)

    def get_inbox(self, limit: int = 100) -> List[Dict]:
        """Get inbox (all received messages)"""
        if not self.messages:
            return []
        return self.messages.get_inbox(limit)

    def get_unread_count(self, friend_device_name: str = None) -> int:
        """Get unread message count"""
        if not self.messages:
            return 0
        return self.messages.get_unread_count(friend_device_name)

    def mark_messages_read(self, message_id: str = None, friend_device_name: str = None):
        """Mark messages as read"""
        if self.messages:
            self.messages.mark_as_read(message_id, friend_device_name)

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
