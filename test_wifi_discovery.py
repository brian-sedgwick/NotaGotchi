#!/usr/bin/env python3
"""
Wi-Fi Discovery Test - Find NotaGotchi devices on local network

Tests mDNS/Zeroconf service discovery to find other NotaGotchi devices
on the same Wi-Fi network.

Usage:
    python3 test_wifi_discovery.py
"""

import time
import sys
import socket
from typing import Dict, List
import test_wifi_config as config

try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
except ImportError:
    print("ERROR: zeroconf library not installed")
    print("Install with: pip3 install zeroconf")
    sys.exit(1)


def get_local_ip():
    """Get the local IP address for WiFi interface"""
    try:
        # Try to get IP from wlan0
        import subprocess
        result = subprocess.run(['ip', '-4', 'addr', 'show', 'wlan0'],
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'inet ' in line:
                ip = line.strip().split()[1].split('/')[0]
                return ip
    except:
        pass

    # Fallback method
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None


class NotaGotchiListener(ServiceListener):
    """Listener for NotaGotchi service discoveries"""

    def __init__(self):
        self.devices: Dict[str, Dict] = {}

    def add_service(self, zc: Zeroconf, service_type: str, name: str):
        """Called when a new service is discovered"""
        info = zc.get_service_info(service_type, name)

        if info:
            # Extract device name from service name (e.g., "NotaGotchi_TestA._notagotchi._tcp.local.")
            device_name = name.replace(f".{config.SERVICE_TYPE}", "")

            # Get IPv4 addresses
            addresses = [addr for addr in info.parsed_addresses() if ":" not in addr]

            if addresses:
                device_info = {
                    "name": device_name,
                    "address": addresses[0],
                    "port": info.port,
                    "properties": {
                        k.decode('utf-8'): v.decode('utf-8') if isinstance(v, bytes) else v
                        for k, v in info.properties.items()
                    }
                }

                self.devices[device_name] = device_info

                print(f"\n✅ Discovered: {device_name}")
                print(f"   Address: {addresses[0]}:{info.port}")
                print(f"   Properties: {device_info['properties']}")

    def remove_service(self, zc: Zeroconf, service_type: str, name: str):
        """Called when a service goes away"""
        device_name = name.replace(f".{config.SERVICE_TYPE}", "")
        if device_name in self.devices:
            print(f"\n⚠️  Lost connection to: {device_name}")
            del self.devices[device_name]

    def update_service(self, zc: Zeroconf, service_type: str, name: str):
        """Called when service information is updated"""
        # For now, treat updates the same as adds
        self.add_service(zc, service_type, name)


def discover_devices(duration_seconds: float = config.DISCOVERY_DURATION_SECONDS) -> List[Dict]:
    """
    Discover NotaGotchi devices on the local network

    Args:
        duration_seconds: How long to scan for devices

    Returns:
        List of discovered device information dictionaries
    """
    print(f"\n{'='*60}")
    print(f"NotaGotchi Wi-Fi Discovery Test")
    print(f"{'='*60}")
    print(f"Service Type: {config.SERVICE_TYPE}")

    # Get local IP and bind to it
    local_ip = get_local_ip()
    if local_ip:
        print(f"Binding to interface: {local_ip}")
    else:
        print("Using default interface")

    print(f"Scanning for {duration_seconds} seconds...\n")

    # Create Zeroconf instance with explicit interface
    if local_ip:
        zc = Zeroconf(interfaces=[local_ip])
    else:
        zc = Zeroconf()

    listener = NotaGotchiListener()

    # Start browsing for services
    browser = ServiceBrowser(zc, config.SERVICE_TYPE, listener)

    try:
        # Wait for the specified duration
        time.sleep(duration_seconds)
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
    finally:
        # Cleanup
        zc.close()

    print(f"\n{'='*60}")
    print(f"Discovery Complete")
    print(f"{'='*60}")

    devices = list(listener.devices.values())

    if devices:
        print(f"\n✅ Found {len(devices)} NotaGotchi device(s):\n")
        for i, device in enumerate(devices, 1):
            print(f"Device {i}:")
            print(f"  Name:    {device['name']}")
            print(f"  Address: {device['address']}")
            print(f"  Port:    {device['port']}")
            print(f"  Version: {device['properties'].get('version', 'unknown')}")
            print()
    else:
        print("\n❌ No NotaGotchi devices found")
        print("\nMake sure:")
        print("  1. Another device is running test_wifi_server.py")
        print("  2. Both devices are on the same Wi-Fi network")
        print("  3. Firewall allows mDNS (port 5353)")
        print()

    return devices


def main():
    """Main entry point"""
    print(f"\n{'='*60}")
    print(f"NotaGotchi - Wi-Fi Discovery Test")
    print(f"{'='*60}\n")

    try:
        devices = discover_devices()

        if devices:
            print(f"{'='*60}")
            print("Next Steps:")
            print(f"{'='*60}")
            print("Run test_wifi_client.py to connect and send messages")
            print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
