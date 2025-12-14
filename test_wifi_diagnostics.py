#!/usr/bin/env python3
"""
Wi-Fi Diagnostics - Debug mDNS and network connectivity

Run this on both Pis to diagnose mDNS issues.
"""

import socket
import subprocess
import sys
import platform

def run_command(cmd, description):
    """Run a shell command and display results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print(f"✅ SUCCESS")
            if result.stdout:
                print(f"Output:\n{result.stdout}")
        else:
            print(f"❌ FAILED (exit code: {result.returncode})")
            if result.stderr:
                print(f"Error:\n{result.stderr}")
            if result.stdout:
                print(f"Output:\n{result.stdout}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"⚠️  TIMEOUT (command took > 5 seconds)")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_network_info():
    """Display network information"""
    print(f"\n{'='*60}")
    print(f"Network Information")
    print(f"{'='*60}")

    # Hostname
    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")

    # IP addresses
    try:
        # Get all IP addresses
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        ips = result.stdout.strip().split()
        print(f"IP Addresses: {', '.join(ips)}")

        # Get default interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"Default Interface IP: {local_ip}")

    except Exception as e:
        print(f"Error getting IP: {e}")


def check_zeroconf_library():
    """Check if zeroconf library is installed"""
    print(f"\n{'='*60}")
    print(f"Python Zeroconf Library")
    print(f"{'='*60}")

    try:
        import zeroconf
        print(f"✅ Installed: version {zeroconf.__version__}")
        return True
    except ImportError:
        print(f"❌ NOT INSTALLED")
        print(f"Install with: pip3 install zeroconf")
        return False


def main():
    """Run all diagnostics"""
    print(f"\n{'='*70}")
    print(f"NotaGotchi Wi-Fi Diagnostics")
    print(f"{'='*70}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"{'='*70}")

    # Basic network info
    check_network_info()

    # Check Python library
    zeroconf_ok = check_zeroconf_library()

    # Check Avahi daemon (required for mDNS on Linux)
    avahi_running = run_command(
        "systemctl status avahi-daemon | head -n 3",
        "Avahi daemon status (required for mDNS)"
    )

    if not avahi_running:
        print(f"\n⚠️  Avahi daemon not running!")
        print(f"To fix, run:")
        print(f"  sudo systemctl start avahi-daemon")
        print(f"  sudo systemctl enable avahi-daemon")

    # Check if avahi-browse is available
    run_command(
        "which avahi-browse",
        "Check for avahi-browse tool"
    )

    # Try to browse for all mDNS services
    print(f"\n{'='*60}")
    print(f"Scanning for ALL mDNS services (10 seconds)...")
    print(f"{'='*60}")
    run_command(
        "timeout 10 avahi-browse -a -t -r 2>/dev/null | head -n 50",
        "Browse all mDNS services"
    )

    # Try to browse specifically for NotaGotchi services
    print(f"\n{'='*60}")
    print(f"Scanning for NotaGotchi services (5 seconds)...")
    print(f"{'='*60}")
    run_command(
        "timeout 5 avahi-browse _notagotchi._tcp -t -r 2>/dev/null",
        "Browse NotaGotchi services"
    )

    # Check firewall status
    run_command(
        "sudo ufw status 2>/dev/null || echo 'ufw not installed'",
        "Firewall status"
    )

    # Test basic connectivity
    print(f"\n{'='*60}")
    print(f"Network Connectivity Test")
    print(f"{'='*60}")
    run_command(
        "ping -c 3 8.8.8.8",
        "Internet connectivity (ping Google DNS)"
    )

    # Check for multicast route (required for mDNS)
    run_command(
        "ip route | grep 224.0.0.0",
        "Multicast route (required for mDNS)"
    )

    # Summary
    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC SUMMARY")
    print(f"{'='*70}")

    if not zeroconf_ok:
        print(f"❌ Install zeroconf: pip3 install zeroconf")
    else:
        print(f"✅ Zeroconf library installed")

    if not avahi_running:
        print(f"❌ Start Avahi daemon:")
        print(f"   sudo systemctl start avahi-daemon")
        print(f"   sudo systemctl enable avahi-daemon")
    else:
        print(f"✅ Avahi daemon running")

    print(f"\n{'='*70}")
    print(f"Next Steps:")
    print(f"{'='*70}")
    print(f"1. Fix any issues shown above")
    print(f"2. Run this diagnostic on BOTH Raspberry Pis")
    print(f"3. On one Pi: python3 test_wifi_server.py NotaGotchi_TestA")
    print(f"4. On other Pi: Run this diagnostic again to see if server appears")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
