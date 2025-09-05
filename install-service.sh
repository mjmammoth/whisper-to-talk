#!/bin/bash
# Install Whisper Transcriber as a user service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/whisper-transcriber.service"

echo "Installing Whisper Transcriber user service..."

# Copy service file to user systemd directory
mkdir -p ~/.config/systemd/user
cp "$SERVICE_FILE" ~/.config/systemd/user/

# Reload systemd and enable the service
systemctl --user daemon-reload
systemctl --user enable whisper-transcriber.service
systemctl --user start whisper-transcriber.service

echo "Service installed and started!"
echo "Status: $(systemctl --user is-active whisper-transcriber.service)"
echo ""
echo "To check status: systemctl --user status whisper-transcriber"
echo "To stop: systemctl --user stop whisper-transcriber"
echo "To disable: systemctl --user disable whisper-transcriber"