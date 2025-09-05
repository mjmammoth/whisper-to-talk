# Whisper-to-Talk

A high-performance, real-time push-to-talk transcription system built on Whisper. Press a key, speak, press again - your speech is instantly transcribed to your clipboard.

## Features

🚀 **Lightning Fast**: Sub-second transcription with pre-loaded Whisper large-v3-turbo model  
🎯 **Push-to-Talk**: Simple F9 key interface - start recording, speak, stop recording  
📋 **Clipboard Ready**: Transcribed text automatically copied for immediate pasting  
🔒 **Privacy First**: Complete offline operation, no cloud services  
🎛️ **Production Ready**: Background service with robust error handling  
🖥️ **Desktop Optimized**: Built for Linux/Hyprland with Wayland support  

## Quick Start

### Prerequisites
- Linux with Hyprland window manager
- PipeWire/PulseAudio with `parecord`
- `wl-copy` (Wayland clipboard)
- Python 3.11+ with faster-whisper

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd whisper-to-talk

# Install Python dependencies (see requirements.txt)
pip install -r requirements.txt

# Download Whisper model (first run will auto-download)
# Model will be cached for future use

# Set up Hyprland key binding
echo 'bind = , F9, exec, /path/to/whisper-to-talk/hyprland_transcribe_simple.sh toggle' >> ~/.config/hypr/keybindings.conf

# Start the background transcription server
./start_transcription_server.sh start

# Test the system
# Press F9, speak "Hello world", press F9 again
# Text should appear in your clipboard
```

### Basic Usage
1. **Press F9** → Recording starts (microphone active)
2. **Speak your message** → Audio is captured
3. **Press F9 again** → Recording stops, transcription begins
4. **Text appears in clipboard** → Ready to paste anywhere

## Performance

- **First Use**: ~3-5 seconds (model loading)
- **Subsequent Uses**: ~1.2 seconds average
- **Accuracy**: State-of-the-art with Whisper large-v3-turbo
- **Memory Usage**: ~2GB (model loaded in background)

## Architecture

See [PUSH_TO_TALK_ARCHITECTURE.md](PUSH_TO_TALK_ARCHITECTURE.md) for detailed technical documentation.

## Configuration

### Model Selection
Edit `config.yaml`:
```yaml
whisper:
  model_size: large-v3-turbo  # Options: base, small, medium, large-v3-turbo
  compute_type: float32       # float16 for GPU, float32 for CPU
```

### Audio Device
Script auto-detects USB headsets. For manual configuration, edit the device parameter in `hyprland_transcribe_simple.sh`.

### Key Binding
Change F9 to any key by editing your Hyprland config:
```
bind = , <YOUR_KEY>, exec, /path/to/whisper-to-talk/hyprland_transcribe_simple.sh toggle
```

## Service Management

```bash
./start_transcription_server.sh start    # Start background server
./start_transcription_server.sh stop     # Stop server
./start_transcription_server.sh status   # Check status
./start_transcription_server.sh restart  # Restart server

# Auto-start on boot
./install-service.sh
```

## Monitoring

- **Server Logs**: `/tmp/whisper_server.log`
- **Transcription Logs**: `/tmp/whisper_transcription.log`
- **Status**: `/tmp/whisper_status.json`

## Troubleshooting

### No Audio Captured
Check your audio device:
```bash
pactl list sources | grep -i input
```

### Server Not Responding
Check server logs:
```bash
tail -f /tmp/whisper_server.log
```

### Poor Transcription Quality
- Verify large-v3-turbo model is loaded
- Check microphone positioning and background noise
- Ensure clear speech with appropriate pauses

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your preferred license]

## Acknowledgments

Built on the excellent [Whisper-WebUI](https://github.com/jhj0517/Whisper-WebUI) project and OpenAI's Whisper models.

---

**Need Help?** Check the [Architecture Documentation](PUSH_TO_TALK_ARCHITECTURE.md) or open an issue.