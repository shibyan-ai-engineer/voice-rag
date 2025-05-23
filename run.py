#!/usr/bin/env python
"""
Run script for the Voice RAG FastAPI application.
"""
import uvicorn
import os
import sys

def setup_environment():
    """Set up environment variables."""
    # Enable MPS fallback for PyTorch on Apple Silicon
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

def main():
    """Run the FastAPI application."""
    setup_environment()
    
    # Run with uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    sys.exit(main())
