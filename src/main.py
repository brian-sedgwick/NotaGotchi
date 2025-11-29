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

        # Game state
        self.pet = None
        self.last_update_time = time.time()
        self.last_save_time = time.time()
        self.last_display_time = time.time()
        self.action_occurred = False  # Track user actions for full refresh

        # Register action callbacks
        self._register_actions()

        # Load or create pet
        self._load_or_create_pet()

        # Preload sprites
        print("Loading sprites...")
        self.sprite_manager.preload_all_sprites()

        print("=" * 50)
        print("Initialization complete!\n")

    def _register_actions(self):
        """Register callbacks for menu actions"""
        self.screen_manager.register_action('feed', self._action_feed)
        self.screen_manager.register_action('play', self._action_play)
        self.screen_manager.register_action('clean', self._action_clean)
        self.screen_manager.register_action('sleep', self._action_sleep)
        self.screen_manager.register_action('reset', self._action_reset)

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
        """Recover pet state after being powered off"""
        if self.pet is None:
            return

        time_offline = time.time() - self.pet.last_update
        hours_offline = time_offline / 3600

        if hours_offline > 0.1:  # More than 6 minutes
            print(f"Pet was offline for {hours_offline:.1f} hours")
            print("Recovering stats...")

            # Apply stat changes for time missed
            changes = self.pet.update_stats()

            # Log recovery
            self.db.log_event(
                self.pet.id,
                "recovery",
                stat_changes=changes,
                notes=f"Recovered from {hours_offline:.1f} hours offline"
            )

            print(f"Stats after recovery: {self.pet.get_stats_dict()}")

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

    def _save_pet(self):
        """Save pet state to database"""
        if self.pet is None:
            return

        success = self.db.update_pet(
            self.pet.id,
            hunger=int(self.pet.hunger),
            happiness=int(self.pet.happiness),
            health=int(self.pet.health),
            evolution_stage=self.pet.evolution_stage,
            age_seconds=self.pet.age_seconds,
            last_update=self.pet.last_update
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
                    # Handle special actions
                    if action == "name_entry_complete":
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

    def _render_display(self):
        """Render current screen to display"""
        current_time = time.time()

        # Throttle display updates
        if current_time - self.last_display_time < config.DISPLAY_UPDATE_RATE:
            return

        self.last_display_time = current_time

        # Update evolution timer
        if self.pet:
            self.pet.tick_evolution_timer(current_time - self.last_display_time)

        # Render based on current screen
        if self.screen_manager.is_home():
            image = self._render_home_screen()
        elif self.screen_manager.is_menu():
            image = self._render_menu_screen()
        elif self.screen_manager.is_name_entry():
            image = self._render_name_entry_screen()
        elif self.screen_manager.is_confirmation():
            image = self._render_confirmation_screen()
        else:
            return  # Unknown screen

        # Update display (with full refresh if user action occurred)
        self.display.update_display(image, full_refresh=self.action_occurred)

        # Reset action flag after display update
        if self.action_occurred:
            self.action_occurred = False

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

        # Render status screen
        return self.display.draw_status_screen(
            pet_sprite,
            self.pet.name,
            self.pet.get_stats_dict(),
            self.pet.get_age_display()
        )

    def _render_menu_screen(self):
        """Render menu screen"""
        menu_state = self.screen_manager.get_menu_state()
        return self.display.draw_menu(
            menu_state['items'],
            menu_state['selected_index'],
            "Care Menu"
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
