# NotaGotchi Comprehensive Software Quality Audit

**Date:** 2025-12-20
**Scope:** Full codebase audit covering all software development principles
**Total Issues Found:** 127+ (23 Critical, 38 High, 42 Medium, 24+ Low)

---

## Implementation Status

| Phase | Status | Completion Date |
|-------|--------|-----------------|
| **Phase 1: Critical Safety** | ✅ COMPLETE | 2025-12-20 |
| Phase 2: Testability | ⏳ Pending | - |
| Phase 3: Architecture | ⏳ Pending | - |
| Phase 4: Code Quality | ⏳ Pending | - |
| Phase 5: Polish | ⏳ Pending | - |

### Phase 1 Implementation Summary (Completed 2025-12-20)

**1. Database Locking** - ✅ FIXED
- Added `threading.RLock()` to `DatabaseManager` (`persistence.py`)
- All database operations wrapped with `with self._db_lock():` context manager
- Shared lock passed to `FriendManager` and `MessageManager`
- Files modified: `persistence.py`, `friend_manager.py`, `messaging.py`, `main.py`

**2. Callback Queue** - ✅ FIXED
- Added `queue.Queue` to `WiFiManager` for thread-safe event handling
- Server thread now queues events instead of direct callback invocation
- Added `process_callback_queue()` method called from main game loop
- Files modified: `wifi_manager.py`, `main.py`

**3. Transaction Atomicity** - ✅ FIXED
- `accept_friend_request()` now uses explicit `BEGIN IMMEDIATE` transaction
- Both INSERT and UPDATE wrapped atomically with rollback on failure
- Files modified: `friend_manager.py`

**4. Input Validation** - ✅ FIXED
- Message content validated for None, empty, type, content_type, and length
- Pet names validated with regex pattern, length bounds, no whitespace-only
- Added `config.validate_pet_name()` helper function
- Files modified: `messaging.py`, `config.py`, `main.py`

---

## Executive Summary

The NotaGotchi codebase demonstrates solid foundational design with clear module separation and good documentation. However, it suffers from **critical architectural issues** that will impact maintainability, testability, and reliability:

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Architecture & SOLID | 5 | 8 | 6 | 3 |
| Code Quality (DRY/KISS/YAGNI) | 2 | 7 | 12 | 8 |
| Error Handling & Security | 1 | 6 | 5 | 3 |
| Concurrency & Threading | 3 | 2 | 2 | 1 |
| State Management | 1 | 3 | 4 | 2 |
| Testing & Testability | 3 | 4 | 3 | 2 |
| Performance | 1 | 4 | 5 | 3 |
| Data Integrity | 2 | 3 | 3 | 1 |
| Logging & Observability | 0 | 1 | 2 | 1 |
| **TOTAL** | **23** | **38** | **42** | **24+** |

**Key Findings:**
- `NotAGotchiApp` is a **god object** (1000+ lines, 40+ methods, 12+ dependencies)
- **Critical race conditions** in message queue and WiFi callbacks
- **Zero unit test coverage** due to tight coupling
- **No transaction atomicity** in multi-step database operations
- **86+ magic numbers** without named constants

---

## 1. ARCHITECTURE & SOLID PRINCIPLES

### 1.1 Single Responsibility Principle (SRP) Violations

#### CRITICAL: God Object - NotAGotchiApp
**File:** `src/main.py` | **Lines:** 1-1000+ | **Risk:** CRITICAL

The `NotAGotchiApp` class handles 8+ distinct responsibilities:
1. Application lifecycle (startup, shutdown, signals)
2. Game loop orchestration
3. UI rendering (40+ render methods)
4. Data persistence
5. Social feature coordination
6. Action handling (feed, play, clean, sleep)
7. Input processing
8. State management

**Impact:** Impossible to unit test, changes cascade everywhere, 1000+ line class

**Fix:** Extract to separate classes:
```
NotAGotchiApp (50 lines) - thin orchestrator
├── GameController - main loop
├── RenderEngine - all _render_* methods
├── ActionHandler - all _action_* methods
├── SocialManager - WiFi/friends/messages init
└── ApplicationLifecycle - startup/shutdown
```

#### HIGH: DisplayManager Mixed Concerns
**File:** `src/modules/display.py` | **Lines:** 1-1500+ | **Risk:** HIGH

