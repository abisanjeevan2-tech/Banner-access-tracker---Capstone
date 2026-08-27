import os
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException
from app.config import settings


class FileUploadService:
    """Handle file uploads and validation"""
    
    @staticmethod
    def validate_file(file: UploadFile) -> None:
        """Validate uploaded file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {ext} not allowed. Allowed types: {', '.join(settings.ALLOWED_UPLOAD_EXTENSIONS)}"
            )
    
    @staticmethod
    async def save_file(file: UploadFile, request_id: int) -> Tuple[str, str]:
        """
        Save uploaded file and return (storage_path, original_filename)
        """
        FileUploadService.validate_file(file)
        
        # Create request-specific directory
        request_dir = os.path.join(settings.UPLOAD_DIR, str(request_id))
        os.makedirs(request_dir, exist_ok=True)
        
        # Generate unique filename
        ext = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{ext}"
        storage_path = os.path.join(request_dir, unique_filename)
        
        # Save file
        content = await file.read()
        
        # Check file size
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
        
        with open(storage_path, "wb") as f:
            f.write(content)
        
        return storage_path, file.filename
    
    @staticmethod
    def delete_file(storage_path: str) -> None:
        """Delete a file from storage"""
        if os.path.exists(storage_path):
            os.remove(storage_path)


file_upload_service = FileUploadService()
