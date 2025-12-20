# NotaGotchi Refactoring Reference Guide

**Date:** 2025-12-20
**Purpose:** Quick reference for debugging issues after the comprehensive refactoring

---

## Overview

The refactoring extracted logic from the monolithic `NotAGotchiApp` into separate modules using dependency injection and design patterns. **101 tests pass** after refactoring.

---

## Architecture Changes

### 1. ActionHandler (NEW: `src/modules/action_handler.py`)

**Purpose:** Handles all user-triggered actions (care, navigation, social)

**Key Methods:**
```python
# Care actions - return True if successful
action_feed() -> bool
action_play() -> bool
action_clean() -> bool
action_sleep() -> bool
action_reset() -> None  # Shows confirmation dialog

# Navigation actions
action_care() -> None      # Opens care submenu
action_friends() -> None   # Opens friends list
action_requests() -> None  # Opens friend requests
action_inbox() -> None     # Opens inbox
action_view_message() -> None  # Marks message as read

# Pet management
complete_name_entry() -> bool  # Gets name from screen_manager, creates/renames pet

# Social actions
handle_send_message(data: dict) -> bool
handle_send_friend_request(device: dict, show_feedback: bool = True) -> bool
handle_friend_request_action(request: dict) -> None  # Shows confirmation dialog
```

**Dependencies (injected via callables):**
```python
ActionHandler(
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
```

**How main.py delegates:**
```python
def _action_feed(self):
    if hasattr(self, 'action_handler'):
        self.action_handler.action_feed()
```

---

### 2. MessageHandlers (NEW: `src/modules/message_handlers.py`)

**Purpose:** Strategy pattern for handling different WiFi message types

**Key Classes:**
```python
class MessageHandler(ABC):
    @property
    def message_type(self) -> str: pass  # e.g., 'friend_request'
    def handle(self, message_data, sender_ip, context) -> bool: pass

class MessageHandlerContext:
    # Provides access to managers without tight coupling
    friends: FriendManager
    messages: MessageManager
    wifi: WiFiManager
    own_pet_name: str
    on_friend_request_received: Callable  # UI callback
    on_friend_request_accepted: Callable
    on_friend_request_rejected: Callable
    on_message_received: Callable

class MessageHandlerRegistry:
    def register(handler: MessageHandler) -> None
    def handle_message(message_data, sender_ip, context) -> bool
```

**Built-in Handlers:**
- `FriendRequestHandler` - handles 'friend_request' messages
- `FriendRequestAcceptedHandler` - handles 'friend_request_accepted' messages
- `ChatMessageHandler` - handles 'message' messages

**How SocialCoordinator uses it:**
```python
def _handle_incoming_message(self, message_data, sender_ip):
    context = self._create_handler_context()
    self._message_registry.handle_message(message_data, sender_ip, context)
```

---

### 3. ScreenStateMachine (NEW: `src/modules/screen_state_machine.py`)

**Purpose:** Formal state machine for screen navigation

**Key Classes:**
```python
class ScreenStateMachine:
    def register_state(name, allowed_transitions, on_enter, on_exit, data)
    def transition_to(target_state, **kwargs) -> TransitionResult
    def go_back() -> bool
    def go_home() -> bool
    @property
    def current_state -> str

class ScreenPlugin(ABC):
    @property
    def state_name(self) -> str: pass
    def render(self, context) -> Image: pass
    def handle_input(self, event, state_machine) -> bool: pass
    def register(self, state_machine) -> None
```

**Factory:**
```python
create_default_state_machine() -> ScreenStateMachine  # All standard screens registered
```

---

### 4. Repositories (NEW: `src/modules/repositories.py`)

**Purpose:** Repository pattern for data access (enables testing without database)

**Data Classes:**
```python
@dataclass
class PetData:
    id, name, hunger, happiness, health, energy, stage, ...
    def to_dict() -> dict
    @classmethod
    def from_dict(data) -> PetData

@dataclass
class FriendData:
    id, device_name, pet_name, last_ip, last_port, ...

@dataclass
class FriendRequestData:
    id, from_device_name, from_pet_name, from_ip, from_port, status, ...

@dataclass
class MessageData:
    message_id, from_device_name, from_pet_name, to_device_name, content, ...
```

