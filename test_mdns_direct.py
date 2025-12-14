#!/usr/bin/env python3
"""
Direct mDNS Test - Send and receive mDNS packets manually

This bypasses the zeroconf library to test raw mDNS functionality.
"""

import socket
import struct
import time
import sys

MDNS_ADDR = '224.0.0.251'
MDNS_PORT = 5353

def test_mdns_send():
    """Test sending mDNS multicast packets"""
    print(f"\n{'='*60}")
    print("Testing mDNS SEND")
    print(f"{'='*60}")

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set multicast TTL
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)

        # Simple mDNS query packet for _notagotchi._tcp.local
        # This is a simplified DNS query packet
        query = (
            b'\x00\x00'  # Transaction ID
            b'\x00\x00'  # Flags
            b'\x00\x01'  # Questions: 1
            b'\x00\x00'  # Answer RRs: 0
            b'\x00\x00'  # Authority RRs: 0
            b'\x00\x00'  # Additional RRs: 0
            # Question: _notagotchi._tcp.local
            b'\x0b_notagotchi\x04_tcp\x05local\x00'  # Name
            b'\x00\x0c'  # Type: PTR
            b'\x00\x01'  # Class: IN
        )

        print(f"Sending mDNS query to {MDNS_ADDR}:{MDNS_PORT}")
        sock.sendto(query, (MDNS_ADDR, MDNS_PORT))
        print("✅ mDNS packet sent successfully")

        sock.close()
        return True

    except Exception as e:
        print(f"❌ Failed to send mDNS packet: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mdns_receive(timeout=5):
    """Test receiving mDNS multicast packets"""
    print(f"\n{'='*60}")
    print("Testing mDNS RECEIVE")
    print(f"{'='*60}")
    print(f"Listening for {timeout} seconds...")

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to mDNS port
        sock.bind(('', MDNS_PORT))

        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(MDNS_ADDR), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Set timeout
        sock.settimeout(timeout)

        print(f"Listening on port {MDNS_PORT}...")
        packet_count = 0

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(9216)
                packet_count += 1

                # Check if this is a NotaGotchi packet
                if b'notagotchi' in data.lower():
                    print(f"\n✅ Received NotaGotchi mDNS packet!")
                    print(f"   From: {addr[0]}:{addr[1]}")
                    print(f"   Size: {len(data)} bytes")

                    # Try to find the service name
                    if b'NotaGotchi_' in data:
                        # Find the device name
                        idx = data.find(b'NotaGotchi_')
                        name_end = data.find(b'\x00', idx)
                        if name_end > idx:
                            device_name = data[idx:name_end].decode('utf-8', errors='ignore')
                            print(f"   Device: {device_name}")

            except socket.timeout:
                continue

        sock.close()

        print(f"\n{'='*60}")
        if packet_count > 0:
            print(f"✅ Received {packet_count} mDNS packets total")
            return True
        else:
            print(f"❌ No mDNS packets received in {timeout} seconds")
            return False

    except Exception as e:
        print(f"❌ Failed to receive mDNS packets: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_interface_info():
    """Show network interface information"""
    print(f"\n{'='*60}")
    print("Network Interface Information")
    print(f"{'='*60}")

    import subprocess

    # Show IP addresses
    print("\nIP Addresses:")
    result = subprocess.run(['ip', 'addr', 'show', 'wlan0'],
                          capture_output=True, text=True)
    print(result.stdout)

    # Show multicast route
    print("\nMulticast Route:")
    result = subprocess.run(['ip', 'route', 'show'],
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if '224.0.0.0' in line:
            print(f"✅ {line}")
            break
    else:
        print("❌ No multicast route found!")

    # Show multicast memberships
    print("\nMulticast Memberships:")
    try:
        with open('/proc/net/igmp', 'r') as f:
            print(f.read())
    except Exception as e:
        print(f"Could not read /proc/net/igmp: {e}")


def main():
    """Run all tests"""
    print(f"\n{'='*60}")
    print("NotaGotchi - Direct mDNS Test")
    print(f"{'='*60}")

    if len(sys.argv) > 1 and sys.argv[1] == 'send':
        # Send mode - just send queries
        print("Mode: SEND queries only")
        test_mdns_send()
    elif len(sys.argv) > 1 and sys.argv[1] == 'receive':
        # Receive mode - just listen
        print("Mode: RECEIVE only")
        test_mdns_receive(timeout=10)
    else:
        # Full test
        print("Mode: FULL test (interface info + send + receive)")
        test_interface_info()
        test_mdns_send()
        time.sleep(1)
        test_mdns_receive(timeout=5)

    print(f"\n{'='*60}")
    print("Test Complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
