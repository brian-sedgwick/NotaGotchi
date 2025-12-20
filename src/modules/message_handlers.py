"""
Not-A-Gotchi Message Handler Strategy Pattern

Implements the Strategy pattern for handling different WiFi message types.
New message types can be added by creating a handler and registering it.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
import time
from . import config


class MessageHandler(ABC):
    """
    Abstract base class for message handlers (Strategy pattern).

    Each handler is responsible for one type of message.
    """

    @property
    @abstractmethod
    def message_type(self) -> str:
        """
        The message type this handler processes.

        Returns:
            String identifying the message type (e.g., 'friend_request')
        """
        pass

    @abstractmethod
    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: 'MessageHandlerContext') -> bool:
        """
        Handle the incoming message.

        Args:
            message_data: The parsed message dictionary
            sender_ip: IP address of the sender
            context: Context object providing access to managers

        Returns:
            True if message was handled successfully
        """
        pass


class MessageHandlerContext:
    """
    Context object passed to message handlers.

    Provides access to required managers and callbacks without
    tight coupling to the SocialCoordinator.
    """

    def __init__(
        self,
        friend_manager,
        message_manager,
        wifi_manager,
        own_pet_name: str,
        on_friend_request_received: Optional[Callable] = None,
        on_friend_request_accepted: Optional[Callable] = None,
        on_friend_request_rejected: Optional[Callable] = None,
        on_message_received: Optional[Callable] = None
    ):
        self.friends = friend_manager
        self.messages = message_manager
        self.wifi = wifi_manager
        self.own_pet_name = own_pet_name

        # UI callbacks
        self.on_friend_request_received = on_friend_request_received
        self.on_friend_request_accepted = on_friend_request_accepted
        self.on_friend_request_rejected = on_friend_request_rejected
        self.on_message_received = on_message_received


class MessageHandlerRegistry:
    """
    Registry for message handlers (Strategy pattern).

    Allows dynamic registration of handlers for different message types.
    """

    def __init__(self):
        self._handlers: Dict[str, MessageHandler] = {}

    def register(self, handler: MessageHandler) -> None:
        """
        Register a message handler.

        Args:
            handler: The handler to register
        """
        self._handlers[handler.message_type] = handler
        print(f"Registered handler for message type: {handler.message_type}")

    def unregister(self, message_type: str) -> bool:
        """
        Unregister a handler.

        Args:
            message_type: The message type to unregister

        Returns:
            True if handler was found and removed
        """
        if message_type in self._handlers:
            del self._handlers[message_type]
            return True
        return False

    def get_handler(self, message_type: str) -> Optional[MessageHandler]:
        """
        Get the handler for a message type.

        Args:
            message_type: The message type

        Returns:
            The handler, or None if not found
        """
        return self._handlers.get(message_type)

    def handle_message(self, message_data: Dict[str, Any], sender_ip: str,
                       context: MessageHandlerContext) -> bool:
        """
        Route a message to the appropriate handler.

        Args:
            message_data: The parsed message dictionary
            sender_ip: IP address of the sender
            context: Context object for handlers

        Returns:
            True if message was handled, False if no handler found
        """
        message_type = message_data.get('type')
        if not message_type:
            print("⚠️  Message missing 'type' field")
            return False

        handler = self.get_handler(message_type)
        if handler:
            return handler.handle(message_data, sender_ip, context)
        else:
            print(f"⚠️  Unknown message type: {message_type}")
            return False

    @property
    def registered_types(self) -> List[str]:
        """Get list of registered message types."""
        return list(self._handlers.keys())


# =============================================================================
# CONCRETE HANDLERS
# =============================================================================

class FriendRequestHandler(MessageHandler):
    """Handler for incoming friend requests."""

    @property
    def message_type(self) -> str:
        return 'friend_request'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        from_ip = message_data.get('from_ip', sender_ip)
        from_port = message_data.get('from_port', config.WIFI_PORT)

        print(f"\n{'='*60}")
        print(f"📬 Friend request received!")
        print(f"   From: {from_pet_name} ({from_device_name})")
        print(f"   Address: {from_ip}:{from_port}")
        print(f"{'='*60}\n")

        # Store in database
        success = context.friends.receive_friend_request(
            from_device_name,
            from_pet_name,
            from_ip,
            from_port
        )

        if success and context.on_friend_request_received:
            context.on_friend_request_received({
                'device_name': from_device_name,
                'pet_name': from_pet_name,
                'ip': from_ip,
                'port': from_port
            })

        return success


class FriendRequestAcceptedHandler(MessageHandler):
    """Handler for friend request acceptance messages."""

    @property
    def message_type(self) -> str:
        return 'friend_request_accepted'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        from_ip = message_data.get('from_ip', sender_ip)
        from_port = message_data.get('from_port', config.WIFI_PORT)

        print(f"\n{'='*60}")
        print(f"🎉 Friend request accepted!")
        print(f"   {from_pet_name} is now your friend!")
        print(f"{'='*60}\n")

        # Add to friends list (they accepted our request)
        success = context.friends.add_friend(
            from_device_name,
            from_pet_name,
            from_ip,
            from_port
        )

        if success and context.on_friend_request_accepted:
            context.on_friend_request_accepted({
                'device_name': from_device_name,
                'pet_name': from_pet_name,
                'ip': from_ip,
                'port': from_port
            })

        return success


class ChatMessageHandler(MessageHandler):
    """Handler for incoming chat messages."""

    @property
    def message_type(self) -> str:
        return 'message'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        content = message_data.get('content')
        content_type = message_data.get('content_type', 'text')
        message_id = message_data.get('message_id')
        timestamp = message_data.get('timestamp', time.time())

        # Verify sender is a friend
        if not context.friends.is_friend(from_device_name):
            print(f"⚠️  Ignoring message from non-friend: {from_device_name}")
            return False

        print(f"\n📬 Message from {from_pet_name}: {content}")

        # Store message if message manager available
        if context.messages:
            success = context.messages.receive_message(
                from_device_name=from_device_name,
                from_pet_name=from_pet_name,
                message_id=message_id,
                content=content,
                content_type=content_type,
                timestamp=timestamp
            )

            if not success:
                print(f"❌ Failed to store message from {from_pet_name}")
                return False

        # Update friend's last_seen timestamp
        friends_list = context.friends.get_friends()
        friend = next((f for f in friends_list if f['device_name'] == from_device_name), None)

        if friend:
            # Update last contact info (IP/port/last_seen)
            context.friends.update_friend_contact(
                from_device_name,
                sender_ip,
                friend['port']
            )
            print(f"✅ Updated online status for {from_pet_name}")
        else:
            print(f"⚠️  Could not find friend record for {from_device_name}")

        # Notify UI
        if context.on_message_received:
            context.on_message_received({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'content': content,
                'content_type': content_type,
                'message_id': message_id
            })

        return True


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_default_registry() -> MessageHandlerRegistry:
    """
    Create a registry with all default handlers registered.

    Returns:
        MessageHandlerRegistry with standard handlers
    """
    registry = MessageHandlerRegistry()

    # Register all default handlers
    registry.register(FriendRequestHandler())
    registry.register(FriendRequestAcceptedHandler())
    registry.register(ChatMessageHandler())

    return registry
