"""File-related helpers: safe naming and content-based type detection.

These utilities exist to keep untrusted, client-supplied file data from
influencing where we write on disk (path traversal) or what we believe a file
to be (spoofed Content-Type headers).
"""

from pathlib import PurePosixPath, PureWindowsPath


# Canonical file types the platform understands, mapped to their stored extension.
SUPPORTED_EXTENSIONS: dict[str, str] = {
    "pdf": ".pdf",
    "docx": ".docx",
}

# Leading magic bytes used to identify a file from its content rather than its
# (spoofable) Content-Type header or extension. DOCX is an OOXML zip container,
# so it shares the generic zip signature; we treat "zip" as a DOCX candidate.
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF-", "pdf"),
    (b"PK\x03\x04", "docx"),
]


def sniff_file_type(data: bytes) -> str | None:
    """Return the canonical file type ('pdf' | 'docx') inferred from magic bytes.

    Returns None if the content does not match any supported signature. This is
    the authoritative type check — never trust the client Content-Type header.
    """
    for signature, file_type in _MAGIC_SIGNATURES:
        if data.startswith(signature):
            return file_type
    return None


def safe_stored_filename(file_type: str) -> str:
    """Return a server-controlled filename for storing an upload of ``file_type``.

    The original client filename is NEVER used to build a path — it can contain
    traversal sequences (``../``), absolute paths, or OS-specific separators.
    We store every upload under a fixed name keyed only by its validated type.
    """
    extension = SUPPORTED_EXTENSIONS.get(file_type)
    if extension is None:
        raise ValueError(f"Unsupported file type: {file_type!r}")
    return f"original{extension}"


def sanitize_display_name(original: str | None) -> str:
    """Reduce a client-supplied filename to a bare basename for display/metadata.

    The result is stored as metadata only and must not be used to construct a
    filesystem path. Strips directory components using both POSIX and Windows
    separator rules so a name crafted on one OS can't traverse on another.
    """
    if not original:
        return "resume"
    # Take the basename under both separator conventions and keep the shorter,
    # i.e. the one that actually stripped a directory component.
    posix_name = PurePosixPath(original).name
    windows_name = PureWindowsPath(original).name
    name = min((posix_name, windows_name), key=len) or "resume"
    return name.strip() or "resume"
