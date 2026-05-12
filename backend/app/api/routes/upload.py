from fastapi import APIRouter, File, UploadFile # type: ignore
from ...core.logging import AppLogger
from uuid import uuid4

router = APIRouter(prefix="/resume", tags=['Resume upload'])

@router.post("/upload")
async def upload_resume(file : UploadFile = File(...)):
    loggr = AppLogger("ResumeUploader")
    loggr.info("Uploading resume...")
    file_id = str(uuid4())
    
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        loggr.error(f"Unsupported file type: {file.content_type} for file: {file.filename}")
        return {"error": "Unsupported file type. Only PDF and DOCX are allowed."}
    
    else:
        loggr.debug(f"Received file: {file.filename} with content type: {file.content_type} and size: {len(await file.read())} bytes, assigned file ID: {file_id}")
        return {"message" : "resume uploaded successfully!", "file_id": file_id}
from fastapi import (
    APIRouter,
    File,
    UploadFile,
    HTTPException
)

from pathlib import Path
from uuid import uuid4

from app.core.logging import AppLogger
from app.storage.session_repository import SessionRepository


router = APIRouter(prefix="/resume", tags=["Resume upload"])

logger = AppLogger("ResumeUploader")

session_repository = SessionRepository()

PROJECT_ROOT = Path(__file__).resolve().parents[3]

STORAGE_ROOT = (PROJECT_ROOT /"storage" /"session_data")

STORAGE_ROOT.mkdir(parents=True,exist_ok=True)


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):

    logger.info("Uploading resume...")

    allowed_types = [

        "application/pdf",

        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]

    if file.content_type not in allowed_types:

        logger.error(
            f"Unsupported file type: {file.content_type}")

        raise HTTPException(
            status_code=400,
            detail=("Unsupported file type.Only PDF and DOCX are allowed.")
        )

    file_data = await file.read()

    logger.debug( f"Received file={file.filename} size={len(file_data)} bytes")

    session_id = str(uuid4())

    logger.info(f"Generated session_id={session_id}")

    try:

        upload_metadata = (
            await session_repository.create_upload(
                session_id=session_id,
                file_name=file.filename,
                file_data=file_data
            )
        )

    except Exception as e:

        logger.error(f"Failed to create upload: {str(e)}" )

        raise HTTPException(status_code=500,detail="Failed to upload resume")


    logger.info(
        f"Resume uploaded successfully... upload_id={upload_metadata['upload_id']}"
    )

    return {

        "message": (
            "Resume uploaded successfully"
        ),

        "session_id": (
            upload_metadata["session_id"]
        ),

        "upload_id": (
            upload_metadata["upload_id"]
        ),

        "status": (
            upload_metadata["status"]
        ),

        "saved_file_path": (
            upload_metadata["saved_file_path"]
        )
    }