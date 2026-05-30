/**
 * App — Main orchestrator for the ParakeetAI phone client.
 *
 * Wires together: AudioCapture → WebSocketClient → UIRenderer
 * Manages screen transitions, file uploads, settings, and wake lock.
 */

// ── Globals ──────────────────────────────────────────
const audioCapture = new AudioCapture();
const wsClient = new WebSocketClient();
let uiRenderer = null; // Initialized when interview screen loads
let isMicActive = false;
let wakeLock = null;
let lastQuestionText = '';

// ── Initialization ───────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Load saved server URL from localStorage
    const savedUrl = localStorage.getItem('parakeet_server_url');
    if (savedUrl) {
        document.getElementById('server-url').value = savedUrl;
    } else {
        // Auto-detect: use current page host
        const host = window.location.hostname || 'localhost';
        const port = window.location.port || '8000';
        document.getElementById('server-url').value = `${host}:${port}`;
    }

    // Check if context is already loaded
    checkExistingContext();

    // Set up file upload handlers
    setupFileUploads();
});

// ── File Upload Handlers ─────────────────────────────
function setupFileUploads() {
    document.getElementById('resume-file').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        await uploadFile(file, 'resume');
    });

    document.getElementById('jd-file').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        await uploadFile(file, 'jd');
    });
}

async function uploadFile(file, type) {
    const statusEl = document.getElementById(`${type === 'resume' ? 'resume' : 'jd'}-status`);
    statusEl.textContent = `Uploading ${file.name}...`;
    statusEl.className = 'upload-status';

    const serverBase = getHttpBaseUrl();
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${serverBase}/api/upload/${type === 'resume' ? 'resume' : 'jd'}`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`);
        }

        const result = await response.json();
        statusEl.textContent = `✅ ${file.name} (${result.chars} chars extracted)`;
        statusEl.className = 'upload-status success';
    } catch (err) {
        console.error('[Upload] Error:', err);
        statusEl.textContent = `❌ Upload failed: ${err.message}`;
        statusEl.className = 'upload-status error';
    }
}

async function checkExistingContext() {
    const serverBase = getHttpBaseUrl();
    try {
        const response = await fetch(`${serverBase}/api/context`);
        if (response.ok) {
            const data = await response.json();
            if (data.resume) {
                document.getElementById('resume-status').textContent = `✅ Resume loaded (${data.resume.length} chars)`;
                document.getElementById('resume-status').className = 'upload-status success';
            }
            if (data.job_description) {
                document.getElementById('jd-status').textContent = `✅ JD loaded (${data.job_description.length} chars)`;
                document.getElementById('jd-status').className = 'upload-status success';
            }
        }
    } catch (err) {
        // Server not reachable yet, that's fine
    }
}

// ── Screen Navigation ────────────────────────────────
function startInterview() {
    const serverInput = document.getElementById('server-url').value.trim();
    if (!serverInput) {
        alert('Please enter the server URL');
        return;
    }

    // Save to localStorage
    localStorage.setItem('parakeet_server_url', serverInput);

    // Build WebSocket URL
    const wsUrl = getWsUrl(serverInput);

    // Switch screens
    document.getElementById('setup-screen').classList.remove('active');
    document.getElementById('interview-screen').classList.add('active');

    // Initialize UI renderer
    uiRenderer = new UIRenderer();

    // Connect WebSocket
    setupWebSocket(wsUrl);

    // Request wake lock to prevent screen from sleeping
    requestWakeLock();
}

function goBack() {
    // Stop everything
    if (isMicActive) {
        toggleMicrophone();
    }
    wsClient.disconnect();
    releaseWakeLock();

    // Switch screens
    document.getElementById('interview-screen').classList.remove('active');
    document.getElementById('setup-screen').classList.add('active');
}

// ── WebSocket Setup ──────────────────────────────────
function setupWebSocket(url) {
    wsClient.onConnected = () => {
        updateConnectionStatus('connected', 'Connected');
    };

    wsClient.onDisconnected = () => {
        updateConnectionStatus('error', 'Disconnected');
    };

    wsClient.onStatus = (message) => {
        updateConnectionStatus('connected', message);
    };

    wsClient.onError = (message) => {
        console.error('[App] Server error:', message);
        updateConnectionStatus('error', 'Error');
    };

    wsClient.onTranscript = (text, isQuestion) => {
        if (uiRenderer) {
            uiRenderer.addTranscript(text, isQuestion);
        }
        if (isQuestion) {
            lastQuestionText = text;
        }
    };

    wsClient.onAnswerStart = () => {
        if (uiRenderer) {
            uiRenderer.startAnswer(lastQuestionText);
        }
    };

    wsClient.onAnswerToken = (token) => {
        if (uiRenderer) {
            uiRenderer.appendToken(token);
        }
    };

    wsClient.onAnswerEnd = (fullAnswer) => {
        if (uiRenderer) {
            uiRenderer.endAnswer();
        }
    };

    wsClient.connect(url);
}

