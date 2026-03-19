/**
 * Airbot - Aerospace Intelligence Platform
 * Frontend JavaScript Application
 */

// Configuration
const runtimeApiBaseUrl =
    window.AIRBOT_API_BASE_URL ||
    window.__AIRBOT_CONFIG__?.API_BASE_URL ||
    '';

const fallbackApiBaseUrl =
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000'
        : '';

const CONFIG = {
    API_BASE_URL: (runtimeApiBaseUrl || fallbackApiBaseUrl).replace(/\/$/, ''),
    ENDPOINTS: {
        CHAT: '/chat/',
        DOWNLOAD: '/download/excel',
        AUTH_LOGIN: '/auth/login',
        AUTH_ME: '/auth/me',
        AUTH_VERIFY: '/auth/verify'
    }
};

const STUDENT_DOMAIN = '@student.tce.edu';
const ACCESS_GRANTED_SEEN_KEY = 'airbot_access_granted_seen';

function redirectToAccessDenied(reason) {
    const encodedReason = encodeURIComponent(reason || 'not_authorized');
    window.location.href = `auth-access-denied.html?reason=${encodedReason}`;
}

// State Management
const state = {
    currentMode: 'general_chat',
    isLoading: false,
    messages: [],
    lastTestCaseResponse: null,
    lastTestCaseQuery: '',
    user: null,
    isAuthenticated: false
};

// DOM Elements
const elements = {
    modeButtons: document.querySelectorAll('.mode-btn'),
    modeIndicator: document.querySelector('.mode-indicator'),
    welcomeSection: document.getElementById('welcomeSection'),
    messagesContainer: document.getElementById('messagesContainer'),
    userInput: document.getElementById('userInput'),
    sendBtn: document.getElementById('sendBtn'),
    charCount: document.getElementById('charCount'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    quickPrompts: document.querySelectorAll('.quick-prompt'),
    downloadSection: document.getElementById('downloadSection'),
    downloadBtn: document.getElementById('downloadBtn'),
    loginBtn: document.getElementById('loginBtn'),
    logoutBtn: document.getElementById('logoutBtn'),
    userProfile: document.getElementById('userProfile'),
    userAvatar: document.getElementById('userAvatar'),
    userName: document.getElementById('userName'),
    premiumIndicator: document.getElementById('premiumIndicator')
};

// Initialize Application
async function init() {
    setupEventListeners();
    updateModeIndicator();
    autoResizeTextarea();
    await checkAuthStatus();

    const initialMode = new URLSearchParams(window.location.search).get('mode');
    if (initialMode === 'test_case') {
        switchMode('test_case');
    }
}

// Event Listeners Setup
function setupEventListeners() {
    // Mode switching
    elements.modeButtons.forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });

    // Input handling
    elements.userInput.addEventListener('input', handleInputChange);
    elements.userInput.addEventListener('keydown', handleKeyDown);

    // Send button
    elements.sendBtn.addEventListener('click', sendMessage);

    // Quick prompts
    elements.quickPrompts.forEach(prompt => {
        prompt.addEventListener('click', () => {
            const promptText = prompt.dataset.prompt;
            elements.userInput.value = promptText;
            handleInputChange();
            sendMessage();
        });
    });

    // Window resize for mode indicator
    window.addEventListener('resize', updateModeIndicator);

    // Download button
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadTestCases);
    }

    // Auth buttons
    if (elements.loginBtn) {
        elements.loginBtn.addEventListener('click', handleLogin);
    }
    if (elements.logoutBtn) {
        elements.logoutBtn.addEventListener('click', handleLogout);
    }
}

