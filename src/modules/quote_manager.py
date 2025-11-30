"""
Not-A-Gotchi Quote Manager Module

Handles loading and random selection of mood-based quotes for the pet.
"""

import json
import random
import os
from typing import Dict, List, Optional


class QuoteManager:
    """Manages pet quotes loaded from external JSON file"""

    def __init__(self, quotes_file_path: str):
        """
        Initialize the quote manager

        Args:
            quotes_file_path: Path to the quotes JSON file
        """
        self.quotes: Dict[str, List[str]] = {}
        self.quotes_file = quotes_file_path
        self._load_quotes()

    def _load_quotes(self):
        """Load quotes from JSON file"""
        if not os.path.exists(self.quotes_file):
            print(f"Warning: Quotes file not found at {self.quotes_file}")
            print("Pet will not display quotes")
            return

        try:
            with open(self.quotes_file, 'r', encoding='utf-8') as f:
                self.quotes = json.load(f)
            print(f"Loaded quotes for {len(self.quotes)} emotions")
        except json.JSONDecodeError as e:
            print(f"Error parsing quotes JSON: {e}")
            print("Pet will not display quotes")
            self.quotes = {}
        except Exception as e:
            print(f"Error loading quotes file: {e}")
            self.quotes = {}

    def get_random_quote(self, emotion: str) -> Optional[str]:
        """
        Get a random quote for the given emotion

        Args:
            emotion: The pet's current emotion state

        Returns:
            A random quote string, or None if no quotes available
        """
        if emotion not in self.quotes:
            return None

        quote_list = self.quotes[emotion]
        if not quote_list:
            return None

        # Filter out empty strings
        valid_quotes = [q for q in quote_list if q.strip()]
        if not valid_quotes:
            return None

        return random.choice(valid_quotes)

    def reload_quotes(self):
        """Reload quotes from file (useful for updating quotes without restart)"""
        self._load_quotes()
