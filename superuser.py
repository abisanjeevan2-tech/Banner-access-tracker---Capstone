from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Role, SystemSetting
from app.routers.auth import require_role
from app.utils.auth import hash_password
from app.models import User, Role, SystemSetting, AccessRequest
from app.utils.audit import audit_logger
from app.config import settings
import csv
import io

router = APIRouter(prefix="/superuser", tags=["superuser"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def superuser_dashboard(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """SuperUser dashboard"""
    users_count = db.query(User).count()
    return templates.TemplateResponse(
        "superuser/dashboard.html",
        {"request": request, "user": user, "users_count": users_count}
    )


@router.get("/users", response_class=HTMLResponse)
async def manage_users(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Manage users"""
    users = db.query(User).order_by(User.username).all()
    roles = db.query(Role).all()
    error = request.query_params.get('error')
    return templates.TemplateResponse(
        "superuser/users.html",
        {"request": request, "user": user, "users": users, "roles": roles, "error": error}
    )


@router.post("/users/create")
async def create_user(
    request: Request,
    cwid: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role_id: int = Form(...),
    email: str = Form(None),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Create new user"""
    existing = db.query(User).filter(
        (User.cwid == cwid) | (User.username == username)
    ).first()

    if existing:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request,
                "user": user,
                "users": users,
                "roles": roles,
                "error": "User with this CWID or username already exists"
            }
        )

    new_user = User(
        cwid=cwid,
        username=username,
        password_hash=hash_password(password),
        role_id=role_id,
        email=email
    )
    db.add(new_user)
    db.commit()
    audit_logger.log(db, "user_created", user.id, "user", new_user.id)
    return RedirectResponse(url="/superuser/users?success=created", status_code=303)


@router.post("/users/import-csv")
async def import_users_csv(
    request: Request,
    csv_file: UploadFile = File(...),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Import users from CSV file"""
    if not csv_file.filename.endswith('.csv'):
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": ["File must be a .csv file"]
            }
        )

    content = await csv_file.read()
    try:
        decoded = content.decode('utf-8')
    except UnicodeDecodeError:
        decoded = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))

    required_headers = {'cwid', 'username', 'password', 'email', 'role'}
    if not reader.fieldnames:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": ["CSV file is empty or has no headers"]
            }
        )

    actual_headers = {h.strip().lower() for h in reader.fieldnames}
    missing_headers = required_headers - actual_headers
    if missing_headers:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": [f"Missing required columns: {', '.join(missing_headers)}. Required: cwid, username, password, email, role"]
            }
        )

    valid_roles = {r.name: r for r in db.query(Role).all()}
    errors = []
    users_to_add = []

    for i, row in enumerate(reader, start=2):
        row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        row_errors = []

        cwid = row.get('cwid', '')
        if not cwid:
            row_errors.append("CWID is required")
        elif not cwid.isdigit() or len(cwid) != 8:
            row_errors.append(f"CWID must be 8 digits (got '{cwid}')")

        username = row.get('username', '')
        if not username:
            row_errors.append("Username is required")

        password = row.get('password', '')
        if not password:
            row_errors.append("Password is required")

        email = row.get('email', '')
        if not email:
            row_errors.append("Email is required")

        role_name = row.get('role', '')
        if not role_name:
            row_errors.append("Role is required")
        elif role_name not in valid_roles:
            row_errors.append(f"Invalid role '{role_name}'. Must be one of: {', '.join(valid_roles.keys())}")

        if cwid and username and not row_errors:
            existing = db.query(User).filter(
                (User.cwid == cwid) | (User.username == username)
            ).first()
            if existing:
                row_errors.append(f"User with CWID '{cwid}' or username '{username}' already exists")

        if row_errors:
            errors.append(f"Row {i}: {', '.join(row_errors)}")
        else:
            users_to_add.append({
                'cwid': cwid,
                'username': username,
                'password': password,
                'email': email,
                'role': valid_roles[role_name]
            })

    if errors:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": errors
            }
        )

    for u_data in users_to_add:
        new_user = User(
            cwid=u_data['cwid'],
            username=u_data['username'],
            password_hash=hash_password(u_data['password']),
            email=u_data['email'],
            role_id=u_data['role'].id
        )
        db.add(new_user)
        audit_logger.log(db, "user_created_csv", user.id, "user", None)

    db.commit()
    return RedirectResponse(
        url=f"/superuser/users?success=csv&count={len(users_to_add)}",
        status_code=303
    )

@router.post("/users/delete-grantees-csv")
async def delete_grantees_csv(
    request: Request,
    csv_file: UploadFile = File(...),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Delete grantees by CSV containing CWIDs or usernames"""
    if not csv_file.filename.endswith('.csv'):
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": ["File must be a .csv file"]
            }
        )

    content = await csv_file.read()
    try:
        decoded = content.decode('utf-8')
    except UnicodeDecodeError:
        decoded = content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(decoded))

    if not reader.fieldnames:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": ["CSV file is empty or has no headers"]
            }
        )

    actual_headers = {h.strip().lower() for h in reader.fieldnames}
    if 'cwid' not in actual_headers and 'username' not in actual_headers:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": ["CSV must have at least one column: 'cwid' or 'username'"]
            }
        )

    # Get grantee role
    grantee_role = db.query(Role).filter(Role.name == settings.ROLE_GRANTEE).first()

    errors = []
    users_to_delete = []

    for i, row in enumerate(reader, start=2):
        row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        cwid = row.get('cwid', '')
        username = row.get('username', '')

        if not cwid and not username:
            errors.append(f"Row {i}: Must provide either CWID or username")
            continue

        # Find user
        query = db.query(User).filter(User.role_id == grantee_role.id)
        if cwid:
            target = query.filter(User.cwid == cwid).first()
        else:
            target = query.filter(User.username == username).first()

        if not target:
            identifier = cwid or username
            errors.append(f"Row {i}: Grantee '{identifier}' not found")
            continue

        users_to_delete.append(target)

    if errors:
        users = db.query(User).order_by(User.username).all()
        roles = db.query(Role).all()
        return templates.TemplateResponse(
            "superuser/users.html",
            {
                "request": request, "user": user,
                "users": users, "roles": roles,
                "csv_errors": errors
            }
        )

    # Delete users and their requests
    count = 0
    for target_user in users_to_delete:
        # Delete their requests (cascades to approvals and attachments)
        db.query(AccessRequest).filter(
            AccessRequest.applicant_user_id == target_user.id
        ).delete(synchronize_session=False)
        db.delete(target_user)
        audit_logger.log(db, "grantee_deleted_csv", user.id, "user", target_user.id)
        count += 1

    db.commit()
    return RedirectResponse(
        url=f"/superuser/users?success=grantees_deleted&count={count}",
        status_code=303
    )

