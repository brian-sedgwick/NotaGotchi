#!/usr/bin/env python3
"""
Not-A-Gotchi Main Application

Main entry point and game loop for the Not-A-Gotchi virtual pet.
"""

import sys
import os
import time
import signal

# Add modules directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import config
from modules.persistence import DatabaseManager
from modules.pet import Pet
from modules.sprite_manager import SpriteManager
from modules.display import DisplayManager
from modules.input_handler import InputHandler, InputEvent
from modules.screen_manager import ScreenManager
from modules.quote_manager import QuoteManager
from modules.wifi_manager import WiFiManager
from modules.friend_manager import FriendManager
from modules.messaging import MessageManager
from modules.social_coordinator import SocialCoordinator


class NotAGotchiApp:
    """Main application class"""

    def __init__(self, simulation_mode: bool = False):
        """
        Initialize the application

        Args:
            simulation_mode: Run without actual hardware (for testing)
        """
        self.simulation_mode = simulation_mode
        self.running = False

        # Initialize components
        print(f"Starting {config.PROJECT_NAME} v{config.VERSION}")
        print("=" * 50)

        self.db = DatabaseManager()
        self.sprite_manager = SpriteManager()
        self.display = DisplayManager(simulation_mode=simulation_mode)
        self.input_handler = InputHandler(simulation_mode=simulation_mode)
        self.screen_manager = ScreenManager()
        self.quote_manager = QuoteManager(config.QUOTES_FILE)

        # Social features (WiFi + Friends + Messaging)
        self.wifi_manager = None
        self.friend_manager = None
        self.message_manager = None
        self.social_coordinator = None

        # Game state
        self.pet = None
        self.last_update_time = time.time()
        self.last_save_time = time.time()
        self.last_display_time = time.time()
        self.last_quote_change_time = time.time()
        self.current_quote = None
        self.action_occurred = False  # Track user actions for full refresh
        self.first_render = True  # Force full refresh on first render

        # Register action callbacks
        self._register_actions()

        # Load or create pet
        self._load_or_create_pet()

        # Preload sprites
        print("Loading sprites...")
        self.sprite_manager.preload_all_sprites()

        # Initialize social features (WiFi requires pet to be loaded)
        self._initialize_social_features()

        print("=" * 50)
        print("Initialization complete!\n")

    def _initialize_social_features(self):
        """Initialize WiFi, friends, and messaging"""
        try:
            # Get device name (will use pet name once available)
            if self.pet:
                device_name = f"{config.DEVICE_ID_PREFIX}_{self.pet.name}"
                pet_name = self.pet.name
            else:
                device_name = f"{config.DEVICE_ID_PREFIX}_NotAGotchi"
                pet_name = "NotAGotchi"

            print("\nInitializing social features...")
            print(f"Device name: {device_name}")

            # Initialize managers
            self.wifi_manager = WiFiManager(device_name)
            self.friend_manager = FriendManager(self.db.connection, device_name)
            self.message_manager = MessageManager(
                self.db.connection,
                self.wifi_manager,
                self.friend_manager,
                device_name
            )
            self.social_coordinator = SocialCoordinator(
                self.wifi_manager,
                self.friend_manager,
                pet_name,
                self.message_manager
            )

            # Start WiFi server
            if self.wifi_manager.start_server():
                print("✅ WiFi server started")
            else:
                print("⚠️  WiFi server failed to start (social features disabled)")
                return

            # Start message queue processor
            self.message_manager.start_queue_processor()
            print("✅ Message queue processor started")

            # Register message callback
            def on_message_received(message_data, sender_ip):
                from_pet = message_data.get('from_pet_name', 'Unknown')
                content = message_data.get('content', '')
                print(f"\n📬 Message from {from_pet}: {content}")

            self.social_coordinator.register_ui_callbacks(
                on_message=on_message_received
            )

            print("✅ Social features initialized")

        except Exception as e:
            print(f"⚠️  Failed to initialize social features: {e}")
            print("Continuing without social features...")
            self.wifi_manager = None
            self.friend_manager = None
            self.message_manager = None
            self.social_coordinator = None

    def _register_actions(self):
        """Register callbacks for menu actions"""
        # Care actions
        self.screen_manager.register_action('feed', self._action_feed)
        self.screen_manager.register_action('play', self._action_play)
        self.screen_manager.register_action('clean', self._action_clean)
        self.screen_manager.register_action('sleep', self._action_sleep)
        self.screen_manager.register_action('reset', self._action_reset)
        # Main menu navigation
        self.screen_manager.register_action('care', self._action_care)
        self.screen_manager.register_action('friends', self._action_friends)
        self.screen_manager.register_action('requests', self._action_requests)

    def _load_or_create_pet(self):
        """Load existing pet or create new one"""
        pet_data = self.db.get_active_pet()

        if pet_data:
            print(f"Loading existing pet: {pet_data['name']}")
            self.pet = Pet.from_dict(pet_data)

            # Recover from time offline
            self._recover_from_offline()
        else:
            print("No existing pet found. Creating new pet...")
            self.screen_manager.start_name_entry()
            self.pet = None  # Will be created after name entry

    def _recover_from_offline(self):
        """Recover pet state after being powered off - pause behavior"""
        if self.pet is None:
            return

        current_time = time.time()
        time_offline = current_time - self.pet.last_update
        hours_offline = time_offline / 3600

        if hours_offline > 0.1:  # More than 6 minutes
            print(f"Pet was offline for {hours_offline:.1f} hours")
            print("Resuming from saved state (no stat changes)")

        # Reset timing anchors to current time (pause effect)
        self.pet.last_update = current_time
        self.pet.last_sleep_time = current_time

        # Save the updated timestamps
        self._save_pet()

        # Log the pause/resume event
        self.db.log_event(
            self.pet.id,
            "resume",
            notes=f"Resumed after {hours_offline:.1f} hours offline (paused)"
        )

    def _action_feed(self):
        """Handle feed action"""
        if self.pet is None:
            return

        changes = self.pet.feed()
        self.db.log_event(self.pet.id, "feed", stat_changes=changes)
        self._save_pet()
        self.action_occurred = True  # Trigger full refresh
        self.screen_manager.go_home()
        print(f"Fed {self.pet.name}")

    def _action_play(self):
        """Handle play action"""
        if self.pet is None:
            return

        changes = self.pet.play()
        self.db.log_event(self.pet.id, "play", stat_changes=changes)
        self._save_pet()
        self.action_occurred = True  # Trigger full refresh
        self.screen_manager.go_home()
        print(f"Played with {self.pet.name}")

    def _action_clean(self):
        """Handle clean action"""
        if self.pet is None:
            return

        changes = self.pet.clean()
        self.db.log_event(self.pet.id, "clean", stat_changes=changes)
        self._save_pet()
        self.action_occurred = True  # Trigger full refresh
        self.screen_manager.go_home()
        print(f"Cleaned {self.pet.name}")

    def _action_sleep(self):
        """Handle sleep action"""
        if self.pet is None:
            return

        changes = self.pet.sleep()
        self.db.log_event(self.pet.id, "sleep", stat_changes=changes)
        self._save_pet()
        self.action_occurred = True  # Trigger full refresh
        self.screen_manager.go_home()
        print(f"{self.pet.name} is sleeping")

    def _action_reset(self):
        """Handle reset action - show confirmation first"""
        if self.pet is None:
            return

        def confirm_reset():
            print("Resetting pet...")
            self.pet.reset()
            self.db.log_event(self.pet.id, "reset", notes="Pet was reset")
            self._save_pet()
            self.action_occurred = True  # Trigger full refresh
            # Start name entry for new pet
            self.screen_manager.start_name_entry()

        self.screen_manager.show_confirmation(
            "Reset pet? All progress will be lost!",
            confirm_reset
        )

    def _action_care(self):
        """Open care submenu"""
        self.screen_manager.set_screen(config.ScreenState.CARE_MENU)

    def _action_friends(self):
        """Open friends list"""
        # Update friends list from social coordinator
        if self.social_coordinator:
            friends = self.social_coordinator.get_friends()
            self.screen_manager.set_friends_list(friends)
        else:
            self.screen_manager.set_friends_list([])
        self.screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)

    def _action_requests(self):
        """Open friend requests"""
        # Update pending requests from social coordinator
        if self.social_coordinator:
            requests = self.social_coordinator.get_pending_requests()
            self.screen_manager.set_pending_requests(requests)
        else:
            self.screen_manager.set_pending_requests([])
        self.screen_manager.set_screen(config.ScreenState.FRIEND_REQUESTS)

    def _save_pet(self):
        """Save pet state to database"""
        if self.pet is None:
            return

        success = self.db.update_pet(
            self.pet.id,
            hunger=int(self.pet.hunger),
            happiness=int(self.pet.happiness),
            health=int(self.pet.health),
            energy=int(self.pet.energy),
            evolution_stage=self.pet.evolution_stage,
            age_seconds=self.pet.age_seconds,
            last_update=self.pet.last_update,
            last_sleep_time=self.pet.last_sleep_time
        )

        if success:
            self.last_save_time = time.time()
        else:
            print("Warning: Failed to save pet state")

    def _update_pet_stats(self):
        """Update pet stats based on elapsed time"""
        if self.pet is None:
            return

        current_time = time.time()
        time_since_update = current_time - self.last_update_time

        if time_since_update >= config.UPDATE_INTERVAL:
            print("Updating pet stats...")
            changes = self.pet.update_stats(current_time)
            self.last_update_time = current_time

            # Log stat update
            self.db.log_event(
                self.pet.id,
                "stat_update",
                stat_changes=changes
            )

            print(f"Stats: {self.pet.get_stats_dict()}")

    def _auto_save(self):
        """Periodically save pet state"""
        current_time = time.time()
        if current_time - self.last_save_time >= config.SAVE_INTERVAL:
            self._save_pet()

    def _handle_input(self):
        """Process input events"""
        # Check for long press
        self.input_handler.check_long_press()

        # Process all pending events
        while self.input_handler.has_events():
            event = self.input_handler.get_event()
            if event:
                action = self.screen_manager.handle_input(event)

                if action:
                    # Handle tuple actions (social features)
                    if isinstance(action, tuple):
                        action_type, data = action
                        if action_type == "send_message":
                            self._handle_send_message(data)
                        elif action_type == "send_friend_request":
                            self._handle_send_friend_request(data)
                        elif action_type == "handle_friend_request":
                            self._handle_friend_request_action(data)
                    # Handle string actions
                    elif action == "name_entry_complete":
                        self._complete_name_entry()
                    else:
                        # Trigger registered action
                        self.screen_manager.trigger_action(action)

    def _complete_name_entry(self):
        """Complete name entry and create/rename pet"""
        name = self.screen_manager.get_entered_name()

        if not name:
            name = config.DEFAULT_PET_NAME

        if self.pet is None:
            # Create new pet
            pet_id = self.db.create_pet(name)
            if pet_id:
                pet_data = self.db.get_active_pet()
                self.pet = Pet.from_dict(pet_data)
                print(f"Created new pet: {name}")
        else:
            # Rename existing pet
            self.pet.name = name
            self._save_pet()
            print(f"Renamed pet to: {name}")

        self.action_occurred = True  # Trigger full refresh
        self.screen_manager.go_home()

    def _handle_send_message(self, data):
        """Handle sending a message to a friend"""
        if not self.social_coordinator:
            print("Social features not available")
            return

        to_device = data.get('to_device')
        content = data.get('content', '')
        msg_type = data.get('type', 'custom')

        print(f"Sending {msg_type} message to {data.get('to_name')}: {content}")

        # Send via social coordinator
        success = self.social_coordinator.send_message(to_device, content)

        if success:
            print("Message sent successfully")
        else:
            print("Failed to send message (queued for retry)")

        self.action_occurred = True
        self.screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)

    def _handle_send_friend_request(self, device):
        """Handle sending a friend request"""
        if not self.social_coordinator:
            print("Social features not available")
            return

        device_name = device.get('name', 'Unknown')
        device_ip = device.get('ip')

        print(f"Sending friend request to {device_name}")

        success = self.social_coordinator.send_friend_request(device_ip)

        if success:
            print(f"Friend request sent to {device_name}")
        else:
            print(f"Failed to send friend request to {device_name}")

        self.action_occurred = True
        self.screen_manager.set_screen(config.ScreenState.FIND_FRIENDS)

    def _handle_friend_request_action(self, request):
        """Handle accepting/rejecting a friend request"""
        if not self.social_coordinator:
            print("Social features not available")
            return

        from_name = request.get('from_pet_name', 'Unknown')

        def accept_request():
            print(f"Accepting friend request from {from_name}")
            self.social_coordinator.accept_friend_request(request)
            self.action_occurred = True
            # Refresh the requests list
            requests = self.social_coordinator.get_pending_requests()
            self.screen_manager.set_pending_requests(requests)
            if len(requests) == 0:
                self.screen_manager.set_screen(config.ScreenState.MENU)

        self.screen_manager.show_confirmation(
            f"Accept {from_name} as friend?",
            accept_request
        )

    def _render_display(self):
        """Render current screen to display"""
        current_time = time.time()

        # Throttle display updates
        if current_time - self.last_display_time < config.DISPLAY_UPDATE_RATE:
            return

        self.last_display_time = current_time

        # Update evolution and sleep timers
        if self.pet:
            delta_time = current_time - self.last_display_time
            self.pet.tick_evolution_timer(delta_time)
            self.pet.tick_sleep_timer(delta_time)

        # Update quote rotation (every 10 seconds)
        if self.pet and current_time - self.last_quote_change_time >= config.QUOTE_ROTATION_INTERVAL:
            emotion = self.pet.get_emotion_state()
            self.current_quote = self.quote_manager.get_random_quote(emotion)
            self.last_quote_change_time = current_time

        # Render based on current screen
        if self.screen_manager.is_home():
            image = self._render_home_screen()
        elif self.screen_manager.is_menu():
            image = self._render_menu_screen()
        elif self.screen_manager.is_name_entry():
            image = self._render_name_entry_screen()
        elif self.screen_manager.is_confirmation():
            image = self._render_confirmation_screen()
        elif self.screen_manager.is_care_menu():
            image = self._render_care_menu_screen()
        elif self.screen_manager.is_friends_list():
            image = self._render_friends_list_screen()
        elif self.screen_manager.is_find_friends():
            image = self._render_find_friends_screen()
        elif self.screen_manager.is_friend_requests():
            image = self._render_friend_requests_screen()
        elif self.screen_manager.is_message_type_menu():
            image = self._render_message_type_menu_screen()
        elif self.screen_manager.is_emoji_select():
            image = self._render_emoji_select_screen()
        elif self.screen_manager.is_preset_select():
            image = self._render_preset_select_screen()
        elif self.screen_manager.is_text_compose():
            image = self._render_text_compose_screen()
        else:
            return  # Unknown screen

        # Update display (with full refresh if user action occurred or first render)
        force_full = self.action_occurred or self.first_render
        self.display.update_display(image, full_refresh=force_full)

        # Reset flags after display update
        if self.action_occurred:
            self.action_occurred = False
        if self.first_render:
            self.first_render = False

    def _render_home_screen(self):
        """Render home/status screen"""
        if self.pet is None:
            # Show "Waiting for name..." message
            from PIL import Image, ImageDraw
            image = Image.new('1', (self.display.width, self.display.height), 1)
            draw = ImageDraw.Draw(image)
            draw.text((50, 50), "Waiting for name...", fill=0)
            return image

        # Get pet sprite
        sprite_name = self.pet.get_current_sprite()
        pet_sprite = self.sprite_manager.get_sprite_by_name(sprite_name)

        if pet_sprite is None:
            # Use placeholder
            pet_sprite = self.sprite_manager.create_placeholder_sprite()

        # Get WiFi and friend status for header
        wifi_connected = self.wifi_manager.running if self.wifi_manager else False
        online_friends = len(self.social_coordinator.get_friends(online_only=True)) if self.social_coordinator else 0

        # Render status screen
        return self.display.draw_status_screen(
            pet_sprite,
            self.pet.name,
            self.pet.get_stats_dict(),
            self.pet.get_age_display(),
            self.current_quote,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_menu_screen(self):
        """Render menu screen with pet sprite"""
        if self.pet is None:
            pet_sprite = None
        else:
            # Get pet sprite (same as home screen)
            sprite_name = self.pet.get_current_sprite()
            pet_sprite = self.sprite_manager.get_sprite_by_name(sprite_name)
            if pet_sprite is None:
                pet_sprite = self.sprite_manager.create_placeholder_sprite()

        # Get WiFi and friend status for header
        wifi_connected = self.wifi_manager.running if self.wifi_manager else False
        online_friends = len(self.social_coordinator.get_friends(online_only=True)) if self.social_coordinator else 0

        menu_state = self.screen_manager.get_menu_state()
        return self.display.draw_menu(
            menu_state['items'],
            menu_state['selected_index'],
            "Menu",
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_name_entry_screen(self):
        """Render name entry screen"""
        state = self.screen_manager.get_name_entry_state()
        return self.display.draw_text_input(
            state['current_text'],
            state['char_pool'],
            state['selected_char_index']
        )

    def _render_confirmation_screen(self):
        """Render confirmation dialog"""
        state = self.screen_manager.get_confirmation_state()
        return self.display.draw_confirmation(
            state['message'],
            state['selected']
        )

    def _get_pet_sprite(self):
        """Helper to get current pet sprite"""
        if self.pet is None:
            return None
        sprite_name = self.pet.get_current_sprite()
        pet_sprite = self.sprite_manager.get_sprite_by_name(sprite_name)
        if pet_sprite is None:
            pet_sprite = self.sprite_manager.create_placeholder_sprite()
        return pet_sprite

    def _get_wifi_status(self):
        """Helper to get WiFi connection status"""
        return self.wifi_manager.running if self.wifi_manager else False

    def _get_online_friends_count(self):
        """Helper to get online friends count"""
        if self.social_coordinator:
            return len(self.social_coordinator.get_friends(online_only=True))
        return 0

    def _render_care_menu_screen(self):
        """Render care menu screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_care_menu_state()
        return self.display.draw_menu(
            state['items'],
            state['selected_index'],
            "Care",
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_friends_list_screen(self):
        """Render friends list screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_friends_list_state()
        return self.display.draw_friends_list(
            state['friends'],
            state['selected_index'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_find_friends_screen(self):
        """Render find friends screen"""
        # Trigger device discovery when entering this screen
        if self.social_coordinator:
            devices = self.social_coordinator.discover_new_devices()
            self.screen_manager.set_discovered_devices(devices)

        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_find_friends_state()
        return self.display.draw_find_friends(
            state['devices'],
            state['selected_index'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_friend_requests_screen(self):
        """Render friend requests screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_friend_requests_state()
        return self.display.draw_friend_requests(
            state['requests'],
            state['selected_index'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_message_type_menu_screen(self):
        """Render message type selection screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_message_type_menu_state()
        title = f"To: {state['friend_name']}" if state['friend_name'] else "Send"
        return self.display.draw_menu(
            state['items'],
            state['selected_index'],
            title,
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_emoji_select_screen(self):
        """Render emoji selection screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_emoji_select_state()
        return self.display.draw_emoji_select(
            state['emojis'],
            state['selected_index'],
            state['friend_name'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_preset_select_screen(self):
        """Render preset message selection screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_preset_select_state()
        return self.display.draw_preset_select(
            state['presets'],
            state['selected_index'],
            state['friend_name'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_text_compose_screen(self):
        """Render custom text compose screen"""
        state = self.screen_manager.get_text_compose_state()
        return self.display.draw_text_input(
            state['current_text'],
            state['char_pool'],
            state['selected_char_index'],
            title=f"To: {state['friend_name']}" if state['friend_name'] else "Compose"
        )

    def run(self):
        """Main game loop"""
        self.running = True

        print("Starting main game loop...")
        print("Press Ctrl+C to exit\n")

        try:
            while self.running:
                # Handle input
                self._handle_input()

                # Update pet stats
                self._update_pet_stats()

                # Auto-save
                self._auto_save()

                # Render display
                self._render_display()

                # Small delay to prevent CPU spinning
                time.sleep(config.INPUT_POLL_RATE)

        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        print("\nShutting down...")
        self.running = False

        # Save pet one last time
        if self.pet:
            self._save_pet()
            print("Pet state saved")

        # Stop social features
        if self.message_manager:
            self.message_manager.stop_queue_processor()
            print("Message queue processor stopped")

        if self.wifi_manager:
            self.wifi_manager.stop_server()
            print("WiFi server stopped")

        # Clean up resources
        self.display.close()
        self.input_handler.close()
        self.db.close()

        print("Shutdown complete")

    def handle_signal(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        print(f"\nReceived signal {signum}")
        self.running = False


def main():
    """Entry point"""
    # Check for simulation mode
    simulation_mode = '--sim' in sys.argv or '--simulation' in sys.argv

    # Create and run app
    app = NotAGotchiApp(simulation_mode=simulation_mode)

    # Set up signal handlers
    signal.signal(signal.SIGINT, app.handle_signal)
    signal.signal(signal.SIGTERM, app.handle_signal)

    # Run main loop
    app.run()


if __name__ == "__main__":
    main()
