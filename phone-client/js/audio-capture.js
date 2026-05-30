/**
 * AudioCapture — Browser microphone capture with VAD (Voice Activity Detection).
 *
 * Uses MediaRecorder to capture WebM/Opus audio, with browser-side volume
 * monitoring to detect speech boundaries. Only sends audio segments that
 * contain speech, reducing unnecessary API calls.
 *
 * Flow:
 *   1. Monitor microphone volume via AnalyserNode
 *   2. When speech detected (volume > threshold), start recording
 *   3. When silence detected (volume < threshold for SILENCE_DURATION), stop recording
 *   4. Send the complete speech segment to the callback
 */
class AudioCapture {
    constructor() {
        // ── Configuration ────────────────────────────
        this.SPEECH_THRESHOLD = 8;       // Volume level to consider as speech (0-255) — lowered for sensitivity
        this.SILENCE_DURATION = 1800;    // ms of silence before ending a segment
        this.CHECK_INTERVAL = 80;        // ms between volume checks
        this.MAX_SEGMENT_DURATION = 30000; // Max 30 seconds per segment

        // ── State ────────────────────────────────────
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.recorder = null;
        this.isCapturing = false;
        this.isRecording = false;
        this.silenceStart = null;
        this.recordingStart = null;
        this.chunks = [];
        this.volumeCheckInterval = null;

        // ── Callbacks ────────────────────────────────
        this.onSegmentReady = null;     // Called with Blob when speech segment complete
        this.onVolumeChange = null;     // Called with volume level (0-255)
        this.onStateChange = null;      // Called with state string
    }

    /**
     * Start capturing audio from the microphone.
     */
    async start() {
        try {
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            });

            console.log('[AudioCapture] Microphone access granted');

            // Set up Web Audio API for volume analysis
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();

            // CRITICAL: AudioContext starts suspended on mobile browsers.
            // Must resume after a user gesture (the start button click counts).
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
                console.log('[AudioCapture] AudioContext resumed from suspended state');
            }

            const source = this.audioContext.createMediaStreamSource(this.stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512;
            this.analyser.smoothingTimeConstant = 0.3;
            source.connect(this.analyser);

            this.isCapturing = true;
            this._startVolumeMonitoring();
            this._emitState('listening');

            console.log('[AudioCapture] Started successfully. Threshold:', this.SPEECH_THRESHOLD);
            return true;
        } catch (err) {
            console.error('[AudioCapture] Failed to start:', err.name, err.message);
            this._emitState('error');
            return false;
        }
    }

    /**
     * Stop all audio capture and clean up.
     */
    stop() {
        this.isCapturing = false;
        this._stopRecording(false); // Don't send partial segment

        if (this.volumeCheckInterval) {
            clearInterval(this.volumeCheckInterval);
            this.volumeCheckInterval = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        this._emitState('stopped');
        console.log('[AudioCapture] Stopped');
    }

    /**
     * Monitor volume levels to detect speech/silence boundaries.
     */
    _startVolumeMonitoring() {
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

        this.volumeCheckInterval = setInterval(() => {
            if (!this.isCapturing || !this.analyser) return;

            this.analyser.getByteFrequencyData(dataArray);

            // Calculate average volume across frequency bins
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i];
            }
            const volume = sum / dataArray.length;

            // Report volume to UI for visual feedback
            if (this.onVolumeChange) {
                this.onVolumeChange(volume);
            }

            const isSpeech = volume > this.SPEECH_THRESHOLD;

            if (isSpeech) {
                this.silenceStart = null;

                if (!this.isRecording) {
                    console.log(`[AudioCapture] Speech detected (vol: ${volume.toFixed(1)}), starting recording`);
                    this._startRecording();
                }
            } else if (this.isRecording) {
                // Silence detected while recording
                if (!this.silenceStart) {
                    this.silenceStart = Date.now();
                } else if (Date.now() - this.silenceStart >= this.SILENCE_DURATION) {
                    // Enough silence — end the segment
                    console.log('[AudioCapture] Silence detected, ending segment');
                    this._stopRecording(true);
                }
            }

            // Safety: cap segment length
            if (this.isRecording && this.recordingStart &&
                Date.now() - this.recordingStart >= this.MAX_SEGMENT_DURATION) {
                console.log('[AudioCapture] Max segment duration reached');
                this._stopRecording(true);
            }
        }, this.CHECK_INTERVAL);
    }

    /**
     * Start recording a speech segment.
     */
    _startRecording() {
        if (this.isRecording || !this.stream) return;

        // Determine the best supported MIME type
        const mimeType = this._getSupportedMimeType();
        console.log('[AudioCapture] Using MIME type:', mimeType || 'browser default');

        try {
            const options = mimeType ? { mimeType } : {};
            this.recorder = new MediaRecorder(this.stream, options);
        } catch (e) {
            console.warn('[AudioCapture] MediaRecorder creation failed with options, using defaults');
            this.recorder = new MediaRecorder(this.stream);
        }

        this.chunks = [];
        this.recordingStart = Date.now();
        this.silenceStart = null;
        this.isRecording = true;

        this.recorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                this.chunks.push(e.data);
            }
        };

        this.recorder.start(500); // Collect data every 500ms
        this._emitState('recording');
    }

    /**
     * Stop recording and optionally send the segment.
     */
    _stopRecording(sendSegment) {
        if (!this.isRecording || !this.recorder) return;

        this.isRecording = false;
        this.silenceStart = null;

        const recorder = this.recorder;
        this.recorder = null;

        if (recorder.state === 'recording') {
            recorder.onstop = () => {
                if (sendSegment && this.chunks.length > 0) {
                    const blob = new Blob(this.chunks, { type: recorder.mimeType || 'audio/webm' });
                    const duration = Date.now() - (this.recordingStart || Date.now());

                    console.log(`[AudioCapture] Segment ready: ${(blob.size / 1024).toFixed(1)}KB, ${(duration / 1000).toFixed(1)}s`);

                    // Only send if segment has meaningful duration (> 400ms) and size
                    if (duration > 400 && blob.size > 200) {
                        if (this.onSegmentReady) {
                            this.onSegmentReady(blob);
                        }
                    } else {
                        console.log('[AudioCapture] Segment too short, discarding');
                    }
                }
                this.chunks = [];
                this.recordingStart = null;
            };
            recorder.stop();
        }

        if (this.isCapturing) {
            this._emitState('listening');
        }
    }

    /**
     * Get the best supported audio MIME type for MediaRecorder.
     */
    _getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
        ];

        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }

        return ''; // Let browser decide
    }

    /**
     * Emit state change event.
     */
    _emitState(state) {
        if (this.onStateChange) {
            this.onStateChange(state);
        }
    }
}
