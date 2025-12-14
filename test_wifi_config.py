#!/usr/bin/env python3
"""
Wi-Fi Test Configuration
mDNS/Zeroconf settings for NotaGotchi Wi-Fi connectivity testing
"""

# ============================================================================
# MDNS/ZEROCONF CONFIGURATION
# ============================================================================
# Service type for mDNS advertisement and discovery
SERVICE_TYPE = "_notagotchi._tcp.local."

# Service properties - metadata sent with mDNS advertisement
SERVICE_PROPERTIES = {
    "version": "1.0",
    "protocol": "notagotchi"
}

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================
# TCP Server settings
DEFAULT_PORT = 5555
CONNECTION_TIMEOUT_SECONDS = 10.0
MESSAGE_TIMEOUT_SECONDS = 5.0

# Discovery settings
DISCOVERY_DURATION_SECONDS = 5.0

# Message settings
MAX_MESSAGE_SIZE = 8192  # 8KB max message size
MESSAGE_ENCODING = "utf-8"

# ============================================================================
# TEST CONFIGURATION
# ============================================================================
# Test device names
TEST_DEVICE_A_NAME = "NotaGotchi_TestA"
TEST_DEVICE_B_NAME = "NotaGotchi_TestB"

# Test messages
TEST_MESSAGES = [
    "Hello from Device A!",
    "Hello from Device B!",
    "This is a test message",
    "Testing 1-2-3",
    "Message delivery confirmed"
]

# Debug settings
DEBUG_MODE = True
VERBOSE_LOGGING = True
