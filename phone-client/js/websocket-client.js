/**
 * WebSocketClient — Manages the WebSocket connection to the backend.
 *
 * Features:
 *   - Auto-reconnect with exponential backoff
 *   - Binary audio frame sending
 *   - JSON message parsing and event dispatching
 */
class WebSocketClient {
    constructor() {
        this.ws = null;
        this.url = '';
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 15;
        this.reconnectTimeout = null;

        // ── Event Callbacks ──────────────────────────
        this.onConnected = null;
        this.onDisconnected = null;
        this.onTranscript = null;
        this.onAnswerStart = null;
        this.onAnswerToken = null;
        this.onAnswerEnd = null;
        this.onStatus = null;
        this.onError = null;
    }

    /**
     * Connect to the WebSocket server.
     * @param {string} url - WebSocket URL (e.g., ws://192.168.1.5:8000/ws/interview)
     */
    connect(url) {
        this.url = url;
        this._doConnect();
    }

    /**
     * Disconnect and stop reconnection attempts.
     */
    disconnect() {
        this.maxReconnectAttempts = 0; // Prevent auto-reconnect
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }

    /**
     * Send an audio blob (binary) to the server.
     * @param {Blob} audioBlob - WebM/Opus audio segment
     */
    async sendAudio(audioBlob) {
        if (!this.isConnected || !this.ws) return;

        try {
            const buffer = await audioBlob.arrayBuffer();
            this.ws.send(buffer);
        } catch (err) {
            console.error('[WS] Failed to send audio:', err);
        }
    }

    /**
     * Send a JSON command to the server.
     * @param {object} command - Command object (e.g., {type: "clear_history"})
     */
    sendCommand(command) {
        if (!this.isConnected || !this.ws) return;

        try {
            this.ws.send(JSON.stringify(command));
        } catch (err) {
            console.error('[WS] Failed to send command:', err);
        }
    }

    // ── Private Methods ────────────────────────────

    _doConnect() {
        try {
            this.ws = new WebSocket(this.url);
            this.ws.binaryType = 'arraybuffer';

            this.ws.onopen = () => {
                console.log('[WS] Connected to', this.url);
                this.isConnected = true;
                this.reconnectAttempts = 0;
                if (this.onConnected) this.onConnected();
            };

            this.ws.onclose = (event) => {
                console.log('[WS] Disconnected:', event.code, event.reason);
                this.isConnected = false;
                if (this.onDisconnected) this.onDisconnected();
                this._scheduleReconnect();
            };

            this.ws.onerror = (err) => {
                console.error('[WS] Error:', err);
            };

            this.ws.onmessage = (event) => {
                this._handleMessage(event.data);
            };
        } catch (err) {
            console.error('[WS] Connection failed:', err);
            this._scheduleReconnect();
        }
    }

    _handleMessage(data) {
        try {
            const msg = JSON.parse(data);

            switch (msg.type) {
                case 'transcript':
                    if (this.onTranscript) this.onTranscript(msg.text, msg.is_question);
                    break;
                case 'answer_start':
                    if (this.onAnswerStart) this.onAnswerStart();
                    break;
                case 'answer_token':
                    if (this.onAnswerToken) this.onAnswerToken(msg.token);
                    break;
                case 'answer_end':
                    if (this.onAnswerEnd) this.onAnswerEnd(msg.full_answer);
                    break;
                case 'status':
                    if (this.onStatus) this.onStatus(msg.message);
                    break;
                case 'error':
                    if (this.onError) this.onError(msg.message);
                    break;
                case 'pong':
                    // Heartbeat response, ignore
                    break;
                default:
                    console.log('[WS] Unknown message type:', msg.type);
            }
        } catch (err) {
            console.error('[WS] Failed to parse message:', err, data);
        }
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WS] Max reconnect attempts reached');
            return;
        }

        const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000);
        this.reconnectAttempts++;

        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        this.reconnectTimeout = setTimeout(() => {
            this._doConnect();
        }, delay);
    }
}
