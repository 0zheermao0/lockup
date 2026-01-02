from dataclasses import dataclass
import smtplib
from celery import shared_task
from django.db import models
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from anymail.exceptions import AnymailError


class EMailSendStatus(models.TextChoices):
    SUCCESS = "success", "Main Success"
    FALLBACK = "fallback", "Main Fail, Fallback Success"
    FAILURE = "failure", "Fail"
    
@dataclass
class EMailSendResult:
    backend: str
    status: EMailSendStatus
    error_message: str | None
    
    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "status": self.status,
            "error_message": self.error_message,
        }
    
def _send_email(
    *,
    subject: str,
    body: str,
    to: list[str]|str,
    from_email: str = None,
    is_html: bool = False,
) -> EMailSendResult:
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

        return EMailSendResult(
            backend=main_backend,
            status=EMailSendStatus.SUCCESS,
            error_message=None,
        )
        
    except (AnymailError, smtplib.SMTPException) as exc:
        mailgun_error = exc  # keep for logging / error message

    # ---- fallback to local SMTP ----
    try:
        email.connection = get_connection(
            backend=settings.FALLBACK_EMAIL_BACKEND,
            host=settings.FALLBACK_EMAIL_HOST,
            port=settings.FALLBACK_EMAIL_PORT,
            username=settings.FALLBACK_EMAIL_HOST_USER,
            password=settings.FALLBACK_EMAIL_HOST_PASSWORD,
            use_tls=settings.FALLBACK_EMAIL_USE_TLS,
        )

        email.send()

        return EMailSendResult(
            backend=settings.FALLBACK_EMAIL_BACKEND,
            status=EMailSendStatus.FALLBACK,
            error_message=str(mailgun_error),
        )
        
    except smtplib.SMTPException as exc:
        return EMailSendResult(
            backend=settings.FALLBACK_EMAIL_BACKEND,
            status=EMailSendStatus.FAILURE,
            error_message=f"main:{str(mailgun_error)} fallback:{str(exc)}",
        )
    
        
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
) -> EMailSendResult:

    result = _send_email(
        subject=subject,
        body=body,
        to=to,
        from_email=from_email,
        is_html=is_html,
    )
        
    if result.status == EMailSendStatus.FAILURE:
        raise Exception(result.error_message)

    return result.to_dict()
    
    