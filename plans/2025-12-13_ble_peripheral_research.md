# BLE GATT Peripheral/Server Research for Raspberry Pi Zero 2W
**Date:** December 13, 2025
**Focus:** Practical, tested solutions for BLE peripheral implementation in Python

## Executive Summary

After extensive research into BLE GATT peripheral/server implementations on Raspberry Pi Zero 2W, the landscape in 2024-2025 is **challenging but workable** with the right approach. The key findings:

1. **bluez-peripheral is ABANDONED** (last update Dec 2022, no maintenance)
2. **Bless has compatibility issues** with BlueZ but is cross-platform
3. **btferret is the newest and most promising** (actively maintained, 2024+)
4. **Direct D-Bus approach works** but requires significant boilerplate
5. **Simpler alternatives exist** for peer-to-peer messaging (ble-serial, Nordic UART Service)

### Bottom Line Recommendation

**For Not-A-Gotchi peer-to-peer messaging:**
- **Best choice:** ble-serial library for simple UART-style communication
- **Alternative:** btferret for more control and mesh networking
- **Avoid:** bluez-peripheral (abandoned), full GATT server complexity

---

## 1. Library Status and Viability

### 1.1 bluez-peripheral
**Status:** ⚠️ ABANDONED - DO NOT USE

- **Last release:** 0.1.7 (December 19, 2022)
- **PyPI status:** Inactive - no releases in past 12+ months
- **Maintenance:** No pull request activity or issue updates
- **GitHub:** 53 stars, 10 forks
- **Security:** Scanned safe, but no active maintenance

**Verdict:** Despite being mentioned in many tutorials, this library is no longer maintained. Using it risks compatibility issues with newer BlueZ versions and no support for bug fixes.

### 1.2 Bless (Bluetooth Low Energy Server Supplement)
**Status:** ✅ ACTIVE but with Linux issues

- **Last release:** v0.2.6 (March 6, 2024)
- **GitHub:** 175 stars, 42 forks
- **Cross-platform:** Windows, macOS, Linux
- **API:** Similar to Bleak (good for learning)

**Known Issues (2024):**
- DBus access denied errors on Linux: "Connection is not allowed to own the service 'org.bluez.TestService'"
- BlueZ-to-BlueZ connection drops: Bleak clients connecting to Bless servers instantly disconnect on Ubuntu 22.04 with BlueZ 5.64
- Security policy conflicts with D-Bus configuration

**Verdict:** Works better on Windows/macOS than Linux. If you need cross-platform development/testing, it's useful, but expect friction on Raspberry Pi.

### 1.3 bluezero
**Status:** ✅ ACTIVE and well-maintained

- **Latest:** v0.9.1 (March 23, 2025) - recently updated!
- **GitHub:** ukBaz/python-bluezero (established project)
- **Requirements:** BlueZ 5.50+, works with Raspberry Pi OS
- **Focus:** Simplified API with "sensible defaults"
- **Documentation:** Extensive, with Raspberry Pi + micro:bit tutorials

**Features:**
- Peripheral and central support
- Nordic UART Service (NUS) examples
- Educational focus (good for STEM activities)
- Hides D-Bus complexity

**Verdict:** Solid choice for standard BLE operations. Good documentation and active maintenance. However, many BlueZ features still flagged as "experimental."

### 1.4 btferret
**Status:** ✅ NEW and HIGHLY RECOMMENDED

- **Released:** 2024 (forum posts from October 2024)
- **GitHub:** petzval/btferret - 207 stars, 29 forks
- **Languages:** Both C and Python
- **License:** MIT

**Key Features:**
- Operates at HCI level, **bypasses BlueZ service** (can stop bluetoothd)
- Connects to multiple Classic and LE devices simultaneously
- Mesh networking between Raspberry Pis
- Cross-platform: Raspberry Pi, Ubuntu, Windows (with Pi Zero 2W as dongle!)
- Excellent documentation: "has come out of many months struggling with the vagaries of bluez"

**Community Feedback:**
- "This looks fantastic... Well documented"
- "This is some fantastic code"
- "It will connect to Windows/Android/HC-05 devices when bluez often has problems"

