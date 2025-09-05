#!/bin/bash
# Whisper-to-Talk Installation Script

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check for required commands
    local required_commands=("python3" "pip" "pactl" "parecord" "wl-copy")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -ne 0 ]; then
        error "Missing required commands: ${missing_commands[*]}"
        echo "Please install the following packages:"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip pulseaudio-utils wl-clipboard"
        echo "  Arch Linux: sudo pacman -S python python-pip pipewire wl-clipboard"
        echo "  Fedora: sudo dnf install python3 python3-pip pipewire-utils wl-clipboard"
        exit 1
    fi
    
    # Check Python version
    local python_version
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    if [[ $(echo "$python_version < 3.8" | bc -l 2>/dev/null || echo "1") == "1" ]]; then
        error "Python 3.8+ required, found $python_version"
        exit 1
    fi
    
    success "System requirements satisfied"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv "$INSTALL_DIR/venv"
    fi
    
    # Activate virtual environment and install dependencies
    source "$INSTALL_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/requirements.txt"
    
    success "Python dependencies installed"
}

# Make scripts executable
setup_scripts() {
    log "Setting up executable permissions..."
    
    chmod +x "$INSTALL_DIR/hyprland_transcribe_simple.sh"
    chmod +x "$INSTALL_DIR/transcription_server.py"
    chmod +x "$INSTALL_DIR/transcribe_client.py"
    chmod +x "$INSTALL_DIR/start_transcription_server.sh"
    chmod +x "$INSTALL_DIR/install-service.sh"
    
    success "Scripts configured"
}

# Update script paths
update_paths() {
    log "Updating script paths..."
    
    # Update paths in scripts to use current installation directory
    sed -i "s|SCRIPT_DIR=\".*\"|SCRIPT_DIR=\"$INSTALL_DIR\"|g" "$INSTALL_DIR/hyprland_transcribe_simple.sh"
    sed -i "s|SCRIPT_DIR=\".*\"|SCRIPT_DIR=\"$INSTALL_DIR\"|g" "$INSTALL_DIR/start_transcription_server.sh"
    
    success "Paths updated"
}

# Setup Hyprland integration
setup_hyprland() {
    log "Setting up Hyprland integration..."
    
    local hypr_config_dir="$HOME/.config/hypr"
    local keybindings_file="$hypr_config_dir/keybindings.conf"
    
    if [ ! -d "$hypr_config_dir" ]; then
        warning "Hyprland config directory not found at $hypr_config_dir"
        log "You'll need to manually add the key binding to your Hyprland config:"
        echo "bind = , F9, exec, $INSTALL_DIR/hyprland_transcribe_simple.sh toggle"
        return
    fi
    
    local binding_line="bind = , F9, exec, $INSTALL_DIR/hyprland_transcribe_simple.sh toggle"
    
    if ! grep -q "whisper.*toggle" "$keybindings_file" 2>/dev/null; then
        echo "" >> "$keybindings_file"
        echo "# Whisper-to-Talk key binding" >> "$keybindings_file"
        echo "$binding_line" >> "$keybindings_file"
        success "Added F9 key binding to Hyprland config"
        
        log "Reloading Hyprland configuration..."
        if command -v hyprctl >/dev/null 2>&1; then
            hyprctl reload
            success "Hyprland configuration reloaded"
        else
            warning "hyprctl not found, please reload Hyprland manually"
        fi
    else
        warning "Key binding already exists in Hyprland config"
    fi
}

# Test installation
test_installation() {
    log "Testing installation..."
    
    # Test that scripts can run
    if ! "$INSTALL_DIR/start_transcription_server.sh" status >/dev/null 2>&1; then
        log "Server not running, which is expected for a fresh install"
    fi
    
    # Test audio device detection
    if ! pactl list sources | grep -q "input"; then
        warning "No audio input devices detected"
        log "Please ensure your microphone is connected and working"
    fi
    
    success "Installation test completed"
}

# Main installation function
main() {
    log "Starting Whisper-to-Talk installation..."
    
    check_requirements
    install_python_deps
    setup_scripts
    update_paths
    setup_hyprland
    test_installation
    
    success "Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Start the transcription server:"
    echo "   $INSTALL_DIR/start_transcription_server.sh start"
    echo ""
    echo "2. Test the system:"
    echo "   - Press F9 to start recording"
    echo "   - Speak a message"
    echo "   - Press F9 again to stop and transcribe"
    echo ""
    echo "3. Optional: Install as system service:"
    echo "   $INSTALL_DIR/install-service.sh"
    echo ""
    echo "For troubleshooting, see logs at:"
    echo "   /tmp/whisper_server.log"
    echo "   /tmp/whisper_transcription.log"
}

# Run main function
main "$@"