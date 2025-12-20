# NotaGotchi Code Maintainability Audit

**Date:** 2025-12-20
**Scope:** Full Refactoring (~3 hours)
**Status:** In Progress

---

## Executive Summary

A thorough audit of the NotaGotchi codebase identified **86+ maintainability issues** across 6 key files. The most critical problems are concentrated in `display.py` and `screen_manager.py`, where extensive code duplication and magic numbers create significant maintenance burden.

**Key Findings:**
- **76+ magic numbers** without named constants
- **16 near-duplicate canvas creation blocks** in display.py
- **15+ identical highlight rectangle implementations**
- **8 methods with nearly identical list rendering logic**
- **3+ separate files** must be modified to add a new screen type
- **3 locations** with duplicated device name parsing logic

**Estimated Technical Debt Reduction:** Addressing the top 10 issues would reduce future development time for new features by 40-60%.

---

## Priority Ranking

### HIGH Priority (Will likely cause bugs when code is modified)

| # | Issue | File | Lines | Impact |
|---|-------|------|-------|--------|
| 1 | Derived constants hardcoded separately | config.py | 55-64 | If HEADER_HEIGHT changes, 3 values silently break |
| 2 | Header layout chain of magic numbers | display.py | 1046-1125 | Single change breaks entire header positioning |
| 3 | Highlight rectangle duplicated 15+ times | display.py | Multiple | Style change requires 15+ edits |
| 4 | List rendering pattern in 8 methods | display.py | Multiple | UI behavior change requires 8 edits |
| 5 | Screen dispatch chain (OCP violation) | screen_manager.py | 62-77, 137-155 | New screen requires 60+ lines in 3 files |
| 6 | Cached data can get out of sync | screen_manager.py | 35-43 | Stale friends/messages shown silently |
| 7 | Stat bar hardcoding (not extensible) | display.py | 1201-1224 | Can't add 5th stat without code changes |
| 8 | Text input/confirmation hardcoded coords | display.py | 282-298, 339-356 | Layout breaks if display changes |

### MEDIUM Priority (Makes code harder to maintain)

| # | Issue | File | Lines | Impact |
|---|-------|------|-------|--------|
| 9 | Pet sprite lookup duplicated 12+ times | main.py | 564-908 | Sprite logic change requires 12 edits |
| 10 | WiFi status code duplicated 12+ times | main.py | 566-921 | Status logic change requires 12 edits |
| 11 | Care action handlers identical structure | main.py | 215-237 | Business logic duplicated 4x |
| 12 | Canvas creation duplicated 16 times | display.py | Multiple | Maintenance burden |
| 13 | Time formatting duplicated | display.py | 631-644, 718-734 | Threshold change needs 2 edits |
| 14 | Word wrapping duplicated 3 places | display.py | 324-336, 753-764, 1278-1289 | Algorithm change needs 3 edits |
| 15 | Category index arithmetic fragile | screen_manager.py | 318-324, 366-371 | IndexError if config changes |
| 16 | State explosion (23 instance vars) | screen_manager.py | 19-48 | Hard to reason about state |
| 17 | Device name parsing in 3 locations | main.py, display.py, social | Multiple | Format change needs 3 edits |
| 18 | Font sizes hardcoded | display.py | 46-48 | Can't adjust text sizes easily |
| 19 | Item heights inconsistent (14,15,16,18) | display.py | Multiple | No rationale; confusing |
| 20 | Emotion rules use lambdas | config.py | 133-148 | Hard to test/debug |
| 21 | Test values in production config | config.py | 157-165 | Easy to ship wrong values |
| 22 | Message data uses implicit dict keys | screen_manager.py | 308-313 | Typos go undetected |

### LOW Priority (Style/organization improvements)

| # | Issue | File | Lines | Impact |
|---|-------|------|-------|--------|
| 23 | Related constants not grouped | config.py | 47-68 | Hard to find related values |
| 24 | Icon loading silent failures | display.py | 57-79 | Cryptic errors if icon missing |
| 25 | Battery "AC" label unclear | display.py | 1181-1231 | Users confused by display |
| 26 | Queue processor timing hardcoded | messaging.py | 340-347 | Can't tune without source edit |
| 27 | DB parameters not fully exposed | persistence.py | 26-30 | journal_mode hardcoded |
| 28 | No message protocol versioning | config.py | N/A | Future compatibility issues |
| 29 | No unified error handling | Multiple | Multiple | Inconsistent error reporting |
| 30 | Emoji/preset loading not cached | main.py | 841-866 | Minor inefficiency |

