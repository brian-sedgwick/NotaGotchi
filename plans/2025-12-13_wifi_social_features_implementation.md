# NotaGotchi WiFi Social Features Implementation Plan
**Date:** December 13, 2025
**Version:** 2.0 (WiFi-based, supersedes BLE plan v1.0)
**Status:** Ready for Implementation
**Timeline:** 3-4 weeks (60-80 hours)

---

## Executive Summary

This plan adapts the proven social features architecture to use **WiFi + mDNS** instead of BLE, leveraging the working test code we just validated. Key advantages:
- ✅ **Simpler implementation** - 3-4 weeks vs 4-6 weeks for BLE
- ✅ **Proven technology** - Working tests validate approach
- ✅ **Fewer integration issues** - Uses avahi directly (no port conflicts)
- ✅ **Better reliability** - TCP ensures message delivery
- ✅ **More connections** - 20-50 simultaneous vs BLE's 3-5

**Trade-off:** Devices must be on same WiFi network (acceptable for home use, documented requirement).

### Architecture Decisions (Based on User Input)

1. **Always-on Server**: TCP server + mDNS advertising runs continuously in background
   - Enables spontaneous message delivery to friends
   - Discovery UI only for finding NEW friends
   - Minimal power impact (~5mA for avahi daemon)

2. **WiFi Prerequisites**: Out of scope
   - Parent configures WiFi during Pi OS setup
   - NotaGotchi assumes network connectivity exists

3. **Message Queueing**: Full offline queue with retry
   - Messages queue locally if friend offline
   - Retry every 30 seconds with exponential backoff
   - Delivers automatically when friend comes online

4. **Message Types**: Complete feature set
   - Custom text messaging
   - Emoji selector (50 emojis, 5 categories)
   - Preset messages (100 presets, 7 categories)

---

## Phase 1: WiFi Foundation & Friend System (Week 1-2, 25-35 hours)

### 1.1 WiFi Manager Module (`wifi_manager.py`)

**Based on:** `test_wifi_server.py` + `test_wifi_discovery_avahi.py`

**Core Components:**
```python
class WiFiManager:
    def __init__(self, device_name, port=5555):
        self.device_name = device_name
        self.port = port
        self.server_thread = None
        self.running = False
        self.message_callbacks = []

    def start_server(self):
        """Start TCP server in background thread"""
        # Based on test_wifi_server.py
        # Binds to 0.0.0.0:5555
        # Registers with avahi/zeroconf
        # Handles connections in separate threads

    def discover_devices(self, duration=5):
        """Discover NotaGotchi devices via avahi-browse"""
        # Based on test_wifi_discovery_avahi.py
        # Returns list of {name, address, port, properties}

    def send_message(self, target_ip, target_port, message_data):
        """Send JSON message with acknowledgment"""
        # Based on test_wifi_client.py
        # Uses socket.shutdown(SHUT_WR) for proper TCP close
```

