"""
Uvicorn launcher for the ParakeetAI backend.

Usage:
  python run.py          # HTTP on port 8000 (desktop browser only)
  python run.py --https  # HTTPS on port 8443 (required for phone microphone)

First time HTTPS setup:
  python generate_cert.py   # generates cert.pem + key.pem
  python run.py --https
"""

import sys
import os
import uvicorn
from app.config import settings

USE_HTTPS = "--https" in sys.argv
CERT_FILE = os.path.join(os.path.dirname(__file__), "cert.pem")
KEY_FILE  = os.path.join(os.path.dirname(__file__), "key.pem")

if __name__ == "__main__":
    key_status = "Set" if settings.GROQ_API_KEY else "MISSING - add to .env"
    port = 8443 if USE_HTTPS else settings.PORT
    protocol = "https" if USE_HTTPS else "http"

    print("")
    print("=" * 52)
    print("  ParakeetAI Clone - Interview Copilot")
    print("=" * 52)
    print(f"  Mode:    {'HTTPS (phone-ready)' if USE_HTTPS else 'HTTP (desktop only)'}")
    print(f"  Server:  {protocol}://0.0.0.0:{port}")
    print(f"  Groq:    {key_status}")
    print(f"  Model:   {settings.GROQ_LLM_MODEL}")
    print("")

    if USE_HTTPS:
        if not os.path.exists(CERT_FILE):
            print("  ERROR: cert.pem not found!")
            print("  Run first:  python generate_cert.py")
            sys.exit(1)
        print("  Open on your PHONE (accept the security warning):")
        print(f"  https://<your-pc-ip>:{port}")
    else:
        print("  For PHONE microphone access, use HTTPS mode:")
        print("    python generate_cert.py")
        print("    python run.py --https")

    print("=" * 52)
    print("")

    ssl_kwargs = {}
    if USE_HTTPS:
        ssl_kwargs = {"ssl_certfile": CERT_FILE, "ssl_keyfile": KEY_FILE}

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=port,
        reload=True,
        log_level="info",
        **ssl_kwargs,
    )
