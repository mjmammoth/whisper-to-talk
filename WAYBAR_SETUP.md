# Waybar Integration for Whisper-to-Talk

This document explains how to integrate the Whisper-to-Talk transcription system with your Waybar status bar for visual feedback and quick access.

## Features

- **Visual Status Indicator**: Shows current transcription state (idle, recording, processing, offline, error)
- **Continuous Styling**: Blends seamlessly with your existing Waybar without creating separate sections
- **Interactive Controls**: 
  - Left-click: Toggle recording (same as F9 key)
  - Right-click: Toggle transcription server on/off
- **Real-time Updates**: Status updates every 2 seconds
- **Hover Tooltips**: Detailed status information on hover

## Status States

| State | Icon | Description | Color |
|-------|------|-------------|-------|
| **Idle** | 🎤 | Ready to record | Normal (inherits from theme) |
| **Recording** | 🔴 | Currently recording audio | Red with pulse animation |
| **Processing** | ⚡ | Transcribing recorded audio | Orange with scale animation |
| **Offline** | 🎤 | Server not running | Dimmed (30% opacity) |
| **Error** | ❌ | Error occurred | Red with flash animation |

## Installation

### 1. Add Module to Waybar Config

Edit your Waybar configuration file (usually `~/.config/waybar/config`) and add the whisper-transcriber module to your modules list:

```json
{
    "modules-left": ["hyprland/workspaces", "hyprland/window"],
    "modules-center": ["clock"],
    "modules-right": ["whisper-transcriber", "pulseaudio", "network", "battery"],
    
    "whisper-transcriber": {
        "exec": "/home/markm/whisper-to-talk/waybar_status.py",
        "return-type": "json",
        "interval": 2,
        "signal": 8,
        "on-click": "/home/markm/whisper-to-talk/waybar_status.py 1",
        "on-click-right": "/home/markm/whisper-to-talk/waybar_status.py 3",
        "tooltip": true,
        "format": "{icon}",
        "format-icons": {
            "idle": "🎤",
            "recording": "🔴", 
            "processing": "⚡",
            "offline": "🎤",
            "error": "❌"
        }
    }
}
```

### 2. Add Styling (Optional)

If you want custom styling, add the whisper-transcriber styles to your Waybar CSS file (usually `~/.config/waybar/style.css`):

```css
/* Import the whisper-to-talk styles */
@import url('/home/markm/whisper-to-talk/waybar_style.css');
```

Or copy the contents of `waybar_style.css` directly into your existing style file.

### 3. Make Script Executable

```bash
chmod +x /home/markm/whisper-to-talk/waybar_status.py
```

### 4. Restart Waybar

```bash
killall waybar && waybar &
```

## Configuration Options

### Update Interval
Change the `"interval"` value to update more or less frequently:
- `1`: Update every second (more responsive, higher CPU usage)
- `5`: Update every 5 seconds (less responsive, lower CPU usage)

### Custom Icons
Modify the `"format-icons"` section to use different icons:
```json
"format-icons": {
    "idle": "🎙️",
    "recording": "⏺️", 
    "processing": "🔄",
    "offline": "⏸️",
    "error": "⚠️"
}
```

### Positioning
Move the module to different positions by changing which modules list it appears in:
- `"modules-left"`: Left side of the bar
- `"modules-center"`: Center of the bar  
- `"modules-right"`: Right side of the bar

## Troubleshooting

### Module Not Appearing
1. Check that the script is executable: `ls -la /home/markm/whisper-to-talk/waybar_status.py`
2. Test the script manually: `/home/markm/whisper-to-talk/waybar_status.py`
3. Check Waybar logs: `journalctl --user -f -u waybar`

### Wrong Status Shown
1. Verify transcription server is running: `/home/markm/whisper-to-talk/start_transcription_server.sh status`
2. Check for stale status files: `ls -la /tmp/whisper_*`
3. Restart Waybar: `killall waybar && waybar &`

### Styling Issues
1. Make sure CSS is properly imported or copied
2. Check for CSS syntax errors in your style file
3. Try without custom styling first to isolate the issue

## Integration Notes

- The module automatically detects if the transcription server is running
- Recording state is determined by checking for `/tmp/whisper_recording` file
- Status updates are lightweight and won't impact system performance
- Click handlers work independently of keyboard shortcuts (F9/mouse buttons)

## Advanced Usage

### Manual Status Updates
You can trigger manual updates by sending signal 8 to Waybar:
```bash
pkill -SIGUSR1 waybar
```

### Custom Click Actions
Modify the click handlers in `waybar_status.py` to perform different actions:
- Add middle-click support
- Open logs in a terminal
- Show transcription history
- Configure different toggle behaviors