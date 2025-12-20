"""
Not-A-Gotchi Configuration Module

Central configuration for all hardware, display, and game logic constants.
"""

import os

# ============================================================================
# PROJECT INFO
# ============================================================================
PROJECT_NAME = "Not-A-Gotchi"
VERSION = "0.1.0"

# ============================================================================
# FILE PATHS
# ============================================================================
# Get the project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")
SPRITES_DIR = os.path.join(RESOURCES_DIR, "sprites")
QUOTES_FILE = os.path.join(RESOURCES_DIR, "quotes.json")
DATA_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "data")
DATABASE_PATH = os.path.join(DATA_DIR, "not-a-gotchi.db")

# ============================================================================
# GPIO PIN ASSIGNMENTS
# ============================================================================
# Rotary Encoder Pins
ENCODER_CLK_PIN = 23   # Pin 16 - Clock signal
ENCODER_DT_PIN = 22    # Pin 15 - Data signal
ENCODER_SW_PIN = 27    # Pin 13 - Switch/button

# Display SPI Pins (used by Waveshare library)
DISPLAY_RST_PIN = 17
DISPLAY_DC_PIN = 25
DISPLAY_CS_PIN = 8
DISPLAY_BUSY_PIN = 24

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================
# Display Hardware
DISPLAY_WIDTH = 250    # Landscape orientation
DISPLAY_HEIGHT = 122   # Landscape orientation
DISPLAY_ROTATION = 90  # Degrees

# Display Layout (Landscape: 250×122)
HEADER_HEIGHT = 14     # Top header for time/battery

# Pet sprite area (left side, below header)
PET_SPRITE_X = 0
PET_SPRITE_Y = HEADER_HEIGHT  # Derived from header height
PET_SPRITE_WIDTH = 100
PET_SPRITE_HEIGHT = 100

# Status/menu area (right side, below header)
STATUS_AREA_X = 100
STATUS_AREA_Y = HEADER_HEIGHT  # Derived from header height
STATUS_AREA_WIDTH = 150
STATUS_AREA_HEIGHT = DISPLAY_HEIGHT - HEADER_HEIGHT  # Derived: 122 - 14 = 108

# Display Refresh Settings
PARTIAL_REFRESH_INTERVAL = 1    # Seconds between partial refreshes
FULL_REFRESH_MIN_INTERVAL = 30  # Minimum seconds between full refreshes (on user action)
DISPLAY_UPDATE_RATE = 1.0       # Seconds between display updates

# Quote Display Settings
QUOTE_ROTATION_INTERVAL = 10   # Seconds between quote changes
QUOTE_BOX_Y = 76               # Y position (lower portion of 100px pet sprite)
QUOTE_BOX_HEIGHT = 24          # Height of quote box area
QUOTE_BOX_PADDING = 3          # Padding inside quote box

# ============================================================================
# SPRITE CONFIGURATION
# ============================================================================
SPRITE_SIZE = (100, 100)  # Width, Height
SPRITE_FORMAT = "1"        # 1-bit (black & white)

# Emotion Sprite File Names
EMOTION_SPRITES = {
    "happy": "happy.bmp",
    "sad": "sad.bmp",
    "hungry": "hungry.bmp",
    "sick": "sick.bmp",
    "sleeping": "sleeping.bmp",
    "tired": "tired.bmp",
    "excited": "excited.bmp",
    "content": "content.bmp",
    "dead": "dead.bmp"
}

# Stage Sprite File Names
STAGE_SPRITES = {
    0: "egg.bmp",      # Egg stage
    1: "baby.bmp",     # Baby stage
    2: "child.bmp",    # Child stage
    3: "teen.bmp",     # Teen stage
    4: "adult.bmp"     # Adult stage
}

# ============================================================================
# PET STAT CONFIGURATION
# ============================================================================
# Stat Ranges
STAT_MIN = 0
STAT_MAX = 100

# Initial Stats (for new pet)
INITIAL_HUNGER = 50
INITIAL_HAPPINESS = 75
INITIAL_HEALTH = 100
INITIAL_ENERGY = 100

