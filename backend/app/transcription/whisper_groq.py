"""
Groq Whisper ASR client.
Sends audio blobs (WebM/Opus) directly to Groq's transcription API.
No local FFmpeg or model dependencies required.
"""

import io
import httpx
from app.config import settings


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
    """
    Send an audio blob to Groq's Whisper API and return the transcription.

    Args:
        audio_bytes: Raw audio file bytes (WebM/Opus from browser MediaRecorder).
        mime_type: MIME type of the audio file.

    Returns:
        Transcribed text string. Empty string if no speech detected.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return ""

    # Determine file extension from MIME type
    ext_map = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/wav": "wav"}
    ext = ext_map.get(mime_type, "webm")

    # Build the multipart form data
    # Groq's API expects a file upload similar to OpenAI's format
    files = {
        "file": (f"audio.{ext}", io.BytesIO(audio_bytes), mime_type),
    }
    data = {
        "model": settings.GROQ_ASR_MODEL,
        "language": "en",
        "response_format": "text",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                files=files,
                data=data,
            )
            response.raise_for_status()
            text = response.text.strip()
            return text
    except httpx.HTTPStatusError as e:
        print(f"[ASR] Groq API error {e.response.status_code}: {e.response.text}")
        return ""
    except Exception as e:
        print(f"[ASR] Transcription error: {e}")
        return ""