Mixes hardware initialization, resource loading, 20+ rendering methods, battery monitoring, and utility helpers.

**Fix:** Extract DisplayHardware, IconManager, BatteryMonitor, and individual screen renderers.

#### MEDIUM: ScreenManager Overloaded
**File:** `src/modules/screen_manager.py` | **Lines:** 1-600+ | **Risk:** MEDIUM

Handles screen state, input routing (14 handlers), data caching, and state queries (17 is_* methods).

---

### 1.2 Open/Closed Principle (OCP) Violations

#### HIGH: Message Type if-elif Chain
**File:** `src/modules/social_coordinator.py` | **Lines:** 206-250 | **Risk:** HIGH

```python
if message_type == 'friend_request':
    self._handle_friend_request(...)
elif message_type == 'friend_request_accepted':
    self._handle_friend_request_accepted(...)
elif message_type == 'message':
    self._handle_chat_message(...)
```

Adding new message types requires modifying this class.

**Fix:** Use Strategy pattern with message handler registry:
```python
class MessageHandler(ABC):
    def can_handle(self, msg) -> bool: pass
    def handle(self, msg, sender): pass

self.handlers.append(VoiceMessageHandler())  # Extensible
```

#### HIGH: Screen Rendering Not Extensible
**Files:** `main.py`, `display.py` | **Risk:** HIGH

Adding a new screen requires changes in 4 files:
1. `config.py` - add ScreenState
2. `screen_manager.py` - add handler + state methods
3. `main.py` - add _render_* method
4. `display.py` - add draw_* method

**Fix:** Screen plugin architecture with self-registering screens.

#### MEDIUM: Emotion Rules Hardcoded
**File:** `src/modules/config.py` | **Lines:** 232-246 | **Risk:** MEDIUM

Lambda-based rules with implicit evaluation order. Adding emotions requires understanding hidden dependencies.

---

### 1.3 Dependency Inversion Principle (DIP) Violations

#### HIGH: Direct Database Dependencies
**Files:** `friend_manager.py`, `messaging.py`, `persistence.py` | **Risk:** HIGH

All database modules depend directly on `sqlite3.Connection`:
```python
cursor = self.connection.cursor()
cursor.execute('''SELECT...FROM friends...''')
```

Can't swap databases, can't mock for tests.

**Fix:** Repository pattern:
```python
class FriendRepository(ABC):
    def get_friends(self) -> List[Friend]: pass

class SQLiteFriendRepository(FriendRepository):
    # SQL implementation

class FriendManager:
    def __init__(self, repo: FriendRepository):  # Inject abstraction
```

#### MEDIUM: Global Config Dependencies
**Files:** All modules | **Risk:** MEDIUM

Every module imports `from . import config` directly. Can't inject test configs.

**Fix:** Pass config as constructor parameter or use AppConfig class.

---

### 1.4 Design Patterns Assessment

#### Patterns Used (Good)
| Pattern | Location | Quality |
|---------|----------|---------|
| Singleton (implicit) | DatabaseManager | Good |
| Observer/Callback | WiFiManager | Functional |
| Factory | SpriteManager | Good |
| DTO | Pet.to_dict() | Excellent |

#### Patterns Missing (Should Use)
| Pattern | Where Needed | Current Cost |
|---------|--------------|--------------|
| **Repository** | All DB access | Can't test/swap DB |
| **Dependency Injection** | All constructors | Can't mock anything |
| **Strategy** | Message handling | if-elif chains grow |
| **Command** | User actions | Scattered in main.py |
| **State Machine** | Screen navigation | Implicit, error-prone |
| **Factory** | App creation | Can't create test instances |

#### Anti-patterns Detected
| Anti-pattern | Location | Impact |
|--------------|----------|--------|
| **God Object** | main.py NotAGotchiApp | Unmaintainable |
| **Service Locator** | config.py globals | Hard to test |
| **Callback Hell** | WiFi → Social callbacks | Circular deps |
| **Flag-Driven Dev** | main.py boolean flags | Confusing state |

---

## 2. CODE QUALITY

### 2.1 DRY Violations

#### CRITICAL: Care Action Duplication
**File:** `src/modules/pet.py` | **Lines:** 166-260 | **Risk:** CRITICAL

`feed()`, `play()`, `clean()`, `sleep()` all follow identical patterns:
```python
if not self.is_alive(): return {}
changes = config.CARE_ACTIONS['action'].copy()
self.hunger = max(MIN, min(MAX, self.hunger + changes['hunger']))
# Repeated for happiness, health, energy - 16 times total
```