**Real-world use case (Nov 2025):** Used to make Raspberry Pi 500+ work as Bluetooth keyboard

**Verdict:** This is the most interesting option. By operating at HCI level, it avoids BlueZ's D-Bus complexity and experimental feature flags. Fresh approach from someone who has "struggled with bluez for months."

### 1.5 ble-serial
**Status:** ✅ ACTIVE - Specialized tool

- **GitHub:** Jakeler/ble-serial - 358 stars, 46 forks
- **Focus:** "RFCOMM for BLE" - virtual serial port over BLE
- **Cross-platform:** Linux, Mac, Windows
- **Latest commits:** 259 commits (active development)

**What it does:**
- Creates virtual serial port (/dev/pts/x on Linux, COM port on Windows)
- Bridges BLE UART services to traditional serial I/O
- Transparent bridge: everything sent to virtual port transmitted via BLE

**Use case fit for Not-A-Gotchi:**
PERFECT for peer-to-peer messaging without full GATT complexity. Each device runs ble-serial, and you communicate over simple serial I/O.

**Verdict:** If your messaging needs are simple (send/receive text, emojis, presets), this is the easiest path. No GATT server code needed - just read/write to serial port.

---

## 2. Common Issues and Challenges

### 2.1 BlueZ Version Fragmentation
- **Problem:** Different BlueZ versions have different bugs and features
- **Ubuntu 20.04:** Ships with BlueZ 5.53 (outdated, missing features)
- **Recent versions:** 5.66-5.75 have introduced new bugs
- **2024 issues:** Updates overwrite configuration, break existing setups

**Impact:** January 2024 update (5.66-1+rpt1+deb12u1) broke SPP settings made with sdptool

### 2.2 D-Bus Complexity
- **Documentation:** "Likely the least documented major package in the entire Linux collection"
- **Security policies:** DBus access denied errors common
- **Permissions:** Need to be in bluetooth group (`sudo usermod -aG bluetooth $USER`)

### 2.3 Connection Stability Issues (2024)
**BlueZ-to-BlueZ connections:**
- Peripheral mode causes scan failures: "Failed to start discovery: org.bluez.Error.InProgress"
- Connections drop after 5 seconds (security requirement mismatch)
- Android pairing issues: devices disconnect after accepting pairing

**Solution:** Use "Just Works" security first, then try passkey options

### 2.4 Raspberry Pi Zero 2W Specific Issues
**Hardware discrepancy:**
- Advertised: Bluetooth 4.2 with BLE
- Reality: Some units report Bluetooth 4.1
- Missing feature: LE Data Length Extension (DLE) not supported

**Power considerations:**
- 100-200mA under typical load
- BLE advertising consumes power continuously
- Need sleep modes when inactive

---

## 3. Working Approaches and Examples

### 3.1 Direct D-Bus Implementation
**Status:** ✅ Works but requires significant code

**Best tutorial:** Punch Through - "Creating A BLE Peripheral With BlueZ"
- Written for Raspberry Pi 3+ running BlueZ 5.53
- Based on official BlueZ examples (example-gatt-server, example-advertisement)
- Full code available, well-documented

**Other resources:**
- BlueZ official: `bluez/test/example-gatt-server` (Python with dbus module)
- ukBaz.github.io: D-Bus and Bluez guide with dasbus library
- scribles.net: UART service tutorial

**Required components:**
1. GATT Service definition (org.bluez.GattService1)
2. GATT Application (org.bluez.GattApplication1)
3. Advertisement registration (separate from service!)
4. Agent for pairing (NoIoAgent for simple cases)

**Gotcha:** The Python example-gatt-server does NOT advertise by itself - must run example-advertisement separately.

### 3.2 Nordic UART Service (NUS)
**Purpose:** Industry standard for simple UART over BLE

**UUIDs:**
- Service: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- TX Characteristic: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (write)
- RX Characteristic: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (read/notify)

