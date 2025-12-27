"""
Game Base Class

Abstract base class that all game implementations must extend.
Provides common interface for game logic, validation, and state management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import json


class GameStatus(Enum):
    """Game session status"""
    PENDING = "pending"       # Invite sent, waiting for accept
    ACTIVE = "active"         # Game in progress
    COMPLETED = "completed"   # Game finished normally
    FORFEITED = "forfeited"   # One player quit
    EXPIRED = "expired"       # Invite timed out
    CANCELLED = "cancelled"   # Initiator cancelled invite


class GameResult(Enum):
    """Game outcome"""
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"
    ONGOING = "ongoing"


class GameBase(ABC):
    """
    Abstract base class for all game implementations.

    Each game must implement:
    - Game-specific move validation
    - Move application to game state
    - Win/draw condition checking
    - State serialization for network sync
    - Display state for rendering
    """

    def __init__(self, my_role: str, opponent_role: str):
        """
        Initialize game.

        Args:
            my_role: This player's role (e.g., 'X' or 'O' for tic-tac-toe)
            opponent_role: Opponent's role
        """
        self.my_role = my_role
        self.opponent_role = opponent_role
        self.move_history: List[Dict[str, Any]] = []
        self.current_turn = None  # Role of player whose turn it is
        self._winner = None
        self._is_draw = False

    @property
    @abstractmethod
    def game_type(self) -> str:
        """Return the game type identifier (e.g., 'tic_tac_toe')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return human-readable game name."""
        pass

    @abstractmethod
    def initialize_state(self) -> None:
        """Initialize game to starting state."""
        pass

    @abstractmethod
    def validate_move(self, move_data: Dict[str, Any], player_role: str) -> Tuple[bool, str]:
        """
        Validate a proposed move.

        Args:
            move_data: Game-specific move data
            player_role: Role of player making the move

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def apply_move(self, move_data: Dict[str, Any], player_role: str) -> bool:
        """
        Apply a validated move to game state.

        Args:
            move_data: Game-specific move data
            player_role: Role of player making the move

        Returns:
            True if move was applied successfully
        """
        pass

    @abstractmethod
    def check_game_over(self) -> Tuple[bool, Optional[str], bool]:
        """
        Check if game has ended.

        Returns:
            Tuple of (is_game_over, winner_role_or_none, is_draw)
        """
        pass

    @abstractmethod
    def get_display_state(self) -> Dict[str, Any]:
        """
        Get state needed for rendering the game screen.

        Returns:
            Dict with game-specific display data
        """
        pass

    @abstractmethod
    def serialize(self) -> str:
        """
        Serialize game state to JSON string for storage/sync.

        Returns:
            JSON string of game state
        """
        pass

    @abstractmethod
    def deserialize(self, state_json: str) -> None:
        """
        Restore game state from JSON string.

        Args:
            state_json: JSON string from serialize()
        """
        pass

    # Common methods (can be overridden if needed)

    def is_my_turn(self) -> bool:
        """Check if it's this player's turn."""
        return self.current_turn == self.my_role

    def get_result(self) -> GameResult:
        """Get the current game result from this player's perspective."""
        if self._winner is None and not self._is_draw:
            return GameResult.ONGOING
        elif self._is_draw:
            return GameResult.DRAW
        elif self._winner == self.my_role:
            return GameResult.WIN
        else:
            return GameResult.LOSE

    def record_move(self, move_data: Dict[str, Any], player_role: str) -> None:
        """Record a move in history."""
        self.move_history.append({
            'move_number': len(self.move_history) + 1,
            'player': player_role,
            'data': move_data
        })

    def get_move_count(self) -> int:
        """Get total number of moves made."""
        return len(self.move_history)

    def switch_turn(self) -> None:
        """Switch to other player's turn."""
        if self.current_turn == self.my_role:
            self.current_turn = self.opponent_role
        else:
            self.current_turn = self.my_role

    def set_first_turn(self, first_player_role: str) -> None:
        """Set which player goes first."""
        self.current_turn = first_player_role

    def get_base_state(self) -> Dict[str, Any]:
        """Get base state common to all games."""
        return {
            'my_role': self.my_role,
            'opponent_role': self.opponent_role,
            'current_turn': self.current_turn,
            'move_history': self.move_history,
            'winner': self._winner,
            'is_draw': self._is_draw
        }

    def restore_base_state(self, state: Dict[str, Any]) -> None:
        """Restore base state common to all games."""
        self.my_role = state.get('my_role', self.my_role)
        self.opponent_role = state.get('opponent_role', self.opponent_role)
        self.current_turn = state.get('current_turn')
        self.move_history = state.get('move_history', [])
        self._winner = state.get('winner')
        self._is_draw = state.get('is_draw', False)
