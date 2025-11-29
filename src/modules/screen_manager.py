"""
Not-A-Gotchi Screen Manager Module

Manages screen states and navigation between different screens.
"""

from typing import Optional, Callable, Any, Dict
from . import config
from .input_handler import InputEvent


class ScreenManager:
    """Manages screen state and navigation"""

    def __init__(self):
        """Initialize screen manager"""
        self.current_screen = config.ScreenState.HOME
        self.previous_screen = None

        # Screen-specific state
        self.menu_index = 0
        self.text_entry_buffer = ""
        self.text_entry_char_index = 0
        self.confirmation_selection = True  # True = Yes, False = No
        self.confirmation_callback = None
        self.confirmation_message = ""

        # Action callbacks
        self.action_callbacks: Dict[str, Callable] = {}

    def set_screen(self, screen_state: str):
        """
        Change to a new screen

        Args:
            screen_state: New screen state
        """
        self.previous_screen = self.current_screen
        self.current_screen = screen_state
        print(f"Screen changed: {self.previous_screen} -> {self.current_screen}")

        # Reset screen-specific state when changing screens
        if screen_state == config.ScreenState.MENU:
            self.menu_index = 0
        elif screen_state == config.ScreenState.NAME_ENTRY:
            self.text_entry_buffer = ""
            self.text_entry_char_index = 0
        elif screen_state == config.ScreenState.CONFIRM:
            self.confirmation_selection = True

    def go_back(self):
        """Return to previous screen"""
        if self.previous_screen:
            self.set_screen(self.previous_screen)
        else:
            self.set_screen(config.ScreenState.HOME)

    def go_home(self):
        """Return to home screen"""
        self.set_screen(config.ScreenState.HOME)

    def register_action(self, action_name: str, callback: Callable):
        """
        Register a callback for an action

        Args:
            action_name: Name of the action (e.g., "feed", "play")
            callback: Function to call when action is triggered
        """
        self.action_callbacks[action_name] = callback

    def trigger_action(self, action_name: str, *args, **kwargs) -> Any:
        """
        Trigger a registered action

        Args:
            action_name: Name of the action
            *args, **kwargs: Arguments to pass to callback

        Returns:
            Return value from callback, or None if not registered
        """
        if action_name in self.action_callbacks:
            return self.action_callbacks[action_name](*args, **kwargs)
        else:
            print(f"Warning: No callback registered for action '{action_name}'")
            return None

    def handle_input(self, event: InputEvent) -> Optional[str]:
        """
        Handle input event based on current screen

        Args:
            event: Input event to handle

        Returns:
            Action name if an action was triggered, None otherwise
        """
        if self.current_screen == config.ScreenState.HOME:
            return self._handle_home_input(event)
        elif self.current_screen == config.ScreenState.MENU:
            return self._handle_menu_input(event)
        elif self.current_screen == config.ScreenState.NAME_ENTRY:
            return self._handle_name_entry_input(event)
        elif self.current_screen == config.ScreenState.CONFIRM:
            return self._handle_confirmation_input(event)

        return None

    def _handle_home_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on home screen"""
        if event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Short press opens menu
            self.set_screen(config.ScreenState.MENU)
        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            # Long press does nothing on home (could add features later)
            pass

        return None

    def _handle_menu_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on menu screen"""
        menu_items = config.MAIN_MENU

        if event.type == InputEvent.TYPE_ROTATE_CW:
            # Scroll down
            self.menu_index = (self.menu_index + 1) % len(menu_items)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            # Scroll up
            self.menu_index = (self.menu_index - 1) % len(menu_items)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Select current menu item
            selected_item = menu_items[self.menu_index]
            action = selected_item['action']

            if action == 'back':
                self.go_home()
            else:
                return action  # Return action to be handled by main loop

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            # Long press goes back
            self.go_home()

        return None

    def _handle_name_entry_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on name entry screen"""
        char_pool = config.TEXT_ENTRY_CHARS

        if event.type == InputEvent.TYPE_ROTATE_CW:
            # Next character
            self.text_entry_char_index = (self.text_entry_char_index + 1) % len(char_pool)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            # Previous character
            self.text_entry_char_index = (self.text_entry_char_index - 1) % len(char_pool)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Add character to buffer
            if len(self.text_entry_buffer) < config.MAX_NAME_LENGTH:
                selected_char = char_pool[self.text_entry_char_index]
                if selected_char == ' ' and len(self.text_entry_buffer) == 0:
                    # Don't allow leading space
                    pass
                else:
                    self.text_entry_buffer += selected_char
                    print(f"Name entry: '{self.text_entry_buffer}'")

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            # Finish entry or go back
            if len(self.text_entry_buffer) >= config.MIN_NAME_LENGTH:
                # Valid name entered
                return "name_entry_complete"
            else:
                # Cancel entry
                self.text_entry_buffer = ""
                self.go_back()

        return None

    def _handle_confirmation_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on confirmation screen"""
        if event.type == InputEvent.TYPE_ROTATE_CW or event.type == InputEvent.TYPE_ROTATE_CCW:
            # Toggle selection
            self.confirmation_selection = not self.confirmation_selection

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Execute selection
            if self.confirmation_selection:
                # Yes selected
                if self.confirmation_callback:
                    self.confirmation_callback()
                    self.confirmation_callback = None
                self.go_home()
                return "confirmation_yes"
            else:
                # No selected
                self.go_home()
                return "confirmation_no"

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            # Cancel (same as No)
            self.go_home()
            return "confirmation_cancel"

        return None

    def show_confirmation(self, message: str, callback: Callable):
        """
        Show confirmation dialog

        Args:
            message: Confirmation message
            callback: Function to call if user selects Yes
        """
        self.confirmation_message = message
        self.confirmation_callback = callback
        self.confirmation_selection = True
        self.set_screen(config.ScreenState.CONFIRM)

    def start_name_entry(self):
        """Start name entry screen"""
        self.text_entry_buffer = ""
        self.text_entry_char_index = 0
        self.set_screen(config.ScreenState.NAME_ENTRY)

    def get_entered_name(self) -> str:
        """Get the name entered in name entry screen"""
        return self.text_entry_buffer.strip()

    def get_menu_state(self) -> Dict[str, Any]:
        """Get current menu state for rendering"""
        return {
            'items': config.MAIN_MENU,
            'selected_index': self.menu_index
        }

    def get_name_entry_state(self) -> Dict[str, Any]:
        """Get current name entry state for rendering"""
        return {
            'current_text': self.text_entry_buffer,
            'char_pool': config.TEXT_ENTRY_CHARS,
            'selected_char_index': self.text_entry_char_index
        }

    def get_confirmation_state(self) -> Dict[str, Any]:
        """Get current confirmation state for rendering"""
        return {
            'message': self.confirmation_message,
            'selected': self.confirmation_selection
        }

    def is_home(self) -> bool:
        """Check if on home screen"""
        return self.current_screen == config.ScreenState.HOME

    def is_menu(self) -> bool:
        """Check if on menu screen"""
        return self.current_screen == config.ScreenState.MENU

    def is_name_entry(self) -> bool:
        """Check if on name entry screen"""
        return self.current_screen == config.ScreenState.NAME_ENTRY

    def is_confirmation(self) -> bool:
        """Check if on confirmation screen"""
        return self.current_screen == config.ScreenState.CONFIRM
