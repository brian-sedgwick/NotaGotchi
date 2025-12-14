# BLE-Serial Library Research for NotaGotchi Peer-to-Peer Communication

**Date:** 2025-12-13
**Research Focus:** Evaluating ble-serial Python library for bidirectional peer-to-peer communication between two Raspberry Pi Zero 2W devices

---

## Executive Summary

**VERDICT: ble-serial is NOT suitable for true peer-to-peer NotaGotchi communication.**

The ble-serial library requires **pre-designated roles** (one server/peripheral, one client/central). It cannot support the desired use case where two NotaGotchi devices discover each other dynamically and establish bidirectional communication without knowing in advance which device is the server.

### Key Limitations

1. **No Simultaneous Server/Client Mode**: Each ble-serial instance must be either server OR client, not both
2. **BlueZ Scanning Limitation**: Linux/BlueZ prevents scanning once peripheral mode is initialized
3. **Discovery Problem**: Both devices cannot advertise AND scan simultaneously for mutual discovery
4. **No Role Switching**: Library doesn't support dynamic role negotiation after initial connection

---

## Detailed Findings

### 1. Can Both Raspberry Pis Run ble-serial Server Mode?

**Answer: No - this won't work.**

If both devices run in server mode (peripheral):
- Both will advertise their services
- Neither will scan for the other
- No connection will ever be established
- Result: Two islands advertising to no one

**From the research:**
- ble-serial operates in **either** client (BLE central) or server (BLE peripheral) mode
- Mode is set with `-g {server,client}` or `--role {server,client}` parameter
- Default is client mode

### 2. Server Mode Commands and Configuration

#### Server Mode Setup

```bash
# Install server dependencies
pip install ble-serial[server]

# On Windows (additional requirement)
pip install https://github.com/gwangyi/pysetupdi/archive/refs/heads/master.zip
```

#### Starting Server

```bash
ble-serial -g server -s <SERVICE_UUID>
```

**Key server parameters:**
- `-g server` or `--role server`: Operate as BLE peripheral
- `-s SERVICE_UUID`: Define the service UUID (required)
- `-r READ_UUID`: Read characteristic (auto-generated if omitted)
- `-w WRITE_UUID`: Write characteristic (auto-generated if omitted)
- `-n GAP_NAME`: Custom display name (default: "BLE Serial Server {PID}")
- `-m MTU`: Maximum packet size (default: 20 bytes)
- `--permit {ro,rw,wo}`: Restrict transfer direction

#### Server Output Example

```
17:02:23.860 | INFO | linux_pty.py: Port endpoint created on /tmp/ttyBLE -> /dev/pts/6
17:02:23.860 | INFO | ble_server.py: Name/ID: BLE Serial Server 11296
17:02:23.860 | INFO | ble_server.py: Listener set up
17:02:23.860 | WARNING | uuid_helpers.py: No write uuid specified, derived from service 6e400001-b5a3-f393-e0a9-e50e24dcca9e -> 6e400002-b5a3-f393-e0a9-e50e24dcca9e
17:02:23.860 | WARNING | uuid_helpers.py: No read uuid specified, derived from service 6e400001-b5a3-f393-e0a9-e50e24dcca9e -> 6e400003-b5a3-f393-e0a9-e50e24dcca9e
17:02:23.864 | INFO | ble_server.py: Service 6e400001-b5a3-f393-e0a9-e50e24dcca9e
17:02:23.864 | INFO | ble_server.py: Write characteristic: 6e400002-b5a3-f393-e0a9-e50e24dcca9e: Nordic UART RX
17:02:23.864 | INFO | ble_server.py: Read characteristic: 6e400003-b5a3-f393-e0a9-e50e24dcca9e: Nordic UART TX
17:02:23.893 | INFO | ble_server.py: Server startup successful
17:02:23.893 | INFO | main.py: Running main loop!
```

#### Client Connection to Server

```bash
# Connect by service UUID (recommended for dynamic discovery)
ble-serial -g client -s 6e400001-b5a3-f393-e0a9-e50e24dcca9e

# Connect by MAC address
ble-serial -g client -d 20:91:48:4C:4C:54
```

### 3. Examples of Two Linux Devices Using ble-serial

