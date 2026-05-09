from fastapi import APIRouter, File, UploadFile # type: ignore
from ...core.logging import AppLogger 

router = APIRouter(prefix="/resume", tags=['Resume upload'])

@router.post("/upload")
async def upload_resume(file : UploadFile = File(...)):
    loggr = AppLogger("ResumeUploader")
    loggr.info("Uploading resume...")
    
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        loggr.error(f"Unsupported file type: {file.content_type} for file: {file.filename}")
        return {"error": "Unsupported file type. Only PDF and DOCX are allowed."}
    
    else:
        loggr.debug(f"Received file: {file.filename} with content type: {file.content_type} and size: {len(await file.read())} bytes")
        return {"message" : "resume uploaded successfully!"}
