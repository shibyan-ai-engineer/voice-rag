"""
Main FastAPI application.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.v1.endpoints import router as api_router
from app.core.config import API_V1_PREFIX, PROJECT_NAME, TEMP_AUDIO_DIR, UPLOADS_DIR
from app.core.logging_config import logger
from app.models_init import init_models
from app.utils import clean_temp_files


# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    description="Voice Retrieval Augmented Generation API",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=API_V1_PREFIX)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Make sure necessary directories exist
os.makedirs(str(TEMP_AUDIO_DIR), exist_ok=True)
os.makedirs(str(UPLOADS_DIR), exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    try:
        logger.info("Starting Voice RAG API application")
        
        # Initialize AI models
        logger.info("Initializing AI models")
        model_status = init_models()
        logger.info(f"Models initialized: {model_status}")
        
        # Clean up old temporary files
        clean_temp_files()
        
        logger.info("Application startup complete")
    
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        # We don't re-raise here to allow the app to start even with model initialization issues
        # Models can be reinitialized later via the API if needed


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    try:
        logger.info("Shutting down Voice RAG API application")
        
        # Clean up temporary files
        clean_temp_files()
        
        logger.info("Application shutdown complete")
    
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


@app.get("/")
async def root():
    """Serve the main frontend page."""
    return FileResponse("static/index.html")


# For direct execution (development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)