#!/bin/bash
# Not-A-Gotchi Update Script
# Updates dependencies and restarts the service

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
echo "   Not-A-Gotchi Update Script"
echo "=================================================="
echo ""

# Detect environment
print_info "Detecting environment..."

CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)
INSTALL_DIR=$(pwd)
SERVICE_NAME="not-a-gotchi"
VENV_DIR="$INSTALL_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

print_info "Detected settings:"
echo "  User:          $CURRENT_USER"
echo "  Group:         $CURRENT_GROUP"
echo "  Install dir:   $INSTALL_DIR"
echo "  Venv dir:      $VENV_DIR"
echo ""

# Verify we're in the right directory
if [ ! -f "src/main.py" ]; then
    print_error "Cannot find src/main.py"
    print_error "Please run this script from the NotaGotchi directory"
    exit 1
fi

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    print_error "Virtual environment not found at $VENV_DIR"
    print_error "Please run ./install.sh first"
    exit 1
fi

# Check if service exists
if ! systemctl list-unit-files | grep -q "${SERVICE_NAME}.service"; then
    print_error "Service ${SERVICE_NAME}.service not found"
    print_error "Please run ./install.sh first"
    exit 1
fi

# Stop the service if running
print_info "Checking service status..."
if systemctl is-active --quiet ${SERVICE_NAME}.service; then
    print_info "Stopping ${SERVICE_NAME} service..."
    if sudo systemctl stop ${SERVICE_NAME}.service; then
        print_success "Service stopped"
    else
        print_error "Failed to stop service"
        exit 1
    fi
else
    print_info "Service is not running"
fi

# Update Python dependencies
print_info "Updating Python dependencies..."
if [ -f "requirements.txt" ]; then
    if "$VENV_PYTHON" -m pip install --upgrade pip; then
        print_success "pip upgraded"
    fi

    if "$VENV_PYTHON" -m pip install -r requirements.txt --upgrade; then
        print_success "Dependencies updated"
    else
        print_error "Failed to update dependencies"
        exit 1
    fi
else
    print_error "requirements.txt not found"
    exit 1
fi

# Regenerate and update systemd service file
print_info "Updating systemd service file..."

SERVICE_FILE="/tmp/${SERVICE_NAME}.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Not-A-Gotchi Virtual Pet
Documentation=https://github.com/yourusername/not-a-gotchi
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_GROUP
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_PYTHON $INSTALL_DIR/src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment="PYTHONUNBUFFERED=1"
Environment="VIRTUAL_ENV=$VENV_DIR"
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

if sudo cp "$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"; then
    print_success "Service file updated"
    rm "$SERVICE_FILE"
else
    print_error "Failed to update service file"
    exit 1
fi

# Reload systemd
print_info "Reloading systemd daemon..."
if sudo systemctl daemon-reload; then
    print_success "Systemd reloaded"
else
    print_error "Failed to reload systemd"
    exit 1
fi

# Start the service
print_info "Starting ${SERVICE_NAME} service..."
if sudo systemctl start ${SERVICE_NAME}.service; then
    print_success "Service started"
    sleep 2

    # Check status
    print_info "Checking service status..."
    sudo systemctl status ${SERVICE_NAME}.service --no-pager -n 10
else
    print_error "Failed to start service"
    print_info "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi

# Update complete
echo ""
echo "=================================================="
print_success "Update Complete!"
echo "=================================================="
echo ""
print_info "Useful commands:"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
