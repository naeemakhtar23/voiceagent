// OCR System - Frontend JavaScript

const API_BASE_URL = window.location.origin;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeOCRApp();
});

function initializeOCRApp() {
    // Setup navigation
    setupNavigation();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load document results
    loadDocumentResults();
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
    // Upload form submission
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            uploadDocument();
        });
    }
    
    // PaddleOCR upload button
    const paddleocrUploadButton = document.getElementById('paddleocrUploadButton');
    if (paddleocrUploadButton) {
        paddleocrUploadButton.addEventListener('click', (e) => {
            e.preventDefault();
            uploadDocumentPaddleOCR();
        });
    }
    
    // Refresh results button
    const refreshResultsBtn = document.getElementById('refreshResultsBtn');
    if (refreshResultsBtn) {
        refreshResultsBtn.addEventListener('click', loadDocumentResults);
    }
    
    // Close details button
    const closeDetailsBtn = document.getElementById('closeDetailsBtn');
    if (closeDetailsBtn) {
        closeDetailsBtn.addEventListener('click', () => {
            document.getElementById('documentDetailsCard').style.display = 'none';
        });
    }
}

// Upload document with PaddleOCR
async function uploadDocumentPaddleOCR() {
    const fileInput = document.getElementById('documentFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatusMessage('Please select a file', 'error');
        return;
    }
    
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
        showStatusMessage('Invalid file type. Please upload PDF, PNG, or JPG files', 'error');
        return;
    }
    
    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showStatusMessage('File size exceeds 10MB limit', 'error');
        return;
    }
    
    // Disable button and show loading
    const uploadButton = document.getElementById('paddleocrUploadButton');
    const buttonText = uploadButton.querySelector('span');
    uploadButton.disabled = true;
    if (buttonText) {
        buttonText.textContent = 'Processing with PaddleOCR...';
    }
    
    showStatusMessage('Uploading document for PaddleOCR processing...', 'info');
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/ocr/paddleocr-upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `Server error: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, use status text
                errorMessage = response.statusText || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showStatusMessage(`Document uploaded successfully with PaddleOCR! Document ID: ${data.document_id}`, 'success');
            document.getElementById('processingPanel').style.display = 'block';
            updateProcessingStatus({
                id: data.document_id,
                file_name: file.name,
                status: 'processing',
                created_at: new Date().toISOString()
            });
            
            // Poll for processing status
            startProcessingPolling(data.document_id);
            
            // Reset form
            fileInput.value = '';
        } else {
            showStatusMessage(`Error: ${data.error}`, 'error');
            uploadButton.disabled = false;
            if (buttonText) {
                buttonText.textContent = 'Upload & Process (PaddleOCR)';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showStatusMessage(`Error uploading document: ${error.message}`, 'error');
        uploadButton.disabled = false;
        if (buttonText) {
            buttonText.textContent = 'Upload & Process (PaddleOCR)';
        }
    }
}

// Upload document
async function uploadDocument() {
    const fileInput = document.getElementById('documentFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatusMessage('Please select a file', 'error');
        return;
    }
    
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
        showStatusMessage('Invalid file type. Please upload PDF, PNG, or JPG files', 'error');
        return;
    }
    
    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showStatusMessage('File size exceeds 10MB limit', 'error');
        return;
    }
    
    // Disable button and show loading
    const uploadButton = document.getElementById('uploadButton');
    const buttonText = uploadButton.querySelector('span');
    uploadButton.disabled = true;
    if (buttonText) {
        buttonText.textContent = 'Uploading...';
    }
    
    showStatusMessage('Uploading document...', 'info');
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/ocr/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStatusMessage(`Document uploaded successfully! Document ID: ${data.document_id}`, 'success');
            document.getElementById('processingPanel').style.display = 'block';
            updateProcessingStatus({
                id: data.document_id,
                file_name: file.name,
                status: 'processing',
                created_at: new Date().toISOString()
            });
            
            // Poll for processing status
            startProcessingPolling(data.document_id);
            
            // Reset form
            fileInput.value = '';
        } else {
            showStatusMessage(`Error: ${data.error}`, 'error');
            uploadButton.disabled = false;
            if (buttonText) {
                buttonText.textContent = 'Upload & Process';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showStatusMessage(`Error uploading document: ${error.message}`, 'error');
        uploadButton.disabled = false;
        if (buttonText) {
            buttonText.textContent = 'Upload & Process';
        }
    }
}

// Start polling for processing status
let processingCheckInterval = null;

function startProcessingPolling(documentId) {
    if (processingCheckInterval) {
        clearInterval(processingCheckInterval);
    }
    
    processingCheckInterval = setInterval(() => {
        checkProcessingStatus(documentId);
    }, 3000);
    
    checkProcessingStatus(documentId);
}

// Check processing status
async function checkProcessingStatus(documentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ocr/document/${documentId}`);
        const documentData = await response.json();
        
        if (documentData.error) {
            console.error('Error fetching document status:', documentData.error);
            return;
        }
        
        updateProcessingStatus(documentData);
        
        if (documentData.status === 'completed' || documentData.status === 'error') {
            if (processingCheckInterval) {
                clearInterval(processingCheckInterval);
                processingCheckInterval = null;
            }
            
            const uploadButton = document.getElementById('uploadButton');
            const buttonText = uploadButton.querySelector('span');
            uploadButton.disabled = false;
            if (buttonText) {
                buttonText.textContent = 'Upload & Process';
            }
            
            // Reload results
            loadDocumentResults();
        }
    } catch (error) {
        console.error('Error checking processing status:', error);
    }
}