// Mode Switching
function switchMode(mode) {
    if (state.currentMode === mode) return;

    if (mode === 'test_case' && !hasTestCaseAccess()) {
        redirectToAccessDenied(
            !state.isAuthenticated ? 'login_required' : 'domain_restricted'
        );
        return;
    }

    if (mode === 'test_case' && hasTestCaseAccess() && !sessionStorage.getItem(ACCESS_GRANTED_SEEN_KEY)) {
        sessionStorage.setItem(ACCESS_GRANTED_SEEN_KEY, '1');
        window.location.href = 'auth-access-granted.html?next=%2F%3Fmode%3Dtest_case';
        return;
    }

    state.currentMode = mode;

    // Update button states
    elements.modeButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Update indicator position
    updateModeIndicator();

    // Update placeholder text
    if (mode === 'test_case') {
        elements.userInput.placeholder = 'Describe the aerospace system or scenario to generate test cases...';
    } else {
        elements.userInput.placeholder = 'Ask about aerospace engineering or request test cases...';
        // Hide download button in general chat mode
        hideDownloadSection();
    }
}

// Update Mode Indicator Position
function updateModeIndicator() {
    const activeBtn = document.querySelector('.mode-btn.active');
    if (activeBtn && elements.modeIndicator) {
        const btnRect = activeBtn.getBoundingClientRect();
        const containerRect = activeBtn.parentElement.getBoundingClientRect();

        elements.modeIndicator.style.width = `${btnRect.width}px`;
        elements.modeIndicator.style.left = `${activeBtn.offsetLeft}px`;
    }
}

// Handle Input Changes
function handleInputChange() {
    const value = elements.userInput.value;
    elements.charCount.textContent = value.length;
    elements.sendBtn.disabled = value.trim().length === 0;
    autoResizeTextarea();
}

// Auto-resize Textarea
function autoResizeTextarea() {
    const textarea = elements.userInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

// Handle Keyboard Events
function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!elements.sendBtn.disabled) {
            sendMessage();
        }
    }
}

// Send Message to API
async function sendMessage() {
    const question = elements.userInput.value.trim();
    if (!question || state.isLoading) return;

    if (state.currentMode === 'test_case' && !hasTestCaseAccess()) {
        redirectToAccessDenied(
            !state.isAuthenticated ? 'login_required' : 'domain_restricted'
        );
        return;
    }

    // Show messages container, hide welcome
    showMessagesContainer();

    // Add user message
    addMessage('user', question);

    // Clear input
    elements.userInput.value = '';
    handleInputChange();

    // Show loading
    setLoading(true);

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CHAT}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                question: question,
                mode: state.currentMode
            })
        });

        if (response.status === 403 && state.currentMode === 'test_case') {
            redirectToAccessDenied(
                !state.isAuthenticated ? 'login_required' : 'domain_restricted'
            );
            return;
        }

        if (!response.ok) {
            let errorMessage = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData?.detail) {
                    errorMessage = errorData.detail;
                }
            } catch (e) {
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();

        // Add assistant message
        addMessage('assistant', data.answer, state.currentMode);

        // Store test case response for download
        if (state.currentMode === 'test_case') {
            state.lastTestCaseResponse = data.answer;
            state.lastTestCaseQuery = question;
            showDownloadSection();
        }

    } catch (error) {
        console.error('Error:', error);
        addMessage('assistant', `Sorry, I encountered an error: ${error.message}. Please make sure the backend server is running on ${CONFIG.API_BASE_URL}`, 'error');
    } finally {
        setLoading(false);
    }
}

// Show Messages Container
function showMessagesContainer() {
    elements.welcomeSection.classList.add('hidden');
    elements.messagesContainer.classList.add('active');
}

