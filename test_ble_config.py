#!/usr/bin/env python3
"""
BLE Test Configuration
UUIDs and constants for NotaGotchi BLE connectivity testing
"""

# ============================================================================
# BLE SERVICE AND CHARACTERISTIC UUIDs
# ============================================================================
# Custom UUIDs for NotaGotchi BLE service
# Format: 12345678-1234-5678-1234-56789abcdefX (X = characteristic number)

# Main service UUID
NOTAGOTCHI_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"

# Characteristic UUIDs
DEVICE_INFO_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"
MESSAGE_INBOX_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef2"
MESSAGE_OUTBOX_CHAR_UUID = "12345678-1234-5678-1234-56789abcdef3"

# ============================================================================
# BLE CONFIGURATION
# ============================================================================
# Advertising settings
DEVICE_NAME_PREFIX = "NotaGotchi"
ADVERTISING_INTERVAL_MS = 1000  # 1 second

# Scanning settings
SCAN_DURATION_SECONDS = 5.0
SCAN_INTERVAL_SECONDS = 30

# Connection settings
CONNECTION_TIMEOUT_SECONDS = 10.0
MESSAGE_TIMEOUT_SECONDS = 5.0

# Message settings
MAX_MESSAGE_SIZE = 512  # bytes (BLE MTU size)
MESSAGE_ENCODING = "utf-8"

# ============================================================================
# TEST CONFIGURATION
# ============================================================================
# Test device names
TEST_DEVICE_A_NAME = f"{DEVICE_NAME_PREFIX}_TestA"
TEST_DEVICE_B_NAME = f"{DEVICE_NAME_PREFIX}_TestB"

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
