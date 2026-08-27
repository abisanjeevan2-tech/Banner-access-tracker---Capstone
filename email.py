import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email notifications"""

    @staticmethod
    async def send_email(to: str, subject: str, body: str, html_body: str = None):
        """Send email via SMTP or log to console in dev mode"""
        if settings.SMTP_ENABLED and settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = settings.SMTP_FROM
                msg['To'] = to
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                if html_body:
                    msg.attach(MIMEText(html_body, 'html'))
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM, to, msg.as_string())
                logger.info(f"Email sent to {to}: {subject}")
            except Exception as e:
                logger.error(f"Failed to send email to {to}: {e}")
        else:
            logger.info(f"""
{'='*80}
EMAIL NOTIFICATION (not sent - SMTP disabled)
{'='*80}
To: {to}
Subject: {subject}
{'='*80}
{body}
{'='*80}
            """)

    @staticmethod
    async def send_helpdesk_approval_notification(
        helpdesk_email: str,
        applicant_username: str,
        applicant_email: str,
        applicant_cwid: str,
        request_id: int,
        forms: List[str],
        pdf_links: List[dict],
        access_type: str = "Read"
    ):
        """Send approval notification to helpdesk with full grantee info and PDF links"""
        subject = f"Banner Access Request #{request_id} APPROVED - Action Required"

        # Build PDF section for plain text
        if pdf_links:
            plain_pdf_section = "PDF Forms available for distribution:\n\n"
            for pdf in pdf_links:
                plain_pdf_section += f"  {pdf['form_code']}:\n  {pdf['download_url']}\n\n"
        else:
            plain_pdf_section = "No PDFs are currently uploaded for the requested forms.\n"

        plain_body = f"""A Banner access request has been fully approved and requires processing.

Request ID: #{request_id}

Applicant Information:
- Username: {applicant_username}
- Email: {applicant_email}
- CWID: {applicant_cwid}

Requested Access:
- Access Type: {access_type}
- Forms: {', '.join(forms)}

{plain_pdf_section}
Please process this request in Banner and distribute the approved forms to the applicant.

Thank you,
Banner Access Management System
"""

        # Build HTML PDF section
        if pdf_links:
            html_pdf_section = "<p><strong>PDF Forms available for distribution:</strong></p><ul>"
            for pdf in pdf_links:
                html_pdf_section += f'<li>{pdf["form_code"]}: <a href="{pdf["download_url"]}" style="color:#862633;">Download PDF</a></li>'
            html_pdf_section += "</ul>"
        else:
            html_pdf_section = """
            <div style="background:#fff3cd;padding:1rem;border-left:4px solid #856404;border-radius:4px;">
                <strong>Note:</strong> No PDFs are currently uploaded for the requested forms.
            </div>
            """

        forms_list = "".join([f"<li>{f}</li>" for f in forms])

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #FFC72C; padding: 1rem 2rem;">
                <h1 style="color: #862633; margin: 0; font-size: 1.2rem; letter-spacing: 0.05em;">
                    BANNER ACCESS TRACKER
                </h1>
            </div>
            <div style="padding: 2rem; background: #f7f7f7;">
                <div style="background: white; padding: 2rem; border-radius: 8px; border-top: 4px solid #862633;">
                    <h2 style="color: #862633;">Request #{request_id} — Action Required</h2>
                    <p>A Banner access request has been <strong style="color:#28a745;">FULLY APPROVED</strong> and requires processing.</p>

                    <h3 style="color: #862633;">Applicant Information:</h3>
                    <table style="width:100%; border-collapse: collapse; margin-bottom: 1rem;">
                        <tr style="background:#f9f9f9;">
                            <td style="padding:0.5rem; border:1px solid #ddd; font-weight:bold;">Username</td>
                            <td style="padding:0.5rem; border:1px solid #ddd;">{applicant_username}</td>
                        </tr>
                        <tr>
                            <td style="padding:0.5rem; border:1px solid #ddd; font-weight:bold;">Email</td>
                            <td style="padding:0.5rem; border:1px solid #ddd;">
                                <a href="mailto:{applicant_email}" style="color:#862633;">{applicant_email}</a>
                            </td>
                        </tr>
                        <tr style="background:#f9f9f9;">
                              <td style="padding:0.5rem; border:1px solid #ddd; font-weight:bold;">CWID</td>
                              <td style="padding:0.5rem; border:1px solid #ddd;">{applicant_cwid}</td>
                          </tr>
                          <tr>
                              <td style="padding:0.5rem; border:1px solid #ddd; font-weight:bold;">Access Type</td>
                              <td style="padding:0.5rem; border:1px solid #ddd;"><strong>{access_type}</strong></td>
                          </tr>
                      </table>

                    <h3 style="color: #862633;">Approved Forms:</h3>
                    <ul>{forms_list}</ul>

                    {html_pdf_section}

                    <div style="margin-top:1.5rem; padding:1rem; background:#f0f0f0; border-radius:4px;">
                        <strong>Action Required:</strong> Please process this request in Banner and
                        distribute the approved forms to the applicant at
                        <a href="mailto:{applicant_email}" style="color:#862633;">{applicant_email}</a>.
                    </div>

                    <hr style="margin-top: 2rem; border: none; border-top: 1px solid #ddd;">
                    <p style="color: #666; font-size: 0.875rem;">
                        Winthrop University IT — Banner Access Management System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        await EmailService.send_email(helpdesk_email, subject, plain_body, html_body)

    @staticmethod
    async def send_applicant_confirmation(
        applicant_email: str,
        applicant_name: str,
        cwid: str,
        username: str,
        forms: List[str],
        permission_groups: List[str],
        request_id: int
    ):
        """Send confirmation email to applicant after submission"""
        subject = "Banner Access Request Submitted - Confirmation"
        body = f"""Dear {applicant_name},

Your Banner access request has been successfully submitted.

Request Details:
- Request ID: {request_id}
- CWID: {cwid}
- Username: {username}
- Forms Requested: {', '.join(forms)}
- Submitted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Your request requires approval from two authorized Grantors.
You will be notified once your request has been fully approved.

If you have questions please contact the Help Desk at {settings.HELPDESK_EMAIL}.

Thank you,
Winthrop University IT
Banner Access Management System
"""
        await EmailService.send_email(applicant_email, subject, body)

    @staticmethod
    async def send_helpdesk_notification(
        cwid: str,
        username: str,
        forms: List[str],
        permission_groups: List[str],
        has_secure_notes: bool,
        attachments: List[str],
        approvals: List[dict],
        request_id: int
    ):
        """Send notification to Help Desk after dual approval — grantor route"""
        subject = f"APPROVED: Banner Access Request #{request_id} - {username}"
        approvals_text = "\n".join([
            f"  - {a['grantor_name']} at {a['approved_at']}"
            for a in approvals
        ])
        attachments_text = "\n".join([f"  - {att}" for att in attachments]) if attachments else "  None"
        body = f"""A Banner access request has been APPROVED by two Grantors and requires processing.

Request ID: {request_id}

Applicant Information:
- CWID: {cwid}
- Username: {username}

Requested Access:
- Forms: {', '.join(forms)}

Approvals:
{approvals_text}

Additional Information:
- Secure Notes: {'Yes (see system)' if has_secure_notes else 'No'}
- Attachments:
{attachments_text}

Please process this access request in Banner.

Thank you,
Banner Access Management System
"""
        await EmailService.send_email(settings.HELPDESK_EMAIL, subject, body)


email_service = EmailService()