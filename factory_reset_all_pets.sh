#!/bin/bash

#
# Factory Reset All NotaGotchi Pets Remotely
#
# This script remotely factory resets all NotaGotchi devices.
# WARNING: This is EXTREMELY DESTRUCTIVE and will wipe all pets!
#
# Usage: ./factory_reset_all_pets.sh
#

# =============================================================================
# CONFIGURATION
# =============================================================================

# Maximum number of pets (adjustable)
MAX_PETS=8

# SSH user
SSH_USER="brian"

# Base hostname pattern (rp0-1, rp0-2, etc.)
HOSTNAME_PREFIX="rp0-"

# Project directory on each pet
PROJECT_DIR="~/source/NotaGotchi"

# SSH connection timeout (seconds)
TIMEOUT=5

# =============================================================================
# COLORS
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# FUNCTIONS
# =============================================================================

# Check if a host is reachable via SSH
is_online() {
    local host=$1
    ssh -o ConnectTimeout=$TIMEOUT -o BatchMode=yes -o StrictHostKeyChecking=no \
        "$host" "exit" &>/dev/null
    return $?
}

# Factory reset a single pet
factory_reset_pet() {
    local pet_num=$1
    local hostname="${HOSTNAME_PREFIX}${pet_num}"
    local ssh_host="${SSH_USER}@${hostname}"

    echo ""
    echo "========================================"
    echo "Checking ${hostname}..."
    echo "========================================"

    # Check if device is online
    if ! is_online "$ssh_host"; then
        echo -e "${YELLOW}⚠️  ${hostname} is offline, skipping...${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ ${hostname} is online${NC}"
    echo ""
    echo -e "${RED}💣 Factory resetting ${hostname}...${NC}"

    # Run factory reset script remotely (pipe YES to bypass confirmation)
    if ! ssh "$ssh_host" "cd $PROJECT_DIR && echo 'YES' | ./factory_reset.sh"; then
        echo -e "${RED}❌ Failed to factory reset ${hostname}${NC}"
        return 1
    fi

    echo ""
    echo -e "${GREEN}✅ ${hostname} factory reset successfully!${NC}"
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

echo ""
echo -e "${RED}╔════════════════════════════════════════╗${NC}"
echo -e "${RED}║   NotaGotchi Mass Factory Reset       ║${NC}"
echo -e "${RED}╔════════════════════════════════════════╗${NC}"
echo ""
echo -e "${RED}⚠️  ⚠️  ⚠️  EXTREME DANGER  ⚠️  ⚠️  ⚠️${NC}"
echo ""
echo -e "${RED}This will PERMANENTLY DELETE ALL DATA from ALL pets:${NC}"
echo "  • All pet data and history"
echo "  • All friends and messages"
echo "  • All configuration"
echo ""
echo "Backups will be created on each device, but this"
echo "operation is IRREVERSIBLE!"
echo ""
echo "Configuration:"
echo "  Max pets: ${MAX_PETS}"
echo "  SSH user: ${SSH_USER}"
echo "  Hostname pattern: ${HOSTNAME_PREFIX}[1-${MAX_PETS}]"
echo "  Project directory: ${PROJECT_DIR}"
echo "  Connection timeout: ${TIMEOUT}s"
echo ""

# Triple confirmation (because this is REALLY destructive)
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo -e "${YELLOW}CONFIRMATION STEP 1 OF 3${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo ""
read -p "Do you want to factory reset ALL pets? (yes/no): " confirm1

if [[ "$confirm1" != "yes" ]]; then
    echo ""
    echo "Factory reset cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo -e "${YELLOW}CONFIRMATION STEP 2 OF 3${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo ""
read -p "This will delete ALL pet data. Are you SURE? (yes/no): " confirm2

if [[ "$confirm2" != "yes" ]]; then
    echo ""
    echo "Factory reset cancelled."
    exit 0
fi

echo ""
echo -e "${RED}═══════════════════════════════════════════${NC}"
echo -e "${RED}FINAL CONFIRMATION - STEP 3 OF 3${NC}"
echo -e "${RED}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${RED}Type 'RESET ALL PETS' in ALL CAPS to confirm:${NC}"
read -p "> " confirm3

if [[ "$confirm3" != "RESET ALL PETS" ]]; then
    echo ""
    echo "Factory reset cancelled."
    exit 0
fi

echo ""
echo -e "${RED}Starting mass factory reset...${NC}"
echo ""

# Counters
total=0
online=0
reset=0
failed=0
offline=0

# Factory reset each pet
for i in $(seq 1 $MAX_PETS); do
    ((total++))

    if factory_reset_pet $i; then
        ((online++))
        ((reset++))
    elif is_online "${SSH_USER}@${HOSTNAME_PREFIX}${i}"; then
        ((online++))
        ((failed++))
    else
        ((offline++))
    fi

    # Small delay between resets to avoid overwhelming the network
    if [ $i -lt $MAX_PETS ]; then
        sleep 1
    fi
done

# Summary
echo ""
echo "╔════════════════════════════════════════╗"
echo "║          Factory Reset Summary         ║"
echo "╔════════════════════════════════════════╗"
echo ""
echo "Total pets checked: ${total}"
echo "├─ 🟢 Online: ${online}"
echo "│  ├─ ✅ Factory reset successfully: ${reset}"
echo "│  └─ ❌ Failed to reset: ${failed}"
echo "└─ ⚠️  Offline: ${offline}"
echo ""

if [ $failed -gt 0 ]; then
    echo -e "${RED}⚠️  Some pets failed to factory reset. Check logs above.${NC}"
    exit 1
elif [ $reset -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No pets were reset (all offline?).${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All online pets factory reset successfully!${NC}"
    echo ""
    echo "All pets will be in initial setup state on next use."
    echo "Backups are stored in data/ directory on each device."
    exit 0
fi
