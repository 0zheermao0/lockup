"""
邮箱验证相关工具函数
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from users.models import EmailVerification
from .email import send_email_task

logger = logging.getLogger(__name__)


def is_email_domain_allowed(email: str) -> bool:
    """
    检查邮箱域名是否在白名单中

    Args:
        email: 邮箱地址

    Returns:
        bool: 是否允许的域名
    """
    if not email or '@' not in email:
        return False

    domain = email.split('@')[1].lower()
    allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', [])

    # 检查完全匹配
    if domain in allowed_domains:
        return True

    # 检查教育邮箱后缀匹配
    for allowed_domain in allowed_domains:
        if allowed_domain.startswith('.') and domain.endswith(allowed_domain):
            return True
        elif allowed_domain == 'edu.cn' and domain.endswith('.edu.cn'):
            return True
        elif allowed_domain == 'edu' and domain.endswith('.edu'):
            return True
        elif allowed_domain == 'ac.uk' and domain.endswith('.ac.uk'):
            return True
        elif allowed_domain == 'ac.cn' and domain.endswith('.ac.cn'):
            return True

    return False


def get_rate_limit_key(email: str, ip_address: str = None) -> str:
    """
    生成频率限制的缓存键

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）

    Returns:
        str: 缓存键
    """
    if ip_address:
        return f"email_verification_rate_limit:{email}:{ip_address}"
    else:
        return f"email_verification_rate_limit:{email}"


def check_rate_limit(email: str, ip_address: str = None) -> tuple[bool, int]:
    """
    检查发送频率限制

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）

    Returns:
        tuple[bool, int]: (是否可以发送, 剩余可发送次数)
    """
    max_attempts = getattr(settings, 'EMAIL_VERIFICATION_MAX_ATTEMPTS_PER_HOUR', 5)

    # 检查邮箱级别的限制
    email_key = get_rate_limit_key(email)
    email_attempts = cache.get(email_key, 0)

    if email_attempts >= max_attempts:
        return False, 0

    # 检查IP级别的限制（如果提供了IP）
    if ip_address:
        ip_key = get_rate_limit_key('', ip_address)
        ip_attempts = cache.get(ip_key, 0)

        if ip_attempts >= max_attempts * 2:  # IP限制更严格
            return False, 0

    remaining = max_attempts - email_attempts
    return True, remaining


def increment_rate_limit(email: str, ip_address: str = None):
    """
    增加发送次数计数

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）
    """
    timeout = 3600  # 1小时

    # 增加邮箱计数
    email_key = get_rate_limit_key(email)
    current_count = cache.get(email_key, 0)
    cache.set(email_key, current_count + 1, timeout)

    # 增加IP计数（如果提供了IP）
    if ip_address:
        ip_key = get_rate_limit_key('', ip_address)
        current_ip_count = cache.get(ip_key, 0)
        cache.set(ip_key, current_ip_count + 1, timeout)


def clean_expired_verifications():
    """
    清理过期的验证码记录
    """
    expired_count = EmailVerification.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()[0]

    if expired_count > 0:
        logger.info(f"Cleaned {expired_count} expired email verification records")

    return expired_count


def send_verification_email(email: str, verification_code: str) -> bool:
    """
    发送验证邮件

    Args:
        email: 收件人邮箱
        verification_code: 验证码

    Returns:
        bool: 是否发送成功
    """
    subject = "Lock-Up 账号注册验证码"

    # 邮件内容（HTML格式）
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Lock-Up 账号注册验证</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: white; padding: 30px; border: 2px solid #000; border-top: none; border-radius: 0 0 8px 8px; }}
            .verification-code {{ font-size: 32px; font-weight: bold; color: #007bff; text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border: 2px solid #007bff; border-radius: 8px; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; text-align: center; }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 Lock-Up</h1>
                <h2>账号注册验证</h2>
            </div>
            <div class="content">
                <p>您好！</p>
                <p>感谢您注册 Lock-Up 自律锁时应用。请使用以下验证码完成账号注册：</p>

                <div class="verification-code">
                    {verification_code}
                </div>

                <div class="warning">
                    <strong>⚠️ 重要提醒：</strong>
                    <ul>
                        <li>验证码有效期为 15 分钟</li>
                        <li>请勿将验证码泄露给他人</li>
                        <li>如非本人操作，请忽略此邮件</li>
                    </ul>
                </div>

                <p>如果您没有注册 Lock-Up 账号，请忽略此邮件。</p>

                <p>祝您使用愉快！<br>Lock-Up 团队</p>
            </div>
            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复。</p>
                <p>如有疑问，请联系客服支持。</p>
            </div>
        </div>
    </body>
    </html>
    """

    # 纯文本版本（备用）
    text_content = f"""
Lock-Up 账号注册验证

您好！

感谢您注册 Lock-Up 自律锁时应用。请使用以下验证码完成账号注册：

验证码：{verification_code}

重要提醒：
- 验证码有效期为 15 分钟
- 请勿将验证码泄露给他人
- 如非本人操作，请忽略此邮件

如果您没有注册 Lock-Up 账号，请忽略此邮件。

祝您使用愉快！
Lock-Up 团队

此邮件由系统自动发送，请勿直接回复。
    """

    try:
        # 异步发送邮件
        result = send_email_task.delay(
            subject=subject,
            body=html_content,
            to=email,
            is_html=True
        )

        logger.info(f"Verification email queued for {email}, task_id: {result.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to queue verification email for {email}: {e}")
        return False


