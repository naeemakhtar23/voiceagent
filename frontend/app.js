// Professional Voice Call System - Frontend JavaScript

const API_BASE_URL = window.location.origin;

let questionCounter = 0;
let currentCallId = null;
let statusCheckInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Setup navigation
    setupNavigation();
    
    // Setup event listeners
    setupEventListeners();
    
    // Add first question
    addQuestion();
    
    // Load call history
    loadCallHistory();
}

// Navigation Setup
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.content-section');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all
            navItems.forEach(nav => nav.classList.remove('active'));
            sections.forEach(section => section.classList.remove('active'));
            
            // Add active class to clicked item
            item.classList.add('active');
            
            // Show corresponding section
            const sectionId = item.dataset.section;
            const targetSection = document.getElementById(`${sectionId}-section`);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });
}

// Setup Event Listeners
function setupEventListeners() {
    // Add question button
    const addQuestionBtn = document.getElementById('addQuestionBtn');
    if (addQuestionBtn) {
        addQuestionBtn.addEventListener('click', addQuestion);
    }
    
    // Call form submission
    const callForm = document.getElementById('callForm');
    if (callForm) {
        callForm.addEventListener('submit', (e) => {
            e.preventDefault();
            initiateCall();
        });
    }
    
    // ElevenLabs call button
    const elevenlabsCallButton = document.getElementById('elevenlabsCallButton');
    if (elevenlabsCallButton) {
        elevenlabsCallButton.addEventListener('click', (e) => {
            e.preventDefault();
            initiateElevenLabsCall();
        });
    }
    
    // Refresh history button
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', loadCallHistory);
    }
    
    // Copy JSON button
    const copyJsonBtn = document.getElementById('copyJsonBtn');
    if (copyJsonBtn) {
        copyJsonBtn.addEventListener('click', copyJsonToClipboard);
    }
}

// Add a new question input
function addQuestion() {
    questionCounter++;
    const questionsList = document.getElementById('questionsList');
    
    if (!questionsList) return;
    
    const questionDiv = document.createElement('div');
    questionDiv.className = 'question-item';
    questionDiv.id = `question-${questionCounter}`;
    
    questionDiv.innerHTML = `
        <span class="question-number">Q${questionCounter}</span>
        <input type="text" 
               value="Will the service be provided in the client’s home."
               placeholder="Enter your question (e.g., Do you have health insurance?)" 
               class="question-input"
               required>
        <button type="button" class="btn-remove" data-question-id="${questionCounter}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;
    
    
    questionsList.appendChild(questionDiv);

    const questionDiv2 = document.createElement('div');
    questionDiv2.className = 'question-item';
    questionDiv2.id = `question-${questionCounter+1}`;
    
    questionDiv2.innerHTML = `
        <span class="question-number">Q${questionCounter+1}</span>
        <input type="text" 
               value="Does the client use augmentative or assistive communication aids."
               placeholder="Enter your question (e.g., Do you have health insurance?)" 
               class="question-input"
               required>
        <button type="button" class="btn-remove" data-question-id="${questionCounter+1}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;
    
    
    questionsList.appendChild(questionDiv2);
    
    // Add remove button event listener
    const removeBtn = questionDiv.querySelector('.btn-remove');
    if (removeBtn) {
        removeBtn.addEventListener('click', () => {
            removeQuestion(questionCounter);
        });
    }
}

// Remove a question
function removeQuestion(id) {
    const questionDiv = document.getElementById(`question-${id}`);
    if (questionDiv) {
        questionDiv.remove();
    }
}

// Get all questions
function getQuestions() {
    const questionInputs = document.querySelectorAll('.question-input');
    const questions = [];
    
    questionInputs.forEach((input) => {
        const text = input.value.trim();
        if (text) {
            questions.push({
                text: text
            });
        }
    });
    
    return questions;
}

