from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from app.models import User, AccessRequest, Approval, Attachment, Form as FormModel
from app.routers.auth import require_role
from app.utils.audit import audit_logger
from app.utils.approval import send_approval_email
from app.utils.email import email_service
from app.utils.encryption import encryptor
from app.config import settings
import os

router = APIRouter(prefix="/grantor", tags=["grantor"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def grantor_dashboard(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """Grantor dashboard - view all requests, pending first"""
    authorized_form_ids = [f.id for f in user.approved_forms]

    from app.models import Form as FormModel
    total_forms = db.query(FormModel).filter(FormModel.active == True).count()

    all_requests = db.query(AccessRequest).order_by(
        AccessRequest.created_at.desc()
    ).all()

    if len(authorized_form_ids) == 0:
        all_requests = []
    elif len(authorized_form_ids) >= total_forms:
        pass
    else:
        all_requests = [
            req for req in all_requests
            if any(f.id in authorized_form_ids for f in req.forms)
        ]

    pending = [r for r in all_requests if r.status == settings.STATUS_PENDING]
    others = [r for r in all_requests if r.status != settings.STATUS_PENDING]
    sorted_requests = pending + others

    return templates.TemplateResponse(
        "grantor/dashboard.html",
        {"request": request, "user": user, "requests": sorted_requests}
    )


@router.get("/requests/{request_id}", response_class=HTMLResponse)
async def view_request(
    request: Request,
    request_id: int,
    user: User = Depends(require_role([settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """View request details for approval"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id
    ).first()

    if not access_request:
        return RedirectResponse(url="/grantor/dashboard")

    authorized_form_ids = [f.id for f in user.approved_forms]

    # Find which forms in this request the grantor can approve
    # and which ones they have already approved
    approvable_forms = []
    for form in access_request.forms:
        if not authorized_form_ids or form.id in authorized_form_ids:
            existing = db.query(Approval).filter(
                and_(
                    Approval.access_request_id == request_id,
                    Approval.grantor_user_id == user.id,
                    Approval.form_id == form.id
                )
            ).first()
            approvable_forms.append({
                "form": form,
                "already_approved": existing is not None,
                "approval": existing
            })

    approvals = db.query(Approval).filter(
        Approval.access_request_id == request_id
    ).all()

    decrypted_notes = None
    if access_request.secure_notes_encrypted:
        try:
            decrypted_notes = encryptor.decrypt(access_request.secure_notes_encrypted)
        except:
            decrypted_notes = "Unable to decrypt notes"

    return templates.TemplateResponse(
        "grantor/request_detail.html",
        {
            "request": request,
            "user": user,
            "access_request": access_request,
            "approvable_forms": approvable_forms,
            "approvals": approvals,
            "decrypted_notes": decrypted_notes
        }
    )


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request: Request,
    request_id: int,
    comment: str = Form(None),
    form_ids: list = Form(default=[]),
    user: User = Depends(require_role([settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """Approve specific forms in an access request"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.status == settings.STATUS_PENDING
    ).first()

    if not access_request:
        return RedirectResponse(url="/grantor/dashboard?error=request_not_found", status_code=303)

    authorized_form_ids = [f.id for f in user.approved_forms]

    # Create approval for each selected form
    for form_id in form_ids:
        form_id = int(form_id)
        # Check grantor is authorized for this form
        if authorized_form_ids and form_id not in authorized_form_ids:
            continue

        # Check not already approved
        existing = db.query(Approval).filter(
            and_(
                Approval.access_request_id == request_id,
                Approval.grantor_user_id == user.id,
                Approval.form_id == form_id
            )
        ).first()
        if existing:
            continue

        approval = Approval(
            access_request_id=request_id,
            grantor_user_id=user.id,
            form_id=form_id,
            decision="approved",
            comment=comment
        )
        db.add(approval)

    db.commit()
    audit_logger.log_approval(db, user.id, request_id, "approved")

    # Check if ALL forms in the request now have at least one approval
    all_approved = True
    for form in access_request.forms:
        form_approval = db.query(Approval).filter(
            and_(
                Approval.access_request_id == request_id,
                Approval.form_id == form.id,
                Approval.decision == "approved"
            )
        ).first()
        if not form_approval:
            all_approved = False
            break

    if all_approved:
        old_status = access_request.status
        access_request.status = settings.STATUS_APPROVED
        db.commit()

        audit_logger.log_status_change(db, user.id, request_id, old_status, settings.STATUS_APPROVED)

        approvals = db.query(Approval).filter(
            and_(
                Approval.access_request_id == request_id,
                Approval.decision == "approved"
            )
        ).all()

        approval_details = [
            {
                "grantor_name": a.grantor.username,
                "grantor_username": a.grantor.username,
                "approved_at": a.created_at.strftime('%Y-%m-%d %H:%M UTC')
            }
            for a in approvals
        ]

        await email_service.send_helpdesk_notification(
            cwid=access_request.applicant.cwid,
            username=access_request.applicant.username,
            forms=[f.code for f in access_request.forms],
            permission_groups=[pg.name for pg in access_request.permission_groups],
            has_secure_notes=bool(access_request.secure_notes_encrypted),
            attachments=[att.filename for att in access_request.attachments],
            approvals=approval_details,
            request_id=request_id
        )

        base_url = str(request.base_url).rstrip('/')
        await send_approval_email(access_request, db, base_url=base_url)

    return RedirectResponse(url="/grantor/dashboard?success=approved", status_code=303)


@router.post("/requests/{request_id}/deny")
async def deny_request(
    request: Request,
    request_id: int,
    comment: str = Form(...),
    user: User = Depends(require_role([settings.ROLE_GRANTOR])),
    db: Session = Depends(get_db)
):
    """Deny an access request"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id,
        AccessRequest.status == settings.STATUS_PENDING
    ).first()

    if not access_request:
        return RedirectResponse(url="/grantor/dashboard?error=request_not_found", status_code=303)

    # Create a denial without form_id (denies the whole request)
    existing_denial = db.query(Approval).filter(
        and_(
            Approval.access_request_id == request_id,
            Approval.grantor_user_id == user.id,
            Approval.decision == "denied"
        )
    ).first()

    if not existing_denial:
        approval = Approval(
            access_request_id=request_id,
            grantor_user_id=user.id,
            form_id=None,
            decision="denied",
            comment=comment
        )
        db.add(approval)

    old_status = access_request.status
    access_request.status = settings.STATUS_REJECTED
    db.commit()

    audit_logger.log_approval(db, user.id, request_id, "denied")
    audit_logger.log_status_change(db, user.id, request_id, old_status, settings.STATUS_REJECTED)

    return RedirectResponse(url="/grantor/dashboard?success=denied", status_code=303)


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    user: User = Depends(require_role([settings.ROLE_GRANTOR, settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Download an attachment"""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment or not os.path.exists(attachment.storage_path):
        return Response(content="File not found", status_code=404)

    with open(attachment.storage_path, "rb") as f:
        file_data = f.read()

    return Response(
        content=file_data,
        media_type=attachment.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={attachment.filename}"}
    )


@router.get("/attachments/{attachment_id}/view")
async def view_attachment(
    attachment_id: int,
    user: User = Depends(require_role([settings.ROLE_GRANTOR, settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """View an attachment inline"""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment or not os.path.exists(attachment.storage_path):
        return Response(content="File not found", status_code=404)

    with open(attachment.storage_path, "rb") as f:
        file_data = f.read()

    return Response(
        content=file_data,
        media_type=attachment.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename={attachment.filename}"}
    )