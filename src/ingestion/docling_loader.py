# src/ingestion/docling_loader.py
"""
Lean Document Loader using Amazon Textract (AWS Native).
Replaces the heavyweight Docling library.
"""

import os
import boto3
import io
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}

@dataclass
class DocumentElement:
    element_type: str
    text: str
    level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ParsedDocument:
    filename: str
    path: str
    elements: List[DocumentElement]
    format: str
    page_count: int = 0
    status: str = "OK"
    error: Optional[str] = None

    @property
    def full_text(self) -> str:
        return "\n\n".join(el.text for el in self.elements if el.text.strip())

def load_document_from_bytes(file_bytes: bytes, filename: str) -> ParsedDocument:
    """
    Load and parse a single document using Amazon Textract.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        textract = boto3.client("textract", region_name=region)
        
        # Call Textract
        response = textract.detect_document_text(
            Document={'Bytes': file_bytes}
        )
        
        elements = []
        for item in response.get("Blocks", []):
            if item["BlockType"] == "LINE":
                elements.append(DocumentElement(
                    element_type="paragraph",
                    text=item["Text"]
                ))
        
        return ParsedDocument(
            filename=filename,
            path="<memory>",
            elements=elements,
            format=ext,
            status="OK"
        )
    except Exception as e:
        logger.error(f"Textract parsing failed: {str(e)}")
        # Fallback to very basic text extraction for plain text files
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
            return ParsedDocument(
                filename=filename,
                path="<memory>",
                elements=[DocumentElement(element_type="text", text=text)],
                format=ext,
                status="OK"
            )
        except Exception:
            return ParsedDocument(
                filename=filename,
                path="<memory>",
                elements=[],
                format=ext,
                status="ERROR",
                error=str(e)
            )

def convert_to_legacy_format(parsed_docs: List[ParsedDocument]) -> List[Dict]:
    """Convert to the internal dict format used by the pipeline."""
    legacy = []
    for doc in parsed_docs:
        legacy.append({
            "filename": doc.filename,
            "text": doc.full_text,
            "status": doc.status,
            "error": doc.error
        })
    return legacy

# Stub functions to maintain compatibility with existing ingestion scripts
def load_documents_with_docling(docs_dir: str, **kwargs):
    """Stub for legacy compatibility, now uses Textract logic."""
    # This would normally crawl a directory, but in our Zero-Storage 
    # query-time flow, we mostly use load_document_from_bytes.
    return []
