"""
Not-A-Gotchi Display Module

Handles all display rendering for the Waveshare 2.13" e-Paper V4 display.
"""

import time
from typing import Optional, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from . import config
from .logging_config import get_logger

# Module logger
logger = get_logger(__name__)

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
    logger.warning(f"Could not import Waveshare library: {e}")
    logger.info("Display will run in simulation mode")
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

        # Try to load default fonts using config sizes
        try:
            self.font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                config.FONT_SIZE_SMALL
            )
            self.font_medium = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                config.FONT_SIZE_MEDIUM
            )
            self.font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                config.FONT_SIZE_LARGE
            )
        except Exception:
            logger.debug("TrueType fonts not available, using default font")
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
                self.font_emoji = ImageFont.truetype(font_path, config.FONT_SIZE_EMOJI)
                logger.debug(f"Loaded emoji font from: {font_path}")
                break
            except Exception:
                continue

        if self.font_emoji is None:
            logger.warning("Emoji font (Symbola) not found, emojis may display as boxes")
            logger.info("Run ./install_emoji_font.sh to install the emoji font")
            self.font_emoji = self.font_small  # Fallback to regular font

        # Load stat bar icon bitmaps (supports both PNG and BMP)
        icons_dir = os.path.join(config.SPRITES_DIR, "icons")
        self.icon_food = self._load_icon_flexible(icons_dir, "food")
        self.icon_happy = self._load_icon_flexible(icons_dir, "happy")
        self.icon_heart = self._load_icon_flexible(icons_dir, "heart")
        self.icon_energy = self._load_icon_flexible(icons_dir, "energy")

        # Load header status icons
        self.icon_wifi_on = self._load_icon_flexible(icons_dir, "wifi_on")
        self.icon_wifi_off = self._load_icon_flexible(icons_dir, "wifi_off")
        # Reuse heart icon for friends count
        self.icon_friends = self.icon_heart

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

        logger.debug(f"Could not find icon '{icon_name}' in PNG or BMP format")
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

            logger.debug(f"Loaded icon: {os.path.basename(icon_path)}")
            return icon
        except Exception:
            # Silently fail - we try multiple extensions
            return None

    def _initialize_display(self):
        """Initialize the e-Paper display hardware"""
        try:
            logger.info("Initializing e-Paper display...")
            self.epd = epd2in13_V4.EPD()
            self.epd.init()
            self.epd.Clear()
            logger.info("Display initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing display: {e}")
            logger.info("Falling back to simulation mode")
            self.simulation_mode = True
            self.epd = None

    # =========================================================================
    # HELPER METHODS - Extracted to reduce duplication
    # =========================================================================

    def _create_canvas(self) -> tuple:
        """
        Create a blank canvas for drawing.

        Returns:
            Tuple of (PIL Image, ImageDraw object)
        """
        image = Image.new('1', (self.width, self.height), 1)
        return image, ImageDraw.Draw(image)

    def _format_time_ago(self, timestamp: float, verbose: bool = False) -> str:
        """
        Convert timestamp to relative time string.

        Args:
            timestamp: Unix timestamp
            verbose: If True, use longer format ("Just now", "5 min ago")
                    If False, use short format ("now", "5m", "2h", "3d")

        Returns:
            Relative time string
        """
        if not timestamp:
            return ""
        age_secs = time.time() - timestamp
        if age_secs < 60:
            return "Just now" if verbose else "now"
        elif age_secs < 3600:
            mins = int(age_secs / 60)
            return f"{mins} min ago" if verbose else f"{mins}m"
        elif age_secs < 86400:
            hours = int(age_secs / 3600)
            return f"{hours} hr ago" if verbose else f"{hours}h"
        else:
            days = int(age_secs / 86400)
            return f"{days} days ago" if verbose else f"{days}d"

    def _draw_list_item(self, draw: ImageDraw.Draw, x: int, y: int,
                        text: str, selected: bool, item_height: int,
                        font=None, right_margin: int = None) -> None:
        """
        Draw a list item with optional selection highlight.

        This is the standard method for drawing selectable list items.
        Use this consistently throughout the codebase to avoid duplication.

        Args:
            draw: ImageDraw object
            x: X position for text
            y: Y position for text
            text: Text to display
            selected: Whether this item is selected (highlighted)
            item_height: Height of the item for highlight rectangle
            font: Font to use (defaults to font_small)
            right_margin: Right margin from screen edge (defaults to config value)
        """
        font = font or self.font_small
        right_margin = right_margin if right_margin is not None else config.LIST_RIGHT_MARGIN

        if selected:
            draw.rectangle(
                [(x - config.LIST_HIGHLIGHT_X_OFFSET, y - config.LIST_HIGHLIGHT_Y_OFFSET),
                 (self.width - right_margin, y + item_height - config.LIST_HIGHLIGHT_BOTTOM_OFFSET)],
                fill=0
            )
            draw.text((x, y), text, fill=1, font=font)
        else:
            draw.text((x, y), text, fill=0, font=font)

    def _wrap_text(self, draw: ImageDraw.Draw, text: str,
                   max_width: int, font) -> list:
        """
        Wrap text to fit within max_width.

        Args:
            draw: ImageDraw object (used for measuring text)
            text: Text to wrap
            max_width: Maximum width in pixels
            font: Font to use for measurement

        Returns:
            List of wrapped lines
        """
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)
        return lines

    def draw_status_screen(self, pet_sprite: Optional[Image.Image],
                          pet_name: str, stats: Dict[str, int],
                          age_display: str, quote: Optional[str] = None,
                          wifi_connected: bool = False, online_friends: int = 0,
                          unread_messages: int = 0) -> Image.Image:
        """
        Draw the main status screen with pet and stats

        Args:
            pet_sprite: PIL Image of pet sprite (100×100)
            pet_name: Pet's name
            stats: Dict with 'hunger', 'happiness', 'health', 'energy'
            age_display: Formatted age string (e.g., "5h" or "2d")
            quote: Optional quote to display over pet sprite
            wifi_connected: Whether WiFi server is running
            online_friends: Number of online friends
            unread_messages: Number of unread messages

        Returns:
            PIL Image of the complete screen
        """
        image, draw = self._create_canvas()

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

        # Draw header LAST so it renders on top of any oversized sprites
        self._draw_header(draw, pet_name, age_display, wifi_connected, online_friends, unread_messages)

        return image

    def draw_menu(self, menu_items: List[Dict[str, str]],
                  selected_index: int, title: str = "Menu",
                  pet_sprite: Optional[Image.Image] = None,
                  wifi_connected: bool = False, online_friends: int = 0,
                  unread_messages: int = 0) -> Image.Image:
        """
        Draw a menu screen with pet sprite on left

        Args:
            menu_items: List of menu items with 'label' and 'action'
            selected_index: Index of currently selected item
            title: Menu title
            pet_sprite: Optional pet sprite to display on left side
            wifi_connected: Whether WiFi server is running
            online_friends: Number of online friends
            unread_messages: Number of unread messages

        Returns:
            PIL Image of the menu screen
        """
        image, draw = self._create_canvas()

        # Draw header with title (use _draw_header for consistency with status icons)
        # Pass title as pet_name and empty age since menu doesn't show age
        self._draw_header(draw, title, "", wifi_connected, online_friends, unread_messages)

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
                       selected_char_index: int, title: str = "Enter Name:") -> Image.Image:
        """
        Draw text input screen for naming

        Args:
            current_text: Text entered so far
            char_pool: Available characters
            selected_char_index: Index of currently selected character
            title: Title to display at top

        Returns:
            PIL Image of the text input screen
        """
        image, draw = self._create_canvas()

        # Title
        draw.text((5, 2), title, fill=0, font=self.font_medium)
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

    def draw_keyboard(self, buffer: str, selected_index: int,
                      title: str = "") -> Image.Image:
        """
        Draw full-screen keyboard for text input

        Args:
            buffer: Text entered so far
            selected_index: Index of currently selected key (0-44)
            title: Optional title to display (e.g., "Enter Name:" or "To: Friend")

        Returns:
            PIL Image of the keyboard screen
        """
        image, draw = self._create_canvas()

        # 1. Draw text input line with cursor
        display_text = self._truncate_with_ellipsis(draw, buffer, max_width=240)
        draw.text((5, 2), display_text + "_", fill=0, font=self.font_medium)
        draw.line([(0, config.KEYBOARD_TEXT_LINE_HEIGHT + 2),
                   (self.width, config.KEYBOARD_TEXT_LINE_HEIGHT + 2)], fill=0)

        # 2. Draw rows 0-3 (10 keys each)
        for i in range(40):  # First 40 keys (rows 0-3)
            row = i // config.KEYBOARD_COLS
            col = i % config.KEYBOARD_COLS

            x = config.KEYBOARD_START_X + col * config.KEYBOARD_KEY_WIDTH
            y = config.KEYBOARD_START_Y + row * config.KEYBOARD_ROW_HEIGHT

            key_label = config.KEYBOARD_KEYS[i]
            self._draw_keyboard_key(draw, x, y,
                                   config.KEYBOARD_KEY_WIDTH - 2,
                                   config.KEYBOARD_KEY_HEIGHT,
                                   key_label,
                                   selected=(i == selected_index))

        # 3. Draw row 4 (5 control keys, wider)
        control_y = config.KEYBOARD_START_Y + 4 * config.KEYBOARD_ROW_HEIGHT + 4

        for i in range(config.KEYBOARD_CONTROL_COLS):
            idx = 40 + i
            x = config.KEYBOARD_START_X + i * config.KEYBOARD_CONTROL_WIDTH

            # Get display label for control keys
            key_label = config.KEYBOARD_KEY_LABELS.get(idx, config.KEYBOARD_KEYS[idx])
            self._draw_keyboard_key(draw, x, control_y,
                                   config.KEYBOARD_CONTROL_WIDTH - 4,
                                   config.KEYBOARD_CONTROL_HEIGHT,
                                   key_label,
                                   selected=(idx == selected_index))

        return image

    def _draw_keyboard_key(self, draw: ImageDraw.Draw, x: int, y: int,
                           width: int, height: int, label: str,
                           selected: bool = False):
        """
        Draw a single keyboard key

        Args:
            draw: ImageDraw object
            x: X position
            y: Y position
            width: Key width
            height: Key height
            label: Text to display on key
            selected: Whether this key is selected (inverted colors)
        """
        if selected:
            # Draw filled rectangle (black background)
            draw.rectangle([(x, y), (x + width, y + height)], fill=0)
            # Draw text in white (inverted)
            # Center the text in the key
            bbox = draw.textbbox((0, 0), label, font=self.font_small)
            text_width = bbox[2] - bbox[0]
            text_x = x + (width - text_width) // 2
            draw.text((text_x, y + 2), label, fill=1, font=self.font_small)
        else:
            # Draw text in black (normal)
            bbox = draw.textbbox((0, 0), label, font=self.font_small)
            text_width = bbox[2] - bbox[0]
            text_x = x + (width - text_width) // 2
            draw.text((text_x, y + 2), label, fill=0, font=self.font_small)

    def _truncate_with_ellipsis(self, draw: ImageDraw.Draw, buffer: str,
                                 max_width: int = 240) -> str:
        """
        Return buffer text, with ellipsis at start if too long.
        Shows the end of the message so user can see what they're typing.

        Args:
            draw: ImageDraw object (used for measuring text)
            buffer: Text to potentially truncate
            max_width: Maximum width in pixels

        Returns:
            Original buffer or truncated version with "..." prefix
        """
        if not buffer:
            return ""

        # Measure full text width
        bbox = draw.textbbox((0, 0), buffer, font=self.font_medium)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            return buffer

        # Need ellipsis - find how many trailing chars fit
        ellipsis = "..."
        ellipsis_bbox = draw.textbbox((0, 0), ellipsis, font=self.font_medium)
        ellipsis_width = ellipsis_bbox[2] - ellipsis_bbox[0]
        available = max_width - ellipsis_width

        # Iterate from end to find max chars that fit
        for i in range(1, len(buffer) + 1):
            test_text = buffer[-i:]
            test_bbox = draw.textbbox((0, 0), test_text, font=self.font_medium)
            test_width = test_bbox[2] - test_bbox[0]
            if test_width > available:
                # Previous iteration was the max that fits
                if i > 1:
                    return ellipsis + buffer[-(i-1):]
                else:
                    return ellipsis

        return ellipsis + buffer

    def draw_confirmation(self, message: str, selected: bool = True) -> Image.Image:
        """
        Draw a confirmation dialog

        Args:
            message: Confirmation message
            selected: True for "Yes" selected, False for "No"

        Returns:
            PIL Image of confirmation screen
        """
        image, draw = self._create_canvas()

        # Draw border
        draw.rectangle([(10, 20), (self.width - 10, self.height - 20)],
                      outline=0, width=2)

        # Draw message (word wrap if needed)
        max_width = self.width - 30
        lines = self._wrap_text(draw, message, max_width, self.font_small)
        y_offset = 30
        for line in lines:
            draw.text((20, y_offset), line, fill=0, font=self.font_small)
            y_offset += 12

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

    def draw_friends_list(self, friends: list, selected_index: int,
                          pet_sprite: Optional[Image.Image],
                          wifi_connected: bool = False,
                          online_friends: int = 0) -> Image.Image:
        """
        Draw friends list screen

        Args:
            friends: List of friend dictionaries with 'pet_name', 'online' keys
            selected_index: Currently selected friend index
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of friends list screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Friends", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw friends list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL
        item_height = config.LIST_ITEM_HEIGHT_LARGE

        # Build items list: friends + "Find Friends" option
        items = []
        for friend in friends:
            name = friend.get('pet_name', 'Unknown')
            online = friend.get('online', False)
            prefix = "+" if online else "o"  # + for online, o for offline
            items.append(f"{prefix} {name}")

        items.append("> Find Friends")
        items.append("< Back")

        # Draw visible items
        visible_items = config.VISIBLE_ITEMS_FRIENDS
        start_idx = max(0, selected_index - visible_items + 1)
        end_idx = min(len(items), start_idx + visible_items)

        for i in range(start_idx, end_idx):
            item_text = items[i]
            y_pos = y + (i - start_idx) * item_height
            self._draw_list_item(draw, x, y_pos, item_text,
                                i == selected_index, item_height)

        # Add hint at bottom when friend is selected
        if selected_index < len(friends):
            hint = "Press:msg Hold:options"
            hint_x = self.width - draw.textlength(hint, font=self.font_small) - 5
            draw.text((hint_x, self.height - 15), hint, font=self.font_small, fill=0)

        return image

    def draw_find_friends(self, devices: list, selected_index: int,
                          pet_sprite: Optional[Image.Image],
                          wifi_connected: bool = False,
                          online_friends: int = 0) -> Image.Image:
        """
        Draw find friends (device discovery) screen

        Args:
            devices: List of discovered device dictionaries
            selected_index: Currently selected device index
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of find friends screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Find Friends", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw devices list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL
        item_height = config.LIST_ITEM_HEIGHT_LARGE

        # Build items list: devices + Back option
        items = []
        for device in devices:
            # Extract pet name from device name (e.g., "Buddy_notagotchi" -> "Buddy")
            full_name = device.get('name', 'Unknown')
            suffix = f"_{config.DEVICE_ID_PREFIX}"
            if full_name.endswith(suffix):
                name = full_name[:-len(suffix)]
            else:
                name = full_name
            items.append(name)
        items.append("< Back")

        if len(devices) == 0:
            draw.text((x, y), "Scanning...", fill=0, font=self.font_small)
            draw.text((x, y + 20), "No devices found", fill=0, font=self.font_small)
            # Still show Back option
            y_pos = y + 50
            self._draw_list_item(draw, x, y_pos, "< Back",
                                selected_index == 0, item_height)
        else:
            # Draw item list (devices + Back)
            visible_items = 5
            start_idx = max(0, selected_index - visible_items + 1)
            end_idx = min(len(items), start_idx + visible_items)

            for i in range(start_idx, end_idx):
                item_text = items[i]
                y_pos = y + (i - start_idx) * item_height
                self._draw_list_item(draw, x, y_pos, item_text,
                                    i == selected_index, item_height)

            # Hint at bottom (only if not on Back)
            if selected_index < len(devices):
                draw.text((x, self.height - 15), "Press to add", fill=0, font=self.font_small)

        return image

    def draw_friend_requests(self, requests: list, selected_index: int,
                             pet_sprite: Optional[Image.Image],
                             wifi_connected: bool = False,
                             online_friends: int = 0) -> Image.Image:
        """
        Draw friend requests screen

        Args:
            requests: List of pending friend request dictionaries
            selected_index: Currently selected request index
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of friend requests screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Requests", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw requests list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL
        item_height = config.LIST_ITEM_HEIGHT_LARGE

        # Build items list: requests + Back option
        items = []
        for request in requests:
            name = request.get('pet_name', 'Unknown')
            items.append(name)
        items.append("< Back")

        if len(requests) == 0:
            draw.text((x, y), "No requests", fill=0, font=self.font_small)
            # Still show Back option
            y_pos = y + 30
            self._draw_list_item(draw, x, y_pos, "< Back",
                                selected_index == 0, item_height)
        else:
            # Draw count
            draw.text((x, y), f"Pending: {len(requests)}", fill=0, font=self.font_small)
            y += 15

            # Draw item list (requests + Back)
            visible_items = config.VISIBLE_ITEMS_REQUESTS
            start_idx = max(0, selected_index - visible_items + 1)
            end_idx = min(len(items), start_idx + visible_items)

            for i in range(start_idx, end_idx):
                item_text = items[i]
                y_pos = y + (i - start_idx) * item_height
                self._draw_list_item(draw, x, y_pos, item_text,
                                    i == selected_index, item_height)

            # Hint at bottom (only if not on Back)
            if selected_index < len(requests):
                draw.text((x, self.height - 15), "Press to accept", fill=0, font=self.font_small)

        return image

    def draw_inbox(self, messages: list, selected_index: int,
                   pet_sprite: Optional[Image.Image] = None,
                   wifi_connected: bool = False, online_friends: int = 0,
                   unread_messages: int = 0) -> Image.Image:
        """
        Draw inbox screen with message list

        Args:
            messages: List of message dictionaries with 'from_pet_name', 'content', 'timestamp', 'is_read'
            selected_index: Currently selected message index
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends
            unread_messages: Number of unread messages

        Returns:
            PIL Image of inbox screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Inbox", "", wifi_connected, online_friends, unread_messages)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw messages list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL

        # Define font for inbox items - change here to adjust size
        inbox_font = self.font_medium
        # Calculate item height from font (keeps highlight in sync with text)
        sample_bbox = draw.textbbox((0, 0), "Ag", font=inbox_font)
        item_height = (sample_bbox[3] - sample_bbox[1]) + 4  # font height + padding

        # Build items list: messages + Back option
        items = []
        for msg in messages:
            sender = msg.get('from_pet_name', 'Unknown')[:config.SENDER_NAME_MAX_LENGTH]
            content = msg.get('content', '')[:config.MESSAGE_PREVIEW_LENGTH]
            is_read = msg.get('is_read', False)
            # Format time ago
            time_str = self._format_time_ago(msg.get('received_at', 0))

            # Build single-line display: "* Sender (1h) - preview" or "  Sender (1h) - preview"
            line = sender
            if time_str:
                line += f" ({time_str})"
            line += " - " + (content if content else "...")
            # Prefix: "* " for unread, "  " for read (keeps alignment)
            line = ("* " if not is_read else "  ") + line
            items.append(line)

        if len(messages) == 0:
            draw.text((x, y), "No messages", fill=0, font=inbox_font)
            # Still show Back option
            y_pos = y + item_height * 2
            self._draw_list_item(draw, x, y_pos, "< Back",
                                selected_index == 0, item_height, inbox_font)
        else:
            # Draw message list - calculate visible items from available space
            available_height = config.STATUS_AREA_HEIGHT - 10
            visible_items = available_height // item_height
            # Account for Back option
            total_items = len(items) + 1  # +1 for Back
            start_idx = max(0, selected_index - visible_items + 1)
            end_idx = min(total_items, start_idx + visible_items)

            for i in range(start_idx, end_idx):
                y_pos = y + (i - start_idx) * item_height
                if i < len(items):
                    text = items[i]
                else:
                    text = "< Back"
                self._draw_list_item(draw, x, y_pos, text,
                                    i == selected_index, item_height, inbox_font)

        # Add hint at bottom when message is selected
        if selected_index < len(messages):
            hint = "Press:view Hold:delete"
            hint_x = self.width - draw.textlength(hint, font=self.font_small) - 5
            draw.text((hint_x, self.height - 15), hint, font=self.font_small, fill=0)

        return image

    def draw_message_detail(self, message: dict, pet_sprite: Optional[Image.Image] = None,
                            wifi_connected: bool = False, online_friends: int = 0,
                            unread_messages: int = 0) -> Image.Image:
        """
        Draw full message view

        Args:
            message: Message dictionary with 'from_pet_name', 'content', 'timestamp'
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends
            unread_messages: Number of unread messages

        Returns:
            PIL Image of message detail screen
        """
        image, draw = self._create_canvas()

        # Draw header with sender name
        sender = message.get('from_pet_name', 'Unknown')
        self._draw_header(draw, f"From: {sender}", "", wifi_connected, online_friends, unread_messages)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw message content on right side
        x = config.STATUS_AREA_X + 5
        y = config.STATUS_AREA_Y + 5

        # Format time
        time_str = self._format_time_ago(message.get('timestamp', 0), verbose=True)
        if time_str:
            draw.text((x, y), time_str, fill=0, font=self.font_medium)
            y += 18

        # Draw message content (word-wrapped)
        content = message.get('content', '')
        max_width = config.STATUS_AREA_WIDTH - 10
        lines = self._wrap_text(draw, content, max_width, self.font_emoji)

        # Draw wrapped lines
        for line in lines[:4]:  # Max 4 lines with larger font
            draw.text((x, y), line, fill=0, font=self.font_emoji)
            y += 16

        # Hint at bottom - updated to show long-press option
        hint = "Press:back Hold:options"
        hint_x = self.width - draw.textlength(hint, font=self.font_small) - 5
        draw.text((hint_x, self.height - 15), hint, font=self.font_small, fill=0)

        return image

    def draw_message_options(self, selected_index: int = 0) -> Image.Image:
        """
        Draw message options menu

        Args:
            selected_index: Index of selected menu item

        Returns:
            PIL Image of message options screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Message Options", "")

        # Draw menu items
        menu_items = config.MESSAGE_OPTIONS_MENU
        y_offset = config.HEADER_LINE_Y + 5

        for i, item in enumerate(menu_items):
            # Highlight selected item
            if i == selected_index:
                draw.rectangle([
                    (2, y_offset),
                    (self.width - 2, y_offset + config.MENU_ITEM_HEIGHT)
                ], outline=0, width=1)

            # Draw label
            draw.text((5, y_offset + 2), item['label'], font=self.font_small, fill=0)
            y_offset += config.MENU_ITEM_HEIGHT + 2

        return image

    def draw_friend_options(self, friend_name: str, selected_index: int = 0) -> Image.Image:
        """
        Draw friend options menu

        Args:
            friend_name: Name of friend being managed
            selected_index: Index of selected menu item

        Returns:
            PIL Image of friend options screen
        """
        image, draw = self._create_canvas()

        # Draw header with friend name (truncate if too long)
        title = f"Options: {friend_name}"[:20]
        self._draw_header(draw, title, "")

        # Draw menu items
        menu_items = config.FRIEND_OPTIONS_MENU
        y_offset = config.HEADER_LINE_Y + 5

        for i, item in enumerate(menu_items):
            # Highlight selected item
            if i == selected_index:
                draw.rectangle([
                    (2, y_offset),
                    (self.width - 2, y_offset + config.MENU_ITEM_HEIGHT)
                ], outline=0, width=1)

            # Draw label
            draw.text((5, y_offset + 2), item['label'], font=self.font_small, fill=0)
            y_offset += config.MENU_ITEM_HEIGHT + 2

        return image

    def draw_status_message(self, message: str, submessage: str = "") -> Image.Image:
        """
        Draw a centered status message (toast-style feedback)

        Args:
            message: Main message to display
            submessage: Optional smaller text below main message

        Returns:
            PIL Image of the status message screen
        """
        image, draw = self._create_canvas()

        # Draw centered message box
        box_margin = 20
        box_top = 35
        box_bottom = 95
        draw.rectangle([(box_margin, box_top), (self.width - box_margin, box_bottom)],
                       outline=0, width=2)

        # Main message (centered)
        bbox = draw.textbbox((0, 0), message, font=self.font_medium)
        text_width = bbox[2] - bbox[0]
        text_x = (self.width - text_width) // 2
        draw.text((text_x, box_top + 12), message, fill=0, font=self.font_medium)

        # Submessage (centered, smaller)
        if submessage:
            bbox = draw.textbbox((0, 0), submessage, font=self.font_small)
            text_width = bbox[2] - bbox[0]
            text_x = (self.width - text_width) // 2
            draw.text((text_x, box_top + 35), submessage, fill=0, font=self.font_small)

        return image

    def draw_emoji_category_select(self, categories: list, selected_index: int,
                                   friend_name: str, pet_sprite: Optional[Image.Image],
                                   wifi_connected: bool = False,
                                   online_friends: int = 0) -> Image.Image:
        """
        Draw emoji category selection screen

        Args:
            categories: List of (key, display_name) tuples
            selected_index: Currently selected category index
            friend_name: Name of friend to send to
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of category select screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Emoji", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw category list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL
        item_height = config.LIST_ITEM_HEIGHT_MEDIUM

        # Add Back option to categories
        items = [(None, "< Back")] + list(categories)

        visible_items = config.VISIBLE_ITEMS_EMOJI_CATEGORY
        start_idx = max(0, selected_index - visible_items + 1)
        end_idx = min(len(items), start_idx + visible_items)

        for i in range(start_idx, end_idx):
            _, display_name = items[i]
            y_pos = y + (i - start_idx) * item_height
            self._draw_list_item(draw, x, y_pos, display_name,
                                i == selected_index, item_height)

        # To: friend name
        draw.text((x, self.height - 15), f"To: {friend_name}", fill=0, font=self.font_small)

        return image

    def draw_emoji_select(self, emojis: list, selected_index: int,
                          friend_name: str, pet_sprite: Optional[Image.Image],
                          wifi_connected: bool = False,
                          online_friends: int = 0) -> Image.Image:
        """
        Draw emoji selection screen

        Args:
            emojis: List of emoji strings
            selected_index: Currently selected emoji index
            friend_name: Name of friend to send to
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of emoji select screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Emoji", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw emoji selector on right side
        x = config.STATUS_AREA_X + 5
        y = config.STATUS_AREA_Y + 5

        # Current emoji (large)
        if len(emojis) > 0:
            selected_emoji = emojis[selected_index]
            draw.rectangle([(x + 10, y), (x + 60, y + 50)], outline=0, width=2)
            # Use emoji font for proper Unicode emoji rendering
            draw.text((x + 18, y + 8), selected_emoji, fill=0, font=self.font_emoji)

            # Show index
            draw.text((x + 70, y + 15), f"{selected_index + 1}/{len(emojis)}", fill=0, font=self.font_small)

        # To: friend name
        draw.text((x, y + 70), f"To: {friend_name}", fill=0, font=self.font_small)

        # Hint
        draw.text((x, self.height - 15), "Press:send Hold:back", fill=0, font=self.font_small)

        return image

    def draw_preset_category_select(self, categories: list, selected_index: int,
                                    friend_name: str, pet_sprite: Optional[Image.Image],
                                    wifi_connected: bool = False,
                                    online_friends: int = 0) -> Image.Image:
        """
        Draw preset message category selection screen

        Args:
            categories: List of (key, display_name) tuples
            selected_index: Currently selected category index
            friend_name: Name of friend to send to
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of category select screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Quick Msg", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw category list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL
        item_height = config.LIST_ITEM_HEIGHT_SMALL

        # Add Back option to categories
        items = [(None, "< Back")] + list(categories)

        visible_items = config.VISIBLE_ITEMS_PRESET_CATEGORY
        start_idx = max(0, selected_index - visible_items + 1)
        end_idx = min(len(items), start_idx + visible_items)

        for i in range(start_idx, end_idx):
            _, display_name = items[i]
            y_pos = y + (i - start_idx) * item_height
            self._draw_list_item(draw, x, y_pos, display_name,
                                i == selected_index, item_height)

        # To: friend name
        draw.text((x, self.height - 15), f"To: {friend_name}", fill=0, font=self.font_small)

        return image

    def draw_preset_select(self, presets: list, selected_index: int,
                           friend_name: str, pet_sprite: Optional[Image.Image],
                           wifi_connected: bool = False,
                           online_friends: int = 0) -> Image.Image:
        """
        Draw preset message selection screen

        Args:
            presets: List of preset message strings
            selected_index: Currently selected preset index
            friend_name: Name of friend to send to
            pet_sprite: Pet sprite image
            wifi_connected: WiFi connection status
            online_friends: Number of online friends

        Returns:
            PIL Image of preset select screen
        """
        image, draw = self._create_canvas()

        # Draw header
        self._draw_header(draw, "Quick Msg", "", wifi_connected, online_friends)

        # Draw pet sprite on left (if available)
        if pet_sprite:
            image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

        # Draw preset list on right side
        x = config.STATUS_AREA_X + config.UI_PADDING_MEDIUM
        y = config.STATUS_AREA_Y + config.UI_PADDING_SMALL
        item_height = config.LIST_ITEM_HEIGHT_MEDIUM

        # Draw preset list
        visible_items = config.VISIBLE_ITEMS_PRESETS
        start_idx = max(0, selected_index - visible_items + 1)
        end_idx = min(len(presets), start_idx + visible_items)

        for i in range(start_idx, end_idx):
            preset = presets[i]
            # Truncate if too long
            if len(preset) > config.PRESET_MAX_DISPLAY_LENGTH:
                preset = preset[:config.PRESET_MAX_DISPLAY_LENGTH - 2] + ".."
            y_pos = y + (i - start_idx) * item_height
            self._draw_list_item(draw, x, y_pos, preset,
                                i == selected_index, item_height)

        # To: friend name
        draw.text((x, self.height - 28), f"To: {friend_name}", fill=0, font=self.font_small)

        # Hint
        draw.text((x, self.height - 15), "Press:send Hold:back", fill=0, font=self.font_small)

        return image

    # =========================================================================
    # GAME SCREENS
    # =========================================================================

    def draw_game_select(self, items: list, selected_index: int,
                         opponent_name: str) -> Image.Image:
        """
        Draw game selection screen

        Args:
            items: List of game menu items
            selected_index: Currently selected game index
            opponent_name: Name of opponent to play against

        Returns:
            PIL Image of game select screen
        """
        image, draw = self._create_canvas()

        # Draw header with opponent name
        title = f"Play with: {opponent_name}"[:25]
        self._draw_header(draw, title, "")

        # Calculate visible area
        y_start = config.HEADER_LINE_Y + 5
        item_height = config.MENU_ITEM_HEIGHT + 2
        available_height = self.height - y_start - 5  # Leave margin at bottom
        visible_items = available_height // item_height

        # Calculate which items to show (scrolling)
        start_idx = max(0, selected_index - visible_items + 1)
        end_idx = min(len(items), start_idx + visible_items)

        # Draw visible menu items
        for i in range(start_idx, end_idx):
            item = items[i]
            y_pos = y_start + (i - start_idx) * item_height

            # Highlight selected item
            if i == selected_index:
                draw.rectangle([
                    (2, y_pos),
                    (self.width - 2, y_pos + config.MENU_ITEM_HEIGHT)
                ], outline=0, width=1)

            # Draw label
            draw.text((5, y_pos + 2), item['label'], font=self.font_small, fill=0)

        # Draw scroll indicators if needed
        if start_idx > 0:
            draw.text((self.width - 15, y_start), "^", font=self.font_small, fill=0)
        if end_idx < len(items):
            draw.text((self.width - 15, self.height - 12), "v", font=self.font_small, fill=0)

        return image

    def draw_game_waiting(self, opponent_name: str, game_type: str) -> Image.Image:
        """
        Draw game waiting screen (waiting for opponent to accept)

        Args:
            opponent_name: Name of opponent
            game_type: Type of game being proposed

        Returns:
            PIL Image of waiting screen
        """
        image, draw = self._create_canvas()

        # Get game display name
        game_config = config.GAME_TYPES.get(game_type, {})
        game_name = game_config.get('name', game_type.replace('_', ' ').title())

        # Header
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)], fill=0)
        draw.text((2, 1), game_name, fill=1, font=self.font_small)

        # Centered waiting message
        msg = f"Waiting for {opponent_name}..."
        bbox = draw.textbbox((0, 0), msg, font=self.font_medium)
        text_width = bbox[2] - bbox[0]
        text_x = (self.width - text_width) // 2
        draw.text((text_x, 45), msg, fill=0, font=self.font_medium)

        # Animated dots indicator (static for now)
        dots = "..."
        bbox = draw.textbbox((0, 0), dots, font=self.font_large)
        dot_width = bbox[2] - bbox[0]
        dot_x = (self.width - dot_width) // 2
        draw.text((dot_x, 65), dots, fill=0, font=self.font_large)

        # Cancel hint
        hint = "Press to cancel"
        bbox = draw.textbbox((0, 0), hint, font=self.font_small)
        hint_width = bbox[2] - bbox[0]
        hint_x = (self.width - hint_width) // 2
        draw.text((hint_x, self.height - 15), hint, fill=0, font=self.font_small)

        return image

    def draw_game_rps(self, display_state: dict, choice_index: int,
                      opponent_name: str) -> Image.Image:
        """
        Draw Rock-Paper-Scissors game screen

        Args:
            display_state: Game display state from RPS.get_display_state()
            choice_index: Currently selected choice (0=rock, 1=paper, 2=scissors)
            opponent_name: Opponent's name

        Returns:
            PIL Image of RPS game screen
        """
        image, draw = self._create_canvas()

        # Header with turn status
        if display_state.get('waiting_for_opponent'):
            status = "Waiting..."
        elif display_state.get('waiting_for_me'):
            status = "Your turn!"
        else:
            status = "Round over"

        # Draw header
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)], fill=0)
        header_text = f"vs {opponent_name} - {status}"[:35]
        draw.text((2, 1), header_text, fill=1, font=self.font_small)

        choices = ['rock', 'paper', 'scissors']
        symbols = {'rock': 'R', 'paper': 'P', 'scissors': 'S'}
        labels = {'rock': 'Rock', 'paper': 'Paper', 'scissors': 'Scissors'}

        if display_state.get('round_complete'):
            # Show result
            my_choice = display_state.get('my_choice')
            opp_choice = display_state.get('opponent_choice')
            result = display_state.get('result')

            # Result message
            if result == 'win':
                result_msg = "You Win!"
            elif result == 'lose':
                result_msg = "You Lose!"
            else:
                result_msg = "Draw!"

            bbox = draw.textbbox((0, 0), result_msg, font=self.font_large)
            msg_width = bbox[2] - bbox[0]
            draw.text(((self.width - msg_width) // 2, 25), result_msg, fill=0, font=self.font_large)

            # Show choices
            my_label = f"You: {labels.get(my_choice, '?')}"
            opp_label = f"{opponent_name}: {labels.get(opp_choice, '?')}"

            draw.text((20, 55), my_label, fill=0, font=self.font_medium)
            draw.text((20, 75), opp_label, fill=0, font=self.font_medium)

            # Hint
            draw.text((20, self.height - 15), "Press to continue", fill=0, font=self.font_small)

        elif display_state.get('waiting_for_opponent'):
            # We chose, waiting for opponent
            my_choice = display_state.get('my_choice')
            msg = f"You chose: {labels.get(my_choice, '?')}"
            bbox = draw.textbbox((0, 0), msg, font=self.font_medium)
            draw.text(((self.width - bbox[2] + bbox[0]) // 2, 40), msg, fill=0, font=self.font_medium)

            wait_msg = "Waiting for opponent..."
            bbox = draw.textbbox((0, 0), wait_msg, font=self.font_small)
            draw.text(((self.width - bbox[2] + bbox[0]) // 2, 70), wait_msg, fill=0, font=self.font_small)

        else:
            # Selection phase
            msg = "Make your choice!"
            bbox = draw.textbbox((0, 0), msg, font=self.font_medium)
            draw.text(((self.width - bbox[2] + bbox[0]) // 2, 20), msg, fill=0, font=self.font_medium)

            # Draw choices horizontally
            choice_width = 70
            start_x = (self.width - 3 * choice_width) // 2

            for i, choice in enumerate(choices):
                x = start_x + i * choice_width
                y = 45

                # Highlight selected
                if i == choice_index:
                    draw.rectangle([(x, y), (x + 60, y + 50)], outline=0, width=2)

                # Symbol
                symbol = f"({symbols[choice]})"
                bbox = draw.textbbox((0, 0), symbol, font=self.font_large)
                sym_x = x + (60 - bbox[2] + bbox[0]) // 2
                draw.text((sym_x, y + 5), symbol, fill=0, font=self.font_large)

                # Label
                label = labels[choice]
                bbox = draw.textbbox((0, 0), label, font=self.font_small)
                lbl_x = x + (60 - bbox[2] + bbox[0]) // 2
                draw.text((lbl_x, y + 35), label, fill=0, font=self.font_small)

            # Hint
            draw.text((5, self.height - 15), "Press:select  Hold:forfeit", fill=0, font=self.font_small)

        return image

    def draw_game_result(self, display_state: dict, opponent_name: str,
                         game_type: str) -> Image.Image:
        """
        Draw game result screen

        Args:
            display_state: Game display state
            opponent_name: Opponent's name
            game_type: Type of game

        Returns:
            PIL Image of result screen
        """
        image, draw = self._create_canvas()

        # Get game display name
        game_config = config.GAME_TYPES.get(game_type, {})
        game_name = game_config.get('name', game_type.replace('_', ' ').title())

        # Header
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)], fill=0)
        draw.text((2, 1), game_name, fill=1, font=self.font_small)

        # Result
        result = display_state.get('result')
        if result == 'win':
            result_msg = "You Win!"
            emoji = ":D"
        elif result == 'lose':
            result_msg = "You Lose"
            emoji = ":("
        else:
            result_msg = "Draw!"
            emoji = ":|"

        # Big result message
        bbox = draw.textbbox((0, 0), result_msg, font=self.font_large)
        msg_width = bbox[2] - bbox[0]
        draw.text(((self.width - msg_width) // 2, 35), result_msg, fill=0, font=self.font_large)

        # Emoji
        bbox = draw.textbbox((0, 0), emoji, font=self.font_large)
        emoji_width = bbox[2] - bbox[0]
        draw.text(((self.width - emoji_width) // 2, 60), emoji, fill=0, font=self.font_large)

        # Opponent name
        vs_msg = f"vs {opponent_name}"
        bbox = draw.textbbox((0, 0), vs_msg, font=self.font_small)
        vs_width = bbox[2] - bbox[0]
        draw.text(((self.width - vs_width) // 2, 85), vs_msg, fill=0, font=self.font_small)

        # Hint
        hint = "Press to continue"
        bbox = draw.textbbox((0, 0), hint, font=self.font_small)
        hint_width = bbox[2] - bbox[0]
        draw.text(((self.width - hint_width) // 2, self.height - 15), hint, fill=0, font=self.font_small)

        return image

    def draw_game_invite(self, from_name: str, game_type: str) -> Image.Image:
        """
        Draw game invite confirmation screen

        Args:
            from_name: Name of person sending invite
            game_type: Type of game being proposed

        Returns:
            PIL Image of invite screen
        """
        image, draw = self._create_canvas()

        # Get game display name
        game_config = config.GAME_TYPES.get(game_type, {})
        game_name = game_config.get('name', game_type.replace('_', ' ').title())

        # Header
        draw.rectangle([(0, 0), (self.width, config.HEADER_HEIGHT)], fill=0)
        draw.text((2, 1), "Game Invite!", fill=1, font=self.font_small)

        # Message
        msg1 = f"{from_name} wants to play"
        msg2 = game_name

        bbox = draw.textbbox((0, 0), msg1, font=self.font_medium)
        draw.text(((self.width - bbox[2] + bbox[0]) // 2, 30), msg1, fill=0, font=self.font_medium)

        bbox = draw.textbbox((0, 0), msg2, font=self.font_medium)
        draw.text(((self.width - bbox[2] + bbox[0]) // 2, 50), msg2, fill=0, font=self.font_medium)

        # Accept/Decline buttons
        accept_text = "[Yes]"
        decline_text = "[No]"

        # Draw both options
        draw.text((60, 80), accept_text, fill=0, font=self.font_medium)
        draw.text((150, 80), decline_text, fill=0, font=self.font_medium)

        # Hint
        draw.text((5, self.height - 15), "Turn to select, Press to confirm", fill=0, font=self.font_small)

        return image

    def _draw_header(self, draw: ImageDraw.Draw, pet_name: str, age: str,
                     wifi_connected: bool = False, online_friends: int = 0,
                     unread_messages: int = 0):
        """Draw header with pet name, age, wifi status, friends count, mail, and battery"""
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
        age_text_width = bbox[2] - bbox[0]
        age_x = battery_x - age_text_width - 4  # 4px gap between age and battery
        draw.text((age_x, 1), age_text, fill=1, font=self.font_small)

        # Friends count with heart icon (left of age)
        friends_text = str(online_friends)
        bbox = draw.textbbox((0, 0), friends_text, font=self.font_small)
        friends_text_width = bbox[2] - bbox[0]
        header_icon_size = 10

        # Position: icon then text, to left of age
        friends_text_x = age_x - friends_text_width - 4  # 4px gap from age
        friends_icon_x = friends_text_x - header_icon_size - 1  # 1px gap between icon and text

        # Draw friends icon (heart) - need to invert for white-on-black header
        if self.icon_friends:
            from PIL import ImageOps
            icon = self.icon_friends.resize((header_icon_size, header_icon_size), Image.Resampling.NEAREST)
            # Invert colors for header (black bg needs white icon)
            icon = ImageOps.invert(icon.convert('L')).convert('1')
            # Create a temporary image to paste the icon
            # We can't paste directly onto draw, need to work with the image
            pass  # Will handle this via draw operations instead

        # Draw heart shape manually for header (simpler and works with draw)
        heart_x = friends_icon_x
        heart_y = 2
        # Simple small heart: two circles and triangle
        draw.ellipse([(heart_x, heart_y + 1), (heart_x + 4, heart_y + 5)], fill=1)
        draw.ellipse([(heart_x + 4, heart_y + 1), (heart_x + 8, heart_y + 5)], fill=1)
        draw.polygon([(heart_x, heart_y + 4), (heart_x + 8, heart_y + 4), (heart_x + 4, heart_y + 9)], fill=1)

        # Draw friends count text
        draw.text((friends_text_x, 1), friends_text, fill=1, font=self.font_small)

        # WiFi icon (left of friends)
        wifi_x = friends_icon_x - header_icon_size - 4  # 4px gap from friends icon

        # Draw WiFi icon manually for header
        if wifi_connected:
            # WiFi on - three arcs and dot
            draw.arc([(wifi_x, 1), (wifi_x + 9, 10)], start=220, end=320, fill=1, width=1)
            draw.arc([(wifi_x + 2, 3), (wifi_x + 7, 8)], start=220, end=320, fill=1, width=1)
            draw.ellipse([(wifi_x + 3, 7), (wifi_x + 5, 9)], fill=1)
        else:
            # WiFi off - arcs with X
            draw.arc([(wifi_x, 1), (wifi_x + 9, 10)], start=220, end=320, fill=1, width=1)
            draw.arc([(wifi_x + 2, 3), (wifi_x + 7, 8)], start=220, end=320, fill=1, width=1)
            draw.ellipse([(wifi_x + 3, 7), (wifi_x + 5, 9)], fill=1)
            # X overlay
            draw.line([(wifi_x, 1), (wifi_x + 9, 10)], fill=1, width=1)
            draw.line([(wifi_x + 9, 1), (wifi_x, 10)], fill=1, width=1)

        # Mail icon with unread count (left of WiFi)
        if unread_messages > 0:
            mail_text = str(unread_messages)
            bbox = draw.textbbox((0, 0), mail_text, font=self.font_small)
            mail_text_width = bbox[2] - bbox[0]

            # Position: icon then text, to left of WiFi
            mail_text_x = wifi_x - mail_text_width - 4  # 4px gap from WiFi
            mail_icon_x = mail_text_x - 10 - 1  # 10px icon, 1px gap

            # Draw envelope shape (8x6 pixels)
            env_x, env_y = mail_icon_x, 3
            draw.rectangle([(env_x, env_y), (env_x + 8, env_y + 6)], outline=1)
            # Envelope flap (V shape)
            draw.line([(env_x, env_y), (env_x + 4, env_y + 3)], fill=1)
            draw.line([(env_x + 4, env_y + 3), (env_x + 8, env_y)], fill=1)

            # Draw unread count text
            draw.text((mail_text_x, 1), mail_text, fill=1, font=self.font_small)

    def _get_battery_level(self) -> Optional[int]:
        """
        Get battery level from INA219 I2C battery monitor (0-100)

        Returns:
            Battery percentage (0-100) or None if not available
        """
        try:
            from ina219 import INA219
            logger.debug("INA219 library imported successfully")

            # INA219 configuration (matches your test code)
            SHUNT_OHMS = 0.1
            logger.debug(f"Connecting to INA219 (bus=1, address=0x43, shunt={SHUNT_OHMS} ohms)")
            ina = INA219(SHUNT_OHMS, busnum=1, address=0x43)
            ina.configure()
            logger.debug("INA219 configured successfully")

            # Calculate percentage based on voltage (3V to 4.2V range for LiPo)
            voltage = ina.voltage()
            logger.debug(f"Battery voltage read: {voltage:.3f}V")

            percent = (voltage - 3.0) / 1.2 * 100
            logger.debug(f"Battery percentage (raw): {percent:.1f}%")

            # Clamp to 0-100 range
            if percent > 100:
                percent = 100
            if percent < 0:
                percent = 0

            logger.debug(f"Battery final percentage: {int(percent)}%")
            return int(percent)

        except ImportError as e:
            # ina219 library not installed
            logger.debug(f"INA219 library not available: {e}")
            return None
        except Exception as e:
            # INA219 not connected or I2C error
            logger.debug(f"Error reading from INA219: {type(e).__name__}: {e}")
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
            logger.debug("Simulation mode: Would display image")
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
                    logger.debug("Performing full refresh")
                    self.epd.init()
                    self.epd.display(buffer)
                    self.last_full_refresh_time = current_time
                else:
                    # Not enough time has passed, do partial instead
                    time_remaining = config.FULL_REFRESH_MIN_INTERVAL - time_since_last_full
                    logger.debug(f"Full refresh requested but {time_since_last_full:.1f}s elapsed, doing partial refresh")
                    self.epd.displayPartial(buffer)
            else:
                # Normal partial refresh (no logging to reduce console noise)
                self.epd.displayPartial(buffer)

        except Exception as e:
            logger.error(f"Error updating display: {e}")

    def clear_display(self):
        """Clear the display to white"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.init()
                self.epd.Clear()
                self.last_full_refresh_time = time.time()  # Reset timestamp after full clear
            except Exception as e:
                logger.error(f"Error clearing display: {e}")

    def sleep(self):
        """Put display into sleep mode"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.sleep()
                logger.info("Display entering sleep mode")
            except Exception as e:
                logger.error(f"Error putting display to sleep: {e}")

    def close(self):
        """Clean up display resources"""
        if not self.simulation_mode and self.epd:
            try:
                self.epd.sleep()
                logger.info("Display closed")
            except Exception as e:
                logger.error(f"Error closing display: {e}")
