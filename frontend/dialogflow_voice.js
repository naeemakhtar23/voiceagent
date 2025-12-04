// Dialogflow ES Voice Recognition
// This replaces Web Speech API with Dialogflow ES streaming for better first-word capture

// Note: currentSession and isProcessingAnswer are declared in voice_bot.js and accessible via window
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let mediaStream = null;

// These functions will be available from voice_bot.js or we'll define fallbacks
function playReadyBeep() {
    if (window.playReadyBeep) {
        window.playReadyBeep();
    } else {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (error) {
            console.warn('Could not play beep:', error);
        }
    }
}

function showStatusMessage(message, type) {
    if (window.showStatusMessage) {
        window.showStatusMessage(message, type);
    } else {
        const statusMessage = document.getElementById('statusMessage');
        if (statusMessage) {
            statusMessage.textContent = message;
            statusMessage.className = `status-message status-${type}`;
            statusMessage.style.display = 'block';
        }
    }
}

function startQuestion(session) {
    if (window.startQuestion) {
        window.startQuestion(session);
    } else {
        // Fallback implementation
        document.getElementById('currentQuestionNum').textContent = session.current_question + 1;
        document.getElementById('totalQuestions').textContent = session.total_questions;
        document.getElementById('questionText').textContent = session.question_text;
    }
}

// Initialize Dialogflow ES voice recognition
async function initializeDialogflowVoice() {
    console.log('Initializing Dialogflow ES voice recognition...');
    
    // Check if MediaRecorder is available
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('MediaRecorder API not available');
        return false;
    }
    
    return true;
}

// Start recording audio with proper warm-up
async function startDialogflowRecording(sessionId) {
    console.log('Starting Dialogflow ES recording...');
    
    if (isRecording) {
        console.log('Already recording, stopping first...');
        await stopDialogflowRecording();
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    try {
        // Request microphone with echo cancellation (as per ChatGPT advice)
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,  // CRITICAL: Prevents echo issues
                noiseSuppression: true,   // Reduces background noise
                autoGainControl: true,    // Normalizes audio levels
                sampleRate: 16000         // Dialogflow ES requires 16kHz
            }
        });
        
        console.log('✅ Microphone access granted with echo cancellation');
        
        // CRITICAL: Wake up VAD (Voice Activity Detection) with a noise burst
        // This ensures the first word "yes" is captured immediately
        // Without this, VAD needs to detect sound first, causing the first word to be missed
        try {
            console.log('🔊 Generating VAD wake-up noise burst for Dialogflow...');
            const vadWakeupContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = vadWakeupContext.createOscillator();
            const gainNode = vadWakeupContext.createGain();
            
            // Create a very low volume noise burst (user won't hear it)
            oscillator.frequency.value = 1000; // 1kHz tone
            oscillator.type = 'sine';
            
            // Very low volume - just enough to wake VAD
            gainNode.gain.setValueAtTime(0.01, vadWakeupContext.currentTime); // 1% volume
            
            oscillator.connect(gainNode);
            gainNode.connect(vadWakeupContext.destination);
            
            oscillator.start(vadWakeupContext.currentTime);
            oscillator.stop(vadWakeupContext.currentTime + 0.05); // 50ms burst
            
            // Close the context after the burst
            setTimeout(() => {
                vadWakeupContext.close().catch(() => {}); // Ignore errors
            }, 100);
            
            console.log('✅ VAD wake-up noise burst sent (50ms, inaudible to user)');
        } catch (vadError) {
            console.warn('Could not generate VAD wake-up burst:', vadError);
            // Continue anyway - this is a helper, not critical
        }
        
        // Create MediaRecorder
        const options = {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: 16000
        };
        
        // Fallback to default if webm not supported
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'audio/webm';
        }
        
        mediaRecorder = new MediaRecorder(mediaStream, options);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
                console.log(`Audio chunk received: ${event.data.size} bytes`);
            }
        };
        
        mediaRecorder.onstop = async () => {
            console.log('Recording stopped, processing audio...');
            await processRecordedAudio(sessionId);
        };
        
        // CRITICAL: Warm-up period (as per ChatGPT advice)
        console.log('⏳ Warm-up period: Waiting 800ms for microphone to initialize...');
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Start recording
        mediaRecorder.start(100); // Collect data every 100ms
        isRecording = true;
        
        console.log('✅✅✅ Recording started - microphone is ready! ✅✅✅');
        console.log('✅✅✅ USER CAN NOW SPEAK - First utterance will be captured! ✅✅✅');
        
        // Play beep to indicate ready
        playReadyBeep();
        showStatusMessage('✅ READY! Say "yes" or "no" now.', 'success');
        
        return true;
    } catch (error) {
        console.error('Error starting recording:', error);
        showStatusMessage('Error accessing microphone. Please allow microphone access.', 'error');
        return false;
    }
}

// Stop recording
async function stopDialogflowRecording() {
    if (mediaRecorder && isRecording) {
        console.log('Stopping recording...');
        mediaRecorder.stop();
        isRecording = false;
    }
    
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
}

