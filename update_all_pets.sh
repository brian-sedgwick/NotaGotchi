#!/bin/bash

#
# Update All NotaGotchi Pets
#
# This script pulls the latest code and runs update.sh on all NotaGotchi devices.
# It gracefully handles offline devices without errors.
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
# FUNCTIONS
# =============================================================================

# Check if a host is reachable via SSH
is_online() {
    local host=$1
    ssh -o ConnectTimeout=$TIMEOUT -o BatchMode=yes -o StrictHostKeyChecking=no \
        "$host" "exit" &>/dev/null
    return $?
}

# Update a single pet
update_pet() {
    local pet_num=$1
    local hostname="${HOSTNAME_PREFIX}${pet_num}"
    local ssh_host="${SSH_USER}@${hostname}"

    echo ""
    echo "========================================"
    echo "Checking ${hostname}..."
    echo "========================================"

    # Check if device is online
    if ! is_online "$ssh_host"; then
        echo "⚠️  ${hostname} is offline, skipping..."
        return 1
    fi

    echo "✅ ${hostname} is online"
    echo ""
    echo "📥 Pulling latest code..."

    # Pull latest code
    if ! ssh "$ssh_host" "cd $PROJECT_DIR && git pull"; then
        echo "❌ Failed to pull code on ${hostname}"
        return 1
    fi

    echo ""
    echo "🔄 Running update script..."

    # Run update script
    if ! ssh "$ssh_host" "cd $PROJECT_DIR && ./update.sh"; then
        echo "❌ Failed to run update.sh on ${hostname}"
        return 1
    fi

    echo ""
    echo "✅ ${hostname} updated successfully!"
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

echo "╔════════════════════════════════════════╗"
echo "║   NotaGotchi Mass Update Script       ║"
echo "╔════════════════════════════════════════╗"
echo ""
echo "Configuration:"
echo "  Max pets: ${MAX_PETS}"
echo "  SSH user: ${SSH_USER}"
echo "  Hostname pattern: ${HOSTNAME_PREFIX}[1-${MAX_PETS}]"
echo "  Project directory: ${PROJECT_DIR}"
echo "  Connection timeout: ${TIMEOUT}s"
echo ""

# Counters
total=0
online=0
updated=0
failed=0
offline=0

# Update each pet
for i in $(seq 1 $MAX_PETS); do
    ((total++))

    if update_pet $i; then
        ((online++))
        ((updated++))
    elif is_online "${SSH_USER}@${HOSTNAME_PREFIX}${i}"; then
        ((online++))
        ((failed++))
    else
        ((offline++))
    fi
done

# Summary
echo ""
echo "╔════════════════════════════════════════╗"
echo "║          Update Summary                ║"
echo "╔════════════════════════════════════════╗"
echo ""
echo "Total pets checked: ${total}"
echo "├─ 🟢 Online: ${online}"
echo "│  ├─ ✅ Updated successfully: ${updated}"
echo "│  └─ ❌ Failed to update: ${failed}"
echo "└─ ⚠️  Offline: ${offline}"
echo ""

if [ $failed -gt 0 ]; then
    echo "⚠️  Some pets failed to update. Check logs above."
    exit 1
elif [ $updated -eq 0 ]; then
    echo "⚠️  No pets were updated (all offline?)."
    exit 1
else
    echo "✅ All online pets updated successfully!"
    exit 0
fi
