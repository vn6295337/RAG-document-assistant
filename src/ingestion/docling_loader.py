"""
Docling-based document loader for multi-format document processing.

Supports: PDF, DOCX, PPTX, HTML, images, and Markdown.
Provides structure-aware parsing with table extraction and hierarchy preservation.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx",
    ".html", ".htm",
    ".md", ".markdown",
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp"
}


@dataclass
class DocumentElement:
    """Represents a structural element in a document."""
    element_type: str  # paragraph, table, heading, list, code, image
    text: str
    level: int = 0  # heading level (1-6) or nesting depth
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Result of parsing a document with Docling."""
    filename: str
    path: str
    elements: List[DocumentElement]
    format: str
    page_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "OK"
    error: Optional[str] = None

    @property
    def full_text(self) -> str:
        """Get concatenated text from all elements."""
        return "\n\n".join(el.text for el in self.elements if el.text.strip())

    @property
    def chars(self) -> int:
        return len(self.full_text)

    @property
    def words(self) -> int:
        return len(self.full_text.split())


def _get_docling_converter():
    """Lazy load Docling converter to avoid import overhead."""
    try:
        from docling.document_converter import DocumentConverter
        return DocumentConverter()
    except ImportError as e:
        logger.error(f"Docling not installed: {e}")
        raise ImportError(
            "Docling is required for multi-format document loading. "
            "Install with: pip install docling"
        ) from e


def _extract_elements_from_docling(doc_result) -> List[DocumentElement]:
    """
    Extract structured elements from a Docling conversion result.

    Args:
        doc_result: Docling ConversionResult object

    Returns:
        List of DocumentElement objects
    """
    elements = []

    try:
        # Get the DoclingDocument
        docling_doc = doc_result.document

        # Iterate through document items
        for item, level in docling_doc.iterate_items():
            item_type = item.__class__.__name__.lower()

            # Map Docling item types to our element types
            if "heading" in item_type or "title" in item_type:
                el_type = "heading"
                el_level = getattr(item, "level", 1)
            elif "table" in item_type:
                el_type = "table"
                el_level = 0
            elif "list" in item_type:
                el_type = "list"
                el_level = level
            elif "code" in item_type:
                el_type = "code"
                el_level = 0
            elif "image" in item_type or "figure" in item_type:
                el_type = "image"
                el_level = 0
            else:
                el_type = "paragraph"
                el_level = level

            # Extract text content
            text = ""
            if hasattr(item, "text") and item.text:
                text = item.text
            elif hasattr(item, "export_to_markdown"):
                try:
                    # Some items require doc parameter
                    text = item.export_to_markdown(docling_doc)
                except TypeError:
                    try:
                        text = item.export_to_markdown()
                    except Exception:
                        text = str(item) if hasattr(item, "__str__") else ""
            elif hasattr(item, "__str__"):
                text = str(item)

            if text and text.strip():
                elements.append(DocumentElement(
                    element_type=el_type,
                    text=text.strip(),
                    level=el_level,
                    metadata={
                        "original_type": item_type,
                        "depth": level
                    }
                ))

    except Exception as e:
        logger.warning(f"Error extracting elements: {e}")
        # Fallback: try to get markdown export
        try:
            md_text = doc_result.document.export_to_markdown()
            if md_text:
                elements.append(DocumentElement(
                    element_type="paragraph",
                    text=md_text,
                    level=0
                ))
        except Exception:
            pass

    return elements


