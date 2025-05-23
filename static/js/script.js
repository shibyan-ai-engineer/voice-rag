/**
 * Voice RAG Frontend Application
 * 
 * This script handles:
 * 1. Wake word detection using WebSocket communication
 * 2. Audio recording via Web Audio API
 * 3. Communication with the backend API
 * 4. UI updates and visual feedback
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const statusMessage = document.getElementById('status-message');
    const userQueryDisplay = document.getElementById('user-query-display');
    const botResponseDisplay = document.getElementById('bot-response-display');
    const audioPlayer = document.getElementById('bot-audio-player');
    const pdfUploadInput = document.getElementById('pdf-upload');
    const pdfUploadBtn = document.getElementById('pdf-upload-btn');
    const pdfSubmitBtn = document.getElementById('pdf-submit-btn');
    const fileName = document.getElementById('file-name');
    const pdfStatus = document.getElementById('pdf-status');
    const pdfUploadForm = document.getElementById('pdf-upload-form');

    // Application State
    const appState = {
        LISTENING_WW: 'LISTENING_WW',   // Listening for wake word
        RECORDING_PROMPT: 'RECORDING_PROMPT', // Recording user prompt
        PROCESSING: 'PROCESSING',       // Processing query
        PLAYING_RESPONSE: 'PLAYING_RESPONSE', // Playing audio response
        ERROR: 'ERROR'                  // Error state
    };
    
    // Current state
    let currentState = appState.LISTENING_WW;
    
    // API endpoints
    const API = {
        CHAT_VOICE: '/api/v1/chat_voice',
        UPLOAD_PDF: '/api/v1/upload_pdf',
        STATUS: '/api/v1/status',
        CLEAR_STATE: '/api/v1/clear_state'
    };
    
    // GIF paths
    const GIFS = {
        LISTENING_WW: '/static/gifs/listening_for_wakeword.gif',
        WAKEWORD_DETECTED: '/static/gifs/wakeword_detected.gif',
        RECORDING_PROMPT: '/static/gifs/listening_for_prompt.gif',
        PROCESSING: '/static/gifs/processing_query.gif',
        PLAYING_RESPONSE: '/static/gifs/speaking_response.gif',
        ERROR: '/static/gifs/error.gif'
    };

    // Audio recording variables
    let mediaRecorder = null;
    let audioChunks = [];
    let recordingTimeout = null;
    const MAX_RECORDING_TIME = 10000; // 10 seconds max recording time

    // Variables for WebSocket wake word detection
    let wsReconnectTimer = null;

    /**
     * Initialize the application
     */
    async function initApp() {
        updateUI(appState.LISTENING_WW, 'Initializing...');
        
        // First clear state on page load to reset database and conversation history
        try {
            await fetch(API.CLEAR_STATE, {
                method: 'POST'
            });
            console.log('Application state cleared on page load');
        } catch (error) {
            console.error('Error clearing application state:', error);
        }
        
        // Check API status
        try {
            const response = await fetch(API.STATUS);
            const status = await response.json();
            
            if (status.status === 'healthy') {
                console.log('API is healthy', status);
                
                // Update the current document display
                const currentDocumentName = document.getElementById('current-document-name');
                if (status.indexed_document_name) {
                    currentDocumentName.textContent = status.indexed_document_name;
                    pdfStatus.textContent = `Document successfully loaded`;
                    // Change the button text to "Select Another PDF" when a document is loaded
                    pdfUploadBtn.textContent = "Select Another PDF";
                    // Hide "No file selected" when a document is already loaded
                    fileName.style.display = 'none';
                } else {
                    currentDocumentName.textContent = 'No document loaded';
                    pdfStatus.textContent = 'Please upload a PDF document';
                    pdfUploadBtn.textContent = "Select PDF File";
                }
                
                // Initialize wake word detection
                initWakeWordDetection();
            } else {
                updateUI(appState.ERROR, 'API is not ready. Please try again later.');
            }
        } catch (error) {
            console.error('Error checking API status:', error);
            updateUI(appState.ERROR, 'Failed to connect to the API. Please check if the server is running.');
        }
        
        // Set up PDF upload button
        pdfUploadBtn.addEventListener('click', () => pdfUploadInput.click());
        
        pdfUploadInput.addEventListener('change', () => {
            if (pdfUploadInput.files.length > 0) {
                fileName.textContent = pdfUploadInput.files[0].name;
                fileName.style.display = 'inline-block';
                pdfSubmitBtn.disabled = false;
            } else {
                fileName.style.display = 'none';
            }
        });
        
        pdfUploadForm.addEventListener('submit', handlePdfUpload);
    }

    /**
     * Initialize wake word detection
     */
    async function initWakeWordDetection() {
        try {
            // Request microphone access
            await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Initialize WebSocket wake word detector
            await initWebSocketWakeWord();
            updateUI(appState.LISTENING_WW, 'Waiting for wake word "Friday"...');
        } catch (error) {
            console.error('Error initializing wake word detection:', error);
            updateUI(appState.ERROR, 'Microphone access is required for voice commands. Please allow microphone access and reload the page.');
        }
    }

    /**
     * Initialize WebSocket-based wake word detector
     * This connects to the server for continuous wake word detection
     */
    async function initWebSocketWakeWord() {
        try {
            console.log('Setting up voice recognition using WebSocket...');
            
            // Configure reconnection parameters
            const MAX_RECONNECT_DELAY = 30000; // Max delay between reconnection attempts (30 seconds)
            const INITIAL_RECONNECT_DELAY = 1000; // Initial delay (1 second)
            let reconnectDelay = INITIAL_RECONNECT_DELAY;
            let reconnectAttempts = 0;
            let isReconnecting = false;
            
            // Function to create and set up the WebSocket
            function setupWebSocket() {
                // Create a WebSocket for continuous voice recognition
                let socketUrl = `ws://${window.location.host}/api/v1/ws/listen`;
                console.log(`Connecting to WebSocket at: ${socketUrl}`);
                
                // Use try-catch to handle potential issues with WebSocket creation
                let socket;
                try {
                    socket = new WebSocket(socketUrl);
                } catch (wsError) {
                    console.error("Error creating WebSocket connection:", wsError);
                    console.log("Switching to browser-based wake word detection...");
                    setupBrowserFallback();
                    return null;
                }
                
                socket.onopen = () => {
                    console.log('WebSocket connection opened for voice recognition');
                    updateUI(appState.LISTENING_WW, 'Listening for wake word "Friday"...');
                    
                    // Reset reconnection parameters on successful connection
                    reconnectDelay = INITIAL_RECONNECT_DELAY;
                    reconnectAttempts = 0;
                    isReconnecting = false;
                };
                
                socket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'wake_word_detected') {
                            // Wake word detected, handle it
                            console.log('Wake word "Friday" detected via WebSocket!');
                            handleWakeWordDetected();
                        } else if (data.type === 'log') {
                            if (data.message !== 'heartbeat') {  // Don't log heartbeats
                                console.log('Server log:', data.message);
                            }
                        } else if (data.type === 'error') {
                            console.error('Server error:', data.message);
                        }
                    } catch (err) {
                        console.error('Error parsing WebSocket message:', err, event.data);
                    }
                };
                
                socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    updateUI(appState.ERROR, 'Connection issue detected. Attempting to reconnect...');
                    
                    // If we've tried too many times, fall back to browser-based solution
                    if (reconnectAttempts > 5) {
                        console.log('Too many WebSocket errors, falling back to browser-based wake word detection');
                        updateUI(appState.ERROR, 'Using browser-based wake word detection as fallback');
                        setupBrowserFallback();
                    }
                };
                
                socket.onclose = (event) => {
                    console.log('WebSocket connection closed:', event.code, event.reason);
                    
                    // Attempt to reconnect if not already reconnecting
                    if (!isReconnecting) {
                        isReconnecting = true;
                        
                        // Update UI to inform user
                        updateUI(appState.LISTENING_WW, 'Connection lost. Attempting to reconnect...');
                        
                        // Use exponential backoff with jitter for reliable reconnection
                        const jitter = Math.random() * 0.5 + 0.75; // Random between 0.75 and 1.25
                        const delay = Math.min(reconnectDelay * jitter, MAX_RECONNECT_DELAY);
                        
                        console.log(`Attempting to reconnect WebSocket in ${delay}ms (attempt ${reconnectAttempts + 1})`);
                        
                        setTimeout(() => {
                            reconnectAttempts++;
                            reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
                            
                            // Try to reconnect
                            setupWebSocket();
                        }, delay);
                    }
                };
                
                // Store the socket for later use
                window.voiceSocket = socket;
                
                // Set up a heartbeat checker
                if (window.heartbeatChecker) {
                    clearInterval(window.heartbeatChecker);
                }
                
                window.lastHeartbeat = Date.now();
                window.heartbeatChecker = setInterval(() => {
                    // If no heartbeat received for 90 seconds, reconnect
                    if (Date.now() - window.lastHeartbeat > 90000) {
                        console.log('No heartbeat received for 90 seconds, reconnecting...');
                        socket.close();
                    }
                }, 30000); // Check every 30 seconds
                
                return socket;
            }
            
            // Create the initial WebSocket
            setupWebSocket();
            
            // Also set up a separate heartbeat WebSocket connection
            try {
                const heartbeatSocket = new WebSocket(`ws://${window.location.host}/api/v1/ws/heartbeat`);
                
                heartbeatSocket.onopen = () => {
                    console.log('WebSocket heartbeat connection established');
                };
                
                heartbeatSocket.onmessage = () => {
                    window.lastHeartbeat = Date.now();
                };
                
                heartbeatSocket.onerror = (error) => {
                    console.error('WebSocket heartbeat error:', error);
                };
                
                window.heartbeatSocket = heartbeatSocket;
            } catch (e) {
                console.error('Failed to set up heartbeat WebSocket:', e);
            }
            
            console.log('Voice recognition initialized via WebSocket');
        } catch (error) {
            console.error('Error initializing voice recognition:', error);
            // Fall back to in-browser solution if WebSocket setup fails
            setupBrowserFallback();
        }
    }
    
    /**
     * Set up browser-side fallback for wake word detection
     * This implementation uses the browser's built-in SpeechRecognition API
     * as a fallback when the WebSocket-based wake word detection fails
     */
    function setupBrowserFallback() {
        console.log('Setting up browser-based wake word detection as fallback...');
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('Speech recognition not supported in this browser');
            addSimulateWakeWordButton();
            return;
        }
        
        try {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            let isListening = false;
            
            recognition.onstart = function() {
                console.log('Browser fallback: Speech recognition started');
                isListening = true;
                updateUI(appState.LISTENING_WW, 'Listening for wake word "Friday"... (browser mode)');
            };
            
            recognition.onresult = function(event) {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript.toLowerCase().trim();
                    console.log('Browser heard:', transcript);
                    
                    if (transcript.includes('friday')) {
                        console.log('Wake word "Friday" detected in browser mode:', transcript);
                        recognition.stop();
                        handleWakeWordDetected();
                        return;
                    }
                }
            };
            
            recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                isListening = false;
                setTimeout(() => {
                    if (!isListening) recognition.start();
                }, 1000);
            };
            
            recognition.onend = function() {
                console.log('Speech recognition ended');
                isListening = false;
                // Restart if we're not in the middle of processing a query
                if (currentState === appState.LISTENING_WW) {
                    setTimeout(() => recognition.start(), 1000);
                }
            };
            
            // Start recognition
            recognition.start();
            window.speechRecognition = recognition;
            
            console.log('Browser fallback voice recognition initialized');
        } catch (error) {
            console.error('Error initializing browser speech recognition:', error);
            addSimulateWakeWordButton();
        }
    }
    
    /**
     * For demo purposes: Add a button to simulate wake word detection
     */
    function addSimulateWakeWordButton() {
        const btn = document.createElement('button');
        btn.textContent = 'Simulate "Friday" Wake Word';
        btn.className = 'btn btn-primary';
        btn.style.margin = '20px auto 10px';
        btn.style.display = 'block';
        
        btn.addEventListener('click', handleWakeWordDetected);
        
        // Insert after the animation container
        const container = document.getElementById('visual-feedback-container');
        container.parentNode.insertBefore(btn, container.nextSibling);
        
        updateUI(appState.LISTENING_WW, 'Wake word detection not available. Use the button to simulate.');
    }

    /**
     * Handle wake word detection
     */
    function handleWakeWordDetected() {
        if (currentState !== appState.LISTENING_WW) {
            console.log('Wake word ignored: not in listening state');
            return; // Only respond to wake word in listening state
        }
        
        console.log('Wake word detected!');
        
        // Temporarily change UI to acknowledge wake word detection
        // Skip animation for faster flow and directly update status message
        updateUI(appState.LISTENING_WW, 'Wake word "Friday" detected!');
        
        // Stop wake word detection while recording
        if (window.voiceSocket && window.voiceSocket.readyState === WebSocket.OPEN) {
            window.voiceSocket.send(JSON.stringify({
                action: 'pause_listening'
            }));
            console.log('Sent pause_listening command to WebSocket server');
        } else if (window.speechRecognition) {
            try {
                window.speechRecognition.stop();
                console.log('Browser speech recognition paused');
            } catch (e) {
                console.log('Error stopping speech recognition:', e);
            }
        }
        
        // Short delay to acknowledge wake word before starting recording
        setTimeout(() => {
            startRecording();
        }, 600);
    }

    /**
     * Start audio recording
     */
    async function startRecording() {
        updateUI(appState.RECORDING_PROMPT, 'I\'m listening to your question...');
        
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Create MediaRecorder instance
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            // Store audio chunks when data is available
            mediaRecorder.addEventListener('dataavailable', (event) => {
                audioChunks.push(event.data);
            });
            
            // Handle recording complete
            mediaRecorder.addEventListener('stop', () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                sendAudioToServer(audioBlob);
            });
            
            // Start recording
            mediaRecorder.start();
            
            // Set timeout to automatically stop recording
            recordingTimeout = setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    stopRecording();
                }
            }, MAX_RECORDING_TIME);
            
            // TODO: Add silence detection for better user experience
            
            // Add stop recording button for user control
            addStopRecordingButton();
            
        } catch (error) {
            console.error('Error starting audio recording:', error);
            updateUI(appState.ERROR, 'Failed to access microphone. Please check your browser permissions.');
            resetToListening();
        }
    }
    
    /**
     * Add a temporary button to stop recording
     */
    function addStopRecordingButton() {
        // Remove any existing button first
        const existingBtn = document.getElementById('stop-recording-btn');
        if (existingBtn) {
            existingBtn.remove();
        }
        
        const btn = document.createElement('button');
        btn.id = 'stop-recording-btn';
        btn.textContent = 'Done Speaking';
        btn.className = 'btn btn-primary';
        btn.style.margin = '20px auto 10px';
        btn.style.display = 'block';
        
        btn.addEventListener('click', stopRecording);
        
        // Insert after the animation container
        const container = document.getElementById('visual-feedback-container');
        container.parentNode.insertBefore(btn, container.nextSibling);
    }
    
    /**
     * Remove the stop recording button
     */
    function removeStopRecordingButton() {
        const btn = document.getElementById('stop-recording-btn');
        if (btn) {
            btn.remove();
        }
    }

    /**
     * Stop audio recording
     */
    function stopRecording() {
        // Clear recording timeout
        if (recordingTimeout) {
            clearTimeout(recordingTimeout);
            recordingTimeout = null;
        }
        
        // Remove stop recording button
        removeStopRecordingButton();
        
        // Stop media recorder if it's recording
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            
            // Stop the microphone track
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            updateUI(appState.PROCESSING, 'Processing your question...');
        }
    }

    /**
     * Send the recorded audio to the server
     * @param {Blob} audioBlob - The recorded audio blob
     */
    async function sendAudioToServer(audioBlob) {
        try {
            // Create form data for file upload
            const formData = new FormData();
            formData.append('audio_file', audioBlob, 'recording.wav');
            
            // Send audio to server
            const response = await fetch(API.CHAT_VOICE, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Update UI with transcription and response
            userQueryDisplay.textContent = result.user_query_text;
            botResponseDisplay.textContent = result.response_text;
            
            // Play audio response
            playAudioResponse(result.response_audio_url);
            
        } catch (error) {
            console.error('Error sending audio to server:', error);
            updateUI(appState.ERROR, 'Failed to process your question. Please try again.');
            
            // Reset after a short delay
            setTimeout(resetToListening, 3000);
        }
    }

    /**
     * Play the audio response from the server
     * @param {string} audioUrl - The URL to the audio file
     */
    function playAudioResponse(audioUrl) {
        updateUI(appState.PLAYING_RESPONSE, 'Here\'s my response...');
        
        // Set the audio source
        audioPlayer.src = audioUrl;
        
        // Play the audio
        audioPlayer.play().catch(error => {
            console.error('Error playing audio:', error);
            // Continue with the flow even if audio playback fails
            resetToListening();
        });
        
        // Reset to listening when audio finishes
        audioPlayer.onended = resetToListening;
    }

    /**
     * Handle PDF upload
     * @param {Event} event - Form submit event
     */
    async function handlePdfUpload(event) {
        event.preventDefault();
        
        if (!pdfUploadInput.files.length) {
            return;
        }
        
        try {
            pdfStatus.textContent = 'Uploading PDF...';
            pdfSubmitBtn.disabled = true;
            
            // Create form data for PDF upload
            const formData = new FormData();
            formData.append('file', pdfUploadInput.files[0]);
            
            // Send PDF to server
            const response = await fetch(API.UPLOAD_PDF, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Update UI
            pdfStatus.textContent = `Document successfully processed`;
            document.getElementById('current-document-name').textContent = result.filename;
            
            // Reset file input
            pdfUploadInput.value = '';
            fileName.style.display = 'none'; // Hide the filename display
            pdfSubmitBtn.disabled = true;
            // Keep the "Select Another PDF" text on the button
            
        } catch (error) {
            console.error('Error uploading PDF:', error);
            pdfStatus.textContent = 'Failed to upload PDF. Please try again.';
            pdfSubmitBtn.disabled = false;
        }
    }

    /**
     * Reset to listening for wake word state
     */
    function resetToListening() {
        console.log('Resetting to listening state');
        
        // Resume wake word detection via WebSocket or browser recognition
        if (window.voiceSocket && window.voiceSocket.readyState === WebSocket.OPEN) {
            // Send a message to resume listening on the server side
            window.voiceSocket.send(JSON.stringify({
                action: 'resume_listening'
            }));
            console.log('Sent resume_listening command to WebSocket server');
        } else if (window.speechRecognition) {
            // Resume browser-based speech recognition
            try {
                window.speechRecognition.start();
                console.log('Browser speech recognition resumed');
            } catch (e) {
                console.log('Browser recognition already running or error:', e);
            }
        }
        
        updateUI(appState.LISTENING_WW, 'Waiting for wake word "Friday"...');
    }

    /**
     * Update the UI based on current state
     * @param {string} state - New app state
     * @param {string} message - Status message to display
     * @param {string} animationOverride - Optional override for the animation to display
     */
    function updateUI(state, message, animationOverride = null) {
        currentState = state;
        statusMessage.textContent = message;
        
        // Remove any existing class from status message
        statusMessage.className = '';
        
        // Hide all animations
        document.querySelectorAll('.animation').forEach(anim => {
            anim.classList.remove('active');
        });
        
        // Show the appropriate animation
        let animationId;
        
        switch (state) {
            case appState.LISTENING_WW:
                animationId = 'listening-animation';
                statusMessage.classList.add('listening');
                break;
            case appState.RECORDING_PROMPT:
                animationId = 'recording-animation';
                statusMessage.classList.add('recording');
                break;
            case appState.PROCESSING:
                animationId = 'processing-animation';
                statusMessage.classList.add('processing');
                break;
            case appState.PLAYING_RESPONSE:
                animationId = 'speaking-animation';
                statusMessage.classList.add('speaking');
                break;
            case appState.ERROR:
                animationId = 'error-animation';
                statusMessage.classList.add('error');
                break;
        }
        
        // Show the chosen animation
        document.getElementById(animationId).classList.add('active');
        
        // We're no longer using the wake word animation as it slowed down the flow
        // Code for animation override has been removed
    }

    // Initialize the app
    initApp();
});