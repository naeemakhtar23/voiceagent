// ElevenLabs Voice Agent Frontend
let currentSession = null;

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    const startBtn = document.getElementById('startAgentSessionBtn');
    const endBtn = document.getElementById('endSessionBtn');
    const viewResultsBtn = document.getElementById('viewResultsBtn');
    
    if (startBtn) {
        startBtn.addEventListener('click', startAgentSession);
    }
    if (endBtn) {
        endBtn.addEventListener('click', endAgentSession);
    }
    if (viewResultsBtn) {
        viewResultsBtn.addEventListener('click', () => {
            if (currentSession && currentSession.call_id) {
                window.location.href = `/results?call_id=${currentSession.call_id}`;
            }
        });
    }
}

async function startAgentSession() {
    try {
        // Stop any existing polling
        stopPolling();
        
        // Clear any previous results
        const formResults = document.getElementById('formResults');
        if (formResults) {
            formResults.innerHTML = '<p>Results will appear here when the form is submitted.</p>';
        }
        
        showStatusMessage('Starting agent session...', 'info');
        
        const response = await fetch('/api/elevenlabs-agent/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}) // Send empty JSON object instead of no body
        });
        
        const data = await response.json();
        if (data.success) {
            currentSession = data.session;
            
            // If agent_id is not in session, fetch it from config
            if (!currentSession.agent_id) {
                try {
                    const configResponse = await fetch('/api/elevenlabs-agent/config');
                    const configData = await configResponse.json();
                    if (configData.success && configData.agent_id) {
                        currentSession.agent_id = configData.agent_id;
                    }
                } catch (configError) {
                    console.warn('Could not fetch agent_id from config:', configError);
                }
            }
            
            showActiveSession(currentSession);
            showStatusMessage('Agent session started. The agent will now ask questions.', 'success');
        } else {
            showStatusMessage(data.error || 'Failed to start session', 'error');
        }
    } catch (error) {
        console.error('Error starting session:', error);
        showStatusMessage('Error starting session. Please try again.', 'error');
    }
}

function showActiveSession(session) {
    document.getElementById('startSession').style.display = 'none';
    document.getElementById('activeSession').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    
    const sessionInfo = document.getElementById('sessionInfo');
    sessionInfo.innerHTML = `
        <div class="info-item" style="margin-bottom: 10px;">
            <strong>Session ID:</strong> ${session.session_id}
        </div>
        <div class="info-item" style="margin-bottom: 10px;">
            <strong>Call ID:</strong> ${session.call_id}
        </div>
        <div class="info-item" style="margin-bottom: 10px;">
            <strong>Total Questions:</strong> ${session.total_questions}
        </div>
        <div class="info-item" style="margin-bottom: 10px;">
            <strong>Status:</strong> <span class="status-badge" style="display: inline-block; padding: 4px 12px; background: #10b981; color: white; border-radius: 4px; font-size: 0.85em;">Active</span>
        </div>
    `;
    
    // Load ElevenLabs widget with agent ID and session data (including questions)
    loadAgentWidget(session.agent_id, session);
    
    // Start polling for results (only for this new session)
    startPolling();
}

function loadAgentWidget(agentId, session = null) {
    const widgetContainer = document.getElementById('widgetContainer');
    
    // Fallback to default agent ID if not provided
    if (!agentId) {
        // Use the agent ID from the widget code you provided, or try to fetch from config
        agentId = 'agent_8701kbq27cvjew5rh7t67v6y6bsp'; // Default fallback
        
        // Try to fetch from config asynchronously
        fetch('/api/elevenlabs-agent/config')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.agent_id) {
                    agentId = data.agent_id;
                    createWidgetElement(agentId, session);
                } else {
                    createWidgetElement(agentId, session); // Use fallback
                }
            })
            .catch(() => {
                createWidgetElement(agentId, session); // Use fallback on error
            });
    } else {
        createWidgetElement(agentId, session);
    }
}

