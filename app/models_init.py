"""
Centralized AI model loading and initialization.
"""
import os
import torch
import nemo.collections.asr as nemo_asr
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from kokoro import KPipeline
from app.core.logging_config import logger
from app.core.config import get_device, ASR_MODEL_NAME, LLM_MODEL_NAME, EMBEDDING_MODEL_NAME

# Set MPS fallback for PyTorch if on macOS
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# Global model instances
asr_model = None
embeddings_model = None
llm_model = None
tts_pipeline = None


def init_models():
    """Initialize all AI models used in the application."""
    global asr_model, embeddings_model, llm_model, tts_pipeline
    
    device = get_device()
    logger.info(f"Using device: {device}")
    
    # Initialize ASR model
    try:
        logger.info(f"Loading ASR model: {ASR_MODEL_NAME}")
        asr_model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(model_name=ASR_MODEL_NAME)
        
        if device == "mps":
            asr_model = asr_model.to(torch.device("mps"))
        elif device == "cuda":
            asr_model = asr_model.to(torch.device("cuda"))
        
        logger.info("ASR model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading ASR model: {e}")
        raise
    
    # Initialize Ollama Embeddings
    try:
        logger.info(f"Loading Embedding model: {EMBEDDING_MODEL_NAME}")
        embeddings_model = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
        logger.info("Embeddings model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading Embeddings model: {e}")
        raise
    
    # Initialize Ollama LLM
    try:
        logger.info(f"Loading LLM: {LLM_MODEL_NAME}")
        llm_model = Ollama(model=LLM_MODEL_NAME)
        logger.info("LLM loaded successfully")
    except Exception as e:
        logger.error(f"Error loading LLM: {e}")
        raise
    
    # Initialize Kokoro TTS
    try:
        logger.info("Loading TTS model")
        tts_pipeline = KPipeline(lang_code='b')  # British English
        logger.info("TTS model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading TTS model: {e}")
        raise
    
    logger.info("All models initialized successfully")
    return {
        "asr": asr_model is not None,
        "embeddings": embeddings_model is not None,
        "llm": llm_model is not None,
        "tts": tts_pipeline is not None
    }


def get_models():
    """Get the initialized models."""
    return {
        "asr": asr_model,
        "embeddings": embeddings_model,
        "llm": llm_model,
        "tts": tts_pipeline
    }