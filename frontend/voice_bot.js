// Voice Bot JavaScript
let currentSession = null;
let recognition = null;
let isListening = false;
let isProcessingAnswer = false; // Flag to prevent duplicate processing
let microphoneStream = null; // Keep microphone stream active during recognition

// Initialize Web Speech API
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        
        // Use continuous mode but with manual stop - this gives us more control
        // Non-continuous mode has issues where onresult doesn't fire reliably
        recognition.continuous = true;
        recognition.interimResults = true; // Get interim results to see if it's detecting anything
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        
        console.log('Speech Recognition initialized with continuous mode');
        
        let hasResult = false;
        let finalTranscript = '';
        let interimTranscript = '';
        let recognitionTimeout = null;
        let interimProcessTimeout = null;
        
        recognition.onstart = () => {
            console.log('✅ Speech recognition started successfully!');
            console.log('Recognition state:', recognition.continuous ? 'continuous' : 'single', 
                       'interimResults:', recognition.interimResults,
                       'lang:', recognition.lang);
            isListening = true;
            hasResult = false;
            finalTranscript = '';
            interimTranscript = '';
            isProcessingAnswer = false; // Reset processing flag
            
            // Clear any pending timeouts
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
            }
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
            }
            
            // Set a longer timeout (15 seconds) - if no speech after this, stop
            recognitionTimeout = setTimeout(() => {
                if (!hasResult && !isProcessingAnswer) {
                    console.log('⏱️ Recognition timeout - no speech detected after 15 seconds');
                    console.log('Final transcript:', finalTranscript, 'Interim transcript:', interimTranscript);
                    recognition.stop();
                }
            }, 15000);
        };
        
        recognition.onaudiostart = () => {
            console.log('🎤 Audio capture started');
        };
        
        recognition.onaudioend = () => {
            console.log('🎤 Audio capture ended');
        };
        
        recognition.onsoundstart = () => {
            console.log('🔊 Sound detected (speech may be starting)');
        };
        
        recognition.onsoundend = () => {
            console.log('🔇 Sound ended');
        };
        
        recognition.onspeechstart = () => {
            console.log('🗣️ Speech detected!');
        };
        
        recognition.onspeechend = () => {
            console.log('🗣️ Speech ended - waiting for API to process and return results...');
            console.log('The API needs to send audio to Google servers and get results back (usually 2-4 seconds)');
            
            // In continuous mode, we need to manually stop after speech ends to get final results
            // For short words like "yes" or "no", we need to wait longer (4-5 seconds)
            // to give the API enough time to process and return results
            // Single words are often too short, so we wait longer
            setTimeout(() => {
                if (!hasResult && !isProcessingAnswer && isListening) {
                    console.log('Stopping recognition after speech ended to force result processing...');
                    try {
                        recognition.stop(); // This should trigger onresult with final results
                    } catch (e) {
                        console.error('Error stopping recognition:', e);
                    }
                }
            }, 5000); // Wait 5 seconds for API to process (longer for short words like single "yes"/"no")
        };
        
        recognition.onresult = (event) => {
            console.log('✅✅✅ onresult event FIRED! ✅✅✅');
            console.log('resultIndex:', event.resultIndex, 'results.length:', event.results.length);
            console.log('Full event object:', event);
            console.log('Event results array:', event.results);
            
            // Check if results array is empty (this would be unusual)
            if (!event.results || event.results.length === 0) {
                console.error('⚠️ onresult fired but results array is empty!');
                console.error('This is unusual - the API detected speech but returned no results');
                return;
            }
            
            // Don't process if we're already processing an answer
            if (isProcessingAnswer) {
                console.log('Already processing answer, ignoring new results');
                return;
            }
            
            // Clear the timeout since we got a result
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
                recognitionTimeout = null;
            }
            
            // Clear any pending interim processing
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
                interimProcessTimeout = null;
            }
            
            // Process all results from this event
            console.log('Processing results from index', event.resultIndex, 'to', event.results.length - 1);
            
            let foundAnyResult = false;
            let currentInterim = '';
            let currentFinal = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (!result) {
                    console.warn(`Result ${i} is null/undefined`);
                    continue;
                }
                
                if (!result[0]) {
                    console.warn(`Result ${i}[0] is null/undefined`);
                    continue;
                }
                
                const transcript = result[0].transcript;
                if (!transcript) {
                    console.warn(`Result ${i} has no transcript`);
                    continue;
                }
                
                const trimmedTranscript = transcript.trim();
                const confidence = result[0].confidence || 0;
                const isFinal = result.isFinal;
                
                console.log(`Result ${i}: "${trimmedTranscript}" isFinal: ${isFinal}, confidence: ${confidence}`);
                foundAnyResult = true;
                
                if (isFinal) {
                    currentFinal += trimmedTranscript + ' ';
                    hasResult = true;
                    console.log('✅ Final result found:', trimmedTranscript);
                } else {
                    currentInterim += trimmedTranscript + ' ';
                    console.log('📝 Interim result found:', trimmedTranscript);
                }
            }
            
            if (!foundAnyResult) {
                console.error('⚠️ onresult fired but no valid results found in event.results');
                console.error('This might indicate an API issue');
                return;
            }
            
            // Update our transcripts (store in outer scope for timeout access)
            if (currentInterim.trim()) {
                interimTranscript = currentInterim.trim();
                console.log('Interim transcript updated:', interimTranscript);
            }
            if (currentFinal.trim()) {
                finalTranscript = currentFinal.trim();
                console.log('Final transcript updated:', finalTranscript);
            }
            
            // If we have a final result, process it immediately (this is the primary path)
            if (currentFinal.trim()) {
                const transcript = currentFinal.trim();
                const lastResult = event.results[event.results.length - 1];
                const confidence = lastResult && lastResult[0] ? lastResult[0].confidence : 0;
                console.log('✅ Processing FINAL result:', transcript, 'Confidence:', confidence);
                
                // Clear any pending interim processing since we have a final result
                if (interimProcessTimeout) {
                    clearTimeout(interimProcessTimeout);
                    interimProcessTimeout = null;
                }
                
                // Mark as having a result
                hasResult = true;
                
                // Stop recognition immediately and process
                try {
                    recognition.stop();
                } catch (e) {
                    console.log('Error stopping recognition:', e);
                }
                
                // Process the answer
                processVoiceInput(transcript);
                return; // Exit early since we processed final result
            }
            
            // If we only have interim results, check if we should process immediately
            if (currentInterim.trim() && !hasResult && !isProcessingAnswer) {
                // Store the interim result
                interimTranscript = currentInterim.trim();
                const cleanInterim = currentInterim.trim().toLowerCase();
                console.log('Interim result detected:', cleanInterim);
                
                // Check if it's a clear single word - process IMMEDIATELY
                // This prevents the user from having to repeat "yes" or "no"
                const isSingleWord = cleanInterim === 'yes' || cleanInterim === 'no';
                
                if (isSingleWord) {
                    // Process single words immediately - don't wait for timeout
                    console.log('✅ Processing single word immediately:', cleanInterim);
                    
                    // Clear any pending timeout
                    if (interimProcessTimeout) {
                        clearTimeout(interimProcessTimeout);
                        interimProcessTimeout = null;
                    }
                    
                    // Mark as having a result
                    hasResult = true;
                    
                    // Stop recognition immediately
                    try {
                        recognition.stop();
                    } catch (e) {
                        console.log('Error stopping recognition:', e);
                    }
                    
                    // Process the answer immediately
                    processVoiceInput(cleanInterim);
                    return; // Exit early since we processed it
                } else {
                    // For longer phrases, wait a bit to see if we get a final result
                    console.log('Phrase detected, waiting for final result or timeout...');
                    
                    // Clear any existing timeout first
                    if (interimProcessTimeout) {
                        clearTimeout(interimProcessTimeout);
                    }
                    
                    // Wait 3 seconds for final result before processing interim phrase
                    interimProcessTimeout = setTimeout(() => {
                        // Check again if we're still not processing and no final result came
                        if (!isProcessingAnswer && !hasResult && isListening) {
                            // Use the stored interimTranscript
                            const cleanInterimCheck = interimTranscript.trim().toLowerCase();
                            console.log('Processing interim phrase after timeout:', cleanInterimCheck);
                            
                            // Process if it's a clear yes/no phrase
                            if (cleanInterimCheck === 'yes yes' || cleanInterimCheck === 'no no' ||
                                cleanInterimCheck.startsWith('yes') || cleanInterimCheck.startsWith('no')) {
                                // Clean up duplicates - if it's "yes yes", extract just "yes"
                                const answer = cleanInterimCheck.includes('yes') ? 'yes' : 'no';
                                console.log('✅ Processing interim phrase as final:', answer);
                                
                                // Mark as having a result
                                hasResult = true;
                                try {
                                    recognition.stop();
                                } catch (e) {
                                    console.log('Error stopping recognition:', e);
                                }
                                // Don't set isProcessingAnswer here - let processVoiceInput do it
                                processVoiceInput(answer);
                            } else {
                                console.log('Interim phrase not clear enough:', cleanInterimCheck);
                            }
                        } else {
                            console.log('Skipping interim processing - already processing or has result');
                        }
                    }, 3000); // Wait 3 seconds for final result before processing phrase
                }
            }
        };
        
        recognition.onerror = (event) => {
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
                recognitionTimeout = null;
            }
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
                interimProcessTimeout = null;
            }
            
            console.error('❌ Speech recognition error:', event.error);
            console.error('Error details:', event);
            isListening = false;
            hasResult = false;
            
            let errorMessage = 'Speech recognition error. ';
            switch(event.error) {
                case 'no-speech':
                    errorMessage += 'No speech detected. Please speak louder and clearer.';
                    break;
                case 'audio-capture':
                    errorMessage += 'No microphone found. Please check your microphone.';
                    break;
                case 'not-allowed':
                    errorMessage += 'Microphone permission denied. Please allow microphone access.';
                    break;
                case 'aborted':
                    // Don't show error for aborted - it's usually intentional
                    console.log('Speech recognition aborted');
                    return;
                case 'network':
                    errorMessage += 'Network error. Web Speech API requires internet connection to Google servers. Please check your connection.';
                    break;
                case 'service-not-allowed':
                    errorMessage += 'Speech recognition service not allowed. This may be a browser or network issue.';
                    break;
                default:
                    errorMessage += `Error: ${event.error}. This may indicate a network or browser compatibility issue.`;
            }
            
            stopListening();
            showStatusMessage(errorMessage, 'error');
        };
        
        recognition.onend = () => {
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
                recognitionTimeout = null;
            }
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
                interimProcessTimeout = null;
            }
            
            console.log('Speech recognition ended, hasResult:', hasResult, 'isProcessingAnswer:', isProcessingAnswer, 'finalTranscript:', finalTranscript, 'interimTranscript:', interimTranscript);
            isListening = false;
            
            // If we're processing an answer, don't show error messages
            if (isProcessingAnswer || hasResult) {
                // We got a result (either final or interim), UI will be updated by processVoiceInput
                console.log('Recognition ended with result - answer is being processed');
                stopListening();
            } else if (interimTranscript && !hasResult) {
                // We have interim transcript but no final result - process the interim
                console.log('Processing interim transcript as final (onresult may not have fired):', interimTranscript);
                const cleanInterim = interimTranscript.trim().toLowerCase();
                if (cleanInterim === 'yes' || cleanInterim === 'no' || 
                    cleanInterim.includes('yes') || cleanInterim.includes('no')) {
                    const answer = cleanInterim.includes('yes') ? 'yes' : 'no';
                    hasResult = true;
                    processVoiceInput(answer);
                    stopListening();
                    return;
                }
            }
            
            if (document.getElementById('listeningStatus').style.display !== 'none') {
                // Recognition ended without a result and we're still showing listening status
                console.log('Recognition ended without result');
                console.warn('⚠️ Web Speech API onresult event did not fire. This can happen if:');
                console.warn('  1. No internet connection (Web Speech API requires internet)');
                console.warn('  2. Browser compatibility issue');
                console.warn('  3. Speech recognition service unavailable');
                stopListening();
                showStatusMessage('Speech detected but results not received. This may be due to internet connectivity or browser limitations. Please use the Yes/No buttons below, or check your internet connection and try again.', 'info');
            } else {
                // Recognition ended but we're not in listening state, just clean up
                stopListening();
            }
        };
        
        return true;
    }
    return false;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const speechAvailable = initializeSpeechRecognition();
    if (!speechAvailable) {
        console.warn('Speech recognition not supported in this browser');
        const startListeningBtn = document.getElementById('startListeningBtn');
        if (startListeningBtn) {
            startListeningBtn.style.display = 'none';
        }
    }
    
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Start session
    const startSessionBtn = document.getElementById('startSessionBtn');
    if (startSessionBtn) {
        startSessionBtn.addEventListener('click', startNewSession);
    }
    
    // Voice input
    const startListeningBtn = document.getElementById('startListeningBtn');
    if (startListeningBtn) {
        startListeningBtn.addEventListener('click', () => {
            if (recognition && !isListening) {
                startListening();
            }
        });
    }
    
    // Button handlers
    const yesBtn = document.getElementById('yesBtn');
    const noBtn = document.getElementById('noBtn');
    const repeatBtn = document.getElementById('repeatBtn');
    const skipBtn = document.getElementById('skipBtn');
    const viewResultsBtn = document.getElementById('viewResultsBtn');
    const startNewSessionBtn = document.getElementById('startNewSessionBtn');
    
    if (yesBtn) yesBtn.addEventListener('click', () => submitAnswer('yes', 'text'));
    if (noBtn) noBtn.addEventListener('click', () => submitAnswer('no', 'text'));
    if (repeatBtn) repeatBtn.addEventListener('click', repeatQuestion);
    if (skipBtn) skipBtn.addEventListener('click', () => submitAnswer('skip', 'text'));
    if (viewResultsBtn) viewResultsBtn.addEventListener('click', viewResults);
    if (startNewSessionBtn) startNewSessionBtn.addEventListener('click', startNewSession);
}