def load_document_with_docling(file_path: str) -> ParsedDocument:
    """
    Load a single document using Docling.

    Args:
        file_path: Path to the document file

    Returns:
        ParsedDocument with extracted structure and content
    """
    path = Path(file_path)

    if not path.exists():
        return ParsedDocument(
            filename=path.name,
            path=str(path),
            elements=[],
            format=path.suffix.lower(),
            status="ERROR",
            error=f"File not found: {file_path}"
        )

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return ParsedDocument(
            filename=path.name,
            path=str(path),
            elements=[],
            format=ext,
            status="SKIPPED",
            error=f"Unsupported format: {ext}"
        )

    try:
        converter = _get_docling_converter()
        result = converter.convert(str(path))

        elements = _extract_elements_from_docling(result)

        # Get page count if available
        page_count = 0
        try:
            if hasattr(result.document, "pages"):
                page_count = len(result.document.pages)
        except Exception:
            pass

        return ParsedDocument(
            filename=path.name,
            path=str(path),
            elements=elements,
            format=ext,
            page_count=page_count,
            metadata={
                "converter": "docling",
                "element_count": len(elements)
            },
            status="OK"
        )

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return ParsedDocument(
            filename=path.name,
            path=str(path),
            elements=[],
            format=ext,
            status="ERROR",
            error=str(e)
        )


def load_documents_with_docling(
    dir_path: str,
    extensions: Optional[List[str]] = None,
    max_chars: int = 50000,
    recursive: bool = False
) -> List[ParsedDocument]:
    """
    Load multiple documents from a directory using Docling.

    Args:
        dir_path: Path to directory containing documents
        extensions: List of extensions to process (default: all supported)
        max_chars: Maximum characters per document (skip larger files)
        recursive: Whether to search subdirectories

    Returns:
        List of ParsedDocument objects
    """
    path = Path(dir_path).expanduser()

    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if extensions is None:
        extensions = list(SUPPORTED_EXTENSIONS)
    else:
        extensions = [e if e.startswith(".") else f".{e}" for e in extensions]

    # Find all matching files
    files = []
    for ext in extensions:
        pattern = f"**/*{ext}" if recursive else f"*{ext}"
        files.extend(path.glob(pattern))

    files = sorted(set(files))

    documents = []
    for file_path in files:
        doc = load_document_with_docling(str(file_path))

        # Check size limit
        if doc.status == "OK" and doc.chars > max_chars:
            doc.status = "SKIPPED_TOO_LARGE"
            doc.error = f"Document exceeds {max_chars} chars ({doc.chars})"
            doc.elements = []

        documents.append(doc)

    return documents


def convert_to_legacy_format(docs: List[ParsedDocument]) -> List[Dict]:
    """
    Convert ParsedDocument list to legacy format for backward compatibility.

    Args:
        docs: List of ParsedDocument objects

    Returns:
        List of dicts matching load_markdown_docs output format
    """
    legacy = []
    for doc in docs:
        legacy.append({
            "filename": doc.filename,
            "path": doc.path,
            "text": doc.full_text if doc.status == "OK" else None,
            "chars": doc.chars,
            "words": doc.words,
            "status": doc.status,
            "format": doc.format,
            "elements": doc.elements,  # Additional: structured elements
            "page_count": doc.page_count,
            "metadata": doc.metadata
        })
    return legacy


def print_summary(docs: List[ParsedDocument]):
    """Print summary of loaded documents."""
    if not docs:
        print("No documents found or all were skipped.")
        return

    print(f"{'FILENAME':40} {'FORMAT':8} {'STATUS':20} {'CHARS':>8} {'ELEMENTS':>8}")
    print("-" * 90)

    for d in docs:
        name = d.filename[:40]
        fmt = d.format[:8]
        status = d.status[:20]
        chars = d.chars
        elements = len(d.elements)
        print(f"{name:40} {fmt:8} {status:20} {chars:8d} {elements:8d}")

    ok_count = sum(1 for d in docs if d.status == "OK")
    skipped = len(docs) - ok_count
    print("-" * 90)
    print(f"Total: {len(docs)}  OK: {ok_count}  Skipped/Errors: {skipped}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Load documents using Docling for RAG ingestion."
    )
    parser.add_argument("dir", help="Directory containing documents")
    parser.add_argument(
        "--extensions", "-e",
        nargs="+",
        default=None,
        help="File extensions to process (default: all supported)"
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=50000,
        help="Max characters to accept (default: 50000)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Search subdirectories recursively"
    )

    args = parser.parse_args()

    docs = load_documents_with_docling(
        args.dir,
        extensions=args.extensions,
        max_chars=args.max_chars,
        recursive=args.recursive
    )
    print_summary(docs)
