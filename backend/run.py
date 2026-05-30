"""
Uvicorn launcher for the ParakeetAI backend.
Run: python run.py
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    key_status = "API key set" if settings.GROQ_API_KEY else "Set GROQ_API_KEY in .env"

    print("")
    print("=" * 50)
    print("  ParakeetAI Clone - Interview Copilot")
    print("=" * 50)
    print(f"  Server:  http://{settings.HOST}:{settings.PORT}")
    print(f"  Groq:    {key_status}")
    print(f"  Model:   {settings.GROQ_LLM_MODEL}")
    print("")
    print("  Open on your phone:")
    print(f"  http://<your-pc-ip>:{settings.PORT}")
    print("=" * 50)
    print("")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