**Implementations:**
- **Bleak:** `examples/uart_service.py` - terminal program using NUS
- **CircuitPython BLE:** Simulated UART for bi-directional byte stream
- **bluezero:** NUS example based on Nordic spec
- **pynus:** NUS console in Python 3 using BlueZ/D-Bus
- **scribles.net:** Full GATT server with UART service tutorial

**Advantages:**
- Standardized (works with nRF Connect app for testing)
- Simple concept: two characteristics for TX/RX
- Well-documented across many platforms

**Perfect for Not-A-Gotchi:** Standard way to send messages between devices.

### 3.3 BLE Advertising without Connections
**Ultra-simple approach for broadcasting:**
- Advertising packets can contain data (temperature, ID, status)
- No GATT connection needed
- Scan response packets provide additional data

**Use case:** Device discovery, status broadcasting
**Limitation:** Small payload (31 bytes in advertising + 31 bytes scan response)
**Not suitable for:** Two-way messaging, large data

---

## 4. Simpler Alternatives for Peer-to-Peer

### 4.1 ble-serial (RECOMMENDED)
**Why it's simpler:**
- No GATT server code needed
- No characteristic/service definitions
- Standard Python serial I/O (`pyserial`)
- Built-in service discovery

**How it works:**
```python
# Device A runs ble-serial as server
# Device B runs ble-serial as client
# Both get virtual serial ports
# Communication is transparent serial I/O
```

**Setup:**
```bash
pip install ble-serial
ble-scan  # Find devices
ble-serial -d AA:BB:CC:DD:EE:FF  # Connect and get /dev/pts/X
# Now use any serial library to read/write
```

**Messaging example:**
```python
import serial
port = serial.Serial('/dev/pts/5', 9600)
port.write(b"Hello from Not-A-Gotchi!\n")
message = port.readline()
```

**Advantages:**
- One-time setup with ble-serial tool
- Familiar serial programming model
- No BLE/GATT knowledge required
- Works across Linux/Mac/Windows

**Limitations:**
- Requires ble-serial daemon running
- Point-to-point (not broadcast)
- Discovery still needs scanning

### 4.2 btferret Mesh Networking
**Use case:** Multiple Not-A-Gotchi devices in mesh

**Advantages:**
- Connect to multiple devices simultaneously
- Mesh network between Pis
- HCI-level control (no BlueZ dependency conflicts)
- Both C and Python APIs

**Learning curve:** Higher than ble-serial, but comprehensive documentation

**Best for:** If you want device-to-device AND multi-device networking

### 4.3 Classic Bluetooth Serial (RFCOMM)
**Alternative:** Skip BLE entirely, use Bluetooth 2.0 serial

**Advantages:**
- Well-established, stable
- PyBluez library is mature
- `rfcomm bind` creates serial ports
- Longer range than BLE

**Disadvantages:**
- Higher power consumption
- Not "modern" (BLE is standard for IoT)
- Raspberry Pi Zero 2W supports both anyway

**When to consider:** If BLE proves too problematic and range > battery life

---

## 5. Security and Pairing

### 5.1 "Just Works" Pairing
**Characteristics:**
- No user interaction required
- No MITM (Man-In-The-Middle) protection
- Provides encryption against passive eavesdropping
- Default for devices without I/O capabilities

**Security level:** Mode 1 Level 2
- Pairing required
- Encrypted connection
- Vulnerable to active attacks during pairing

**For Not-A-Gotchi:** Perfectly acceptable for children's toy
- Not handling sensitive data
- Simplifies user experience
- Standard for headsets, toys, fitness trackers

### 5.2 LE Secure Connections
**Modern standard (2024-2025):**
- Mandatory for Bluetooth 5+ certified devices
- Default on Android and iOS
- ECDH key exchange

**Implementation note:** BlueZ handles this automatically if hardware supports it

### 5.3 Connection Drop Issues
**5-second disconnect problem:**
- **Cause:** Client security requirements not met by server
- **Solution sequence:**
  1. Try "Just Works" first
  2. If fails, try passkey entry
  3. Check BlueZ version compatibility
  4. Verify agent is registered properly

**Code example (with agent):**
```python
from bluez_peripheral.agent import NoIoAgent
agent = NoIoAgent()  # Just Works pairing
await agent.register(bus)
```

