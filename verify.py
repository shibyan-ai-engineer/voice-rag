#!/usr/bin/env python
"""
Verification script to check that all components of the Voice RAG system are working correctly.
"""
import os
import sys
import torch
import logging
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verification")


def check_directories():
    """Check if required directories exist."""
    logger.info("Checking directories...")
    
    required_dirs = [
        "app",
        "app/api",
        "app/api/v1",
        "app/core",
        "app/services",
        "data",
        "data/temp_audio",
        "data/uploads",
        "faiss_index",
        "static",
        "static/css",
        "static/js",
        "static/gifs",
        "logs"
    ]
    
    for directory in required_dirs:
        if not os.path.isdir(directory):
            logger.error(f"Missing directory: {directory}")
            return False
    
    logger.info("All required directories are present.")
    return True


def check_files():
    """Check if critical files exist."""
    logger.info("Checking files...")
    
    required_files = [
        "app/main.py",
        "app/models_init.py",
        "app/utils.py",
        "app/api/v1/endpoints.py",
        "app/api/v1/schemas.py",
        "app/core/config.py",
        "app/core/logging_config.py",
        "app/services/audio_service.py",
        "app/services/document_service.py",
        "app/services/rag_llm_service.py",
        "static/index.html",
        "static/css/style.css",
        "static/js/script.js",
        "run.py"
    ]
    
    for filepath in required_files:
        if not os.path.isfile(filepath):
            logger.error(f"Missing file: {filepath}")
            return False
    
    logger.info("All critical files are present.")
    return True


def check_hardware():
    """Check hardware configuration."""
    logger.info("Checking hardware configuration...")
    
    # Check CUDA
    if torch.cuda.is_available():
        device = "CUDA"
        logger.info(f"CUDA is available. Device count: {torch.cuda.device_count()}")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "MPS"
        logger.info("Apple Silicon MPS is available")
    else:
        device = "CPU"
        logger.warning("No GPU acceleration found, using CPU")
    
    logger.info(f"Using device: {device}")
    return True


def check_audio_devices():
    """Check audio devices."""
    logger.info("Checking audio devices...")
    
    try:
        devices = sd.query_devices()
        logger.info(f"Found {len(devices)} audio devices")
        
        input_devices = []
        output_devices = []
        
        for i, device in enumerate(devices):
            device_info = {}
            try:
                # Try accessing the device info in various ways
                if isinstance(device, dict):
                    device_info = device
                elif hasattr(device, 'to_dict'):
                    device_info = device.to_dict()
                
                if device_info:
                    max_in = device_info.get('max_input_channels', 0)
                    max_out = device_info.get('max_output_channels', 0)
                    name = device_info.get('name', f'Device {i}')
                    
                    if max_in > 0:
                        input_devices.append((i, name, max_in))
                    if max_out > 0:
                        output_devices.append((i, name, max_out))
            except Exception as e:
                logger.warning(f"Error accessing device {i} info: {e}")
        
        logger.info(f"Input devices: {len(input_devices)}")
        for idx, name, channels in input_devices:
            logger.info(f"  [{idx}] {name} ({channels} channels)")
        
        logger.info(f"Output devices: {len(output_devices)}")
        for idx, name, channels in output_devices:
            logger.info(f"  [{idx}] {name} ({channels} channels)")
        
        default_in = sd.default.device[0]
        default_out = sd.default.device[1]
        logger.info(f"Default input device: {default_in}")
        logger.info(f"Default output device: {default_out}")
        
        return len(input_devices) > 0
    except Exception as e:
        logger.error(f"Error checking audio devices: {e}")
        return False


def test_audio_recording():
    """Test audio recording functionality."""
    logger.info("Testing audio recording...")
    
    try:
        duration = 1  # Record for 1 second
        sample_rate = 16000
        
        logger.info(f"Recording {duration} second of audio at {sample_rate}Hz")
        
        # Record audio
        audio = sd.rec(
            int(duration * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            dtype='float32'
        )
        sd.wait()
        
        # Check if audio was recorded
        if audio is None or len(audio) == 0:
            logger.error("No audio was recorded")
            return False
        
        # Save test audio
        test_file = os.path.join("data", "temp_audio", "test_recording.wav")
        write(test_file, sample_rate, (audio * 32767).astype(np.int16))
        
        # Check file
        if os.path.exists(test_file) and os.path.getsize(test_file) > 0:
            logger.info(f"Audio recording test passed, file saved to {test_file}")
            return True
        else:
            logger.error("Failed to save audio file")
            return False
    except Exception as e:
        logger.error(f"Error testing audio recording: {e}")
        return False


def main():
    """Run verification tests to check all components."""
    logger.info("Starting Voice RAG verification tests")
    
    # Check component presence
    if not check_directories():
        logger.error("Directory verification failed")
        return 1
    
    if not check_files():
        logger.error("File verification failed")
        return 1
    
    # Check hardware and audio
    check_hardware()
    
    if not check_audio_devices():
        logger.warning("No audio input devices detected, voice features will not work")
    
    try:
        if not test_audio_recording():
            logger.warning("Audio recording test failed, voice features may not work")
    except Exception as e:
        logger.warning(f"Could not test audio recording: {e}")
    
    logger.info("Verification complete. Run the application with: python run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