**Fix:** Extract `_apply_stat_changes(action_name)` helper.

#### HIGH: Stat Clamping Pattern
**File:** `src/modules/pet.py` | **Lines:** Multiple | **Risk:** HIGH

`max(MIN, min(MAX, value))` repeated 16+ times.

**Fix:** Create `_clamp_stat(value)` or use property setters.

#### HIGH: Highlight Rectangle Code
**File:** `src/modules/display.py` | **Lines:** 15+ locations | **Risk:** HIGH

```python
# Repeated in 15+ methods:
if i == selected_index:
    draw.rectangle([(x-2, y-1), (width-5, y+height-3)], fill=0)
    draw.text((x, y), text, fill=1, font=font)
else:
    draw.text((x, y), text, fill=0, font=font)
```

**Fix:** `_draw_list_item()` helper exists but isn't used consistently.

#### MEDIUM: Status Data Retrieval
**File:** `src/main.py` | **Lines:** Multiple render methods | **Risk:** MEDIUM

Same 3 status values retrieved in 12+ methods:
```python
wifi_connected = self._get_wifi_status()
online_friends = self._get_online_friends_count()
unread_messages = self._get_unread_count()
```

**Fix:** Already added `_get_header_status()` - use consistently.

---

### 2.2 KISS Violations

#### MEDIUM: Over-complex Message Composition State
**File:** `src/modules/screen_manager.py` | **Lines:** 70-95 | **Risk:** MEDIUM

12+ state variables for message composition:
- `message_type_index`, `emoji_category_index`, `selected_emoji_category`
- `emoji_index`, `current_emoji_items`, `preset_category_index`
- `selected_preset_category`, `preset_index`, `current_preset_items`
- `compose_buffer`, `compose_char_index`

**Fix:** Use nested state dict or MessageCompositionContext class.

#### MEDIUM: Emotion Logic with Hidden Dependencies
**File:** `src/modules/config.py` | **Lines:** 232-246 | **Risk:** MEDIUM

Lambda rules evaluated sequentially - earlier matches prevent later ones. Order matters but isn't documented.

**Fix:** Use explicit priority system or clearer rule engine.

---

### 2.3 YAGNI Violations

#### LOW: Unused _draw_list_item() Method
**File:** `src/modules/display.py` | **Lines:** 180-199 | **Risk:** LOW

Method exists but never called - code manually implements list items everywhere.

**Fix:** Either use it consistently or remove it.

#### LOW: Over-generalized Category Config
**File:** `src/modules/config.py` | **Lines:** 343-348 | **Risk:** LOW

```python
PRESET_CATEGORIES = [("key", "Display Name"), ...]
```

Tuples with internal keys that are never used for lookup.

---

### 2.4 Magic Numbers (86+ instances)

**Critical locations:**
| File | Line | Value | Should Be |
|------|------|-------|-----------|
| display.py | 404 | `+2` | TEXT_VERTICAL_PADDING |
| display.py | 430 | `-2, -1` | HIGHLIGHT_OFFSET_X/Y |
| wifi_manager.py | 295 | `5` | WIFI_SERVER_BACKLOG |
| messaging.py | 398 | `10` | MESSAGE_QUEUE_BATCH_SIZE |
| friend_manager.py | 220 | `300` | FRIEND_ONLINE_TIMEOUT_SECONDS |

---

## 3. ERROR HANDLING & SECURITY

### 3.1 Error Handling Issues

#### ~~CRITICAL: Missing Message Content Validation~~ ✅ FIXED (Phase 1)
**File:** `src/modules/messaging.py` | **Lines:** 88-104 | **Risk:** ~~CRITICAL~~ RESOLVED

~~Only validated is_friend and content length. Missing: empty string, None, invalid content_type.~~

**Resolution:** Added comprehensive validation in `send_message()` and `receive_message()`:
- Validates content is not None
- Validates content is a string
- Strips whitespace and checks for empty
- Validates content_type against `VALID_CONTENT_TYPES` set
- Validates content length

#### HIGH: Bare Except Clauses
**File:** `src/modules/display.py` | **Lines:** 62-76 | **Risk:** HIGH

```python
except:  # Catches KeyboardInterrupt, SystemExit too!
    print("Using default font")
```

