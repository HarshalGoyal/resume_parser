from fastapi import APIRouter,File,UploadFile,HTTPException #type: ignore
from pathlib import Path
from uuid import uuid4

from app.core.logging import AppLogger
from app.storage.session_repository import SessionRepository
from app.services.resume_parsing_service import ResumeParsingService


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

    try:
        resume_parser = ResumeParsingService ()
        parsed_document = await resume_parser.parse_resume (session_id = session_id,
                                                                     upload_id  = upload_metadata["upload_id"],
                                                                     file_path = upload_metadata["saved_file_path"])
    except Exception as e:
        
        logger.error (f"failed to process file{str(e)}")
        
        raise HTTPException(status_code = 500, detail="Failed to extract the resume information")
    
    logger.info ("Resume parsed successfully")
    return {

        "message": "Resume uploaded successfully!!",
        "session_id": upload_metadata["session_id"],
        "upload_id": upload_metadata["upload_id"],
            
        "status": "Doc tree generted",
        "parsed_document": parsed_document
    }