---

## Detailed Findings by File

### display.py (1300+ lines) - CRITICAL

**Magic Numbers (76+ instances):**
```python
# Text Input Screen (lines 282-298)
draw.text((5, 2), title, ...)           # Why 5,2?
draw.line([(0, 15), (self.width, 15)])  # Why 15?
draw.text((10, 25), current_display)    # Why 10,25?
draw.rectangle([(75, 60), (175, 95)])   # Hardcoded box coords
draw.text((110, 70), selected_char)     # Text position not derived from box

# Confirmation Dialog (lines 339-356)
yes_box = [(30, 80), (100, 100)]        # Hardcoded button positions
no_box = [(130, 80), (200, 100)]        # Not derived from display width
draw.text((52, 87), "Yes", ...)         # Position not calculated from box center

# Header Layout Chain (lines 1047-1125)
battery_x = self.width - battery_width - 2  # 2px gap
age_x = battery_x - age_text_width - 4      # 4px gap
friends_icon_x = friends_text_x - 10 - 1    # 1px gap - inconsistent!
# Each value depends on previous - fragile chain
```

**DRY Violations:**

1. **Canvas creation** (16 locations):
```python
# Pattern repeated in draw_home, draw_menu, draw_text_input, etc.
image = Image.new('1', (self.width, self.height), 1)
draw = ImageDraw.Draw(image)
```

2. **Highlight rectangle** (15+ locations):
```python
# Lines 415-416, 476-478, 551-552, 660-661, 855-856, 962-963, 1020-1021, etc.
if i == selected_index:
    draw.rectangle([(x - 2, y_pos - 1), (self.width - 5, y_pos + item_height - 3)], fill=0)
    draw.text((x, y_pos), text, fill=1, font=self.font_small)
else:
    draw.text((x, y_pos), text, fill=0, font=self.font_small)
```

3. **Time formatting** (2 locations):
```python
# Lines 631-644 and 718-734
if age_secs < 60: time_str = "now"
elif age_secs < 3600: time_str = f"{int(age_secs / 60)}m"
elif age_secs < 86400: time_str = f"{int(age_secs / 3600)}h"
else: time_str = f"{int(age_secs / 86400)}d"
```

**Missing Abstractions:**
- No `ListScreen` base class despite 8 methods with identical structure
- No `HeaderLayout` class for complex header positioning
- No `_wrap_text()` helper despite 3 duplicate implementations

---

### screen_manager.py - CRITICAL

**OCP Violation (Adding a new screen requires):**

1. **config.py**: Add `ScreenState.NEW_SCREEN = "new_screen"` (1 line)
2. **screen_manager.py**:
   - Add state vars in `__init__` (2-5 lines)
   - Add elif in `set_screen()` (3-5 lines)
   - Add `_handle_*_input()` method (30-50 lines)
   - Add elif in `handle_input()` (1-2 lines)
   - Add `is_*()` method (1 line)
   - Add `get_*_state()` method (3-5 lines)
3. **main.py**:
   - Add `_render_*_screen()` method (10-20 lines)
   - Add elif in `_render_display()` (1-2 lines)

**Total: 60-90 lines across 3 files**

**State Management Issues:**
```python
# Lines 35-43 - Caches that can become stale
self.discovered_devices = []  # Updated by social_coordinator
self.friends_list = []        # Updated by social_coordinator
self.pending_requests = []    # Updated by social_coordinator
# No TTL, no validation, no cache versioning
```

**SRP Violation (ScreenManager has 8 responsibilities):**
1. State storage (23 instance variables)
2. Navigation (set_screen, go_back, go_home)
3. Input routing (14 handlers)
4. State initialization
5. Action callback registration
6. Data caching
7. State querying (17 is_* methods)
8. Rendering support (13 get_*_state methods)

---

### config.py - HIGH

