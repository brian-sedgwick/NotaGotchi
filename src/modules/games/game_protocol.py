"""
Game Protocol Message Handlers

Implements message handlers for the game communication protocol.
Uses the Strategy pattern from message_handlers.py.

Message Types:
- game_invite: Player invites another to a game
- game_accept: Player accepts a game invitation
- game_decline: Player declines a game invitation
- game_cancel: Initiator cancels a pending invite
- game_move: Player submits a move
- game_forfeit: Player forfeits the game
- game_sync: Request/respond with current game state
"""

import time
from typing import Dict, Any, Optional, Callable
from ..message_handlers import MessageHandler, MessageHandlerContext, MessageHandlerRegistry
from .. import config


class GameInviteHandler(MessageHandler):
    """Handler for incoming game invitations."""

    @property
    def message_type(self) -> str:
        return 'game_invite'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        game_session_id = message_data.get('game_session_id')
        game_type = message_data.get('game_type')
        expires_at = message_data.get('expires_at')
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n{'='*60}")
        print(f"🎮 Game invite received!")
        print(f"   From: {from_pet_name} ({from_device_name})")
        print(f"   Game: {game_type}")
        print(f"   Session: {game_session_id}")
        print(f"{'='*60}\n")

        # Check if invite has expired
        if expires_at and time.time() > expires_at:
            print(f"⚠️  Game invite has expired")
            return False

        # Verify sender is a friend
        if not context.friends.is_friend(from_device_name):
            print(f"⚠️  Ignoring game invite from non-friend: {from_device_name}")
            return False

        # Notify game manager via callback if available
        game_callback = getattr(context, 'on_game_invite_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'game_session_id': game_session_id,
                'game_type': game_type,
                'expires_at': expires_at,
                'timestamp': timestamp,
                'sender_ip': sender_ip
            })

        return True


class GameAcceptHandler(MessageHandler):
    """Handler for game acceptance messages."""

    @property
    def message_type(self) -> str:
        return 'game_accept'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        game_session_id = message_data.get('game_session_id')
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n{'='*60}")
        print(f"✅ Game accepted!")
        print(f"   {from_pet_name} accepted the game invite!")
        print(f"   Session: {game_session_id}")
        print(f"{'='*60}\n")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_accept_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'game_session_id': game_session_id,
                'timestamp': timestamp,
                'sender_ip': sender_ip
            })

        return True


class GameDeclineHandler(MessageHandler):
    """Handler for game decline messages."""

    @property
    def message_type(self) -> str:
        return 'game_decline'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        game_session_id = message_data.get('game_session_id')
        reason = message_data.get('reason', 'declined')
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n{'='*60}")
        print(f"❌ Game declined")
        print(f"   {from_pet_name} declined the game invite")
        print(f"   Reason: {reason}")
        print(f"{'='*60}\n")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_decline_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'game_session_id': game_session_id,
                'reason': reason,
                'timestamp': timestamp
            })

        return True


class GameCancelHandler(MessageHandler):
    """Handler for game cancellation messages (initiator cancels pending invite)."""

    @property
    def message_type(self) -> str:
        return 'game_cancel'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        game_session_id = message_data.get('game_session_id')
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n🚫 Game invite cancelled by {from_pet_name}")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_cancel_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'game_session_id': game_session_id,
                'timestamp': timestamp
            })

        return True


class GameMoveHandler(MessageHandler):
    """Handler for game move messages."""

    @property
    def message_type(self) -> str:
        return 'game_move'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        game_session_id = message_data.get('game_session_id')
        move_number = message_data.get('move_number')
        move_data = message_data.get('move_data', {})
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n🎯 Game move received")
        print(f"   Session: {game_session_id}")
        print(f"   Move #: {move_number}")
        print(f"   Data: {move_data}")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_move_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'game_session_id': game_session_id,
                'move_number': move_number,
                'move_data': move_data,
                'timestamp': timestamp,
                'sender_ip': sender_ip
            })

        return True


class GameForfeitHandler(MessageHandler):
    """Handler for game forfeit messages."""

    @property
    def message_type(self) -> str:
        return 'game_forfeit'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        game_session_id = message_data.get('game_session_id')
        reason = message_data.get('reason', 'user_quit')
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n{'='*60}")
        print(f"🏳️ Game forfeited")
        print(f"   {from_pet_name} has forfeited the game")
        print(f"   Reason: {reason}")
        print(f"{'='*60}\n")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_forfeit_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'game_session_id': game_session_id,
                'reason': reason,
                'timestamp': timestamp
            })

        return True


class GameSyncHandler(MessageHandler):
    """Handler for game state synchronization messages."""

    @property
    def message_type(self) -> str:
        return 'game_sync'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        game_session_id = message_data.get('game_session_id')
        game_state = message_data.get('game_state')
        is_request = message_data.get('is_request', False)
        timestamp = message_data.get('timestamp', time.time())

        if is_request:
            print(f"\n🔄 Game sync requested for session {game_session_id}")
        else:
            print(f"\n🔄 Game sync received for session {game_session_id}")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_sync_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'game_session_id': game_session_id,
                'game_state': game_state,
                'is_request': is_request,
                'timestamp': timestamp,
                'sender_ip': sender_ip
            })

        return True


