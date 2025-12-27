"""
Game Manager Module

Manages game sessions, state, and lifecycle for NotAGotchi multiplayer games.
Coordinates between GameProtocol (network), GameBase implementations, and UI.
"""

import time
import json
from typing import Dict, Any, Optional, Callable, List, TYPE_CHECKING
from .game_base import GameBase, GameStatus, GameResult
from .game_protocol import GameProtocol, register_game_handlers
from .. import config

if TYPE_CHECKING:
    from ..wifi_manager import WiFiManager
    from ..friend_manager import FriendManager
    from ..persistence import DatabaseManager


class GameSession:
    """
    Represents an active or pending game session.

    Tracks all state for a single game between two players.
    """

    def __init__(
        self,
        session_id: str,
        game_type: str,
        opponent_device: str,
        opponent_pet_name: str,
        is_initiator: bool,
        my_role: str = None,
        opponent_role: str = None
    ):
        self.session_id = session_id
        self.game_type = game_type
        self.opponent_device = opponent_device
        self.opponent_pet_name = opponent_pet_name
        self.is_initiator = is_initiator  # True if we sent the invite

        # Roles (e.g., 'X'/'O' for tic-tac-toe)
        self.my_role = my_role
        self.opponent_role = opponent_role

        # Session state
        self.status = GameStatus.PENDING
        self.game: Optional[GameBase] = None

        # Timing
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.last_move_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.expires_at: Optional[float] = None

        # Network info (for sending messages back)
        self.opponent_ip: Optional[str] = None
        self.opponent_port: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            'session_id': self.session_id,
            'game_type': self.game_type,
            'opponent_device': self.opponent_device,
            'opponent_pet_name': self.opponent_pet_name,
            'is_initiator': self.is_initiator,
            'my_role': self.my_role,
            'opponent_role': self.opponent_role,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'last_move_at': self.last_move_at,
            'completed_at': self.completed_at,
            'expires_at': self.expires_at,
            'game_state': self.game.serialize() if self.game else None
        }


