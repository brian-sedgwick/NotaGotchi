#!/usr/bin/env python3
"""
Wi-Fi Discovery using Avahi D-Bus - Works with avahi-daemon

This uses the system's avahi-daemon instead of python-zeroconf,
avoiding port conflicts.
"""

import subprocess
import json
import time
import sys
from typing import Dict, List

def discover_via_avahi(duration_seconds: float = 5.0) -> List[Dict]:
    """
    Discover NotaGotchi devices using avahi-browse command

    Args:
        duration_seconds: How long to scan

    Returns:
        List of discovered devices
    """
    print(f"\n{'='*60}")
    print(f"NotaGotchi Wi-Fi Discovery (using Avahi)")
    print(f"{'='*60}")
    print(f"Service Type: _notagotchi._tcp")
    print(f"Scanning for {duration_seconds} seconds...\n")

    # Run avahi-browse with parseable output
    cmd = [
        'avahi-browse',
        '_notagotchi._tcp',
        '-t',  # Terminate after dumping
        '-r',  # Resolve services
        '-p'   # Parseable output
    ]

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration_seconds
        )

        devices = {}

        # Parse avahi-browse output
        # Format: =;interface;protocol;name;type;domain;hostname;address;port;txt
        for line in result.stdout.split('\n'):
            if not line.startswith('='):
                continue

            parts = line.split(';')
            if len(parts) < 10:
                continue

            interface = parts[1]
            protocol = parts[2]  # IPv4 or IPv6
            name = parts[3]
            service_type = parts[4]
            domain = parts[5]
            hostname = parts[6]
            address = parts[7]
            port = parts[8]
            txt = parts[9] if len(parts) > 9 else ""

            if address and port and protocol == 'IPv4':
                device_info = {
                    'name': name,
                    'address': address,
                    'port': int(port),
                    'hostname': hostname,
                    'interface': interface,
                    'properties': {}
                }

                # Parse TXT records if present
                if txt:
                    for item in txt.split():
                        if '=' in item:
                            k, v = item.split('=', 1)
                            device_info['properties'][k.strip('"')] = v.strip('"')

                devices[name] = device_info

                print(f"✅ Discovered: {name}")
                print(f"   Address: {address}:{port}")
                if device_info['properties']:
                    print(f"   Properties: {device_info['properties']}")
                print()

        return list(devices.values())

    except subprocess.TimeoutExpired:
        print(f"Scan timeout after {duration_seconds} seconds")
        return []
    except FileNotFoundError:
        print(f"❌ ERROR: avahi-browse not found")
        print(f"Install with: sudo apt-get install avahi-utils")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Main entry point"""
    print(f"\n{'='*60}")
    print(f"NotaGotchi - Wi-Fi Discovery Test (Avahi)")
    print(f"{'='*60}\n")

    devices = discover_via_avahi()

    print(f"\n{'='*60}")
    print(f"Discovery Complete")
    print(f"{'='*60}")

    if devices:
        print(f"\n✅ Found {len(devices)} NotaGotchi device(s):\n")
        for i, device in enumerate(devices, 1):
            print(f"Device {i}:")
            print(f"  Name:    {device['name']}")
            print(f"  Address: {device['address']}")
            print(f"  Port:    {device['port']}")
            for key, value in device['properties'].items():
                print(f"  {key}: {value}")
            print()
    else:
        print("\n❌ No NotaGotchi devices found")
        print("\nMake sure:")
        print("  1. Another device is running test_wifi_server.py")
        print("  2. Both devices are on the same Wi-Fi network")
        print()

    return devices


if __name__ == "__main__":
    main()