@router.post("/users/{user_id}/edit")
async def edit_user(
    request: Request,
    user_id: int,
    cwid: str = Form(...),
    username: str = Form(...),
    role_id: int = Form(...),
    password: str = Form(None),
    email: str = Form(None),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Edit user"""
    edit_user = db.query(User).filter(User.id == user_id).first()

    if not edit_user:
        return RedirectResponse(url="/superuser/users?error=not_found", status_code=303)

    edit_user.cwid = cwid
    edit_user.username = username
    edit_user.role_id = role_id
    edit_user.email = email

    if password and password.strip():
        edit_user.password_hash = hash_password(password)

    db.commit()
    audit_logger.log(db, "user_updated", user.id, "user", user_id)
    return RedirectResponse(url="/superuser/users?success=updated", status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(
    request: Request,
    user_id: int,
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Delete user"""
    delete_target = db.query(User).filter(User.id == user_id).first()

    if not delete_target:
        return RedirectResponse(url="/superuser/users?success=deleted", status_code=303)

    # Check if deleting the last superuser first
    if delete_target.role.name == settings.ROLE_SUPERUSER:
        superuser_count = db.query(User).join(User.role).filter(
            Role.name == settings.ROLE_SUPERUSER
        ).count()
        if superuser_count <= 1:
            return RedirectResponse(
                url="/superuser/users?error=last_superuser",
                status_code=303
            )

    # Prevent deleting self after superuser check
    if user_id == user.id:
        return RedirectResponse(url="/superuser/users?error=cannot_delete_self", status_code=303)

    db.delete(delete_target)
    db.commit()
    audit_logger.log(db, "user_deleted", user.id, "user", user_id)
    return RedirectResponse(url="/superuser/users?success=deleted", status_code=303)

@router.get("/settings", response_class=HTMLResponse)
async def system_settings(
    request: Request,
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Manage system settings"""
    # Ensure default settings exist
    default_settings = {
        "helpdesk_email": settings.HELPDESK_EMAIL,
        "max_upload_size_mb": str(settings.MAX_UPLOAD_SIZE_MB),
        "session_timeout_hours": "8"
    }
    for key, default_value in default_settings.items():
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not existing:
            setting = SystemSetting(key=key, value=default_value)
            db.add(setting)
    db.commit()

    settings_list = db.query(SystemSetting).all()

    # Get current helpdesk email
    helpdesk_setting = db.query(SystemSetting).filter(
        SystemSetting.key == "helpdesk_email"
    ).first()
    helpdesk_email = helpdesk_setting.value if helpdesk_setting else settings.HELPDESK_EMAIL

    return templates.TemplateResponse(
        "superuser/settings.html",
        {
            "request": request,
            "user": user,
            "settings": settings_list,
            "helpdesk_email": helpdesk_email
        }
    )


@router.post("/settings/helpdesk-email")
async def update_helpdesk_email(
    request: Request,
    email: str = Form(...),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Update helpdesk email address"""
    setting = db.query(SystemSetting).filter(
        SystemSetting.key == "helpdesk_email"
    ).first()
    if setting:
        setting.value = email
    else:
        setting = SystemSetting(key="helpdesk_email", value=email)
        db.add(setting)
    db.commit()
    audit_logger.log(db, "helpdesk_email_updated", user.id, "system_setting", None)
    return RedirectResponse(url="/superuser/settings?success=updated", status_code=303)


@router.post("/settings/{setting_id}/update")
async def update_setting(
    request: Request,
    setting_id: int,
    value: str = Form(...),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Update system setting"""
    setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()
    if setting:
        setting.value = value
        db.commit()
        audit_logger.log(db, "setting_updated", user.id, "system_setting", setting_id)
    return RedirectResponse(url="/superuser/settings?success=updated", status_code=303)


@router.post("/settings/{setting_id}/update")
async def update_setting(
    request: Request,
    setting_id: int,
    value: str = Form(...),
    user: User = Depends(require_role([settings.ROLE_SUPERUSER])),
    db: Session = Depends(get_db)
):
    """Update system setting"""
    setting = db.query(SystemSetting).filter(SystemSetting.id == setting_id).first()

    if setting:
        setting.value = value
        db.commit()
        audit_logger.log(db, "setting_updated", user.id, "system_setting", setting_id)

    return RedirectResponse(url="/superuser/settings?success=updated", status_code=303)