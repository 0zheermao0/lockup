"""
密码重置相关工具函数
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from users.models import PasswordReset
from .email import send_email_task

logger = logging.getLogger(__name__)
User = get_user_model()


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


def get_reset_rate_limit_key(email: str, ip_address: str = None) -> str:
    """
    生成密码重置频率限制的缓存键

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）

    Returns:
        str: 缓存键
    """
    if ip_address:
        return f"password_reset_rate_limit:{email}:{ip_address}"
    else:
        return f"password_reset_rate_limit:{email}"


def check_reset_rate_limit(email: str, ip_address: str = None) -> tuple[bool, int]:
    """
    检查密码重置发送频率限制

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）

    Returns:
        tuple[bool, int]: (是否可以发送, 剩余可发送次数)
    """
    max_attempts = getattr(settings, 'EMAIL_VERIFICATION_MAX_ATTEMPTS_PER_HOUR', 5)

    # 检查邮箱级别的限制
    email_key = get_reset_rate_limit_key(email)
    email_attempts = cache.get(email_key, 0)

    if email_attempts >= max_attempts:
        return False, 0

    # 检查IP级别的限制（如果提供了IP）
    if ip_address:
        ip_key = get_reset_rate_limit_key('', ip_address)
        ip_attempts = cache.get(ip_key, 0)

        if ip_attempts >= max_attempts * 2:  # IP限制更严格
            return False, 0

    remaining = max_attempts - email_attempts
    return True, remaining


def increment_reset_rate_limit(email: str, ip_address: str = None):
    """
    增加密码重置发送次数计数

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）
    """
    timeout = 3600  # 1小时

    # 增加邮箱计数
    email_key = get_reset_rate_limit_key(email)
    current_count = cache.get(email_key, 0)
    cache.set(email_key, current_count + 1, timeout)

    # 增加IP计数（如果提供了IP）
    if ip_address:
        ip_key = get_reset_rate_limit_key('', ip_address)
        current_ip_count = cache.get(ip_key, 0)
        cache.set(ip_key, current_ip_count + 1, timeout)


def clean_expired_password_resets():
    """
    清理过期的密码重置记录
    """
    expired_count = PasswordReset.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()[0]

    if expired_count > 0:
        logger.info(f"Cleaned {expired_count} expired password reset records")

    return expired_count


def send_password_reset_email(email: str, reset_code: str) -> bool:
    """
    发送密码重置邮件

    Args:
        email: 收件人邮箱
        reset_code: 重置码

    Returns:
        bool: 是否发送成功
    """
    subject = "Lock-Up 密码重置验证码"

    # 邮件内容（HTML格式）
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Lock-Up 密码重置</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: white; padding: 30px; border: 2px solid #000; border-top: none; border-radius: 0 0 8px 8px; }}
            .reset-code {{ font-size: 32px; font-weight: bold; color: #dc3545; text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border: 2px solid #dc3545; border-radius: 8px; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; text-align: center; }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 15px 0; }}
            .security {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 Lock-Up</h1>
                <h2>密码重置验证</h2>
            </div>
            <div class="content">
                <p>您好！</p>
                <p>您正在请求重置 Lock-Up 账号密码。请使用以下验证码完成密码重置：</p>

                <div class="reset-code">
                    {reset_code}
                </div>

                <div class="warning">
                    <strong>⚠️ 重要提醒：</strong>
                    <ul>
                        <li>验证码有效期为 15 分钟</li>
                        <li>请勿将验证码泄露给他人</li>
                        <li>验证码仅可使用一次</li>
                    </ul>
                </div>

                <div class="security">
                    <strong>🛡️ 安全提醒：</strong>
                    <ul>
                        <li>如非本人操作，请立即忽略此邮件</li>
                        <li>建议设置更强的密码</li>
                        <li>请妥善保管您的账号信息</li>
                    </ul>
                </div>

                <p>如果您没有请求重置密码，请忽略此邮件。您的账号安全不会受到影响。</p>

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
Lock-Up 密码重置验证

您好！

您正在请求重置 Lock-Up 账号密码。请使用以下验证码完成密码重置：

验证码：{reset_code}

重要提醒：
- 验证码有效期为 15 分钟
- 请勿将验证码泄露给他人
- 验证码仅可使用一次

安全提醒：
- 如非本人操作，请立即忽略此邮件
- 建议设置更强的密码
- 请妥善保管您的账号信息

如果您没有请求重置密码，请忽略此邮件。您的账号安全不会受到影响。

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

        logger.info(f"Password reset email queued for {email}, task_id: {result.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to queue password reset email for {email}: {e}")
        return False


def create_and_send_password_reset(email: str, ip_address: str = None) -> tuple[bool, str, dict]:
    """
    创建并发送密码重置码

    Args:
        email: 邮箱地址
        ip_address: IP地址（可选）

    Returns:
        tuple[bool, str, dict]: (是否成功, 错误消息, 额外信息)
    """
    # 1. 检查邮箱是否存在注册用户
    user = User.objects.filter(email=email).first()
    if not user:
        # 为了安全，不暴露邮箱是否存在
        return False, "如果该邮箱已注册，重置码将发送到您的邮箱", {}

    # 2. 检查邮箱域名
    if not is_email_domain_allowed(email):
        return False, "不支持的邮箱域名，请使用常用邮箱服务商", {}

    # 3. 检查发送频率限制
    can_send, remaining = check_reset_rate_limit(email, ip_address)
    if not can_send:
        return False, "发送过于频繁，请稍后再试", {"remaining_attempts": 0}

    # 4. 清理该邮箱的过期重置码
    PasswordReset.objects.filter(
        email=email,
        expires_at__lt=timezone.now()
    ).delete()

    # 5. 检查是否有未过期的重置码
    existing_reset = PasswordReset.objects.filter(
        email=email,
        is_used=False,
        expires_at__gt=timezone.now()
    ).first()

    if existing_reset:
        # 如果有未过期的重置码，检查是否刚刚发送（防止重复发送）
        time_since_last = timezone.now() - existing_reset.created_at
        if time_since_last < timedelta(minutes=1):
            return False, "重置码已发送，请稍后再试", {
                "remaining_attempts": remaining - 1,
                "expires_in_minutes": int((existing_reset.expires_at - timezone.now()).total_seconds() / 60)
            }

    # 6. 创建新的重置码
    reset_record = PasswordReset.create_reset_code(email, ip_address)

    # 7. 发送重置邮件
    email_sent = send_password_reset_email(email, reset_record.reset_code)

    if not email_sent:
        # 如果邮件发送失败，删除创建的重置码
        reset_record.delete()
        return False, "邮件发送失败，请稍后重试", {"remaining_attempts": remaining}

    # 8. 增加发送次数计数
    increment_reset_rate_limit(email, ip_address)

    logger.info(f"Password reset code created and email sent for {email}")

    return True, "重置码已发送到您的邮箱", {
        "remaining_attempts": remaining - 1,
        "expires_in_minutes": 15
    }


def verify_reset_code(email: str, reset_code: str) -> tuple[bool, str]:
    """
    验证密码重置码

    Args:
        email: 邮箱地址
        reset_code: 重置码

    Returns:
        tuple[bool, str]: (是否成功, 错误消息)
    """
    if not email or not reset_code:
        return False, "邮箱和重置码不能为空"

    if len(reset_code) != 6 or not reset_code.isdigit():
        return False, "重置码格式错误"

    # 查找匹配的重置记录
    try:
        reset_record = PasswordReset.objects.get(
            email=email,
            reset_code=reset_code,
            is_used=False
        )
    except PasswordReset.DoesNotExist:
        return False, "重置码错误或已失效"

    # 检查是否过期
    if reset_record.is_expired():
        return False, "重置码已过期"

    # 标记为已使用
    reset_record.is_used = True
    reset_record.save()

    logger.info(f"Password reset code verified successfully for {email}")
    return True, "重置码验证成功"


def reset_user_password(email: str, reset_code: str, new_password: str) -> tuple[bool, str]:
    """
    重置用户密码

    Args:
        email: 邮箱地址
        reset_code: 重置码
        new_password: 新密码

    Returns:
        tuple[bool, str]: (是否成功, 错误消息)
    """
    # 1. 验证重置码
    code_valid, code_message = verify_reset_code(email, reset_code)
    if not code_valid:
        return False, code_message

    # 2. 获取用户
    user = User.objects.filter(email=email).first()
    if not user:
        return False, "用户不存在"

    # 3. 设置新密码
    try:
        user.set_password(new_password)
        user.save()
        logger.info(f"Password reset successfully for user {user.username} ({email})")
        return True, "密码重置成功"
    except Exception as e:
        logger.error(f"Failed to reset password for {email}: {e}")
        return False, "密码重置失败，请重试"