---

## 6. Hardware Considerations

### 6.1 Raspberry Pi Zero 2W BLE Capabilities
**Specifications:**
- Bluetooth 4.2 (some units report 4.1)
- BLE support confirmed
- Onboard antenna
- Quad-core CPU (better than Zero W for concurrent operations)

**Known limitations:**
- No LE Data Length Extension on some units
- Power consumption: 100-200mA typical
- Cannot simultaneously run peripheral and scanning on some BlueZ versions

### 6.2 E-ink Display Compatibility
**Important:** BLE and e-ink display both use power efficiently
- E-ink only draws power during refresh
- BLE advertising is periodic, can be tuned
- Both are suitable for battery operation

**Threading consideration:**
- BLE services need event loop (asyncio)
- Display refresh should be separate thread
- Queue-based messaging between threads (from Bjorn pattern)

---

## 7. Testing and Debugging

### 7.1 Essential Tools
**nRF Connect (mobile app):**
- Android/iOS app by Nordic
- Essential for testing GATT server
- Can read characteristics, enable notifications
- Shows all services/characteristics
- Free and well-maintained

**ble-scan (included with ble-serial):**
```bash
ble-scan -t 30  # 30 second scan
ble-scan -d MAC_ADDRESS  # Deep scan (read services/characteristics)
```

**bluetoothctl (Linux built-in):**
```bash
bluetoothctl
scan on
devices
info MAC_ADDRESS
connect MAC_ADDRESS
```

### 7.2 Common Debugging Steps
1. **Check BlueZ version:** `bluetoothctl --version`
2. **Verify adapter is up:** `bluetoothctl show`
3. **Enable if needed:** `bluetoothctl power on`
4. **Check permissions:** `groups | grep bluetooth`
5. **Monitor D-Bus:** `dbus-monitor --system "interface='org.bluez.*'"`
6. **Check logs:** `sudo journalctl -u bluetooth -f`

### 7.3 Testing Strategy
**Development machine → Production Pi:**
1. Test on laptop/desktop Linux first
2. Verify with nRF Connect app
3. Test Pi-to-phone communication
4. Finally test Pi-to-Pi communication

**Why:** Faster iteration on desktop, easier debugging

---

## 8. Recommendations for Not-A-Gotchi

### 8.1 Immediate Implementation Path

**RECOMMENDED APPROACH: ble-serial + Nordic UART Service**

**Phase 1: Device Discovery (1-2 days)**
```python
# Use Bleak for scanning (central mode)
from bleak import BleakScanner

async def discover_notagotchis():
    devices = await BleakScanner.discover()
    return [d for d in devices if "NotaGotchi" in d.name]
```

**Phase 2: Messaging via ble-serial (2-3 days)**
1. Install ble-serial: `pip install ble-serial`
2. Run ble-serial daemon on each device
3. Use Python serial library for messaging
4. Implement message protocol (emoji, presets, custom text)

**Phase 3: Integration with Game Logic (2-3 days)**
1. Queue-based messaging (Bjorn pattern)
2. Background thread for BLE communication
3. Main thread for game logic and display
4. CSV logging of interactions

**Total estimate:** 5-8 days for BLE functionality

### 8.2 Alternative Approach (More Control)

**ADVANCED APPROACH: btferret library**

**Advantages:**
- More control over BLE operations
- HCI-level access (bypass BlueZ issues)
- Mesh networking capability
- Both Python and C APIs

**Use if:**
- You need multi-device mesh (not just peer-to-peer)
- You want to avoid BlueZ D-Bus complexity
- You're comfortable with lower-level BLE concepts

**Learning curve:** 1-2 weeks to master
**Implementation time:** 2-3 weeks

### 8.3 What NOT to Do

❌ **Don't use bluez-peripheral** - abandoned, no support
❌ **Don't write raw D-Bus code** - too much boilerplate
❌ **Don't implement full GATT server** - overkill for messaging
❌ **Don't assume BlueZ "just works"** - test early and often
❌ **Don't mix scanning and peripheral** - some BlueZ versions fail

