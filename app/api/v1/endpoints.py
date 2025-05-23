"""
API endpoints for the Voice RAG FastAPI application.
"""
import os
import shutil
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse

from app.api.v1.schemas import (
    TextQueryRequest,
    TextQueryResponse,
    ChatVoiceResponse,
    UploadPdfResponse,
    StatusResponse,
    ErrorResponse,
)
from app.services.audio_service import transcribe_audio, text_to_speech, save_uploaded_audio
from app.services.document_service import process_and_index_pdf, query_faiss_index, CURRENT_PDF_NAME, clear_faiss_index
from app.services.rag_llm_service import reset_conversation_memory
from app.services.rag_llm_service import generate_response
from app.core.config import UPLOADS_DIR, TEMP_AUDIO_DIR
from app.core.logging_config import logger

import json
import asyncio
from typing import Dict, Any, List, Optional, cast
import sounddevice as sd
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
import torch
from sklearn.metrics.pairwise import cosine_similarity
from langchain_community.embeddings import OllamaEmbeddings

from app.api.v1.schemas import WebSocketAction, WebSocketMessage


router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get the health status of the API and model status.
    """
    from app.models_init import get_models
    
    try:
        # Get model status
        models = get_models()
        model_status = {
            "asr": models["asr"] is not None,
            "embeddings": models["embeddings"] is not None,
            "llm": models["llm"] is not None,
            "tts": models["tts"] is not None,
        }
        
        return {
            "status": "healthy",
            "models_loaded": model_status,
            "indexed_document_name": CURRENT_PDF_NAME,
        }
    
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_pdf", response_model=UploadPdfResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF for processing and indexing.
    """
    try:
        if file.filename is None:
            raise HTTPException(status_code=400, detail="Missing filename")
            
        filename = file.filename
        logger.info(f"Received PDF upload: {filename}")
        
        # Validate file type
        if not filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type: {filename}")
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Create unique filename and ensure it's a string
        pdf_path = os.path.join(str(UPLOADS_DIR), filename)
        
        # Save the uploaded file
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"PDF saved to {pdf_path}")
        
        # Process and index the PDF (with filename asserted to be string)
        assert filename is not None, "Filename cannot be None at this point"
        process_and_index_pdf(pdf_path, filename)
        
        # Reset conversation memory since a new document is loaded
        reset_conversation_memory()
        
        return {
            "message": "PDF processed and indexed successfully",
            "filename": filename,
        }
    
    except Exception as e:
        logger.error(f"Error processing PDF upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat_voice", response_model=ChatVoiceResponse)