**In-Memory Implementations (for testing):**
```python
class InMemoryPetRepository:
    def create_pet(name, **stats) -> int
    def get_active_pet() -> Optional[PetData]
    def update_pet(pet_id, **stats) -> bool
    def log_event(pet_id, event_type, stat_changes, notes) -> bool

class InMemoryFriendRepository:
    def add_friend(device_name, pet_name, ip, port) -> bool
    def get_friends() -> List[FriendData]
    def is_friend(device_name) -> bool

class InMemoryFriendRequestRepository:
    def create_request(device_name, pet_name, ip, port, expires) -> bool
    def get_pending_requests() -> List[FriendRequestData]
    def update_request_status(device_name, status) -> bool

class InMemoryMessageRepository:
    def save_message(message: MessageData) -> bool
    def get_messages(device_name, unread_only) -> List[MessageData]
    def mark_read(message_id) -> bool
```

---

### 5. Logging (NEW: `src/modules/logging_config.py`)

**Purpose:** Centralized logging configuration

```python
setup_logging(level=logging.INFO, log_file=None, console=True)
get_logger(name: str) -> logging.Logger

# Usage:
from modules.logging_config import get_logger
logger = get_logger("module_name")
logger.info("Message")
logger.error("Error", exc_info=True)
```

---

### 6. Metrics (NEW: `src/modules/metrics.py`)

**Purpose:** Performance monitoring

```python
class MovingAverage:
    def add(value) -> None
    @property
    def average -> float

class Timer:
    # Context manager for timing
    with Timer() as t:
        do_work()
    print(t.elapsed_ms)

class PerformanceMetrics:
    def record_frame_time(ms)
    def record_db_query(ms)
    def get_summary() -> dict

# Global convenience:
record_frame_time(elapsed_ms)
get_metrics() -> PerformanceMetrics
```

---

### 7. FriendManager Updates (`src/modules/friend_manager.py`)

**New Method:**
```python
def add_friend(device_name, pet_name, ip, port) -> bool:
    """Add friend directly (used when someone accepts OUR request)"""
```

**Thread Safety:**
```python
def _db_lock(self):
    """Context manager for database locking"""
    # All database operations wrapped in: with self._db_lock():
```

---

### 8. SocialCoordinator Updates (`src/modules/social_coordinator.py`)

**New Constructor Parameter:**
```python
def __init__(self, wifi_manager, friend_manager, own_pet_name,
             message_manager=None, message_registry=None):
    # message_registry defaults to create_default_registry()
```

**New Methods:**
```python
@property
def message_registry -> MessageHandlerRegistry

def register_message_handler(handler) -> None:
    """Register custom message handler for extensibility"""

def _create_handler_context() -> MessageHandlerContext:
    """Creates context with all managers and callbacks"""
```

**Removed Methods (logic moved to message_handlers.py):**
- `_handle_friend_request()`
- `_handle_friend_request_accepted()`
- `_handle_chat_message()`

---

### 9. main.py Updates

**New Methods:**
```python
def _create_action_handler(self):
    """Creates ActionHandler with all dependencies injected"""

def _create_new_pet(self, name: str):
    """Creates pet in DB and updates self.pet (callback for ActionHandler)"""
```

**Delegation Pattern:**
All `_action_*` methods now delegate:
```python
def _action_feed(self):
    if hasattr(self, 'action_handler'):
        self.action_handler.action_feed()
```

All `_handle_*` methods now delegate:
```python
def _handle_send_message(self, data):
    if hasattr(self, 'action_handler'):
        self.action_handler.handle_send_message(data)
```

---

### 10. Config Updates (`src/modules/config.py`)

**New UI Constants:**
```python
# Font sizes
FONT_SIZE_SMALL = 10
FONT_SIZE_MEDIUM = 14
FONT_SIZE_LARGE = 18
FONT_SIZE_EMOJI = 28

# List item heights
LIST_ITEM_HEIGHT_SMALL = 14
LIST_ITEM_HEIGHT_MEDIUM = 16
LIST_ITEM_HEIGHT_LARGE = 18

# Highlight offsets
LIST_HIGHLIGHT_X_OFFSET = 2
LIST_HIGHLIGHT_Y_OFFSET = 1
LIST_HIGHLIGHT_BOTTOM_OFFSET = 2
LIST_RIGHT_MARGIN = 5

# Visible items per screen
VISIBLE_ITEMS_FRIENDS = 5
VISIBLE_ITEMS_INBOX = 5
VISIBLE_ITEMS_REQUESTS = 4
VISIBLE_ITEMS_MENU = 5

# Text limits
MAX_FRIEND_NAME_DISPLAY = 12
MAX_MESSAGE_PREVIEW = 20
```

---

## Common Debugging Scenarios

### 1. Action Not Working

**Check:** Is ActionHandler created?
```python
# In main.py __init__, verify _create_action_handler() is called AFTER:
# - _initialize_social_features()
# - All managers are initialized
```

**Check:** Is the action method delegating?
```python
def _action_feed(self):
    if hasattr(self, 'action_handler'):  # This guard needed
        self.action_handler.action_feed()
```

