"""
Rock Paper Scissors Game Implementation

A simple simultaneous-reveal game where both players choose
rock, paper, or scissors, then results are compared.

This is a "blind" game - both players submit moves before either sees
the opponent's choice. The game resolves after both moves are received.
"""

import json
from typing import Dict, Any, Optional, Tuple, List
from ..game_base import GameBase, GameResult


class RockPaperScissors(GameBase):
    """
    Rock Paper Scissors game implementation.

    Unlike turn-based games, RPS has both players submit moves
    simultaneously (or as close as network allows). The game
    waits for both moves before revealing the result.
    """

    # Valid choices
    ROCK = 'rock'
    PAPER = 'paper'
    SCISSORS = 'scissors'
    VALID_CHOICES = [ROCK, PAPER, SCISSORS]

    # Win conditions: key beats value
    BEATS = {
        ROCK: SCISSORS,      # Rock crushes scissors
        PAPER: ROCK,         # Paper covers rock
        SCISSORS: PAPER      # Scissors cut paper
    }

    # Display symbols for each choice
    SYMBOLS = {
        ROCK: '(R)',
        PAPER: '(P)',
        SCISSORS: '(S)'
    }

    def __init__(self, my_role: str, opponent_role: str):
        """Initialize Rock Paper Scissors game."""
        super().__init__(my_role, opponent_role)
        self.my_choice: Optional[str] = None
        self.opponent_choice: Optional[str] = None
        self.round_number = 1
        self.best_of = 1  # Single round by default

    @property
    def game_type(self) -> str:
        return 'rock_paper_scissors'

    @property
    def display_name(self) -> str:
        return 'Rock Paper Scissors'

    def initialize_state(self) -> None:
        """Initialize game to starting state."""
        self.my_choice = None
        self.opponent_choice = None
        self.round_number = 1
        self.move_history = []
        self._winner = None
        self._is_draw = False
        # Both players can move simultaneously
        self.current_turn = 'both'

    def validate_move(self, move_data: Dict[str, Any], player_role: str) -> Tuple[bool, str]:
        """
        Validate a move.

        Args:
            move_data: Must contain 'choice' key with rock/paper/scissors
            player_role: The player making the move

        Returns:
            Tuple of (is_valid, error_message)
        """
        choice = move_data.get('choice')

        if not choice:
            return False, "Move must include 'choice'"

        choice = choice.lower()
        if choice not in self.VALID_CHOICES:
            return False, f"Invalid choice. Must be one of: {self.VALID_CHOICES}"

        # Check if player already made a choice this round
        if player_role == self.my_role and self.my_choice is not None:
            return False, "You already made your choice"
        if player_role == self.opponent_role and self.opponent_choice is not None:
            return False, "Opponent already made their choice"

        return True, ""

    def apply_move(self, move_data: Dict[str, Any], player_role: str) -> bool:
        """
        Apply a validated move.

        Args:
            move_data: Contains 'choice' with the player's selection
            player_role: The player making the move

        Returns:
            True if move was applied
        """
        choice = move_data.get('choice', '').lower()

        if player_role == self.my_role:
            self.my_choice = choice
        else:
            self.opponent_choice = choice

        return True

    def check_game_over(self) -> Tuple[bool, Optional[str], bool]:
        """
        Check if the round/game has ended.

        The round ends when both players have made their choice.

        Returns:
            Tuple of (is_game_over, winner_role_or_none, is_draw)
        """
        # Need both choices to determine result
        if self.my_choice is None or self.opponent_choice is None:
            return False, None, False

        # Determine winner
        if self.my_choice == self.opponent_choice:
            # Draw
            self._is_draw = True
            self._winner = None
            return True, None, True

        elif self.BEATS.get(self.my_choice) == self.opponent_choice:
            # I win
            self._winner = self.my_role
            self._is_draw = False
            return True, self.my_role, False

        else:
            # Opponent wins
            self._winner = self.opponent_role
            self._is_draw = False
            return True, self.opponent_role, False

    def get_display_state(self) -> Dict[str, Any]:
        """
        Get state for rendering.

        Returns:
            Dict with:
            - game_type: 'rock_paper_scissors'
            - my_choice: current choice or None
            - opponent_choice: opponent's choice (only revealed after both chose)
            - waiting_for_opponent: True if waiting for opponent
            - waiting_for_me: True if I haven't chosen yet
            - round_complete: True if round is complete
            - result: 'win', 'lose', 'draw', or None
        """
        round_complete = self.my_choice is not None and self.opponent_choice is not None

        result = None
        if round_complete:
            game_result = self.get_result()
            if game_result == GameResult.WIN:
                result = 'win'
            elif game_result == GameResult.LOSE:
                result = 'lose'
            elif game_result == GameResult.DRAW:
                result = 'draw'

        return {
            'game_type': self.game_type,
            'display_name': self.display_name,
            'my_choice': self.my_choice,
            'opponent_choice': self.opponent_choice if round_complete else None,
            'waiting_for_opponent': self.my_choice is not None and self.opponent_choice is None,
            'waiting_for_me': self.my_choice is None,
            'round_complete': round_complete,
            'result': result,
            'round_number': self.round_number,
            'choices': self.VALID_CHOICES,
            'symbols': self.SYMBOLS
        }

    def serialize(self) -> str:
        """Serialize game state to JSON."""
        state = self.get_base_state()
        state.update({
            'my_choice': self.my_choice,
            'opponent_choice': self.opponent_choice,
            'round_number': self.round_number,
            'best_of': self.best_of
        })
        return json.dumps(state)

    def deserialize(self, state_json: str) -> None:
        """Restore game state from JSON."""
        state = json.loads(state_json)
        self.restore_base_state(state)
        self.my_choice = state.get('my_choice')
        self.opponent_choice = state.get('opponent_choice')
        self.round_number = state.get('round_number', 1)
        self.best_of = state.get('best_of', 1)

    def is_my_turn(self) -> bool:
        """
        In RPS, both players can move simultaneously.
        Returns True if I haven't made my choice yet.
        """
        return self.my_choice is None

    def get_choice_display(self, choice: Optional[str]) -> str:
        """Get display symbol for a choice."""
        if choice is None:
            return '?'
        return self.SYMBOLS.get(choice, choice)
