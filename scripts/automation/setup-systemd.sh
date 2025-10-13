#!/bin/bash
# CardFlux systemd Service Setup (Linux)
# Run as root or with sudo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_FILE="$SCRIPT_DIR/cardflux-update.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "========================================"
echo "CardFlux systemd Service Setup"
echo "========================================"
echo ""
echo "Configuration:"
echo "  Root directory: $ROOT_DIR"
echo "  Service file: $SERVICE_FILE"
echo "  systemd directory: $SYSTEMD_DIR"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Check if service file exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Update service file with actual paths
TEMP_SERVICE="/tmp/cardflux-update.service"
sed "s|/opt/cardflux|$ROOT_DIR|g" "$SERVICE_FILE" > "$TEMP_SERVICE"

# Copy service file
echo "📄 Installing service file..."
cp "$TEMP_SERVICE" "$SYSTEMD_DIR/cardflux-update.service"
chmod 644 "$SYSTEMD_DIR/cardflux-update.service"

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
systemctl enable cardflux-update.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "Management Commands:"
echo "  Start service:   sudo systemctl start cardflux-update"
echo "  Stop service:    sudo systemctl stop cardflux-update"
echo "  Status:          sudo systemctl status cardflux-update"
echo "  View logs:       sudo journalctl -u cardflux-update -f"
echo "  Restart:         sudo systemctl restart cardflux-update"
echo "  Disable:         sudo systemctl disable cardflux-update"
echo ""
echo "To start the service now:"
echo "  sudo systemctl start cardflux-update"
echo ""