### 2. Messages Not Being Handled

**Check:** Is the registry being used?
```python
# In social_coordinator._handle_incoming_message:
context = self._create_handler_context()
self._message_registry.handle_message(message_data, sender_ip, context)
```

**Check:** Is the handler registered?
```python
# create_default_registry() registers:
# - FriendRequestHandler ('friend_request')
# - FriendRequestAcceptedHandler ('friend_request_accepted')
# - ChatMessageHandler ('message')
```

### 3. Friend Request Accepted But Not Added

**Check:** Is `add_friend()` method being called?
```python
# FriendRequestAcceptedHandler calls:
context.friends.add_friend(from_device_name, from_pet_name, from_ip, from_port)
```

**Check:** Is the friend already in the list?
```python
# add_friend() returns False if already friends
if self.is_friend(device_name):
    return False
```

### 4. Pet Not Created After Name Entry

**Check:** Is `_create_new_pet` callback working?
```python
# ActionHandler.complete_name_entry() calls:
self._create_new_pet(name)  # This is main.py._create_new_pet

# main.py._create_new_pet does:
pet_id = self.db.create_pet(name)
pet_data = self.db.get_active_pet()
self.pet = Pet.from_dict(pet_data)
```

### 5. Screen Navigation Issues

**Check:** Is ScreenStateMachine being used?
```python
# screen_state_machine.go_home() clears history AFTER transition
def go_home(self):
    result = self.transition_to(config.ScreenState.HOME)
    self._history.clear()  # Clear AFTER, not before
    return result == TransitionResult.SUCCESS
```

### 6. Tests Failing

**Run individual test files:**
```bash
python3 tests/test_pet.py           # 46 tests
python3 tests/test_repositories.py  # 36 tests
python3 tests/test_integration.py   # 19 tests
```

**Common test issues:**
- Timestamps too close together: Add `time.sleep(0.001)` between events
- Emotion tests: Check emotion rules order in config.py

---

## Data Flow Diagrams

### Action Flow
```
User Input
    ↓
ScreenManager.handle_input()
    ↓
Returns action string/tuple
    ↓
main.py._handle_input()
    ↓
Calls _action_* or _handle_* method
    ↓
Delegates to ActionHandler
    ↓
ActionHandler uses injected dependencies
```

### Message Flow
```
WiFi receives message
    ↓
WiFiManager invokes callback
    ↓
SocialCoordinator._handle_incoming_message()
    ↓
Creates MessageHandlerContext
    ↓
MessageHandlerRegistry.handle_message()
    ↓
Routes to appropriate handler (Strategy pattern)
    ↓
Handler processes message using context
```

### Pet Creation Flow
```
User enters name
    ↓
ScreenManager returns "name_entry_complete"
    ↓
main.py._complete_name_entry()
    ↓
ActionHandler.complete_name_entry()
    ↓
Gets name from screen_manager
    ↓
Validates name
    ↓
Calls _create_new_pet callback
    ↓
main.py._create_new_pet(name)
    ↓
db.create_pet() → db.get_active_pet() → Pet.from_dict()
```

---

## File Index

| File | Lines | Purpose |
|------|-------|---------|
| `src/main.py` | ~900 | Main app, now delegates to ActionHandler |
| `src/modules/action_handler.py` | ~420 | All action logic |
| `src/modules/message_handlers.py` | ~300 | Strategy pattern for messages |
| `src/modules/screen_state_machine.py` | ~460 | Screen navigation state machine |
| `src/modules/repositories.py` | ~450 | Data classes and in-memory repos |
| `src/modules/social_coordinator.py` | ~350 | WiFi/friends coordination |
| `src/modules/friend_manager.py` | ~600 | Friend database operations |
| `src/modules/logging_config.py` | ~80 | Logging setup |
| `src/modules/metrics.py` | ~150 | Performance tracking |
| `tests/test_pet.py` | ~560 | 46 pet unit tests |
| `tests/test_repositories.py` | ~560 | 36 repository tests |
| `tests/test_integration.py` | ~450 | 19 integration tests |

---

## Quick Fixes

### "AttributeError: 'NoneType' object has no attribute..."
- Check if the manager is initialized before ActionHandler is created
- Check if `skip_social_init` is True (testing mode)

### "Action not responding"
- Verify action is registered in `_register_actions()`
- Verify delegation method has `hasattr` guard

### "Message handler not found"
- Check message 'type' field matches handler's `message_type` property
- Verify handler is registered with `create_default_registry()`

### "Friend not added after acceptance"
- Verify `FriendManager.add_friend()` method exists
- Check for duplicate friend (returns False if already friends)
- Check friend limit (`MAX_FRIENDS` in config)