function createWidgetElement(agentId, session = null) {
    const widgetContainer = document.getElementById('widgetContainer');
    
    if (!agentId) {
        widgetContainer.innerHTML = '<p style="color: #ef4444;">Agent ID not available. Please check your configuration.</p>';
        return;
    }
    
    // Clear any existing widget
    widgetContainer.innerHTML = '';
    
    // Create the widget element
    const widgetElement = document.createElement('elevenlabs-convai');
    widgetElement.setAttribute('agent-id', agentId);
    
    // Prepare conversation initiation client data with questions
    let client_data = null;
    let override_prompt_text = null;
    let override_first_message_text = null;
    
    if (session && session.questions) {
        // Format questions similar to how it's done in initiate_call
        const questions_list = session.questions.map(q => ({ text: typeof q === 'string' ? q : q.text || q }));
        const questions_text = questions_list.map((q, i) => `Question ${i+1}: ${q.text}`).join('\n');
        const conversation_context = `You are conducting a survey call. Ask the following questions one by one and wait for yes/no answers:
            
${questions_text}

After each answer, acknowledge it and move to the next question. When all questions are answered, thank the caller and end the call.`;
        
        // Format for ElevenLabs widget - PRIORITIZE dynamic_variables (recommended by ElevenLabs)
        // NOTE: override_first_message requires "First message" override to be enabled in agent settings
        // Go to ElevenLabs dashboard > Agent Settings > Security > Enable "First message" override
        
        const first_question = questions_list[0]?.text || '';
        
        // PRIMARY METHOD: Use dynamic_variables (recommended by ElevenLabs, works without enabling overrides)
        // This is the preferred method as it doesn't require enabling overrides in agent settings
        client_data = {
            // Dynamic variables (PRIMARY METHOD - works without enabling overrides)
            dynamic_variables: {
                call_id: String(session.call_id),
                questions: JSON.stringify(questions_list),  // Array of objects with 'text' field
                questions_text: questions_text,  // Formatted text with all questions
                conversation_context: conversation_context,
                total_questions: String(questions_list.length),
                first_question: first_question,  // First question text for immediate use
                question_list: JSON.stringify(questions_list.map(q => q.text))  // Simple array of question texts (easiest to parse)
            },
            // Override methods (SECONDARY - requires enabling overrides in agent settings)
            // To enable: ElevenLabs Dashboard > Agent Settings > Security > Enable "First message" override
            override_prompt: `You are conducting a healthcare survey. You MUST ask the following questions one by one and wait for yes/no answers:

${questions_text}

Instructions:
- Ask each question clearly, one at a time
- Wait for the user's response (yes/no)
- Extract yes/no answers (yes, yeah, yep, correct, no, nope, nah, incorrect, etc.)
- After each answer, acknowledge it briefly and move to the next question
- Once ALL questions are answered, Use the submit_form tool
- Pass a single parameter answers, an array of objects with question_number, question_text, and answer_bool/answer_text.
- You MUST include all questions
- Do NOT ask the user to provide questions - they are listed above
- Start asking the questions immediately after greeting the user`,
            override_first_message: first_question 
                ? `Hello! I'm conducting a healthcare survey. ${first_question} Please answer yes or no.`
                : 'Hello! I\'m conducting a healthcare survey. Let me start with the first question.',
            // Also include at root level for backward compatibility
            call_id: String(session.call_id),
            questions: questions_list,
            questions_text: questions_text,
            conversation_context: conversation_context
        };
        
        // Store override texts for HTML attributes (these work even if overrides aren't enabled in some cases)
        override_prompt_text = client_data.override_prompt;
        override_first_message_text = client_data.override_first_message;
        
        // Set the conversation-initiation-client-data attribute
        // The widget expects this as a JSON string
        widgetElement.setAttribute('conversation-initiation-client-data', JSON.stringify(client_data));
        
        console.log('Passing questions to widget:', {
            total_questions: questions_list.length,
            questions_text: questions_text.substring(0, 100) + '...',
            client_data: client_data
        });
        
        // Log dynamic variables specifically (primary method)
        if (client_data.dynamic_variables) {
            console.log('Dynamic variables (PRIMARY METHOD):', {
                first_question: client_data.dynamic_variables.first_question,
                question_list: client_data.dynamic_variables.question_list,
                total_questions: client_data.dynamic_variables.total_questions
            });
        }
        
        // Log override methods (requires enabling in agent settings)
        if (client_data.override_first_message) {
            console.log('Override first message (requires enabling in agent settings):', 
                client_data.override_first_message.substring(0, 100) + '...');
            console.warn('⚠️ NOTE: override_first_message requires "First message" override to be enabled in:');
            console.warn('   ElevenLabs Dashboard > Agent Settings > Security > Enable "First message" override');
        }
    }
    
    // Add some styling
    widgetElement.style.width = '100%';
    widgetElement.style.minHeight = '400px';
    widgetElement.style.display = 'block';
    
    // IMPORTANT: Set the attributes BEFORE appending to DOM
    // This ensures the widget reads them during initialization
    if (client_data) {
        widgetElement.setAttribute('conversation-initiation-client-data', JSON.stringify(client_data));
        console.log('✅ Set conversation-initiation-client-data attribute');
    }
    
    // Also set override-prompt and override-first-message as HTML attributes
    // These might work even if overrides aren't enabled in security settings
    if (override_prompt_text) {
        widgetElement.setAttribute('override-prompt', override_prompt_text);
        console.log('✅ Set override-prompt attribute');
    }
    
    if (override_first_message_text) {
        widgetElement.setAttribute('override-first-message', override_first_message_text);
        console.log('✅ Set override-first-message attribute');
    }
    
    widgetContainer.appendChild(widgetElement);
    
    // Wait for the script to load and use JavaScript API to set client data
    const setupWidget = () => {
        if (!client_data) {
            console.warn('No client data to pass to widget');
            return;
        }
        
        // Method 1: Try to use the widget's JavaScript API if available
        if (widgetElement && typeof widgetElement.startConversation === 'function') {
            try {
                widgetElement.startConversation({
                    conversationInitiationClientData: client_data
                });
                console.log('✅ Started conversation with client data via JavaScript API');
                return;
            } catch (error) {
                console.warn('Could not use JavaScript API startConversation:', error);
            }
        }
        
        // Method 2: Try to set the attribute again (in case widget reinitialized)
        try {
            widgetElement.setAttribute('conversation-initiation-client-data', JSON.stringify(client_data));
            console.log('✅ Set conversation-initiation-client-data attribute (retry)');
        } catch (error) {
            console.warn('Could not set attribute:', error);
        }
        
        // Method 3: Try accessing the widget's internal API
        if (widgetElement && widgetElement.conversationInitiationClientData !== undefined) {
            try {
                widgetElement.conversationInitiationClientData = client_data;
                console.log('✅ Set conversationInitiationClientData property');
            } catch (error) {
                console.warn('Could not set conversationInitiationClientData property:', error);
            }
        }
    };
    
    // Wait for the script to load if it hasn't already
    if (typeof window.ElevenLabsConvAI === 'undefined') {
        // Script is loading asynchronously, wait for it
        const checkScript = setInterval(() => {
            if (typeof window.ElevenLabsConvAI !== 'undefined' || document.querySelector('script[src*="convai-widget-embed"]')) {
                clearInterval(checkScript);
                console.log('ElevenLabs widget script loaded');
                // Try to setup widget after script loads (wait a bit longer for full initialization)
                setTimeout(setupWidget, 1000);
            }
        }, 100);
        
        // Timeout after 5 seconds
        setTimeout(() => {
            clearInterval(checkScript);
            setupWidget(); // Try setup anyway
        }, 5000);
    } else {
        // Script already loaded, setup immediately (but wait a bit for widget to be ready)
        setTimeout(setupWidget, 1000);
    }
    
    // Also listen for widget events to ensure data is passed when conversation starts
    widgetElement.addEventListener('conversation-started', () => {
        console.log('Conversation started event detected');
        if (client_data) {
            // Try to pass data again when conversation actually starts
            setupWidget();
        }
    });
    
    console.log(`ElevenLabs widget loaded with agent ID: ${agentId}${session && session.questions ? ` and ${session.questions.length} questions` : ''}`);
}

