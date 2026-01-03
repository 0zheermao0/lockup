from dataclasses import dataclass
import smtplib
import logging
from celery import shared_task
from django.db import models
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from anymail.exceptions import AnymailError

logger = logging.getLogger(__name__)


def validate_email_configuration() -> bool:
    """验证邮件配置是否完整"""
    required_settings = [
        'EMAIL_BACKEND',
        'DEFAULT_FROM_EMAIL',
        'FALLBACK_EMAIL_BACKEND',
        'FALLBACK_EMAIL_HOST',
    ]

    missing_settings = []
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            missing_settings.append(setting)

    # 检查 Mailgun 配置
    if hasattr(settings, 'ANYMAIL'):
        anymail_config = settings.ANYMAIL
        if not anymail_config.get('MAILGUN_API_KEY'):
            logger.warning("MAILGUN_API_KEY is empty - Mailgun emails will fail")
        if not anymail_config.get('MAILGUN_SENDER_DOMAIN'):
            missing_settings.append('ANYMAIL.MAILGUN_SENDER_DOMAIN')
    else:
        missing_settings.append('ANYMAIL')

    if missing_settings:
        logger.error(f"Missing email configuration: {', '.join(missing_settings)}")
        return False

    logger.info("Email configuration validation passed")
    return True


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
    to: list[str] | str,
    from_email: str | None = None,
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
    
    mailgun_error = None

    # ---- try main backend (Mailgun) ----
    try:
        main_backend = settings.EMAIL_BACKEND
        email.connection = get_connection(
            backend=main_backend
        )
        email.send()

        logger.info(f"Email sent successfully via {main_backend} to {to}, subject: '{subject}'")
        return EMailSendResult(
            backend=main_backend,
            status=EMailSendStatus.SUCCESS,
            error_message=None,
        )

    except (AnymailError, smtplib.SMTPException) as exc:
        mailgun_error = exc
        logger.warning(f"Mailgun failed for email to {to}: {exc}, trying fallback")
    except Exception as exc:
        mailgun_error = exc
        logger.error(f"Unexpected error with Mailgun for email to {to}: {exc}, trying fallback")

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

        logger.info(f"Email sent successfully via fallback to {to}, subject: '{subject}'")
        return EMailSendResult(
            backend=settings.FALLBACK_EMAIL_BACKEND,
            status=EMailSendStatus.FALLBACK,
            error_message=str(mailgun_error) if mailgun_error else None,
        )

    except Exception as exc:
        error_message = f"main:{str(mailgun_error) if mailgun_error else 'Unknown'} fallback:{str(exc)}"
        logger.error(f"Email sending failed completely to {to}: {error_message}")
        return EMailSendResult(
            backend=settings.FALLBACK_EMAIL_BACKEND,
            status=EMailSendStatus.FAILURE,
            error_message=error_message,
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
    to: list[str] | str,
    from_email: str | None = None,
    is_html: bool = False,
) -> dict:

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
    
    