async def chat_voice(background_tasks: BackgroundTasks, audio_file: UploadFile = File(...)):
    """
    Process a voice query and return a voice response.
    """
    try:
        # Check file details for debugging
        file_details = f"filename: {audio_file.filename}, content_type: {audio_file.content_type}, size: {audio_file.size if hasattr(audio_file, 'size') else 'unknown'}"
        logger.info(f"Received voice chat request: {file_details}")
        
        # Save the uploaded audio
        content = await audio_file.read()
        logger.debug(f"Read audio content of size: {len(content)} bytes")
        audio_path = save_uploaded_audio(content)
        
        # Transcribe the audio
        user_query = transcribe_audio(audio_path)
        
        # Get relevant chunks from FAISS
        context_chunks = query_faiss_index(user_query)
        
        # Generate text response
        response_text = generate_response(user_query, context_chunks)
        
        # Generate audio response
        audio_file_path, _ = text_to_speech(response_text)
        
        # Get the filename from the path
        audio_filename = os.path.basename(audio_file_path)
        
        # Clean up temporary files in background
        background_tasks.add_task(os.remove, audio_path)
        
        return {
            "user_query_text": user_query,
            "response_text": response_text,
            "response_audio_url": f"/api/v1/audio/{audio_filename}",
        }
    
    except Exception as e:
        logger.error(f"Error processing voice chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """
    Serve generated audio files.
    """
    try:
        logger.info(f"Requested audio file: {filename}")
        
        audio_path = os.path.join(TEMP_AUDIO_DIR, filename)
        
        if not os.path.exists(audio_path):
            logger.warning(f"Audio file not found: {audio_path}")
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            audio_path,
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat_text", response_model=TextQueryResponse)
async def chat_text(query: TextQueryRequest):
    """
    Process a text query and return a text response.
    """
    try:
        logger.info(f"Received text chat request: {query.query_text}")
        
        # Get relevant chunks from FAISS
        context_chunks = query_faiss_index(query.query_text)
        
        # Generate text response
        response_text = generate_response(query.query_text, context_chunks)
        
        return {
            "response_text": response_text,
            "context_used": context_chunks,
        }
    
    except Exception as e:
        logger.error(f"Error processing text chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/listen")
async def websocket_listen(websocket: WebSocket):
    """
    WebSocket endpoint for continuous listening and wake word detection.
    This allows the server to continuously listen for the wake word "Friday"
    and notify the client when it's detected.
    """
    await websocket.accept()
    logger.info("WebSocket connection established for voice listening")
    
    try:
        # Get embeddings model for wake word detection
        from app.models_init import get_models
        
        models = get_models()
        embeddings_model = models["embeddings"]
        
        if embeddings_model is None:
            await websocket.send_text(json.dumps(
                WebSocketMessage(
                    type="error",
                    message="Embeddings model not initialized"
                ).dict()
            ))
            await websocket.close()
            return
        
        # Get wake word embedding
        WAKE_WORD = "Friday"
        SIMILARITY_THRESHOLD = 0.7
        SAMPLE_RATE = 16000
        RECORDING_DURATION = 3  # seconds - increased for better wake word detection
        
        try:
            wake_word_embedding = np.array(embeddings_model.embed_query(WAKE_WORD)).reshape(1, -1)
            await websocket.send_text(json.dumps(
                WebSocketMessage(
                    type="log",
                    message="Wake word embedding created. Listening for 'Friday'..."
                ).dict()
            ))
        except Exception as e:
            logger.error(f"Error creating wake word embedding: {e}")
            await websocket.send_text(json.dumps(
                WebSocketMessage(
                    type="error",
                    message=f"Failed to create wake word embedding: {str(e)}"
                ).dict()
            ))
            await websocket.close()
            return
        
        # Variable to track if we should be listening
        listening = True
        
        # Function to record audio
        async def record_audio():
            try:
                logger.info("Starting audio recording for wake word detection")
                 # Get audio devices more safely with robust error handling
                input_device = 0  # Default to device 0 as a safe fallback
                
                try:
                    # Try to query available devices
                    try:
                        devices = sd.query_devices()
                        logger.info(f"Successfully queried {len(devices)} audio devices")
                    except Exception as query_err:
                        logger.warning(f"Could not query audio devices: {query_err}")
                        logger.info("Using default device 0")
                        return input_device
                    
                    # Try to find a suitable input device
                    for i, device in enumerate(devices):
                        try:
                            # Convert device to dict if it's not already
                            device_dict = device
                            if not isinstance(device, dict):
                                device_dict = device.to_dict() if hasattr(device, 'to_dict') else {}
                            
                            # Try different ways to get max input channels
                            max_inputs = 0
                            if isinstance(device_dict, dict) and 'max_input_channels' in device_dict:
                                max_inputs = device_dict['max_input_channels']
                            elif hasattr(device, 'max_input_channels'):
                                max_inputs = device.max_input_channels
                            
                            logger.debug(f"Device {i}: {device_dict.get('name', 'Unknown')} - Input channels: {max_inputs}")
                            
                            if max_inputs > 0:
                                input_device = i
                                logger.info(f"Selected input device {i}: {device_dict.get('name', 'Unknown')}")
                                break
                        except Exception as device_err:
                            logger.warning(f"Error processing device {i}: {device_err}")
                            continue
                    
                    # Try to use system default if no suitable device was found
                    if input_device == 0:
                        try:
                            default_device = sd.default.device[0]
                            if default_device is not None:
                                input_device = default_device
                                logger.info(f"Using system default input device: {input_device}")
                        except Exception as default_err:
                            logger.warning(f"Could not get default device: {default_err}")
                except Exception as dev_err:
                    logger.warning(f"Error in device selection process: {dev_err}")
                    logger.info(f"Using fallback input device: {input_device}")
                
                # Log the selected device
                logger.info(f"Using input device for WebSocket: {input_device}")
                
                # Record audio
                audio = sd.rec(int(RECORDING_DURATION * SAMPLE_RATE),
                              samplerate=SAMPLE_RATE,
                              channels=1,
                              dtype='float32',
                              device=input_device)
                
                # Wait for recording to complete
                sd.wait()
                
                return audio
            except Exception as e:
                logger.error(f"Error in WebSocket audio recording: {e}")
                return np.zeros(int(RECORDING_DURATION * SAMPLE_RATE)).astype(np.float32).reshape(-1, 1)
        
        # Main listening loop
        while True:
            # Check for incoming messages from client
            try:
                # Use wait_for with a timeout to make this non-blocking
                message_data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.01  # Short timeout to check but not block
                )
                
                try:
                    # Parse the client message
                    message = json.loads(message_data)
                    action = message.get("action")
                    
                    if action == "pause_listening":
                        listening = False
                        logger.info("Voice listening paused via WebSocket")
                        # Acknowledge the pause
                        await websocket.send_text(json.dumps(
                            WebSocketMessage(
                                type="log",
                                message="Listening paused"
                            ).dict()
                        ))
                    elif action == "resume_listening":
                        listening = True
                        logger.info("Voice listening resumed via WebSocket")
                        # Acknowledge the resume
                        await websocket.send_text(json.dumps(
                            WebSocketMessage(
                                type="log",
                                message="Listening resumed"
                            ).dict()
                        ))
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON via WebSocket: {message_data}")
            except asyncio.TimeoutError:
                # No message received within timeout, continue with normal operation
                pass
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            
            # Skip recording if listening is paused
            if not listening:
                await asyncio.sleep(0.5)  # Small sleep when not listening
                continue
            
            # Record audio
            audio_data = await record_audio()
            
            # Process for wake word detection only if we're still listening
            # (in case pause_listening was received during recording)
            if listening and audio_data.size > 0:
                try:
                    # Get ASR model to transcribe
                    asr_model = models["asr"]
                    if asr_model is None:
                        continue  # Skip this round if ASR model not available
                    
                    # Convert audio data to format needed by ASR
                    # Save as temporary WAV file (NeMo needs a file path)
                    import os
                    import uuid
                    from scipy.io.wavfile import write
                    
                    temp_file = os.path.join(TEMP_AUDIO_DIR, f"ws_temp_{uuid.uuid4()}.wav")
                    write(temp_file, SAMPLE_RATE, (audio_data * 32767).astype(np.int16))
                    
                    # Transcribe audio
                    result = asr_model.transcribe([temp_file])
                    transcription = result[0].text.lower()
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                    
                    # Check for wake word using embedding similarity
                    if transcription:
                        logger.debug(f"WebSocket heard: {transcription}")
                        
                        # Compute embedding for the transcription
                        try:
                            transcription_embedding = np.array(embeddings_model.embed_query(transcription)).reshape(1, -1)
                            
                            # Compute cosine similarity
                            similarity = cosine_similarity(wake_word_embedding, transcription_embedding)[0][0]
                            
                            if similarity >= SIMILARITY_THRESHOLD:
                                logger.info(f"Wake word detected via WebSocket! Similarity: {similarity:.2f}")
                                
                                # Notify the client
                                await websocket.send_text(json.dumps(
                                    WebSocketMessage(
                                        type="wake_word_detected",
                                        message="Wake word 'Friday' detected"
                                    ).dict()
                                ))
                                
                                # Pause listening until client sends resume
                                listening = False
                        except Exception as e:
                            logger.error(f"Error computing embedding similarity: {e}")
                except Exception as e:
                    logger.error(f"Error in wake word detection processing: {e}")
            
            # Short delay between recording attempts
            await asyncio.sleep(0.1)
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info("WebSocket connection closed")


@router.websocket("/ws/heartbeat")
async def websocket_heartbeat_endpoint(websocket: WebSocket):
    """
    Simple WebSocket endpoint that sends a heartbeat message every few seconds.
    This is helpful for clients to check if the connection is still alive.
    """
    await websocket.accept()
    logger.info("WebSocket heartbeat connection established")
    
    try:
        # Start the heartbeat task
        heartbeat_task = asyncio.create_task(websocket_heartbeat(websocket))
        
        # Wait indefinitely (until client disconnects)
        while True:
            # Check for incoming messages but don't block
            try:
                # Wait for a message with a short timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                # Echo it back for debugging
                await websocket.send_text(data)
            except asyncio.TimeoutError:
                # No message received, just continue
                await asyncio.sleep(1)
            except WebSocketDisconnect:
                break
        
        # Cancel the heartbeat task when the client disconnects
        heartbeat_task.cancel()
        
    except WebSocketDisconnect:
        logger.info("WebSocket heartbeat client disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket heartbeat: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


async def websocket_heartbeat(websocket: WebSocket):
    """Send periodic heartbeats to keep the WebSocket connection alive."""
    try:
        while True:
            await asyncio.sleep(30)  # Send a heartbeat every 30 seconds
            await websocket.send_text(json.dumps(
                WebSocketMessage(
                    type="log",
                    message="heartbeat"
                ).dict()
            ))
    except Exception:
        # Just exit if there's an error
        pass


@router.post("/clear_state")
async def clear_state():
    """
    Endpoint to clear application state (FAISS index and conversation history)
    when the frontend page is refreshed.
    """
    try:
        logger.info("Clearing application state due to page refresh")
        
        # Clear FAISS index
        index_cleared = clear_faiss_index()
        
        # Reset conversation history
        reset_conversation_memory()
        
        return {
            "message": "Application state cleared successfully",
            "index_cleared": index_cleared
        }
    
    except Exception as e:
        logger.error(f"Error clearing application state: {e}")
        raise HTTPException(status_code=500, detail=str(e))