# Stat Degradation Rates (per minute)
HUNGER_INCREASE_RATE = 1.0     # +1 hunger per minute
HAPPINESS_DECREASE_RATE = 0.5  # -0.5 happiness per minute
ENERGY_DECREASE_RATE = 0.3     # -0.3 energy per minute (base rate)

# Health Regeneration/Degradation
HEALTH_REGEN_THRESHOLD_HUNGER = 50    # Hunger must be < this to regen
HEALTH_REGEN_THRESHOLD_HAPPINESS = 50  # Happiness must be > this to regen
HEALTH_REGEN_RATE = 0.5               # +0.5 health per minute when conditions met

HEALTH_DEGRADE_THRESHOLD_HUNGER = 80   # Hunger > this causes health loss
HEALTH_DEGRADE_THRESHOLD_HAPPINESS = 20 # Happiness < this causes health loss
HEALTH_DEGRADE_RATE = 0.5              # -0.5 health per minute when conditions met

# Energy Degradation Modifiers
ENERGY_LOW_FULLNESS_THRESHOLD = 30     # Fullness < this increases energy drain
ENERGY_LOW_FULLNESS_MULTIPLIER = 2.0   # Energy drains 2x faster when hungry
ENERGY_RESTORE_FROM_SLEEP = 50         # +50 energy when sleeping

# Maximum degradation time (for power-loss recovery)
MAX_DEGRADATION_HOURS = 8  # Cap stat changes to this many hours max

# ============================================================================
# CARE ACTION EFFECTS
# ============================================================================
# Each action modifies stats by these amounts
CARE_ACTIONS = {
    "feed": {
        "hunger": -30,      # Reduces hunger
        "happiness": +5,    # Small happiness boost
        "health": 0,
        "energy": +5        # Small energy boost from eating
    },
    "play": {
        "hunger": +5,       # Makes pet slightly more hungry
        "happiness": +20,   # Significant happiness boost
        "health": 0,
        "energy": -10       # Playing uses energy
    },
    "clean": {
        "hunger": 0,
        "happiness": +5,    # Small happiness boost
        "health": +10,      # Improves health
        "energy": 0
    },
    "sleep": {
        "hunger": +10,      # Gets hungrier while sleeping
        "happiness": 0,
        "health": +15,      # Significant health boost
        "energy": +50       # Significant energy restore
    }
}

# ============================================================================
# EMOTION MAPPING
# ============================================================================
# Thresholds for determining pet's current emotion based on stats
# Evaluated in order - first match wins
# Lambda parameters: h=hunger, hp=happiness, ht=health, e=energy
EMOTION_RULES = [
    # Critical states (checked first)
    {"emotion": "dead", "condition": lambda h, hp, ht, e: ht <= 0},
    {"emotion": "sick", "condition": lambda h, hp, ht, e: ht < 30},

    # Needs-based emotions
    {"emotion": "hungry", "condition": lambda h, hp, ht, e: h > 70},
    {"emotion": "tired", "condition": lambda h, hp, ht, e: e < 30},
    {"emotion": "sad", "condition": lambda h, hp, ht, e: hp < 30},

    # Positive emotions
    {"emotion": "excited", "condition": lambda h, hp, ht, e: hp > 80 and h < 30},
    {"emotion": "content", "condition": lambda h, hp, ht, e: h < 50 and hp > 50 and ht > 70},

    # Default
    {"emotion": "happy", "condition": lambda h, hp, ht, e: True}  # Default
]

# ============================================================================
# LIFECYCLE / EVOLUTION CONFIGURATION
# ============================================================================
# Environment-based configuration
# Set NOTAGOTCHI_ENV=test for faster evolution (testing)
# Set NOTAGOTCHI_ENV=production for realistic evolution times
ENVIRONMENT = os.getenv('NOTAGOTCHI_ENV', 'test')  # Default to test for development

# Age thresholds for evolution (in seconds)
_STAGE_THRESHOLDS_PRODUCTION = {
    0: 0,              # Egg: immediate
    1: 86400,          # Baby: 1 day
    2: 259200,         # Child: 3 days
    3: 604800,         # Teen: 7 days
    4: 1209600         # Adult: 14 days
}