**Fix:** Use `except Exception as e:` or catch specific exceptions.

#### HIGH: Swallowed Exceptions in Font Loading
**File:** `src/modules/display.py` | **Lines:** 66-76 | **Risk:** HIGH

Font loading silently fails with no error message.

**Fix:** Add debug logging for failed load attempts.

#### MEDIUM: No Transaction Rollback on Error
**File:** `src/modules/persistence.py` | **Lines:** 77-95 | **Risk:** MEDIUM

Database migrations don't rollback on failure:
```python
try:
    cursor.execute("ALTER TABLE...")
    # No commit!
except:
    # No rollback!
```

---

### 3.2 Security Considerations

#### ~~MEDIUM: No Pet Name Validation~~ ✅ FIXED (Phase 1)
**File:** `src/main.py` | **Lines:** 420-433 | **Risk:** ~~MEDIUM~~ RESOLVED

~~Pet names validated for length but not special characters, unicode, or whitespace-only strings.~~

**Resolution:** Added `config.validate_pet_name()` function with:
- Regex pattern `^[A-Za-z0-9][A-Za-z0-9\s\-]*$`
- Length bounds checking (MIN_NAME_LENGTH to MAX_NAME_LENGTH)
- Whitespace-only string rejection
- Type validation (must be string)

#### LOW: File Path Traversal Risk
**File:** `src/modules/sprite_manager.py` | **Lines:** 59-71 | **Risk:** LOW

If sprite filenames were user-controlled, path traversal possible. Currently safe (hardcoded config).

---

## 4. CONCURRENCY & THREADING

### 4.1 Race Conditions

#### ~~CRITICAL: Message Queue Database Race~~ ✅ FIXED (Phase 1)
**File:** `src/modules/messaging.py` | **Lines:** 370-430 | **Risk:** ~~CRITICAL~~ RESOLVED

~~Queue processor runs in separate thread, accessing same database as main thread without synchronization.~~

**Resolution:** Added `threading.RLock()` shared across all database modules. All database operations now wrapped with `with self._db_lock():` context manager.

#### ~~CRITICAL: WiFi Callback Thread Safety~~ ✅ FIXED (Phase 1)
**File:** `src/modules/wifi_manager.py` | **Lines:** 295-320 | **Risk:** ~~CRITICAL~~ RESOLVED

~~Callbacks invoked from socket server thread modify SocialCoordinator state accessed from main thread.~~

**Resolution:** Added `queue.Queue` for callback events. Server thread queues events via `_invoke_callbacks()`, main loop processes via `process_callback_queue()`.

#### ~~CRITICAL: Shared Database Connection~~ ✅ FIXED (Phase 1)
**File:** `src/modules/friend_manager.py` | **Risk:** ~~CRITICAL~~ RESOLVED

~~Same `sqlite3.Connection` used by main thread and WiFi thread. SQLite is NOT thread-safe by default.~~

**Resolution:** Shared `threading.RLock()` passed from `DatabaseManager` to `FriendManager` and `MessageManager`. All operations synchronized.

---

## 5. STATE MANAGEMENT

### 5.1 State Issues

#### CRITICAL: No Stat Bounds Validation on Load
**File:** `src/modules/pet.py` | **Lines:** 40-49 | **Risk:** CRITICAL

`from_dict()` loads stats from database without validating [0, 100] bounds:
```python
hunger = data.get('hunger', config.INITIAL_HUNGER)
# No validation - corrupted DB value passes through
```

**Fix:** Add property setters with clamping or validate in from_dict().

#### HIGH: Pet State Can Become Stale
**File:** `src/main.py` | **Lines:** 68-93 | **Risk:** HIGH

Pet loaded once at startup, never re-validated. If database modified externally, UI renders stale state.

#### MEDIUM: Screen State Inconsistency
**File:** `src/modules/screen_manager.py` | **Lines:** 50-57 | **Risk:** MEDIUM

`set_screen()` only resets some state selectively. Navigating quickly can leave old indices.

**Fix:** Use per-screen state dictionaries:
```python
self.screen_states = {
    ScreenState.MENU: {'index': 0},
    ScreenState.FRIENDS_LIST: {'index': 0, 'scroll': 0},
}
```

---

## 6. TESTING & TESTABILITY

### 6.1 Testability Blockers

#### CRITICAL: Zero Unit Test Coverage
**Status:** No test files found in codebase.