// Initiate a call
async function initiateCall() {
    const phoneNumber = document.getElementById('phoneNumber').value.trim();
    const questions = getQuestions();
    
    // Validation
    if (!phoneNumber) {
        showStatusMessage('Please enter a phone number', 'error');
        return;
    }
    
    if (!phoneNumber.startsWith('+')) {
        showStatusMessage('Phone number must include country code (e.g., +923001234567)', 'error');
        return;
    }
    
    if (questions.length === 0) {
        showStatusMessage('Please add at least one question', 'error');
        return;
    }
    
    // Disable button and show loading
    const callButton = document.getElementById('callButton');
    const buttonText = callButton.querySelector('span');
    callButton.disabled = true;
    if (buttonText) {
        buttonText.textContent = 'Initiating...';
    }
    
    showStatusMessage('Initiating call...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/initiate-call`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phone_number: phoneNumber,
                questions: questions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentCallId = data.call_id;
            
            // Check if demo mode
            if (data.demo_mode && data.results) {
                showStatusMessage(`Demo call completed! Call ID: ${data.call_id}`, 'success');
                document.getElementById('statusPanel').style.display = 'block';
                updateCallStatusDisplay({
                    id: data.call_id,
                    phone_number: phoneNumber,
                    status: 'completed',
                    started_at: new Date().toISOString(),
                    duration_seconds: data.results.duration_seconds || 45
                });
                // Display results immediately
                displayResults(data.results);
                loadCallHistory();
            } else {
                showStatusMessage(`Call initiated successfully! Call ID: ${data.call_id}`, 'success');
                document.getElementById('statusPanel').style.display = 'block';
                startStatusPolling(data.call_id);
            }
        } else {
            showStatusMessage(`Error: ${data.error}`, 'error');
            callButton.disabled = false;
            if (buttonText) {
                buttonText.textContent = 'Initiate Call';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showStatusMessage(`Error initiating call: ${error.message}`, 'error');
        callButton.disabled = false;
        if (buttonText) {
            buttonText.textContent = 'Initiate Call';
        }
    }
}

// Initiate an ElevenLabs call
async function initiateElevenLabsCall() {
    const phoneNumber = document.getElementById('phoneNumber').value.trim();
    const questions = getQuestions();
    
    // Validation
    if (!phoneNumber) {
        showStatusMessage('Please enter a phone number', 'error');
        return;
    }
    
    if (!phoneNumber.startsWith('+')) {
        showStatusMessage('Phone number must include country code (e.g., +923001234567)', 'error');
        return;
    }
    
    if (questions.length === 0) {
        showStatusMessage('Please add at least one question', 'error');
        return;
    }
    
    // Disable button and show loading
    const callButton = document.getElementById('elevenlabsCallButton');
    const buttonText = callButton.querySelector('span');
    callButton.disabled = true;
    if (buttonText) {
        buttonText.textContent = 'Initiating...';
    }
    
    showStatusMessage('Initiating ElevenLabs call...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/initiate-elevenlabs-call`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phone_number: phoneNumber,
                questions: questions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentCallId = data.call_id;
            showStatusMessage(`ElevenLabs call initiated successfully! Call ID: ${data.call_id}`, 'success');
            document.getElementById('statusPanel').style.display = 'block';
            startStatusPolling(data.call_id);
        } else {
            showStatusMessage(`Error: ${data.error}`, 'error');
            callButton.disabled = false;
            if (buttonText) {
                buttonText.textContent = 'ElevenLabs Call';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showStatusMessage(`Error initiating ElevenLabs call: ${error.message}`, 'error');
        callButton.disabled = false;
        if (buttonText) {
            buttonText.textContent = 'ElevenLabs Call';
        }
    }
}

// Start polling for call status
function startStatusPolling(callId) {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    statusCheckInterval = setInterval(() => {
        checkCallStatus(callId);
    }, 3000);
    
    checkCallStatus(callId);
}

// Check call status
async function checkCallStatus(callId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/call/${callId}`);
        const callData = await response.json();
        
        if (callData.error) {
            console.error('Error fetching call status:', callData.error);
            return;
        }
        
        updateCallStatusDisplay(callData);
        
        if (callData.status === 'completed' || callData.status === 'busy' || callData.status === 'no-answer' || callData.status === 'failed') {
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
            }
            
            setTimeout(() => {
                fetchCallResults(callId);
            }, 2000);
            
            const callButton = document.getElementById('callButton');
            const buttonText = callButton.querySelector('span');
            callButton.disabled = false;
            if (buttonText) {
                buttonText.textContent = 'Initiate Call';
            }
        }
    } catch (error) {
        console.error('Error checking call status:', error);
    }
}

// Update call status display
function updateCallStatusDisplay(callData) {
    const statusPanel = document.getElementById('currentCallStatus');
    if (!statusPanel) return;
    
    const statusBadgeClass = callData.status.replace(' ', '-').toLowerCase();
    
    statusPanel.innerHTML = `
        <div class="status-item">
            <label>Call ID</label>
            <value>${callData.id}</value>
        </div>
        <div class="status-item">
            <label>Phone Number</label>
            <value>${callData.phone_number}</value>
        </div>
        <div class="status-item">
            <label>Status</label>
            <value><span class="status-badge ${statusBadgeClass}">${callData.status}</span></value>
        </div>
        ${callData.started_at ? `
        <div class="status-item">
            <label>Started</label>
            <value>${new Date(callData.started_at).toLocaleString()}</value>
        </div>
        ` : ''}
        ${callData.duration_seconds ? `
        <div class="status-item">
            <label>Duration</label>
            <value>${callData.duration_seconds}s</value>
        </div>
        ` : ''}
    `;
}

// Fetch call results
async function fetchCallResults(callId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/call-results/${callId}`);
        const results = await response.json();
        
        if (results.error) {
            document.getElementById('jsonResults').textContent = `Error: ${results.error}`;
            return;
        }
        
        displayResults(results);
        loadCallHistory();
    } catch (error) {
        console.error('Error fetching call results:', error);
        document.getElementById('jsonResults').textContent = `Error fetching results: ${error.message}`;
    }
}