_STAGE_THRESHOLDS_TEST = {
    0: 0,              # Egg: immediate
    1: 300,            # Baby: 5 minutes
    2: 3600,           # Child: 1 hour
    3: 86400,          # Teen: 1 day
    4: 259200          # Adult: 3 days
}

STAGE_THRESHOLDS = _STAGE_THRESHOLDS_PRODUCTION if ENVIRONMENT == 'production' else _STAGE_THRESHOLDS_TEST

# Display evolution for this many seconds after stage change
EVOLUTION_DISPLAY_DURATION = 5  # Seconds

# Display sleeping emotion for this many seconds after sleep action
SLEEP_DISPLAY_DURATION = 15  # Seconds

# ============================================================================
# UPDATE INTERVALS
# ============================================================================
UPDATE_INTERVAL = 60  # Update pet stats every 60 seconds
SAVE_INTERVAL = 60    # Auto-save to database every 60 seconds
INPUT_POLL_RATE = 0.1  # Check for input 10 times per second

# ============================================================================
# INPUT CONFIGURATION
# ============================================================================
BUTTON_DEBOUNCE_TIME = 0.05    # 50ms debounce
LONG_PRESS_DURATION = 0.5      # 500ms for long press

# ============================================================================
# TEXT ENTRY CONFIGURATION
# ============================================================================
# Character pool for name entry
TEXT_ENTRY_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
MAX_NAME_LENGTH = 12
MIN_NAME_LENGTH = 1

# Valid characters pattern for pet names (alphanumeric, spaces, dashes)
import re
PET_NAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\s\-]*$')


