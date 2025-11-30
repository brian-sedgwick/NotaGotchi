#!/bin/bash
# Install Symbola emoji font for NotaGotchi

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo ""
echo "=================================================="
echo "   Installing Symbola Emoji Font"
echo "=================================================="
echo ""

# Create fonts directory if it doesn't exist
FONTS_DIR="$HOME/.fonts"
if [ ! -d "$FONTS_DIR" ]; then
    print_info "Creating fonts directory..."
    mkdir -p "$FONTS_DIR"
    print_success "Created $FONTS_DIR"
fi

# Download Symbola font from Internet Archive
print_info "Downloading Symbola.ttf from Internet Archive..."
FONT_URL="https://archive.org/download/Symbola/Symbola613.ttf"
FONT_PATH="$FONTS_DIR/Symbola.ttf"

if wget -O "$FONT_PATH" "$FONT_URL"; then
    print_success "Font downloaded successfully"
else
    echo "Error: Failed to download font"
    exit 1
fi

# Update font cache (if fc-cache is available)
if command -v fc-cache &> /dev/null; then
    print_info "Updating font cache..."
    fc-cache -f -v
    print_success "Font cache updated"
else
    print_info "fc-cache not available, skipping cache update"
fi

# Verify installation
if [ -f "$FONT_PATH" ]; then
    print_success "Symbola font installed to $FONT_PATH"
    ls -lh "$FONT_PATH"
else
    echo "Error: Font file not found after installation"
    exit 1
fi

echo ""
echo "=================================================="
print_success "Font Installation Complete!"
echo "=================================================="
echo ""
print_info "Font location: $FONT_PATH"
print_info "Next step: Run ./update.sh to apply code changes"
echo ""