// Start new session
async function startNewSession() {
    try {
        showStatusMessage('Starting session...', 'info');
        
        const response = await fetch('/api/voice-bot/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            currentSession = data.session;
            startQuestion(currentSession);
            showStatusMessage('Session started successfully', 'success');
        } else {
            showStatusMessage(data.error || 'Failed to start session', 'error');
        }
    } catch (error) {
        console.error('Error starting session:', error);
        showStatusMessage('Error starting session. Please try again.', 'error');
    }
}

// Start question
function startQuestion(session) {
    document.getElementById('startSession').style.display = 'none';
    document.getElementById('questionDisplay').style.display = 'block';
    document.getElementById('completionMessage').style.display = 'none';
    document.getElementById('progressIndicator').style.display = 'block';
    
    document.getElementById('currentQuestionNum').textContent = session.current_question + 1;
    document.getElementById('totalQuestions').textContent = session.total_questions;
    document.getElementById('questionText').textContent = session.question_text;
    
    // Speak question using Web Speech API
    if ('speechSynthesis' in window) {
        // Cancel any ongoing speech
        speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(session.question_text);
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        utterance.onend = () => {
            console.log('Question spoken');
        };
        
        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
        };
        
        speechSynthesis.speak(utterance);
    }
}

// Start listening
async function startListening() {
    console.log('startListening called, recognition:', recognition ? 'exists' : 'null', 'isListening:', isListening);
    
    if (!recognition) {
        console.error('Speech recognition not available!');
        showStatusMessage('Speech recognition not supported in this browser. Please use Chrome or Edge.', 'error');
        return;
    }
    
    // Check if already listening
    if (isListening) {
        console.log('Already listening, stopping first...');
        try {
            recognition.stop();
        } catch (e) {
            console.log('Error stopping recognition:', e);
        }
        // Wait a bit before restarting
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    // Request microphone permission (just to ensure we have it)
    // Note: Web Speech API handles its own microphone access, but we request permission
    // first to ensure the browser has granted it
    console.log('Requesting microphone access...');
    try {
        // Release any existing stream first
        if (microphoneStream) {
            microphoneStream.getTracks().forEach(track => track.stop());
            microphoneStream = null;
        }
        
        // Request permission but release immediately - recognition will handle its own access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('Microphone permission granted');
        
        // Release immediately - Web Speech API will request its own access
        stream.getTracks().forEach(track => track.stop());
        console.log('Permission stream released - recognition will use its own microphone access');
    } catch (error) {
        console.error('Microphone permission error:', error);
        showStatusMessage('Microphone permission denied. Please allow microphone access in your browser settings.', 'error');
        return;
    }
    
    try {
        console.log('Updating UI and starting recognition...');
        // Update UI first
        document.getElementById('listeningStatus').style.display = 'flex';
        const startListeningBtn = document.getElementById('startListeningBtn');
        if (startListeningBtn) {
            startListeningBtn.disabled = true;
            startListeningBtn.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span>Listening...</span>
            `;
        }
        
        // Clear any previous status messages
        const statusMsg = document.getElementById('statusMessage');
        if (statusMsg) {
            statusMsg.style.display = 'none';
        }
        
        // Start recognition
        console.log('Calling recognition.start()...');
        console.log('Recognition config:', {
            continuous: recognition.continuous,
            interimResults: recognition.interimResults,
            lang: recognition.lang,
            maxAlternatives: recognition.maxAlternatives
        });
        
        // Test network connectivity to Google Speech API
        console.log('Testing network connectivity...');
        fetch('https://www.google.com', { mode: 'no-cors', method: 'HEAD' })
            .then(() => console.log('✅ Network connectivity OK'))
            .catch(() => console.warn('⚠️ Network connectivity test failed (may be normal due to CORS)'));
        
        try {
            recognition.start();
            console.log('✅ recognition.start() called successfully');
            showStatusMessage('Listening... Say "yes" or "no" clearly into your microphone.', 'info');
            
            // Monitor recognition state
            setTimeout(() => {
                if (isListening) {
                    console.log('✅ Recognition is still active after 1 second');
                } else {
                    console.warn('⚠️ Recognition stopped unexpectedly');
                }
            }, 1000);
        } catch (startError) {
            console.error('❌ Error calling recognition.start():', startError);
            stopListening();
            showStatusMessage(`Error starting recognition: ${startError.message}. Please try again.`, 'error');
        }
    } catch (error) {
        console.error('Error starting speech recognition:', error, 'Error name:', error.name);
        if (error.name === 'InvalidStateError') {
            console.log('InvalidStateError - recognition already running, stopping and retrying...');
            // Recognition is already running, stop it first and retry
            try {
                recognition.stop();
            } catch (e) {
                console.log('Error stopping recognition:', e);
            }
            setTimeout(() => {
                try {
                    console.log('Retrying recognition.start()...');
                    recognition.start();
                    console.log('Retry successful');
                    showStatusMessage('Listening... Say "yes" or "no" clearly.', 'info');
                } catch (retryError) {
                    console.error('Error retrying speech recognition:', retryError);
                    stopListening();
                    showStatusMessage('Error starting voice input. Please try again.', 'error');
                }
            }, 500);
        } else {
            console.error('Other error starting recognition:', error);
            stopListening();
            showStatusMessage('Error starting voice input. Please try again or use buttons.', 'error');
        }
    }
}

// Stop listening
function stopListening() {
    isListening = false;
    
    // Stop recognition if it's running
    if (recognition) {
        try {
            recognition.stop();
        } catch (error) {
            // Ignore errors when stopping
            console.log('Recognition already stopped');
        }
    }
    
    // Microphone stream is already released (we don't keep it active)
    
    document.getElementById('listeningStatus').style.display = 'none';
    const startListeningBtn = document.getElementById('startListeningBtn');
    if (startListeningBtn) {
        startListeningBtn.disabled = false;
        startListeningBtn.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
            <span>Start Speaking</span>
        `;
    }
}

// Process voice input
async function processVoiceInput(text) {
    console.log('processVoiceInput called with:', text, 'isProcessingAnswer:', isProcessingAnswer);
    
    // Prevent duplicate processing
    if (isProcessingAnswer) {
        console.log('Already processing answer, ignoring duplicate:', text);
        return;
    }
    
    // Mark as processing immediately to prevent race conditions
    isProcessingAnswer = true;
    console.log('Marked as processing, calling submitAnswer...');
    
    // Stop listening first
    stopListening();
    
    // Clean up the text - remove duplicates and normalize
    let cleanText = text.trim().toLowerCase();
    
    // Handle cases like "yes yes" or "no no"
    if (cleanText.includes('yes')) {
        cleanText = 'yes';
    } else if (cleanText.includes('no')) {
        cleanText = 'no';
    }
    
    // Show what was recognized
    if (cleanText && (cleanText === 'yes' || cleanText === 'no')) {
        console.log('Cleaned text:', cleanText, '- calling submitAnswer');
        showStatusMessage(`Recognized: "${cleanText}". Processing...`, 'info');
        try {
            await submitAnswer(cleanText, 'text');
        } catch (error) {
            console.error('Error in submitAnswer:', error);
            isProcessingAnswer = false; // Reset on error
            showStatusMessage('Error processing answer. Please try again.', 'error');
        }
    } else {
        console.log('Invalid text, resetting:', cleanText);
        showStatusMessage('Could not understand. Please try again or use buttons.', 'error');
        isProcessingAnswer = false; // Reset if we couldn't process
    }
}

// Repeat question
function repeatQuestion() {
    if (currentSession) {
        const questionText = document.getElementById('questionText').textContent;
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(questionText);
            utterance.rate = 0.9;
            speechSynthesis.speak(utterance);
        }
    }
}

// Submit answer
async function submitAnswer(input, inputType) {
    console.log('submitAnswer called with:', input, 'inputType:', inputType, 'currentSession:', currentSession ? 'exists' : 'null');
    
    if (!currentSession) {
        console.error('No current session!');
        showStatusMessage('No active session', 'error');
        isProcessingAnswer = false;
        return;
    }
    
    // Disable buttons while processing
    const buttons = document.querySelectorAll('.btn-answer, .btn-voice');
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        showStatusMessage('Processing answer...', 'info');
        console.log('Sending request to /api/voice-bot/answer with:', {
            session_id: currentSession.session_id,
            input: input,
            input_type: inputType
        });
        
        const response = await fetch('/api/voice-bot/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession.session_id,
                input: input,
                input_type: inputType
            })
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        if (data.success) {
            const result = data.result;
            
            if (result.action === 'next') {
                currentSession.current_question = result.question_number - 1;
                currentSession.question_text = result.question_text;
                // Reset processing flag before starting next question
                isProcessingAnswer = false;
                startQuestion(currentSession);
                showStatusMessage(`Answer saved: ${result.previous_answer}`, 'success');
            } else if (result.action === 'repeat') {
                // Question repeated, no change needed
                isProcessingAnswer = false;
                showStatusMessage('Question repeated', 'info');
            } else if (result.action === 'complete') {
                document.getElementById('questionDisplay').style.display = 'none';
                document.getElementById('completionMessage').style.display = 'block';
                document.getElementById('progressIndicator').style.display = 'none';
                currentSession = null;
                isProcessingAnswer = false;
                showStatusMessage('All questions completed!', 'success');
            }
        } else {
            showStatusMessage(data.error || 'Error processing answer', 'error');
            isProcessingAnswer = false; // Reset on error
        }
    } catch (error) {
        console.error('Error submitting answer:', error);
        showStatusMessage('Error submitting answer. Please try again.', 'error');
        isProcessingAnswer = false; // Reset on error
    } finally {
        // Re-enable buttons
        buttons.forEach(btn => btn.disabled = false);
    }
}

// View results
function viewResults() {
    if (currentSession && currentSession.call_id) {
        window.location.href = `/results?call_id=${currentSession.call_id}`;
    } else {
        window.location.href = '/#results';
    }
}

// Show status message
function showStatusMessage(message, type) {
    const statusMessage = document.getElementById('statusMessage');
    if (!statusMessage) return;
    
    statusMessage.textContent = message;
    statusMessage.className = `status-message status-${type}`;
    statusMessage.style.display = 'block';
    
    // Auto-hide after 3 seconds for success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 3000);
    }
}