### 8.4 Messaging Protocol Design

**Keep it simple:**
1. **Device discovery:** Advertising with "NotaGotchi" in name
2. **Connection:** Use NUS UUID for service discovery
3. **Message format:** JSON over serial
   ```json
   {
     "type": "emoji|preset|custom",
     "content": "😊",
     "from_id": "device_mac",
     "timestamp": 1234567890
   }
   ```

**Why JSON:**
- Easy to parse in Python
- Extensible for future features
- Human-readable for debugging
- Standard library support

---

## 9. Code Examples

### 9.1 Device Discovery with Bleak
```python
import asyncio
from bleak import BleakScanner

async def scan_for_notagotchis(timeout=10):
    """Scan for nearby Not-A-Gotchi devices."""
    devices = await BleakScanner.discover(timeout=timeout)

    notagotchis = []
    for device in devices:
        if device.name and "NotaGotchi" in device.name:
            notagotchis.append({
                "name": device.name,
                "address": device.address,
                "rssi": device.rssi
            })

    return notagotchis

# Usage
devices = asyncio.run(scan_for_notagotchis())
for d in devices:
    print(f"Found: {d['name']} at {d['address']} (RSSI: {d['rssi']})")
```

### 9.2 Simple Messaging with ble-serial
```python
import serial
import json
import time

class BLEMessenger:
    def __init__(self, port='/dev/pts/5'):
        self.ser = serial.Serial(port, 9600, timeout=1)

    def send_emoji(self, emoji):
        """Send emoji to connected device."""
        msg = {
            "type": "emoji",
            "content": emoji,
            "timestamp": int(time.time())
        }
        self.ser.write((json.dumps(msg) + '\n').encode())

    def send_preset(self, preset_id):
        """Send preset message by ID."""
        msg = {
            "type": "preset",
            "content": preset_id,
            "timestamp": int(time.time())
        }
        self.ser.write((json.dumps(msg) + '\n').encode())

    def receive_message(self):
        """Non-blocking read of incoming message."""
        if self.ser.in_waiting:
            line = self.ser.readline().decode().strip()
            return json.loads(line)
        return None

# Usage
messenger = BLEMessenger()
messenger.send_emoji("😊")

while True:
    msg = messenger.receive_message()
    if msg:
        print(f"Received {msg['type']}: {msg['content']}")
    time.sleep(0.1)
```

### 9.3 Nordic UART Service with bluezero
```python
from bluezero import peripheral
import asyncio

class NotaGotchiNUS:
    """Nordic UART Service for Not-A-Gotchi."""

    NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
    NUS_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # Write
    NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Notify

    def __init__(self, device_name="NotaGotchi"):
        self.device_name = device_name
        self.message_callback = None

    def on_message_received(self, value):
        """Called when data is written to RX characteristic."""
        message = bytes(value).decode('utf-8')
        if self.message_callback:
            self.message_callback(message)

    def send_message(self, message):
        """Send message via TX characteristic."""
        # Trigger notification on TX characteristic
        pass  # bluezero implementation

    async def start(self):
        """Start advertising and GATT server."""
        # Implementation with bluezero peripheral API
        pass

# Usage
nus = NotaGotchiNUS(device_name="NotaGotchi-A")
nus.message_callback = lambda msg: print(f"Received: {msg}")
asyncio.run(nus.start())
```

---

## 10. Timeline and Effort Estimate

### 10.1 Minimal Viable BLE (ble-serial approach)
**Week 1: Setup and Discovery**
- Days 1-2: Install ble-serial, test on development machine
- Days 3-4: Device discovery implementation with Bleak
- Day 5: Testing device discovery on Raspberry Pi

**Week 2: Messaging**
- Days 1-2: Serial messaging protocol (JSON over ble-serial)
- Days 3-4: Emoji and preset message integration
- Day 5: Testing Pi-to-Pi messaging

**Total: 10 days**

### 10.2 Full GATT Implementation (if needed later)
**Week 1-2:** Same as above
**Week 3: GATT Server**
- Research and implement Nordic UART Service
- Advertisement registration
- Pairing agent setup

