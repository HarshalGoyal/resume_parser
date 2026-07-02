from fastapi import APIRouter, File, UploadFile, HTTPException  # type: ignore
from pathlib import Path

from app.core.logging import AppLogger
from app.storage.session_repository import SessionRepository
from app.services.resume_parsing_service import ResumeParsingService
from app.core.config import settings


router = APIRouter(prefix="/resume", tags=["Resume upload"])

logger = AppLogger("ResumeUploader")

session_repository = SessionRepository()


PROJECT_ROOT = Path(__file__).resolve().parents[3]

STORAGE_ROOT = Path(settings.storage_path)

STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):

    logger.info("Uploading resume...")

    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_types:
        logger.error(f"Unsupported file type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF and DOCX files are allowed.",
        )

    file_data = await file.read()

    # Additional validation by magic bytes
    is_pdf = file_data[:4] == b"%PDF"
    is_docx = file_data[:2] == b"PK"  # DOCX is a ZIP
    if not is_pdf and not is_docx:
        logger.error("Uploaded file failed magic byte validation.")
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid PDF or DOCX.",
        )

    if len(file_data) > settings.upload_max_size:
        logger.error(
            f"File size {len(file_data)} bytes exceeds maximum allowed size "
            f"{settings.upload_max_size} bytes"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"File size exceeds maximum allowed size of "
                f"{settings.upload_max_size / 1024 / 1024:.2f} MB"
            ),
        )

    logger.debug(f"Received file={file.filename} size={len(file_data)} bytes")

    session_id = await session_repository.create_session()

    logger.info(f"Generated session_id={session_id}")

    try:
        upload_metadata = await session_repository.create_upload(
            session_id=session_id,
            file_name=file.filename,
            file_data=file_data,
        )
    except Exception as e:
        logger.error(f"Failed to create upload: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload resume")

    logger.info(
        f"Resume uploaded successfully... upload_id={upload_metadata['upload_id']}"
    )

    try:
        resume_parser = ResumeParsingService()
        await resume_parser.parse_resume(
            session_id=session_id,
            upload_id=upload_metadata["upload_id"],
            file_path=upload_metadata["saved_file_path"],
        )
    except Exception as e:
        logger.error(f"failed to process file: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to extract the resume information"
        )

    logger.info("Resume parsed successfully")
    return {
        "message": "Resume uploaded successfully!!",
        "session_id": upload_metadata["session_id"],
        "upload_id": upload_metadata["upload_id"],
        "status": "parsed",
    }