**Key Implementation Details:**
- Server runs in daemon thread (doesn't block main loop)
- Uses `threading.Lock()` for thread-safe callback invocation
- mDNS registration via `zeroconf.ServiceInfo` with explicit IP binding
- All JSON messages use UTF-8 encoding, max 8KB size

**Deliverables:**
- `src/modules/wifi_manager.py` (~400 lines)
- Background server with connection handling
- Discovery via avahi-browse subprocess
- Send/receive with acknowledgment
- Thread-safe callback system

**Testing:**
- Server starts and accepts connections
- Discovery finds test devices
- Messages send/receive successfully
- Acknowledgments work
- Thread safety verified (no race conditions)

---

### 1.2 Friend Management (`friend_manager.py`)

**Database Schema:**
```sql
CREATE TABLE friends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL UNIQUE,        -- "notagotchi_PetName"
    device_ip TEXT NOT NULL,               -- Last known IP
    pet_name TEXT NOT NULL,
    friendship_date REAL NOT NULL,
    last_seen REAL,
    last_ip TEXT,                          -- Track IP changes
    status TEXT DEFAULT 'active',
    created_at REAL NOT NULL DEFAULT (julianday('now'))
);

CREATE TABLE friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,       -- "freq_<uuid>"
    from_device_id TEXT NOT NULL,
    from_device_ip TEXT NOT NULL,
    from_pet_name TEXT NOT NULL,
    received_at REAL NOT NULL,
    expires_at REAL NOT NULL,              -- 24 hours
    status TEXT DEFAULT 'pending',         -- pending/accepted/rejected
    created_at REAL NOT NULL DEFAULT (julianday('now'))
);

CREATE INDEX idx_friends_status ON friends(status);
CREATE INDEX idx_requests_status ON friend_requests(status, expires_at);
```

**Friend Request Protocol:**
```json
{
  "version": 1,
  "message_type": "friend_request",
  "message_id": "freq_abc123",
  "from_device_id": "notagotchi_Buddy",
  "from_pet_name": "Buddy",
  "from_device_ip": "192.168.0.100",
  "action": "request|accept|reject",
  "timestamp": 1702345678.123,
  "requires_ack": true
}
```

**Friend Request Flow:**
```
User → Discovery Screen
  ↓
Select device → "Send Friend Request"
  ↓
WiFi Manager sends friend_request message
  ↓
Recipient gets notification
  ↓
Recipient accepts/rejects
  ↓
Response sent back to sender
  ↓
Both add to friends table (if accepted)
  ↓
Can now send messages
```

**Key Features:**
- Friendship is mutual (both must accept)
- Friend requests expire after 24 hours
- Can only message existing friends (friendship prerequisite)
- IP addresses updated on each contact
- "Last seen" tracks when friend was last online

**Deliverables:**
- `src/modules/friend_manager.py` (~350 lines)
- Database schema and migrations
- Friend request send/accept/reject
- Friend list management
- Friendship verification before messaging

---

### 1.3 UI Screens for Friends

**New Screen Types:**

1. **Device Discovery Screen** (menu: "Find Friends")
   - Lists nearby NotaGotchi devices (via avahi scan)
   - Shows signal strength (N/A for WiFi, but can show "Same Network")
   - "Send Friend Request" button for each device
   - Refresh button to scan again

2. **Friend Requests Screen** (notification badge)
   - Shows pending incoming requests
   - "Accept" / "Reject" buttons
   - Shows sender's pet name
   - Auto-navigates here when request received

3. **Friends List Screen** (menu: "Friends")
   - Lists all accepted friends
   - Shows online/offline status (last seen)
   - "Send Message" button for each
   - "Remove Friend" option

4. **Friend Details Screen**
   - Pet name, device ID
   - Friendship date
   - Last seen timestamp
   - Message history link
   - Remove friend option

**Integration with `screen_manager.py`:**
```python
# New screen states
SCREEN_DISCOVERY = "discovery"
SCREEN_FRIEND_REQUESTS = "friend_requests"
SCREEN_FRIENDS_LIST = "friends_list"
SCREEN_FRIEND_DETAILS = "friend_details"

# New menu items in MAIN_MENU
{"label": "Find Friends", "action": "discover_friends"}
{"label": "Friends", "action": "show_friends"}
{"label": "Messages", "action": "show_messages"}  # Added in Phase 2
```

**Deliverables:**
- `src/modules/social_screens.py` (~300 lines)
- 4 new UI screen renderers
- Navigation logic
- Real-time updates (friend comes online)

---

## Phase 2: Messaging System (Week 2-3, 20-30 hours)

### 2.1 Message Database Schema

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL UNIQUE,       -- "msg_<uuid>"
    from_device_id TEXT NOT NULL,
    to_device_id TEXT NOT NULL,
    content_type TEXT NOT NULL,            -- text/emoji/preset
    content TEXT NOT NULL,
    category TEXT,                         -- For emoji/preset
    sent_at REAL NOT NULL,
    delivered_at REAL,
    read_at REAL,
    status TEXT DEFAULT 'pending',         -- pending/delivered/read/failed
    direction TEXT NOT NULL,               -- sent/received
    created_at REAL NOT NULL DEFAULT (julianday('now')),
    FOREIGN KEY (from_device_id) REFERENCES friends(device_id),
    FOREIGN KEY (to_device_id) REFERENCES friends(device_id)
);

CREATE TABLE message_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL UNIQUE,
    to_device_id TEXT NOT NULL,
    to_device_ip TEXT NOT NULL,            -- Target IP
    message_json TEXT NOT NULL,            -- Full message as JSON
    retry_count INTEGER DEFAULT 0,
    next_retry_at REAL,
    last_error TEXT,
    created_at REAL NOT NULL DEFAULT (julianday('now')),
    FOREIGN KEY (to_device_id) REFERENCES friends(device_id)
);

