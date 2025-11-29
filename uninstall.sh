#!/bin/bash
# Not-A-Gotchi Uninstallation Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Header
echo ""
echo "=================================================="
echo "   Not-A-Gotchi Uninstallation Script"
echo "=================================================="
echo ""

SERVICE_NAME="not-a-gotchi"
DATA_DIR="$HOME/data"

# Confirm uninstallation
print_warning "This will remove the Not-A-Gotchi service"
read -p "Are you sure you want to uninstall? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Uninstallation cancelled"
    exit 0
fi

# Stop service if running
print_info "Stopping service..."
if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
    if sudo systemctl stop ${SERVICE_NAME}.service; then
        print_success "Service stopped"
    else
        print_warning "Failed to stop service (may not be running)"
    fi
else
    print_info "Service not running"
fi

# Disable service
print_info "Disabling service..."
if sudo systemctl is-enabled --quiet ${SERVICE_NAME}.service; then
    if sudo systemctl disable ${SERVICE_NAME}.service; then
        print_success "Service disabled"
    else
        print_warning "Failed to disable service"
    fi
else
    print_info "Service not enabled"
fi

# Remove service file
print_info "Removing service file..."
if [ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
    if sudo rm "/etc/systemd/system/${SERVICE_NAME}.service"; then
        print_success "Service file removed"
    else
        print_error "Failed to remove service file"
        exit 1
    fi
else
    print_info "Service file not found"
fi

# Reload systemd
print_info "Reloading systemd daemon..."
if sudo systemctl daemon-reload; then
    print_success "Systemd reloaded"
else
    print_warning "Failed to reload systemd"
fi

# Ask about data
echo ""
read -p "Do you want to delete pet data in $DATA_DIR? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$DATA_DIR" ]; then
        print_info "Backing up database before deletion..."
        if [ -f "$DATA_DIR/not-a-gotchi.db" ]; then
            BACKUP_FILE="$HOME/not-a-gotchi-backup-$(date +%Y%m%d-%H%M%S).db"
            cp "$DATA_DIR/not-a-gotchi.db" "$BACKUP_FILE"
            print_success "Backup created: $BACKUP_FILE"
        fi

        print_info "Deleting data directory..."
        rm -rf "$DATA_DIR"
        print_success "Data directory removed"
    else
        print_info "Data directory not found"
    fi
else
    print_info "Keeping data directory"
    print_info "Pet data preserved in: $DATA_DIR"
fi

# Ask about source code
echo ""
print_warning "The source code in $(pwd) has NOT been deleted"
read -p "Do you want to delete the source code directory? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Deleting source directory..."
    cd ..
    SOURCE_DIR=$(basename "$OLDPWD")
    rm -rf "$SOURCE_DIR"
    print_success "Source directory removed"
else
    print_info "Source code preserved"
fi

# Uninstallation complete
echo ""
echo "=================================================="
print_success "Uninstallation Complete!"
echo "=================================================="
echo ""

if [ -f "$BACKUP_FILE" ]; then
    print_info "Database backup saved to: $BACKUP_FILE"
fi

print_info "To reinstall, run ./install.sh from the source directory"
echo ""
