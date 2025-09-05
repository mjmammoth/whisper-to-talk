#!/usr/bin/env python3
"""
Waybar status module for Whisper-to-Talk
Shows different states: idle, recording, processing
Updated for standalone whisper-to-talk system
"""

import json
import os
import time
import subprocess
import sys
from pathlib import Path

class TranscriberStatus:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.server_pid_file = Path("/tmp/whisper_server.pid")
        self.status_file = Path("/tmp/whisper_status.json")
        self.recording_file = Path("/tmp/whisper_recording")
        
        # Status states and their icons
        self.states = {
            "idle": {
                "text": "🎤",
                "tooltip": "Whisper: Ready to record (F9 or mouse button)",
                "class": "idle",
                "alt": "idle"
            },
            "recording": {
                "text": "🔴",
                "tooltip": "Whisper: Recording... (Press F9 to stop)",
                "class": "recording",
                "alt": "recording"
            },
            "processing": {
                "text": "⚡",
                "tooltip": "Whisper: Processing audio...",
                "class": "processing", 
                "alt": "processing"
            },
            "offline": {
                "text": "🎤",
                "tooltip": "Whisper: Server not running",
                "class": "offline",
                "alt": "offline"
            },
            "error": {
                "text": "❌",
                "tooltip": "Whisper: Error occurred",
                "class": "error",
                "alt": "error"
            }
        }
    
    def is_server_running(self):
        """Check if the transcription server is running"""
        if not self.server_pid_file.exists():
            return False
        
        try:
            pid = int(self.server_pid_file.read_text().strip())
            # Check if process is actually running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, ProcessLookupError):
            return False
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording_file.exists()
    
    def get_current_status(self):
        """Get the current transcription status"""
        # Check if server is running first
        if not self.is_server_running():
            return "offline"
        
        # Check if currently recording
        if self.is_recording():
            return "recording"
        
        # Check if there's a status file with current state
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    status_data = json.load(f)
                    state = status_data.get('state', 'idle')
                    
                    # Check if status is stale (older than 5 seconds)
                    last_update = status_data.get('timestamp', 0)
                    if time.time() - last_update > 5:
                        return "idle"
                    
                    return state
            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                pass
        
        # Default to idle if server is running
        return "idle"
    
    def get_waybar_output(self):
        """Generate Waybar JSON output"""
        status = self.get_current_status()
        state_info = self.states[status]
        
        output = {
            "text": state_info["text"],
            "tooltip": state_info["tooltip"],
            "class": state_info["class"],
            "alt": state_info["alt"]
        }
        
        return json.dumps(output)
    
    def handle_click(self, button):
        """Handle Waybar click events"""
        if button == "1":  # Left click - toggle recording
            self.toggle_recording()
        elif button == "3":  # Right click - toggle server
            self.toggle_server()
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        script_path = self.script_dir / "hyprland_transcribe_simple.sh"
        if script_path.exists():
            subprocess.run([str(script_path), "toggle"], capture_output=True)
    
    def toggle_server(self):
        """Toggle the transcription server on/off"""
        script_path = self.script_dir / "start_transcription_server.sh"
        
        if self.is_server_running():
            subprocess.run([str(script_path), "stop"], capture_output=True)
        else:
            subprocess.run([str(script_path), "start"], capture_output=True)

def main():
    transcriber = TranscriberStatus()
    
    # Handle click events if provided as arguments
    if len(sys.argv) > 1:
        button = sys.argv[1]
        transcriber.handle_click(button)
        return
    
    # Output current status for Waybar
    print(transcriber.get_waybar_output())

if __name__ == "__main__":
    main()