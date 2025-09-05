#!/bin/bash
# Start the background transcription server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"

cd "$SCRIPT_DIR"

# Function to run with virtual environment
run_with_venv() {
    if [ -d "$VENV_PATH" ] && [ -x "$VENV_PATH/bin/python" ]; then
        PYTHONPATH="$SCRIPT_DIR" "$VENV_PATH/bin/python" "$@"
    else
        echo "Warning: Virtual environment not found, using system python"
        PYTHONPATH="$SCRIPT_DIR" python3 "$@"
    fi
}

case "${1:-start}" in
    "start")
        echo "Starting Whisper transcription server..."
        run_with_venv transcription_server_standalone.py
        ;;
    "stop")
        echo "Stopping Whisper transcription server..."
        run_with_venv transcription_server_standalone.py stop
        ;;
    "restart")
        echo "Restarting Whisper transcription server..."
        run_with_venv transcription_server_standalone.py stop
        sleep 2
        run_with_venv transcription_server_standalone.py
        ;;
    "status")
        if [ -f "/tmp/whisper_server.pid" ]; then
            PID=$(cat /tmp/whisper_server.pid)
            if kill -0 $PID 2>/dev/null; then
                echo "Server running (PID $PID)"
                exit 0
            else
                echo "Server not running (stale PID file)"
                exit 1
            fi
        else
            echo "Server not running"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac