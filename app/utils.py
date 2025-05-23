"""
Utility functions for the Voice RAG application.
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import List

from app.core.logging_config import logger
from app.core.config import TEMP_AUDIO_DIR


def clean_old_files(directory: str, max_age_hours: int = 24) -> List[str]:
    """
    Clean up temporary files older than the specified age.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files in hours
        
    Returns:
        List of removed files
    """
    try:
        logger.info(f"Cleaning old files from {directory} (older than {max_age_hours} hours)")
        
        now = datetime.now()
        removed_files = []
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip directories and non-files
            if not os.path.isfile(file_path):
                continue
            
            # Get the file's modification time
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # If the file is older than the max age, remove it
            if now - file_mod_time > timedelta(hours=max_age_hours):
                os.remove(file_path)
                removed_files.append(file_path)
                logger.info(f"Removed old file: {file_path}")
        
        logger.info(f"Removed {len(removed_files)} old files")
        return removed_files
    
    except Exception as e:
        logger.error(f"Error cleaning old files: {e}")
        return []


def clean_temp_files() -> List[str]:
    """
    Clean up temporary audio files.
    
    Returns:
        List of removed files
    """
    return clean_old_files(str(TEMP_AUDIO_DIR), 2)  # Clean files older than 2 hours


def generate_unique_id() -> str:
    """
    Generate a unique ID for file naming.
    
    Returns:
        A unique ID string
    """
    return str(uuid.uuid4())