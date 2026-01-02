import smtplib
from celery import shared_task
from django.db import models
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from anymail.exceptions import AnymailError


class MailSendStatus(models.TextChoices):
    SUCCESS = "success", "Main Success"
    FALLBACK = "fallback", "Main Fail, Fallback Success"
    FAILURE = "failure", "Fail"
    
    
def _send_email(
    *,
    subject: str,
    body: str,
    to: list[str]|str,
    from_email: str = None,
    is_html: bool = False,
) -> dict:
    if isinstance(to, str):
        to = [to]
        
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=to,
    )
    email.content_subtype = 'html' if is_html else 'plain'
    
    # ---- try main backend (Mailgun) ----
    try:    
        main_backend = settings.EMAIL_BACKEND
        email.connection = get_connection(
            backend=main_backend
        )
        email.send()

        return {
            "backend": main_backend,
            "status": MailSendStatus.SUCCESS,
            "error_message": None,
        }

    except (AnymailError, smtplib.SMTPException) as exc:
        mailgun_error = exc  # keep for logging / error message

    # ---- fallback to local SMTP ----
    try:
        fallback_backend = settings.FALLBACK_EMAIL_BACKEND
        fallback_host = settings.FALLBACK_EMAIL_HOST
        fallback_port = settings.FALLBACK_EMAIL_PORT
        email.connection = get_connection(
            backend=fallback_backend,
            host=fallback_host,
            port=fallback_port,
        )
        email.send()

        return {
            "backend": fallback_backend,
            "status": MailSendStatus.FALLBACK,
            "error_message": str(mailgun_error),
        }

    except smtplib.SMTPException as exc:
        return {
            "backend": fallback_backend,
            "status": MailSendStatus.FAILURE,
            "error_message": f"main:{str(mailgun_error)} fallback:{str(exc)}",
        }
    
        
@shared_task(
    bind=True, 
    autoretry_for=(Exception,), 
    retry_kwargs={"max_retries": 3, "countdown": 60}, 
    retry_backoff=True,
)
def send_email_task(
    self, 
    *, 
    subject: str,
    body: str,
    to: list[str]|str,
    from_email: str|None = None,
    is_html: bool = False,
) -> dict:

    result = _send_email(
        subject=subject,
        body=body,
        to=to,
        from_email=from_email,
        is_html=is_html,
    )
        
    if result["status"] == MailSendStatus.FAILURE:
        raise Exception(result["error_message"])

    return result
    
    