**Week 4: Integration and Testing**
- Threading and event loop integration
- Game logic integration
- Stress testing and bug fixes

**Total: 4 weeks**

### 10.3 btferret Mesh Approach
**Week 1:** Learning btferret API and examples
**Week 2:** Basic connection and messaging
**Week 3:** Mesh networking setup
**Week 4:** Integration with game logic

**Total: 4 weeks**

---

## 11. Risk Assessment

### 11.1 Technical Risks

**HIGH RISK:**
- BlueZ version incompatibilities (mitigation: test early, document working version)
- Connection stability issues (mitigation: implement retry logic, "Just Works" pairing)
- Raspberry Pi Zero 2W performance with concurrent BLE + display (mitigation: threading, profiling)

**MEDIUM RISK:**
- D-Bus permission issues (mitigation: documented setup steps, user group management)
- Power consumption higher than expected (mitigation: tune advertising intervals, sleep modes)
- Range limitations in typical home (mitigation: set expectations, test in target environment)

**LOW RISK:**
- Message protocol design (mitigation: JSON is flexible and well-understood)
- Integration with existing game logic (mitigation: queue-based pattern from Bjorn)

### 11.2 Timeline Risks

**Optimistic (ble-serial):** 1-2 weeks
**Realistic (ble-serial):** 2-3 weeks
**Pessimistic (custom GATT):** 4-6 weeks

**Christmas delivery:** Feasible with ble-serial approach if started immediately

---

## 12. Conclusion and Action Items

### Final Recommendation: ble-serial + Nordic UART Service

**Why:**
1. ✅ Proven, working library (358 GitHub stars, active)
2. ✅ Simple API (standard serial I/O)
3. ✅ No GATT server code needed
4. ✅ Fast implementation (1-2 weeks)
5. ✅ Cross-platform testing capability
6. ✅ Nordic UART Service is industry standard

**What to avoid:**
- ❌ bluez-peripheral (abandoned)
- ❌ Raw D-Bus implementation (too complex)
- ❌ Bless on Linux (connection issues)

**Backup plan:** btferret if ble-serial proves insufficient

### Immediate Next Steps:

1. **Install ble-serial on development machine:** `pip install ble-serial`
2. **Test with two devices:** Laptop + phone with nRF Connect
3. **Verify Nordic UART Service:** Use nRF Connect to send/receive
4. **Prototype message protocol:** JSON over serial
5. **Test on Raspberry Pi Zero 2W:** Verify performance and stability
6. **Integrate with game logic:** Queue-based messaging
7. **Field test:** Two Pi units communicating in real-world scenario

### Success Criteria:

- ✅ Device discovery works reliably (< 10 second scan)
- ✅ Messages send/receive successfully (> 95% success rate)
- ✅ No impact on display refresh performance
- ✅ Battery life acceptable (> 8 hours with typical use)
- ✅ Range adequate for typical home (> 10 meters)

---

## References and Resources

### Documentation
- **ble-serial:** https://github.com/Jakeler/ble-serial
- **btferret:** https://github.com/petzval/btferret
- **bluezero:** https://github.com/ukBaz/python-bluezero
- **Bleak:** https://github.com/hbldh/bleak

### Tutorials
- **Punch Through (BlueZ peripheral):** https://punchthrough.com/creating-a-ble-peripheral-with-bluez/
- **scribles.net (UART service):** https://scribles.net/creating-ble-gatt-server-uart-service-on-raspberry-pi/
- **ukBaz D-Bus guide:** https://ukbaz.github.io/howto/python_dbus_bluez.html

### Community
- **Raspberry Pi Forums:** https://forums.raspberrypi.com/
- **BlueZ GitHub:** https://github.com/bluez/bluez

### Testing Tools
- **nRF Connect (mobile):** Nordic Semiconductor (Android/iOS)
- **bluetoothctl:** Built into Linux
- **ble-scan:** Included with ble-serial

---

**Document prepared:** December 13, 2025
**Research depth:** 39,000+ tokens across 15+ web sources
**Status:** Comprehensive, ready for implementation planning
