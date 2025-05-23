"""
Audio processing services: Transcription (ASR) and Text-to-Speech (TTS)
"""
import os
import tempfile
import numpy as np
import soundfile as sf
import torch
import time
import uuid

from app.core.logging_config import logger
from app.core.config import (
    AUDIO_SAMPLE_RATE, 
    AUDIO_TTS_SAMPLE_RATE,
    TEMP_AUDIO_DIR,
    TTS_MODEL_VOICE
)
from app.models_init import get_models


def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio file using NeMo ASR model.
    
    Args:
        audio_file_path: Path to the uploaded audio file
    
    Returns:
        Transcribed text
    """
    try:
        logger.info(f"Transcribing audio file: {audio_file_path}")
        
        # Verify file exists and size
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file does not exist: {audio_file_path}")
        
        file_size = os.path.getsize(audio_file_path)
        logger.info(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            logger.warning("Audio file is empty")
            return ""
        
        # Get ASR model
        models = get_models()
        asr_model = models["asr"]
        
        if asr_model is None:
            raise ValueError("ASR model not initialized")
        
        # Log device information
        device_str = "Unknown"
        try:
            device_str = str(next(asr_model.parameters()).device)
            logger.info(f"ASR model is on device: {device_str}")
        except Exception as e:
            logger.warning(f"Could not determine model device: {e}")
        
        # Transcribe audio with timeout protection
        logger.info("Starting transcription...")
        start_time = time.time()
        
        result = asr_model.transcribe([audio_file_path])
        
        elapsed_time = time.time() - start_time
        logger.info(f"Transcription took {elapsed_time:.2f} seconds")
        
        if not result or len(result) == 0:
            logger.warning("Transcription returned empty result")
            return ""
        
        transcription = result[0].text.lower()
        
        logger.info(f"Transcription completed: '{transcription}'")
        return transcription
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        # Return empty string instead of raising to avoid interrupting the workflow
        logger.info("Returning empty transcription due to error")
        return ""


def text_to_speech(text: str) -> tuple[str, bytes]:
    """
    Convert text to speech using Kokoro TTS model.
    
    Args:
        text: Text to convert to speech
    
    Returns:
        tuple: (audio_file_path, audio_bytes)
    """
    try:
        logger.info(f"Converting text to speech: '{text}'")
        
        # Get TTS model
        models = get_models()
        tts_pipeline = models["tts"]
        
        if tts_pipeline is None:
            raise ValueError("TTS model not initialized")
        
        # Generate unique file name
        file_id = str(uuid.uuid4())[:8]
        output_file = os.path.join(TEMP_AUDIO_DIR, f"response_{file_id}.wav")
        
        # Generate audio with Kokoro
        generator = tts_pipeline(
            text,
            voice=TTS_MODEL_VOICE,
            speed=1,
            split_pattern=r'\n+'
        )
        
        # Collect all audio segments
        all_audio = []
        for _, _, audio in generator:
            # Convert tensor to numpy array if needed
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()
            all_audio.append(audio)
        
        # Concatenate segments if multiple were generated
        if len(all_audio) > 1:
            full_audio = np.concatenate(all_audio)
        else:
            full_audio = all_audio[0] if all_audio else np.array([])
        
        # Save the audio to a file
        sf.write(output_file, full_audio, AUDIO_TTS_SAMPLE_RATE)
        logger.info(f"Audio generated and saved to {output_file}")
        
        # Also return the audio as bytes for direct response
        with open(output_file, "rb") as f:
            audio_bytes = f.read()
        
        return output_file, audio_bytes
    
    except Exception as e:
        logger.error(f"Error in text-to-speech conversion: {e}")
        raise


def save_uploaded_audio(file_content: bytes) -> str:
    """
    Save uploaded audio to a temporary file.
    
    Args:
        file_content: Audio file content as bytes
    
    Returns:
        Path to the saved file
    """
    try:
        # Validate input
        if not file_content:
            logger.warning("Empty file content received")
            raise ValueError("Empty audio content")
        
        logger.info(f"Saving uploaded audio, size: {len(file_content)} bytes")
        
        # Create a temporary file with .wav extension
        file_id = str(uuid.uuid4())[:8]
        temp_dir = str(TEMP_AUDIO_DIR)  # Convert Path to string
        os.makedirs(temp_dir, exist_ok=True)  # Ensure directory exists
        
        temp_file = os.path.join(temp_dir, f"upload_{file_id}.wav")
        
        # Write the content to the file
        with open(temp_file, "wb") as f:
            f.write(file_content)
        
        # Verify file was written correctly
        if not os.path.exists(temp_file):
            raise FileNotFoundError(f"Failed to create file at {temp_file}")
        
        file_size = os.path.getsize(temp_file)
        logger.info(f"Uploaded audio saved to {temp_file} (size: {file_size} bytes)")
        
        if file_size == 0:
            raise ValueError(f"File was created but is empty: {temp_file}")
        
        return temp_file
    
    except Exception as e:
        logger.error(f"Error saving uploaded audio: {e}")
        raise