// Process recorded audio and send to Dialogflow ES
async function processRecordedAudio(sessionId) {
    if (window.isProcessingAnswer) {
        console.log('Already processing answer, ignoring...');
        return;
    }
    
    if (audioChunks.length === 0) {
        console.warn('No audio chunks to process');
        showStatusMessage('No audio captured. Please try again.', 'error');
        return;
    }
    
    window.isProcessingAnswer = true;
    
    try {
        console.log(`Processing ${audioChunks.length} audio chunks...`);
        
        // Combine audio chunks into a single blob
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        console.log(`Audio blob size: ${audioBlob.size} bytes`);
        
        if (audioBlob.size < 100) {
            console.warn('Audio blob too small, may not contain speech');
            showStatusMessage('Audio too short. Please speak clearly.', 'error');
            window.isProcessingAnswer = false;
            return;
        }
        
        // Convert to WAV format for Dialogflow ES (requires 16kHz, 16-bit PCM)
        const wavBlob = await convertToWav(audioBlob);
        
        // Send to backend for Dialogflow ES processing
        showStatusMessage('Processing your answer...', 'info');
        
        const formData = new FormData();
        formData.append('audio', wavBlob, 'audio.wav');
        formData.append('session_id', sessionId);
        
        const response = await fetch('/api/voice-bot/stream-audio', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            const result = data.result;
            
            if (result.action === 'next') {
                if (window.currentSession) {
                    window.currentSession.current_question = result.question_number - 1;
                    window.currentSession.question_text = result.question_text;
                    startQuestion(window.currentSession);
                    showStatusMessage(`Answer saved: ${result.previous_answer}`, 'success');
                }
            } else if (result.action === 'repeat') {
                showStatusMessage('Question repeated', 'info');
            } else if (result.action === 'complete') {
                document.getElementById('questionDisplay').style.display = 'none';
                document.getElementById('completionMessage').style.display = 'block';
                document.getElementById('progressIndicator').style.display = 'none';
                window.currentSession = null; // Update global reference
                showStatusMessage('All questions completed!', 'success');
            }
        } else {
            showStatusMessage(data.error || 'Error processing answer', 'error');
        }
    } catch (error) {
        console.error('Error processing audio:', error);
        showStatusMessage('Error processing audio. Please try again.', 'error');
    } finally {
        window.isProcessingAnswer = false;
        audioChunks = []; // Clear chunks for next recording
    }
}

// Convert WebM audio to WAV format (16kHz, 16-bit PCM) for Dialogflow ES
async function convertToWav(audioBlob) {
    try {
        // Create audio context (local to this function to avoid conflicts)
        const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        
        // Decode audio
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        // Convert to 16-bit PCM
        const samples = audioBuffer.getChannelData(0);
        const pcmData = new Int16Array(samples.length);
        
        for (let i = 0; i < samples.length; i++) {
            // Clamp and convert float32 (-1 to 1) to int16 (-32768 to 32767)
            const s = Math.max(-1, Math.min(1, samples[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        // Create WAV file
        const wavBuffer = createWavFile(pcmData, 16000);
        return new Blob([wavBuffer], { type: 'audio/wav' });
    } catch (error) {
        console.error('Error converting to WAV:', error);
        // Fallback: return original blob (backend will need to handle conversion)
        return audioBlob;
    }
}

// Create WAV file from PCM data
function createWavFile(pcmData, sampleRate) {
    const length = pcmData.length;
    const buffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(buffer);
    
    // WAV header
    const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * 2, true);
    
    // Write PCM data
    let offset = 44;
    for (let i = 0; i < length; i++) {
        view.setInt16(offset, pcmData[i], true);
        offset += 2;
    }
    
    return buffer;
}

// Start listening with Dialogflow ES (replaces Web Speech API)
async function startDialogflowListening() {
    // Get currentSession from voice_bot.js
    if (!window.currentSession) {
        showStatusMessage('No active session', 'error');
        return;
    }
    
    console.log('Starting Dialogflow ES listening...');
    
    // Update UI
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
    
    showStatusMessage('Initializing microphone... Please wait for "Ready" message.', 'info');
    
    // Start recording with warm-up
    const success = await startDialogflowRecording(window.currentSession.session_id);
    
    if (!success) {
        stopDialogflowListening();
    }
}

// Stop listening
function stopDialogflowListening() {
    stopDialogflowRecording();
    
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

// Auto-stop recording after speech ends (with delay as per ChatGPT advice)
function setupAutoStop() {
    // Stop recording 2 seconds after user stops speaking
    // This gives Dialogflow ES time to process the audio
    setTimeout(async () => {
        if (isRecording && !window.isProcessingAnswer) {
            console.log('Auto-stopping recording after speech ended...');
            await stopDialogflowRecording();
        }
    }, 2000);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', async () => {
    const available = await initializeDialogflowVoice();
    if (!available) {
        console.warn('Dialogflow ES voice recognition not available');
        const startListeningBtn = document.getElementById('startListeningBtn');
        if (startListeningBtn) {
            startListeningBtn.style.display = 'none';
        }
    }
});

// Export functions for use in voice_bot.js
window.startDialogflowListening = startDialogflowListening;
window.stopDialogflowListening = stopDialogflowListening;