CREATE INDEX idx_messages_conversation ON messages(from_device_id, to_device_id, sent_at);
CREATE INDEX idx_messages_unread ON messages(direction, read_at) WHERE direction = 'received';
CREATE INDEX idx_queue_retry ON message_queue(next_retry_at) WHERE retry_count < 10;
```

### 2.2 Message Protocol

**Text Message:**
```json
{
  "version": 1,
  "message_type": "text_message",
  "message_id": "msg_xyz789",
  "from_device_id": "notagotchi_Buddy",
  "from_pet_name": "Buddy",
  "to_device_id": "notagotchi_Charlie",
  "content_type": "text",
  "content": "Hello friend!",
  "timestamp": 1702345678.123,
  "requires_ack": true
}
```

**Emoji Message:**
```json
{
  "message_type": "text_message",
  "content_type": "emoji",
  "content": "happy",              // Emoji name
  "category": "faces"
}
```

**Preset Message:**
```json
{
  "message_type": "text_message",
  "content_type": "preset",
  "content": "Want to play together?",
  "category": "play"
}
```

**Acknowledgment:**
```json
{
  "message_type": "ack",
  "ack_message_id": "msg_xyz789",
  "status": "delivered",           // delivered/read
  "timestamp": 1702345679.456
}
```

### 2.3 Message Queue & Retry Logic

**Queue Processing** (runs every 30 seconds in background):
```python
def process_message_queue(self):
    """Process queued messages with retry logic"""
    # Get messages ready for retry
    messages = db.get_messages_for_retry()

    for msg_record in messages:
        # Check if friend is online (try to connect)
        if self.wifi_manager.is_device_reachable(msg_record['to_device_ip']):
            try:
                # Send message
                success = self.wifi_manager.send_message(
                    msg_record['to_device_ip'],
                    self.port,
                    json.loads(msg_record['message_json'])
                )

                if success:
                    # Mark as delivered
                    db.update_message_status(msg_record['message_id'], 'delivered')
                    db.remove_from_queue(msg_record['message_id'])
                else:
                    # Increment retry, update next_retry_at
                    self._schedule_retry(msg_record)
            except Exception as e:
                self._schedule_retry(msg_record, error=str(e))
        else:
            # Friend still offline, schedule next retry
            self._schedule_retry(msg_record)

def _schedule_retry(self, msg_record, error=None):
    """Schedule next retry with exponential backoff"""
    retry_count = msg_record['retry_count'] + 1

    if retry_count >= 10:
        # Max retries reached, mark as failed
        db.update_message_status(msg_record['message_id'], 'failed')
        db.remove_from_queue(msg_record['message_id'])
        return

    # Exponential backoff: 30s, 60s, 120s, 240s, ..., max 1800s (30 min)
    delay = min(30 * (2 ** retry_count), 1800)
    next_retry = time.time() + delay

    db.update_queue_retry(
        msg_record['message_id'],
        retry_count=retry_count,
        next_retry_at=next_retry,
        last_error=error
    )
```

**Key Features:**
- Messages queue if friend offline
- Retry every 30s initially, exponential backoff up to 30 min
- Max 10 retry attempts before marking as failed
- User sees "Queued" / "Sending..." / "Delivered" / "Read" status
- Failed messages show error in UI

### 2.4 Messaging UI Screens

**Message Compose Screen:**
- Select friend from friends list
- Choose message type: [Text] [Emoji] [Preset]
- Enter content or select from list
- Send button
- Shows "Sending..." → "Delivered" → "Read" status

**Inbox Screen:**
- Lists received messages
- Unread indicator (● vs ○)
- Shows sender, preview, timestamp
- Sort by date (newest first)
- Pagination (load 20 at a time)

**Message View Screen:**
- Full message content
- Sender name & pet avatar (if we add sprites)
- Timestamp
- Mark as read automatically
- Reply button (opens compose)

**Conversation History:**
- All messages with specific friend
- Grouped by date
- Sent messages on right, received on left
- Read receipts shown

**Deliverables:**
- `src/modules/messaging.py` (~450 lines)
- Message send/receive/queue/retry
- Queue processing in background
- Status tracking
- UI screens for messaging (~400 lines added to social_screens.py)

---

## Phase 3: Emoji & Preset Systems (Week 3, 15-20 hours)

### 3.1 Data Loading

**Emoji Definition:** `resources/emojis.json`
```json
{
  "faces": [
    {"name": "happy", "file": "emoji_happy.png", "label": "😊"},
    {"name": "sad", "file": "emoji_sad.png", "label": "😢"}
  ],
  "symbols": [],
  "food": [],
  "animals": [],
  "objects": []
}
```

**Preset Messages:** `resources/preset_messages.json`
```json
{
  "greetings": [
    "Hello!",
    "Good morning!",
    "How are you?"
  ],
  "play": [
    "Want to play together?",
    "Let's have fun!"
  ]
}
```

**Loading Module:** `src/modules/content_manager.py`
```python
class ContentManager:
    def __init__(self):
        self.emojis = self._load_emojis()
        self.presets = self._load_presets()

    def get_emoji_categories(self):
        """Returns list of emoji categories"""

    def get_emojis_in_category(self, category):
        """Returns emojis for category"""

    def get_preset_categories(self):
        """Returns list of preset categories"""

    def get_presets_in_category(self, category):
        """Returns preset messages for category"""
