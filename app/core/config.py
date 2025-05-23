"""
Configuration settings for the Voice RAG FastAPI application.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
TEMP_AUDIO_DIR = DATA_DIR / "temp_audio"
FAISS_INDEX_DIR = ROOT_DIR / "faiss_index"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Audio settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_TTS_SAMPLE_RATE = 24000  # Kokoro TTS sample rate
AUDIO_MAX_DURATION = 30  # Max duration of audio recording in seconds

# RAG settings
RAG_TOP_K = 3  # Number of chunks to retrieve

# Model settings
ASR_MODEL_NAME = "nvidia/parakeet-rnnt-1.1b"
LLM_MODEL_NAME = "gemma3:4b-it-qat"
EMBEDDING_MODEL_NAME = "nomic-embed-text"
TTS_MODEL_VOICE = "af_heart"

# Determine device (CUDA, MPS, or CPU)
def get_device():
    """Determine the appropriate device for model inference."""
    import torch
    
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon GPU
    else:
        return "cpu"

# Environment settings
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"

# FastAPI settings
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "Voice RAG API"

# Get uploaded PDF name - will be set during runtime
CURRENT_PDF_NAME: Optional[str] = None