// ── Microphone Control ───────────────────────────────
async function toggleMicrophone() {
    const micBtn = document.getElementById('mic-btn');
    const micLabel = document.getElementById('mic-label');
    const volumeBar = document.getElementById('volume-bar-container');

    if (!isMicActive) {
        // Start
        audioCapture.onSegmentReady = (blob) => {
            console.log(`[App] Speech segment: ${(blob.size / 1024).toFixed(1)}KB`);
            wsClient.sendAudio(blob);
        };

        audioCapture.onVolumeChange = (vol) => {
            const fill = document.getElementById('volume-bar-fill');
            const label = document.getElementById('volume-label');
            if (fill) fill.style.width = Math.min(100, (vol / 40) * 100) + '%';
            if (label) label.textContent = Math.round(vol);
        };

        audioCapture.onStateChange = (state) => {
            if (state === 'recording') {
                micLabel.textContent = '🔴 Recording speech...';
                micBtn.style.boxShadow = '0 0 20px rgba(239,68,68,0.5)';
            } else if (state === 'listening') {
                micLabel.textContent = '👂 Listening...';
                micBtn.style.boxShadow = '';
            }
        };

        const started = await audioCapture.start();
        if (started) {
            isMicActive = true;
            micBtn.classList.add('active');
            micLabel.textContent = '👂 Listening...';
            if (volumeBar) volumeBar.style.display = 'flex';
        } else {
            micLabel.textContent = '❌ Mic access denied';
        }
    } else {
        // Stop
        audioCapture.stop();
        isMicActive = false;
        micBtn.classList.remove('active');
        micBtn.style.boxShadow = '';
        micLabel.textContent = 'Tap to Start';
        if (volumeBar) volumeBar.style.display = 'none';
        // Reset volume bar
        const fill = document.getElementById('volume-bar-fill');
        if (fill) fill.style.width = '0%';
    }
}

// ── History Control ──────────────────────────────────
function clearHistory() {
    wsClient.sendCommand({ type: 'clear_history' });
    if (uiRenderer) {
        uiRenderer.clearAnswers();
        uiRenderer.clearTranscripts();
    }
}

// ── Manual Answer Trigger ────────────────────────────
function forceAnswer() {
    // Send command to backend to generate an answer for the latest transcript
    wsClient.sendCommand({ type: 'force_answer' });

    // Visual feedback — flash the button
    const btn = document.getElementById('answer-trigger-btn');
    btn.style.background = 'rgba(245, 158, 11, 0.35)';
    setTimeout(() => {
        btn.style.background = '';
    }, 300);
}

// ── UI Helpers ───────────────────────────────────────
function updateConnectionStatus(state, text) {
    const dot = document.getElementById('connection-dot');
    const statusText = document.getElementById('status-text');

    dot.className = 'dot';
    if (state === 'connected') dot.classList.add('connected');
    if (state === 'error') dot.classList.add('error');

    statusText.textContent = text;
}

function getHttpBaseUrl() {
    const serverInput = document.getElementById('server-url').value.trim();
    // Remove any protocol prefix
    let host = serverInput.replace(/^(https?|wss?):\/\//, '');
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    return `${protocol}://${host}`;
}

function getWsUrl(serverInput) {
    let host = serverInput.replace(/^(https?|wss?):\/\//, '');
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${protocol}://${host}/ws/interview`;
}

// ── Wake Lock (prevent phone screen sleep) ───────────
async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
            console.log('[App] Wake lock acquired');
        }
    } catch (err) {
        console.log('[App] Wake lock not available:', err);
    }
}

function releaseWakeLock() {
    if (wakeLock) {
        wakeLock.release();
        wakeLock = null;
        console.log('[App] Wake lock released');
    }
}

// Re-acquire wake lock when page becomes visible again
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && isMicActive) {
        requestWakeLock();
    }
});