// Add Message to Chat
function addMessage(type, content, mode = 'general_chat') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const avatarSvg = type === 'user'
        ? `<svg viewBox="0 0 24 24" fill="none"><path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/></svg>`
        : `<svg viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2"/><path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2"/><path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2"/></svg>`;

    let formattedContent;
    if (type === 'assistant' && mode === 'test_case') {
        formattedContent = formatTestCase(content);
    } else if (type === 'assistant') {
        formattedContent = formatGeneralResponse(content);
    } else {
        formattedContent = `<div class="user-message">${escapeHtml(content)}</div>`;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarSvg}</div>
        <div class="message-content">${formattedContent}</div>
    `;

    elements.messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Format Test Case Response
function formatTestCase(content) {
    // Try to parse the structured test case format
    const testCaseRegex = /\*\*TEST CASE\*\*[\s\S]*?(?=\*\*TEST CASE\*\*|$)/gi;
    const testCases = content.match(testCaseRegex);

    if (testCases && testCases.length > 0) {
        return testCases.map(tc => parseAndFormatTestCase(tc)).join('');
    }

    // Fallback: try to extract fields manually
    return parseAndFormatTestCase(content);
}

// Parse and Format Individual Test Case
function parseAndFormatTestCase(content) {
    const fields = {
        id: extractField(content, /\*\*ID:\*\*\s*(.+?)(?:\n|$)/i) || extractField(content, /ID:\s*(.+?)(?:\n|$)/i) || 'TC-001',
        title: extractField(content, /\*\*Title:\*\*\s*(.+?)(?:\n|$)/i) || extractField(content, /Title:\s*(.+?)(?:\n|$)/i) || 'Test Case',
        system: extractField(content, /\*\*System Under Test:\*\*\s*(.+?)(?:\n|$)/i) || '-',
        standards: extractField(content, /\*\*Applicable Standards:\*\*\s*(.+?)(?:\n|$)/i) || '-',
        description: extractField(content, /\*\*Description:\*\*\s*([\s\S]+?)(?=\n\*\*Preconditions|$)/i) || '-',
        preconditions: extractListField(content, /\*\*Preconditions:\*\*([\s\S]*?)(?=\*\*Test Equipment|\*\*Test Steps|$)/i),
        equipment: extractListField(content, /\*\*Test Equipment Required:\*\*([\s\S]*?)(?=\*\*Test Steps|$)/i),
        steps: extractListField(content, /\*\*Test Steps:\*\*([\s\S]*?)(?=\*\*Expected|$)/i),
        expected: extractListField(content, /\*\*Expected Results:\*\*([\s\S]*?)(?=\*\*Failure|$)/i),
        failure: extractListField(content, /\*\*Failure Criteria:\*\*([\s\S]*?)(?=\*\*Actual|$)/i),
        actual: extractField(content, /\*\*Actual Results:\*\*\s*(.+?)(?:\n\*\*|$)/i) || 'To be filled during execution',
        status: extractField(content, /\*\*Status:\*\*\s*(.+?)(?:\n|$)/i) || 'PENDING',
        priority: extractField(content, /\*\*Priority:\*\*\s*(.+?)(?:\n|$)/i) || 'MEDIUM',
        category: extractField(content, /\*\*Category:\*\*\s*(.+?)(?:\n|$)/i) || 'Functional',
        duration: extractField(content, /\*\*Estimated Duration:\*\*\s*(.+?)(?:\n|$)/i) || '-',
        risk: extractField(content, /\*\*Risk Level:\*\*\s*(.+?)(?:\n|$)/i) || 'Medium'
    };

    const statusClass = fields.status.toLowerCase().includes('pass') ? 'pass'
        : fields.status.toLowerCase().includes('fail') ? 'fail'
        : 'pending';

    const priorityClass = fields.priority.toLowerCase().includes('critical') ? 'critical'
        : fields.priority.toLowerCase().includes('high') ? 'high'
        : fields.priority.toLowerCase().includes('low') ? 'low'
        : 'medium';

    const riskClass = fields.risk.toLowerCase().includes('high') ? 'high'
        : fields.risk.toLowerCase().includes('low') ? 'low'
        : 'medium';

    return `
        <div class="test-case-container">
            <div class="test-case-header">
                <svg viewBox="0 0 24 24" fill="none">
                    <path d="M9 11L12 14L22 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 12V19C21 20.1046 20.1046 21 19 21H5C3.89543 21 3 20.1046 3 19V5C3 3.89543 3.89543 3 5 3H16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="test-case-title">${escapeHtml(fields.id)} - ${escapeHtml(fields.title)}</span>
            </div>
            <div class="test-case-meta">
                <span class="meta-badge category">${escapeHtml(fields.category)}</span>
                <span class="meta-badge priority ${priorityClass}">${escapeHtml(fields.priority.split('-')[0].trim())}</span>
                <span class="meta-badge risk ${riskClass}">Risk: ${escapeHtml(fields.risk.split('-')[0].trim())}</span>
                ${fields.duration !== '-' ? `<span class="meta-badge duration">${escapeHtml(fields.duration)}</span>` : ''}
            </div>
            <div class="test-case-body">
                ${fields.system !== '-' ? `
                <div class="test-case-row">
                    <div class="test-case-label">System</div>
                    <div class="test-case-value">${escapeHtml(fields.system)}</div>
                </div>` : ''}
                ${fields.standards !== '-' ? `
                <div class="test-case-row">
                    <div class="test-case-label">Standards</div>
                    <div class="test-case-value standards">${escapeHtml(fields.standards)}</div>
                </div>` : ''}
                <div class="test-case-row">
                    <div class="test-case-label">Description</div>
                    <div class="test-case-value description">${escapeHtml(fields.description.trim())}</div>
                </div>
                <div class="test-case-row">
                    <div class="test-case-label">Preconditions</div>
                    <div class="test-case-value">${formatListItems(fields.preconditions)}</div>
                </div>
                ${fields.equipment.length > 0 && fields.equipment[0] !== '-' ? `
                <div class="test-case-row">
                    <div class="test-case-label">Equipment</div>
                    <div class="test-case-value equipment">${formatListItems(fields.equipment)}</div>
                </div>` : ''}
                <div class="test-case-row steps-row">
                    <div class="test-case-label">Test Steps</div>
                    <div class="test-case-value">${formatNumberedList(fields.steps)}</div>
                </div>
                <div class="test-case-row">
                    <div class="test-case-label">Expected Results</div>
                    <div class="test-case-value expected">${formatListItems(fields.expected)}</div>
                </div>
                ${fields.failure.length > 0 && fields.failure[0] !== '-' ? `
                <div class="test-case-row">
                    <div class="test-case-label">Failure Criteria</div>
                    <div class="test-case-value failure">${formatListItems(fields.failure)}</div>
                </div>` : ''}
                <div class="test-case-row">
                    <div class="test-case-label">Actual Results</div>
                    <div class="test-case-value">${escapeHtml(fields.actual)}</div>
                </div>
                <div class="test-case-row">
                    <div class="test-case-label">Status</div>
                    <div class="test-case-value">
                        <span class="test-case-status ${statusClass}">${escapeHtml(fields.status)}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Extract Field from Content
