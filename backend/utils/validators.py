"""
Custom file validators for secure upload
"""
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .file_upload import validate_file_security


def secure_file_validator(uploaded_file):
    """
    Django文件字段验证器，用于验证上传文件的安全性

    Args:
        uploaded_file: Django UploadedFile对象

    Raises:
        ValidationError: 文件不安全时抛出异常
    """
    if not uploaded_file:
        return

    if not isinstance(uploaded_file, UploadedFile):
        raise ValidationError("无效的文件对象")

    try:
        # 使用我们的安全验证函数
        validate_file_security(uploaded_file)
    except ValidationError:
        raise  # 重新抛出验证错误
    except Exception as e:
        raise ValidationError(f"文件验证失败: {str(e)}")


def secure_image_validator(uploaded_file):
    """
    专门用于图片的验证器

    Args:
        uploaded_file: Django UploadedFile对象

    Raises:
        ValidationError: 图片不安全时抛出异常
    """
    if not uploaded_file:
        return

    try:
        file_info = validate_file_security(uploaded_file)

        # 确保是图片类型
        if file_info['file_type'] != 'image':
            raise ValidationError("只允许上传图片文件")

    except ValidationError:
        raise  # 重新抛出验证错误
    except Exception as e:
        raise ValidationError(f"图片验证失败: {str(e)}")


def secure_avatar_validator(uploaded_file):
    """
    专门用于头像的验证器

    Args:
        uploaded_file: Django UploadedFile对象

    Raises:
        ValidationError: 头像不安全时抛出异常
    """
    if not uploaded_file:
        return

    try:
        file_info = validate_file_security(uploaded_file)

        # 确保是图片类型
        if file_info['file_type'] != 'image':
            raise ValidationError("头像只能是图片文件")

        # 头像特殊限制
        max_avatar_size = int(2.5 * 1024 * 1024)  # 2.5MB
        if file_info['file_size'] > max_avatar_size:
            raise ValidationError(f"头像文件过大，最大允许 {max_avatar_size / 1024 / 1024:.1f}MB")

    except ValidationError:
        raise  # 重新抛出验证错误
    except Exception as e:
        raise ValidationError(f"头像验证失败: {str(e)}")