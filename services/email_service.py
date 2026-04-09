import logging
from flask import current_app
from flask_mail import Message
from extensions import mail

logger = logging.getLogger(__name__)


def send_application_confirmation(student_email, application_id, job_role, company):
    subject = f'Application Confirmation - {job_role} at {company}'
    body = (
        f'Your application has been successfully submitted.\n\n'
        f'Application ID: {application_id}\n'
        f'Position: {job_role}\n'
        f'Company: {company}\n\n'
        f'Please save your Application ID for future reference.\n\n'
        f'— UWI Jobs'
    )

    mail_configured = current_app.config.get('MAIL_SERVER')
    if mail_configured and student_email:
        try:
            msg = Message(
                subject=subject,
                recipients=[student_email],
                body=body
            )
            mail.send(msg)
            logger.info(f'Confirmation email sent to {student_email} for application {application_id}')
            return True
        except Exception as e:
            logger.error(f'Failed to send email to {student_email}: {e}')
            # Fall through to console log
    
    # Console fallback for development
    logger.info(
        f'\n===== APPLICATION CONFIRMATION EMAIL =====\n'
        f'To: {student_email or "(no email on file)"}\n'
        f'Subject: {subject}\n\n'
        f'{body}\n'
        f'==========================================\n'
    )
    return False