function extractField(content, regex) {
    const match = content.match(regex);
    return match ? match[1].trim() : null;
}

// Extract List Field from Content
function extractListField(content, regex) {
    const match = content.match(regex);
    if (!match) return [];

    const listContent = match[1];
    const items = listContent.split(/\n/).filter(line => {
        const trimmed = line.trim();
        return trimmed.startsWith('-') || trimmed.startsWith('*') || /^\d+\./.test(trimmed);
    }).map(item => item.replace(/^[-*\d.]+\s*/, '').trim()).filter(item => item.length > 0);

    return items.length > 0 ? items : [listContent.trim()];
}

// Format List Items
function formatListItems(items) {
    if (!items || items.length === 0) return '-';
    if (items.length === 1 && items[0] === '-') return '-';

    return `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

// Format Numbered List (for test steps)
function formatNumberedList(items) {
    if (!items || items.length === 0) return '-';
    if (items.length === 1 && items[0] === '-') return '-';

    return `<ol>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ol>`;
}

// Format General Response
function formatGeneralResponse(content) {
    // Convert markdown-like formatting to HTML
    let formatted = escapeHtml(content);

    // Convert **bold**
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Convert *italic*
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Convert line breaks to paragraphs
    const paragraphs = formatted.split(/\n\n+/).filter(p => p.trim());

    if (paragraphs.length > 1) {
        formatted = paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    } else {
        formatted = formatted.replace(/\n/g, '<br>');
    }

    return `<div class="general-response">${formatted}</div>`;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Set Loading State
function setLoading(loading) {
    state.isLoading = loading;
    elements.loadingOverlay.classList.toggle('active', loading);
    elements.sendBtn.disabled = loading || elements.userInput.value.trim().length === 0;
}

// Scroll to Bottom of Messages
function scrollToBottom() {
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

// Show Download Section
function showDownloadSection() {
    if (elements.downloadSection) {
        elements.downloadSection.classList.add('visible');
    }
}

// Hide Download Section
function hideDownloadSection() {
    if (elements.downloadSection) {
        elements.downloadSection.classList.remove('visible');
    }
}

// Download Test Cases as Excel
async function downloadTestCases() {
    if (!state.lastTestCaseResponse) {
        alert('No test cases available to download. Generate test cases first.');
        return;
    }

    const downloadBtn = elements.downloadBtn;
    const originalContent = downloadBtn.innerHTML;

    try {
        // Show loading state on button
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = `
            <svg class="spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="10"/>
            </svg>
            <span>Generating...</span>
        `;

        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DOWNLOAD}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: state.lastTestCaseResponse,
                query: state.lastTestCaseQuery
            })
        });

        if (!response.ok) {
            throw new Error(`Download failed: ${response.status}`);
        }

        // Get filename from response headers or generate one
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'airbot_test_cases.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename=(.+)/);
            if (match) {
                filename = match[1].replace(/"/g, '');
            }
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // Show success state briefly
        downloadBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none">
                <path d="M9 11L12 14L22 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>Downloaded!</span>
        `;

        setTimeout(() => {
            downloadBtn.innerHTML = originalContent;
            downloadBtn.disabled = false;
        }, 2000);

    } catch (error) {
        console.error('Download error:', error);
        alert(`Failed to download: ${error.message}`);
        downloadBtn.innerHTML = originalContent;
        downloadBtn.disabled = false;
    }
}

