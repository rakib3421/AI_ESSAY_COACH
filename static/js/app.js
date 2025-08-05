// Main JavaScript for AI Essay Revision Application

// Global variables
let currentEssayId = null;
let suggestionModal = null;
let currentAnalysis = null;
let acceptedSuggestions = [];
let acceptedWordSuggestions = new Set();
let rejectedWordSuggestions = new Set();
let currentWordSuggestionId = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApplication();
});

function initializeApplication() {
    // Initialize Bootstrap components
    initializeBootstrap();
    
    // Initialize file upload
    initializeFileUpload();
    
    // Initialize essay suggestions
    initializeSuggestions();
    
    // Initialize analysis form
    initializeAnalysisForm();
    
    // Initialize charts if present
    if (typeof Chart !== 'undefined') {
        initializeCharts();
    }
    
    // Initialize tooltips
    initializeTooltips();
}

function initializeBootstrap() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize modal
    const modalElement = document.getElementById('suggestionModal');
    if (modalElement) {
        suggestionModal = new bootstrap.Modal(modalElement);
    }
}

function initializeFileUpload() {
    const fileInput = document.getElementById('file');
    if (!fileInput) return;
    
    const uploadArea = document.createElement('div');
    uploadArea.className = 'file-upload-area mt-2';
    uploadArea.innerHTML = `
        <i class="fas fa-cloud-upload-alt fa-3x mb-3" style="color: #1e2839;"></i>
        <p class="mb-2">Drag and drop your .docx file here or click to browse</p>
        <small class="text-muted">Maximum file size: 16MB</small>
    `;
    
    // Insert after file input
    fileInput.parentNode.insertBefore(uploadArea, fileInput.nextSibling);
    
    // Hide original file input
    fileInput.style.display = 'none';
    
    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // Drag and drop functionality
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.name.endsWith('.docx')) {
                fileInput.files = files;
                updateUploadArea(file.name);
            } else {
                showAlert('Please select a .docx file', 'error');
            }
        }
    });
    
    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            updateUploadArea(this.files[0].name);
        }
    });
    
    function updateUploadArea(filename) {
        uploadArea.innerHTML = `
            <i class="fas fa-file-word fa-3x mb-3" style="color: #1e2839;"></i>
            <p class="mb-2"><strong>${filename}</strong></p>
            <small class="text-success">File selected successfully</small>
        `;
    }
}

function initializeAnalysisForm() {
    const analyzeForm = document.getElementById('analyzeForm');
    if (!analyzeForm) return;
    
    analyzeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(analyzeForm);
        const essayText = formData.get('essay_text');
        const essayType = formData.get('essay_type');
        const coachingLevel = formData.get('coaching_level');
        const suggestionAggressiveness = formData.get('suggestion_aggressiveness');
        
        if (!essayText || essayText.trim().length < 50) {
            showAlert('Please enter at least 50 characters of essay text.', 'error');
            return;
        }
        
        analyzeEssay({
            essay: essayText.trim(),
            essay_type: essayType || 'auto',
            coaching_level: coachingLevel || 'medium',
            suggestion_aggressiveness: suggestionAggressiveness || 'medium'
        });
    });
}

function initializeSuggestions() {
    // Add click handlers for suggestions in essay content
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('suggestion-delete') || 
            e.target.classList.contains('suggestion-add')) {
            handleSuggestionClick(e.target);
        }
    });
}

function handleSuggestionClick(element) {
    const suggestionType = element.classList.contains('suggestion-delete') ? 'delete' : 'add';
    const text = element.textContent;
    const explanation = element.getAttribute('data-explanation') || 'No explanation provided';
    
    showSuggestionModal(suggestionType, text, explanation, element);
}

function showSuggestionModal(type, text, explanation, element) {
    if (!suggestionModal) return;
    
    const modalContent = document.getElementById('suggestion-content');
    const typeLabel = type === 'delete' ? 'Delete' : 'Add';
    const typeClass = type === 'delete' ? 'text-primary' : 'text-danger';
    
    modalContent.innerHTML = `
        <div class="mb-3">
            <h6>Suggestion Type: <span class="${typeClass}">${typeLabel}</span></h6>
            <p class="border rounded p-2 bg-light">${text}</p>
        </div>
        <div>
            <h6>Explanation:</h6>
            <p>${explanation}</p>
        </div>
    `;
    
    // Store element reference for accept/reject actions
    suggestionModal._element = element;
    
    suggestionModal.show();
}