#### CRITICAL: Tight Coupling Prevents Testing
**File:** `src/main.py` | **Lines:** 31-45 | **Risk:** CRITICAL

Constructor initializes 12+ components directly:
```python
self.db = DatabaseManager()           # Can't mock
self.wifi = WiFiManager()             # Can't mock
self.social = SocialCoordinator(...)  # Can't mock
```

**Example impossible test:**
```python
def test_feed_action():
    app = NotAGotchiApp()  # Initializes EVERYTHING
    app._action_feed()      # Saves to REAL database
```

**Fix:** Dependency injection:
```python
def __init__(self, db=None, wifi=None, ...):
    self.db = db or DatabaseManager()
```

#### HIGH: Side Effects in Pure Functions
**File:** `src/modules/pet.py` | **Lines:** 168-200 | **Risk:** HIGH

`update_stats()` has side effects (prints, modifies state, checks evolution) mixed with calculations.

**Fix:** Separate `_calculate_stat_changes()` (pure) from `_apply_changes()` (side effects).

---

## 7. PERFORMANCE

### 7.1 Performance Issues

#### HIGH: Device Discovery Every Frame
**File:** `src/main.py` | **Lines:** 741-746 | **Risk:** HIGH

```python
def _render_find_friends_screen(self):
    devices = self.social_coordinator.discover_new_devices()  # EVERY FRAME!
```

Device discovery blocks for `WIFI_DISCOVERY_TIMEOUT` seconds on every render.

**Fix:** Only discover when screen first entered, not every frame.

#### HIGH: Inefficient Online Status Check
**File:** `src/modules/friend_manager.py` | **Lines:** 175-210 | **Risk:** HIGH

`get_friends()` recalculates online status for every friend on every call (30 FPS × 50 friends = 1500 calculations/sec).

**Fix:** Cache online status for 5+ seconds.

#### MEDIUM: Over-refreshing Display
**File:** `src/main.py` | **Lines:** 680-710 | **Risk:** MEDIUM

`action_occurred` flag triggers full refresh on EVERY action. Quick feed + play = two full refreshes.

**Fix:** Debounce - only refresh if 500ms+ since last action.

#### MEDIUM: No Message Queue Backpressure
**File:** `src/modules/messaging.py` | **Lines:** 395-440 | **Risk:** MEDIUM

Queue processes up to 10 messages in quick succession with no rate limiting.

---

## 8. DATA INTEGRITY

### 8.1 Integrity Issues

#### ~~CRITICAL: No Transaction Atomicity~~ ✅ FIXED (Phase 1)
**File:** `src/modules/friend_manager.py` | **Lines:** 79-116 | **Risk:** ~~CRITICAL~~ RESOLVED

~~`accept_friend_request()` does two operations that should be atomic. Power loss between operations causes inconsistent state.~~

**Resolution:** `accept_friend_request()` now uses explicit `BEGIN IMMEDIATE` transaction:
```python
cursor.execute('BEGIN IMMEDIATE')
try:
    cursor.execute('INSERT INTO friends...')
    cursor.execute('UPDATE friend_requests...')
    connection.commit()
except Exception:
    connection.rollback()
    raise
```

#### HIGH: Duplicate Message Risk
**File:** `src/modules/messaging.py` | **Lines:** 240-280 | **Risk:** HIGH

If delivery succeeds but crash before `_mark_delivered()`, message stays "pending" and gets resent.

#### MEDIUM: Dead Pet Can Receive Actions
**File:** `src/modules/pet.py` | **Lines:** 315-330 | **Risk:** MEDIUM

If pet dies during action queue processing, queued actions still execute on dead pet.

---

## 9. LOGGING & OBSERVABILITY

### 9.1 Issues

#### HIGH: No Structured Logging
**Files:** All modules | **Risk:** HIGH

All error reporting via `print()`:
- No timestamps
- No log levels
- No filtering by module
- No file output for debugging

**Fix:** Use `logging` module:
```python
import logging
logger = logging.getLogger(__name__)
logger.error("WiFi server error", exc_info=True)
```

#### MEDIUM: No Performance Metrics
**File:** `src/main.py` | **Risk:** MEDIUM

No visibility into frame time, database latency, or rendering time. Can't diagnose slowdowns.

---

## 10. ADDITIONAL PRINCIPLES

