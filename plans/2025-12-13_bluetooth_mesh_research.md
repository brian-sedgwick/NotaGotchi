# Bluetooth Mesh Networking Research for NotaGotchi

**Date:** December 13, 2025
**Research Focus:** Evaluating Bluetooth Mesh as peer-to-peer communication solution for 5-20 NotaGotchi devices on Raspberry Pi Zero 2W

---

## Executive Summary

**VERDICT: Bluetooth Mesh is NOT recommended for NotaGotchi's use case.**

While Bluetooth Mesh technically supports multiple devices discovering each other and provides true many-to-many communication, the implementation complexity, power consumption requirements, and lack of mature Python libraries make it **impractical for a Christmas deadline project**.

### Critical Findings

1. ✅ **Solves Discovery Problem:** Bluetooth Mesh uses connectionless advertising bearer, eliminating the "can't scan while advertising" limitation
2. ✅ **True Peer-to-Peer:** All devices are equal, no pre-assigned roles required
3. ❌ **High Implementation Complexity:** 2-6 months development timeline (vs. 1-2 weeks for Wi-Fi)
4. ❌ **Limited Python Support:** BlueZ mesh requires D-Bus integration, no mature high-level libraries
5. ❌ **High Power Consumption:** 100% duty cycle scanning (nodes always listening unless transmitting)
6. ❌ **Overkill for Use Case:** Mesh is designed for 100s-1000s of devices in smart home/industrial automation

### Bottom Line Recommendation

**For NotaGotchi peer-to-peer messaging between 5-20 devices:**
- **Best choice:** Wi-Fi with mDNS/Zeroconf (1-2 weeks, proven technology)
- **Acceptable fallback:** BLE with pre-assigned roles using ble-serial (2 weeks, asymmetric but workable)
- **Avoid:** Bluetooth Mesh (4-6 months, power-hungry, unnecessary complexity)

---

## 1. What is Bluetooth Mesh and How Does It Differ from BLE GATT?

### 1.1 Traditional BLE GATT Architecture

**Connection Model:**
- Central/Peripheral (master/slave) relationship
- Point-to-point star topology: one central connects to multiple peripherals
- Connection-oriented: devices negotiate GATT client/server data exchange after pairing
- Limited simultaneous connections: typically 8 maximum

**Discovery Process:**
- Peripherals advertise on 3 channels (37, 38, 39) at regular intervals
- Centrals scan these channels to discover advertisers
- **Critical limitation:** Most BlueZ implementations cannot scan while advertising (peripheral mode)

**Use Cases:**
- Wearables connecting to smartphones
- Sensors connecting to hubs
- IoT devices connecting to gateways
- **NOT suitable for:** Device-to-device mesh without central hub

### 1.2 Bluetooth Mesh Architecture

**Connection Model:**
- **Connectionless:** Uses only BLE advertising/scanning states, NO GATT connections
- Many-to-many topology: every node can communicate with every other node
- Flooding mechanism: messages are relayed by intermediate nodes until destination reached
- **No central device:** All nodes are equal peers (can be relay nodes)

**Communication Method:**
- All mesh data transmitted on advertising channels 37, 38, 39
- Nodes use **100% duty cycle scanning** (always listening unless transmitting)
- Messages sent immediately after random backoff time (not periodic advertising intervals)
- **Managed flood protocol:** Messages propagate through network with TTL limit (max 127 hops)

**Bearer Types:**
1. **ADV Bearer (Primary):** Connectionless advertising-based communication
   - Implemented on ALL mesh nodes
   - Uses broadcaster/observer roles
   - High reliability through message flooding

2. **GATT Bearer (Optional):** Connection-oriented proxy for non-mesh devices
   - Only implemented on Proxy Nodes
   - Allows smartphones/tablets to interact with mesh via GATT profile
   - Proxy nodes convert between ADV and GATT bearers

**Use Cases:**
- Smart home lighting (100+ bulbs)
- Building automation (1000+ sensors)
- Industrial monitoring (large-scale deployments)
- **Overkill for:** 5-20 children's toys exchanging simple messages

---

## 2. Does Bluetooth Mesh Solve the "Can't Scan While Advertising" Problem?

### Answer: YES - Completely Eliminates This Problem

**Why it works:**

1. **No Connection Required:** Mesh uses only advertising bearer, not GATT connections
   - Devices don't need to establish connections like traditional BLE
   - No need to switch between peripheral (advertising) and central (scanning) roles

2. **All Nodes Are Observers:** Every mesh node continuously scans for advertising packets
   - 100% duty cycle: always listening for mesh messages
   - No state switching between advertising and scanning modes

3. **All Nodes Are Broadcasters:** Every mesh node can transmit advertising packets
   - Transmit occurs during short windows after random backoff
   - Doesn't interfere with continuous scanning

4. **Time-Slicing at Protocol Level:** Mesh protocol handles transmit/receive scheduling
   - Managed flood ensures messages propagate efficiently
   - Collision avoidance through randomized transmission timing

**Comparison:**

| Aspect | BLE GATT (Problem) | Bluetooth Mesh (Solution) |
|--------|-------------------|---------------------------|
| **Role switching** | Required (peripheral ↔ central) | Not needed (all nodes equal) |
| **BlueZ limitation** | "Error.InProgress" when scanning during advertising | N/A - uses only ADV bearer |
| **Discovery** | Asymmetric (one advertises, one scans) | Symmetric (all flood messages) |
| **State management** | Complex (connection states) | Simple (connectionless) |

**Trade-off:** Solves discovery problem at the cost of continuous scanning (high power consumption)

---

## 3. Python Libraries for Bluetooth Mesh on Raspberry Pi

### 3.1 BlueZ Mesh Support (Official, Limited)

**Status:** ✅ Available but difficult to use

**Version Requirements:**
- BlueZ v5.47+: Initial mesh support introduced
- BlueZ v5.50+: Recommended for full mesh features
- Raspberry Pi OS default: Usually has compatible BlueZ version

**Tools Provided:**
- `meshctl`: CLI tool for provisioning mesh devices (GATT bearer)
- `mesh-cfgclient`: Create mesh networks over advertising bearer (PB-ADV)
- `bluetooth-meshd`: Mesh networking daemon

