from app.utils.email import email_service
from app.config import settings
from app.models import SystemSetting


async def send_approval_email(access_request, db, base_url: str = None):
    """Called any time a request status changes to Approved - sends to helpdesk"""

    # Get helpdesk email from database settings, fall back to config
    helpdesk_setting = db.query(SystemSetting).filter(
        SystemSetting.key == "helpdesk_email"
    ).first()
    helpdesk_email = helpdesk_setting.value if helpdesk_setting else settings.HELPDESK_EMAIL

    # Use provided base_url or fall back to config
    url_base = base_url or settings.BASE_URL
    if 'ngrok' in url_base and url_base.startswith('http://'):
        url_base = url_base.replace('http://', 'https://', 1)

    pdf_links = []
    for form in access_request.forms:
        if form.pdf:
            pdf_links.append({
                "form_code": form.code,
                "download_url": f"{url_base}/grantee/forms/{form.id}/download-pdf"
            })

    await email_service.send_helpdesk_approval_notification(
        helpdesk_email=helpdesk_email,
        applicant_username=access_request.applicant.username,
        applicant_email=access_request.applicant.email or "No email on file",
        applicant_cwid=access_request.applicant.cwid,
        request_id=access_request.id,
        forms=[f.code for f in access_request.forms],
        pdf_links=pdf_links,
        access_type=getattr(access_request, 'access_type', 'Read')
    )