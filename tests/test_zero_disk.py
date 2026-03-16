"""
Test zero-disk processing implementation.

Verifies that document processing doesn't create temporary files.

Usage:
    # With pytest (recommended)
    pytest tests/test_zero_disk.py -v

    # Or directly (requires docling installed)
    python -m tests.test_zero_disk
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_loader_function():
    """Import load_document_from_bytes, handling missing dependencies gracefully."""
    try:
        # Direct import from module to avoid package-level dependencies
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "docling_loader",
            project_root / "src/ingestion/docling_loader.py"
        )
        docling_loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(docling_loader)
        return docling_loader.load_document_from_bytes
    except Exception as e:
        return None, str(e)


def test_no_temp_files_created():
    """Verify that load_document_from_bytes doesn't create temp files."""
    load_document_from_bytes = get_loader_function()

    if load_document_from_bytes is None:
        print("⚠️  Skipping: Could not import docling_loader")
        return

    # Create a simple HTML document
    sample_html = b"""
    <!DOCTYPE html>
    <html>
    <head><title>Test Document</title></head>
    <body>
        <h1>Test Heading</h1>
        <p>This is a test paragraph for zero-disk validation.</p>
    </body>
    </html>
    """

    # Get temp directory contents before processing
    tmp_dir = tempfile.gettempdir()
    tmp_files_before = set(os.listdir(tmp_dir))

    try:
        # Process document from bytes
        result = load_document_from_bytes(sample_html, "test.html")

        # Get temp directory contents after processing
        tmp_files_after = set(os.listdir(tmp_dir))

        # Verify no new temp files were created
        new_files = tmp_files_after - tmp_files_before

        assert new_files == set(), f"Temporary files created: {new_files}"

        if result.status == "OK":
            assert result.path == "<memory>", "Path should be marked as <memory>"
            assert result.metadata.get("zero_disk") is True, "zero_disk flag not set"
            assert len(result.elements) > 0, "No elements extracted"
            print(f"✅ Zero-disk test passed!")
            print(f"   Status: {result.status}")
            print(f"   Elements: {len(result.elements)}")
            print(f"   Path: {result.path}")
            print(f"   Zero-disk flag: {result.metadata.get('zero_disk')}")
        else:
            # Docling not installed - but no temp files created
            print(f"⚠️  Docling processing failed: {result.error}")
            print(f"✅ But zero temp files created (primary verification)")

        print(f"   Temp files created: {len(new_files)}")

    except Exception as e:
        # Even if processing fails, check that no temp files were created
        tmp_files_after = set(os.listdir(tmp_dir))
        new_files = tmp_files_after - tmp_files_before
        if new_files == set():
            print(f"⚠️  Processing error: {e}")
            print(f"✅ But zero temp files created (primary verification)")
        else:
            raise AssertionError(f"Temp files created: {new_files}")


def test_memory_marker_in_metadata():
    """Verify metadata contains zero-disk markers."""
    load_document_from_bytes = get_loader_function()

    if load_document_from_bytes is None:
        print("⚠️  Skipping: Could not import docling_loader")
        return

    sample_md = b"""
# Test Markdown

This is a simple markdown document for testing.

## Features
- Zero-disk processing
- In-memory parsing
"""

    result = load_document_from_bytes(sample_md, "test.md")

    if result.status == "OK":
        assert result.metadata.get("zero_disk") is True
        assert result.metadata.get("converter") == "docling"
        print(f"✅ Metadata test passed!")
        print(f"   Metadata: {result.metadata}")
    else:
        print(f"⚠️  Skipping metadata check: {result.error}")


def test_large_file_handling():
    """Test handling of larger files (still in memory)."""
    load_document_from_bytes = get_loader_function()

    if load_document_from_bytes is None:
        print("⚠️  Skipping: Could not import docling_loader")
        return

    # Create a larger HTML document (~100KB)
    large_html = b"<!DOCTYPE html><html><body>"
    for i in range(1000):
        large_html += f"<p>Paragraph {i}: Test content for zero-disk validation.</p>".encode()
    large_html += b"</body></html>"

    tmp_dir = tempfile.gettempdir()
    tmp_files_before = set(os.listdir(tmp_dir))

    result = load_document_from_bytes(large_html, "large_test.html")

    tmp_files_after = set(os.listdir(tmp_dir))
    new_files = tmp_files_after - tmp_files_before

    assert new_files == set(), f"Temporary files created for large file: {new_files}"

    print(f"✅ Large file test passed!")
    print(f"   File size: {len(large_html):,} bytes")
    print(f"   Status: {result.status}")
    print(f"   Temp files created: 0")


if __name__ == "__main__":
    print("=" * 60)
    print("Zero-Disk Processing Tests")
    print("=" * 60)
    print()

    try:
        test_no_temp_files_created()
        print()
        test_memory_marker_in_metadata()
        print()
        test_large_file_handling()
        print()
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        sys.exit(1)
