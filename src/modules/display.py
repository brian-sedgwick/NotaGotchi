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
        self.last_full_refresh_time = 0  # Track last full refresh timestamp

        # Try to load default fonts
        try:
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            print("Using default font (TrueType fonts not available)")
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

        # Try to load emoji font (Symbola)
        import os
        emoji_font_paths = [
            os.path.expanduser("~/.fonts/Symbola.ttf"),  # User fonts directory
            "/usr/share/fonts/truetype/ancient-scripts/Symbola.ttf",  # System location
            "/usr/share/fonts/Symbola.ttf"  # Alternative system location
        ]

        self.font_emoji = None
        for font_path in emoji_font_paths:
            try:
                self.font_emoji = ImageFont.truetype(font_path, 14)
                print(f"Loaded emoji font from: {font_path}")
                break
            except:
                continue

        if self.font_emoji is None:
            print("Warning: Emoji font (Symbola) not found, emojis may display as boxes")
            print("Run ./install_emoji_font.sh to install the emoji font")
            self.font_emoji = self.font_small  # Fallback to regular font

        # Load stat bar icon bitmaps (supports both PNG and BMP)
        icons_dir = os.path.join(config.SPRITES_DIR, "icons")
        self.icon_food = self._load_icon_flexible(icons_dir, "food")
        self.icon_happy = self._load_icon_flexible(icons_dir, "happy")
        self.icon_heart = self._load_icon_flexible(icons_dir, "heart")
        self.icon_energy = self._load_icon_flexible(icons_dir, "energy")

        if not self.simulation_mode:
            self._initialize_display()

    def _load_icon_flexible(self, icons_dir: str, icon_name: str) -> Optional[Image.Image]:
        """Load an icon, trying multiple formats (PNG, BMP)"""
        # Try PNG first (most common from Icons8), then BMP
        for extension in ['.png', '.bmp']:
            icon_path = os.path.join(icons_dir, f"{icon_name}{extension}")
            icon = self._load_icon(icon_path)
            if icon is not None:
                return icon

        print(f"Warning: Could not find icon '{icon_name}' in PNG or BMP format")
        return None

    def _load_icon(self, icon_path: str) -> Optional[Image.Image]:
        """Load an icon from a specific path, return None if not found"""
        try:
            icon = Image.open(icon_path)

            # Handle transparency by compositing onto white background
            if icon.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', icon.size, (255, 255, 255))
                # Convert icon to RGBA if it's not already
                if icon.mode != 'RGBA':
                    icon = icon.convert('RGBA')
                # Paste icon onto white background using alpha channel
                background.paste(icon, (0, 0), icon)
                icon = background

            # Convert to 1-bit (black and white)
            if icon.mode != '1':
                icon = icon.convert('1')

            print(f"Loaded icon: {os.path.basename(icon_path)}")
            return icon
        except Exception:
            # Silently fail - we try multiple extensions
            return None

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
                          age_display: str, quote: Optional[str] = None) -> Image.Image:
        """
        Draw the main status screen with pet and stats

        Args:
            pet_sprite: PIL Image of pet sprite (100×100)
            pet_name: Pet's name
            stats: Dict with 'hunger', 'happiness', 'health', 'energy'
            age_display: Formatted age string (e.g., "5h" or "2d")
            quote: Optional quote to display over pet sprite

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

        # Draw quote box (overlaid on lower pet sprite area)
        if quote:
            self._draw_quote_box(draw, quote)

        # Draw stats (right side)
        self._draw_stats_bars(image, draw, stats)

        return image

    def draw_menu(self, menu_items: List[Dict[str, str]],
                  selected_index: int, title: str = "Menu",
                  pet_sprite: Optional[Image.Image] = None) -> Image.Image:
        """
        Draw a menu screen with pet sprite on left

        Args:
            menu_items: List of menu items with 'label' and 'action'
            selected_index: Index of currently selected item
            title: Menu title
            pet_sprite: Optional pet sprite to display on left side

        Returns:
            PIL Image of the menu screen
        """
        # Create blank canvas
        image = Image.new('1', (self.width, self.height), 1)
        draw = ImageDraw.Draw(image)

        # Draw header with title
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)], fill=0)
        draw.text((2, 1), title, fill=1, font=self.font_small)

        # Draw pet sprite on left side (same position as home screen)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))
        else:
            # Draw placeholder box if no sprite
            draw.rectangle([
                (config.PET_SPRITE_X, config.PET_SPRITE_Y),
                (config.PET_SPRITE_X + config.PET_SPRITE_WIDTH,
                 config.PET_SPRITE_Y + config.PET_SPRITE_HEIGHT)
            ], outline=0)

        # Draw menu items on right side (status area)
        x = config.STATUS_AREA_X + 5
        y_offset = config.STATUS_AREA_Y + 5
        item_height = 15
        menu_width = config.STATUS_AREA_WIDTH - 10

        for i, item in enumerate(menu_items):
            # Check if this item is visible
            if y_offset + item_height > self.height:
                break

            # Highlight selected item
            if i == selected_index:
                draw.rectangle([
                    (x, y_offset),
                    (x + menu_width, y_offset + item_height - 2)
                ], fill=0)
                # Draw text in white (inverted)
                draw.text((x + 3, y_offset + 2), item['label'],
                         fill=1, font=self.font_small)
            else:
                # Draw normal text
                draw.text((x + 3, y_offset + 2), item['label'],
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
        """Draw header with pet name, age, and battery"""
        # Background
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)],
                      fill=0)

        # Pet name (left side, white text)
        draw.text((2, 1), pet_name, fill=1, font=self.font_small)

        # Battery icon (right side)
        battery_width = 15
        battery_x = self.width - battery_width - 2
        self._draw_battery_icon(draw, battery_x, 2)

        # Age (pushed left to make room for battery)
        age_text = f"Age: {age}"
        bbox = draw.textbbox((0, 0), age_text, font=self.font_small)
        text_width = bbox[2] - bbox[0]
        age_x = battery_x - text_width - 4  # 4px gap between age and battery
        draw.text((age_x, 1), age_text, fill=1, font=self.font_small)

    def _get_battery_level(self) -> Optional[int]:
        """
        Get battery level from INA219 I2C battery monitor (0-100)

        Returns:
            Battery percentage (0-100) or None if not available
        """
        try:
            from ina219 import INA219
            print("[Battery] INA219 library imported successfully")

            # INA219 configuration (matches your test code)
            SHUNT_OHMS = 0.1
            print(f"[Battery] Connecting to INA219 (bus=1, address=0x43, shunt={SHUNT_OHMS} ohms)")
            ina = INA219(SHUNT_OHMS, busnum=1, address=0x43)
            ina.configure()
            print("[Battery] INA219 configured successfully")

            # Calculate percentage based on voltage (3V to 4.2V range for LiPo)
            voltage = ina.voltage()
            print(f"[Battery] Voltage read: {voltage:.3f}V")

            percent = (voltage - 3.0) / 1.2 * 100
            print(f"[Battery] Calculated percentage (raw): {percent:.1f}%")

            # Clamp to 0-100 range
            if percent > 100:
                percent = 100
            if percent < 0:
                percent = 0

            print(f"[Battery] Final percentage: {int(percent)}%")
            return int(percent)

        except ImportError as e:
            # ina219 library not installed
            print(f"[Battery] ImportError - INA219 library not available: {e}")
            return None
        except Exception as e:
            # INA219 not connected or I2C error
            print(f"[Battery] Error reading from INA219: {type(e).__name__}: {e}")
            return None

    def _draw_battery_icon(self, draw: ImageDraw.Draw, x: int, y: int):
        """Draw battery icon with current charge level"""
        battery_level = self._get_battery_level()

        # Battery dimensions
        width = 12
        height = 8
        tip_width = 2
        tip_height = 4

        if battery_level is None:
            # No battery - draw AC power symbol
            draw.text((x, y), "AC", fill=1, font=self.font_small)
        else:
            # Draw battery outline (white)
            draw.rectangle([(x, y), (x + width, y + height)], outline=1, fill=0)

            # Draw battery tip (white)
            draw.rectangle([
                (x + width, y + (height - tip_height) // 2),
                (x + width + tip_width, y + (height + tip_height) // 2)
            ], fill=1, outline=1)

            # Draw fill level (white fill based on percentage)
            fill_width = int((battery_level / 100.0) * (width - 2))
            if fill_width > 0:
                draw.rectangle([
                    (x + 1, y + 1),
                    (x + 1 + fill_width, y + height - 1)
                ], fill=1)

    def _draw_stats_bars(self, image: Image.Image, draw: ImageDraw.Draw, stats: Dict[str, int]):
        """Draw stat bars on the right side"""
        x = config.STATUS_AREA_X + 5
        y = config.STATUS_AREA_Y + 5  # Reduced padding to fit 4 bars
        bar_width = config.STATUS_AREA_WIDTH - 35  # Leave room for value text on right
        bar_height = 10  # Slightly reduced height
        spacing = 27  # Reduced spacing to fit 4 bars

        # Fullness bar (inverted hunger - full bar = well fed, empty = hungry)
        fullness = 100 - stats['hunger']
        self._draw_stat_bar(image, draw, x, y, bar_width, bar_height,
                          self.icon_food, fullness, fallback_text="🍖")

        # Happiness bar
        self._draw_stat_bar(image, draw, x, y + spacing, bar_width, bar_height,
                          self.icon_happy, stats['happiness'], fallback_text="😊")

        # Health bar
        self._draw_stat_bar(image, draw, x, y + spacing * 2, bar_width, bar_height,
                          self.icon_heart, stats['health'], fallback_text="❤️")

        # Energy bar
        self._draw_stat_bar(image, draw, x, y + spacing * 3, bar_width, bar_height,
                          self.icon_energy, stats['energy'], fallback_text="⚡")

    def _draw_stat_bar(self, image: Image.Image, draw: ImageDraw.Draw, x: int, y: int,
                       width: int, height: int, icon: Optional[Image.Image], value: int,
                       fallback_text: str = "?"):
        """Draw a single stat bar with icon or text label"""
        # Space reserved for icon/label (20px icon + 2px padding)
        label_width = 22

        # Draw icon or fallback text
        if icon is not None:
            # Paste icon bitmap
            # Center the icon vertically relative to the bar
            # Bar height is 10px, icon is 20px, so offset up by 5px to center
            icon_y = y - 5
            image.paste(icon, (x, icon_y))
        else:
            # Fallback to emoji text if icon not available
            draw.text((x, y), fallback_text, fill=0, font=self.font_emoji)

        # Bar starts after the icon/label, and is narrower to accommodate it
        bar_x = x + label_width
        bar_width = width - label_width

        # Bar outline
        draw.rectangle([(bar_x, y), (bar_x + bar_width, y + height)], outline=0, width=1)

        # Fill bar based on value (0-100)
        fill_width = int((value / 100.0) * (bar_width - 2))
        if fill_width > 0:
            draw.rectangle([(bar_x + 1, y + 1),
                          (bar_x + 1 + fill_width, y + height - 1)], fill=0)

        # Value text
        value_text = f"{value}"
        draw.text((bar_x + bar_width + 3, y + 1), value_text, fill=0, font=self.font_small)

    def _draw_quote_box(self, draw: ImageDraw.Draw, quote: str):
        """Draw quote text box overlaid on lower pet sprite area"""
        # Calculate quote box position (lower portion of pet sprite)
        box_x = config.PET_SPRITE_X
        box_y = config.PET_SPRITE_Y + config.QUOTE_BOX_Y
        box_width = config.PET_SPRITE_WIDTH
        box_height = config.QUOTE_BOX_HEIGHT
        padding = config.QUOTE_BOX_PADDING

        # Draw white background box with border
        draw.rectangle([
            (box_x, box_y),
            (box_x + box_width, box_y + box_height)
        ], fill=1, outline=0, width=1)

        # Wrap text to fit within box width
        max_chars_per_line = 16  # Approximate chars that fit in 100px with small font
        words = quote.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Limit to 3 lines maximum
        lines = lines[:3]

        # Draw text centered in box
        line_height = 10  # Approximate height of small font
        total_text_height = len(lines) * line_height
        start_y = box_y + padding + (box_height - total_text_height - 2 * padding) // 2

        for i, line in enumerate(lines):
            # Center text horizontally
            bbox = draw.textbbox((0, 0), line, font=self.font_small)
            text_width = bbox[2] - bbox[0]
            text_x = box_x + (box_width - text_width) // 2
            text_y = start_y + i * line_height

            draw.text((text_x, text_y), line, fill=0, font=self.font_small)

    def update_display(self, image: Image.Image, full_refresh: bool = False):
        """
        Update the physical display

        Args:
            image: PIL Image to display
            full_refresh: Request full refresh (only honored if enough time has passed)
        """
        if self.simulation_mode:
            # In simulation mode, just save the image
            print("Simulation mode: Would display image")
            return

        try:
            # Convert image to display format
            buffer = self.epd.getbuffer(image)

            # Determine refresh type
            if full_refresh:
                # Check if enough time has passed since last full refresh
                current_time = time.time()
                time_since_last_full = current_time - self.last_full_refresh_time

                if time_since_last_full >= config.FULL_REFRESH_MIN_INTERVAL:
                    # Do full refresh
                    print("Performing full refresh...")
                    self.epd.init()
                    self.epd.display(buffer)
                    self.last_full_refresh_time = current_time
                else:
                    # Not enough time has passed, do partial instead
                    time_remaining = config.FULL_REFRESH_MIN_INTERVAL - time_since_last_full
                    print(f"Full refresh requested but only {time_since_last_full:.1f}s elapsed (need {config.FULL_REFRESH_MIN_INTERVAL}s, {time_remaining:.1f}s remaining), doing partial refresh...")
                    self.epd.displayPartial(buffer)
            else:
                # Normal partial refresh (no logging to reduce console noise)
                self.epd.displayPartial(buffer)

        except Exception as e:
            print(f"Error updating display: {e}")

    def clear_display(self):
        """Clear the display to white"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.init()
                self.epd.Clear()
                self.last_full_refresh_time = time.time()  # Reset timestamp after full clear
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
