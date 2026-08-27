from fastapi import APIRouter, Request, Depends, Form, Query, File, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import User, AccessRequest, Form as FormModel, PermissionGroup, FormPDF
from app.routers.auth import require_role
from app.utils.audit import audit_logger
from app.config import settings
from app.utils.approval import send_approval_email
from app.utils.encryption import encryptor
import csv
import io
import base64

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    per_page = 15
    query = db.query(AccessRequest)

    if status:
        query = query.filter(AccessRequest.status == status)
    if search:
        query = query.join(AccessRequest.applicant).filter(
            (User.username.ilike(f"%{search}%")) | (User.cwid.ilike(f"%{search}%"))
        )

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    requests = query.order_by(AccessRequest.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "requests": requests,
            "current_status": status,
            "current_search": search,
            "page": page,
            "total_pages": total_pages,
            "total": total
        }
    )


@router.get("/requests/{request_id}", response_class=HTMLResponse)
async def view_request(
    request: Request,
    request_id: int,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id
    ).first()
    if not access_request:
        return RedirectResponse(url="/admin/dashboard")
    # Decrypt secure notes if present
    decrypted_notes = None
    if access_request.secure_notes_encrypted:
        try:
            decrypted_notes = encryptor.decrypt(access_request.secure_notes_encrypted)
        except:
            decrypted_notes = "Unable to decrypt notes"

    return templates.TemplateResponse(
        "admin/request_detail.html",
        {
            "request": request,
            "user": user,
            "access_request": access_request,
            "decrypted_notes": decrypted_notes
        }
    )


@router.post("/requests/{request_id}/status")
async def update_status(
    request: Request,
    request_id: int,
    new_status: str = Form(...),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id
    ).first()

    if not access_request:
        return RedirectResponse(url="/admin/dashboard?error=not_found", status_code=303)

    old_status = access_request.status
    access_request.status = new_status
    db.commit()

    audit_logger.log_status_change(db, user.id, request_id, old_status, new_status)

    # Send approval email if status changed to Approved
    if new_status == settings.STATUS_APPROVED and old_status != settings.STATUS_APPROVED:
        # Get base URL from request
        base_url = str(request.base_url).rstrip('/')
        await send_approval_email(access_request, db, base_url=base_url)

    return RedirectResponse(url=f"/admin/requests/{request_id}?success=status_updated", status_code=303)


