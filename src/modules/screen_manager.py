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

        # Care menu state
        self.care_menu_index = 0

        # Friends/social screen state
        self.friends_list_index = 0
        self.find_friends_index = 0
        self.friend_requests_index = 0
        self.discovered_devices = []  # Cached discovered devices
        self.friends_list = []  # Cached friends list
        self.pending_requests = []  # Cached friend requests

        # Message compose state
        self.selected_friend = None  # Device ID of friend to message
        self.selected_friend_name = None  # Display name of friend
        self.message_type_index = 0
        self.emoji_index = 0
        self.preset_index = 0
        self.compose_buffer = ""  # For custom text compose
        self.compose_char_index = 0

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
        elif screen_state == config.ScreenState.CARE_MENU:
            self.care_menu_index = 0
        elif screen_state == config.ScreenState.FRIENDS_LIST:
            self.friends_list_index = 0
        elif screen_state == config.ScreenState.FIND_FRIENDS:
            self.find_friends_index = 0
        elif screen_state == config.ScreenState.FRIEND_REQUESTS:
            self.friend_requests_index = 0
        elif screen_state == config.ScreenState.MESSAGE_TYPE_MENU:
            self.message_type_index = 0
        elif screen_state == config.ScreenState.EMOJI_SELECT:
            self.emoji_index = 0
        elif screen_state == config.ScreenState.PRESET_SELECT:
            self.preset_index = 0
        elif screen_state == config.ScreenState.TEXT_COMPOSE:
            self.compose_buffer = ""
            self.compose_char_index = 0

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
        elif self.current_screen == config.ScreenState.CARE_MENU:
            return self._handle_care_menu_input(event)
        elif self.current_screen == config.ScreenState.FRIENDS_LIST:
            return self._handle_friends_list_input(event)
        elif self.current_screen == config.ScreenState.FIND_FRIENDS:
            return self._handle_find_friends_input(event)
        elif self.current_screen == config.ScreenState.FRIEND_REQUESTS:
            return self._handle_friend_requests_input(event)
        elif self.current_screen == config.ScreenState.MESSAGE_TYPE_MENU:
            return self._handle_message_type_menu_input(event)
        elif self.current_screen == config.ScreenState.EMOJI_SELECT:
            return self._handle_emoji_select_input(event)
        elif self.current_screen == config.ScreenState.PRESET_SELECT:
            return self._handle_preset_select_input(event)
        elif self.current_screen == config.ScreenState.TEXT_COMPOSE:
            return self._handle_text_compose_input(event)

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
                    current_screen = self.current_screen
                    self.confirmation_callback()
                    self.confirmation_callback = None
                    # Only go home if callback didn't change the screen
                    if self.current_screen == current_screen:
                        self.go_home()
                else:
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

    def _handle_care_menu_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on care menu screen"""
        menu_items = config.CARE_MENU

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.care_menu_index = (self.care_menu_index + 1) % len(menu_items)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.care_menu_index = (self.care_menu_index - 1) % len(menu_items)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            selected_item = menu_items[self.care_menu_index]
            action = selected_item['action']

            if action == 'back':
                self.set_screen(config.ScreenState.MENU)
            else:
                return action  # feed, play, clean, sleep

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.MENU)

        return None

    def _handle_friends_list_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on friends list screen"""
        # Items: friends + "Find Friends" + "Back"
        total_items = len(self.friends_list) + 2  # +2 for Find Friends and Back

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.friends_list_index = (self.friends_list_index + 1) % total_items

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.friends_list_index = (self.friends_list_index - 1) % total_items

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            if self.friends_list_index == len(self.friends_list):
                # "Find Friends" selected
                self.set_screen(config.ScreenState.FIND_FRIENDS)
            elif self.friends_list_index == len(self.friends_list) + 1:
                # "Back" selected
                self.set_screen(config.ScreenState.MENU)
            else:
                # Friend selected - open message menu
                friend = self.friends_list[self.friends_list_index]
                self.selected_friend = friend.get('device_id')
                self.selected_friend_name = friend.get('pet_name', 'Friend')
                self.set_screen(config.ScreenState.MESSAGE_TYPE_MENU)

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.MENU)

        return None

    def _handle_find_friends_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on find friends screen"""
        # Items: devices + "Back"
        total_items = len(self.discovered_devices) + 1  # +1 for Back

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.find_friends_index = (self.find_friends_index + 1) % total_items

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.find_friends_index = (self.find_friends_index - 1) % total_items

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            if self.find_friends_index >= len(self.discovered_devices):
                # "Back" selected
                self.set_screen(config.ScreenState.FRIENDS_LIST)
            else:
                # Send friend request to selected device
                device = self.discovered_devices[self.find_friends_index]
                return ("send_friend_request", device)

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.FRIENDS_LIST)

        return None

    def _handle_friend_requests_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on friend requests screen"""
        # Items: requests + "Back"
        total_items = len(self.pending_requests) + 1  # +1 for Back

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.friend_requests_index = (self.friend_requests_index + 1) % total_items

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.friend_requests_index = (self.friend_requests_index - 1) % total_items

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            if self.friend_requests_index >= len(self.pending_requests):
                # "Back" selected
                self.set_screen(config.ScreenState.MENU)
            else:
                # Accept/show options for selected request
                request = self.pending_requests[self.friend_requests_index]
                return ("handle_friend_request", request)

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.MENU)

        return None

    def _handle_message_type_menu_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on message type selection"""
        menu_items = config.MESSAGE_TYPE_MENU

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.message_type_index = (self.message_type_index + 1) % len(menu_items)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.message_type_index = (self.message_type_index - 1) % len(menu_items)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            selected_item = menu_items[self.message_type_index]
            action = selected_item['action']

            if action == 'back':
                self.set_screen(config.ScreenState.FRIENDS_LIST)
            elif action == 'msg_emoji':
                self.set_screen(config.ScreenState.EMOJI_SELECT)
            elif action == 'msg_preset':
                self.set_screen(config.ScreenState.PRESET_SELECT)
            elif action == 'msg_custom':
                self.set_screen(config.ScreenState.TEXT_COMPOSE)

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.FRIENDS_LIST)

        return None

    def _handle_emoji_select_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on emoji selection screen"""
        emojis = config.EMOJI_LIST

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.emoji_index = (self.emoji_index + 1) % len(emojis)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.emoji_index = (self.emoji_index - 1) % len(emojis)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Send emoji message
            selected_emoji = emojis[self.emoji_index]
            return ("send_message", {
                "type": "emoji",
                "content": selected_emoji,
                "to_device": self.selected_friend,
                "to_name": self.selected_friend_name
            })

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.MESSAGE_TYPE_MENU)

        return None

    def _handle_preset_select_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on preset message selection screen"""
        presets = config.MESSAGE_PRESETS

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.preset_index = (self.preset_index + 1) % len(presets)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.preset_index = (self.preset_index - 1) % len(presets)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Send preset message
            selected_preset = presets[self.preset_index]
            return ("send_message", {
                "type": "preset",
                "content": selected_preset,
                "to_device": self.selected_friend,
                "to_name": self.selected_friend_name
            })

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            self.set_screen(config.ScreenState.MESSAGE_TYPE_MENU)

        return None

    def _handle_text_compose_input(self, event: InputEvent) -> Optional[str]:
        """Handle input on custom text compose screen"""
        char_pool = config.TEXT_ENTRY_CHARS

        if event.type == InputEvent.TYPE_ROTATE_CW:
            self.compose_char_index = (self.compose_char_index + 1) % len(char_pool)

        elif event.type == InputEvent.TYPE_ROTATE_CCW:
            self.compose_char_index = (self.compose_char_index - 1) % len(char_pool)

        elif event.type == InputEvent.TYPE_BUTTON_PRESS:
            # Add character to buffer
            if len(self.compose_buffer) < config.MESSAGE_MAX_LENGTH:
                selected_char = char_pool[self.compose_char_index]
                self.compose_buffer += selected_char
                print(f"Compose: '{self.compose_buffer}'")

        elif event.type == InputEvent.TYPE_BUTTON_LONG_PRESS:
            if len(self.compose_buffer) > 0:
                # Send message
                return ("send_message", {
                    "type": "custom",
                    "content": self.compose_buffer.strip(),
                    "to_device": self.selected_friend,
                    "to_name": self.selected_friend_name
                })
            else:
                # Go back if empty
                self.set_screen(config.ScreenState.MESSAGE_TYPE_MENU)

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

    def is_care_menu(self) -> bool:
        """Check if on care menu screen"""
        return self.current_screen == config.ScreenState.CARE_MENU

    def is_friends_list(self) -> bool:
        """Check if on friends list screen"""
        return self.current_screen == config.ScreenState.FRIENDS_LIST

    def is_find_friends(self) -> bool:
        """Check if on find friends screen"""
        return self.current_screen == config.ScreenState.FIND_FRIENDS

    def is_friend_requests(self) -> bool:
        """Check if on friend requests screen"""
        return self.current_screen == config.ScreenState.FRIEND_REQUESTS

    def is_message_type_menu(self) -> bool:
        """Check if on message type menu screen"""
        return self.current_screen == config.ScreenState.MESSAGE_TYPE_MENU

    def is_emoji_select(self) -> bool:
        """Check if on emoji select screen"""
        return self.current_screen == config.ScreenState.EMOJI_SELECT

    def is_preset_select(self) -> bool:
        """Check if on preset select screen"""
        return self.current_screen == config.ScreenState.PRESET_SELECT

    def is_text_compose(self) -> bool:
        """Check if on text compose screen"""
        return self.current_screen == config.ScreenState.TEXT_COMPOSE

    def get_care_menu_state(self) -> Dict[str, Any]:
        """Get current care menu state for rendering"""
        return {
            'items': config.CARE_MENU,
            'selected_index': self.care_menu_index
        }

    def get_friends_list_state(self) -> Dict[str, Any]:
        """Get current friends list state for rendering"""
        return {
            'friends': self.friends_list,
            'selected_index': self.friends_list_index
        }

    def get_find_friends_state(self) -> Dict[str, Any]:
        """Get current find friends state for rendering"""
        return {
            'devices': self.discovered_devices,
            'selected_index': self.find_friends_index
        }

    def get_friend_requests_state(self) -> Dict[str, Any]:
        """Get current friend requests state for rendering"""
        return {
            'requests': self.pending_requests,
            'selected_index': self.friend_requests_index
        }

    def get_message_type_menu_state(self) -> Dict[str, Any]:
        """Get current message type menu state for rendering"""
        return {
            'items': config.MESSAGE_TYPE_MENU,
            'selected_index': self.message_type_index,
            'friend_name': self.selected_friend_name
        }

    def get_emoji_select_state(self) -> Dict[str, Any]:
        """Get current emoji select state for rendering"""
        return {
            'emojis': config.EMOJI_LIST,
            'selected_index': self.emoji_index,
            'friend_name': self.selected_friend_name
        }

    def get_preset_select_state(self) -> Dict[str, Any]:
        """Get current preset select state for rendering"""
        return {
            'presets': config.MESSAGE_PRESETS,
            'selected_index': self.preset_index,
            'friend_name': self.selected_friend_name
        }

    def get_text_compose_state(self) -> Dict[str, Any]:
        """Get current text compose state for rendering"""
        return {
            'current_text': self.compose_buffer,
            'char_pool': config.TEXT_ENTRY_CHARS,
            'selected_char_index': self.compose_char_index,
            'friend_name': self.selected_friend_name
        }

    def set_friends_list(self, friends: list):
        """Update the cached friends list"""
        self.friends_list = friends

    def set_discovered_devices(self, devices: list):
        """Update the cached discovered devices"""
        self.discovered_devices = devices

    def set_pending_requests(self, requests: list):
        """Update the cached pending requests"""
        self.pending_requests = requests
