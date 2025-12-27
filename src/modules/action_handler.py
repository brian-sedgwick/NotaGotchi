"""
Not-A-Gotchi Action Handler Module

Handles all user-triggered actions (care actions, navigation, etc.)
Extracted from main.py to reduce god object size and improve testability.
"""

from typing import Callable, Optional, Any
from . import config


class ActionHandler:
    """
    Handles user-triggered actions for the NotaGotchi game.

    This class is responsible for:
    - Care actions (feed, play, clean, sleep)
    - Navigation actions (care menu, friends, requests, inbox)
    - Pet management (reset, name entry completion)
    - Social actions (send message, friend requests)

    Dependencies are injected for testability.
    """

    def __init__(
        self,
        get_pet: Callable[[], Any],
        get_db: Callable[[], Any],
        get_screen_manager: Callable[[], Any],
        get_social_coordinator: Callable[[], Optional[Any]],
        get_message_manager: Callable[[], Optional[Any]],
        save_pet: Callable[[], None],
        set_action_occurred: Callable[[bool], None],
        create_new_pet: Callable[[str], None],
        get_wifi_manager: Callable[[], Optional[Any]] = None,
        get_display: Callable[[], Optional[Any]] = None
    ):
        """
        Initialize ActionHandler with dependency getters.

        Using getters (callables) instead of direct references allows
        for lazy evaluation and avoids circular dependency issues.

        Args:
            get_pet: Returns current Pet instance
            get_db: Returns DatabaseManager instance
            get_screen_manager: Returns ScreenManager instance
            get_social_coordinator: Returns SocialCoordinator (may be None)
            get_message_manager: Returns MessageManager (may be None)
            save_pet: Callback to save pet state
            set_action_occurred: Callback to set action_occurred flag
            create_new_pet: Callback to create a new pet with given name
            get_wifi_manager: Returns WiFiManager (may be None)
            get_display: Returns DisplayManager (may be None)
        """
        self._get_pet = get_pet
        self._get_db = get_db
        self._get_screen_manager = get_screen_manager
        self._get_social_coordinator = get_social_coordinator
        self._get_message_manager = get_message_manager
        self._save_pet = save_pet
        self._set_action_occurred = set_action_occurred
        self._create_new_pet = create_new_pet
        self._get_wifi_manager = get_wifi_manager or (lambda: None)
        self._get_display = get_display or (lambda: None)

    # =========================================================================
    # Care Actions
    # =========================================================================

    def action_feed(self) -> bool:
        """
        Handle feed action.

        Returns:
            True if action was performed, False otherwise
        """
        pet = self._get_pet()
        if pet is None:
            return False

        changes = pet.feed()
        if not changes:  # Pet is dead
            return False

        self._get_db().log_event(pet.id, "feed", stat_changes=changes)
        self._save_pet()
        self._set_action_occurred(True)
        self._get_screen_manager().go_home()
        print(f"Fed {pet.name}")
        return True

    def action_play(self) -> bool:
        """
        Handle play action.

        Returns:
            True if action was performed, False otherwise
        """
        pet = self._get_pet()
        if pet is None:
            return False

        changes = pet.play()
        if not changes:  # Pet is dead
            return False

        self._get_db().log_event(pet.id, "play", stat_changes=changes)
        self._save_pet()
        self._set_action_occurred(True)
        self._get_screen_manager().go_home()
        print(f"Played with {pet.name}")
        return True

    def action_clean(self) -> bool:
        """
        Handle clean action.

        Returns:
            True if action was performed, False otherwise
        """
        pet = self._get_pet()
        if pet is None:
            return False

        changes = pet.clean()
        if not changes:  # Pet is dead
            return False

        self._get_db().log_event(pet.id, "clean", stat_changes=changes)
        self._save_pet()
        self._set_action_occurred(True)
        self._get_screen_manager().go_home()
        print(f"Cleaned {pet.name}")
        return True

    def action_sleep(self) -> bool:
        """
        Handle sleep action.

        Returns:
            True if action was performed, False otherwise
        """
        pet = self._get_pet()
        if pet is None:
            return False

        changes = pet.sleep()
        if not changes:  # Pet is dead
            return False

        self._get_db().log_event(pet.id, "sleep", stat_changes=changes)
        self._save_pet()
        self._set_action_occurred(True)
        self._get_screen_manager().go_home()
        print(f"{pet.name} is sleeping")
        return True

    def action_reset(self) -> None:
        """
        Handle reset action - shows confirmation dialog.
        Actual reset happens in confirm_reset callback.
        """
        pet = self._get_pet()
        if pet is None:
            return

        screen_manager = self._get_screen_manager()

        def confirm_reset():
            print("Resetting pet...")
            self._get_db().log_event(pet.id, "reset", notes="Pet was reset")
            self._set_action_occurred(True)
            # Start keyboard for new pet name entry
            screen_manager.start_keyboard("name_entry", "Enter Name:")

        screen_manager.show_confirmation(
            "Reset pet? All progress will be lost!",
            confirm_reset
        )

    # =========================================================================
    # Navigation Actions
    # =========================================================================

    def action_care(self) -> None:
        """Open care submenu."""
        self._get_screen_manager().set_screen(config.ScreenState.CARE_MENU)

    def action_friends(self) -> None:
        """Open friends list."""
        screen_manager = self._get_screen_manager()
        social_coordinator = self._get_social_coordinator()

        if social_coordinator:
            friends = social_coordinator.get_friends()
            screen_manager.set_friends_list(friends)
        else:
            screen_manager.set_friends_list([])

        screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)

    def action_requests(self) -> None:
        """Open friend requests."""
        screen_manager = self._get_screen_manager()
        social_coordinator = self._get_social_coordinator()

        if social_coordinator:
            requests = social_coordinator.get_pending_requests()
            screen_manager.set_pending_requests(requests)
        else:
            screen_manager.set_pending_requests([])

        screen_manager.set_screen(config.ScreenState.FRIEND_REQUESTS)

    def action_inbox(self) -> None:
        """Open inbox."""
        screen_manager = self._get_screen_manager()
        message_manager = self._get_message_manager()

        if message_manager:
            messages = message_manager.get_inbox(limit=20)
            screen_manager.set_inbox_messages(messages)
        else:
            screen_manager.set_inbox_messages([])

        screen_manager.set_screen(config.ScreenState.INBOX)

    def action_view_message(self) -> None:
        """Handle viewing a message - marks it as read."""
        screen_manager = self._get_screen_manager()
        message_manager = self._get_message_manager()

        message = screen_manager.selected_message
        if message and message_manager:
            msg_id = message.get('message_id')
            if msg_id:
                message_manager.mark_as_read(msg_id)
                message['is_read'] = True  # Update cached object

    # =========================================================================
    # Pet Management
    # =========================================================================

    def complete_name_entry(self) -> bool:
        """
        Complete name entry and create/rename pet.

        Gets the name from screen_manager, validates it, and either creates
        a new pet or renames an existing one.

        Returns:
            True if successful
        """
        screen_manager = self._get_screen_manager()
        name = screen_manager.get_entered_name()

        # Validate the name
        if name:
            name = name.strip()
            is_valid, error = config.validate_pet_name(name)
            if not is_valid:
                print(f"⚠️  Invalid pet name: {error}")
                name = None

        if not name:
            name = config.DEFAULT_PET_NAME
            print(f"Using default pet name: {name}")

        pet = self._get_pet()
        if pet is None:
            # Create new pet via callback
            self._create_new_pet(name)
            print(f"Created new pet: {name}")

            # Update WiFi device name with new pet name
            wifi_manager = self._get_wifi_manager()
            social_coordinator = self._get_social_coordinator()
            new_device_name = f"{name}_{config.DEVICE_ID_PREFIX}"

            if wifi_manager:
                wifi_manager.update_device_name(new_device_name)
            if social_coordinator:
                social_coordinator.own_pet_name = name
        else:
            # Rename existing pet
            pet.name = name
            self._save_pet()
            print(f"Renamed pet to: {name}")

        self._set_action_occurred(True)
        screen_manager.go_home()
        return True

    def complete_keyboard_name_entry(self) -> bool:
        """
        Complete keyboard name entry and create/rename pet.

        Gets the name from keyboard buffer, validates it, and either creates
        a new pet or renames an existing one.

        Returns:
            True if successful
        """
        screen_manager = self._get_screen_manager()
        name = screen_manager.get_keyboard_buffer()

        # Validate the name
        if name:
            name = name.strip()
            is_valid, error = config.validate_pet_name(name)
            if not is_valid:
                print(f"Invalid pet name: {error}")
                name = None

        if not name:
            name = config.DEFAULT_PET_NAME
            print(f"Using default pet name: {name}")

        pet = self._get_pet()
        if pet is None:
            # Create new pet via callback
            self._create_new_pet(name)
            print(f"Created new pet: {name}")

            # Update WiFi device name with new pet name
            wifi_manager = self._get_wifi_manager()
            social_coordinator = self._get_social_coordinator()
            new_device_name = f"{name}_{config.DEVICE_ID_PREFIX}"

            if wifi_manager:
                wifi_manager.update_device_name(new_device_name)
            if social_coordinator:
                social_coordinator.own_pet_name = name
        else:
            # Rename existing pet
            pet.name = name
            self._save_pet()
            print(f"Renamed pet to: {name}")

        self._set_action_occurred(True)
        screen_manager.go_home()
        return True

    def handle_send_message(self, data: dict) -> bool:
        """
        Handle sending a message to a friend.

        Args:
            data: Dict with 'to_device', 'content', 'type', 'to_name'

        Returns:
            True if message was sent/queued, False otherwise
        """
        social_coordinator = self._get_social_coordinator()
        if not social_coordinator:
            print("Social features not available")
            return False

        to_device = data.get('to_device')
        content = data.get('content', '')
        msg_type = data.get('type', 'custom')

        print(f"Sending {msg_type} message to {data.get('to_name')}: {content}")

        # Send via social coordinator
        success = social_coordinator.send_message(to_device, content)

        if success:
            print("Message sent successfully")
        else:
            print("Failed to send message (queued for retry)")

        self._set_action_occurred(True)
        self._get_screen_manager().set_screen(config.ScreenState.FRIENDS_LIST)
        return success

    def handle_send_friend_request(self, device: dict, show_feedback: bool = True) -> bool:
        """
        Handle sending a friend request.

        Args:
            device: Dict with device info from discovery ('name', 'address', 'port')
            show_feedback: Whether to show visual feedback on display

        Returns:
            True if request was sent, False otherwise
        """
        import time  # For brief pause

        social_coordinator = self._get_social_coordinator()
        if not social_coordinator:
            print("Social features not available")
            return False

        device_name = device.get('name', 'Unknown')
        # Extract pet name from device name (e.g., "Buddy_notagotchi" -> "Buddy")
        suffix = f"_{config.DEVICE_ID_PREFIX}"
        if device_name.endswith(suffix):
            pet_name = device_name[:-len(suffix)]
        else:
            pet_name = device_name

        print(f"Sending friend request to {pet_name}")

        success = social_coordinator.send_friend_request(device)

        if success:
            print(f"Friend request sent to {pet_name}")
            message = "Request Sent!"
            submessage = f"to {pet_name}"
        else:
            print(f"Failed to send friend request to {pet_name}")
            message = "Request Failed"
            submessage = ""

        # Show visual feedback if display is available
        if show_feedback:
            display = self._get_display()
            if display:
                image = display.draw_status_message(message, submessage)
                display.update_display(image)
                # Brief pause for user to see message
                time.sleep(1.5)

        # Navigate back to friends list
        self._set_action_occurred(True)
        self._get_screen_manager().set_screen(config.ScreenState.FRIENDS_LIST)
        return success

    def handle_friend_request_action(self, request: dict) -> None:
        """
        Handle a friend request - shows confirmation dialog with accept/reject options.

        Args:
            request: The friend request data with 'pet_name' and 'device_name'
        """
        social_coordinator = self._get_social_coordinator()
        if not social_coordinator:
            print("Social features not available")
            return

        from_name = request.get('pet_name', 'Unknown')
        device_name = request.get('device_name')
        screen_manager = self._get_screen_manager()

        def accept_request():
            print(f"Accepting friend request from {from_name}")
            social_coordinator.accept_friend_request(device_name)
            self._set_action_occurred(True)
            # Refresh the requests list
            requests = social_coordinator.get_pending_requests()
            screen_manager.set_pending_requests(requests)
            if len(requests) == 0:
                screen_manager.set_screen(config.ScreenState.MENU)

        def reject_request():
            print(f"Rejecting friend request from {from_name}")
            social_coordinator.reject_friend_request(device_name)
            self._set_action_occurred(True)
            # Refresh the requests list
            requests = social_coordinator.get_pending_requests()
            screen_manager.set_pending_requests(requests)
            if len(requests) == 0:
                screen_manager.set_screen(config.ScreenState.MENU)

        screen_manager.show_confirmation(
            f"Accept {from_name} as friend?",
            accept_request,
            reject_request
        )

    # =========================================================================
    # Message Deletion Actions
    # =========================================================================

    def handle_delete_single_message(self) -> None:
        """Handle delete single message action"""
        screen_manager = self._get_screen_manager()
        message_manager = self._get_message_manager()

        if not message_manager:
            print("Message manager not available")
            return

        if not screen_manager.selected_message:
            print("No message selected")
            return

        message = screen_manager.selected_message
        message_id = message.get('message_id')
        from_name = message.get('from_pet_name', 'Unknown')

        def execute_delete():
            if message_manager.delete_message(message_id):
                # Refresh inbox
                messages = message_manager.get_inbox(limit=100)
                screen_manager.set_inbox_messages(messages)
                screen_manager.set_screen(config.ScreenState.INBOX)
                self._set_action_occurred(True)
            else:
                print(f"Failed to delete message {message_id}")
                screen_manager.set_screen(config.ScreenState.MESSAGE_OPTIONS)

        def cancel_delete():
            screen_manager.set_screen(config.ScreenState.MESSAGE_OPTIONS)

        screen_manager.show_confirmation(
            f"Delete message from {from_name}?",
            execute_delete,
            cancel_delete
        )

    def handle_delete_conversation(self) -> None:
        """Handle delete conversation action"""
        screen_manager = self._get_screen_manager()
        message_manager = self._get_message_manager()
        social_coordinator = self._get_social_coordinator()

        if not message_manager:
            print("Message manager not available")
            return

        device_name = screen_manager.selected_conversation_device
        if not device_name:
            print("No conversation selected")
            return

        # Get friend name
        friend_name = "Unknown"
        if social_coordinator:
            friend = social_coordinator.friend_manager.get_friend(device_name)
            if friend:
                friend_name = friend.get('pet_name', 'Unknown')

        # Get message count
        count = message_manager.get_conversation_message_count(device_name)

        if count == 0:
            print("No messages to delete")
            screen_manager.set_screen(config.ScreenState.INBOX)
            return

        def execute_delete():
            message_manager.delete_conversation(device_name)
            # Refresh inbox
            messages = message_manager.get_inbox(limit=100)
            screen_manager.set_inbox_messages(messages)
            screen_manager.set_screen(config.ScreenState.INBOX)
            self._set_action_occurred(True)

        def cancel_delete():
            screen_manager.set_screen(config.ScreenState.MESSAGE_OPTIONS)

        screen_manager.show_confirmation(
            f"Delete {count} msg(s) with {friend_name}?",
            execute_delete,
            cancel_delete
        )

    # =========================================================================
    # Friend Removal Actions
    # =========================================================================

    def handle_remove_friend(self) -> None:
        """Handle remove friend action"""
        screen_manager = self._get_screen_manager()
        social_coordinator = self._get_social_coordinator()

        if not social_coordinator:
            print("Social coordinator not available")
            return

        device_name = screen_manager.selected_friend_for_options
        if not device_name:
            print("No friend selected")
            return

        friend = social_coordinator.friend_manager.get_friend(device_name)
        if not friend:
            print(f"Friend {device_name} not found")
            screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)
            return

        friend_name = friend.get('pet_name', 'Unknown')
        counts = social_coordinator.friend_manager.get_friend_message_counts(device_name)
        msg_count = counts['messages'] + counts['queued']

        def execute_remove():
            stats = social_coordinator.friend_manager.remove_friend(device_name)

            if stats['friend_removed']:
                print(f"Removed {friend_name}: {stats['messages_deleted']} messages deleted")
                # Refresh friends list
                friends = social_coordinator.get_friends()
                screen_manager.set_friends_list(friends)
                screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)
                self._set_action_occurred(True)
            else:
                print(f"Failed to remove friend {friend_name}")
                screen_manager.set_screen(config.ScreenState.FRIEND_OPTIONS)

        def cancel_remove():
            screen_manager.set_screen(config.ScreenState.FRIEND_OPTIONS)

        if msg_count > 0:
            confirm_msg = f"Remove {friend_name}? ({msg_count} msg(s) deleted)"
        else:
            confirm_msg = f"Remove {friend_name}?"

        screen_manager.show_confirmation(
            confirm_msg,
            execute_remove,
            cancel_remove
        )