function showResults(results) {
    document.getElementById('activeSession').style.display = 'none';
    document.getElementById('results').style.display = 'block';
    
    const formResults = document.getElementById('formResults');
    if (results && results.questions) {
        let html = '<h3>Form Answers:</h3><ul style="line-height: 2;">';
        results.questions.forEach(q => {
            const answerClass = q.answer === 'yes' ? 'color: #10b981;' : q.answer === 'no' ? 'color: #ef4444;' : '';
            html += `<li style="margin-bottom: 15px;"><strong>Q${q.question_number}:</strong> ${q.question}<br><strong style="${answerClass}">Answer:</strong> ${q.answer}</li>`;
        });
        html += '</ul>';
        formResults.innerHTML = html;
    } else {
        formResults.innerHTML = '<p>Results will appear here when the form is submitted.</p>';
    }
}

async function endAgentSession() {
    if (!currentSession) return;
    
    // Stop polling when ending session
    stopPolling();
    
    try {
        const response = await fetch(`/api/elevenlabs-agent/end/${currentSession.session_id}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            currentSession = null;
            document.getElementById('startSession').style.display = 'block';
            document.getElementById('activeSession').style.display = 'none';
            showStatusMessage('Session ended', 'success');
        }
    } catch (error) {
        console.error('Error ending session:', error);
    }
}

function showStatusMessage(message, type) {
    const statusMsg = document.getElementById('statusMessage');
    if (statusMsg) {
        statusMsg.textContent = message;
        statusMsg.className = `status-message status-${type}`;
        statusMsg.style.display = 'block';
        
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                statusMsg.style.display = 'none';
            }, 5000);
        }
    }
}

// Poll for results (only when session is active)
let pollingInterval = null;

function startPolling() {
    // Clear any existing polling interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    // Only poll if we have an active session
    if (!currentSession || !currentSession.call_id) {
        return;
    }
    
    // Poll immediately first time, then every 3 seconds (more responsive)
    checkForResults();
    
    pollingInterval = setInterval(checkForResults, 3000);
}

function checkForResults() {
    // Check if session is still active
    if (!currentSession || !currentSession.call_id) {
        stopPolling();
        return;
    }
    
    fetch(`/api/calls/${currentSession.call_id}/results`)
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Response not OK');
        })
        .then(data => {
            // Only show results if status is 'completed' and we have actual results
            if (data.status === 'completed' && data.results && data.results.questions) {
                // Check if we have actual answers (not just empty results)
                const hasAnswers = data.results.questions.some(q => q.answer && q.answer !== 'unclear');
                if (hasAnswers) {
                    stopPolling(); // Stop polling once we have results
                    // Stop the session
                    currentSession = null;
                    // Show results
                    showResults(data.results);
                    // Show success message
                    showStatusMessage('Call completed. Results are shown below.', 'success');
                }
            } else if (data.status === 'not_found' || data.status === 'error') {
                // Call not found or error - stop polling
                stopPolling();
            }
            // If status is 'in_progress', continue polling
        })
        .catch(error => {
            // Ignore polling errors - continue polling
            console.debug('Polling error (ignored):', error);
        });
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

