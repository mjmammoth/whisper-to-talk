# Model Management Guide

## Overview

Whisper-to-Talk supports multiple Whisper models with different trade-offs between speed and accuracy. The system automatically downloads models on first use and caches them locally.

## Available Models

| Model | Size | Speed | Accuracy | VRAM | Use Case |
|-------|------|--------|----------|------|----------|
| `tiny` | ~39 MB | Fastest | Basic | ~1GB | Quick notes, testing |
| `base` | ~74 MB | Fast | Good | ~1GB | General use, fast hardware |
| `small` | ~244 MB | Medium | Better | ~2GB | Balanced performance |
| `medium` | ~769 MB | Slower | Great | ~5GB | High accuracy needs |
| `large-v1` | ~1550 MB | Slow | Excellent | ~10GB | Maximum accuracy |
| `large-v2` | ~1550 MB | Slow | Excellent | ~10GB | Improved large model |
| `large-v3` | ~1550 MB | Slow | Best | ~10GB | Latest, most accurate |
| `large-v3-turbo` | ~809 MB | Fast | Best | ~6GB | **Recommended** - Best balance |

## Changing Models

### Method 1: Configuration File (Recommended)

Edit `config.yaml`:
```yaml
whisper:
  model_size: large-v3-turbo  # Change this line
  compute_type: float32       # float16 for GPU, float32 for CPU
  enable_offload: true
```

**Available model_size values:**
- `tiny`, `base`, `small`, `medium`
- `large-v1`, `large-v2`, `large-v3`
- `large-v3-turbo` (recommended)

After changing the config:
```bash
# Restart the server to load the new model
./start_transcription_server.sh restart
```

### Method 2: Environment Variable

Set model temporarily:
```bash
export WHISPER_MODEL_SIZE=small
./start_transcription_server.sh restart
```

### Method 3: Command Line Parameter

Start server with specific model:
```bash
./start_transcription_server.sh start --model small
```

## Model Download and Storage

### Automatic Download
Models are automatically downloaded on first use:
1. Server starts and checks for model
2. If model not found, downloads from Hugging Face
3. Model is cached locally for future use
4. Subsequent starts use cached model (fast startup)

### Manual Download
Pre-download models to avoid first-use delay:
```bash
# Download a specific model
python3 -c "
import faster_whisper
model = faster_whisper.WhisperModel('large-v3-turbo')
print('Model downloaded successfully')
"
```

### Model Storage Location
Models are stored in:
- **Linux**: `~/.cache/huggingface/hub/`
- **Custom location**: Set `HF_HOME` environment variable

Example:
```bash
export HF_HOME=/path/to/your/model/cache
./start_transcription_server.sh start
```

### Storage Requirements
Ensure sufficient disk space for models:
- **tiny**: ~50 MB
- **base**: ~100 MB  
- **small**: ~300 MB
- **medium**: ~800 MB
- **large models**: ~1.6 GB each
- **large-v3-turbo**: ~850 MB

## Performance Optimization

### GPU Acceleration
For NVIDIA GPUs, use float16:
```yaml
whisper:
  model_size: large-v3-turbo
  compute_type: float16  # Faster on GPU
  enable_offload: true
```

Ensure CUDA is available:
```bash
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### CPU Optimization
For CPU-only systems:
```yaml
whisper:
  model_size: base        # Smaller model for CPU
  compute_type: float32   # Required for CPU
  enable_offload: true
```

### Memory Management
Enable model offloading to save VRAM:
```yaml
whisper:
  enable_offload: true    # Unloads model after use
```

## Model Selection Guide

### For Different Use Cases

**🚀 Speed Priority (Real-time notes)**
```yaml
model_size: base
compute_type: float32
```

**⚖️ Balanced (Recommended)**
```yaml
model_size: large-v3-turbo
compute_type: float32
```

**🎯 Accuracy Priority (Professional transcription)**
```yaml
model_size: large-v3
compute_type: float16  # if GPU available
```

**💻 Low-resource Systems**
```yaml
model_size: tiny
compute_type: float32
enable_offload: true
```

**🖥️ High-end Systems**
```yaml
model_size: large-v3
compute_type: float16
enable_offload: false
```

## Testing Different Models

Quick model comparison:
```bash
# Test with base model
echo "model_size: base" > test_config.yaml
./start_transcription_server.sh start --config test_config.yaml
# Record some audio and note accuracy/speed

# Test with large-v3-turbo
echo "model_size: large-v3-turbo" > test_config.yaml  
./start_transcription_server.sh restart --config test_config.yaml
# Record same audio and compare
```

## Troubleshooting Model Issues

### Model Download Failures
```bash
# Check internet connection and Hugging Face access
curl -I https://huggingface.co/

# Clear model cache and re-download
rm -rf ~/.cache/huggingface/hub/models--*whisper*
./start_transcription_server.sh restart
```

### Out of Memory Errors
```bash
# Try smaller model
echo "model_size: small" >> config.yaml
./start_transcription_server.sh restart

# Or enable offloading
echo "enable_offload: true" >> config.yaml
```

### Model Loading Errors
Check logs for specific errors:
```bash
tail -f /tmp/whisper_server.log
```

Common solutions:
- Ensure sufficient disk space
- Check Python dependencies: `pip install -r requirements.txt`
- Verify model name spelling in config.yaml

### Performance Issues
Monitor resource usage:
```bash
# Check CPU/memory usage
htop

# Check GPU usage (if available)
nvidia-smi

# Check model loading time in logs
grep "initialized" /tmp/whisper_server.log
```

## Advanced Configuration

### Custom Model Paths
```yaml
whisper:
  model_path: "/path/to/custom/model"  # Use local model file
  model_size: custom
```

### Multiple Models
Run different models for different use cases:
```bash
# Start lightweight model for quick notes
WHISPER_MODEL_SIZE=base ./start_transcription_server.sh start --port 8001

# Start high-accuracy model for important transcriptions  
WHISPER_MODEL_SIZE=large-v3 ./start_transcription_server.sh start --port 8002
```

### Model Warm-up
Pre-load model at startup to eliminate first-transcription delay:
```yaml
whisper:
  enable_warmup: true     # Runs dummy transcription at startup
  warmup_duration: 5      # Seconds of silence to transcribe for warmup
```

## Model Update Process

When new Whisper models are released:
1. Update `requirements.txt` if needed
2. Add new model to config options
3. Test with your typical audio
4. Update documentation
5. Commit changes

Example of adding a new model:
```yaml
# In config.yaml, add to available models:
whisper:
  model_size: large-v4-turbo  # New model
```

---

## Quick Reference

**Change model:** Edit `config.yaml` → `model_size: <model_name>` → Restart server  
**Download model:** Automatic on first use, or manual with Python script  
**Check storage:** Models stored in `~/.cache/huggingface/hub/`  
**Optimize GPU:** Use `compute_type: float16`  
**Save memory:** Enable `enable_offload: true`  
**Troubleshoot:** Check `/tmp/whisper_server.log`

**Recommended settings:**
- **General use**: `large-v3-turbo` + `float32`
- **GPU available**: `large-v3-turbo` + `float16`  
- **Low resources**: `base` + `float32` + offload
- **Max accuracy**: `large-v3` + `float16`