#!/usr/bin/env python3
"""
Background Whisper Transcription Server
Keeps the model loaded in memory for fast transcriptions
"""

import os
import sys
import json
import time
import socket
import threading
import subprocess
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.whisper.whisper_factory import WhisperFactory
from modules.whisper.data_classes import WhisperParams
from modules.utils.paths import FASTER_WHISPER_MODELS_DIR, OUTPUT_DIR
from modules.utils.logger import get_logger
import logging

# Set up logging
logger = get_logger()
file_handler = logging.FileHandler('/tmp/whisper_server.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

SOCKET_PATH = '/tmp/whisper_transcription.sock'
PID_FILE = '/tmp/whisper_server.pid'

class TranscriptionServer:
    def __init__(self):
        self.whisper_inf = None
        self.socket = None
        self.running = False
        
    def initialize_model(self):
        """Initialize Whisper model once at startup"""
        logger.info("Initializing Whisper model (using backend config)")
        try:
            self.whisper_inf = WhisperFactory.create_whisper_inference(
                whisper_type="faster-whisper",
                faster_whisper_model_dir=FASTER_WHISPER_MODELS_DIR,
                output_dir=OUTPUT_DIR,
            )
            logger.info("Whisper model initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {e}")
            return False
    
    def clean_transcription_text(self, text):
        """Clean up transcription text"""
        if not text or not text.strip():
            return ""
        
        import re
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
        """Transcribe audio file using pre-loaded model"""
        if not os.path.exists(audio_file):
            return {"error": f"Audio file not found: {audio_file}"}
        
        file_size = os.path.getsize(audio_file)
        if file_size < 1000:
            logger.warning(f"Audio file is very small ({file_size} bytes)")
            return {"text": "", "duration": 0}
        
        logger.info(f"Transcribing: {audio_file} ({file_size} bytes)")
        start_time = time.time()
        
        try:
            # Use the same method as before but let the model load the correct size internally
            result = self.whisper_inf.transcribe(audio_file)
            
            if isinstance(result, tuple) and len(result) >= 2:
                segments, elapsed_time = result[0], result[1]
                if segments:
                    text = " ".join([segment.text.strip() for segment in segments])
                    text = self.clean_transcription_text(text)
                else:
                    text = ""
            else:
                logger.error(f"Unexpected result format: {type(result)}")
                text = ""
            
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
                # Handle each request in a separate thread for responsiveness
                thread = threading.Thread(target=self.handle_client, args=(conn,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
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
    
    server = TranscriptionServer()
    
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