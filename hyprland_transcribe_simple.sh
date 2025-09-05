#!/bin/bash
#
# Simplified Hyprland Push-to-Transcribe Integration Script
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRANSCRIBER_SCRIPT="$SCRIPT_DIR/transcribe_client.py"
VENV_PATH="$SCRIPT_DIR/venv"
PID_FILE="/tmp/whisper_recording.pid"
STATUS_FILE="/tmp/whisper_status.json"
AUDIO_FILE="/tmp/whisper_current_recording.wav"
NOTIFICATION_CMD="notify-send"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" >&2
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

# Send notification if available
notify() {
    if command -v "$NOTIFICATION_CMD" >/dev/null 2>&1; then
        "$NOTIFICATION_CMD" "Whisper Transcriber" "$1" >/dev/null 2>&1 || true
    fi
    log "$1"
}

# Update status file for Waybar
update_status() {
    local state="$1"
    local message="${2:-Status: $state}"
    local timestamp=$(date +%s.%N)
    
    cat > "$STATUS_FILE" << EOF
{"state": "$state", "timestamp": $timestamp, "message": "$message"}
EOF
}

# Function to run transcription script
run_transcriber() {
    cd "$SCRIPT_DIR" || exit 1
    
    if [ -d "$VENV_PATH" ] && [ -x "$VENV_PATH/bin/python" ]; then
        PYTHONPATH="$SCRIPT_DIR" "$VENV_PATH/bin/python" "$TRANSCRIBER_SCRIPT" "$@"
    else
        warning "Virtual environment not found at $VENV_PATH, using system python"
        PYTHONPATH="$SCRIPT_DIR" python3 "$TRANSCRIBER_SCRIPT" "$@"
    fi
}

# Start recording function
start_recording() {
    if [ -f "$PID_FILE" ]; then
        warning "Recording already in progress"
        return 1
    fi
    
    log "Starting recording..."
    update_status "recording" "Recording audio..."
    notify "🎤 Recording started"
    
    # Clean up any previous audio file
    rm -f "$AUDIO_FILE"
    
    # Start parecord directly
    parecord \
        --device=alsa_input.usb-SteelSeries_Arctis_Nova_7-00.mono-fallback \
        --format=s16le \
        --rate=48000 \
        --channels=1 \
        "$AUDIO_FILE" &
    
    local recording_pid=$!
    echo "$recording_pid" > "$PID_FILE"
    
    log "Recording started with PID: $recording_pid"
}

# Stop recording and transcribe
stop_recording() {
    if [ ! -f "$PID_FILE" ]; then
        warning "No recording in progress"
        return 1
    fi
    
    local pid
    pid=$(cat "$PID_FILE")
    
    if ! kill -0 "$pid" 2>/dev/null; then
        warning "Recording process not found, cleaning up"
        rm -f "$PID_FILE"
        return 1
    fi
    
    log "Stopping recording (PID: $pid)..."
    update_status "processing" "Finalizing recording..."
    notify "🛑 Stopping recording, please wait..."
    
    # Add a delay to capture final words (increased for better capture)
    sleep 2
    
    # Stop the recording process
    kill -TERM "$pid"
    
    # Wait for the process to finish writing the file
    local timeout=5
    while kill -0 "$pid" 2>/dev/null && [ $timeout -gt 0 ]; do
        sleep 0.1
        timeout=$((timeout - 1))
    done
    
    if kill -0 "$pid" 2>/dev/null; then
        warning "Recording process didn't stop gracefully, killing..."
        kill -KILL "$pid" 2>/dev/null
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    # Give parecord a moment to finalize the file
    sleep 0.2
    
    # Check if audio file exists and has content
    if [ ! -f "$AUDIO_FILE" ]; then
        error "No audio file created"
        update_status "error" "Recording failed - no file created"
        notify "❌ Recording failed"
        return 1
    fi
    
    local file_size
    file_size=$(stat -f%z "$AUDIO_FILE" 2>/dev/null || stat -c%s "$AUDIO_FILE" 2>/dev/null || echo 0)
    
    if [ "$file_size" -lt 1000 ]; then
        error "Audio file too small ($file_size bytes)"
        update_status "error" "Recording failed - file too small"
        notify "❌ Recording too short"
        rm -f "$AUDIO_FILE"
        return 1
    fi
    
    log "Audio file created: $AUDIO_FILE ($file_size bytes)"
    
    # Transcribe the file
    log "Starting transcription..."
    if run_transcriber "$AUDIO_FILE"; then
        success "Transcription completed successfully"
        update_status "idle" "Ready for recording"
        notify "✅ Text copied to clipboard"
    else
        error "Transcription failed"
        update_status "error" "Transcription failed"
        notify "❌ Transcription failed"
    fi
    
    # Clean up audio file
    rm -f "$AUDIO_FILE"
}

# Check if recording is active
is_recording() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

# Toggle recording (start if not running, stop if running)
toggle_recording() {
    if is_recording; then
        stop_recording
    else
        start_recording
    fi
}

# Initialize status file if it doesn't exist
if [ ! -f "$STATUS_FILE" ]; then
    update_status "idle" "Ready for recording"
fi

# Main function
main() {
    case "${1:-toggle}" in
        "start")
            start_recording
            ;;
        "stop")
            stop_recording
            ;;
        "toggle")
            toggle_recording
            ;;
        "status")
            if is_recording; then
                echo "Recording in progress"
                exit 0
            else
                echo "Not recording"
                exit 1
            fi
            ;;
        "transcribe")
            if [ -z "$2" ]; then
                error "Audio file path required for transcribe command"
                exit 1
            fi
            log "Transcribing file: $2"
            run_transcriber "$2"
            ;;
        *)
            echo "Usage: $0 {start|stop|toggle|status|transcribe <file>}"
            echo ""
            echo "Commands:"
            echo "  start      Start recording"
            echo "  stop       Stop recording and transcribe"
            echo "  toggle     Toggle recording (default)"
            echo "  status     Check if recording"
            echo "  transcribe Transcribe an audio file"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"