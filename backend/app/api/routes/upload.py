from fastapi import APIRouter, File, UploadFile, HTTPException

from app.core.logging import AppLogger
from app.core.exceptions import BaseResumeException
from app.api.deps import session_repository, resume_parsing_service
from app.core.config import settings
from app.schemas.response_schema import UploadAccepted, UploadLinks
from app.utils.file_utils import sniff_file_type, SUPPORTED_EXTENSIONS


router = APIRouter(prefix="/resume", tags=["Resume upload"])

logger = AppLogger("ResumeUploader")


@router.post(
    "/upload",
    response_model=UploadAccepted,
    summary="Upload a PDF/DOCX resume and parse it",
)
async def upload_resume(file: UploadFile = File(...)):
    logger.info("Uploading resume...")

    # Reject oversized uploads BEFORE buffering the whole body into memory.
    # Starlette populates UploadFile.size from the multipart part's length.
    if file.size is not None and file.size > settings.upload_max_size:
        logger.error(
            f"File size {file.size} bytes exceeds maximum allowed "
            f"size {settings.upload_max_size} bytes"
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"File size exceeds maximum allowed size of "
                f"{settings.upload_max_size / 1024 / 1024:.2f} MB"
            ),
        )

    file_data = await file.read()

    # Defensive re-check in case .size was absent (chunked / no Content-Length).
    if len(file_data) > settings.upload_max_size:
        logger.error(
            f"File size {len(file_data)} bytes exceeds maximum allowed "
            f"size {settings.upload_max_size} bytes"
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"File size exceeds maximum allowed size of "
                f"{settings.upload_max_size / 1024 / 1024:.2f} MB"
            ),
        )

    # Authoritative type check via magic bytes — the client Content-Type header
    # is untrusted and easily spoofed.
    file_type = sniff_file_type(file_data)
    if file_type not in SUPPORTED_EXTENSIONS:
        logger.error(
            f"Unsupported or spoofed file content "
            f"(declared type={file.content_type})"
        )
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF and DOCX are allowed.",
        )

    logger.debug(
        f"Received file={file.filename!r} type={file_type} "
        f"size={len(file_data)} bytes"
    )

    session_id = await session_repository.create_session()
    logger.info(f"Generated session_id={session_id}")

    try:
        upload_metadata = await session_repository.create_upload(
            session_id=session_id,
            display_name=file.filename,
            file_type=file_type,
            file_data=file_data,
        )
    except Exception as e:
        logger.exception(f"Failed to create upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload resume") from e

    logger.info(
        f"Resume uploaded successfully... upload_id={upload_metadata['upload_id']}"
    )

    try:
        await resume_parsing_service.parse_resume(
            session_id=session_id,
            upload_id=upload_metadata["upload_id"],
            file_path=upload_metadata["saved_file_path"],
            file_type=file_type,
        )
    except BaseResumeException:
        # Let the app-level handler translate structured exceptions into a
        # proper error-code response.
        raise
    except Exception as e:
        logger.exception(f"Failed to process file: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to extract the resume information"
        ) from e

    logger.info("Resume parsed successfully")
    base = f"/resume/{session_id}/{upload_metadata['upload_id']}"
    return UploadAccepted(
        message="Resume uploaded successfully!!",
        session_id=upload_metadata["session_id"],
        upload_id=upload_metadata["upload_id"],
        status="parsed",
        links=UploadLinks(result=base, status=f"{base}/status"),
    )
