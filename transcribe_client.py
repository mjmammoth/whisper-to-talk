#!/usr/bin/env python3
"""
Fast transcription client - communicates with background server
"""

import os
import sys
import json
import socket
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Also log to the whisper transcription log
file_handler = logging.FileHandler('/tmp/whisper_transcription.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

SOCKET_PATH = '/tmp/whisper_transcription.sock'

def copy_to_clipboard(text):
    """Copy text to clipboard using wl-copy"""
    if not text.strip():
        logger.warning("No text to copy")
        return False
    
    try:
        subprocess.run(
            ["wl-copy", text],
            check=True,
            input=text.encode(),
        )
        logger.info("Text copied to clipboard")
        return True
    except Exception as e:
        logger.error(f"Failed to copy to clipboard: {e}")
        return False

def transcribe_with_server(audio_file):
    """Send transcription request to background server"""
    try:
        # Connect to server
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        
        # Send request
        request = {
            "action": "transcribe",
            "file": audio_file
        }
        sock.sendall(json.dumps(request).encode('utf-8'))
        
        # Receive response
        response_data = sock.recv(4096).decode('utf-8')
        response = json.loads(response_data)
        
        sock.close()
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to communicate with server: {e}")
        return {"error": str(e)}

def main():
    if len(sys.argv) != 2:
        print("Usage: python transcribe_client.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        logger.error(f"Audio file not found: {audio_file}")
        sys.exit(1)
    
    # Check file size
    file_size = os.path.getsize(audio_file)
    if file_size < 1000:
        logger.warning(f"Audio file is very small ({file_size} bytes), likely empty")
        print("(no speech detected)")
        sys.exit(0)
    
    logger.info(f"Requesting transcription of: {audio_file} ({file_size} bytes)")
    
    # Send to server for transcription
    result = transcribe_with_server(audio_file)
    
    if "error" in result:
        logger.error(f"Transcription failed: {result['error']}")
        sys.exit(1)
    
    text = result.get("text", "")
    duration = result.get("duration", 0)
    
    if text.strip():
        copy_to_clipboard(text)
        print(text)
        logger.info(f"Transcription completed in {duration:.2f}s: '{text[:50]}...' ({len(text)} chars)")
    else:
        print("(no speech detected)")
        logger.info("Transcription completed but no speech detected")

if __name__ == "__main__":
    main()