```

### 3.2 Emoji Selector UI

**Layout** (250x122 display):
```
┌────────────────────────────────────────┐
│ Select Emoji            [Category]     │ Header (14px)
├────────────────────────────────────────┤
│  😊   😢   😍   😠   😲             │ Row 1 (32px emojis)
│                                        │
│  😉   😴   🤔   😂   😭             │ Row 2
│                                        │
│ [▲ Scroll]                 [Cancel]   │ Footer (14px)
└────────────────────────────────────────┘
```

**Features:**
- 5 emojis per row
- 2 rows visible (10 emojis)
- Scroll up/down for more
- Category tabs at top
- Rotary encoder to navigate + select
- Emoji images: 16x16 PNG (create simple pixel art)

### 3.3 Preset Selector UI

**Layout:**
```
┌────────────────────────────────────────┐
│ Preset Messages         [Greetings]    │
├────────────────────────────────────────┤
│  ▶ Hello!                              │
│    Good morning!                       │
│    How are you?                        │
│    What's up?                          │
│    Nice to meet you!                   │
│                                        │
│ [Select]                   [Cancel]   │
└────────────────────────────────────────┘
```

**Features:**
- Category selector (7 categories)
- Scrollable list of presets
- Quick selection with encoder
- Preview full message before sending

### 3.4 Message Rendering

**Text with Emoji:**
- Render text using normal font
- Insert emoji images inline (16x16)
- Handle line wrapping around emojis
- E-ink display challenge: emoji clarity

**Creating Emoji Images:**
- Use 16x16 pixel art (simple black & white)
- Create 50 emojis over time (start with 10-15 most common)
- Use existing tools or draw manually
- Store in `resources/images/emojis/`

**Deliverables:**
- `src/modules/content_manager.py` (~200 lines)
- `resources/emojis.json` (50 emojis)
- `resources/preset_messages.json` (100 presets)
- `resources/images/emojis/*.png` (start with 15, expand later)
- Emoji selector UI (~150 lines added to social_screens.py)
- Preset selector UI (~150 lines added to social_screens.py)
- Emoji rendering in message view (~100 lines in display.py)

---

## Phase 4: Integration & Polish (Week 4, 15-20 hours)

### 4.1 Main App Integration

**`main.py` Changes:**
```python
from modules.wifi_manager import WiFiManager
from modules.friend_manager import FriendManager
from modules.messaging import MessagingSystem
from modules.content_manager import ContentManager

class NotAGotchiApp:
    def __init__(self, simulation_mode=False):
        # ... existing initialization ...

        # Social features (WiFi-based)
        if not simulation_mode:
            self.wifi_manager = WiFiManager(
                device_name=f"notagotchi_{self.pet.name}",
                port=5555
            )
            self.friend_manager = FriendManager(self.db, self.wifi_manager)
            self.messaging = MessagingSystem(
                self.db,
                self.wifi_manager,
                self.friend_manager
            )
            self.content_manager = ContentManager()

            # Start WiFi services
            self._start_wifi_services()
        else:
            # Simulation mode - no WiFi
            self.wifi_manager = None
            self.friend_manager = None
            self.messaging = None
            self.content_manager = None

    def _start_wifi_services(self):
        """Start WiFi server and mDNS advertising"""
        # Start TCP server in background
        self.wifi_manager.start_server()

        # Register message callback
        self.wifi_manager.register_callback(self._handle_incoming_message)

        # Start queue processor (runs every 30s)
        self._start_queue_processor()

    def _handle_incoming_message(self, message_data, sender_ip):
        """Handle incoming WiFi message"""
        msg_type = message_data.get('message_type')

        if msg_type == 'friend_request':
            # Handle friend request
            self.friend_manager.receive_friend_request(message_data)
            # Show notification
            self._show_friend_request_notification()

        elif msg_type == 'text_message':
            # Handle text message
            self.messaging.receive_message(message_data)
            # Show notification
            self._show_new_message_notification()

        elif msg_type == 'ack':
            # Handle acknowledgment
            self.messaging.handle_acknowledgment(message_data)

    def _start_queue_processor(self):
        """Start background thread for message queue processing"""
        def queue_loop():
            while self.running:
                try:
                    self.messaging.process_message_queue()
                except Exception as e:
                    print(f"Queue processor error: {e}")
                time.sleep(30)  # Process every 30 seconds

        thread = threading.Thread(target=queue_loop, daemon=True)
        thread.start()
```

### 4.2 Configuration Updates

**`config.py` additions:**
```python
# ============================================================================
# WIFI COMMUNICATION
# ============================================================================
WIFI_SERVICE_TYPE = "_notagotchi._tcp.local."
WIFI_PORT = 5555
WIFI_DISCOVERY_TIMEOUT = 5.0       # seconds
WIFI_CONNECTION_TIMEOUT = 10.0     # seconds
WIFI_MESSAGE_MAX_SIZE = 8192       # bytes (8KB)

# Device identification
DEVICE_ID_PREFIX = "notagotchi"    # Creates "notagotchi_PetName"

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
# CONTENT
# ============================================================================
EMOJI_IMAGE_SIZE = 16              # 16x16 pixels
EMOJI_FILE_PATH = "resources/images/emojis/"
EMOJI_JSON_PATH = "resources/emojis.json"
PRESET_JSON_PATH = "resources/preset_messages.json"
```

### 4.3 Menu Integration

**Updated `MAIN_MENU`:**
```python
MAIN_MENU = [
    {"label": "Feed", "action": "feed"},
    {"label": "Play", "action": "play"},
    {"label": "Clean", "action": "clean"},
    {"label": "Sleep", "action": "sleep"},
    {"label": "Friends", "action": "show_friends", "submenu": FRIENDS_MENU},
    {"label": "Reset Pet", "action": "reset"},
    {"label": "Back", "action": "back"}
]

FRIENDS_MENU = [
    {"label": "Friends List", "action": "friends_list"},
    {"label": "Messages", "action": "inbox"},
    {"label": "Find Friends", "action": "discover_friends"},
    {"label": "Requests", "action": "friend_requests", "badge": "pending_count"},
    {"label": "Back", "action": "back"}
]
```

### 4.4 Error Handling & Notifications

**Notification System:**
- **Friend Request Badge:** Red dot on "Friends" menu when pending request
- **Unread Messages Badge:** Number indicator on "Messages"
- **Delivery Status:** Show in message view (Sending... / Delivered / Read)
- **Connection Errors:** "Friend is offline" / "Network error" / "Message failed"

**Error Scenarios:**
1. **WiFi Down:** Detect with socket errors, show "No Network" warning
2. **Friend Offline:** Queue message, show "Queued for delivery" status
3. **Message Too Large:** Reject with error before sending
4. **Friend Not Found:** Should never happen (validate friend before sending)
5. **Server Not Responding:** Queue and retry with backoff

**Recovery Strategies:**
- All messages persist in database
- Queue survives app restart
- Friend IPs update automatically on next contact
- Retry logic handles temporary network issues

### 4.5 Testing & Debugging

**Test Checklist:**
- [ ] Server starts successfully on boot
- [ ] Discovery finds both test devices
- [ ] Friend request send/accept flow works
- [ ] Text message delivery (both online)
- [ ] Emoji message rendering
- [ ] Preset message selection
- [ ] Message queuing (friend offline)
- [ ] Message delivery after friend comes online
- [ ] Retry logic with exponential backoff
- [ ] Failed message handling (max retries)
- [ ] Multiple messages in quick succession
- [ ] Concurrent message processing
- [ ] App restart with pending queue
- [ ] Database integrity after crashes
- [ ] UI responsiveness during network operations

**Debug Tools:**
- Add `--wifi-debug` flag for verbose WiFi logging
- Log all network traffic to `data/network.log`
- Add `/wifi_status` debug screen showing:
  - Server status (running/stopped)
  - Current IP address
  - Friends online/offline
  - Queue size
  - Last error

**Deliverables:**
- Full integration into main.py (~200 lines changes)
- Config updates
- Menu structure
- Notification system
- Error handling throughout
- Debug tools
- Testing documentation

---

## Technical Implementation Details

### WiFi vs BLE Trade-offs

| Aspect | WiFi (This Plan) | BLE (Original Plan) |
|--------|------------------|---------------------|
| **Implementation Time** | ✅ 3-4 weeks | ❌ 4-6 weeks |
| **Code Complexity** | ✅ Simpler (TCP sockets) | ❌ Complex (GATT/characteristics) |
| **Library Maturity** | ✅ Excellent (avahi, sockets) | ❌ Abandoned/experimental |
| **Simultaneous Connections** | ✅ 20-50 | ❌ 3-5 |
| **Range** | ✅ 100m+ | ✅ 15-20m |
| **Power Consumption** | ❌ ~150mA active | ✅ ~10mA |
| **Setup Required** | ❌ Same WiFi network | ✅ None |
| **Portability** | ❌ Network dependent | ✅ Works anywhere |
| **Real-world Use Cases** | Home, school (same network) | ✅ Anywhere nearby |

**Decision:** WiFi is better for:
- Faster implementation (Christmas deadline)
- Proven reliability
- More concurrent connections
- Existing working code

**Limitation:** Requires same WiFi network (acceptable trade-off)

### Proven Architecture (From Working Tests)

**What We Validated:**
1. ✅ mDNS discovery via avahi-browse works reliably
2. ✅ TCP JSON messages with acknowledgment works
3. ✅ `socket.shutdown(SHUT_WR)` signals end of send correctly
4. ✅ Threaded server handles multiple connections
5. ✅ zeroconf service registration requires explicit IP binding
6. ✅ Multicast route required: `224.0.0.0/4 dev wlan0`
7. ✅ avahi-daemon conflicts with python-zeroconf on port 5353
8. ✅ Using avahi directly (subprocess) avoids conflicts

**What We'll Adapt:**
- Test server → Background daemon in main app
- Test client → MessagingSystem send method
- Test discovery → FriendManager discovery
- Manual testing → Automated message queue

### Prerequisites & Setup

**Hardware:**
- 2x Raspberry Pi Zero 2W (for testing)
- Both connected to same WiFi network
- E-ink displays installed

**Software Setup (One-time per Pi):**
```bash
# Install dependencies
pip3 install zeroconf

# Install avahi tools (if not present)
sudo apt-get install avahi-utils

# Add multicast route (persist across reboots)
./fix_mdns.sh  # Our script from testing

# Enable on boot (add to /etc/rc.local)
sudo sh -c 'echo "ip route add 224.0.0.0/4 dev wlan0" >> /etc/rc.local'
```

**WiFi Configuration (Parent Setup):**
```bash
# Parent connects Pi to WiFi during OS install
# Uses Raspberry Pi Imager WiFi settings
# Or: sudo raspi-config → System Options → Wireless LAN
```

**Verifying Setup:**
```bash
# Check WiFi connected
hostname -I

# Check avahi running
systemctl status avahi-daemon

# Check multicast route
ip route | grep 224.0.0.0

# Test discovery manually
avahi-browse _notagotchi._tcp -t
```

---

## Timeline & Milestones

### Week 1: WiFi Foundation (20-25 hours)
**Days 1-3:** WiFi Manager Module
- Port test_wifi_server.py to wifi_manager.py
- Background server thread
- Discovery via avahi-browse
- Send/receive with acks

**Days 4-5:** Friend Manager
- Database schema
- Friend request protocol
- Friendship verification

**Days 6-7:** Friend UI Screens
- Discovery screen
- Friend requests screen
- Friends list screen
- Testing

**Milestone:** Two devices can send friend requests and become friends

---

### Week 2: Messaging System (20-25 hours)
**Days 8-10:** Messaging Module
- Message database schema
- Send/receive text messages
- Message status tracking

**Days 11-12:** Message Queue & Retry
- Offline queue system
- Exponential backoff retry
- Background queue processor

**Days 13-14:** Messaging UI
- Compose screen
- Inbox screen
- Message view screen
- Conversation history

**Milestone:** Friends can send/receive text messages with queueing

---

### Week 3: Emoji & Presets (15-20 hours)
**Days 15-16:** Content Loading
- Create emoji/preset JSON files
- ContentManager module
- Load on startup

**Days 17-18:** Emoji System
- Create 15 initial emoji images
- Emoji selector UI
- Emoji rendering in messages

**Days 19-21:** Preset System
- Write 100 preset messages
- Preset selector UI
- Category navigation

**Milestone:** Can send emojis and preset messages

---

### Week 4: Integration & Polish (15-20 hours)
**Days 22-24:** Main App Integration
- Integrate all modules into main.py
- Background queue processor
- Notification system

**Days 25-26:** Error Handling
- Network error handling
- Offline scenarios
- Failed message UI

**Days 27-28:** Testing & Bug Fixes
- Two-device testing
- Edge cases
- Performance optimization
- Documentation

**Milestone:** Feature-complete social system ready for use

---

## Critical Path

```
WiFi Manager → Friend System → Basic Messaging → Queue/Retry → Emoji/Presets → Integration
   (MUST)         (MUST)           (MUST)           (MUST)         (MUST)        (MUST)
```

**No optional phases** - All features required for complete social experience.

---

## Risks & Mitigation

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Network reliability | High | Medium | Robust retry logic, queue system |
| Concurrent connections | Medium | Low | Thread-safe code, test with multiple devices |
| Message delivery failures | High | Medium | Persistent queue, exponential backoff, user feedback |
| IP address changes | Medium | Medium | Update IPs on each contact, rediscovery if needed |
| Database corruption | High | Low | Use WAL mode, transactions, regular backups |
| UI performance | Medium | Low | Pagination, lazy loading, background threads |

### WiFi-Specific Risks

| Risk | Solution |
|------|----------|
| **Both devices not on same network** | Document clearly, add debug screen showing network status |
| **Router firewall blocks mDNS** | Most home routers allow mDNS, document if needed |
| **WiFi disconnection** | Queue messages, auto-retry when reconnected |
| **IP changes after DHCP renewal** | IPs update on next contact, use device_id as primary key |

---

## Success Criteria

### Phase 1 Success
- ✅ WiFi server runs in background without blocking game
- ✅ Discovery finds other NotaGotchis on network
- ✅ Friend requests send and receive
- ✅ Friendship mutual acceptance works
- ✅ Can only message friends (prerequisite enforced)

### Phase 2 Success
- ✅ Text messages send/receive between friends
- ✅ Messages queue when friend offline
- ✅ Messages deliver automatically when friend comes online
- ✅ Retry logic works correctly (exponential backoff)
- ✅ Inbox shows unread count

### Phase 3 Success
- ✅ Can select and send emojis
- ✅ Can select and send preset messages
- ✅ Emojis render correctly in message view
- ✅ UI is intuitive and responsive

### Phase 4 Success
- ✅ All features integrated into main app
- ✅ Notifications work (friend requests, messages)
- ✅ Error handling is comprehensive
- ✅ No crashes or data loss
- ✅ Two devices can use all features simultaneously

### Overall Success
- ✅ Children can discover friends and send messages without help
- ✅ Messages reliably delivered (queued if offline)
- ✅ No data loss across restarts
- ✅ Performance is acceptable (<3s message delivery when online)
- ✅ Ready for Christmas gifting

---

## Conclusion

This WiFi-based social features plan provides a **realistic, implementable** path to adding messaging to NotaGotchi in 3-4 weeks. Key advantages over BLE:

1. **Proven Technology:** Built on working test code
2. **Faster Timeline:** 25% faster implementation
3. **Simpler Code:** TCP sockets vs GATT characteristics
4. **Better Support:** Mature libraries, extensive documentation
5. **More Reliable:** TCP guarantees delivery, easy debugging

**Trade-off Accepted:** Requires same WiFi network (documented limitation).

**Next Steps:**
1. ✅ Review and approve this plan
2. Run `fix_mdns.sh` on both test Pis (one-time setup)
3. Begin Phase 1: WiFi Manager implementation
4. Test continuously with two physical devices
5. Iterate based on real-world testing

**Estimated Completion:** January 10, 2026 (in time for post-Christmas gifting)