**Derived Constants Should Calculate:**
```python
# Current (lines 55-64) - BUG PRONE
HEADER_HEIGHT = 14
PET_SPRITE_Y = 14            # Should be: HEADER_HEIGHT
STATUS_AREA_Y = 14           # Should be: HEADER_HEIGHT
STATUS_AREA_HEIGHT = 108     # Should be: DISPLAY_HEIGHT - HEADER_HEIGHT

# If HEADER_HEIGHT changes to 16, these 3 break silently!
```

**Test Values in Production:**
```python
# Lines 157-165 - Comments warn about this!
STAGE_THRESHOLDS = {
    1: 300,   # "for testing; change to 86400 for 1 day"
    2: 3600,  # "for testing; change to 259200 for 3 days"
    # Easy to ship wrong values
}
```

---

### main.py - MEDIUM

**DRY Violations:**
```python
# Pet sprite lookup repeated 12+ times (lines 564-908)
sprite_name = self.pet.get_current_sprite()
pet_sprite = self.sprite_manager.get_sprite_by_name(sprite_name)
if pet_sprite is None:
    pet_sprite = self.sprite_manager.create_placeholder_sprite()

# WiFi status repeated 12+ times
wifi_connected = self.wifi_manager.running if self.wifi_manager else False
online_friends = len(self.social_coordinator.get_friends(online_only=True)) if self.social_coordinator else 0
unread_messages = self.message_manager.get_unread_count() if self.message_manager else 0

# Care actions identical structure (lines 215-237)
def _action_feed(self):    # Same pattern as play, clean, sleep
    if self.pet is None: return
    changes = self.pet.feed()
    self.db.log_event(self.pet.id, "feed", stat_changes=changes)
    self._save_pet()
    self.action_occurred = True
    self.screen_manager.go_home()
```

---

## Refactoring Plan (Top 10 Issues)

### 1. Extract Derived Constants (config.py) - 15 min

**Current:**
```python
HEADER_HEIGHT = 14
PET_SPRITE_Y = 14
STATUS_AREA_Y = 14
STATUS_AREA_HEIGHT = 108
```

**Fix:**
```python
HEADER_HEIGHT = 14
PET_SPRITE_Y = HEADER_HEIGHT
STATUS_AREA_Y = HEADER_HEIGHT
STATUS_AREA_HEIGHT = DISPLAY_HEIGHT - HEADER_HEIGHT  # 122 - 14 = 108
```

### 2. Extract Highlight Drawing Helper (display.py) - 20 min

**Create:**
```python
def _draw_list_item(self, draw: ImageDraw.Draw, x: int, y: int,
                    text: str, selected: bool, item_height: int,
                    font=None) -> None:
    """Draw a list item with optional selection highlight."""
    font = font or self.font_small
    if selected:
        draw.rectangle(
            [(x - 2, y - 1), (self.width - 5, y + item_height - 3)],
            fill=0
        )
        draw.text((x, y), text, fill=1, font=font)
    else:
        draw.text((x, y), text, fill=0, font=font)
```

**Then replace 15+ occurrences.**

### 3. Extract Canvas Creation (display.py) - 10 min

**Create:**
```python
def _create_canvas(self) -> tuple[Image.Image, ImageDraw.Draw]:
    """Create a blank canvas for drawing."""
    image = Image.new('1', (self.width, self.height), 1)
    return image, ImageDraw.Draw(image)
```

**Replace 16 occurrences with:**
```python
image, draw = self._create_canvas()
```

### 4. Extract Time Formatting (display.py) - 10 min

**Create:**
```python
def _format_time_ago(self, timestamp: float) -> str:
    """Convert timestamp to relative time (now, 5m, 2h, 3d)."""
    age_secs = time.time() - timestamp
    if age_secs < 60:
        return "now"
    elif age_secs < 3600:
        return f"{int(age_secs / 60)}m"
    elif age_secs < 86400:
        return f"{int(age_secs / 3600)}h"
    else:
        return f"{int(age_secs / 86400)}d"
```

### 5. Extract Word Wrapping (display.py) - 15 min

**Create:**
```python
def _wrap_text(self, draw: ImageDraw.Draw, text: str,
               max_width: int, font) -> list[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
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
```

### 6. Define Header Layout Constants (display.py/config.py) - 20 min