**Major Limitation:**
- **Provisioning tools only:** meshctl is designed for provisioning devices, not for regular mesh node operation
- **D-Bus API:** BlueZ mesh uses D-Bus interface (complex, low-level)
- **No high-level Python wrapper:** Must interact with D-Bus directly

**Kernel Requirements:**
- Default Raspberry Pi kernel missing crypto modules needed for mesh
- **Must recompile kernel** with crypto drivers enabled
- Specific modules needed: CMAC, ECB, CCM AES cipher modes
- Error if missing: "Bluetooth Mesh unsupported due to missing crypto modules" (GitHub issue #3628)

**Developer Study Guides Available:**
- Bluetooth SIG published official guides for deploying BlueZ v5.50 on Raspberry Pi 3/4
- Focus: Creating Bluetooth Mesh provisioner (not regular nodes)
- PDF guides available but 50+ pages, highly technical

### 3.2 python-bluetooth-mesh (Silvair)

**Status:** ⚠️ Exists but limited documentation

**Repository:** https://github.com/SilvairGit/python-bluetooth-mesh
**PyPI:** https://pypi.org/project/bluetooth-mesh/ (v0.1.0, January 2024)

**What it provides:**
- Python library for Bluetooth Mesh
- Uses `dbussy` library for D-Bus asyncio integration
- Examples available in repository

**Limitations:**
- Very limited documentation
- Few examples (mostly low-level)
- Small community (not widely adopted)
- Requires understanding of Bluetooth Mesh specification
- Still requires BlueZ mesh daemon running

**Example code exists:** See GitHub repo for basic usage patterns, but steep learning curve

### 3.3 btferret Library

**Status:** ✅ Active, but uses CUSTOM mesh (not SIG standard)

**Repository:** https://github.com/petzval/btferret (207 stars, MIT license)
**Released:** 2024, actively maintained

**Key Features:**
- Both C and Python APIs
- "Simple mesh network for multiple Pis"
- Operates at HCI level (bypasses BlueZ)
- Works on Raspberry Pi, Ubuntu, Windows

**Critical Caveat:**
> "Uses advertising packets... would be incompatible with any SIG mesh advert packets"

**What this means:**
- **NOT Bluetooth Mesh standard:** Uses custom protocol over advertising
- Devices using btferret mesh cannot communicate with standard Bluetooth Mesh devices
- Proprietary implementation (only btferret devices can communicate)
- **Advantage:** Simpler to use than full Bluetooth Mesh
- **Disadvantage:** Lock-in to btferret library, no interoperability

**Best for:** Quick mesh prototyping without full Bluetooth SIG compliance

### 3.4 Zephyr RTOS (Alternative Platform)

**Status:** ✅ Mature, but requires C programming

**What it is:**
- Real-time operating system with full Bluetooth Mesh stack
- Industry-standard for embedded Bluetooth Mesh devices
- Used in commercial mesh products

**Limitations for NotaGotchi:**
- ❌ Requires C programming (not Python)
- ❌ Different OS than Raspberry Pi OS (Linux)
- ❌ Would need to port entire NotaGotchi application
- ❌ Steep learning curve for embedded development

**Verdict:** Not practical for this project

### 3.5 Summary: Python Library Landscape

| Library | Maturity | Ease of Use | Standard Compliant | Raspberry Pi Support |
|---------|----------|-------------|-------------------|---------------------|
| **BlueZ meshctl** | 🟡 Mature | 🔴 CLI only | ✅ Yes | ✅ Yes |
| **python-bluetooth-mesh** | 🟡 New | 🟡 Medium | ✅ Yes | ✅ Yes |
| **btferret** | 🟢 Active | 🟢 Good | ❌ No | ✅ Yes |
| **Zephyr** | 🟢 Mature | 🔴 C only | ✅ Yes | ⚠️ Different OS |

**Reality:** No mature, easy-to-use Python library for standard Bluetooth Mesh on Raspberry Pi

---

## 4. Working Examples of Bluetooth Mesh on Raspberry Pi

### 4.1 Official Examples (BlueZ)

**Available in BlueZ source code:**
- `test/example-mesh-client` - Basic mesh client operations
- `tools/meshctl` - Interactive mesh provisioning tool
- Raspberry Pi as Bluetooth Mesh Provisioner tutorials

**What they demonstrate:**
- Provisioning new devices into mesh network
- Configuring mesh node models
- Sending configuration messages

**What they DON'T demonstrate:**
- Application-layer messaging (only low-level configuration)
- Python integration (mostly C code)
- Real-world use cases (just provisioning examples)

### 4.2 Community Examples

**Raspberry Pi Forums:**
- Multiple threads asking "Is it possible to implement bluetooth mesh network on Pi?"
- Responses generally: "Yes, but it's complex"
- No complete working projects shared publicly

**GitHub Repositories:**
- `bartn1k/pi-btmesh`: Backups of SD card images with BlueZ Mesh configured
  - No code, just pre-configured system images
  - Shows that setup is complex enough to warrant full image backups

**Blog Tutorials:**
- "Set Up a Bluetooth Mesh Network with Raspberry Pi" (pidiylab.com)
  - Focuses on setup and provisioning
  - Uses BlueZ + meshctl + Python backend
  - Python backend connects to meshctl (not direct mesh API)

### 4.3 Industrial/Commercial Examples

**Silicon Labs Development Kits:**
- Bluetooth Mesh Developer Journey documentation
- Examples use Silicon Labs hardware, not Raspberry Pi

**Nordic Semiconductor:**
- nRF52/nRF53 development boards with mesh examples
- Uses Nordic SDK (C-based), not Python

**Texas Instruments:**
- CC13x2/CC26x2 SimpleLink with BLE5-Stack mesh support
- Embedded C development, not Raspberry Pi Linux

### 4.4 Reality Check

**Working examples are scarce because:**

1. **Bluetooth Mesh is relatively new:** Standard published in 2017, still maturing
2. **Commercial focus:** Most implementations are in commercial products (lights, sensors)
3. **Embedded development:** Mesh typically runs on microcontrollers (nRF52, ESP32), not Linux
4. **Provisioning vs. Operation:** Most Raspberry Pi examples show provisioning (one-time setup), not ongoing mesh communication
5. **Python gap:** Bluetooth Mesh ecosystem is C-centric, Python libraries lag behind

**Conclusion:** Very few hobbyist-friendly, Python-based, Raspberry Pi mesh examples exist

---

## 5. Limitations of Bluetooth Mesh

### 5.1 Network Size and Performance

**Theoretical Limits:**
- **Maximum nodes:** 32,767 (16-bit address space)
- **Maximum hops:** 127 (TTL limit)
- **Practical limits:** Unknown, depends on network density and traffic

**Realistic Limits (from research):**
- Tested networks typically 10-100 nodes
- Performance degrades with network size due to flooding
- Collision probability increases with more simultaneous transmissions

**For NotaGotchi (5-20 devices):**
- ✅ Well within limits
- Network size is NOT a limitation

### 5.2 Message Size Limitations

**Payload Sizes:**
- **Unsegmented messages:** 15 bytes
- **Segmented messages:** 384 bytes maximum (32 segments × 12 bytes)
- **Most messages:** Fit in single 11-byte segment

**Access Layer PDU:**
- Application data: 1-380 bytes
- Transport layer adds encryption/authentication overhead

**For NotaGotchi messaging:**
- Emoji: 1-4 bytes (UTF-8)
- Preset ID: 1-2 bytes
- Custom text: Up to 380 bytes
- ✅ Message size is NOT a limitation

**Bandwidth Considerations:**
- Mesh is **not designed for high-throughput data transfer**
- Command/control applications: ✅ Suitable
- Streaming/bulk data: ❌ Unsuitable
- NotaGotchi (occasional messages): ✅ Suitable

### 5.3 Power Consumption

**Critical Limitation: HIGH POWER CONSUMPTION**

**Mesh Node Power Profile:**
- **100% duty cycle scanning:** Always listening for mesh messages
- No sleep modes for relay nodes
- Much higher than traditional BLE (periodic scanning)

**Battery Life Research Findings:**
- **Regular mesh node:** Requires mains power or large battery
- **Low Power Node (LPN):** Special node type with friend relationship
  - LPN polls Friend Node periodically instead of continuous scanning
  - With 235 mAh battery: 15.6 months (sending message every 10 seconds)
  - ReceiveWindow size significantly affects power consumption

**Friend/LPN Architecture:**
- **Friend Node:** Regular mesh node that buffers messages for LPN
- **Low Power Node:** Sleeps most of the time, wakes to poll Friend
- Reduction in scanning time: Up to 66.65% with optimized friendship mechanism
- Lifetime improvement: 19.81% compared to standard friendship

**For NotaGotchi:**
- ❌ **High power consumption is MAJOR concern**
- Raspberry Pi Zero 2W typical consumption: 100-200mA
- Bluetooth Mesh continuous scanning: Adds significant overhead
- Battery-powered operation: Would drain quickly without LPN mode
- **LPN mode limitations:**
  - Requires Friend Node (another NotaGotchi or permanent hub)
  - Messages not received in real-time (only when polling)
  - Delays communication (not suitable for interactive toy)

### 5.4 Implementation Complexity

**Setup Complexity:**
- Recompile Raspberry Pi kernel for crypto modules
- Configure BlueZ mesh daemon
- Provision devices into mesh network
- Configure node models and publish/subscribe addresses

**Provisioning Process:**
1. Unprovisioned device advertises provisioning beacons
2. Provisioner discovers and initiates provisioning
3. Public key exchange (ECDH)
4. Authentication (OOB or Just Works)
5. Distribution of network key, device key, IV index
6. Configuration of node (models, publish/subscribe)

**Development Complexity:**
- Understand Bluetooth Mesh specification (250+ pages)
- Learn BlueZ D-Bus API
- Implement provisioning logic
- Handle network key management
- Configure publish/subscribe model
- Test multi-hop message relay

**Comparison:**

| Approach | Setup Steps | Code Complexity | Documentation | Testing Difficulty |
|----------|-------------|-----------------|---------------|-------------------|
| **Wi-Fi (mDNS)** | Install Zeroconf library | Low | Excellent | Easy |
| **BLE (ble-serial)** | Install ble-serial | Low | Good | Medium |
| **Bluetooth Mesh** | Kernel recompile + BlueZ config + Provisioning | High | Poor | High |

### 5.5 Lack of Mature Tooling

**What's missing for Raspberry Pi + Python:**
- ❌ High-level Python library (like Bleak for BLE)
- ❌ Comprehensive examples for application messaging
- ❌ GUI tools for network monitoring and debugging
- ❌ Good documentation for non-embedded developers

**What exists:**
- ✅ Low-level BlueZ D-Bus API (complex)
- ✅ Provisioning tools (meshctl, mesh-cfgclient)
- ⚠️ python-bluetooth-mesh (minimal documentation)
- ⚠️ Bluetooth SIG specification (highly technical)

---

## 6. Implementation Difficulty Compared to Wi-Fi mDNS

### 6.1 Wi-Fi with mDNS/Zeroconf (RECOMMENDED)

**Implementation Steps:**

1. **Install library** (5 minutes)
   ```bash
   pip install zeroconf
   ```

2. **Service registration** (1 hour, ~50 lines Python)
   ```python
   from zeroconf import Zeroconf, ServiceInfo
   import socket

   info = ServiceInfo(
       "_notagotchi._tcp.local.",
       "NotaGotchi-A._notagotchi._tcp.local.",
       addresses=[socket.inet_aton("192.168.1.100")],
       port=8888,
       properties={'device_id': 'A', 'pet_name': 'Buddy'}
   )
   zeroconf = Zeroconf()
   zeroconf.register_service(info)
   ```

3. **Service discovery** (1 hour, ~30 lines Python)
   ```python
   from zeroconf import ServiceBrowser

   class NotaGotchiListener:
       def add_service(self, zc, type_, name):
           info = zc.get_service_info(type_, name)
           # Found peer, connect via TCP socket

   browser = ServiceBrowser(zc, "_notagotchi._tcp.local.", NotaGotchiListener())
   ```

4. **Messaging via TCP sockets** (2-3 hours, ~100 lines Python)
   ```python
   import socket
   import json

   # Server
   server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   server.bind(('0.0.0.0', 8888))
   server.listen()

   # Client
   client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   client.connect((peer_address, 8888))
   client.send(json.dumps({"type": "emoji", "content": "😊"}).encode())
   ```

5. **Integration and testing** (2-3 days)

**Total Timeline:** 1-2 weeks
**Difficulty:** Low (Python socket programming, well-documented)
**Power Consumption:** Medium (Wi-Fi active)
**Reliability:** High (TCP guarantees delivery)

### 6.2 Bluetooth Mesh Implementation

**Implementation Steps:**

1. **Kernel recompilation** (2-4 hours)
   - Configure kernel crypto modules
   - Compile kernel
   - Install and reboot
   - Test mesh support

2. **BlueZ mesh setup** (4-8 hours)
   - Configure bluetooth-meshd
   - Create mesh network configuration
   - Generate node keys
   - Debug D-Bus permissions

3. **Python D-Bus integration** (1-2 days)
   - Learn BlueZ mesh D-Bus API
   - Implement node initialization
   - Handle provisioning callbacks
   - Debug asynchronous D-Bus signals

4. **Provisioning implementation** (2-3 days)
   - Implement provisioner logic
   - Create unprovisioned device beacons
   - Handle authentication
   - Configure node after provisioning

5. **Mesh model implementation** (1-2 weeks)
   - Define custom vendor model or use standard models
   - Implement publish/subscribe logic
   - Handle model callbacks
   - Test message propagation

6. **Multi-device testing** (1 week)
   - Provision 5+ devices
   - Test message routing
   - Debug message loss
   - Optimize network performance

7. **Power optimization** (3-5 days)
   - Implement LPN mode (if needed)
   - Configure Friend relationships
   - Test battery life
   - Balance responsiveness vs. power

8. **Integration with NotaGotchi** (1-2 weeks)
   - Thread management (mesh stack runs in background)
   - Message queue integration
   - Display update coordination
   - Error handling and recovery

**Total Timeline:** 2-3 months (realistic), 4-6 months (pessimistic)
**Difficulty:** High (embedded networking, cryptography, low-level BLE)
**Power Consumption:** High (100% duty cycle scanning)
**Reliability:** Medium (flooding provides redundancy, but complexity introduces bugs)

### 6.3 Direct Comparison

| Criterion | Wi-Fi (mDNS) | Bluetooth Mesh |
|-----------|--------------|----------------|
| **Setup complexity** | 🟢 Very low | 🔴 Very high |
| **Code complexity** | 🟢 Low (~200 lines) | 🔴 High (1000+ lines) |
| **Python library maturity** | 🟢 Excellent | 🔴 Poor |
| **Documentation quality** | 🟢 Excellent | 🟡 Technical specs only |
| **Example code available** | 🟢 Many examples | 🔴 Very few |
| **Development timeline** | 🟢 1-2 weeks | 🔴 2-6 months |
| **Debugging difficulty** | 🟢 Standard networking tools | 🔴 Specialized BLE tools |
| **Power consumption** | 🟡 Medium | 🔴 High |
| **Range** | 🟢 50m+ (Wi-Fi router) | 🟡 10m per hop |
| **Peer discovery** | 🟢 True symmetric | 🟢 True symmetric |
| **Message reliability** | 🟢 TCP guarantees | 🟡 Flooding (probabilistic) |
| **Network requirement** | ⚠️ Needs Wi-Fi router | 🟢 Ad-hoc mesh |
| **Scalability (5-20 devices)** | 🟢 Trivial | 🟢 Easy |

**Score:**
- **Wi-Fi:** 10/12 green, 2/12 yellow, 0/12 red
- **Bluetooth Mesh:** 2/12 green, 3/12 yellow, 7/12 red

**Winner:** Wi-Fi with mDNS (by a large margin)

---

## 7. Does BlueZ Support Bluetooth Mesh Properly?

### 7.1 Official Support Status

**Answer: YES, but with significant caveats**

**BlueZ Version History:**
- **v5.47 (2018):** Initial Bluetooth Mesh support introduced
  - New tool: `meshctl` for provisioning via GATT bearer
  - Experimental status

- **v5.50 (2019):** Enhanced mesh support
  - New tool: `mesh-cfgclient` for PB-ADV (advertising bearer)
  - Improved provisioning flows
  - Still flagged as experimental

- **v5.66-5.75 (2024-2025):** Current versions
  - Mesh support more stable
  - Still considered "experimental" feature
  - Some features require `Experimental=true` in `/etc/bluetooth/main.conf`

**Current Status (December 2025):**
- ✅ Provisioning works (GATT and ADV bearers)
- ✅ Basic mesh communication works
- ⚠️ Still experimental (may have breaking changes)
- ⚠️ Limited to provisioning tools (not full mesh stack for applications)

### 7.2 Architecture: BlueZ vs. Application-Level Mesh

**Important Distinction:**

BlueZ provides **mesh daemon and provisioning tools**, NOT a full application-level mesh stack.

**What BlueZ mesh provides:**
- `bluetooth-meshd`: Daemon handling low-level mesh protocol
- `meshctl`: Interactive provisioning tool
- D-Bus API: For applications to send/receive mesh messages

**What BlueZ mesh does NOT provide:**
- High-level Python API
- Application message framing
- Automatic network management
- Built-in models (beyond basic configuration)

**Analogy:**
- BlueZ mesh : Application messaging
- TCP/IP stack : HTTP web server
- (Provides transport, but not the application protocol)

**Implication for NotaGotchi:**
- ✅ BlueZ handles mesh networking at protocol level
- ❌ You still need to implement application-level messaging
- ❌ You need to define custom vendor models or use generic models
- ❌ Message formatting, queuing, and handling is your responsibility

### 7.3 Known Issues and Limitations

**Kernel Crypto Module Issue (Raspberry Pi):**
```
Issue #3628: "Bluetooth mesh unsupported due to missing crypto modules"
```
- Default Raspberry Pi kernel missing required crypto drivers
- CMAC, ECB, CCM AES cipher modes not compiled in
- **Solution:** Recompile kernel with `CONFIG_CRYPTO_*` options enabled
- **Impact:** Cannot use mesh without kernel recompilation

**D-Bus Permission Issues:**
```
Error: "org.freedesktop.DBus.Error.AccessDenied"
```
- Common when application tries to register mesh services
- **Solution:** User must be in `bluetooth` group
- **Solution:** May need custom D-Bus policy files in `/etc/dbus-1/system.d/`

**Experimental Feature Flag:**
```
Error: "Bluetooth Mesh requires experimental mode"
```
- Some mesh features require `Experimental=true` in `/etc/bluetooth/main.conf`
- **Impact:** Features may change or break in future BlueZ versions

**Connection Stability:**
- Some users report mesh connections dropping under load
- Flooding algorithm may cause packet collisions in dense networks
- No built-in congestion control (up to application)

**Provisioning Complexity:**
- Two-step process: provision via meshctl, then run application
- No automatic re-provisioning if node leaves network
- Key management is manual (network keys, application keys)

### 7.4 Comparison with Other Platforms

**Zephyr RTOS:**
- ✅ Full Bluetooth Mesh stack integrated into OS
- ✅ Mature implementation (used in commercial products)
- ✅ Comprehensive examples and documentation
- ❌ Requires C programming, embedded development environment

**ESP32 (Espressif):**
- ✅ ESP-IDF includes Bluetooth Mesh stack
- ✅ Good documentation and examples
- ✅ Lower power consumption than Raspberry Pi
- ❌ Different hardware platform (would need to port NotaGotchi)

**Android/iOS:**
- ⚠️ Limited mesh support (mainly as GATT-based provisioners)
- ⚠️ Cannot act as full mesh relay nodes
- ✅ Good for provisioning and controlling mesh networks
- ❌ Not suitable for peer mesh nodes

**Verdict:** BlueZ mesh support is functional but significantly less mature than embedded RTOS platforms

---

## 8. Specific Assessment for NotaGotchi Use Case

### 8.1 Requirements Alignment

**NotaGotchi Requirements:**
1. ✅ Multiple devices (5-20) need to discover each other → **Mesh supports this**
2. ✅ Bidirectional messaging between any pair → **Mesh supports this**
3. ✅ No pre-assigned roles (all devices equal) → **Mesh supports this**
4. ✅ Each device can connect to multiple others simultaneously → **Mesh supports this**
5. ✅ Must work on Raspberry Pi Zero 2W with Python → **Technically possible but difficult**

### 8.2 Trade-offs for NotaGotchi

**Advantages of Bluetooth Mesh:**
- ✅ True ad-hoc networking (no Wi-Fi router needed)
- ✅ Multi-hop relay (extended range)
- ✅ Redundancy (if one device fails, messages route around)
- ✅ Designed for exactly this type of many-to-many communication
- ✅ Solves "can't scan while advertising" problem completely

**Disadvantages of Bluetooth Mesh:**
- ❌ **2-6 month development timeline** (vs. Christmas deadline)
- ❌ **High power consumption** (100% duty cycle scanning)
- ❌ **Poor Python ecosystem** (immature libraries)
- ❌ **Steep learning curve** (Bluetooth specification, cryptography)
- ❌ **Kernel recompilation required** (Raspberry Pi)
- ❌ **Limited community examples** (few Raspberry Pi + Python projects)
- ❌ **Overkill complexity** (designed for 100+ device networks)

### 8.3 Use Case Reality Check

**What NotaGotchi actually needs:**
- Small network: 5-20 devices (not 100+)
- Occasional messages: emojis, presets (not continuous streaming)
- Home environment: devices within 50m range
- Interactive toy: needs responsive communication
- Christmas deadline: 1-2 weeks for networking implementation

**What Bluetooth Mesh provides:**
- Large-scale networks: optimized for 100-1000+ devices
- Continuous flooding: constant message relay
- Multi-hop routing: messages travel through many intermediate nodes
- Industrial-grade: designed for building automation, smart cities
- Complex setup: provisioning, key management, model configuration

**Mismatch:**
- NotaGotchi is a **consumer toy** with simple messaging needs
- Bluetooth Mesh is **industrial automation technology** for large-scale deployments
- Like using an 18-wheeler truck to drive to the grocery store (technically works, but overkill)

### 8.4 Alternative Assessment

**More appropriate technologies for NotaGotchi:**

1. **Wi-Fi + mDNS (BEST FIT)**
   - ✅ Matches scale (5-20 devices)
   - ✅ Simple discovery (Zeroconf library)
   - ✅ Reliable messaging (TCP sockets)
   - ✅ Fast implementation (1-2 weeks)
   - ⚠️ Requires Wi-Fi network (acceptable for home toy)
   - ⚠️ Higher power than BLE (but Raspberry Pi already power-hungry)

2. **BLE with pre-assigned roles (ACCEPTABLE)**
   - ✅ No network infrastructure needed
   - ✅ Lower power than Wi-Fi
   - ✅ Fast implementation (1-2 weeks with ble-serial)
   - ⚠️ Asymmetric (server/client roles)
   - ⚠️ Limited to peer-to-peer (not group messaging)

3. **Bluetooth Mesh (OVERKILL)**
   - ✅ Technically perfect for requirements
   - ❌ Massive over-engineering for use case
   - ❌ Implementation time exceeds project deadline
   - ❌ Power consumption too high for battery operation

---

## 9. Implementation Timeline Comparison

### 9.1 Wi-Fi with mDNS (1-2 Weeks)

**Week 1:**
- Day 1: Install Zeroconf library, read documentation
- Day 2: Implement service registration and discovery
- Day 3: Implement TCP socket messaging
- Day 4: Test on development machine (laptop + laptop)
- Day 5: Test on Raspberry Pi (Pi + laptop)

**Week 2:**
- Day 1-2: Implement message protocol (emoji, presets, custom text)
- Day 3: Integration with game logic (queue-based messaging from Bjorn pattern)
- Day 4: Testing with 2 Raspberry Pis
- Day 5: Testing with 5+ Raspberry Pis, stress testing

**Risks:** Low (proven technology, good documentation)
**Blockers:** None expected
**Confidence:** High (95%+ success rate)

### 9.2 BLE with ble-serial (1-2 Weeks)

**Week 1:**
- Day 1: Install ble-serial, test basic functionality
- Day 2: Implement role assignment (deterministic based on MAC)
- Day 3: Test client-server communication (Pi to Pi)
- Day 4: Implement discovery and automatic connection
- Day 5: Handle reconnection logic

**Week 2:**
- Day 1-2: Implement message protocol over serial
- Day 3: Integration with game logic
- Day 4-5: Testing and debugging connection stability

**Risks:** Medium (BlueZ version compatibility, connection drops)
**Blockers:** Possible (if BlueZ version has bugs)
**Confidence:** Medium (70-80% success rate)

### 9.3 Bluetooth Mesh (2-6 Months)

**Month 1: Setup and Learning**
- Week 1: Study Bluetooth Mesh specification (250+ pages)
- Week 2: Recompile Raspberry Pi kernel with crypto modules
- Week 3: Configure BlueZ mesh daemon, learn meshctl
- Week 4: Create test mesh network, provision first devices

**Month 2: Basic Implementation**
- Week 1: Learn python-bluetooth-mesh library
- Week 2: Implement D-Bus integration for mesh messages
- Week 3: Create simple send/receive test
- Week 4: Debug provisioning and connectivity issues

**Month 3: Application Development**
- Week 1-2: Define custom vendor model for NotaGotchi messages
- Week 3: Implement publish/subscribe logic
- Week 4: Test multi-device message propagation

**Month 4: Integration and Testing**
- Week 1-2: Integrate with NotaGotchi game logic
- Week 3: Test with 5+ devices
- Week 4: Debug message loss and timing issues

**Month 5-6: Optimization and Bug Fixes**
- Week 1-2: Power consumption optimization (LPN mode?)
- Week 3-4: Stress testing, bug fixes, documentation

**Risks:** HIGH (immature libraries, complex specification, kernel issues)
**Blockers:** Expected (crypto modules, D-Bus permissions, BlueZ bugs)
**Confidence:** LOW (30-50% success rate on first attempt)
**Reality:** Likely to discover fundamental blockers mid-project

### 9.4 Timeline Decision Matrix

| Criterion | Wi-Fi | ble-serial | Bluetooth Mesh |
|-----------|-------|-----------|----------------|
| **Development time** | 1-2 weeks | 1-2 weeks | 2-6 months |
| **Testing time** | 2-3 days | 3-5 days | 2-4 weeks |
| **Risk of blockers** | Low | Medium | High |
| **Christmas deadline** | ✅ Easily | ✅ Feasible | ❌ Impossible |
| **Success confidence** | 95% | 75% | 40% |

**Verdict:** Bluetooth Mesh cannot meet Christmas deadline

---

## 10. Power Consumption Analysis

### 10.1 Raspberry Pi Zero 2W Baseline

**Power Consumption:**
- Idle (Linux running): ~100-150mA @ 5V
- CPU active: ~200-300mA @ 5V
- With e-ink display refresh: +50-100mA during refresh
- Total typical: 150-250mA

**Battery Implications:**
- 2000mAh battery: 8-13 hours runtime (baseline)
- 5000mAh battery: 20-33 hours runtime (baseline)

### 10.2 Wi-Fi Power Consumption

**Wi-Fi Radio:**
- Active (transmitting/receiving): +100-150mA
- Idle (associated, not transmitting): +40-60mA
- Power save mode: +20-30mA

**NotaGotchi Wi-Fi usage pattern:**
- Periodic discovery scans: 5 seconds every 60 seconds
- Message exchange: Occasional (when user interacts)
- Idle most of the time

**Estimated average:** +50mA (power save mode)
**Total with Wi-Fi:** 200-300mA
**Battery life (2000mAh):** 6-10 hours

### 10.3 BLE Traditional (ble-serial) Power Consumption

**BLE Radio:**
- Active connection: +15-30mA
- Advertising: +10-20mA (depending on interval)
- Scanning: +15-25mA
- Idle (connected, no data): +5-10mA

**NotaGotchi BLE usage pattern:**
- Server mode: Advertising continuously until connected
- Client mode: Scanning for 10 seconds every 60 seconds
- Connected: Idle most of the time, occasional message

**Estimated average:** +15mA
**Total with BLE:** 165-265mA
**Battery life (2000mAh):** 7-12 hours

### 10.4 Bluetooth Mesh Power Consumption

**Mesh Node (Regular):**
- **100% duty cycle scanning:** Always listening for mesh packets
- Transmitting: Occasional (when relaying or sending)
- **No idle mode:** Cannot sleep while remaining mesh node

**Power consumption:**
- Continuous scanning: +40-60mA
- Periodic transmissions: +20-30mA (amortized)
- **Total mesh overhead:** +60-90mA

**Total with Bluetooth Mesh:** 210-340mA
**Battery life (2000mAh):** 5-9 hours

**Mesh Low Power Node (LPN):**
- Sleeps most of the time
- Wakes periodically to poll Friend Node
- Polling interval: 1-10 seconds (configurable)

**Power consumption (LPN):**
- Sleep: +1-2mA
- Periodic polling: +15mA amortized (depends on interval)
- **Total LPN overhead:** +16-17mA

**Total with LPN:** 166-267mA
**Battery life (2000mAh):** 7-12 hours

**BUT:** LPN mode limitations
- Requires Friend Node (another device or hub)
- Messages delayed until next poll
- Not suitable for interactive toy (latency)

### 10.5 Power Comparison Summary

| Technology | Overhead | Total Draw | Battery Life (2000mAh) | Interactive? |
|------------|----------|------------|------------------------|--------------|
| **Baseline (no networking)** | 0mA | 150-250mA | 8-13 hours | N/A |
| **Wi-Fi (mDNS)** | +50mA | 200-300mA | 6-10 hours | ✅ Yes |
| **BLE (ble-serial)** | +15mA | 165-265mA | 7-12 hours | ✅ Yes |
| **Bluetooth Mesh (regular)** | +70mA | 220-320mA | 6-9 hours | ✅ Yes |
| **Bluetooth Mesh (LPN)** | +17mA | 167-267mA | 7-12 hours | ⚠️ Delayed |

**Key Insights:**
1. BLE traditional has lowest power overhead (+15mA)
2. Bluetooth Mesh regular has HIGH overhead (+70mA) due to continuous scanning
3. Bluetooth Mesh LPN recovers power efficiency but sacrifices interactivity
4. Wi-Fi is comparable to Mesh regular node (+50mA vs +70mA)
5. **Power consumption is NOT a differentiator** between Wi-Fi and Mesh for this use case

**Conclusion:** Bluetooth Mesh does NOT offer power advantage over Wi-Fi (contrary to initial expectations)

---

## 11. Final Recommendation and Justification

### 11.1 Technology Ranking for NotaGotchi

**1st Choice: Wi-Fi with mDNS/Zeroconf** 🥇

**Rationale:**
- ✅ **Fast implementation:** 1-2 weeks (meets Christmas deadline)
- ✅ **Proven technology:** Mature Python library (Zeroconf)
- ✅ **Simple code:** ~200 lines for complete networking
- ✅ **Excellent documentation:** Hundreds of examples available
- ✅ **Easy debugging:** Standard networking tools (tcpdump, Wireshark)
- ✅ **True peer-to-peer:** Symmetric discovery and communication
- ✅ **Reliable:** TCP provides guaranteed delivery
- ⚠️ **Requires Wi-Fi network:** Acceptable for home use (target environment)
- ⚠️ **Higher power than BLE:** But comparable to Bluetooth Mesh regular node

**Best for:** Meeting project deadline with reliable technology

---

**2nd Choice: BLE with ble-serial (pre-assigned roles)** 🥈

**Rationale:**
- ✅ **Fast implementation:** 1-2 weeks
- ✅ **No network infrastructure:** Ad-hoc device-to-device
- ✅ **Low power:** +15mA overhead (best of all options)
- ✅ **Simple library:** ble-serial handles complexity
- ⚠️ **Asymmetric:** Requires server/client role assignment
- ⚠️ **Limited scalability:** Works for 2 devices, awkward for group messaging
- ⚠️ **BlueZ compatibility risks:** Some versions have bugs

**Best for:** If Wi-Fi network is not available in target environment

---

**3rd Choice: Bluetooth Mesh** 🥉

**Rationale:**
- ✅ **Technically perfect match:** Solves all peer-to-peer requirements
- ✅ **No network infrastructure:** Ad-hoc mesh networking
- ✅ **Future-proof:** Industry standard for IoT device networks
- ❌ **2-6 month timeline:** Cannot meet Christmas deadline
- ❌ **High complexity:** Steep learning curve, complex debugging
- ❌ **Poor Python support:** Immature libraries, few examples
- ❌ **High power consumption:** +70mA overhead (regular node)
- ❌ **Overkill for use case:** Designed for 100+ device networks

**Best for:** Future version of NotaGotchi with 6+ month development time

---

**DO NOT USE:**
- ❌ **Custom BLE implementation (Bleak + Bless):** High complexity, untested on Pi, likely to hit BlueZ limitations
- ❌ **Classic Bluetooth (RFCOMM):** Higher power than BLE, less modern
- ❌ **Zephyr RTOS Bluetooth Mesh:** Requires porting entire application to different OS

### 11.2 Decision Framework

**Choose Wi-Fi if:**
- Christmas deadline is firm
- Target environment has Wi-Fi router (home use)
- Want reliable, proven technology
- Development team prefers simple implementation

**Choose ble-serial if:**
- Christmas deadline is firm
- Wi-Fi infrastructure not available
- Only need 2-device pairing
- Willing to accept asymmetric roles

**Choose Bluetooth Mesh if:**
- Christmas deadline can be extended to June 2026
- Must have ad-hoc networking (no Wi-Fi)
- Must support 5-20 devices with symmetric discovery
- Team has embedded systems / BLE protocol expertise
- Power consumption not a concern (mains powered or large battery)

### 11.3 Recommendation for NotaGotchi Project

**IMPLEMENT WI-FI WITH mDNS/ZEROCONF**

**Reasoning:**

1. **Christmas deadline:** 3-4 weeks remaining, Wi-Fi can be done in 1-2 weeks
2. **Target users:** Children receiving gifts, played at home (Wi-Fi available)
3. **Project complexity:** Already building e-ink display + Tamagotchi game logic + Bluetooth Mesh would add too much risk
4. **Python ecosystem:** NotaGotchi is Python-based, Wi-Fi has excellent Python support
5. **Development velocity:** Fast iteration enables more time for game features and polish
6. **Power consumption:** Raspberry Pi Zero 2W is not ultra-low-power device anyway, Wi-Fi overhead acceptable

**Path forward:**

1. Implement Wi-Fi networking now (December 2025)
2. Deliver Christmas gifts on time
3. If needed, **revisit Bluetooth Mesh for NotaGotchi v2.0** (Summer 2026)
   - By then, Bluetooth Mesh Python libraries may be more mature
   - More time for proper implementation and testing
   - Can keep Wi-Fi as fallback option in firmware

---

## 12. Conclusion

### 12.1 Direct Answers to Research Questions

**1. Is Bluetooth Mesh different from BLE GATT peripheral/central model?**
- ✅ **YES:** Completely different architecture
- Mesh uses **connectionless advertising bearer** (no GATT connections)
- All nodes are **equal peers** (no central/peripheral roles)
- **Flooding protocol** (messages relayed by all nodes)
- Designed for **many-to-many** communication

**2. Does it solve the "can't scan while advertising" problem?**
- ✅ **YES:** Completely eliminates this problem
- No need to switch between peripheral and central roles
- All nodes continuously scan (100% duty cycle)
- All nodes can broadcast (time-sliced with scanning)
- BlueZ limitations with peripheral+central do not apply

**3. What Python libraries exist for Bluetooth Mesh on Raspberry Pi?**
- ⚠️ **LIMITED OPTIONS:**
  - `python-bluetooth-mesh` (Silvair): Minimal documentation, few examples
  - `btferret`: Custom mesh (not SIG standard), easier to use
  - BlueZ D-Bus API: Low-level, requires manual D-Bus interaction
- ❌ **NO mature high-level library** (equivalent to Bleak for BLE)

**4. Are there working examples of Bluetooth Mesh on Raspberry Pi?**
- ⚠️ **FEW EXAMPLES:**
  - BlueZ official examples: Provisioning tools (meshctl, mesh-cfgclient)
  - Bluetooth SIG guides: Raspberry Pi as provisioner (not application messaging)
  - Community projects: Very limited, mostly proof-of-concept
- ❌ **NO comprehensive Python application examples**

**5. What are the limitations?**
- **Network size:** 32,767 nodes (theoretical), 100-1000 practical → ✅ Not a limitation for NotaGotchi
- **Message size:** 384 bytes maximum → ✅ Not a limitation for NotaGotchi
- **Power consumption:** High (+70mA continuous scanning) → ❌ Major concern
- **Implementation complexity:** Very high (2-6 months) → ❌ Major concern
- **Python ecosystem:** Immature → ❌ Major concern

**6. Implementation difficulty compared to Wi-Fi mDNS?**
- **Wi-Fi:** 1-2 weeks, low complexity, excellent Python support
- **Bluetooth Mesh:** 2-6 months, high complexity, poor Python support
- **Ratio:** Mesh is **8-12x more difficult** than Wi-Fi

**7. Does BlueZ support Bluetooth Mesh properly?**
- ✅ **YES, but limited:**
  - Provisioning tools work well
  - D-Bus API available for application messaging
  - Still experimental (may have breaking changes)
  - Kernel recompilation required on Raspberry Pi
- ⚠️ **Not a full application stack** (just transport layer)

### 12.2 Final Verdict

**Bluetooth Mesh is NOT suitable for NotaGotchi's December 2025 Christmas deadline.**

While technically perfect for the peer-to-peer multi-device requirements, the implementation complexity, immature Python ecosystem, and 2-6 month timeline make it impractical for this project.

**Recommended alternative:** Wi-Fi with mDNS/Zeroconf
- ✅ 1-2 week implementation
- ✅ Proven technology
- ✅ Excellent Python support
- ✅ Meets all functional requirements
- ⚠️ Requires Wi-Fi network (acceptable for home toy)

**Future consideration:** Bluetooth Mesh for NotaGotchi v2.0 (2026+)
- When Python libraries are more mature
- When development timeline allows 2-3 months for networking
- When team has gained BLE protocol expertise
- Can offer as firmware option alongside Wi-Fi

---

## 13. References and Resources

### 13.1 Official Specifications and Guides

- **Bluetooth SIG Mesh Specification:** https://www.bluetooth.com/specifications/specs/mesh-protocol/
- **Bluetooth Mesh Networking: An Introduction for Developers:** https://www.bluetooth.com/wp-content/uploads/2019/03/Mesh-Technology-Overview.pdf
- **Developer Study Guide: Using BlueZ as a Bluetooth Mesh Provisioner:** https://www.bluetooth.com/wp-content/uploads/2020/04/Developer-Study-Guide-How-to-Deploy-BlueZ-on-a-Raspberry-Pi-Board-as-a-Bluetooth-Mesh-Provisioner.pdf

### 13.2 BlueZ Resources

- **BlueZ GitHub:** https://github.com/bluez/bluez
- **BlueZ Mesh API:** https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/mesh-api.txt
- **Raspberry Pi Kernel Issue #3628:** https://github.com/raspberrypi/linux/issues/3628 (Missing crypto modules)

### 13.3 Python Libraries

- **python-bluetooth-mesh:** https://github.com/SilvairGit/python-bluetooth-mesh
- **PyPI bluetooth-mesh:** https://pypi.org/project/bluetooth-mesh/
- **btferret:** https://github.com/petzval/btferret (custom mesh, not SIG standard)
- **Zeroconf (recommended alternative):** https://github.com/python-zeroconf/python-zeroconf

### 13.4 Research Papers and Technical Articles

- **Bluetooth Mesh Energy Consumption: A Model:** https://www.mdpi.com/1424-8220/19/5/1238
- **Bluetooth Mesh Networking: The Ultimate Guide:** https://novelbits.io/bluetooth-mesh-networking-the-ultimate-guide/
- **The Bluetooth Mesh Standard: An Overview and Experimental Evaluation:** https://pmc.ncbi.nlm.nih.gov/articles/PMC6111614/

### 13.5 Tutorials and Blog Posts

- **Set Up a Bluetooth Mesh Network with Raspberry Pi:** https://pidiylab.com/bluetooth-mesh-network-using-raspberry-pi/
- **How to deploy BlueZ v5.48 on Raspberry Pi 3:** https://www.bluetooth.com/blog/bluez-on-raspberry-pi/
- **Bluetooth Mesh — Drogue IoT:** https://blog.drogue.io/bluetooth-mesh/

### 13.6 Related NotaGotchi Documents

- `/Users/brian/source/personal/notagotchi/NotaGotchi/CLAUDE.md` - Project requirements
- `/Users/brian/source/personal/notagotchi/NotaGotchi/plans/2025-12-13_ble_peripheral_research.md` - BLE GATT research
- `/Users/brian/source/personal/notagotchi/NotaGotchi/plans/2025-12-13_ble-serial_research.md` - ble-serial library research

---

**Research completed:** December 13, 2025
**Recommendation:** Use Wi-Fi with mDNS/Zeroconf, not Bluetooth Mesh
**Rationale:** Christmas deadline, proven technology, excellent Python support
**Future option:** Consider Bluetooth Mesh for NotaGotchi v2.0 in 2026