function acceptSuggestion() {
    const element = suggestionModal._element;
    if (!element) return;
    
    if (element.classList.contains('suggestion-delete')) {
        // Remove the text
        element.remove();
    } else if (element.classList.contains('suggestion-add')) {
        // Keep the text but remove suggestion styling
        element.classList.remove('suggestion-add');
        element.style.textDecoration = 'none';
        element.style.backgroundColor = 'transparent';
        element.style.color = 'inherit';
    }
    
    suggestionModal.hide();
    showAlert('Suggestion accepted successfully', 'success');
}

function rejectSuggestion() {
    const element = suggestionModal._element;
    if (!element) return;
    
    if (element.classList.contains('suggestion-add')) {
        // Remove the suggested addition
        element.remove();
    } else if (element.classList.contains('suggestion-delete')) {
        // Keep the text but remove suggestion styling
        element.classList.remove('suggestion-delete');
        element.style.textDecoration = 'none';
        element.style.backgroundColor = 'transparent';
        element.style.color = 'inherit';
    }
    
    suggestionModal.hide();
    showAlert('Suggestion rejected', 'info');
}

// New functions for word-level suggestions
function acceptWordSuggestion(suggestionElement) {
    if (!suggestionElement) return;
    
    const suggestionId = suggestionElement.getAttribute('data-suggestion-id');
    const type = suggestionElement.getAttribute('data-type');
    const text = suggestionElement.getAttribute('data-text');
    const newText = suggestionElement.getAttribute('data-new-text');
    
    // Add to accepted suggestions
    acceptedSuggestions.push({
        id: suggestionId,
        type: type,
        text: text,
        newText: newText
    });
    
    // Apply the suggestion immediately and remove highlight
    switch (type) {
        case 'delete':
            // Hide the word completely
            suggestionElement.style.display = 'none';
            break;
        case 'add':
            // Keep the word and remove highlighting
            suggestionElement.classList.remove('word-suggestion-add');
            suggestionElement.classList.add('suggestion-accepted');
            suggestionElement.style.backgroundColor = 'transparent';
            suggestionElement.style.textDecoration = 'none';
            suggestionElement.style.color = 'inherit';
            break;
        case 'replace':
            // Replace with new text and remove highlighting
            suggestionElement.textContent = newText;
            suggestionElement.classList.remove('word-suggestion-replace');
            suggestionElement.classList.add('suggestion-accepted');
            suggestionElement.style.backgroundColor = 'transparent';
            suggestionElement.style.borderBottom = 'none';
            suggestionElement.style.color = 'inherit';
            break;
    }
    
    // Remove click handler and tooltip
    suggestionElement.classList.remove('word-suggestion');
    suggestionElement.removeEventListener('click', handleSuggestionClick);
    const tooltip = suggestionElement.querySelector('.suggestion-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
    
    // Send to backend
    sendSuggestionAction('accept', suggestionId, type, text);
    
    showAlert('Suggestion accepted', 'success');
}

function rejectWordSuggestion(suggestionElement) {
    if (!suggestionElement) return;
    
    const suggestionId = suggestionElement.getAttribute('data-suggestion-id');
    const type = suggestionElement.getAttribute('data-type');
    const text = suggestionElement.getAttribute('data-text');
    
    // Remove all suggestion styling and highlighting
    switch (type) {
        case 'delete':
            // Keep the word but remove delete styling
            suggestionElement.classList.remove('word-suggestion-delete');
            suggestionElement.style.backgroundColor = 'transparent';
            suggestionElement.style.textDecoration = 'none';
            suggestionElement.style.color = 'inherit';
            break;
        case 'add':
            // Remove the suggested addition completely
            suggestionElement.remove();
            sendSuggestionAction('reject', suggestionId, type, text);
            showAlert('Suggestion rejected', 'info');
            return;
        case 'replace':
            // Keep original text and remove replace styling
            suggestionElement.classList.remove('word-suggestion-replace');
            suggestionElement.style.backgroundColor = 'transparent';
            suggestionElement.style.borderBottom = 'none';
            suggestionElement.style.color = 'inherit';
            break;
    }
    
    // Remove click handler and tooltip
    suggestionElement.classList.remove('word-suggestion');
    suggestionElement.classList.add('suggestion-rejected');
    suggestionElement.removeEventListener('click', handleSuggestionClick);
    const tooltip = suggestionElement.querySelector('.suggestion-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
    
    // Send to backend
    sendSuggestionAction('reject', suggestionId, type, text);
    
    showAlert('Suggestion rejected', 'info');
}

// Send suggestion action to backend
function sendSuggestionAction(action, suggestionId, type, text) {
    const endpoint = action === 'accept' ? '/api/suggestions/accept' : '/api/suggestions/reject';
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            suggestion_id: suggestionId,
            type: type,
            text: text
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Suggestion ${action}ed successfully`);
        }
    })
    .catch(error => {
        console.error(`Error ${action}ing suggestion:`, error);
    });
}

function initializeCharts() {
    // Initialize progress charts
    const progressCharts = document.querySelectorAll('.progress-chart');
    progressCharts.forEach(chartElement => {
        const ctx = chartElement.getContext('2d');
        const chartData = {
            labels: ['Grammar', 'Clarity', 'Arguments', 'Vocabulary'],
            datasets: [{
                label: 'Score',
                data: [0, 0, 0, 0], // Default values
                backgroundColor: [
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(255, 205, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(255, 205, 86, 1)',
                    'rgba(75, 192, 192, 1)'
                ],
                borderWidth: 1
            }]
        };
        
        new Chart(ctx, {
            type: 'radar',
            data: chartData,
            options: {
                responsive: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    });
}

function initializeTooltips() {
    // Add tooltips to suggestion elements
    document.querySelectorAll('.suggestion-delete, .suggestion-add').forEach(element => {
        const explanation = element.getAttribute('data-explanation');
        if (explanation) {
            element.setAttribute('data-bs-toggle', 'tooltip');
            element.setAttribute('title', explanation);
            new bootstrap.Tooltip(element);
        }
    });
}

function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const mainContainer = document.querySelector('main.container');
    if (mainContainer) {
        mainContainer.insertBefore(alertContainer, mainContainer.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertContainer.parentNode) {
                alertContainer.remove();
            }
        }, 5000);
    }
}

// Essay export functionality
function exportEssay() {
    if (!currentEssayId) {
        showAlert('No essay selected for export', 'error');
        return;
    }
    
    const essayContent = document.getElementById('essay-content');
    if (!essayContent) {
        showAlert('Essay content not found', 'error');
        return;
    }
    
    // Create a new window for printing
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Essay Export</title>
            <style>
                body {
                    font-family: "Times New Roman", serif;
                    line-height: 2;
                    margin: 1in;
                    font-size: 12pt;
                }
                .suggestion-delete {
                    color: blue;
                    text-decoration: line-through;
                }
                .suggestion-add {
                    color: red;
                    text-decoration: underline;
                }
                @page {
                    margin: 1in;
                }
            </style>
        </head>
        <body>
            ${essayContent.innerHTML}
        </body>
        </html>
    `);
    
    printWindow.document.close();
    printWindow.focus();
    
    // Trigger print dialog
    setTimeout(() => {
        printWindow.print();
        printWindow.close();
    }, 250);
}

// Progress tracking
function updateProgress(scores) {
    const progressBars = {
        grammar: document.querySelector('[data-metric="grammar"] .progress-bar'),
        clarity: document.querySelector('[data-metric="clarity"] .progress-bar'),
        arguments: document.querySelector('[data-metric="arguments"] .progress-bar'),
        vocabulary: document.querySelector('[data-metric="vocabulary"] .progress-bar')
    };
    
    Object.keys(progressBars).forEach(metric => {
        const bar = progressBars[metric];
        if (bar && scores[metric] !== undefined) {
            bar.style.width = `${scores[metric]}%`;
            const badge = bar.parentNode.nextElementSibling;
            if (badge) {
                badge.textContent = `${scores[metric].toFixed(1)}%`;
            }
        }
    });
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Auto-save functionality
let autoSaveTimeout;
function autoSave(content) {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
        // Implement auto-save to server
        console.log('Auto-saving content...');
    }, 2000);
}