def create_and_send_verification(email: str, ip_address: str = None) -> tuple[bool, str, dict]:
    """
    创建并发送验证码

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）

    Returns:
        tuple[bool, str, dict]: (是否成功, 错误消息, 额外信息)
    """
    # 1. 检查邮箱域名
    if not is_email_domain_allowed(email):
        return False, "不支持的邮箱域名，请使用常用邮箱服务商", {}

    # 2. 检查发送频率限制
    can_send, remaining = check_rate_limit(email, ip_address)
    if not can_send:
        return False, "发送过于频繁，请稍后再试", {"remaining_attempts": 0}

    # 3. 清理该邮箱的过期验证码
    EmailVerification.objects.filter(
        email=email,
        expires_at__lt=timezone.now()
    ).delete()

    # 4. 检查是否有未过期的验证码
    existing_verification = EmailVerification.objects.filter(
        email=email,
        is_used=False,
        expires_at__gt=timezone.now()
    ).first()

    if existing_verification:
        # 如果有未过期的验证码，检查是否刚刚发送（防止重复发送）
        time_since_last = timezone.now() - existing_verification.created_at
        if time_since_last < timedelta(minutes=1):
            return False, "验证码已发送，请稍后再试", {
                "remaining_attempts": remaining - 1,
                "expires_in_minutes": int((existing_verification.expires_at - timezone.now()).total_seconds() / 60)
            }

    # 5. 创建新的验证码
    verification = EmailVerification.create_verification(email, ip_address)

    # 6. 发送验证邮件
    email_sent = send_verification_email(email, verification.verification_code)

    if not email_sent:
        # 如果邮件发送失败，删除验证码记录
        verification.delete()
        return False, "邮件发送失败，请稍后重试", {}

    # 7. 增加发送次数计数
    increment_rate_limit(email, ip_address)

    return True, "验证码已发送", {
        "remaining_attempts": remaining - 1,
        "expires_in_minutes": settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES
    }


def verify_email_code(email: str, code: str) -> tuple[bool, str]:
    """
    验证邮箱验证码

    Args:
        email: 邮箱地址
        code: 验证码

    Returns:
        tuple[bool, str]: (是否验证成功, 错误消息)
    """
    if not email or not code:
        return False, "邮箱和验证码不能为空"

    # 查找匹配的验证码
    verification = EmailVerification.objects.filter(
        email=email,
        verification_code=code,
        is_used=False
    ).first()

    if not verification:
        return False, "验证码错误或已失效"

    # 检查是否过期
    if verification.is_expired():
        return False, "验证码已过期"

    # 标记为已使用
    verification.is_used = True
    verification.save()

    logger.info(f"Email verification successful for {email}")
    return True, "验证成功"