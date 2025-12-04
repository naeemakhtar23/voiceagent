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
        showStatusMessage('Starting agent session...', 'info');
        
        const response = await fetch('/api/elevenlabs-agent/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            currentSession = data.session;
            showActiveSession(data.session);
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

// Poll for results (optional - can be replaced with webhooks)
setInterval(async () => {
    if (currentSession && currentSession.call_id) {
        try {
            const response = await fetch(`/api/calls/${currentSession.call_id}/results`);
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'completed') {
                    showResults(data.results);
                }
            }
        } catch (error) {
            // Ignore polling errors
        }
    }
}, 5000);

