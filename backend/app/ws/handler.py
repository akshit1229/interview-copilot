"""
WebSocket handler — the core pipeline orchestrator.

Flow:
  1. Phone browser sends complete audio segments (WebM blobs) via WebSocket
  2. Server transcribes via Groq Whisper
  3. Detects if utterance warrants an LLM answer
  4. Assembles context (resume + JD + history)
  5. Streams LLM answer tokens back to client
"""

import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.transcription.whisper_groq import transcribe_audio
from app.llm.groq_client import stream_groq_chat
from app.llm.prompts import build_messages
from app.context.manager import context_manager
from app.context.history import ConversationHistory
from app.config import settings


async def send_json(ws: WebSocket, msg: dict):
    """Helper to send a JSON message, ignoring errors if connection closed."""
    try:
        await ws.send_text(json.dumps(msg))
    except Exception:
        pass


def should_trigger_answer(text: str) -> bool:
    """
    Determine if an utterance should trigger an LLM answer.

    Triggers on:
    - Any utterance with enough words (if AUTO_ANSWER_ALL is True)
    - Question marks
    - Common question starters
    """
    text = text.strip()
    word_count = len(text.split())

    if word_count < settings.MIN_WORDS_FOR_ANSWER:
        return False

    if settings.AUTO_ANSWER_ALL:
        return True

    # Explicit question detection
    if "?" in text:
        return True

    # Common interview question starters
    question_starters = [
        "tell me", "describe", "explain", "what", "why", "how",
        "where", "when", "can you", "could you", "have you",
        "do you", "are you", "walk me through", "give me",
    ]
    text_lower = text.lower()
    return any(text_lower.startswith(s) for s in question_starters)


async def generate_answer(websocket: WebSocket, history: ConversationHistory, question: str):
    """Generate and stream an LLM answer for the given question."""
    # Add question to history
    history.add_question(question)

    # Build LLM messages
    messages = build_messages(
        resume=context_manager.resume,
        job_description=context_manager.job_description,
        history=history.get_messages()[:-1],  # Exclude current (it's in the prompt)
        current_question=question,
    )

    # Stream LLM answer
    await send_json(websocket, {"type": "answer_start"})

    full_answer = []
    try:
        async for token in stream_groq_chat(messages):
            full_answer.append(token)
            await send_json(websocket, {
                "type": "answer_token",
                "token": token,
            })
    except Exception as e:
        await send_json(websocket, {
            "type": "error",
            "message": f"LLM streaming error: {str(e)}",
        })

    answer_text = "".join(full_answer)
    history.add_answer(answer_text)

    await send_json(websocket, {
        "type": "answer_end",
        "full_answer": answer_text,
    })


async def handle_interview_ws(websocket: WebSocket):
    """
    Main WebSocket handler for an interview session.

    Protocol:
      Client -> Server:
        - Binary frames: complete audio segments (WebM/Opus blobs)
        - Text frames: JSON commands {"type": "clear_history" | "force_answer" | "ping"}

      Server -> Client (JSON text frames):
        - {"type": "transcript", "text": "...", "is_question": bool}
        - {"type": "answer_start"}
        - {"type": "answer_token", "token": "..."}
        - {"type": "answer_end", "full_answer": "..."}
        - {"type": "status", "message": "..."}
        - {"type": "error", "message": "..."}
    """
    await websocket.accept()
    history = ConversationHistory()
    last_transcript = ""  # Track last transcript for force_answer

    await send_json(websocket, {
        "type": "status",
        "message": "Connected! Ready to listen.",
    })

    try:
        while True:
            # Receive data from client
            message = await websocket.receive()

            # Handle text messages (commands)
            if "text" in message:
                try:
                    cmd = json.loads(message["text"])
                    if cmd.get("type") == "clear_history":
                        history.clear()
                        last_transcript = ""
                        await send_json(websocket, {
                            "type": "status",
                            "message": "History cleared.",
                        })

                    elif cmd.get("type") == "force_answer":
                        # Manual trigger — answer the last transcript
                        question = last_transcript or "Please provide a general introduction about yourself."
                        print(f"[WS] Force answer triggered for: {question[:80]}")
                        await send_json(websocket, {
                            "type": "transcript",
                            "text": question,
                            "is_question": True,
                        })
                        await generate_answer(websocket, history, question)

                    elif cmd.get("type") == "ping":
                        await send_json(websocket, {"type": "pong"})

                except json.JSONDecodeError:
                    pass
                continue

            # Handle binary messages (audio blobs)
            if "bytes" not in message:
                continue

            audio_bytes = message["bytes"]
            if not audio_bytes or len(audio_bytes) < 100:
                continue

            # ── Step 1: Transcribe via Groq Whisper ──────────────
            await send_json(websocket, {
                "type": "status",
                "message": "Transcribing...",
            })

            transcript = await transcribe_audio(audio_bytes)

            if not transcript or not transcript.strip():
                await send_json(websocket, {
                    "type": "status",
                    "message": "Connected! Ready to listen.",
                })
                continue

            # Store for force_answer
            last_transcript = transcript

            # Send transcript to client
            is_question = should_trigger_answer(transcript)
            await send_json(websocket, {
                "type": "transcript",
                "text": transcript,
                "is_question": is_question,
            })

            if not is_question:
                continue

            # ── Step 2-4: Generate answer ────────────────────────
            await generate_answer(websocket, history, transcript)

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        try:
            await send_json(websocket, {
                "type": "error",
                "message": f"Server error: {str(e)}",
            })
        except Exception:
            pass
