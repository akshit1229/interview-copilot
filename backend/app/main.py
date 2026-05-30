"""
FastAPI application entry point.
Serves the phone client, REST API for uploads, and WebSocket for interview streaming.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from pathlib import Path
import os

from app.config import settings
from app.context.manager import context_manager
from app.ws.handler import handle_interview_ws


class PermissiveCORSMiddleware:
    """
    Custom CORS middleware that allows all origins for both HTTP and WebSocket.
    Starlette's built-in CORSMiddleware rejects WebSocket upgrades when Origin
    doesn't exactly match — this middleware permits all connections.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            # Check for CORS preflight
            headers = dict(scope.get("headers", []))
            if scope.get("method") == "OPTIONS":
                response_headers = [
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"*"),
                    (b"access-control-max-age", b"86400"),
                ]
                await send({"type": "http.response.start", "status": 200, "headers": response_headers})
                await send({"type": "http.response.body", "body": b""})
                return

            # For regular HTTP, inject CORS headers into the response
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"access-control-allow-origin", b"*"))
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_cors)
        else:
            # WebSocket and other protocols — pass through without CORS checks
            await self.app(scope, receive, send)


# ── App Initialization ───────────────────────────────────────────
app = FastAPI(
    title="ParakeetAI Clone",
    description="Real-time AI interview copilot — phone browser edition",
    version="1.0.0",
)

# Custom CORS that doesn't block WebSocket connections
app.add_middleware(PermissiveCORSMiddleware)


# ── WebSocket Endpoint ───────────────────────────────────────────
@app.websocket("/ws/interview")
async def websocket_interview(websocket: WebSocket):
    """Main WebSocket endpoint for real-time interview assistance."""
    await handle_interview_ws(websocket)


# ── REST API: Health Check ────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "groq_key_set": bool(settings.GROQ_API_KEY),
        "resume_loaded": bool(context_manager.resume),
        "jd_loaded": bool(context_manager.job_description),
    }


# ── REST API: Get Context ────────────────────────────────────────
@app.get("/api/context")
async def get_context():
    return {
        "resume": context_manager.resume,
        "job_description": context_manager.job_description,
    }


# ── REST API: Update Context (Text) ──────────────────────────────
@app.post("/api/context")
async def update_context(
    resume: str = Form(default=None),
    job_description: str = Form(default=None),
):
    if resume is not None:
        context_manager.update_resume(resume)
    if job_description is not None:
        context_manager.update_job_description(job_description)
    return {"status": "updated"}


# ── REST API: Upload Resume (PDF or Text) ─────────────────────────
@app.post("/api/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename and file.filename.lower().endswith(".pdf"):
        try:
            text = context_manager.extract_pdf_text(content)
            context_manager.update_resume(text)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Treat as plain text / markdown
        context_manager.update_resume(content.decode("utf-8"))

    return {
        "status": "uploaded",
        "type": "resume",
        "chars": len(context_manager.resume),
        "preview": context_manager.resume[:200] + "...",
    }


# ── REST API: Upload Job Description (PDF or Text) ────────────────
@app.post("/api/upload/jd")
async def upload_jd(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename and file.filename.lower().endswith(".pdf"):
        try:
            text = context_manager.extract_pdf_text(content)
            context_manager.update_job_description(text)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        context_manager.update_job_description(content.decode("utf-8"))

    return {
        "status": "uploaded",
        "type": "job_description",
        "chars": len(context_manager.job_description),
        "preview": context_manager.job_description[:200] + "...",
    }


# ── Serve Phone Client (Static Files) ────────────────────────────
PHONE_CLIENT_DIR = Path(__file__).parent.parent.parent / "phone-client"

if PHONE_CLIENT_DIR.exists():
    @app.get("/")
    async def serve_phone_client():
        return FileResponse(str(PHONE_CLIENT_DIR / "index.html"))

    # Mount static files for css/ and js/ directories
    app.mount("/css", StaticFiles(directory=str(PHONE_CLIENT_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(PHONE_CLIENT_DIR / "js")), name="js")

    @app.get("/manifest.json")
    async def serve_manifest():
        return FileResponse(str(PHONE_CLIENT_DIR / "manifest.json"))
