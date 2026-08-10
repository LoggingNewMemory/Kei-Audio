#!/bin/bash
set -e

echo "======================================"
echo "    Kei Audio Installation Script     "
echo "======================================"
echo ""

echo "1. Installing dependencies via pacman..."
# python-pystray, python-pillow, tk (for UI), libpulse (for pactl)
sudo pacman -Syu --needed --noconfirm tk libpulse python-pystray python-pillow

echo ""
echo "2. Creating Desktop Shortcut..."

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_PATH="$APP_DIR/Design/Icon.png"
EXEC_PATH="python3 $APP_DIR/kei_main.py"

DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

DESKTOP_FILE="$DESKTOP_DIR/kei-audio.desktop"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=ケイ Audio
Comment=System-wide audio equalizer and enhancer
Exec=$EXEC_PATH
Icon=$ICON_PATH
Terminal=false
Categories=Audio;AudioVideo;
StartupNotify=false
EOF

chmod +x "$DESKTOP_FILE"

echo ""
echo "Installation complete!"
echo "You can now launch 'ケイ Audio' from your desktop application menu."