class GameManager:
    """
    Central manager for all game-related functionality.

    Handles:
    - Game session lifecycle (invite, accept, play, complete)
    - Integration with message handlers via callbacks
    - Pending invite queue for interruption handling
    - Game state persistence
    """

    def __init__(
        self,
        wifi_manager: 'WiFiManager',
        friend_manager: 'FriendManager',
        db_manager: 'DatabaseManager',
        own_device_name: str,
        own_pet_name: str,
        message_registry=None
    ):
        """
        Initialize GameManager.

        Args:
            wifi_manager: WiFiManager instance for network communication
            friend_manager: FriendManager for friend lookups
            db_manager: DatabaseManager for persistence
            own_device_name: This device's name
            own_pet_name: This pet's name
            message_registry: MessageHandlerRegistry to register game handlers
        """
        self.wifi = wifi_manager
        self.friends = friend_manager
        self.db = db_manager
        self.device_name = own_device_name
        self.pet_name = own_pet_name

        # Game protocol helper
        self.protocol = GameProtocol(wifi_manager, own_device_name, own_pet_name)

        # Current active session (only one at a time)
        self._active_session: Optional[GameSession] = None

        # Pending invites received while busy
        self._pending_invites: List[Dict[str, Any]] = []

        # Outgoing invite (waiting for response)
        self._pending_outgoing: Optional[GameSession] = None

        # UI callbacks
        self.on_invite_received: Optional[Callable] = None
        self.on_invite_accepted: Optional[Callable] = None
        self.on_invite_declined: Optional[Callable] = None
        self.on_invite_cancelled: Optional[Callable] = None
        self.on_game_started: Optional[Callable] = None
        self.on_opponent_move: Optional[Callable] = None
        self.on_game_ended: Optional[Callable] = None
        self.on_opponent_forfeit: Optional[Callable] = None

        # Game implementations registry
        self._game_classes: Dict[str, type] = {}

        # Register message handlers if registry provided
        if message_registry:
            self._register_handlers(message_registry)

    def _register_handlers(self, registry) -> None:
        """Register game protocol handlers with the message registry."""
        from .game_protocol import register_game_handlers
        register_game_handlers(registry)

        # Store reference to set callbacks on context
        self._message_registry = registry

    def register_game_class(self, game_type: str, game_class: type) -> None:
        """
        Register a game implementation class.

        Args:
            game_type: The game type identifier (e.g., 'tic_tac_toe')
            game_class: The GameBase subclass for this game
        """
        self._game_classes[game_type] = game_class
        print(f"Registered game: {game_type} -> {game_class.__name__}")

    def get_registered_games(self) -> List[str]:
        """Get list of registered game types."""
        return list(self._game_classes.keys())

    # =========================================================================
    # GAME LIFECYCLE - INITIATING
    # =========================================================================

    def send_invite(self, friend_device: str, game_type: str) -> Optional[str]:
        """
        Send a game invitation to a friend.

        Args:
            friend_device: Friend's device name
            game_type: Type of game to play

        Returns:
            Session ID if invite sent, None if failed
        """
        # Check if already in a game
        if self.is_game_active():
            print("❌ Cannot send invite while game is active")
            return None

        # Check if game type is valid
        if game_type not in config.GAME_TYPES:
            print(f"❌ Unknown game type: {game_type}")
            return None

        # Get friend info
        friend = self.friends.get_friend(friend_device)
        if not friend:
            print(f"❌ Friend not found: {friend_device}")
            return None

        if not friend.get('ip') or not friend.get('port'):
            print(f"❌ No connection info for friend: {friend_device}")
            return None

        # Generate session ID
        session_id = self.protocol.generate_session_id(friend.get('pet_name', 'friend'))

        # Create pending outgoing session
        session = GameSession(
            session_id=session_id,
            game_type=game_type,
            opponent_device=friend_device,
            opponent_pet_name=friend.get('pet_name', 'Unknown'),
            is_initiator=True
        )
        session.opponent_ip = friend['ip']
        session.opponent_port = friend['port']
        session.expires_at = time.time() + config.GAME_INVITE_TIMEOUT

        # Send the invite
        success = self.protocol.send_invite(
            friend['ip'],
            friend['port'],
            game_type,
            session_id
        )

        if success:
            self._pending_outgoing = session
            print(f"✅ Game invite sent to {session.opponent_pet_name}")
            return session_id
        else:
            print(f"❌ Failed to send game invite")
            return None

    def cancel_pending_invite(self) -> bool:
        """Cancel an outgoing invite that hasn't been accepted yet."""
        if not self._pending_outgoing:
            return False

        session = self._pending_outgoing

        # Send cancel message
        if session.opponent_ip and session.opponent_port:
            self.protocol.send_cancel(
                session.opponent_ip,
                session.opponent_port,
                session.session_id
            )

        self._pending_outgoing = None
        print("🚫 Pending invite cancelled")
        return True

    # =========================================================================
    # GAME LIFECYCLE - RESPONDING
    # =========================================================================

    def accept_invite(self, session_id: str) -> bool:
        """
        Accept a game invitation.

        Args:
            session_id: The session ID from the invite

        Returns:
            True if accepted and game started
        """
        # Find the invite in pending list
        invite = None
        for i, inv in enumerate(self._pending_invites):
            if inv.get('game_session_id') == session_id:
                invite = self._pending_invites.pop(i)
                break

        if not invite:
            print(f"❌ Invite not found: {session_id}")
            return False

        # Check if expired
        expires_at = invite.get('expires_at')
        if expires_at and time.time() > expires_at:
            print("❌ Invite has expired")
            return False

        # Create session
        session = GameSession(
            session_id=session_id,
            game_type=invite['game_type'],
            opponent_device=invite['from_device_name'],
            opponent_pet_name=invite['from_pet_name'],
            is_initiator=False
        )
        session.opponent_ip = invite.get('sender_ip')

        # Get friend info for port
        friend = self.friends.get_friend(invite['from_device_name'])
        if friend:
            session.opponent_port = friend.get('port', config.WIFI_PORT)
        else:
            session.opponent_port = config.WIFI_PORT

        # Send acceptance
        if session.opponent_ip and session.opponent_port:
            success = self.protocol.send_accept(
                session.opponent_ip,
                session.opponent_port,
                session_id
            )

            if success:
                self._start_game(session)
                return True

        print("❌ Failed to send acceptance")
        return False

    def decline_invite(self, session_id: str, reason: str = "declined") -> bool:
        """
        Decline a game invitation.

        Args:
            session_id: The session ID from the invite
            reason: Reason for declining

        Returns:
            True if decline sent
        """
        # Find and remove the invite
        invite = None
        for i, inv in enumerate(self._pending_invites):
            if inv.get('game_session_id') == session_id:
                invite = self._pending_invites.pop(i)
                break

        if not invite:
            return False

        # Send decline message
        sender_ip = invite.get('sender_ip')
        friend = self.friends.get_friend(invite['from_device_name'])
        port = friend.get('port', config.WIFI_PORT) if friend else config.WIFI_PORT

        if sender_ip:
            self.protocol.send_decline(sender_ip, port, session_id, reason)

        return True

    # =========================================================================
    # GAME LIFECYCLE - GAMEPLAY
    # =========================================================================

    def _start_game(self, session: GameSession) -> None:
        """Initialize and start a game session."""
        game_type = session.game_type

        # Check if we have a game class registered
        if game_type not in self._game_classes:
            print(f"❌ No game implementation for: {game_type}")
            return

        # Determine roles (initiator usually goes first)
        if session.is_initiator:
            session.my_role = 'player1'
            session.opponent_role = 'player2'
        else:
            session.my_role = 'player2'
            session.opponent_role = 'player1'

        # Create game instance
        game_class = self._game_classes[game_type]
        session.game = game_class(session.my_role, session.opponent_role)
        session.game.initialize_state()

        # Set first turn (initiator goes first by default)
        session.game.set_first_turn('player1')

        # Update session state
        session.status = GameStatus.ACTIVE
        session.started_at = time.time()

        # Set as active session
        self._active_session = session
        self._pending_outgoing = None

        print(f"🎮 Game started: {game_type} vs {session.opponent_pet_name}")

        # Notify UI
        if self.on_game_started:
            self.on_game_started(session)

    def make_move(self, move_data: Dict[str, Any]) -> bool:
        """
        Make a move in the active game.

        Args:
            move_data: Game-specific move data

        Returns:
            True if move was valid and applied
        """
        if not self._active_session or not self._active_session.game:
            print("❌ No active game")
            return False

        session = self._active_session
        game = session.game

        # Check if it's our turn
        if not game.is_my_turn():
            print("❌ Not your turn")
            return False

        # Validate move
        is_valid, error = game.validate_move(move_data, game.my_role)
        if not is_valid:
            print(f"❌ Invalid move: {error}")
            return False

        # Apply move
        game.apply_move(move_data, game.my_role)
        game.record_move(move_data, game.my_role)
        session.last_move_at = time.time()

        # Send move to opponent
        move_number = game.get_move_count()
        if session.opponent_ip and session.opponent_port:
            self.protocol.send_move(
                session.opponent_ip,
                session.opponent_port,
                session.session_id,
                move_number,
                move_data
            )

        # Check for game over
        is_over, winner, is_draw = game.check_game_over()
        if is_over:
            self._end_game(session, winner, is_draw)
        else:
            # Switch turn
            game.switch_turn()

        return True

    def _handle_opponent_move(self, data: Dict[str, Any]) -> None:
        """Handle incoming move from opponent."""
        session_id = data.get('game_session_id')
        move_data = data.get('move_data', {})
        move_number = data.get('move_number')

        if not self._active_session:
            print("⚠️ Received move but no active session")
            return

        if self._active_session.session_id != session_id:
            print("⚠️ Move for different session")
            return

        session = self._active_session
        game = session.game

        if not game:
            return

        # Validate and apply opponent's move
        is_valid, error = game.validate_move(move_data, game.opponent_role)
        if not is_valid:
            print(f"⚠️ Invalid opponent move: {error}")
            return

        game.apply_move(move_data, game.opponent_role)
        game.record_move(move_data, game.opponent_role)
        session.last_move_at = time.time()

        # Notify UI
        if self.on_opponent_move:
            self.on_opponent_move(move_data)

        # Check for game over
        is_over, winner, is_draw = game.check_game_over()
        if is_over:
            self._end_game(session, winner, is_draw)
        else:
            # Switch turn (now our turn)
            game.switch_turn()

    def _end_game(self, session: GameSession, winner: Optional[str], is_draw: bool) -> None:
        """End the game and update state."""
        session.status = GameStatus.COMPLETED
        session.completed_at = time.time()

        if session.game:
            session.game._winner = winner
            session.game._is_draw = is_draw

        result = session.game.get_result() if session.game else GameResult.DRAW

        print(f"\n{'='*60}")
        print(f"🏁 Game Over!")
        if is_draw:
            print("   Result: DRAW")
        elif result == GameResult.WIN:
            print("   Result: YOU WIN!")
        else:
            print(f"   Result: {session.opponent_pet_name} wins")
        print(f"{'='*60}\n")

        # Notify UI
        if self.on_game_ended:
            self.on_game_ended(session, result)

    def forfeit(self, reason: str = "user_quit") -> bool:
        """Forfeit the current game."""
        if not self._active_session:
            return False

        session = self._active_session

        # Send forfeit message
        if session.opponent_ip and session.opponent_port:
            self.protocol.send_forfeit(
                session.opponent_ip,
                session.opponent_port,
                session.session_id,
                reason
            )

        # Update session
        session.status = GameStatus.FORFEITED
        session.completed_at = time.time()

        if session.game:
            session.game._winner = session.opponent_role

        # Clear active session
        self._active_session = None

        print("🏳️ You forfeited the game")

        if self.on_game_ended:
            self.on_game_ended(session, GameResult.LOSE)

        return True

    # =========================================================================
    # STATE QUERIES
    # =========================================================================

    def is_game_active(self) -> bool:
        """Check if there's an active game."""
        return self._active_session is not None and \
               self._active_session.status == GameStatus.ACTIVE

    def is_waiting_for_response(self) -> bool:
        """Check if waiting for opponent to accept invite."""
        return self._pending_outgoing is not None

    def get_active_session(self) -> Optional[GameSession]:
        """Get the current active game session."""
        return self._active_session

    def get_pending_outgoing(self) -> Optional[GameSession]:
        """Get pending outgoing invite."""
        return self._pending_outgoing

    def get_pending_invites(self) -> List[Dict[str, Any]]:
        """Get list of pending incoming invites."""
        # Clean up expired invites
        now = time.time()
        self._pending_invites = [
            inv for inv in self._pending_invites
            if inv.get('expires_at', now + 1) > now
        ]
        return self._pending_invites

    def has_pending_invites(self) -> bool:
        """Check if there are pending incoming invites."""
        return len(self.get_pending_invites()) > 0

    # =========================================================================
    # MESSAGE HANDLER CALLBACKS
    # =========================================================================

    def handle_game_invite(self, data: Dict[str, Any]) -> None:
        """Handle incoming game invite."""
        # If we're in a game, queue it
        if self.is_game_active():
            print("🎮 Queuing invite (game in progress)")
            self._pending_invites.append(data)
            return

        # Add to pending list
        self._pending_invites.append(data)

        # Notify UI
        if self.on_invite_received:
            self.on_invite_received(data)

    def handle_game_accept(self, data: Dict[str, Any]) -> None:
        """Handle opponent accepting our invite."""
        session_id = data.get('game_session_id')

        if not self._pending_outgoing:
            print("⚠️ Received accept but no pending invite")
            return

        if self._pending_outgoing.session_id != session_id:
            print("⚠️ Accept for different session")
            return

        session = self._pending_outgoing
        session.opponent_ip = data.get('sender_ip')

        # Update with any IP info from the accept message
        if data.get('sender_ip'):
            session.opponent_ip = data['sender_ip']

        # Start the game
        self._start_game(session)

        # Notify UI
        if self.on_invite_accepted:
            self.on_invite_accepted(session)

    def handle_game_decline(self, data: Dict[str, Any]) -> None:
        """Handle opponent declining our invite."""
        session_id = data.get('game_session_id')

        if self._pending_outgoing and self._pending_outgoing.session_id == session_id:
            print(f"😔 {data.get('from_pet_name')} declined the game invite")
            self._pending_outgoing = None

            if self.on_invite_declined:
                self.on_invite_declined(data)

    def handle_game_cancel(self, data: Dict[str, Any]) -> None:
        """Handle initiator cancelling an invite."""
        session_id = data.get('game_session_id')

        # Remove from pending list
        self._pending_invites = [
            inv for inv in self._pending_invites
            if inv.get('game_session_id') != session_id
        ]

        if self.on_invite_cancelled:
            self.on_invite_cancelled(data)

    def handle_game_forfeit(self, data: Dict[str, Any]) -> None:
        """Handle opponent forfeiting."""
        session_id = data.get('game_session_id')

        if not self._active_session:
            return

        if self._active_session.session_id != session_id:
            return

        session = self._active_session
        session.status = GameStatus.FORFEITED
        session.completed_at = time.time()

        if session.game:
            session.game._winner = session.game.my_role

        print(f"🏳️ {data.get('from_pet_name')} forfeited the game!")

        if self.on_opponent_forfeit:
            self.on_opponent_forfeit(data)

        if self.on_game_ended:
            self.on_game_ended(session, GameResult.WIN)

        self._active_session = None

    def handle_game_sync(self, data: Dict[str, Any]) -> None:
        """Handle game state sync request/response."""
        # TODO: Implement sync for reconnection scenarios
        pass

    # =========================================================================
    # INTEGRATION WITH MESSAGE HANDLER CONTEXT
    # =========================================================================

    def setup_context_callbacks(self, context) -> None:
        """
        Set up callbacks on a MessageHandlerContext for game events.

        Call this method to connect the game manager to incoming messages.
        """
        context.on_game_invite_received = self.handle_game_invite
        context.on_game_accept_received = self.handle_game_accept
        context.on_game_decline_received = self.handle_game_decline
        context.on_game_cancel_received = self.handle_game_cancel
        context.on_game_move_received = self._handle_opponent_move
        context.on_game_forfeit_received = self.handle_game_forfeit
        context.on_game_sync_received = self.handle_game_sync
