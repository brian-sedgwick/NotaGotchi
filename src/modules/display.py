"""
Not-A-Gotchi Display Module

Handles all display rendering for the Waveshare 2.13" e-Paper V4 display.
"""

import time
from typing import Optional, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from . import config

# Import Waveshare e-Paper library
try:
    import sys
    import os
    # Add waveshare_epd to path
    waveshare_path = os.path.join(os.path.dirname(__file__), '..', 'resources')
    if waveshare_path not in sys.path:
        sys.path.insert(0, waveshare_path)
    from waveshare_epd import epd2in13_V4
    DISPLAY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Waveshare library: {e}")
    print("Display will run in simulation mode")
    DISPLAY_AVAILABLE = False


class DisplayManager:
    """Manages e-ink display rendering"""

    def __init__(self, simulation_mode: bool = False):
        """
        Initialize display manager

        Args:
            simulation_mode: If True, don't initialize actual hardware
        """
        self.simulation_mode = simulation_mode or not DISPLAY_AVAILABLE
        self.epd = None
        self.width = config.DISPLAY_WIDTH
        self.height = config.DISPLAY_HEIGHT
        self.partial_refresh_count = 0

        # Try to load default font
        try:
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            print("Using default font (TrueType fonts not available)")
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

        if not self.simulation_mode:
            self._initialize_display()

    def _initialize_display(self):
        """Initialize the e-Paper display hardware"""
        try:
            print("Initializing e-Paper display...")
            self.epd = epd2in13_V4.EPD()
            self.epd.init()
            self.epd.Clear()
            print("Display initialized successfully")
        except Exception as e:
            print(f"Error initializing display: {e}")
            print("Falling back to simulation mode")
            self.simulation_mode = True
            self.epd = None

    def draw_status_screen(self, pet_sprite: Optional[Image.Image],
                          pet_name: str, stats: Dict[str, int],
                          age_display: str) -> Image.Image:
        """
        Draw the main status screen with pet and stats

        Args:
            pet_sprite: PIL Image of pet sprite (100×100)
            pet_name: Pet's name
            stats: Dict with 'hunger', 'happiness', 'health'
            age_display: Formatted age string (e.g., "5h" or "2d")

        Returns:
            PIL Image of the complete screen
        """
        # Create blank canvas (white background)
        image = Image.new('1', (self.width, self.height), 1)
        draw = ImageDraw.Draw(image)

        # Draw header
        self._draw_header(draw, pet_name, age_display)

        # Draw pet sprite (left side, 100×100)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))
        else:
            # Draw placeholder box if no sprite
            draw.rectangle([
                (config.PET_SPRITE_X, config.PET_SPRITE_Y),
                (config.PET_SPRITE_X + config.PET_SPRITE_WIDTH,
                 config.PET_SPRITE_Y + config.PET_SPRITE_HEIGHT)
            ], outline=0)
            draw.text((config.PET_SPRITE_X + 35, config.PET_SPRITE_Y + 45),
                     "???", fill=0, font=self.font_large)

        # Draw stats (right side)
        self._draw_stats_bars(draw, stats)

        return image

    def draw_menu(self, menu_items: List[Dict[str, str]],
                  selected_index: int, title: str = "Menu") -> Image.Image:
        """
        Draw a menu screen

        Args:
            menu_items: List of menu items with 'label' and 'action'
            selected_index: Index of currently selected item
            title: Menu title

        Returns:
            PIL Image of the menu screen
        """
        # Create blank canvas
        image = Image.new('1', (self.width, self.height), 1)
        draw = ImageDraw.Draw(image)

        # Draw title
        draw.text((5, 2), title, fill=0, font=self.font_medium)
        draw.line([(0, 15), (self.width, 15)], fill=0, width=1)

        # Draw menu items
        y_offset = 20
        item_height = 15

        for i, item in enumerate(menu_items):
            # Check if this item is visible
            if y_offset + item_height > self.height:
                break

            # Highlight selected item
            if i == selected_index:
                draw.rectangle([
                    (2, y_offset),
                    (self.width - 2, y_offset + item_height - 2)
                ], fill=0)
                # Draw text in white (inverted)
                draw.text((5, y_offset + 2), item['label'],
                         fill=1, font=self.font_small)
            else:
                # Draw normal text
                draw.text((5, y_offset + 2), item['label'],
                         fill=0, font=self.font_small)

            y_offset += item_height

        return image

    def draw_text_input(self, current_text: str, char_pool: str,
                       selected_char_index: int) -> Image.Image:
        """
        Draw text input screen for naming

        Args:
            current_text: Text entered so far
            char_pool: Available characters
            selected_char_index: Index of currently selected character

        Returns:
            PIL Image of the text input screen
        """
        # Create blank canvas
        image = Image.new('1', (self.width, self.height), 1)
        draw = ImageDraw.Draw(image)

        # Title
        draw.text((5, 2), "Enter Name:", fill=0, font=self.font_medium)
        draw.line([(0, 15), (self.width, 15)], fill=0, width=1)

        # Current text (large)
        current_display = current_text if current_text else "_"
        draw.text((10, 25), current_display, fill=0, font=self.font_large)

        # Character selector
        draw.line([(0, 50), (self.width, 50)], fill=0, width=1)

        # Show current character large in center
        selected_char = char_pool[selected_char_index]
        draw.rectangle([(75, 60), (175, 95)], outline=0, width=2)
        draw.text((110, 70), selected_char, fill=0, font=self.font_large)

        # Instructions
        draw.text((5, 100), "Turn: Select | Press: Add", fill=0, font=self.font_small)

        return image

    def draw_confirmation(self, message: str, selected: bool = True) -> Image.Image:
        """
        Draw a confirmation dialog

        Args:
            message: Confirmation message
            selected: True for "Yes" selected, False for "No"

        Returns:
            PIL Image of confirmation screen
        """
        # Create blank canvas
        image = Image.new('1', (self.width, self.height), 1)
        draw = ImageDraw.Draw(image)

        # Draw border
        draw.rectangle([(10, 20), (self.width - 10, self.height - 20)],
                      outline=0, width=2)

        # Draw message (word wrap if needed)
        y_offset = 30
        words = message.split()
        line = ""
        for word in words:
            test_line = line + word + " "
            bbox = draw.textbbox((0, 0), test_line, font=self.font_small)
            if bbox[2] - bbox[0] < self.width - 30:
                line = test_line
            else:
                draw.text((20, y_offset), line, fill=0, font=self.font_small)
                line = word + " "
                y_offset += 12

        if line:
            draw.text((20, y_offset), line, fill=0, font=self.font_small)

        # Draw Yes/No buttons
        yes_box = [(30, 80), (100, 100)]
        no_box = [(130, 80), (200, 100)]

        # Draw Yes button
        if selected:
            draw.rectangle(yes_box, fill=0, outline=0)
            draw.text((52, 87), "Yes", fill=1, font=self.font_small)
        else:
            draw.rectangle(yes_box, outline=0, width=2)
            draw.text((52, 87), "Yes", fill=0, font=self.font_small)

        # Draw No button
        if not selected:
            draw.rectangle(no_box, fill=0, outline=0)
            draw.text((157, 87), "No", fill=1, font=self.font_small)
        else:
            draw.rectangle(no_box, outline=0, width=2)
            draw.text((157, 87), "No", fill=0, font=self.font_small)

        return image

    def _draw_header(self, draw: ImageDraw.Draw, pet_name: str, age: str):
        """Draw header with pet name and age"""
        # Background
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)],
                      fill=0)

        # Pet name (left side, white text)
        draw.text((2, 1), pet_name, fill=1, font=self.font_small)

        # Age (right side, white text)
        age_text = f"Age: {age}"
        bbox = draw.textbbox((0, 0), age_text, font=self.font_small)
        text_width = bbox[2] - bbox[0]
        draw.text((self.width - text_width - 2, 1), age_text,
                 fill=1, font=self.font_small)

    def _draw_stats_bars(self, draw: ImageDraw.Draw, stats: Dict[str, int]):
        """Draw stat bars on the right side"""
        x = config.STATUS_AREA_X + 5
        y = config.STATUS_AREA_Y + 10
        bar_width = config.STATUS_AREA_WIDTH - 15
        bar_height = 12
        spacing = 20

        # Hunger bar
        self._draw_stat_bar(draw, x, y, bar_width, bar_height,
                          "Hunger", stats['hunger'])

        # Happiness bar
        self._draw_stat_bar(draw, x, y + spacing, bar_width, bar_height,
                          "Happy", stats['happiness'])

        # Health bar
        self._draw_stat_bar(draw, x, y + spacing * 2, bar_width, bar_height,
                          "Health", stats['health'])

    def _draw_stat_bar(self, draw: ImageDraw.Draw, x: int, y: int,
                       width: int, height: int, label: str, value: int):
        """Draw a single stat bar"""
        # Label
        draw.text((x, y - 10), label, fill=0, font=self.font_small)

        # Bar outline
        draw.rectangle([(x, y), (x + width, y + height)], outline=0, width=1)

        # Fill bar based on value (0-100)
        fill_width = int((value / 100.0) * (width - 2))
        if fill_width > 0:
            draw.rectangle([(x + 1, y + 1),
                          (x + 1 + fill_width, y + height - 1)], fill=0)

        # Value text
        value_text = f"{value}"
        draw.text((x + width + 3, y + 1), value_text, fill=0, font=self.font_small)

    def update_display(self, image: Image.Image, full_refresh: bool = False):
        """
        Update the physical display

        Args:
            image: PIL Image to display
            full_refresh: Force full refresh (clears ghosting)
        """
        if self.simulation_mode:
            # In simulation mode, just save the image
            print("Simulation mode: Would display image")
            return

        try:
            # Convert image to display format
            buffer = self.epd.getbuffer(image)

            # Determine refresh type
            if full_refresh or self.partial_refresh_count >= config.FULL_REFRESH_EVERY_N:
                print("Performing full refresh...")
                self.epd.init()
                self.epd.display(buffer)
                self.partial_refresh_count = 0
            else:
                print("Performing partial refresh...")
                self.epd.displayPartial(buffer)
                self.partial_refresh_count += 1

        except Exception as e:
            print(f"Error updating display: {e}")

    def clear_display(self):
        """Clear the display to white"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.init()
                self.epd.Clear()
                self.partial_refresh_count = 0
            except Exception as e:
                print(f"Error clearing display: {e}")

    def sleep(self):
        """Put display into sleep mode"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.sleep()
                print("Display entering sleep mode")
            except Exception as e:
                print(f"Error putting display to sleep: {e}")

    def close(self):
        """Clean up display resources"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.sleep()
                print("Display closed")
            except Exception as e:
                print(f"Error closing display: {e}")