**No documented examples found** of true peer-to-peer scenarios where both devices can initiate connections.

**What IS documented:**
- Multiple clients connecting to one server (hub-and-spoke model)
- One client connecting to multiple servers sequentially
- Automated reconnection via `helper/ble-autoconnect.py` script

**Example: One Server, Multiple Clients**

Server side:
```bash
ble-serial -g server -s 6e400001-b5a3-f393-e0a9-e50e24dcca9e
```

Client 1 side:
```bash
ble-serial -g client -s 6e400001-b5a3-f393-e0a9-e50e24dcca9e -p /tmp/ttyBLE1
```

Client 2 side:
```bash
ble-serial -g client -s 6e400001-b5a3-f393-e0a9-e50e24dcca9e -p /tmp/ttyBLE2
```

**Note:** This is NOT peer-to-peer - it's client-server architecture.

### 4. Is Server Mode Truly Bidirectional?

**Answer: Yes, within a connection.**

Once a client-server connection is established:
- Server can send data to client via read characteristic notifications
- Client can send data to server via write characteristic
- Data flows in both directions simultaneously
- TCP server mode also supports bidirectional communication

**From the documentation:**
> "The software acts as transparent bridge, everything sent to the virtual port gets transmitted to the BLE module and comes out of the TX pin there. Same in the other direction."

**Limitation:** This bidirectionality only works within an established connection. It does NOT solve the discovery problem.

### 5. Can One Device Be Both Server and Client Simultaneously?

**Answer: No, not with ble-serial. Maybe with raw BlueZ.**

#### ble-serial Limitations

- Each ble-serial instance operates in ONE role only
- Cannot run two instances on the same Bluetooth adapter simultaneously
- The `-g` flag is mutually exclusive (server OR client, not both)

#### Raw BlueZ Limitations

**From BlueZ Issue #914 (Concurrent BLE Peripheral and Central):**

A user reported attempting concurrent central and peripheral operations:

> "If I start with a peripheral device first... I can see my device advertising and I can connect to it. It won't scan once anything peripheral is initialized. I get the error: **Failed to start discovery: org.bluez.Error.InProgress**"

> "If I start as a Central first... With the controller connected as a Central once I type `discoverable on` the connection is dropped, I can't scan or do anything central related anymore."

**Status:** Issue closed as "not planned" - BlueZ team not prioritizing this fix.

#### Theoretical Possibility

Bluetooth 4.1+ specification supports dual-topology:
- Device can be simultaneously central and peripheral
- Device can connect to multiple centrals at same time
- Connection limit applies to TOTAL connections regardless of role

**However:** BlueZ implementation on Linux has significant limitations:
- Scanning fails once peripheral is initialized
- Advertising drops central connections
- No clean way to maintain both roles concurrently

#### Workarounds (Complex)

Some users have achieved limited success:
1. **Experimental mode:** Set `Experimental=true` in `/etc/bluetooth/main.conf`
2. **Stop/start scanning:** Pause scanning to connect, resume after
3. **Low-level HCI access:** Bypass BlueZ and use HCI user channel directly (requires kernel 3.13+)

**Reality:** These workarounds are fragile, undocumented, and unreliable for production use.

---

## Architectural Implications for NotaGotchi

### What We Need (Ideal Scenario)

```
NotaGotchi A          NotaGotchi B
    |                      |
    |-- Advertise -------->|
    |<------ Scan ---------|
    |                      |
    |<------ Advertise ----|
    |------- Scan -------->|
    |                      |
    [Connection Established]
    |<==== Bidirectional ====>|
```

Both devices:
1. Advertise their presence
2. Scan for other NotaGotchi devices
3. Establish connection when found
4. Exchange messages bidirectionally

### What ble-serial Offers

```
NotaGotchi A (SERVER)     NotaGotchi B (CLIENT)
    |                           |
    |---- Advertise ----------->|
    |                           |---- Scan
    |                           |
    [Connection Established]    |
    |<==== Bidirectional =====>|
```

**Problem:** Requires pre-designated roles. NotaGotchi B can only discover NotaGotchi A, never the reverse.

### Possible Workarounds for NotaGotchi

#### Option 1: Pre-Assigned Roles (Simplest)

