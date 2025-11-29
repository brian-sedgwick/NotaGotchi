#!/bin/bash
# Not-A-Gotchi Installation Script
# Automatically detects user, paths, and sets up the service

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
echo "   Not-A-Gotchi Installation Script"
echo "=================================================="
echo ""

# Detect environment
print_info "Detecting environment..."

CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)
INSTALL_DIR=$(pwd)
PYTHON_PATH=$(which python3)
SERVICE_NAME="not-a-gotchi"
DATA_DIR="$HOME/data"
VENV_DIR="$INSTALL_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

print_info "Detected settings:"
echo "  User:          $CURRENT_USER"
echo "  Group:         $CURRENT_GROUP"
echo "  Install dir:   $INSTALL_DIR"
echo "  Python:        $PYTHON_PATH"
echo "  Venv dir:      $VENV_DIR"
echo "  Data dir:      $DATA_DIR"
echo ""

# Verify we're in the right directory
if [ ! -f "src/main.py" ]; then
    print_error "Cannot find src/main.py"
    print_error "Please run this script from the NotaGotchi directory"
    exit 1
fi

# Check and install system dependencies
print_info "Checking system dependencies..."
MISSING_DEPS=()

# Check for python3-venv
if ! dpkg -l | grep -q python3-venv; then
    MISSING_DEPS+=("python3-venv")
fi

# Check for python3-dev (needed for lgpio compilation)
if ! dpkg -l | grep -q python3-dev; then
    MISSING_DEPS+=("python3-dev")
fi

# Check for swig (needed for lgpio compilation)
if ! command -v swig &> /dev/null; then
    MISSING_DEPS+=("swig")
fi

# Check for build-essential (gcc, etc.)
if ! dpkg -l | grep -q build-essential; then
    MISSING_DEPS+=("build-essential")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    print_warning "Missing system dependencies: ${MISSING_DEPS[*]}"
    read -p "Install missing dependencies? (requires sudo) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing system dependencies..."
        if sudo apt-get update && sudo apt-get install -y "${MISSING_DEPS[@]}"; then
            print_success "System dependencies installed"
        else
            print_error "Failed to install system dependencies"
            print_warning "You may need to install them manually:"
            print_warning "  sudo apt-get install ${MISSING_DEPS[*]}"
            exit 1
        fi
    else
        print_warning "Skipping system dependencies"
        print_warning "Installation may fail without them"
    fi
else
    print_success "All system dependencies present"
fi

# Create Python virtual environment
print_info "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating virtual environment..."
    if $PYTHON_PATH -m venv "$VENV_DIR"; then
        print_success "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        print_error "Make sure python3-venv is installed: sudo apt install python3-venv"
        exit 1
    fi
else
    print_success "Virtual environment already exists"
fi

# Install dependencies in venv
print_info "Installing Python dependencies in virtual environment..."
if [ -f "requirements.txt" ]; then
    if "$VENV_PYTHON" -m pip install --upgrade pip; then
        print_success "pip upgraded"
    fi

    if "$VENV_PYTHON" -m pip install -r requirements.txt; then
        print_success "Dependencies installed"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
else
    print_error "requirements.txt not found"
    exit 1
fi

# Create data directory
print_info "Setting up data directory..."
if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    print_success "Created $DATA_DIR"
else
    print_success "Data directory already exists"
fi

# Generate sprites
print_info "Generating placeholder sprites..."
if [ ! -f "src/resources/sprites/happy.bmp" ]; then
    cd src
    if "$VENV_PYTHON" create_placeholder_sprites.py; then
        print_success "Sprites generated successfully"
    else
        print_warning "Failed to generate sprites (you can do this later)"
    fi
    cd ..
else
    print_success "Sprites already exist"
fi

# Check SPI is enabled (for display)
print_info "Checking SPI configuration..."
if lsmod | grep -q spi; then
    print_success "SPI is enabled"
else
    print_warning "SPI may not be enabled"
    print_info "You may need to enable SPI:"
    print_info "  sudo raspi-config"
    print_info "  -> Interface Options -> SPI -> Enable"
fi

# Optional: Install lgpio (recommended for newer Pi systems)
print_info "Checking for lgpio (optional, recommended)..."
if dpkg -l | grep -q python3-lgpio; then
    print_success "python3-lgpio is installed"
else
    print_warning "python3-lgpio not found (gpiozero will use RPi.GPIO fallback)"
    read -p "Install python3-lgpio from system packages? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing python3-lgpio..."
        if sudo apt-get install -y python3-lgpio; then
            print_success "python3-lgpio installed"
        else
            print_warning "Failed to install python3-lgpio"
            print_info "Continuing with RPi.GPIO fallback (this is fine)"
        fi
    else
        print_info "Skipping lgpio installation (RPi.GPIO will be used)"
    fi
fi

# Check GPIO permissions
print_info "Checking GPIO permissions..."
if groups $CURRENT_USER | grep -q '\bgpio\b'; then
    print_success "User '$CURRENT_USER' is in gpio group"
else
    print_warning "User '$CURRENT_USER' is NOT in gpio group"
    print_info "Adding user to gpio group for GPIO access..."
    if sudo usermod -a -G gpio $CURRENT_USER; then
        print_success "User added to gpio group"
        print_warning "You will need to log out and back in for this to take effect"
        print_info "Or run: newgrp gpio"
    else
        print_warning "Failed to add user to gpio group"
        print_info "You may need to run the application with sudo"
    fi
fi

# Check if any not-a-gotchi service is running
if systemctl is-active --quiet ${SERVICE_NAME}.service 2>/dev/null; then
    print_warning "Old ${SERVICE_NAME} service is running"
    print_info "Stopping old service to free GPIO pins..."
    sudo systemctl stop ${SERVICE_NAME}.service
    print_success "Old service stopped"
fi

# Generate systemd service file
print_info "Generating systemd service file..."

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
Environment="PATH=$VENV_DIR/bin:\$PATH"

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

print_success "Service file generated"

# Install service
print_info "Installing systemd service..."
print_warning "This requires sudo privileges"

if sudo cp "$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"; then
    print_success "Service file installed"
    rm "$SERVICE_FILE"
else
    print_error "Failed to install service file"
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

# Enable service
print_info "Enabling service for auto-start..."
if sudo systemctl enable ${SERVICE_NAME}.service; then
    print_success "Service enabled"
else
    print_error "Failed to enable service"
    exit 1
fi

# Ask if user wants to start now
echo ""
read -p "Start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting service..."
    if sudo systemctl start ${SERVICE_NAME}.service; then
        print_success "Service started"
        sleep 2

        # Check status
        print_info "Checking service status..."
        sudo systemctl status ${SERVICE_NAME}.service --no-pager
    else
        print_error "Failed to start service"
        print_info "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
        exit 1
    fi
else
    print_info "Service not started"
    print_info "Start manually with: sudo systemctl start ${SERVICE_NAME}"
fi

# Installation complete
echo ""
echo "=================================================="
print_success "Installation Complete!"
echo "=================================================="
echo ""
print_info "Useful commands:"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo ""
print_info "To uninstall, run: ./uninstall.sh"
echo ""
