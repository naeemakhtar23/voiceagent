// Voice Bot JavaScript
let currentSession = null;
window.currentSession = null; // Make it globally accessible for dialogflow_voice.js
let recognition = null;
let isListening = false;
let isProcessingAnswer = false; // Flag to prevent duplicate processing
window.isProcessingAnswer = false; // Make it globally accessible for dialogflow_voice.js
let microphoneStream = null; // Keep microphone stream active during recognition
let audioContext = null; // For audio level monitoring
let analyser = null; // For audio level analysis
let audioLevelCheckInterval = null; // Interval for checking audio levels

// Initialize Web Speech API
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        
        // Use CONTINUOUS mode - it buffers audio and processes when ready
        // Non-continuous mode has issues where onresult doesn't fire at all
        // Continuous mode at least buffers and can process when second utterance triggers it
        recognition.continuous = true; // Back to true - continuous mode buffers audio
        recognition.interimResults = true; // Get interim results to see if it's detecting anything
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        
        console.log('Speech Recognition initialized with continuous mode (buffers audio for processing)');
        
        let hasResult = false;
        let finalTranscript = '';
        let interimTranscript = '';
        let recognitionTimeout = null;
        let interimProcessTimeout = null;
        let isRecognitionReady = false; // Track when recognition is actually ready to capture
        
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
            window.isProcessingAnswer = false; // Update global reference
            isRecognitionReady = false; // Not ready yet - need to wait for audio to initialize
            window.speechEndedDetected = false; // Reset speech detection flag
            window.speechEndedTime = null; // Reset speech ended time
            
            // Clear any pending timeouts
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
            }
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
            }
            
            // Wait longer (2.5 seconds) for recognition to fully initialize and start capturing audio
            // This prevents the first utterance from being missed
            // The onaudiostart event should fire before this, but if it doesn't, this is a fallback
            const readyTimeout = setTimeout(() => {
                if (!isRecognitionReady) {
                    isRecognitionReady = true;
                    window.recognitionReadyTime = Date.now(); // Track when we became ready
                    console.log('✅✅✅ Recognition is now READY (fallback timeout after 2.5 seconds)! ✅✅✅');
                    console.log('⚠️ NOTE: onaudiostart did not fire - using fallback timeout');
                    console.log('✅✅✅ USER CAN NOW SPEAK - First utterance will be captured! ✅✅✅');
                    
                    // Play beep to indicate ready
                    playReadyBeep();
                    showStatusMessage('✅ READY! Say "yes" or "no" now.', 'success');
                }
            }, 2500); // Increased to 2.5 seconds to give more time for onaudiostart to fire
            
            // Store timeout so we can clear it if onaudiostart fires first
            window.recognitionReadyTimeout = readyTimeout;
            
            // Set a longer timeout (15 seconds) - if no speech after this, stop
            recognitionTimeout = setTimeout(() => {
                if (!hasResult && !isProcessingAnswer) {
                    console.error('⏱️⏱️⏱️ Recognition timeout - no speech detected after 15 seconds ⏱️⏱️⏱️');
                    console.error('Final transcript:', finalTranscript, 'Interim transcript:', interimTranscript);
                    console.error('isRecognitionReady:', isRecognitionReady, 'isListening:', isListening);
                    console.error('speechEndedDetected:', window.speechEndedDetected || false);
                    
                    if (window.speechEndedDetected) {
                        console.error('⚠️⚠️⚠️ CRITICAL: Speech WAS detected (onspeechend fired) but onresult NEVER fired! ⚠️⚠️⚠️');
                        console.error('This is a Web Speech API issue - speech detected but no results returned');
                        console.error('Possible causes:');
                        console.error('  1. Network issue preventing API from returning results');
                        console.error('  2. Web Speech API limitation/bug');
                        console.error('  3. Browser compatibility issue');
                        showStatusMessage('Speech detected but not processed. This is a known API limitation. Please use the Yes/No buttons.', 'error');
                    } else {
                        console.error('This means speech was never detected (onspeechend never fired)');
                        console.error('Possible causes:');
                        console.error('  1. Microphone not working or not accessible');
                        console.error('  2. Speech too quiet or unclear');
                        console.error('  3. Recognition stopped prematurely');
                        console.error('  4. Browser compatibility issue');
                        showStatusMessage('No speech detected. Please check your microphone and try again, or use the Yes/No buttons.', 'error');
                    }
                    recognition.stop();
                }
            }, 15000);
            
            // Add periodic health checks to see if recognition is still active
            let healthCheckCount = 0;
            const healthCheckInterval = setInterval(() => {
                healthCheckCount++;
                console.log(`🔍 Health check ${healthCheckCount}: isListening=${isListening}, isRecognitionReady=${isRecognitionReady}, hasResult=${hasResult}`);
                
                // Clear interval if we got a result or recognition stopped
                if (hasResult || !isListening) {
                    clearInterval(healthCheckInterval);
                    console.log('Health check stopped - recognition completed or stopped');
                }
            }, 2000); // Check every 2 seconds
            
            // Store interval so we can clear it later
            window.recognitionHealthCheck = healthCheckInterval;
        };
        
        recognition.onaudiostart = () => {
            console.log('🎤🎤🎤 Audio capture started - this is the RELIABLE indicator that recognition is ready! 🎤🎤🎤');
            console.log('🎤 Microphone is now actively capturing audio');
            console.log('🎤 Audio level monitoring should show if microphone is actually receiving sound');
            
            // Verify audio is actually flowing by checking our monitoring
            if (analyser) {
                setTimeout(() => {
                    const dataArray = new Uint8Array(analyser.frequencyBinCount);
                    analyser.getByteFrequencyData(dataArray);
                    const maxLevel = Math.max(...dataArray);
                    const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                    console.log(`🎤 Audio level check at onaudiostart: average=${average.toFixed(2)}, max=${maxLevel}`);
                    if (maxLevel > 0 || average > 0) {
                        console.log('✅✅✅ CONFIRMED: Microphone is receiving audio data! ✅✅✅');
                    } else {
                        console.warn('⚠️ WARNING: Audio levels are zero - microphone may not be capturing');
                    }
                }, 100);
            }
            
            // Mark as ready when audio capture actually starts
            // This is the most reliable indicator - when this fires, recognition is definitely ready
            if (!isRecognitionReady) {
                // Add a warm-up period - wait an additional 400ms after audio starts (reduced from 800ms)
                // This ensures the API is fully initialized and ready to process speech
                console.log('⏳ Warm-up period: Waiting 400ms for API to fully initialize...');
                
                setTimeout(() => {
                    isRecognitionReady = true;
                    window.recognitionReadyTime = Date.now(); // Track when we became ready
                    console.log('✅✅✅ Recognition is now READY (warm-up complete)! ✅✅✅');
                    console.log('✅✅✅ USER CAN NOW SPEAK - First utterance will be captured! ✅✅✅');
                    
                    // Final audio level check
                    if (analyser) {
                        const dataArray = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(dataArray);
                        const maxLevel = Math.max(...dataArray);
                        console.log(`🎤 Final audio level check before ready: max=${maxLevel}`);
                    }
                    
                    // Play a beep sound to indicate ready (using Web Audio API)
                    playReadyBeep();
                    
                    // Show prominent ready message
                    showStatusMessage('✅ READY! Say "yes" or "no" now.', 'success');
                    
                    // Clear the fallback timeout since we're ready now
                    if (window.recognitionReadyTimeout) {
                        clearTimeout(window.recognitionReadyTimeout);
                        window.recognitionReadyTimeout = null;
                    }
                }, 400); // 400ms warm-up period after audio capture starts (reduced for faster response)
            } else {
                console.log('Audio capture started but recognition was already marked as ready');
            }
        };
        
        recognition.onaudioend = () => {
            console.log('🎤 Audio capture ended');
            console.warn('⚠️ Audio capture ended - this might indicate recognition stopped prematurely');
            console.warn('If this happens right after you speak, it might be why onresult never fires');
        };
        
        recognition.onsoundstart = () => {
            console.log('🔊 Sound detected (speech may be starting)', 'isRecognitionReady:', isRecognitionReady);
            // If we detect sound but aren't ready yet, mark as ready as a backup
            // This can help catch cases where onaudiostart doesn't fire
            if (!isRecognitionReady) {
                console.warn('⚠️ Sound detected before recognition was marked ready - marking as ready now');
                console.log('✅✅✅ Recognition is now READY (sound detected)! ✅✅✅');
                isRecognitionReady = true;
                showStatusMessage('✅ Ready! Say "yes" or "no" now.', 'success');
                if (window.recognitionReadyTimeout) {
                    clearTimeout(window.recognitionReadyTimeout);
                    window.recognitionReadyTimeout = null;
                }
            }
        };
        
        recognition.onsoundend = () => {
            console.log('🔇 Sound ended');
        };
        
        recognition.onspeechstart = () => {
            console.log('🗣️ Speech detected!', 'isRecognitionReady:', isRecognitionReady);
            
            // Check audio levels when speech is detected
            if (analyser) {
                const dataArray = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(dataArray);
                const maxLevel = Math.max(...dataArray);
                const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
                console.log(`🎤 Audio levels when speech detected: average=${average.toFixed(2)}, max=${maxLevel}`);
                if (maxLevel > 30) {
                    console.log('✅✅✅ CONFIRMED: Strong audio signal detected! ✅✅✅');
                } else if (maxLevel > 0) {
                    console.log('⚠️ Low audio levels - may not be captured properly');
                } else {
                    console.error('❌❌❌ NO AUDIO DETECTED - microphone may not be capturing! ❌❌❌');
                }
            }
            
            if (!isRecognitionReady) {
                console.warn('⚠️ Speech detected but recognition may not be fully ready yet!');
            }
            // Note: onspeechstart is NOT reliable - it may not fire for short words like "yes" or "no"
            // We rely on onresult events instead, which are more reliable
        };
        
        recognition.onspeechend = () => {
            console.log('🗣️🗣️🗣️ Speech ended - this confirms speech WAS detected! 🗣️🗣️🗣️');
            console.log('In continuous mode, audio is buffered and will be processed when API is ready');
            console.log('We will wait a bit longer for results, then try to force them');
            
            // Track that speech ended - we'll use this to detect if onresult never fires
            let speechEndedTime = Date.now();
            window.speechEndedTime = speechEndedTime;
            window.speechEndedDetected = true; // Flag to track that speech was detected
            
            // In continuous mode, we need to wait longer for the API to process
            // The API buffers audio and processes it when ready
            
            // First attempt: Wait 2 seconds, then try to force results by stopping
            setTimeout(() => {
                if (!hasResult && !isProcessingAnswer && isListening) {
                    console.log('⚠️ 2 seconds passed after speech ended - attempting to force results...');
                    console.log('Stopping recognition to trigger onresult with buffered audio...');
                    try {
                        recognition.stop(); // This should trigger onresult with final results from buffer
                        console.log('Recognition stopped - onresult should fire with buffered audio...');
                    } catch (e) {
                        console.error('Error stopping recognition:', e);
                    }
                }
            }, 2000); // Wait 2 seconds - give API time to process buffered audio
            
            // Second attempt: Wait 4 seconds total, try restarting if still no results
            setTimeout(() => {
                if (!hasResult && !isProcessingAnswer && window.speechEndedTime === speechEndedTime) {
                    console.error('⚠️⚠️⚠️ 4 seconds passed - onresult never fired! ⚠️⚠️⚠️');
                    console.error('This indicates the Web Speech API is not returning results');
                    console.error('Attempting to restart recognition to process buffered audio...');
                    
                    // Try restarting recognition - sometimes this triggers processing of buffered audio
                    try {
                        if (isListening) {
                            recognition.stop();
                        }
                        setTimeout(() => {
                            console.log('Restarting recognition to try processing buffered audio...');
                            try {
                                recognition.start();
                                showStatusMessage('Restarting... Please speak again or use buttons.', 'info');
                            } catch (e) {
                                console.error('Error restarting recognition:', e);
                                showStatusMessage('Speech detected but API did not return results. Please use the Yes/No buttons.', 'error');
                            }
                        }, 500);
                    } catch (e) {
                        console.error('Error in recovery attempt:', e);
                        showStatusMessage('Speech detected but API did not return results. Please use the Yes/No buttons.', 'error');
                    }
                }
            }, 4000); // Wait 4 seconds total
        };
        
        recognition.onresult = (event) => {
            console.log('✅✅✅ onresult event FIRED! ✅✅✅');
            console.log('resultIndex:', event.resultIndex, 'results.length:', event.results.length);
            console.log('isRecognitionReady:', isRecognitionReady, 'isProcessingAnswer:', isProcessingAnswer);
            console.log('⚠️ NOTE: onresult is the PRIMARY way to detect speech - onspeechstart may not fire for short words!');
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
            
            // CRITICAL VAD FIX: Process ALL single words immediately, regardless of timing
            // This ensures the first "yes" is captured even if VAD hasn't fully activated
            // Check if this is a single word first
            let transcript = '';
            let isSingleWord = false;
            for (let i = event.results.length - 1; i >= 0; i--) {
                const result = event.results[i];
                if (result && result[0] && result[0].transcript) {
                    transcript = result[0].transcript.trim().toLowerCase();
                    isSingleWord = transcript === 'yes' || transcript === 'no';
                    if (isSingleWord) break;
                }
            }
            
            // If it's a single word, process it immediately - VAD fix
            if (isSingleWord) {
                console.log('✅✅✅ SINGLE WORD DETECTED - Processing immediately (VAD fix) ✅✅✅');
                console.log(`✅ Word: "${transcript}" - Capturing first word even if timing is early`);
                
                // Mark as ready if not already (for logging purposes)
                if (!isRecognitionReady) {
                    isRecognitionReady = true;
                    window.recognitionReadyTime = Date.now();
                    console.log('✅ Marking system as ready (single word detected)');
                }
                
                // Continue processing - don't block single words
            } else {
                // For non-single words, apply timing checks
                if (isRecognitionReady && window.recognitionReadyTime) {
                    const timeSinceReady = Date.now() - window.recognitionReadyTime;
                    if (timeSinceReady < 200) {
                        console.warn(`⚠️ Result received ${timeSinceReady}ms after ready - too soon, ignoring (warm-up protection)`);
                        return;
                    }
                }
                
                if (!isRecognitionReady) {
                    console.warn('⚠️ Got results before recognition was marked as ready - ignoring (not a single word)');
                    return;
                }
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
                    console.log('🎯 THIS IS THE FIRST WORD CAPTURED - Processing it now!');
                    // Clear speech ended time since we got results
                    window.speechEndedTime = null;
                } else {
                    currentInterim += trimmedTranscript + ' ';
                    console.log('📝 Interim result found:', trimmedTranscript);
                    console.log('🎯 INTERIM RESULT FOR FIRST WORD - Will process if no final result comes');
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
                    // Clear speech ended time since we got results
                    window.speechEndedTime = null;
                    
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
                    
                    // Wait 2 seconds for final result before processing interim phrase (reduced from 3)
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
                                // Clear speech ended time since we got results
                                window.speechEndedTime = null;
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
                    }, 2000); // Reduced to 2 seconds for faster processing
                }
            }
        };
        
        recognition.onerror = (event) => {
            // Clear health check interval
            if (window.recognitionHealthCheck) {
                clearInterval(window.recognitionHealthCheck);
                window.recognitionHealthCheck = null;
            }
            
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
                recognitionTimeout = null;
            }
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
                interimProcessTimeout = null;
            }
            
            console.error('❌❌❌ Speech recognition error:', event.error);
            console.error('Error details:', event);
            console.error('This error prevented speech recognition from working');
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
            // Clear health check interval
            if (window.recognitionHealthCheck) {
                clearInterval(window.recognitionHealthCheck);
                window.recognitionHealthCheck = null;
            }
            
            if (recognitionTimeout) {
                clearTimeout(recognitionTimeout);
                recognitionTimeout = null;
            }
            if (interimProcessTimeout) {
                clearTimeout(interimProcessTimeout);
                interimProcessTimeout = null;
            }
            
            console.log('🔴 Speech recognition ended');
            console.log('hasResult:', hasResult, 'isProcessingAnswer:', isProcessingAnswer);
            console.log('finalTranscript:', finalTranscript, 'interimTranscript:', interimTranscript);
            console.log('isRecognitionReady:', isRecognitionReady, 'isListening:', isListening);
            
            if (!hasResult && !isProcessingAnswer) {
                console.warn('⚠️ Recognition ended without capturing any speech!');
                console.warn('This could mean:');
                console.warn('  1. No speech was detected');
                console.warn('  2. onresult never fired (API issue)');
                console.warn('  3. Recognition stopped prematurely');
            }
            
            isListening = false;
            
            // If we're already processing an answer, don't do anything - let it complete
            if (isProcessingAnswer) {
                console.log('Recognition ended but answer is already being processed - ignoring');
                stopListening();
                return;
            }
            
            // If we got a result, it should have been processed already
            if (hasResult) {
                console.log('Recognition ended with result - answer should have been processed');
                stopListening();
                return;
            }
            
            // Only process interim transcript if we're not already processing and have no final result
            if (interimTranscript && !hasResult && !isProcessingAnswer) {
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
            window.currentSession = currentSession; // Make globally accessible
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
    
    // Request microphone permission and set up audio level monitoring
    // Note: Web Speech API handles its own microphone access, but we request permission
    // first to ensure the browser has granted it, and to monitor audio levels
    console.log('Requesting microphone access for monitoring...');
    try {
        // Release any existing stream first
        if (microphoneStream) {
            microphoneStream.getTracks().forEach(track => track.stop());
            microphoneStream = null;
        }
        
        // Stop any existing audio monitoring
        if (audioLevelCheckInterval) {
            clearInterval(audioLevelCheckInterval);
            audioLevelCheckInterval = null;
        }
        if (audioContext) {
            try {
                audioContext.close();
            } catch (e) {
                // Ignore errors when closing
            }
            audioContext = null;
        }
        
        // Request microphone access and keep it for monitoring
        microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('✅ Microphone permission granted');
        
        // CRITICAL: Wake up VAD (Voice Activity Detection) with a noise burst
        // This ensures the first word "yes" is captured immediately
        // Without this, VAD needs to detect sound first, causing the first word to be missed
        try {
            console.log('🔊 Generating VAD wake-up noise burst...');
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
        
        // Set up audio level monitoring
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(microphoneStream);
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            
            console.log('✅ Audio level monitoring started');
            
            // Monitor audio levels to confirm microphone is capturing
            let audioLevelCheckCount = 0;
            audioLevelCheckInterval = setInterval(() => {
                if (!analyser || !isListening) {
                    return;
                }
                
                const dataArray = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(dataArray);
                
                // Calculate average audio level
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) {
                    sum += dataArray[i];
                }
                const average = sum / dataArray.length;
                const maxLevel = Math.max(...dataArray);
                
                audioLevelCheckCount++;
                
                // Log audio levels every 5 checks (every 1 second)
                if (audioLevelCheckCount % 5 === 0) {
                    console.log(`🎤 Audio level check: average=${average.toFixed(2)}, max=${maxLevel}, isListening=${isListening}`);
                    
                    if (average > 10 || maxLevel > 20) {
                        console.log('✅✅✅ MICROPHONE IS CAPTURING AUDIO! ✅✅✅');
                        console.log(`   Average level: ${average.toFixed(2)}, Max level: ${maxLevel}`);
                    } else {
                        console.log('⚠️ Low audio levels - microphone may not be capturing properly');
                    }
                }
                
                // If we detect significant audio, log it immediately
                if (maxLevel > 30) {
                    console.log(`🔊🔊🔊 SIGNIFICANT AUDIO DETECTED! Level: ${maxLevel} 🔊🔊🔊`);
                }
            }, 200); // Check every 200ms
            
            console.log('✅ Audio monitoring active - will log levels every 1 second');
        } catch (monitoringError) {
            console.warn('Could not set up audio monitoring:', monitoringError);
            // Continue anyway - monitoring is optional
        }
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
        
        // CRITICAL: Start recognition EARLY to activate VAD and buffer audio
        // This "hot mic" approach ensures the first word is captured
        // We start recognition immediately, then wait for it to be ready
        console.log('Calling recognition.start() EARLY to activate VAD...');
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
            // Start recognition IMMEDIATELY - this activates VAD and starts buffering
            // The recognition will buffer audio even before we mark it as "ready"
            recognition.start();
            console.log('✅ recognition.start() called successfully (HOT MIC MODE)');
            console.log('⏳ Recognition is now ACTIVE and buffering audio...');
            console.log('⏳ VAD is being activated - first word will be captured!');
            console.log('⏳ Waiting for onstart event...');
            console.log('⏳ Then waiting for onaudiostart event (this confirms microphone is capturing)...');
            showStatusMessage('Initializing microphone... Please wait for "Ready" message before speaking.', 'info');
            
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
    window.isProcessingAnswer = true; // Update global reference
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
            // submitAnswer will reset isProcessingAnswer in its finally block
            await submitAnswer(cleanText, 'text');
        } catch (error) {
            console.error('Error in submitAnswer:', error);
            // submitAnswer's finally block will reset the flag, but reset here too for safety
            isProcessingAnswer = false;
            window.isProcessingAnswer = false; // Update global reference
            showStatusMessage('Error processing answer. Please try again.', 'error');
        }
    } else {
        console.log('Invalid text, resetting:', cleanText);
        showStatusMessage('Could not understand. Please try again or use buttons.', 'error');
        // Reset flag if we couldn't process - this allows user to try again
        isProcessingAnswer = false;
        window.isProcessingAnswer = false; // Update global reference
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
        window.isProcessingAnswer = false; // Update global reference
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
        
        // Create a timeout promise to prevent hanging requests
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Request timeout - server took too long to respond')), 30000); // 30 second timeout
        });
        
        const fetchPromise = fetch('/api/voice-bot/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSession.session_id,
                input: input,
                input_type: inputType
            })
        });
        
        const response = await Promise.race([fetchPromise, timeoutPromise]);
        
        console.log('Response status:', response.status);
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success && data.result) {
            const result = data.result;
            
            if (result.action === 'next') {
                currentSession.current_question = result.question_number - 1;
                currentSession.question_text = result.question_text;
                startQuestion(currentSession);
                showStatusMessage(`Answer saved: ${result.previous_answer}`, 'success');
            } else if (result.action === 'repeat') {
                // Question repeated, no change needed
                showStatusMessage('Question repeated', 'info');
            } else if (result.action === 'complete') {
                document.getElementById('questionDisplay').style.display = 'none';
                document.getElementById('completionMessage').style.display = 'block';
                document.getElementById('progressIndicator').style.display = 'none';
                currentSession = null;
                window.currentSession = null; // Update global reference
                showStatusMessage('All questions completed!', 'success');
            } else {
                // Unknown action
                console.warn('Unknown action in result:', result.action);
                showStatusMessage('Answer processed', 'info');
            }
        } else {
            const errorMsg = data.error || 'Error processing answer';
            console.error('API returned error:', errorMsg);
            showStatusMessage(errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error submitting answer:', error);
        showStatusMessage('Error submitting answer. Please try again.', 'error');
    } finally {
        // ALWAYS reset processing flag and re-enable buttons
        // This ensures the system can process the next answer even if something went wrong
        isProcessingAnswer = false;
        window.isProcessingAnswer = false; // Update global reference
        buttons.forEach(btn => btn.disabled = false);
        console.log('Processing flag reset, buttons re-enabled');
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

// Play a beep sound to indicate recognition is ready
function playReadyBeep() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800; // Higher pitch beep
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
        
        console.log('🔔 Ready beep played');
    } catch (error) {
        console.warn('Could not play beep sound:', error);
        // Fallback: visual flash
        const statusMsg = document.getElementById('statusMessage');
        if (statusMsg) {
            statusMsg.style.animation = 'pulse 0.5s ease-in-out 3';
        }
    }
}

// Show status message
function showStatusMessage(message, type) {
    const statusMessage = document.getElementById('statusMessage');
    if (!statusMessage) return;
    
    statusMessage.textContent = message;
    statusMessage.className = `status-message status-${type}`;
    statusMessage.style.display = 'block';
    
    // Don't auto-hide "Ready" messages - they should stay visible until user speaks
    if (message.includes('Ready!') || message.includes('✅ Ready') || message.includes('✅ READY')) {
        // Keep it visible - don't auto-hide
        return;
    }
    
    // Auto-hide after 3 seconds for other success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 3000);
    }
}