**Designate roles at startup:**
- Each NotaGotchi has a unique ID (e.g., MAC address)
- Device with lower MAC = Server (peripheral)
- Device with higher MAC = Client (central)

**Pros:**
- Simple to implement with ble-serial
- Reliable connection establishment
- Known working pattern

**Cons:**
- Breaks symmetry (devices aren't truly equal peers)
- Server cannot discover new clients
- Not scalable to 3+ devices discovering each other

#### Option 2: Role Rotation (Complex)

**Periodically switch roles:**
- Device starts as server for 30 seconds
- If no connection, switch to client for 30 seconds
- Restart ble-serial with new role

**Pros:**
- Eventually both devices can discover each other
- Maintains peer symmetry conceptually

**Cons:**
- High connection latency (up to 60 seconds)
- ble-serial restart overhead
- Race conditions (both switch at same time)
- Fragile and error-prone

#### Option 3: Advertisement-Based Discovery (Recommended Alternative)

**Don't use ble-serial at all. Use Bleak + Bless directly:**

**Device A:**
```python
# Using Bless to advertise
server = BlessServer()
server.advertise(service_uuid="NOTAGOTCHI-SERVICE")

# Simultaneously using Bleak to scan
scanner = BleakScanner()
devices = await scanner.discover()
for device in devices:
    if "NOTAGOTCHI-SERVICE" in device.metadata:
        # Found another NotaGotchi!
        await connect_as_client(device)
```

**Device B:**
```python
# Same code - symmetric peer behavior
server = BlessServer()
server.advertise(service_uuid="NOTAGOTCHI-SERVICE")

scanner = BleakScanner()
devices = await scanner.discover()
# ...
```

**Pros:**
- True peer-to-peer discovery
- Both devices can find each other
- Lower-level control over BLE behavior

**Cons:**
- More complex Python code
- Must implement own message framing
- May still hit BlueZ limitations
- Requires testing on actual hardware

#### Option 4: Use Wi-Fi Instead

**Fall back to original plan (from CLAUDE.md):**

> "### Wi-Fi Communication
> Device-to-device communication enabling:
> - Discovery of Not-A-Gotchi units on local network
> - Data exchange between devices"

**Using Wi-Fi:**
- mDNS/Zeroconf for local network discovery
- TCP/UDP sockets for message exchange
- Both devices can advertise and discover symmetrically

**Pros:**
- Proven technology stack on Raspberry Pi
- Python libraries well-documented (Zeroconf, socket)
- True peer-to-peer without role limitations
- Higher bandwidth than BLE

**Cons:**
- Requires Wi-Fi network (not ad-hoc device-to-device)
- Higher power consumption than BLE
- Must be on same network

---

## Technical Deep Dive: Why BlueZ Prevents Simultaneous Operations

### The Root Cause

**Single Radio Limitation:**
- Raspberry Pi has ONE Bluetooth radio
- Radio can either transmit (advertise) OR receive (scan)
- While radio can time-slice between modes, BlueZ doesn't handle this well

**BlueZ State Machine:**
- When peripheral service is registered, BlueZ enters "advertising" state
- Scan request fails with `org.bluez.Error.InProgress`
- When central scan is active, BlueZ enters "discovering" state
- Starting advertising drops existing connections

### Low-Level Solutions (Advanced)

#### HCI User Channel (Bypass BlueZ)

**From search results:**
> "Write an advertising receiver by using Bluetooth HCI User Channel feature from the 3.13 kernel. The BlueZ source code contains samples in form of tools/ibeacon.c"

**What this means:**
- Direct HCI access bypasses BlueZ D-Bus API
- Full control over radio scheduling
- Can implement custom scan/advertise interleaving

**Drawbacks:**
- C programming required (or complex Python ctypes)
- Root privileges needed
- Bluetooth stack knowledge required
- High development complexity

#### hcitool + hcidump Method

**For advertisement monitoring:**
```bash
# Terminal 1: Start scanning
hcitool lescan

# Terminal 2: Dump raw advertisements
hcidump -R
```

**This allows:**
- Receiving raw advertisement data
- Bypassing BlueZ de-duplication
- Continuous monitoring

**But:**
- Command-line tools only
- Not suitable for programmatic control
- Can't simultaneously advertise and scan reliably

---

## Comparison: ble-serial vs. Alternative Approaches

| Feature | ble-serial | Bleak + Bless | Wi-Fi (mDNS) | Classic BT |
|---------|-----------|---------------|--------------|------------|
| **Peer-to-peer discovery** | ❌ No | ⚠️ Limited | ✅ Yes | ✅ Yes |
| **Bidirectional comms** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Role designation required** | ✅ Yes | ⚠️ Partial | ❌ No | ❌ No |
| **Python support** | ✅ Excellent | ✅ Good | ✅ Excellent | ✅ Good |
| **Raspberry Pi support** | ✅ Native | ✅ Native | ✅ Native | ✅ Native |
| **Power consumption** | ⚡ Low | ⚡ Low | ⚡⚡ Medium | ⚡⚡ Medium |
| **Range** | 📡 10m | 📡 10m | 📡📡 50m+ | 📡 10m |
| **Network required** | ❌ No | ❌ No | ✅ Yes | ❌ No |
| **Virtual serial port** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Development complexity** | 🟢 Low | 🟡 Medium | 🟢 Low | 🟡 Medium |
| **Reliability** | 🟢 High | 🟡 Untested | 🟢 High | 🟢 High |
| **Documentation** | 🟢 Good | 🟡 Fair | 🟢 Excellent | 🟢 Good |

**Legend:**
- ✅ Fully supported
- ⚠️ Limited/workarounds needed
- ❌ Not supported
- 🟢 Good / 🟡 Medium / 🔴 Poor

---

## Recommendations for NotaGotchi

### Immediate Decision Required

The project needs to choose between:

### 1. **Wi-Fi Communication (RECOMMENDED)**

**Use the original architecture from CLAUDE.md:**
- Local network device discovery via mDNS/Zeroconf
- TCP sockets for message exchange
- Python `zeroconf` library well-documented

**Implementation:**
```python
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser

# Register NotaGotchi service
info = ServiceInfo(
    "_notagotchi._tcp.local.",
    "NotaGotchi-{DEVICE_ID}._notagotchi._tcp.local.",
    addresses=[socket.inet_aton("192.168.1.100")],
    port=8888,
    properties={'device_id': DEVICE_ID, 'pet_name': PET_NAME}
)
zeroconf = Zeroconf()
zeroconf.register_service(info)

# Discover other NotaGotchi devices
class NotaGotchiListener:
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        # Found another NotaGotchi!
        connect_to_peer(info.addresses[0], info.port)
```

**Why this is best:**
- ✅ Proven technology
- ✅ True peer-to-peer
- ✅ Well-documented
- ✅ No role designation needed
- ✅ Already mentioned in project requirements
- ⚠️ Requires Wi-Fi network (acceptable for home use)

### 2. **BLE with Pre-Assigned Roles (FALLBACK)**

**If Wi-Fi is unacceptable, use ble-serial with deterministic roles:**

```python
import hashlib

def get_device_role():
    """Determine role based on MAC address"""
    mac = get_bluetooth_mac()
    hash_value = int(hashlib.md5(mac.encode()).hexdigest(), 16)
    return "server" if hash_value % 2 == 0 else "client"

role = get_device_role()

if role == "server":
    # Start ble-serial in server mode
    os.system("ble-serial -g server -s 6e400001-b5a3-f393-e0a9-e50e24dcca9e")
else:
    # Start ble-serial in client mode
    os.system("ble-serial -g client -s 6e400001-b5a3-f393-e0a9-e50e24dcca9e")
```

**Pros:**
- ✅ Uses ble-serial (simpler than raw Bleak/Bless)
- ✅ Deterministic (same device always same role)
- ✅ Reliable once connected

**Cons:**
- ❌ Not truly peer-to-peer
- ❌ Client must know server exists
- ❌ Server cannot discover clients
- ❌ Doesn't scale beyond 2 devices

### 3. **Custom BLE Implementation (HIGH RISK)**

**Use Bleak + Bless for full control:**
- Requires significant development
- May still hit BlueZ limitations
- Untested on Raspberry Pi Zero 2W
- High risk of discovery failures

**Only pursue if:**
- Wi-Fi is absolutely ruled out
- ble-serial asymmetry is unacceptable
- Team has BLE protocol expertise
- Sufficient testing time available

---

## Code Examples

### ble-serial Client Code (Python)

```python
import asyncio
import logging
from ble_serial.bluetooth.ble_client import BLE_client

def receive_callback(value: bytes):
    """Handle incoming messages from server"""
    print(f"Received from NotaGotchi: {value.decode()}")

async def send_message(ble: BLE_client, message: str):
    """Send message to server"""
    await asyncio.sleep(1.0)
    print(f"Sending: {message}")
    ble.queue_send(message.encode())

async def main():
    ADAPTER = "hci0"
    SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # Custom NotaGotchi service
    WRITE_UUID = None  # Auto-derive
    READ_UUID = None   # Auto-derive
    DEVICE = None      # Auto-discover by service

    ble = BLE_client(ADAPTER, 'NotaGotchi-Client')
    ble.set_receiver(receive_callback)

    try:
        # Connect to any device offering NotaGotchi service
        await ble.connect(DEVICE, "public", SERVICE_UUID, 10.0)
        await ble.setup_chars(WRITE_UUID, READ_UUID, "rw", False)

        # Run send loop and message sender
        await asyncio.gather(
            ble.send_loop(),
            send_message(ble, "Hello from NotaGotchi A!")
        )
    finally:
        await ble.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### ble-serial Server Code (Shell)

```bash
#!/bin/bash
# notagotchi_ble_server.sh

NOTAGOTCHI_SERVICE="6e400001-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_NAME="NotaGotchi-$(hostname)"

echo "Starting NotaGotchi BLE Server..."
ble-serial \
    -g server \
    -s "$NOTAGOTCHI_SERVICE" \
    -n "$DEVICE_NAME" \
    -p /tmp/ttyNotaGotchi \
    -m 244 \
    --permit rw \
    -v

# Read/write to /tmp/ttyNotaGotchi to communicate
```

---

## Conclusion

**ble-serial is fundamentally incompatible with NotaGotchi's peer-to-peer requirements.**

The library requires:
- ✅ Pre-designated roles (server/client)
- ✅ Client must actively discover server
- ✅ Server passively waits for client
- ❌ Cannot support symmetric peer discovery
- ❌ Cannot run both roles simultaneously

**Recommended path forward:**

1. **Primary approach:** Implement Wi-Fi communication as originally planned
2. **Fallback:** Use ble-serial with deterministic role assignment
3. **Avoid:** Custom BLE implementation (too complex, too risky)

**Next steps:**

1. Update `/Users/brian/source/personal/notagotchi/NotaGotchi/docs/03_BLUETOOTH_COMMUNICATION_GUIDE.md` → Change to Wi-Fi communication guide
2. Research Python Zeroconf library for local network discovery
3. Design message protocol for NotaGotchi device-to-device communication
4. Prototype Wi-Fi discovery on actual Raspberry Pi hardware

---

## References

### Documentation
- **ble-serial GitHub:** https://github.com/Jakeler/ble-serial
- **ble-serial PyPI:** https://pypi.org/project/ble-serial/
- **BlueZ Issue #914:** https://github.com/bluez/bluez/issues/914 (Concurrent Peripheral and Central)

### Python Libraries
- **Bleak (BLE client):** https://github.com/hbldh/bleak
- **Bless (BLE server):** https://github.com/kevincar/bless
- **Zeroconf (mDNS):** https://github.com/python-zeroconf/python-zeroconf

### Key Search Results
- "Concurrent BLE Peripheral and Central" discussions confirm BlueZ limitations
- "Using the ble-serial library directly" discussion #72 shows async usage patterns
- Multiple forum posts confirm no symmetric peer-to-peer BLE discovery on Linux/BlueZ

### Related NotaGotchi Files
- `/Users/brian/source/personal/notagotchi/NotaGotchi/CLAUDE.md` - Project architecture
- `/Users/brian/source/personal/notagotchi/NotaGotchi/docs/FEATURES.md` - Feature specifications
- `/Users/brian/source/personal/notagotchi/NotaGotchi/docs/03_BLUETOOTH_COMMUNICATION_GUIDE.md` - Needs updating to Wi-Fi

---

**Research completed:** 2025-12-13
**Recommendation:** Switch to Wi-Fi/mDNS for peer-to-peer communication
