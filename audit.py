from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import AuditLog


class AuditLogger:
    """Service for logging system actions"""
    
    @staticmethod
    def log(
        db: Session,
        action: str,
        actor_user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create an audit log entry"""
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {}
        )
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def log_login(db: Session, user_id: int, username: str, success: bool):
        """Log login attempt"""
        AuditLogger.log(
            db,
            action="login_success" if success else "login_failed",
            actor_user_id=user_id if success else None,
            metadata={"username": username}
        )
    
    @staticmethod
    def log_request_created(db: Session, user_id: int, request_id: int):
        """Log access request creation"""
        AuditLogger.log(
            db,
            action="request_created",
            actor_user_id=user_id,
            entity_type="access_request",
            entity_id=request_id
        )
    
    @staticmethod
    def log_approval(db: Session, user_id: int, request_id: int, decision: str):
        """Log approval/denial decision"""
        AuditLogger.log(
            db,
            action=f"request_{decision}",
            actor_user_id=user_id,
            entity_type="access_request",
            entity_id=request_id,
            metadata={"decision": decision}
        )
    
    @staticmethod
    def log_status_change(db: Session, user_id: int, request_id: int, old_status: str, new_status: str):
        """Log status change"""
        AuditLogger.log(
            db,
            action="status_changed",
            actor_user_id=user_id,
            entity_type="access_request",
            entity_id=request_id,
            metadata={"old_status": old_status, "new_status": new_status}
        )


audit_logger = AuditLogger()
