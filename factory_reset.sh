#!/bin/bash

#
# Factory Reset Script for Not-A-Gotchi
#
# This script performs a complete factory reset:
# - Backs up the current database
# - Stops the service
# - Deletes all user data
# - Restarts the service (creates fresh database)
#
# Usage: ./factory_reset.sh
#

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_DIR="$HOME/source/NotaGotchi"
DATA_DIR="$PROJECT_DIR/data"
DATABASE_FILE="$DATA_DIR/not-a-gotchi.db"
SERVICE_NAME="not-a-gotchi"

# =============================================================================
# COLORS FOR OUTPUT
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# FUNCTIONS
# =============================================================================

print_header() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║   Not-A-Gotchi Factory Reset          ║"
    echo "╔════════════════════════════════════════╗"
    echo ""
}

print_warning() {
    echo -e "${RED}⚠️  WARNING: DESTRUCTIVE OPERATION${NC}"
    echo ""
    echo "This will permanently delete:"
    echo "  • Your pet and all its history"
    echo "  • All friends and friend requests"
    echo "  • All messages"
    echo "  • All configuration"
    echo ""
    echo "A backup will be created, but the device will"
    echo "return to initial setup state."
    echo ""
}

confirm_reset() {
    echo -e "${YELLOW}Are you ABSOLUTELY SURE you want to factory reset?${NC}"
    echo -n "Type 'YES' in all caps to confirm: "
    read -r confirmation

    if [ "$confirmation" != "YES" ]; then
        echo ""
        echo "Factory reset cancelled."
        exit 0
    fi
}

backup_database() {
    if [ ! -f "$DATABASE_FILE" ]; then
        echo "ℹ️  No database found at $DATABASE_FILE"
        echo "   Nothing to backup."
        return 0
    fi

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${DATABASE_FILE}.backup.${timestamp}"

    echo ""
    echo "📦 Creating backup..."
    cp "$DATABASE_FILE" "$backup_file"
    echo -e "${GREEN}✅ Backup created: $backup_file${NC}"
}

stop_service() {
    echo ""
    echo "⏹️  Stopping $SERVICE_NAME service..."
    sudo systemctl stop "$SERVICE_NAME"
    echo -e "${GREEN}✅ Service stopped${NC}"
}

delete_database() {
    echo ""
    echo "🗑️  Deleting database and WAL files..."

    # Delete main database
    if [ -f "$DATABASE_FILE" ]; then
        rm "$DATABASE_FILE"
        echo "   Deleted: not-a-gotchi.db"
    fi

    # Delete WAL file (Write-Ahead Log)
    if [ -f "${DATABASE_FILE}-wal" ]; then
        rm "${DATABASE_FILE}-wal"
        echo "   Deleted: not-a-gotchi.db-wal"
    fi

    # Delete SHM file (Shared Memory)
    if [ -f "${DATABASE_FILE}-shm" ]; then
        rm "${DATABASE_FILE}-shm"
        echo "   Deleted: not-a-gotchi.db-shm"
    fi

    echo -e "${GREEN}✅ All user data deleted${NC}"
}

start_service() {
    echo ""
    echo "▶️  Starting $SERVICE_NAME service..."
    sudo systemctl start "$SERVICE_NAME"

    # Wait a moment for service to start
    sleep 2

    # Check if service started successfully
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ Service started successfully${NC}"
    else
        echo -e "${RED}❌ Service failed to start${NC}"
        echo "   Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

verify_reset() {
    echo ""
    echo "🔍 Verifying factory reset..."

    # Give the service a moment to initialize
    sleep 2

    # Check if new database was created
    if [ -f "$DATABASE_FILE" ]; then
        echo -e "${GREEN}✅ New database created${NC}"
    else
        echo -e "${YELLOW}⚠️  Database not yet created (may still be initializing)${NC}"
    fi
}

print_success() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║   Factory Reset Complete! ✅           ║"
    echo "╔════════════════════════════════════════╗"
    echo ""
    echo "Your Not-A-Gotchi has been reset to factory state."
    echo "On next use, you'll be prompted to enter a new pet name."
    echo ""
    echo "Backups are stored in: $DATA_DIR"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

print_header
print_warning
confirm_reset

# Perform factory reset
backup_database
stop_service
delete_database
start_service
verify_reset
print_success

exit 0
