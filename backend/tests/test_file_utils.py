"""Unit tests for upload-safety helpers: magic-byte sniffing and safe naming."""

import pytest

from app.utils.file_utils import (
    sniff_file_type,
    safe_stored_filename,
    sanitize_display_name,
)


def test_sniff_pdf_and_docx():
    assert sniff_file_type(b"%PDF-1.7 rest of file") == "pdf"
    assert sniff_file_type(b"PK\x03\x04 zip container") == "docx"


def test_sniff_rejects_other_content():
    assert sniff_file_type(b"<html><body>hi</body></html>") is None
    assert sniff_file_type(b"") is None
    assert sniff_file_type(b"MZ\x90\x00 exe header") is None


def test_safe_stored_filename():
    assert safe_stored_filename("pdf") == "original.pdf"
    assert safe_stored_filename("docx") == "original.docx"
    with pytest.raises(ValueError):
        safe_stored_filename("exe")


@pytest.mark.parametrize(
    "hostile, expected",
    [
        ("../../../etc/passwd", "passwd"),
        ("..\\..\\windows\\evil.pdf", "evil.pdf"),
        ("/absolute/path/name.docx", "name.docx"),
        ("C:\\temp\\resume.pdf", "resume.pdf"),
        (None, "resume"),
        ("", "resume"),
        ("   ", "resume"),
    ],
)
def test_sanitize_display_name_strips_traversal(hostile, expected):
    assert sanitize_display_name(hostile) == expected
