"""
Not-A-Gotchi Games Module

Provides multiplayer game functionality for NotAGotchi devices.
Games communicate over WiFi using the existing message infrastructure.
"""

from .game_base import GameBase, GameStatus, GameResult
from .game_protocol import GameProtocol, register_game_handlers
from .game_manager import GameManager, GameSession
from .implementations import RockPaperScissors

__all__ = [
    'GameBase',
    'GameStatus',
    'GameResult',
    'GameProtocol',
    'register_game_handlers',
    'GameManager',
    'GameSession',
    'RockPaperScissors',
]