### 10.1 Law of Demeter Violations

**File:** `src/main.py` | Multiple locations | **Risk:** MEDIUM

Long call chains violate Law of Demeter:
```python
self.social_coordinator.get_friends(online_only=True)
self.screen_manager.get_friends_list_state()['friends']
```

### 10.2 Separation of Concerns

**Status:** Partially good (modules separated), partially bad (main.py does everything).

### 10.3 Single Source of Truth

**Issue:** Friend info structure defined differently in multiple locations:
- `{'device_name', 'pet_name', 'ip', 'port'}` in accept_friend_request
- `{'from_device_name', 'from_pet_name', ...}` in handle_friend_request_accepted

**Fix:** Create `Friend` dataclass as single source of truth.

### 10.4 Composition Over Inheritance

**Status:** Good - codebase uses composition, not deep inheritance hierarchies.

### 10.5 Fail Fast

**Issue:** Many silent failures instead of raising exceptions:
```python
if not content:
    return None  # Silent failure, caller may not check
```

---

## PRIORITY REFACTORING ROADMAP

### Phase 1: Critical Safety (1-2 days) ✅ COMPLETE
1. ✅ **Add database locking** - Prevent race conditions
2. ✅ **Add callback queue** - Thread-safe WiFi communication
3. ✅ **Add transaction atomicity** - Prevent data corruption
4. ✅ **Add input validation** - Prevent malformed data

### Phase 2: Testability (2-3 days)
1. **Dependency injection** - Enable mocking
2. **Extract Repository pattern** - Decouple from SQLite
3. **Separate pure functions** - Enable unit tests
4. **Write core unit tests** - Pet, Friend, Message logic

### Phase 3: Architecture (3-4 days)
1. **Break up NotAGotchiApp** - Extract RenderEngine, ActionHandler
2. **Add Strategy pattern** - Message handler registry
3. **Add State Machine** - Explicit screen navigation
4. **Implement screen plugins** - Extensible screens

### Phase 4: Code Quality (2-3 days)
1. **Extract DRY helpers** - stat clamping, list rendering
2. **Replace magic numbers** - Named constants throughout
3. **Add structured logging** - Replace print statements
4. **Add performance metrics** - Frame time, DB latency

### Phase 5: Polish (Ongoing)
1. **Add integration tests** - Full workflow tests
2. **Add documentation** - API docs, architecture guide
3. **Performance optimization** - Caching, lazy loading
4. **Security hardening** - Input sanitization

---

## ESTIMATED EFFORT

| Phase | Effort | Status | Risk Reduction |
|-------|--------|--------|----------------|
| Phase 1: Critical Safety | 1-2 days | ✅ Complete | Prevents data loss, crashes |
| Phase 2: Testability | 2-3 days | ⏳ Pending | Enables safe refactoring |
| Phase 3: Architecture | 3-4 days | ⏳ Pending | Reduces maintenance burden |
| Phase 4: Code Quality | 2-3 days | ⏳ Pending | Improves readability |
| Phase 5: Polish | Ongoing | ⏳ Pending | Professional quality |
| **TOTAL** | **8-12 days** | **~15% done** | **Production-ready** |

---

## FILES TO MODIFY (Priority Order)

| File | Changes | Priority | Status |
|------|---------|----------|--------|
| `src/main.py` | Extract classes, add DI, fix race conditions | CRITICAL | ✅ Phase 1 (locking, callbacks) |
| `src/modules/persistence.py` | Add locking, transactions | CRITICAL | ✅ Phase 1 Complete |
| `src/modules/messaging.py` | Fix queue races, add validation | CRITICAL | ✅ Phase 1 Complete |
| `src/modules/wifi_manager.py` | Add callback queue | CRITICAL | ✅ Phase 1 Complete |
| `src/modules/friend_manager.py` | Add transactions, locking | HIGH | ✅ Phase 1 Complete |
| `src/modules/config.py` | Add missing constants, validation | LOW | ✅ Phase 1 (validation) |
| `src/modules/pet.py` | Extract helpers, add validation | HIGH | ⏳ Pending |
| `src/modules/social_coordinator.py` | Add handler registry | HIGH | ⏳ Pending |
| `src/modules/display.py` | Use helpers consistently | MEDIUM | ⏳ Pending |
| `src/modules/screen_manager.py` | Simplify state | MEDIUM | ⏳ Pending |
