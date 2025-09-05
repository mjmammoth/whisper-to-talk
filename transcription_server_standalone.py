#!/usr/bin/env python3
"""
Standalone Whisper Transcription Server
Completely independent of Whisper-WebUI - handles model downloading and management
"""

import os
import sys
import json
import time
import socket
import threading
import subprocess
import yaml
import logging
import re
from pathlib import Path

# Direct imports - no Whisper-WebUI dependencies
import faster_whisper
import torch

# Configuration
SOCKET_PATH = '/tmp/whisper_transcription.sock'
PID_FILE = '/tmp/whisper_server.pid'
CONFIG_FILE = 'config.yaml'
DEFAULT_MODEL = 'large-v3-turbo'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('/tmp/whisper_server.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class StandaloneTranscriptionServer:
    def __init__(self):
        self.model = None
        self.socket = None
        self.running = False
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from config.yaml"""
        script_dir = Path(__file__).parent
        config_path = script_dir / CONFIG_FILE
        
        # Default configuration
        default_config = {
            'whisper': {
                'model_size': DEFAULT_MODEL,
                'compute_type': 'float32',
                'enable_offload': True
            },
            'system': {
                'temp_dir': '/tmp',
                'socket_path': SOCKET_PATH,
                'pid_file': PID_FILE,
                'server_log': '/tmp/whisper_server.log'
            }
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                    return config
            except Exception as e:
                logger.warning(f"Error loading config: {e}, using defaults")
        
        return default_config
    
    def initialize_model(self):
        """Initialize Whisper model with automatic downloading"""
        model_size = self.config['whisper']['model_size']
        compute_type = self.config['whisper']['compute_type']
        
        logger.info(f"Initializing Whisper model: {model_size}")
        logger.info(f"Compute type: {compute_type}")
        
        # Check if CUDA is available for GPU acceleration
        if torch.cuda.is_available() and compute_type == 'float16':
            device = "cuda"
            logger.info("Using CUDA acceleration")
        else:
            device = "cpu"
            logger.info("Using CPU")
        
        try:
            logger.info("Downloading/loading model... (this may take a few minutes on first run)")
            
            # Create the model - this will auto-download if not cached
            self.model = faster_whisper.WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=None,  # Use default cache location
            )
            
            # Test the model with a small dummy transcription to warm it up
            logger.info("Warming up model...")
            import numpy as np
            dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
            list(self.model.transcribe(dummy_audio, beam_size=1))
            
            logger.info(f"Whisper model '{model_size}' initialized and ready")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {e}")
            return False
    
    def clean_transcription_text(self, text):
        """Clean up transcription text to remove hallucinations"""
        if not text or not text.strip():
            return ""
        
        # Remove excessive repetition patterns
        text = re.sub(r'(\d+,\s*){10,}', '', text)
        
        # Remove excessive repetition of short phrases
        words = text.split()
        if len(words) > 20:
            for phrase_len in range(3, 8):
                for i in range(len(words) - phrase_len * 3):
                    phrase = ' '.join(words[i:i+phrase_len])
                    if phrase and len(phrase.strip()) > 10:
                        repetitions = 1
                        pos = i + phrase_len
                        while pos + phrase_len <= len(words):
                            next_phrase = ' '.join(words[pos:pos+phrase_len])
                            if phrase.lower() == next_phrase.lower():
                                repetitions += 1
                                pos += phrase_len
                            else:
                                break
                        
                        if repetitions > 3:
                            end_pos = i + phrase_len + (repetitions - 1) * phrase_len
                            words = words[:i+phrase_len] + words[end_pos:]
                            break
        
        text = ' '.join(words)
        
        # Limit length
        max_length = 1000
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + "..."
            logger.warning(f"Transcription truncated to {len(text)} characters")
        
        return text.strip()
    
    def transcribe_file(self, audio_file):
        """Transcribe audio file using the loaded model"""
        if not os.path.exists(audio_file):
            return {"error": f"Audio file not found: {audio_file}"}
        
        file_size = os.path.getsize(audio_file)
        if file_size < 1000:
            logger.warning(f"Audio file is very small ({file_size} bytes)")
            return {"text": "", "duration": 0}
        
        logger.info(f"Transcribing: {audio_file} ({file_size} bytes)")
        start_time = time.time()
        
        try:
            # Transcribe with the model - optimized for speed
            segments, info = self.model.transcribe(
                audio_file,
                beam_size=1,  # Fastest beam search
                best_of=1,    # Single candidate
                temperature=0,  # Deterministic output
                condition_on_previous_text=False,  # Don't use context
                initial_prompt=None,  # No initial prompt
                word_timestamps=False,  # Disable word-level timestamps
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500)  # Reduce silence sensitivity
            )
            
            # Extract text from segments
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text.strip())
            
            text = " ".join(text_segments)
            text = self.clean_transcription_text(text)
            
            total_time = time.time() - start_time
            logger.info(f"Transcribed in {total_time:.2f}s: '{text[:50]}...' ({len(text)} chars)")
            
            return {"text": text, "duration": total_time}
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {"error": str(e)}
    
    def handle_client(self, conn):
        """Handle client transcription request"""
        try:
            data = conn.recv(1024).decode('utf-8')
            request = json.loads(data)
            
            if request.get("action") == "transcribe":
                audio_file = request.get("file")
                result = self.transcribe_file(audio_file)
                response = json.dumps(result)
            elif request.get("action") == "ping":
                response = json.dumps({"status": "ready"})
            elif request.get("action") == "info":
                model_info = {
                    "model": self.config['whisper']['model_size'],
                    "device": "cuda" if torch.cuda.is_available() else "cpu",
                    "compute_type": self.config['whisper']['compute_type']
                }
                response = json.dumps(model_info)
            else:
                response = json.dumps({"error": "Unknown action"})
            
            conn.sendall(response.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            error_response = json.dumps({"error": str(e)})
            conn.sendall(error_response.encode('utf-8'))
        finally:
            conn.close()
    
    def start_server(self):
        """Start the Unix socket server"""
        # Remove existing socket file
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass
        
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(SOCKET_PATH)
        self.socket.listen(5)
        
        # Write PID file
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        logger.info(f"Transcription server started, listening on {SOCKET_PATH}")
        self.running = True
        
        while self.running:
            try:
                conn, addr = self.socket.accept()
                # Handle each request in a separate thread
                thread = threading.Thread(target=self.handle_client, args=(conn,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    logger.error(f"Server error: {e}")
    
    def stop_server(self):
        """Stop the server"""
        logger.info("Stopping transcription server...")
        self.running = False
        if self.socket:
            self.socket.close()
        try:
            os.unlink(SOCKET_PATH)
            os.unlink(PID_FILE)
        except FileNotFoundError:
            pass

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        # Stop existing server
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 15)  # SIGTERM
                print(f"Stopped server (PID {pid})")
            except ProcessLookupError:
                print("Server not running")
                os.unlink(PID_FILE)
        else:
            print("Server not running")
        return
    
    # Check if server is already running
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)  # Check if process exists
            print(f"Server already running (PID {pid})")
            return
        except ProcessLookupError:
            # PID file exists but process doesn't
            os.unlink(PID_FILE)
    
    server = StandaloneTranscriptionServer()
    
    if not server.initialize_model():
        logger.error("Failed to initialize model, exiting")
        sys.exit(1)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        server.stop_server()

if __name__ == "__main__":
    main()