**Add to config.py:**
```python
class HeaderLayout:
    BATTERY_WIDTH = 15
    BATTERY_GAP = 2
    ICON_SIZE = 10
    ICON_TEXT_GAP = 4
    ELEMENT_GAP = 4
```

### 7. Extract Pet Sprite Helper (main.py) - 10 min

**Use existing `_get_pet_sprite()` consistently** - it's defined at line 550 but only used in 3 of 12 places. Update remaining 9 methods.

### 8. Extract WiFi Status Helper (main.py) - 10 min

**Create:**
```python
def _get_header_status(self) -> dict:
    """Get common header status values."""
    return {
        'wifi_connected': self.wifi_manager.running if self.wifi_manager else False,
        'online_friends': len(self.social_coordinator.get_friends(online_only=True)) if self.social_coordinator else 0,
        'unread_messages': self.message_manager.get_unread_count() if self.message_manager else 0
    }
```

### 9. Separate Test vs Production Config (config.py) - 15 min

**Fix:**
```python
import os

ENVIRONMENT = os.getenv('NOTAGOTCHI_ENV', 'production')

_STAGE_THRESHOLDS_PROD = {
    0: 0, 1: 86400, 2: 259200, 3: 604800, 4: 1209600
}
_STAGE_THRESHOLDS_TEST = {
    0: 0, 1: 300, 2: 3600, 3: 86400, 4: 259200
}

STAGE_THRESHOLDS = _STAGE_THRESHOLDS_TEST if ENVIRONMENT == 'test' else _STAGE_THRESHOLDS_PROD
```

### 10. Create Generic List Screen Renderer (display.py) - 45 min

**Create:**
```python
def _draw_list_screen(self, title: str, items: list[str],
                      selected_index: int, pet_sprite: Optional[Image.Image],
                      wifi_connected: bool, online_friends: int,
                      unread_messages: int = 0,
                      item_height: int = 16,
                      visible_items: int = 5) -> Image.Image:
    """Generic list screen with header, pet sprite, and scrollable list."""
    image, draw = self._create_canvas()

    # Draw header
    self._draw_header(draw, title, "", wifi_connected,
                     online_friends, unread_messages)

    # Draw pet sprite
    if pet_sprite:
        image.paste(pet_sprite, (config.PET_SPRITE_X, config.PET_SPRITE_Y))

    # Draw list with scrolling
    x = config.STATUS_AREA_X + 5
    y_start = config.STATUS_AREA_Y + 5

    start_idx = max(0, selected_index - visible_items + 1)
    end_idx = min(len(items), start_idx + visible_items)

    for i in range(start_idx, end_idx):
        y_pos = y_start + (i - start_idx) * item_height
        self._draw_list_item(draw, x, y_pos, items[i],
                            i == selected_index, item_height)

    return image
```

**Then simplify 8 methods to use this helper.**

---

## Implementation Order

1. **Quick Wins (30 min total):** Issues 1, 3, 4 - immediate risk reduction
2. **DRY Reduction (45 min):** Issues 2, 5, 7, 8 - reduce duplication
3. **Architecture (60 min):** Issues 6, 10 - better abstractions
4. **Configuration (15 min):** Issue 9 - safer deployments

**Total estimated time: 2.5-3 hours**

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/modules/config.py` | Derive constants, add HeaderLayout, separate test config |
| `src/modules/display.py` | Add 5 helper methods, refactor 8 list screens |
| `src/main.py` | Use existing helpers consistently, add status helper |
| `src/modules/screen_manager.py` | (Future) Extract to smaller classes |

---

## Risk Assessment

| Refactoring | Risk | Mitigation |
|-------------|------|------------|
| Derived constants | Low | Simple calculation, easy to verify |
| Helper methods | Low | Extract without changing behavior |
| List screen refactor | Medium | Test each screen after refactoring |
| Config separation | Low | Test in both environments |

---

## Success Criteria

After refactoring:
- [ ] Adding a new stat bar requires editing 1 file (config) instead of display.py
- [ ] Changing highlight style requires editing 1 method instead of 15
- [ ] Adding a new list screen requires ~20 lines instead of 60+
- [ ] No magic numbers in layout positioning
- [ ] All derived constants calculate from sources