def validate_pet_name(name: str) -> tuple:
    """
    Validate a pet name.

    Args:
        name: The name to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    if name is None:
        return False, "Name cannot be None"

    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name)}"

    # Strip and check
    name = name.strip()

    if not name:
        return False, "Name cannot be empty"

    if len(name) < MIN_NAME_LENGTH:
        return False, f"Name must be at least {MIN_NAME_LENGTH} character(s)"

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name cannot exceed {MAX_NAME_LENGTH} characters"

    if not PET_NAME_PATTERN.match(name):
        return False, "Name can only contain letters, numbers, spaces, and dashes"

    # Check for whitespace-only (after stripping, this should be caught above)
    if name.isspace():
        return False, "Name cannot be only whitespace"

    return True, None

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DB_TIMEOUT = 30.0  # Seconds to wait for database lock
DB_CHECK_SAME_THREAD = False  # Allow multi-threaded access

# ============================================================================
# SCREEN STATES
# ============================================================================
class ScreenState:
    """Enum for screen states"""
    HOME = "home"              # Status view
    MENU = "menu"              # Main menu (Care, Friends, Requests, Reset)
    NAME_ENTRY = "name_entry"  # Text input for naming
    SETTINGS = "settings"      # System settings
    CONFIRM = "confirm"        # Confirmation dialog
    # Care submenu
    CARE_MENU = "care_menu"    # Pet care actions (Feed, Play, Clean, Sleep)
    # Social screens
    FRIENDS_LIST = "friends_list"          # View friends with online status
    FIND_FRIENDS = "find_friends"          # Discover nearby devices
    FRIEND_REQUESTS = "friend_requests"    # View/accept/reject requests
    # Message screens
    INBOX = "inbox"                          # View received messages
    MESSAGE_DETAIL = "message_detail"        # View single message
    # Message composition screens
    MESSAGE_TYPE_MENU = "message_type_menu"  # Choose message type
    EMOJI_CATEGORY = "emoji_category"        # Choose emoji category
    EMOJI_SELECT = "emoji_select"            # Pick emoji to send
    PRESET_CATEGORY = "preset_category"      # Choose preset category
    PRESET_SELECT = "preset_select"          # Pick preset message
    TEXT_COMPOSE = "text_compose"            # Custom text entry

# ============================================================================
# MENU STRUCTURE
# ============================================================================
# Main menu - high level navigation
MAIN_MENU = [
    {"label": "Care", "action": "care"},            # Opens CARE_MENU
    {"label": "Inbox", "action": "inbox"},          # Opens INBOX
    {"label": "Friends", "action": "friends"},      # Opens FRIENDS_LIST
    {"label": "Requests", "action": "requests"},    # Opens FRIEND_REQUESTS
    {"label": "Reset Pet", "action": "reset"},
    {"label": "Back", "action": "back"}
]

# Care submenu - pet care actions
CARE_MENU = [
    {"label": "Feed", "action": "feed"},
    {"label": "Play", "action": "play"},
    {"label": "Clean", "action": "clean"},
    {"label": "Sleep", "action": "sleep"},
    {"label": "Back", "action": "back"}
]

# Message type selection menu
MESSAGE_TYPE_MENU = [
    {"label": "Emoji", "action": "msg_emoji"},
    {"label": "Quick Msg", "action": "msg_preset"},
    {"label": "Custom", "action": "msg_custom"},
    {"label": "Back", "action": "back"}
]

# Preset messages for quick send
MESSAGE_PRESETS = [
    "Hi!", "Hello!", "How are you?", "Want to play?",
    "Yes!", "No", "Maybe", "Thanks!", "Sorry!",
    "I'm happy!", "Feeling sad", "So tired", "LOL", "Bye!"
]

# Emojis for quick send (text representations for e-ink)
EMOJI_LIST = [
    ":)", ":(", ":D", ";)", ":P",
    "<3", "*", "!", "?", "ZZZ",
    ":O", "XD", ":/", ">:(", "^_^"
]

# Category display names for preset messages
PRESET_CATEGORIES = [
    ("greetings", "Greetings"),
    ("questions", "Questions"),
    ("responses", "Responses"),
    ("emotions", "Emotions"),
    ("activities", "Activities"),
    ("fun", "Fun"),
    ("social", "Social")
]

# Category display names for emojis
EMOJI_CATEGORIES = [
    ("faces", "Faces"),
    ("symbols", "Symbols"),
    ("food", "Food"),
    ("animals", "Animals"),
    ("objects", "Objects")
]

# ============================================================================
# WIFI COMMUNICATION
# ============================================================================
WIFI_SERVICE_TYPE = "_notagotchi._tcp.local."
WIFI_PORT = 5555
WIFI_DISCOVERY_TIMEOUT = 5.0       # seconds
WIFI_CONNECTION_TIMEOUT = 10.0     # seconds
WIFI_MESSAGE_MAX_SIZE = 8192       # bytes (8KB)
MESSAGE_ENCODING = "utf-8"

# Service properties for mDNS advertisement
SERVICE_PROPERTIES = {
    "version": "1.0",
    "protocol": "notagotchi"
}

# Device identification
DEVICE_ID_PREFIX = "notagotchi"    # Creates "PetName_notagotchi"

# ============================================================================
# MESSAGING
# ============================================================================
MESSAGE_RETRY_MAX_ATTEMPTS = 10
MESSAGE_RETRY_INITIAL_DELAY = 30   # seconds
MESSAGE_RETRY_MAX_DELAY = 1800     # seconds (30 minutes)
MESSAGE_EXPIRATION_DAYS = 30
MESSAGE_MAX_LENGTH = 200
MESSAGE_INBOX_LIMIT = 100          # per friend

# ============================================================================
# FRIEND MANAGEMENT
# ============================================================================
FRIEND_REQUEST_EXPIRATION_HOURS = 24
MAX_FRIENDS = 50

# ============================================================================
# CONTENT (EMOJI & PRESETS)
# ============================================================================
EMOJI_IMAGE_SIZE = 16              # 16x16 pixels
EMOJI_FILE_PATH = os.path.join(RESOURCES_DIR, "images", "emojis")
EMOJI_JSON_PATH = os.path.join(RESOURCES_DIR, "emojis.json")
PRESET_JSON_PATH = os.path.join(RESOURCES_DIR, "preset_messages.json")

# ============================================================================
# MISC
# ============================================================================
DEFAULT_PET_NAME = "Pet"
FPS_TARGET = 30  # Target frames per second (not critical for e-ink)