// ==========================================
// Authentication Functions
// ==========================================

// Get stored auth token
function getAuthToken() {
    return localStorage.getItem('airbot_token');
}

// Get auth headers for API calls
function getAuthHeaders() {
    const token = getAuthToken();
    if (token) {
        return { 'Authorization': `Bearer ${token}` };
    }
    return {};
}

function hasTestCaseAccess() {
    const email = (state.user?.email || '').toLowerCase();
    const isStudentDomain = email.endsWith(STUDENT_DOMAIN);
    return Boolean(state.isAuthenticated && state.user?.is_premium && isStudentDomain);
}

// Check authentication status on page load
async function checkAuthStatus() {
    const token = getAuthToken();
    if (!token) {
        updateUIForGuest();
        return;
    }

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.AUTH_ME}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const user = await response.json();
            state.user = user;
            state.isAuthenticated = true;
            updateUIForUser(user);
        } else {
            // Token invalid, clear it
            localStorage.removeItem('airbot_token');
            updateUIForGuest();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        updateUIForGuest();
    }
}

// Handle login button click
async function handleLogin() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.AUTH_LOGIN}`);
        const data = await response.json();

        if (data.auth_url) {
            // Redirect to Google OAuth
            window.location.href = data.auth_url;
        } else {
            alert('Failed to initiate login. Please try again.');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Failed to connect to server. Please make sure the backend is running.');
    }
}

// Handle logout
function handleLogout() {
    localStorage.removeItem('airbot_token');
    sessionStorage.removeItem(ACCESS_GRANTED_SEEN_KEY);
    state.user = null;
    state.isAuthenticated = false;
    updateUIForGuest();
}

// Update UI for authenticated user
function updateUIForUser(user) {
    if (elements.loginBtn) {
        elements.loginBtn.style.display = 'none';
    }
    if (elements.userProfile) {
        elements.userProfile.style.display = 'flex';
    }
    if (elements.userAvatar && user.picture) {
        elements.userAvatar.src = user.picture;
    }
    if (elements.userName) {
        elements.userName.textContent = user.name || user.email;
    }
    if (elements.premiumIndicator) {
        elements.premiumIndicator.style.display = user.is_premium ? 'inline' : 'none';
    }

    if (!user.is_premium && state.currentMode === 'test_case') {
        switchMode('general_chat');
    }
}

// Update UI for guest (not logged in)
function updateUIForGuest() {
    if (elements.loginBtn) {
        elements.loginBtn.style.display = 'flex';
    }
    if (elements.userProfile) {
        elements.userProfile.style.display = 'none';
    }

    if (state.currentMode === 'test_case') {
        switchMode('general_chat');
    }
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', init);
