import os
from utils.email import EMailSendStatus, _send_email, send_email_task
from anymail.exceptions import AnymailError
from smtplib import SMTPException


TEST_EMAIL = os.getenv('TEST_EMAIL', 'test@example.com')

def test_mailgun_success(mocker):
    mock_send = mocker.patch(
        "django.core.mail.EmailMessage.send",
        return_value=1,
    )

    result = _send_email(
        subject="test_success",
        body="hello_success",
        to=[TEST_EMAIL],
    )

    assert result.status == EMailSendStatus.SUCCESS


def test_fallback_on_mailgun_failure(mocker):
    mocker.patch(
        "django.core.mail.EmailMessage.send",
        side_effect=[
            AnymailError("mailgun fail"),  # main
            1,                          # fallback
        ],
    )

    result = _send_email(
        subject="test_fallback",
        body="hello_fallback",
        to=[TEST_EMAIL],
    )

    assert result.status == EMailSendStatus.FALLBACK


def test_both_backends_fail(mocker):
    mocker.patch(
        "django.core.mail.EmailMessage.send",
        side_effect=SMTPException("both fail"),
    )

    result = _send_email(
        subject="test_failure",
        body="hello_failure",
        to=[TEST_EMAIL],
    )

    assert result.status == EMailSendStatus.FAILURE
