from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, Query
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, AccessRequest, Form as FormModel, PermissionGroup, Attachment, FormPDF
from app.routers.auth import require_auth, require_role, get_current_user
from app.utils.encryption import encryptor
from app.utils.file_upload import file_upload_service
from app.utils.email import email_service
from app.utils.audit import audit_logger
from app.config import settings
import re
import base64

router = APIRouter(prefix="/grantee", tags=["grantee"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def grantee_dashboard(
    request: Request,
    page: int = Query(1),
    user: User = Depends(require_role([settings.ROLE_GRANTEE, settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    per_page = 15
    query = db.query(AccessRequest).filter(
        AccessRequest.applicant_user_id == user.id
    )
    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    requests = query.order_by(AccessRequest.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return templates.TemplateResponse(
        "grantee/dashboard.html",
        {
            "request": request,
            "user": user,
            "requests": requests,
            "page": page,
            "total_pages": total_pages,
            "total": total
        }
    )


@router.get("/submit", response_class=HTMLResponse)
async def submit_request_form(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_GRANTEE, settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """Display request submission form"""
    forms = db.query(FormModel).filter(FormModel.active == True).all()
    permission_groups = db.query(PermissionGroup).filter(PermissionGroup.active == True).all()
    
    return templates.TemplateResponse(
        "grantee/submit.html",
        {
            "request": request,
            "user": user,
            "forms": forms,
            "permission_groups": permission_groups
        }
    )


def validate_cwid(cwid: str) -> bool:
    """Validate CWID format (assuming 8 digits)"""
    return bool(re.match(r'^\d{8}$', cwid))


@router.post("/submit")
async def submit_request(
    request: Request,
    form_ids: List[int] = Form(...),
    access_type: str = Form(...),
    secure_notes: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
    user: User = Depends(require_role([settings.ROLE_GRANTEE, settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """Process request submission"""
    # Validate forms exist
    forms = db.query(FormModel).filter(FormModel.id.in_(form_ids)).all()
    if not forms or len(forms) != len(form_ids):
        return templates.TemplateResponse(
            "grantee/submit.html",
            {
                "request": request,
                "user": user,
                "forms": db.query(FormModel).filter(FormModel.active == True).all(),
                "error": "Invalid forms selected."
            }
        )

# Validate access type
    if access_type not in ["Read", "Read/Write"]:
        return templates.TemplateResponse(
            "grantee/submit.html",
            {
                "request": request,
                "user": user,
                "forms": db.query(FormModel).filter(FormModel.active == True).all(),
                "error": "Please select a valid access type."
            }
        )


    # Encrypt secure notes if provided
    encrypted_notes = None
    if secure_notes and secure_notes.strip():
        encrypted_notes = encryptor.encrypt(secure_notes)

    # Create access request
    access_request = AccessRequest(
        applicant_user_id=user.id,
        submitted_by_user_id=user.id,
        status=settings.STATUS_PENDING,
        secure_notes_encrypted=encrypted_notes,
        access_type=access_type
    )

    access_request.forms = forms
    access_request.permission_groups = []

    db.add(access_request)
    db.commit()
    db.refresh(access_request)

    # Handle file uploads
    if files and files[0].filename:
        for file in files:
            if file.filename:
                try:
                    storage_path, original_filename = await file_upload_service.save_file(file, access_request.id)
                    attachment = Attachment(
                        access_request_id=access_request.id,
                        filename=original_filename,
                        content_type=file.content_type,
                        storage_path=storage_path
                    )
                    db.add(attachment)
                except Exception as e:
                    print(f"File upload error: {e}")
        db.commit()

    # Log action
    audit_logger.log_request_created(db, user.id, access_request.id)

    # Send confirmation email if user has email
    if user.email:
        await email_service.send_applicant_confirmation(
            applicant_email=user.email,
            applicant_name=user.username,
            cwid=user.cwid,
            username=user.username,
            forms=[f.code for f in forms],
            permission_groups=[],
            request_id=access_request.id
        )

    return RedirectResponse(url="/grantee/dashboard?success=1", status_code=303)


@router.get("/requests/{request_id}", response_class=HTMLResponse)
async def view_request(
    request: Request,
    request_id: int,
    user: User = Depends(require_role([settings.ROLE_GRANTEE, settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """View request details"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.applicant_user_id == user.id
    ).first()
    
    if not access_request:
        return RedirectResponse(url="/grantee/dashboard")
    
    return templates.TemplateResponse(
        "grantee/request_detail.html",
        {"request": request, "user": user, "access_request": access_request}
    )

@router.get("/forms/{form_id}/download-pdf")
async def download_form_pdf(
    form_id: int,
    db: Session = Depends(get_db)
):
    """Download PDF for an approved form"""
    form_pdf = db.query(FormPDF).filter(FormPDF.form_id == form_id).first()
    if not form_pdf:
        return Response(content="PDF not found", status_code=404)

    file_data = base64.b64decode(form_pdf.file_data)
    return Response(
        content=file_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{form_pdf.filename}"',
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(file_data)),
            "Cache-Control": "no-cache"
        }
    )