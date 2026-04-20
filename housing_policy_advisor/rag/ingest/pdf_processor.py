"""PDF text extraction with page-level tracking."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Extracts text from PDF files page-by-page."""

    def __init__(self) -> None:
        self.supported_formats = {".pdf"}

    def extract_text(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Return list of {page_number, text, metadata} dicts for each page."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if pdf_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {pdf_path.suffix}")

        pages_data: List[Dict[str, Any]] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"Processing {pdf_path.name} ({total_pages} pages)")

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        text = page.extract_text() or ""
                        if not text.strip():
                            logger.warning(f"Page {page_num} in {pdf_path.name} has no extractable text")
                        text = self._clean_text(text)
                        pages_data.append({
                            "page_number": page_num,
                            "text": text,
                            "metadata": {
                                "source_file": pdf_path.name,
                                "source_path": str(pdf_path),
                                "total_pages": total_pages,
                                "page_number": page_num,
                            },
                        })
                    except Exception as e:
                        logger.error(f"Error processing page {page_num} in {pdf_path.name}: {e}")
                        continue

                logger.info(f"Extracted text from {len(pages_data)} pages in {pdf_path.name}")
        except Exception as e:
            logger.error(f"Error opening PDF {pdf_path}: {e}")
            raise

        return pages_data

    def get_pdf_info(self, pdf_path: Path) -> Dict[str, Any]:
        """Return basic info dict for a PDF (name, path, pages, size)."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return {
                    "filename": pdf_path.name,
                    "file_path": str(pdf_path),
                    "total_pages": len(pdf.pages),
                    "file_size": pdf_path.stat().st_size,
                }
        except Exception as e:
            logger.error(f"Error getting PDF info for {pdf_path}: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        cleaned = "\n".join(lines)
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        return cleaned
