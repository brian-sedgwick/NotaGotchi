#!/bin/bash
# Fix mDNS on Raspberry Pi - Add multicast route

echo "========================================================================"
echo "NotaGotchi mDNS Fix Script"
echo "========================================================================"
echo ""

# Check if running as root for some commands
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo privileges for some commands."
    echo "It will prompt for your password when needed."
    echo ""
fi

# Install avahi-utils for debugging tools
echo "Step 1: Installing avahi-utils (for avahi-browse tool)..."
sudo apt-get update -qq
sudo apt-get install -y avahi-utils

if [ $? -eq 0 ]; then
    echo "✅ avahi-utils installed"
else
    echo "❌ Failed to install avahi-utils"
    exit 1
fi

echo ""

# Detect WiFi interface
echo "Step 2: Detecting WiFi interface..."
WIFI_INTERFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -E '^wlan|^wlp' | head -n 1)

if [ -z "$WIFI_INTERFACE" ]; then
    echo "❌ Could not detect WiFi interface"
    echo "Available interfaces:"
    ip link show
    exit 1
fi

echo "✅ WiFi interface: $WIFI_INTERFACE"
echo ""

# Check if multicast route exists
echo "Step 3: Checking for multicast route..."
if ip route | grep -q "224.0.0.0"; then
    echo "✅ Multicast route already exists:"
    ip route | grep "224.0.0.0"
else
    echo "❌ No multicast route found"
    echo ""
    echo "Step 4: Adding multicast route..."
    sudo ip route add 224.0.0.0/4 dev $WIFI_INTERFACE

    if [ $? -eq 0 ]; then
        echo "✅ Multicast route added:"
        ip route | grep "224.0.0.0"
    else
        echo "❌ Failed to add multicast route"
        exit 1
    fi
fi

echo ""

# Make it permanent by adding to /etc/dhcpcd.conf
echo "Step 5: Making multicast route permanent..."

if grep -q "ip route add 224.0.0.0/4" /etc/dhcpcd.conf 2>/dev/null; then
    echo "✅ Multicast route already configured in /etc/dhcpcd.conf"
else
    echo "Adding multicast route to /etc/dhcpcd.conf..."

    # Backup dhcpcd.conf
    sudo cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup.$(date +%Y%m%d_%H%M%S)

    # Add multicast route configuration
    echo "" | sudo tee -a /etc/dhcpcd.conf > /dev/null
    echo "# NotaGotchi: Add multicast route for mDNS" | sudo tee -a /etc/dhcpcd.conf > /dev/null
    echo "interface $WIFI_INTERFACE" | sudo tee -a /etc/dhcpcd.conf > /dev/null
    echo "    static route_metric=224.0.0.0/4" | sudo tee -a /etc/dhcpcd.conf > /dev/null

    echo "✅ Multicast route will persist after reboot"
fi

echo ""

# Restart avahi-daemon
echo "Step 6: Restarting Avahi daemon..."
sudo systemctl restart avahi-daemon

if [ $? -eq 0 ]; then
    echo "✅ Avahi daemon restarted"
else
    echo "❌ Failed to restart Avahi daemon"
    exit 1
fi

echo ""

# Test mDNS
echo "========================================================================"
echo "TESTING mDNS"
echo "========================================================================"
echo ""
echo "Scanning for mDNS services for 3 seconds..."
echo "(This should work after you start the server)"
echo ""

timeout 3 avahi-browse -a -t 2>/dev/null | head -n 20

echo ""
echo "========================================================================"
echo "✅ mDNS FIX COMPLETE!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "  1. Run this script on BOTH Raspberry Pis"
echo "  2. On Pi #1: python3 test_wifi_server.py NotaGotchi_TestA"
echo "  3. On Pi #2: python3 test_wifi_client.py"
echo ""
echo "To test if mDNS is working manually:"
echo "  avahi-browse _notagotchi._tcp -t"
echo ""
echo "========================================================================"
