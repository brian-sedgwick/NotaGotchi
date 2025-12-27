#!/usr/bin/env python3
"""
Not-A-Gotchi Main Application

Main entry point and game loop for the Not-A-Gotchi virtual pet.
"""

import sys
import os
import time
import signal
import json
import logging

# Add modules directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import config
from modules.logging_config import setup_logging, get_logger
from modules.metrics import Timer, get_metrics, record_frame_time

# Initialize logging before anything else
setup_logging(level=logging.INFO)
logger = get_logger("main")
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
from modules.action_handler import ActionHandler
from modules.games import GameManager, RockPaperScissors, register_game_handlers


class NotAGotchiApp:
    """Main application class"""

    def __init__(self, simulation_mode: bool = False,
                 db: DatabaseManager = None,
                 sprite_manager: SpriteManager = None,
                 display: DisplayManager = None,
                 input_handler: InputHandler = None,
                 screen_manager: ScreenManager = None,
                 quote_manager: QuoteManager = None,
                 wifi_manager: WiFiManager = None,
                 friend_manager: FriendManager = None,
                 message_manager: MessageManager = None,
                 social_coordinator: SocialCoordinator = None,
                 skip_social_init: bool = False):
        """
        Initialize the application

        Args:
            simulation_mode: Run without actual hardware (for testing)
            db: DatabaseManager instance (injected for testing)
            sprite_manager: SpriteManager instance (injected for testing)
            display: DisplayManager instance (injected for testing)
            input_handler: InputHandler instance (injected for testing)
            screen_manager: ScreenManager instance (injected for testing)
            quote_manager: QuoteManager instance (injected for testing)
            wifi_manager: WiFiManager instance (injected for testing)
            friend_manager: FriendManager instance (injected for testing)
            message_manager: MessageManager instance (injected for testing)
            social_coordinator: SocialCoordinator instance (injected for testing)
            skip_social_init: Skip social features initialization (for testing)
        """
        self.simulation_mode = simulation_mode
        self.running = False
        self._skip_social_init = skip_social_init

        # Initialize components (use injected dependencies or create defaults)
        logger.info(f"Starting {config.PROJECT_NAME} v{config.VERSION}")
        logger.info("=" * 50)

        self.db = db or DatabaseManager()
        self.sprite_manager = sprite_manager or SpriteManager()
        self.display = display or DisplayManager(simulation_mode=simulation_mode)
        self.input_handler = input_handler or InputHandler(simulation_mode=simulation_mode)
        self.screen_manager = screen_manager or ScreenManager()
        self.quote_manager = quote_manager or QuoteManager(config.QUOTES_FILE)

        # Social features (WiFi + Friends + Messaging)
        # Store injected dependencies (may be None, will be initialized later if needed)
        self._injected_wifi_manager = wifi_manager
        self._injected_friend_manager = friend_manager
        self._injected_message_manager = message_manager
        self._injected_social_coordinator = social_coordinator
        self.wifi_manager = None
        self.friend_manager = None
        self.message_manager = None
        self.social_coordinator = None
        self.game_manager = None

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

        # Load preset messages and emojis
        self.preset_messages = self._load_json(config.PRESET_JSON_PATH)
        self.emojis = self._load_json(config.EMOJI_JSON_PATH)

        # Initialize social features (WiFi requires pet to be loaded)
        self._initialize_social_features()

        # Initialize game manager (requires social features)
        self._initialize_game_manager()

        # Create ActionHandler with all dependencies
        self._create_action_handler()

        # Initialize friend status poller
        self._initialize_friend_status_poller()

        logger.info("=" * 50)
        logger.info("Initialization complete!")

    def _initialize_social_features(self):
        """Initialize WiFi, friends, and messaging"""
        # Check if social features should be skipped (for testing)
        if self._skip_social_init:
            # Use injected dependencies if provided
            self.wifi_manager = self._injected_wifi_manager
            self.friend_manager = self._injected_friend_manager
            self.message_manager = self._injected_message_manager
            self.social_coordinator = self._injected_social_coordinator
            print("Social features skipped (testing mode)")
            return

        try:
            # Get device name (will use pet name once available)
            if self.pet:
                device_name = f"{self.pet.name}_{config.DEVICE_ID_PREFIX}"
                pet_name = self.pet.name
            else:
                device_name = f"NotAGotchi_{config.DEVICE_ID_PREFIX}"
                pet_name = "NotAGotchi"

            print("\nInitializing social features...")
            print(f"Device name: {device_name}")

            # Use injected dependencies or create new instances
            db_lock = self.db.get_lock()
            self.wifi_manager = self._injected_wifi_manager or WiFiManager(device_name)
            self.friend_manager = self._injected_friend_manager or FriendManager(
                self.db.connection, device_name, db_lock
            )
            self.message_manager = self._injected_message_manager or MessageManager(
                self.db.connection,
                self.wifi_manager,
                self.friend_manager,
                device_name,
                db_lock
            )
            self.social_coordinator = self._injected_social_coordinator or SocialCoordinator(
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

            # Register friend request callback for pop-up dialog
            def on_friend_request_received(request_data):
                from_name = request_data.get('pet_name', 'Unknown')
                device_name = request_data.get('device_name')
                print(f"\n📨 Friend request from {from_name}!")

                def accept_request():
                    print(f"Accepting friend request from {from_name}")
                    self.social_coordinator.accept_friend_request(device_name)
                    self.action_occurred = True

                def reject_request():
                    print(f"Rejecting friend request from {from_name}")
                    self.social_coordinator.reject_friend_request(device_name)
                    self.action_occurred = True

                # Show confirmation dialog immediately
                self.screen_manager.show_confirmation(
                    f"Request from {from_name}!",
                    accept_request,
                    reject_request
                )

            self.social_coordinator.register_ui_callbacks(
                on_friend_request=on_friend_request_received,
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

    def _initialize_game_manager(self):
        """Initialize game manager for multiplayer games"""
        if not self.social_coordinator or not self.wifi_manager or not self.friend_manager:
            logger.debug("Skipping game manager (social features not initialized)")
            return

        try:
            # Get device and pet names
            if self.pet:
                device_name = f"{self.pet.name}_{config.DEVICE_ID_PREFIX}"
                pet_name = self.pet.name
            else:
                device_name = f"NotAGotchi_{config.DEVICE_ID_PREFIX}"
                pet_name = "NotAGotchi"

            # Get message registry from social coordinator
            message_registry = self.social_coordinator.get_message_registry()

            # Create game manager
            self.game_manager = GameManager(
                wifi_manager=self.wifi_manager,
                friend_manager=self.friend_manager,
                db_manager=self.db,
                own_device_name=device_name,
                own_pet_name=pet_name,
                message_registry=message_registry
            )

            # Register game implementations
            self.game_manager.register_game_class('rock_paper_scissors', RockPaperScissors)

            # Set up game callbacks for UI updates
            self.game_manager.on_invite_received = self._on_game_invite_received
            self.game_manager.on_invite_accepted = self._on_game_invite_accepted
            self.game_manager.on_invite_declined = self._on_game_invite_declined
            self.game_manager.on_game_started = self._on_game_started
            self.game_manager.on_opponent_move = self._on_opponent_move
            self.game_manager.on_game_ended = self._on_game_ended
            self.game_manager.on_opponent_forfeit = self._on_opponent_forfeit

            # Connect to message handler context
            context = self.social_coordinator.get_handler_context()
            if context:
                self.game_manager.setup_context_callbacks(context)

            print("✅ Game manager initialized")
            logger.info("Game manager initialized with RPS game")

        except Exception as e:
            print(f"⚠️  Failed to initialize game manager: {e}")
            logger.error(f"Game manager init failed: {e}", exc_info=True)
            self.game_manager = None

    def _on_game_invite_received(self, invite_data):
        """Handle incoming game invite - show confirmation dialog"""
        from_name = invite_data.get('from_pet_name', 'Unknown')
        game_type = invite_data.get('game_type')
        session_id = invite_data.get('game_session_id')

        print(f"🎮 Game invite from {from_name}: {game_type}")

        # Store pending invite for UI
        self.screen_manager.set_pending_game_invite(invite_data)

        def accept_invite():
            if self.game_manager:
                self.game_manager.accept_invite(session_id)
            self.screen_manager.clear_pending_game_invite()
            self.action_occurred = True

        def decline_invite():
            if self.game_manager:
                self.game_manager.decline_invite(session_id)
            self.screen_manager.clear_pending_game_invite()
            self.action_occurred = True

        # Show confirmation dialog
        game_config = config.GAME_TYPES.get(game_type, {})
        game_name = game_config.get('name', game_type)
        self.screen_manager.show_confirmation(
            f"{from_name}: {game_name}?",
            accept_invite,
            decline_invite
        )

    def _on_game_invite_accepted(self, session):
        """Handle our invite being accepted"""
        print(f"✅ {session.opponent_pet_name} accepted the game!")
        self.screen_manager.set_game_session(session)
        self.screen_manager.set_screen(config.ScreenState.GAME_ACTIVE)
        self.action_occurred = True

    def _on_game_invite_declined(self, data):
        """Handle our invite being declined"""
        from_name = data.get('from_pet_name', 'Unknown')
        print(f"😔 {from_name} declined the game invite")
        self.screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)
        self.action_occurred = True

    def _on_game_started(self, session):
        """Handle game starting"""
        print(f"🎮 Game started vs {session.opponent_pet_name}")
        self.screen_manager.set_game_session(session)
        self.screen_manager.set_screen(config.ScreenState.GAME_ACTIVE)
        self.action_occurred = True

    def _on_opponent_move(self, move_data):
        """Handle opponent making a move"""
        print(f"🎯 Opponent moved: {move_data}")
        self.action_occurred = True

    def _on_game_ended(self, session, result):
        """Handle game ending"""
        print(f"🏁 Game ended: {result}")
        self.screen_manager.set_screen(config.ScreenState.GAME_RESULT)
        self.action_occurred = True

    def _on_opponent_forfeit(self, data):
        """Handle opponent forfeiting"""
        from_name = data.get('from_pet_name', 'Unknown')
        print(f"🏳️ {from_name} forfeited!")
        self.action_occurred = True

    def _register_actions(self):
        """Register callbacks for menu actions"""
        # Note: Actions are registered here but delegated to self.action_handler
        # after _create_action_handler() is called in __init__

        # Care actions - will be delegated to ActionHandler
        self.screen_manager.register_action('feed', self._action_feed)
        self.screen_manager.register_action('play', self._action_play)
        self.screen_manager.register_action('clean', self._action_clean)
        self.screen_manager.register_action('sleep', self._action_sleep)
        self.screen_manager.register_action('reset', self._action_reset)
        # Main menu navigation
        self.screen_manager.register_action('care', self._action_care)
        self.screen_manager.register_action('inbox', self._action_inbox)
        self.screen_manager.register_action('view_message', self._action_view_message)
        self.screen_manager.register_action('friends', self._action_friends)
        self.screen_manager.register_action('requests', self._action_requests)

    def _create_action_handler(self):
        """Create the ActionHandler with all dependencies."""
        self.action_handler = ActionHandler(
            get_pet=lambda: self.pet,
            get_db=lambda: self.db,
            get_screen_manager=lambda: self.screen_manager,
            get_social_coordinator=lambda: self.social_coordinator,
            get_message_manager=lambda: self.message_manager,
            save_pet=self._save_pet,
            set_action_occurred=lambda v: setattr(self, 'action_occurred', v),
            create_new_pet=self._create_new_pet,
            get_wifi_manager=lambda: self.wifi_manager,
            get_display=lambda: self.display
        )
        logger.debug("ActionHandler created")

    def _initialize_friend_status_poller(self):
        """Initialize the friend status poller for periodic presence checking."""
        self.friend_status_poller = None

        # Only initialize if social features are available
        if not self.social_coordinator or not self.friend_manager or not self.wifi_manager:
            logger.debug("Skipping friend status poller (social features not initialized)")
            return

        try:
            from modules.friend_status_poller import FriendStatusPoller
            from modules import config

            self.friend_status_poller = FriendStatusPoller(
                self.friend_manager,
                self.wifi_manager,
                polling_interval=config.FRIEND_POLL_INTERVAL,
                check_timeout=config.FRIEND_CHECK_TIMEOUT,
                max_parallel_checks=config.FRIEND_MAX_PARALLEL_CHECKS
            )

            # Register callbacks to trigger display refresh
            def on_friend_online(device_name):
                self.action_occurred = True  # Triggers full refresh
                logger.info(f"Friend came online: {device_name}")

            def on_friend_offline(device_name):
                self.action_occurred = True  # Triggers full refresh
                logger.info(f"Friend went offline: {device_name}")

            self.friend_status_poller.on_friend_online = on_friend_online
            self.friend_status_poller.on_friend_offline = on_friend_offline

            # Start polling thread
            self.friend_status_poller.start()
            logger.info(f"Friend status poller started ({config.FRIEND_POLL_INTERVAL}s interval)")
            print(f"✅ Friend status poller started ({config.FRIEND_POLL_INTERVAL}s interval)")

        except Exception as e:
            logger.error(f"Failed to initialize friend status poller: {e}", exc_info=True)
            print(f"⚠️  Friend status poller failed to start: {e}")
            self.friend_status_poller = None

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
            self.screen_manager.start_keyboard("name_entry", "Enter Name:")
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

    def _create_new_pet(self, name: str):
        """
        Create a new pet with the given name.

        This is used as a callback by ActionHandler.

        Args:
            name: The pet's name
        """
        pet_id = self.db.create_pet(name)
        if pet_id:
            pet_data = self.db.get_active_pet()
            self.pet = Pet.from_dict(pet_data)
            logger.info(f"Created new pet: {name} (id={pet_id})")

    # =========================================================================
    # ACTION METHODS - Delegated to ActionHandler
    # =========================================================================
    # These thin wrapper methods delegate to the ActionHandler for actual logic.
    # This keeps backward compatibility with screen_manager's action registration.

    def _action_feed(self):
        """Handle feed action - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_feed()

    def _action_play(self):
        """Handle play action - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_play()

    def _action_clean(self):
        """Handle clean action - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_clean()

    def _action_sleep(self):
        """Handle sleep action - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_sleep()

    def _action_reset(self):
        """Handle reset action - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_reset()

    def _action_care(self):
        """Open care submenu - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_care()

    def _action_friends(self):
        """Open friends list - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_friends()

    def _action_requests(self):
        """Open friend requests - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_requests()

    def _action_inbox(self):
        """Open inbox - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_inbox()

    def _action_view_message(self):
        """Handle viewing a message - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.action_view_message()

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
                    # Handle tuple actions (social features and games)
                    if isinstance(action, tuple):
                        action_type, data = action
                        if action_type == "send_message":
                            self._handle_send_message(data)
                        elif action_type == "send_friend_request":
                            self._handle_send_friend_request(data)
                        elif action_type == "handle_friend_request":
                            self._handle_friend_request_action(data)
                        elif action_type == "send_game_invite":
                            self._handle_send_game_invite(data)
                        elif action_type == "make_game_move":
                            self._handle_make_game_move(data)
                    # Handle string actions
                    elif action == "name_entry_complete":
                        self._complete_name_entry()
                    elif action == "keyboard_name_complete":
                        self._complete_keyboard_name_entry()
                    elif action == "delete_single_message":
                        self._handle_delete_single_message()
                    elif action == "delete_conversation":
                        self._handle_delete_conversation()
                    elif action == "remove_friend":
                        self._handle_remove_friend()
                    elif action == "message_friend":
                        # This is handled by screen navigation in screen_manager
                        pass
                    elif action == "cancel_game_invite":
                        self._handle_cancel_game_invite()
                    elif action == "forfeit_game":
                        self._handle_forfeit_game()
                    else:
                        # Trigger registered action
                        self.screen_manager.trigger_action(action)

    def _complete_name_entry(self):
        """Complete name entry and create/rename pet - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.complete_name_entry()

    def _complete_keyboard_name_entry(self):
        """Complete keyboard name entry and create/rename pet - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.complete_keyboard_name_entry()

    def _handle_send_message(self, data):
        """Handle sending a message to a friend - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.handle_send_message(data)

    def _handle_send_friend_request(self, device):
        """Handle sending a friend request - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.handle_send_friend_request(device)

    def _handle_friend_request_action(self, request):
        """Handle accepting/rejecting a friend request - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.handle_friend_request_action(request)

    def _handle_delete_single_message(self):
        """Handle deleting a single message - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.handle_delete_single_message()

    def _handle_delete_conversation(self):
        """Handle deleting a conversation - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.handle_delete_conversation()

    def _handle_remove_friend(self):
        """Handle removing a friend - delegates to ActionHandler"""
        if hasattr(self, 'action_handler'):
            self.action_handler.handle_remove_friend()

    def _handle_send_game_invite(self, data):
        """Handle sending a game invite to a friend"""
        if not self.game_manager:
            print("⚠️ Game manager not available")
            return

        game_type = data.get('game_type')
        opponent_device = data.get('opponent_device')
        opponent_name = data.get('opponent_name')

        print(f"🎮 Sending {game_type} invite to {opponent_name}")

        session_id = self.game_manager.send_invite(opponent_device, game_type)
        if session_id:
            # Store session and switch to waiting screen
            self.screen_manager.game_opponent_name = opponent_name
            self.screen_manager.game_opponent_device = opponent_device
            pending = self.game_manager.get_pending_outgoing()
            if pending:
                self.screen_manager.current_game_session = pending
            self.screen_manager.set_screen(config.ScreenState.GAME_WAITING)
            self.action_occurred = True
        else:
            print("❌ Failed to send game invite")

    def _handle_make_game_move(self, data):
        """Handle making a move in the active game"""
        if not self.game_manager:
            return

        move_data = data.get('move_data', {})
        success = self.game_manager.make_move(move_data)

        if success:
            self.action_occurred = True

    def _handle_cancel_game_invite(self):
        """Handle cancelling a pending game invite"""
        if self.game_manager:
            self.game_manager.cancel_pending_invite()
        self.screen_manager.current_game_session = None
        self.screen_manager.set_screen(config.ScreenState.GAME_SELECT)
        self.action_occurred = True

    def _handle_forfeit_game(self):
        """Handle forfeiting the current game"""
        if self.game_manager:
            self.game_manager.forfeit()
        self.screen_manager.current_game_session = None
        self.screen_manager.set_screen(config.ScreenState.FRIENDS_LIST)
        self.action_occurred = True

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
        elif self.screen_manager.is_emoji_category():
            image = self._render_emoji_category_screen()
        elif self.screen_manager.is_emoji_select():
            image = self._render_emoji_select_screen()
        elif self.screen_manager.is_preset_category():
            image = self._render_preset_category_screen()
        elif self.screen_manager.is_preset_select():
            image = self._render_preset_select_screen()
        elif self.screen_manager.is_text_compose():
            image = self._render_text_compose_screen()
        elif self.screen_manager.is_inbox():
            image = self._render_inbox_screen()
        elif self.screen_manager.is_message_detail():
            image = self._render_message_detail_screen()
        elif self.screen_manager.is_message_options():
            image = self._render_message_options_screen()
        elif self.screen_manager.is_friend_options():
            image = self._render_friend_options_screen()
        elif self.screen_manager.is_keyboard():
            image = self._render_keyboard_screen()
        elif self.screen_manager.is_game_select():
            image = self._render_game_select_screen()
        elif self.screen_manager.is_game_waiting():
            image = self._render_game_waiting_screen()
        elif self.screen_manager.is_game_active():
            image = self._render_game_active_screen()
        elif self.screen_manager.is_game_result():
            image = self._render_game_result_screen()
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

        # Get pet sprite and header status
        pet_sprite = self._get_pet_sprite()
        status = self._get_header_status()

        # Render status screen
        return self.display.draw_status_screen(
            pet_sprite,
            self.pet.name,
            self.pet.get_stats_dict(),
            self.pet.get_age_display(),
            self.current_quote,
            **status
        )

    def _render_menu_screen(self):
        """Render menu screen with pet sprite"""
        pet_sprite = self._get_pet_sprite()
        status = self._get_header_status()

        menu_state = self.screen_manager.get_menu_state()
        return self.display.draw_menu(
            menu_state['items'],
            menu_state['selected_index'],
            "Menu",
            pet_sprite,
            **status
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

    def _load_json(self, path: str) -> dict:
        """Load JSON file, return empty dict on error"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
            return {}

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

    def _get_unread_count(self):
        """Helper to get unread message count"""
        return self.message_manager.get_unread_count() if self.message_manager else 0

    def _get_header_status(self):
        """Get common header status values for display rendering."""
        return {
            'wifi_connected': self._get_wifi_status(),
            'online_friends': self._get_online_friends_count(),
            'unread_messages': self._get_unread_count()
        }

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

    def _render_emoji_category_screen(self):
        """Render emoji category selection screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_emoji_category_state()
        return self.display.draw_emoji_category_select(
            state['categories'],
            state['selected_index'],
            state['friend_name'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_emoji_select_screen(self):
        """Render emoji selection screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        # Set items from selected category (only if category changed)
        category = self.screen_manager.selected_emoji_category
        if category and category in self.emojis:
            current_loaded = getattr(self, '_loaded_emoji_category', None)
            if current_loaded != category:
                self.screen_manager.set_emoji_items(self.emojis[category])
                self._loaded_emoji_category = category

        state = self.screen_manager.get_emoji_select_state()
        return self.display.draw_emoji_select(
            state['emojis'],
            state['selected_index'],
            state['friend_name'],
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends
        )

    def _render_preset_category_screen(self):
        """Render preset category selection screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = self._get_online_friends_count()

        state = self.screen_manager.get_preset_category_state()
        return self.display.draw_preset_category_select(
            state['categories'],
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

        # Set items from selected category (only if category changed)
        category = self.screen_manager.selected_preset_category
        if category and category in self.preset_messages:
            current_loaded = getattr(self, '_loaded_preset_category', None)
            if current_loaded != category:
                self.screen_manager.set_preset_items(self.preset_messages[category])
                self._loaded_preset_category = category

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

    def _render_inbox_screen(self):
        """Render inbox screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = len(self.social_coordinator.get_friends(online_only=True)) if self.social_coordinator else 0
        unread_messages = self.message_manager.get_unread_count() if self.message_manager else 0

        return self.display.draw_inbox(
            self.screen_manager.inbox_messages,
            self.screen_manager.inbox_index,
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends,
            unread_messages=unread_messages
        )

    def _render_message_detail_screen(self):
        """Render message detail screen"""
        pet_sprite = self._get_pet_sprite()
        wifi_connected = self._get_wifi_status()
        online_friends = len(self.social_coordinator.get_friends(online_only=True)) if self.social_coordinator else 0
        unread_messages = self.message_manager.get_unread_count() if self.message_manager else 0

        message = self.screen_manager.selected_message

        return self.display.draw_message_detail(
            message or {},
            pet_sprite,
            wifi_connected=wifi_connected,
            online_friends=online_friends,
            unread_messages=unread_messages
        )

    def _render_message_options_screen(self):
        """Render message options menu screen"""
        return self.display.draw_message_options(
            self.screen_manager.message_options_index
        )

    def _render_friend_options_screen(self):
        """Render friend options menu screen"""
        friend_name = self.screen_manager.selected_friend_name or "Friend"
        return self.display.draw_friend_options(
            friend_name,
            self.screen_manager.friend_options_index
        )

    def _render_keyboard_screen(self):
        """Render full-screen keyboard for text input"""
        state = self.screen_manager.get_keyboard_state()
        return self.display.draw_keyboard(
            state['buffer'],
            state['selected_index'],
            state['title']
        )

    def _render_game_select_screen(self):
        """Render game selection screen"""
        state = self.screen_manager.get_game_select_state()
        return self.display.draw_game_select(
            state['items'],
            state['selected_index'],
            state['opponent_name'] or "Friend"
        )

    def _render_game_waiting_screen(self):
        """Render game waiting screen"""
        state = self.screen_manager.get_game_waiting_state()
        session = state.get('session')
        game_type = session.game_type if session else 'unknown'
        return self.display.draw_game_waiting(
            state['opponent_name'] or "Friend",
            game_type
        )

    def _render_game_active_screen(self):
        """Render active game screen"""
        state = self.screen_manager.get_game_active_state()
        session = state.get('session')
        display_state = state.get('display_state', {})

        # For now, only RPS is implemented
        return self.display.draw_game_rps(
            display_state,
            state['choice_index'],
            state['opponent_name'] or "Friend"
        )

    def _render_game_result_screen(self):
        """Render game result screen"""
        state = self.screen_manager.get_game_result_state()
        session = state.get('session')
        display_state = state.get('display_state', {})
        game_type = session.game_type if session else 'unknown'

        return self.display.draw_game_result(
            display_state,
            state['opponent_name'] or "Friend",
            game_type
        )

    def run(self):
        """Main game loop"""
        self.running = True

        logger.info("Starting main game loop...")
        logger.info("Press Ctrl+C to exit")

        try:
            while self.running:
                with Timer() as frame_timer:
                    # Process WiFi callback queue (thread-safe message handling)
                    if self.wifi_manager:
                        self.wifi_manager.process_callback_queue()

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

                # Record frame time for performance monitoring
                record_frame_time(frame_timer.elapsed_ms)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down...")
        self.running = False

        # Log final metrics summary
        metrics = get_metrics()
        summary = metrics.get_summary()
        if summary:
            logger.info("=== Final Performance Metrics ===")
            for name, stats in summary.items():
                logger.info(
                    f"  {name}: avg={stats['avg']:.2f}ms, "
                    f"min={stats['min']:.2f}ms, max={stats['max']:.2f}ms"
                )

        # Save pet one last time
        if self.pet:
            self._save_pet()
            logger.info("Pet state saved")

        # Stop social features
        if self.friend_status_poller:
            self.friend_status_poller.stop()
            logger.info("Friend status poller stopped")

        if self.message_manager:
            self.message_manager.stop_queue_processor()
            logger.info("Message queue processor stopped")

        if self.wifi_manager:
            self.wifi_manager.stop_server()
            logger.info("WiFi server stopped")

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
