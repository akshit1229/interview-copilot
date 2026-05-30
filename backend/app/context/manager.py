"""
Context manager for Resume and Job Description documents.
Supports loading from Markdown files and PDF uploads.
"""

import os
from pathlib import Path
from typing import Optional
from app.config import settings

# Lazy import PyPDF2 to avoid hard dependency at module level
_pypdf2_available = False
try:
    from PyPDF2 import PdfReader
    _pypdf2_available = True
except ImportError:
    pass


class ContextManager:
    """Manages resume and job description context documents."""

    def __init__(self):
        self.context_dir = Path(settings.CONTEXT_DIR)
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self._resume: str = ""
        self._job_description: str = ""
        self._load_from_files()

    def _load_from_files(self):
        """Load context documents from disk on startup."""
        resume_path = self.context_dir / "resume.md"
        jd_path = self.context_dir / "job_description.md"

        if resume_path.exists():
            self._resume = resume_path.read_text(encoding="utf-8").strip()
            print(f"[Context] Loaded resume ({len(self._resume)} chars)")

        if jd_path.exists():
            self._job_description = jd_path.read_text(encoding="utf-8").strip()
            print(f"[Context] Loaded JD ({len(self._job_description)} chars)")

    @property
    def resume(self) -> str:
        return self._resume

    @property
    def job_description(self) -> str:
        return self._job_description

    def update_resume(self, text: str):
        """Update resume text and persist to disk."""
        self._resume = text.strip()
        (self.context_dir / "resume.md").write_text(self._resume, encoding="utf-8")
        print(f"[Context] Resume updated ({len(self._resume)} chars)")

    def update_job_description(self, text: str):
        """Update job description text and persist to disk."""
        self._job_description = text.strip()
        (self.context_dir / "job_description.md").write_text(
            self._job_description, encoding="utf-8"
        )
        print(f"[Context] JD updated ({len(self._job_description)} chars)")

    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """
        Extract text content from a PDF file.

        Args:
            pdf_bytes: Raw PDF file bytes.

        Returns:
            Extracted text content.

        Raises:
            RuntimeError: If PyPDF2 is not installed.
        """
        if not _pypdf2_available:
            raise RuntimeError(
                "PyPDF2 is required for PDF processing. "
                "Install it with: pip install PyPDF2"
            )

        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())

        full_text = "\n\n".join(pages_text)
        print(f"[Context] Extracted {len(full_text)} chars from PDF ({len(reader.pages)} pages)")
        return full_text

    async def upload_resume_pdf(self, pdf_bytes: bytes):
        """Process an uploaded resume PDF and store the extracted text."""
        text = self.extract_pdf_text(pdf_bytes)
        self.update_resume(text)
        return text

    async def upload_jd_pdf(self, pdf_bytes: bytes):
        """Process an uploaded job description PDF and store the extracted text."""
        text = self.extract_pdf_text(pdf_bytes)
        self.update_job_description(text)
        return text


# Singleton instance
context_manager = ContextManager()