// Display results
function displayResults(results) {
    // Display JSON
    const jsonResults = document.getElementById('jsonResults');
    if (jsonResults) {
        jsonResults.textContent = JSON.stringify(results, null, 2);
    }
    
    // Update summary
    const callStatus = document.getElementById('callStatus');
    if (callStatus && results.summary) {
        callStatus.innerHTML = `
            <div class="summary-card">
                <label>Total Questions</label>
                <value>${results.summary.total_questions}</value>
            </div>
            <div class="summary-card">
                <label>Yes Answers</label>
                <value>${results.summary.yes_count}</value>
            </div>
            <div class="summary-card">
                <label>No Answers</label>
                <value>${results.summary.no_count}</value>
            </div>
            ${results.summary.unclear_count > 0 ? `
            <div class="summary-card">
                <label>Unclear</label>
                <value>${results.summary.unclear_count}</value>
            </div>
            ` : ''}
        `;
    }
    
    // Switch to results section
    const resultsNav = document.querySelector('[data-section="results"]');
    if (resultsNav) {
        resultsNav.click();
    }
}

// Load call history
async function loadCallHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/calls`);
        const calls = await response.json();
        
        const tbody = document.getElementById('callsBody');
        if (!tbody) return;
        
        if (calls.length === 0 || calls.error) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                        </svg>
                        <p>No calls yet</p>
                        <span>Make your first call to see history here</span>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = calls.map(call => {
            const statusBadgeClass = call.status.replace(' ', '-').toLowerCase();
            const startedAt = call.started_at ? new Date(call.started_at).toLocaleString() : 'N/A';
            const duration = call.duration_seconds ? `${call.duration_seconds}s` : 'N/A';
            
            return `
                <tr>
                    <td>${call.id}</td>
                    <td>${call.phone_number}</td>
                    <td><span class="status-badge ${statusBadgeClass}">${call.status}</span></td>
                    <td>${duration}</td>
                    <td>${startedAt}</td>
                    <td>
                        <button class="btn-icon-small" onclick="viewCallResults(${call.id})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                            View
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading call history:', error);
        const tbody = document.getElementById('callsBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <p>Error loading call history</p>
                    </td>
                </tr>
            `;
        }
    }
}

// View call results
async function viewCallResults(callId) {
    await fetchCallResults(callId);
}

// Copy JSON to clipboard
function copyJsonToClipboard() {
    const jsonResults = document.getElementById('jsonResults');
    if (jsonResults) {
        navigator.clipboard.writeText(jsonResults.textContent).then(() => {
            const btn = document.getElementById('copyJsonBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!';
            setTimeout(() => {
                btn.innerHTML = originalText;
            }, 2000);
        });
    }
}

// Show status message
function showStatusMessage(message, type) {
    const statusDiv = document.getElementById('callStatusMessage');
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusDiv.textContent = '';
            statusDiv.className = 'status-message';
        }, 5000);
    }
}

// Make viewCallResults globally accessible for onclick handlers
window.viewCallResults = viewCallResults;
