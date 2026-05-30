/**
 * UIRenderer — Handles rendering of transcripts and streaming LLM answers.
 *
 * Features:
 *   - Streaming token rendering with cursor animation
 *   - Basic Markdown to HTML conversion (bold, bullets, line breaks)
 *   - Auto-scroll to latest content
 *   - Question/Answer block management
 */
class UIRenderer {
    constructor() {
        this.transcriptEl = document.getElementById('transcript-content');
        this.answerEl = document.getElementById('answer-content');
        this.answerBadge = document.getElementById('answer-badge');

        this._currentAnswerBlock = null;
        this._currentAnswerText = '';
        this._isStreaming = false;
        this._transcriptCount = 0;
    }

    /**
     * Add a transcript entry to the transcript panel.
     */
    addTranscript(text, isQuestion) {
        // Clear empty state on first transcript
        if (this._transcriptCount === 0) {
            this.transcriptEl.innerHTML = '';
        }

        const entry = document.createElement('div');
        entry.className = 'transcript-entry';

        const icon = isQuestion ? '❓' : '💬';
        entry.textContent = `${icon} ${text}`;
        this._transcriptCount++;

        this.transcriptEl.appendChild(entry);

        // Keep only last 10 transcripts visible
        while (this.transcriptEl.children.length > 10) {
            this.transcriptEl.removeChild(this.transcriptEl.firstChild);
        }

        this.transcriptEl.scrollTop = this.transcriptEl.scrollHeight;
    }

    /**
     * Start a new answer block (called when LLM starts generating).
     */
    startAnswer(questionText) {
        this._isStreaming = true;
        this._currentAnswerText = '';

        // Show the generating badge
        if (this.answerBadge) {
            this.answerBadge.style.display = 'inline-block';
        }

        // Clear the empty state if present
        const emptyState = this.answerEl.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        // Create a new answer block
        this._currentAnswerBlock = document.createElement('div');
        this._currentAnswerBlock.className = 'answer-block';

        // Add question label
        const label = document.createElement('div');
        label.className = 'answer-question-label';
        label.textContent = `Q: ${questionText || 'Question detected'}`;
        this._currentAnswerBlock.appendChild(label);

        // Add answer content area
        const contentArea = document.createElement('div');
        contentArea.className = 'answer-text';
        this._currentAnswerBlock.appendChild(contentArea);

        // Insert at the top (latest first)
        this.answerEl.insertBefore(this._currentAnswerBlock, this.answerEl.firstChild);
    }

    /**
     * Append a streaming token to the current answer.
     */
    appendToken(token) {
        if (!this._currentAnswerBlock) return;

        this._currentAnswerText += token;

        // Render with basic markdown formatting
        const contentArea = this._currentAnswerBlock.querySelector('.answer-text');
        if (contentArea) {
            contentArea.innerHTML = this._renderMarkdown(this._currentAnswerText)
                + '<span class="streaming-cursor"></span>';
        }

        // Auto-scroll
        this.answerEl.scrollTop = 0; // Scroll to top since latest is first
    }

    /**
     * End the current answer block (called when LLM finishes generating).
     */
    endAnswer() {
        this._isStreaming = false;

        // Remove streaming cursor
        if (this._currentAnswerBlock) {
            const cursor = this._currentAnswerBlock.querySelector('.streaming-cursor');
            if (cursor) cursor.remove();

            // Final render
            const contentArea = this._currentAnswerBlock.querySelector('.answer-text');
            if (contentArea) {
                contentArea.innerHTML = this._renderMarkdown(this._currentAnswerText);
            }
        }

        // Hide badge
        if (this.answerBadge) {
            this.answerBadge.style.display = 'none';
        }

        this._currentAnswerBlock = null;
        this._currentAnswerText = '';
    }

    /**
     * Clear all answers.
     */
    clearAnswers() {
        this.answerEl.innerHTML = '<div class="empty-state">Answers will appear here when a question is detected</div>';
        this._currentAnswerBlock = null;
        this._currentAnswerText = '';
    }

    /**
     * Clear all transcripts.
     */
    clearTranscripts() {
        this.transcriptEl.innerHTML = '<div class="empty-state">Waiting for speech...</div>';
        this._transcriptCount = 0;
    }

    /**
     * Convert basic Markdown to HTML.
     * Handles: **bold**, - bullets, newlines, ### headers
     */
    _renderMarkdown(text) {
        if (!text) return '';

        let html = text
            // Escape HTML
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Bold: **text** or __text__
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.*?)__/g, '<strong>$1</strong>')
            // Headers
            .replace(/^### (.+)$/gm, '<strong style="color:var(--accent-cyan);font-size:14px;">$1</strong>')
            .replace(/^## (.+)$/gm, '<strong style="color:var(--accent-cyan);font-size:15px;">$1</strong>')
            // Bullet points
            .replace(/^[\-\•\*] (.+)$/gm, '• $1')
            // Numbered lists
            .replace(/^(\d+)\. (.+)$/gm, '$1. $2')
            // Line breaks
            .replace(/\n/g, '<br>');

        return `<p>${html}</p>`;
    }
}