// Update processing status display
function updateProcessingStatus(documentData) {
    const processingPanel = document.getElementById('processingStatus');
    if (!processingPanel) return;
    
    const statusBadgeClass = documentData.status.replace(' ', '-').toLowerCase();
    
    processingPanel.innerHTML = `
        <div class="status-item">
            <label>Document ID</label>
            <value>${documentData.id}</value>
        </div>
        <div class="status-item">
            <label>File Name</label>
            <value>${documentData.file_name || 'N/A'}</value>
        </div>
        <div class="status-item">
            <label>Status</label>
            <value><span class="status-badge ${statusBadgeClass}">${documentData.status}</span></value>
        </div>
        ${documentData.created_at ? `
        <div class="status-item">
            <label>Created</label>
            <value>${new Date(documentData.created_at).toLocaleString()}</value>
        </div>
        ` : ''}
    `;
}

// Load document results
async function loadDocumentResults() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ocr/documents`);
        const documents = await response.json();
        
        const tbody = document.getElementById('documentsBody');
        if (!tbody) return;
        
        if (documents.length === 0 || documents.error) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <p>No documents yet</p>
                        <span>Upload your first document to see results here</span>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = documents.map(doc => {
            const statusBadgeClass = doc.status.replace(' ', '-').toLowerCase();
            const createdAt = doc.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A';
            
            return `
                <tr>
                    <td>${doc.id}</td>
                    <td>${doc.file_name || 'N/A'}</td>
                    <td><span class="status-badge ${statusBadgeClass}">${doc.status}</span></td>
                    <td>${createdAt}</td>
                    <td>
                        <button class="btn-icon-small" onclick="viewDocumentDetails(${doc.id})">
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
        console.error('Error loading document results:', error);
        const tbody = document.getElementById('documentsBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <p>Error loading document results</p>
                    </td>
                </tr>
            `;
        }
    }
}

// View document details
async function viewDocumentDetails(documentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/ocr/document/${documentId}`);
        const documentData = await response.json();
        
        if (documentData.error) {
            showStatusMessage(`Error: ${documentData.error}`, 'error');
            return;
        }
        
        // Display document details
        const detailsCard = document.getElementById('documentDetailsCard');
        const detailsContent = document.getElementById('documentDetailsContent');
        
        detailsContent.innerHTML = `
            <div class="form-group">
                <label>Document ID</label>
                <div class="input-wrapper">
                    <input type="text" value="${documentData.id}" readonly>
                </div>
            </div>
            
            <div class="form-group">
                <label>File Name</label>
                <div class="input-wrapper">
                    <input type="text" value="${documentData.file_name || 'N/A'}" readonly>
                </div>
            </div>
            
            <div class="form-group">
                <label>Status</label>
                <div class="input-wrapper">
                    <input type="text" value="${documentData.status}" readonly>
                </div>
            </div>
            
            <div class="form-group">
                <label>Document Text</label>
                <textarea class="json-display" style="min-height: 400px; font-family: monospace; white-space: pre-wrap;width: 100%;" readonly>${documentData.document_text || 'No text extracted yet'}</textarea>
            </div>
            
            <div class="form-group">
                <label>Extracted Data</label>
                <pre class="json-display">${documentData.ExtractedData ? JSON.stringify(JSON.parse(documentData.ExtractedData), null, 2) : 'No extracted data yet'}</pre>
            </div>
            
            <div class="form-group">
                <label>Parameters List</label>
                <pre class="json-display">${documentData.ParametersList ? JSON.stringify(JSON.parse(documentData.ParametersList), null, 2) : 'No parameters extracted yet'}</pre>
            </div>
            
            <div class="form-group">
                <label>Refined Document Text</label>
                <textarea class="json-display" style="min-height: 400px; font-family: monospace; white-space: pre-wrap;width: 100%;" readonly>${documentData.RefinedDocumentText || 'No refined text yet'}</textarea>
            </div>
        `;
        
        detailsCard.style.display = 'block';
        
        // Switch to results section
        const resultsNav = document.querySelector('[data-section="results"]');
        if (resultsNav) {
            resultsNav.click();
        }
        
        // Scroll to details
        detailsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (error) {
        console.error('Error fetching document details:', error);
        showStatusMessage(`Error fetching document details: ${error.message}`, 'error');
    }
}

// Show status message
function showStatusMessage(message, type) {
    const statusDiv = document.getElementById('uploadStatusMessage');
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

// Make viewDocumentDetails globally accessible for onclick handlers
window.viewDocumentDetails = viewDocumentDetails;