class GameRematchHandler(MessageHandler):
    """Handler for rematch proposal messages."""

    @property
    def message_type(self) -> str:
        return 'game_rematch'

    def handle(self, message_data: Dict[str, Any], sender_ip: str,
               context: MessageHandlerContext) -> bool:
        from_device_name = message_data.get('from_device_name')
        from_pet_name = message_data.get('from_pet_name')
        original_session_id = message_data.get('original_session_id')
        new_session_id = message_data.get('new_session_id')
        game_type = message_data.get('game_type')
        timestamp = message_data.get('timestamp', time.time())

        print(f"\n🔁 Rematch proposed by {from_pet_name}")
        print(f"   Game: {game_type}")

        # Notify game manager via callback
        game_callback = getattr(context, 'on_game_rematch_received', None)
        if game_callback:
            game_callback({
                'from_device_name': from_device_name,
                'from_pet_name': from_pet_name,
                'original_session_id': original_session_id,
                'new_session_id': new_session_id,
                'game_type': game_type,
                'timestamp': timestamp,
                'sender_ip': sender_ip
            })

        return True


# =============================================================================
# PROTOCOL HELPER CLASS
# =============================================================================

class GameProtocol:
    """
    Helper class for sending game protocol messages.

    This class provides methods to construct and send properly formatted
    game messages to other devices.
    """

    def __init__(self, wifi_manager, own_device_name: str, own_pet_name: str):
        """
        Initialize GameProtocol.

        Args:
            wifi_manager: WiFiManager instance for sending messages
            own_device_name: This device's name
            own_pet_name: This pet's name
        """
        self.wifi = wifi_manager
        self.device_name = own_device_name
        self.pet_name = own_pet_name

    def generate_session_id(self, opponent_name: str) -> str:
        """
        Generate a unique game session ID.

        Format: game_{timestamp}_{initiator_short}_{opponent_short}
        """
        timestamp = int(time.time())
        my_short = self.pet_name[:8].lower().replace(' ', '_')
        opp_short = opponent_name[:8].lower().replace(' ', '_')
        return f"game_{timestamp}_{my_short}_{opp_short}"

    def send_invite(self, target_ip: str, target_port: int,
                   game_type: str, session_id: str) -> bool:
        """Send a game invitation."""
        message = {
            "type": "game_invite",
            "from_device_name": self.device_name,
            "from_pet_name": self.pet_name,
            "game_session_id": session_id,
            "game_type": game_type,
            "expires_at": time.time() + config.GAME_INVITE_TIMEOUT,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_accept(self, target_ip: str, target_port: int,
                   session_id: str) -> bool:
        """Send game acceptance."""
        message = {
            "type": "game_accept",
            "from_device_name": self.device_name,
            "from_pet_name": self.pet_name,
            "game_session_id": session_id,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_decline(self, target_ip: str, target_port: int,
                    session_id: str, reason: str = "declined") -> bool:
        """Send game decline."""
        message = {
            "type": "game_decline",
            "from_device_name": self.device_name,
            "from_pet_name": self.pet_name,
            "game_session_id": session_id,
            "reason": reason,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_cancel(self, target_ip: str, target_port: int,
                   session_id: str) -> bool:
        """Cancel a pending invite."""
        message = {
            "type": "game_cancel",
            "from_device_name": self.device_name,
            "from_pet_name": self.pet_name,
            "game_session_id": session_id,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_move(self, target_ip: str, target_port: int,
                 session_id: str, move_number: int,
                 move_data: Dict[str, Any]) -> bool:
        """Send a game move."""
        message = {
            "type": "game_move",
            "from_device_name": self.device_name,
            "game_session_id": session_id,
            "move_number": move_number,
            "move_data": move_data,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_forfeit(self, target_ip: str, target_port: int,
                    session_id: str, reason: str = "user_quit") -> bool:
        """Send game forfeit."""
        message = {
            "type": "game_forfeit",
            "from_device_name": self.device_name,
            "from_pet_name": self.pet_name,
            "game_session_id": session_id,
            "reason": reason,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_sync(self, target_ip: str, target_port: int,
                 session_id: str, game_state: Optional[str] = None,
                 is_request: bool = False) -> bool:
        """Send game state sync (request or response)."""
        message = {
            "type": "game_sync",
            "from_device_name": self.device_name,
            "game_session_id": session_id,
            "game_state": game_state,
            "is_request": is_request,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)

    def send_rematch(self, target_ip: str, target_port: int,
                    original_session_id: str, new_session_id: str,
                    game_type: str) -> bool:
        """Propose a rematch."""
        message = {
            "type": "game_rematch",
            "from_device_name": self.device_name,
            "from_pet_name": self.pet_name,
            "original_session_id": original_session_id,
            "new_session_id": new_session_id,
            "game_type": game_type,
            "timestamp": time.time()
        }
        return self.wifi.send_message(target_ip, target_port, message)


# =============================================================================
# REGISTRATION FUNCTION
# =============================================================================

def register_game_handlers(registry: MessageHandlerRegistry) -> None:
    """
    Register all game message handlers with the registry.

    Args:
        registry: MessageHandlerRegistry to register handlers with
    """
    registry.register(GameInviteHandler())
    registry.register(GameAcceptHandler())
    registry.register(GameDeclineHandler())
    registry.register(GameCancelHandler())
    registry.register(GameMoveHandler())
    registry.register(GameForfeitHandler())
    registry.register(GameSyncHandler())
    registry.register(GameRematchHandler())

    print("🎮 Game protocol handlers registered")