// Search functionality
function searchEssays(query) {
    const searchResults = document.getElementById('searchResults');
    if (!searchResults) return;
    
    // Show loading spinner
    searchResults.innerHTML = '<div class="text-center"><div class="spinner"></div></div>';
    
    // Simulate search delay
    setTimeout(() => {
        // Implement actual search functionality
        searchResults.innerHTML = '<p class="text-muted">Search functionality to be implemented</p>';
    }, 1000);
}

// Notification system
function showNotification(title, message, type = 'info') {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/favicon.ico'
        });
    }
}

// Request notification permission
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Initialize notification permission on page load
requestNotificationPermission();

// Enhanced analysis functions
function analyzeEssay(data) {
    showLoadingOverlay('Analyzing your essay...');
    
    fetch('/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        hideLoadingOverlay();
        if (result.error) {
            showAlert('Analysis Error: ' + result.error, 'error');
        } else {
            currentAnalysis = result;
            displayAnalysisResults(result);
        }
    })
    .catch(error => {
        hideLoadingOverlay();
        console.error('Analysis error:', error);
        showAlert('Failed to analyze essay. Please try again.', 'error');
    });
}

function displayAnalysisResults(analysis) {
    // Display scores
    displayScores(analysis.scores, analysis.score_reasons);
    
    // Display suggestions
    displaySuggestions(analysis.suggestions);
    
    // Display examples
    displayExamples(analysis.examples);
    
    // Display tagged essay
    displayTaggedEssay(analysis.tagged_essay);
    
    // Show results section
    const resultsSection = document.getElementById('analysisResults');
    if (resultsSection) {
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
}

function displayScores(scores, scoreReasons) {
    const scoresContainer = document.getElementById('scoresContainer');
    if (!scoresContainer) return;
    
    let html = '<div class="row">';
    const scoreCategories = ['ideas', 'organization', 'style', 'grammar'];
    
    scoreCategories.forEach(category => {
        const score = scores[category] || 0;
        const reason = scoreReasons[category] || 'No reason provided';
        const color = getScoreColor(score);
        
        html += `
            <div class="col-md-3 mb-3">
                <div class="card score-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">${category.charAt(0).toUpperCase() + category.slice(1)}</h5>
                        <div class="score-circle" style="border-color: ${color}">
                            <span class="score-value" style="color: ${color}">${score}</span>
                        </div>
                        <p class="score-reason mt-2">${reason}</p>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    scoresContainer.innerHTML = html;
}

function displaySuggestions(suggestions) {
    const suggestionsContainer = document.getElementById('suggestionsContainer');
    if (!suggestionsContainer) return;
    
    if (!suggestions || suggestions.length === 0) {
        suggestionsContainer.innerHTML = '<p class="text-muted">No suggestions available.</p>';
        return;
    }
    
    let html = '<div class="suggestions-list">';
    suggestions.forEach((suggestion, index) => {
        html += `
            <div class="suggestion-item mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <span class="badge bg-primary me-2">${suggestion.type || 'General'}</span>
                        <strong>${suggestion.text || 'No text provided'}</strong>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-success me-1" onclick="acceptSuggestion(${index})">
                            Accept
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="rejectSuggestion(${index})">
                            Reject
                        </button>
                    </div>
                </div>
                <p class="suggestion-reason mt-2 mb-0">${suggestion.reason || 'No explanation provided'}</p>
            </div>
        `;
    });
    html += '</div>';
    
    suggestionsContainer.innerHTML = html;
}

function displayExamples(examples) {
    const examplesContainer = document.getElementById('examplesContainer');
    if (!examplesContainer) return;
    
    let html = '<div class="row">';
    const categories = ['ideas', 'organization', 'style', 'grammar'];
    
    categories.forEach(category => {
        const categoryExamples = examples[category] || [];
        html += `
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">${category.charAt(0).toUpperCase() + category.slice(1)} Examples</h6>
                    </div>
                    <div class="card-body">
        `;
        
        if (categoryExamples.length > 0) {
            categoryExamples.forEach(example => {
                html += `<p class="example-item">• ${example}</p>`;
            });
        } else {
            html += '<p class="text-muted">No examples available</p>';
        }
        
        html += `
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    examplesContainer.innerHTML = html;
}

function displayTaggedEssay(taggedEssay) {
    const essayContainer = document.getElementById('taggedEssayContainer');
    if (!essayContainer) return;
    
    // Process tagged essay to add styling
    let processedEssay = taggedEssay;
    
    // Replace tags with styled spans
    processedEssay = processedEssay.replace(/<delete>(.*?)<\/delete>/g, 
        '<span class="suggestion-delete" title="Suggested deletion">$1</span>');
    processedEssay = processedEssay.replace(/<add>(.*?)<\/add>/g, 
        '<span class="suggestion-add" title="Suggested addition">$1</span>');
    processedEssay = processedEssay.replace(/<replace>(.*?)\|(.*?)<\/replace>/g, 
        '<span class="suggestion-replace" title="Suggested replacement: $1 → $2">$1</span>');
    
    essayContainer.innerHTML = `<div class="tagged-essay">${processedEssay}</div>`;
}

function acceptSuggestion(index) {
    if (!currentAnalysis || !currentAnalysis.suggestions) return;
    
    const suggestion = currentAnalysis.suggestions[index];
    if (!acceptedSuggestions.includes(index)) {
        acceptedSuggestions.push(index);
    }
    
    // Update UI
    const suggestionElement = document.querySelectorAll('.suggestion-item')[index];
    if (suggestionElement) {
        suggestionElement.classList.add('accepted');
        suggestionElement.querySelector('.btn-success').disabled = true;
        suggestionElement.querySelector('.btn-success').textContent = 'Accepted';
    }
    
    showAlert('Suggestion accepted!', 'success');
}

function rejectSuggestion(index) {
    if (!currentAnalysis || !currentAnalysis.suggestions) return;
    
    // Remove from accepted suggestions if it was there
    const acceptedIndex = acceptedSuggestions.indexOf(index);
    if (acceptedIndex > -1) {
        acceptedSuggestions.splice(acceptedIndex, 1);
    }
    
    // Update UI
    const suggestionElement = document.querySelectorAll('.suggestion-item')[index];
    if (suggestionElement) {
        suggestionElement.style.display = 'none';
    }
    
    showAlert('Suggestion rejected!', 'info');
}

function exportToWord() {
    if (!currentAnalysis) {
        showAlert('No analysis data to export', 'error');
        return;
    }
    
    const essayText = document.getElementById('essay_text')?.value;
    if (!essayText) {
        showAlert('No essay text found', 'error');
        return;
    }
    
    showLoadingOverlay('Generating Word document...');
    
    fetch('/export', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            essay: essayText,
            analysis: currentAnalysis,
            acceptedSuggestions: acceptedSuggestions
        })
    })
    .then(response => {
        hideLoadingOverlay();
        if (response.ok) {
            return response.blob();
        }
        throw new Error('Export failed');
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'essay_analysis.docx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showAlert('Document exported successfully!', 'success');
    })
    .catch(error => {
        hideLoadingOverlay();
        console.error('Export error:', error);
        showAlert('Failed to export document', 'error');
    });
}

function getScoreColor(score) {
    if (score >= 90) return '#28a745';
    if (score >= 80) return '#20c997';
    if (score >= 70) return '#ffc107';
    if (score >= 60) return '#fd7e14';
    return '#dc3545';
}

function showLoadingOverlay(message = 'Loading...') {
    let overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="loading-message">${message}</p>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        overlay.querySelector('.loading-message').textContent = message;
    }
    overlay.style.display = 'flex';
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatScore(score) {
    return typeof score === 'number' ? score.toFixed(1) : '0.0';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for use in templates
window.exportEssay = exportEssay;
window.acceptSuggestion = acceptSuggestion;
window.rejectSuggestion = rejectSuggestion;
window.acceptWordSuggestion = acceptWordSuggestion;
window.rejectWordSuggestion = rejectWordSuggestion;
window.sendSuggestionAction = sendSuggestionAction;
window.showAlert = showAlert;
window.updateProgress = updateProgress;

// Export global variables for use in templates
window.currentWordSuggestionId = currentWordSuggestionId;
window.acceptedWordSuggestions = acceptedWordSuggestions;
window.rejectedWordSuggestions = rejectedWordSuggestions;
