import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings from environment variables"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/banner_access")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-min-32-chars-long")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "encryption-key-change-in-production-must-be-32-url-safe-base64-chars")
    SESSION_COOKIE_NAME: str = "banner_session"
    SESSION_MAX_AGE: int = 3600 * 8  # 8 hours
    
   
    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@winthrop.edu")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_ENABLED: bool = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    HELPDESK_EMAIL: str = os.getenv("HELPDESK_EMAIL", "helpdesk@winthrop.edu")
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = os.getenv(
        "ALLOWED_UPLOAD_EXTENSIONS", 
        ".pdf,.docx,.jpeg,.jpg,.png"
    ).split(",")
    UPLOAD_DIR: str = "/app/data/uploads"
    
   
  # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_NAME: str = "Winthrop University - Banner Access Tracker"
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    # Roles
    ROLE_GRANTEE: str = "Grantee"
    ROLE_GRANTOR: str = "Grantor"
    ROLE_ADMIN: str = "Administrator"
    ROLE_SUPERUSER: str = "SuperUser"
    
    # Status values
    STATUS_PENDING: str = "Pending"
    STATUS_IN_PROGRESS: str = "In Progress"
    STATUS_APPROVED: str = "Approved"
    STATUS_REJECTED: str = "Rejected"


settings = Settings()