@router.post("/requests/{request_id}/delete")
async def delete_request(
    request: Request,
    request_id: int,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Delete a completed request — only Approved or Rejected requests can be deleted"""
    access_request = db.query(AccessRequest).filter(
        AccessRequest.id == request_id
    ).first()

    if not access_request:
        return RedirectResponse(url="/admin/dashboard?error=not_found", status_code=303)

    if access_request.status == settings.STATUS_PENDING:
        return RedirectResponse(
            url=f"/admin/requests/{request_id}?error=cannot_delete_pending",
            status_code=303
        )

    db.delete(access_request)
    db.commit()
    audit_logger.log(db, "request_deleted", user.id, "access_request", request_id)
    return RedirectResponse(url="/admin/dashboard?success=deleted", status_code=303)

@router.get("/forms", response_class=HTMLResponse)
async def manage_forms(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    forms = db.query(FormModel).order_by(FormModel.code).all()
    return templates.TemplateResponse(
        "admin/forms.html",
        {"request": request, "user": user, "forms": forms}
    )


@router.post("/forms/create")
async def create_form(
    request: Request,
    code: str = Form(...),
    description: str = Form(...),
    active: bool = Form(True),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    form = FormModel(code=code, description=description, active=active)
    db.add(form)
    db.commit()
    audit_logger.log(db, "form_created", user.id, "form", form.id)
    return RedirectResponse(url="/admin/forms?success=created", status_code=303)


@router.post("/forms/{form_id}/edit")
async def edit_form(
    request: Request,
    form_id: int,
    code: str = Form(...),
    description: str = Form(...),
    active: bool = Form(False),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    form = db.query(FormModel).filter(FormModel.id == form_id).first()
    if form:
        form.code = code
        form.description = description
        form.active = active
        db.commit()
        audit_logger.log(db, "form_updated", user.id, "form", form.id)
    return RedirectResponse(url="/admin/forms?success=updated", status_code=303)


@router.post("/forms/{form_id}/delete")
async def delete_form(
    request: Request,
    form_id: int,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    form = db.query(FormModel).filter(FormModel.id == form_id).first()
    if form:
        db.delete(form)
        db.commit()
        audit_logger.log(db, "form_deleted", user.id, "form", form_id)
    return RedirectResponse(url="/admin/forms?success=deleted", status_code=303)


@router.post("/forms/{form_id}/upload-pdf")
async def upload_form_pdf(
    request: Request,
    form_id: int,
    pdf_file: UploadFile = File(...),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Upload PDF for a form"""
    form = db.query(FormModel).filter(FormModel.id == form_id).first()
    if not form:
        return RedirectResponse(url="/admin/forms?error=not_found", status_code=303)

    # Read and encode PDF as base64
    file_data = await pdf_file.read()
    encoded_data = base64.b64encode(file_data).decode('utf-8')

    # Remove existing PDF if any
    existing_pdf = db.query(FormPDF).filter(FormPDF.form_id == form_id).first()
    if existing_pdf:
        db.delete(existing_pdf)
        db.commit()

    # Save new PDF
    form_pdf = FormPDF(
        form_id=form_id,
        filename=pdf_file.filename,
        content_type=pdf_file.content_type or "application/pdf",
        file_data=encoded_data
    )
    db.add(form_pdf)
    db.commit()

    audit_logger.log(db, "form_pdf_uploaded", user.id, "form", form_id)
    return RedirectResponse(url="/admin/forms?success=pdf_uploaded", status_code=303)


@router.get("/forms/{form_id}/download-pdf")
async def download_form_pdf(
    form_id: int,
    user: User = Depends(require_role([
        settings.ROLE_ADMIN, settings.ROLE_SUPERUSER,
        settings.ROLE_GRANTEE, settings.ROLE_GRANTOR
    ])),
    db: Session = Depends(get_db)
):
    """Download PDF for a form"""
    form_pdf = db.query(FormPDF).filter(FormPDF.form_id == form_id).first()
    if not form_pdf:
        return RedirectResponse(url="/admin/forms?error=no_pdf", status_code=303)

    file_data = base64.b64decode(form_pdf.file_data)
    return Response(
        content=file_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={form_pdf.filename}"}
    )


@router.get("/permission-groups", response_class=HTMLResponse)
async def manage_permission_groups(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    groups = db.query(PermissionGroup).order_by(PermissionGroup.name).all()
    return templates.TemplateResponse(
        "admin/permission_groups.html",
        {"request": request, "user": user, "groups": groups}
    )


@router.post("/permission-groups/create")
async def create_permission_group(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    active: bool = Form(True),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    group = PermissionGroup(name=name, description=description, active=active)
    db.add(group)
    db.commit()
    audit_logger.log(db, "permission_group_created", user.id, "permission_group", group.id)
    return RedirectResponse(url="/admin/permission-groups?success=created", status_code=303)


@router.post("/permission-groups/{group_id}/edit")
async def edit_permission_group(
    request: Request,
    group_id: int,
    name: str = Form(...),
    description: str = Form(...),
    active: bool = Form(False),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    group = db.query(PermissionGroup).filter(PermissionGroup.id == group_id).first()
    if group:
        group.name = name
        group.description = description
        group.active = active
        db.commit()
        audit_logger.log(db, "permission_group_updated", user.id, "permission_group", group.id)
    return RedirectResponse(url="/admin/permission-groups?success=updated", status_code=303)


@router.post("/permission-groups/{group_id}/delete")
async def delete_permission_group(
    request: Request,
    group_id: int,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    group = db.query(PermissionGroup).filter(PermissionGroup.id == group_id).first()
    if group:
        db.delete(group)
        db.commit()
        audit_logger.log(db, "permission_group_deleted", user.id, "permission_group", group.id)
    return RedirectResponse(url="/admin/permission-groups?success=deleted", status_code=303)


@router.get("/export")
async def export_requests(
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    requests = db.query(AccessRequest).order_by(AccessRequest.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Request ID', 'CWID', 'Username', 'Email', 'Status', 'Forms',
        'Permission Groups', 'Submitted By', 'Created At', 'Approvals'
    ])
    for req in requests:
        writer.writerow([
            req.id,
            req.applicant.cwid,
            req.applicant.username,
            req.applicant.email or '',
            req.status,
            ', '.join([f.code for f in req.forms]),
            ', '.join([pg.name for pg in req.permission_groups]),
            req.submitted_by.username,
            req.created_at.strftime('%Y-%m-%d %H:%M'),
            len([a for a in req.approvals if a.decision == 'approved'])
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=access_requests.csv"}
    )