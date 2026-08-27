from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, Form as FormModel, Role
from app.routers.auth import require_role
from app.utils.audit import audit_logger
from app.config import settings
from typing import List, Optional

router = APIRouter(prefix="/admin/grantor-forms", tags=["grantor-forms"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def manage_grantor_forms(
    request: Request,
    search: Optional[str] = None,
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Manage which forms each grantor can approve"""
    # Get all grantors
    grantor_role = db.query(Role).filter(Role.name == settings.ROLE_GRANTOR).first()
    grantors = db.query(User).filter(User.role_id == grantor_role.id).order_by(User.username).all()

    # Get all forms with optional search
    forms_query = db.query(FormModel).filter(FormModel.active == True)
    if search:
        forms_query = forms_query.filter(
            (FormModel.code.ilike(f"%{search}%")) |
            (FormModel.description.ilike(f"%{search}%"))
        )
    forms = forms_query.order_by(FormModel.code).all()

    return templates.TemplateResponse(
        "admin/grantor_forms.html",
        {
            "request": request,
            "user": user,
            "grantors": grantors,
            "forms": forms,
            "current_search": search
        }
    )


@router.post("/update/{grantor_id}")
async def update_grantor_forms(
    request: Request,
    grantor_id: int,
    form_ids: List[int] = Form(default=[]),
    no_forms: Optional[str] = Form(default=None),
    user: User = Depends(require_role([settings.ROLE_ADMIN, settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Update forms a grantor can approve"""
    grantor = db.query(User).filter(User.id == grantor_id).first()
    if not grantor:
        return RedirectResponse(url="/admin/grantor-forms?error=not_found", status_code=303)

    if no_forms:
        # None selected - remove all form assignments
        grantor.approved_forms = []
    else:
        # Update with selected forms
        selected_forms = db.query(FormModel).filter(FormModel.id.in_(form_ids)).all()
        grantor.approved_forms = selected_forms

    db.commit()
    audit_logger.log(db, "grantor_forms_updated", user.id, "user", grantor_id)
    return RedirectResponse(url=f"/admin/grantor-forms?success=updated&grantor={grantor_id}", status_code=303)