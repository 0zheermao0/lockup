"""
Secure file upload utilities
"""
import os
import uuid
import time
import hashlib
import mimetypes
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from PIL import Image
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available, using fallback MIME detection")


# 允许的文件类型
ALLOWED_IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'
}

ALLOWED_VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'
}

ALLOWED_DOCUMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.rtf'
}

ALL_ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# 允许的MIME类型
ALLOWED_IMAGE_MIMES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml'
}

ALLOWED_VIDEO_MIMES = {
    'video/mp4', 'video/avi', 'video/quicktime', 'video/x-ms-wmv',
    'video/x-flv', 'video/webm', 'video/x-matroska'
}

ALLOWED_DOCUMENT_MIMES = {
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'application/rtf'
}

ALL_ALLOWED_MIMES = ALLOWED_IMAGE_MIMES | ALLOWED_VIDEO_MIMES | ALLOWED_DOCUMENT_MIMES

# 文件大小限制（字节）
MAX_IMAGE_SIZE = int(2.5 * 1024 * 1024)  # 2.5MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB


def generate_secure_filename(original_filename, file_type='image'):
    """
    生成安全的文件名，包含时间戳和UUID

    Args:
        original_filename: 原始文件名
        file_type: 文件类型 ('image', 'video', 'document')

    Returns:
        安全的文件名
    """
    # 获取文件扩展名
    _, ext = os.path.splitext(original_filename.lower())

    # 验证扩展名
    if ext not in ALL_ALLOWED_EXTENSIONS:
        raise ValidationError(f"不支持的文件扩展名: {ext}")

    # 生成时间戳
    timestamp = int(time.time() * 1000)  # 毫秒级时间戳

    # 生成短UUID
    short_uuid = str(uuid.uuid4())[:8]

    # 生成文件内容哈希前缀（如果需要的话）
    hash_prefix = hashlib.md5(f"{timestamp}{short_uuid}".encode()).hexdigest()[:8]

    # 构建安全文件名
    secure_filename = f"{file_type}_{timestamp}_{short_uuid}_{hash_prefix}{ext}"

    return secure_filename


def validate_file_security(uploaded_file):
    """
    验证上传文件的安全性

    Args:
        uploaded_file: Django UploadedFile对象

    Returns:
        dict: 包含文件信息的字典

    Raises:
        ValidationError: 文件不安全时抛出异常
    """
    # 检查文件大小
    if uploaded_file.size > MAX_VIDEO_SIZE:  # 使用最大限制
        raise ValidationError(f"文件过大，最大允许 {MAX_VIDEO_SIZE / 1024 / 1024:.1f}MB")

    # 获取文件扩展名
    original_name = uploaded_file.name
    _, ext = os.path.splitext(original_name.lower())

    # 验证扩展名
    if ext not in ALL_ALLOWED_EXTENSIONS:
        raise ValidationError(f"不支持的文件类型: {ext}")

    # 检测MIME类型
    uploaded_file.seek(0)
    file_content = uploaded_file.read(1024)  # 读取前1KB用于检测
    uploaded_file.seek(0)

    detected_mime = None

    if MAGIC_AVAILABLE:
        try:
            detected_mime = magic.from_buffer(file_content, mime=True)
        except Exception as e:
            print(f"Magic detection failed: {e}")

    # 如果magic检测失败或不可用，使用mimetypes作为备选
    if not detected_mime:
        detected_mime, _ = mimetypes.guess_type(original_name)

    # 如果仍然无法检测，根据扩展名推断
    if not detected_mime:
        if ext == '.svg':
            detected_mime = 'image/svg+xml'
        elif ext == '.gif':
            detected_mime = 'image/gif'
        elif ext in ALLOWED_IMAGE_EXTENSIONS:
            detected_mime = 'image/jpeg'  # 默认图片类型
        elif ext in ALLOWED_VIDEO_EXTENSIONS:
            detected_mime = 'video/mp4'   # 默认视频类型
        elif ext in ALLOWED_DOCUMENT_EXTENSIONS:
            detected_mime = 'application/pdf'  # 默认文档类型

    # 验证MIME类型
    if detected_mime not in ALL_ALLOWED_MIMES:
        raise ValidationError(f"不支持的文件格式: {detected_mime}")

    # 确定文件类型
    file_type = 'document'  # 默认
    if detected_mime in ALLOWED_IMAGE_MIMES:
        file_type = 'image'
    elif detected_mime in ALLOWED_VIDEO_MIMES:
        file_type = 'video'

    # 针对图片的额外验证
    if file_type == 'image':
        # SVG文件跳过PIL验证，因为PIL不支持SVG
        if detected_mime == 'image/svg+xml':
            # SVG文件的基本验证：检查是否包含SVG标签
            uploaded_file.seek(0)
            try:
                content = uploaded_file.read(1024).decode('utf-8', errors='ignore')
                if '<svg' not in content.lower():
                    raise ValidationError("无效的SVG文件")
            except UnicodeDecodeError:
                raise ValidationError("无效的SVG文件")
            uploaded_file.seek(0)
        else:
            try:
                # 使用PIL验证图片
                uploaded_file.seek(0)
                with Image.open(uploaded_file) as img:
                    # 检查图片尺寸
                    if img.width > 4096 or img.height > 4096:
                        raise ValidationError("图片尺寸过大，最大支持 4096x4096 像素")

                    # 检查图片格式
                    if img.format.lower() not in ['jpeg', 'png', 'gif', 'webp', 'bmp']:
                        raise ValidationError(f"不支持的图片格式: {img.format}")

                uploaded_file.seek(0)

            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError("无效的图片文件")

    # 检查文件大小限制（按类型）
    if file_type == 'image' and uploaded_file.size > MAX_IMAGE_SIZE:
        raise ValidationError(f"图片文件过大，最大允许 {MAX_IMAGE_SIZE / 1024 / 1024:.1f}MB")
    elif file_type == 'video' and uploaded_file.size > MAX_VIDEO_SIZE:
        raise ValidationError(f"视频文件过大，最大允许 {MAX_VIDEO_SIZE / 1024 / 1024:.1f}MB")
    elif file_type == 'document' and uploaded_file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(f"文档文件过大，最大允许 {MAX_DOCUMENT_SIZE / 1024 / 1024:.1f}MB")

    return {
        'file_type': file_type,
        'mime_type': detected_mime,
        'original_name': original_name,
        'file_size': uploaded_file.size,
        'extension': ext
    }


def secure_file_upload_to(instance, filename, upload_dir='uploads'):
    """
    安全的文件上传路径生成器

    Args:
        instance: 模型实例
        filename: 原始文件名
        upload_dir: 上传目录前缀

    Returns:
        安全的文件路径
    """
    # 验证文件（这里只做基础验证，详细验证在视图中进行）
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALL_ALLOWED_EXTENSIONS:
        raise ValidationError(f"不支持的文件扩展名: {ext}")

    # 确定文件类型
    file_type = 'document'
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        file_type = 'image'
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        file_type = 'video'

    # 生成安全文件名
    secure_filename = generate_secure_filename(filename, file_type)

    # 生成日期路径
    now = datetime.now()
    date_path = now.strftime('%Y/%m/%d')

    # 构建完整路径
    return f"{upload_dir}/{date_path}/{secure_filename}"


# 为不同类型创建专用的上传路径生成器
def secure_task_file_upload_to(instance, filename):
    """任务提交文件的安全上传路径"""
    # 标记为新上传，使用安全路径
    instance._is_new_upload = True
    return secure_file_upload_to(instance, filename, 'task_submissions')


def secure_post_image_upload_to(instance, filename):
    """动态图片的安全上传路径"""
    # 标记为新上传，使用安全路径
    instance._is_new_upload = True
    return secure_file_upload_to(instance, filename, 'posts/images')


def secure_comment_image_upload_to(instance, filename):
    """评论图片的安全上传路径"""
    # 标记为新上传，使用安全路径
    instance._is_new_upload = True
    return secure_file_upload_to(instance, filename, 'comments/images')


def secure_avatar_upload_to(instance, filename):
    """用户头像的安全上传路径"""
    # 标记为新上传，使用安全路径
    instance._is_new_upload = True
    return secure_file_upload_to(instance, filename, 'avatars')


def clean_filename_for_display(filename):
    """
    清理文件名用于显示（移除时间戳等安全信息）

    Args:
        filename: 安全文件名

    Returns:
        清理后的显示文件名
    """
    if not filename:
        return filename

    # 提取原始文件名部分（如果是安全格式）
    basename = os.path.basename(filename)

    # 如果是我们生成的安全文件名格式，尝试提取扩展名
    if '_' in basename and len(basename.split('_')) >= 4:
        # 格式: file_type_timestamp_uuid_hash.ext
        parts = basename.split('_')
        if len(parts) >= 4:
            # 获取扩展名
            last_part = parts[-1]  # hash.ext
            if '.' in last_part:
                ext = '.' + last_part.split('.')[-1]
                return f"uploaded_file{ext}"

    return basename


def validate_uploaded_file(uploaded_file, expected_type='image'):
    """
    验证上传的文件

    Args:
        uploaded_file: Django UploadedFile对象
        expected_type: 期望的文件类型 ('image', 'video', 'document')

    Returns:
        dict: 文件信息

    Raises:
        ValidationError: 验证失败时抛出异常
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # 使用现有的安全验证函数
        file_info = validate_file_security(uploaded_file)

        # 检查文件类型是否符合期望
        if expected_type and file_info['file_type'] != expected_type:
            logger.error(f"File type mismatch: expected {expected_type}, got {file_info['file_type']}")
            raise ValidationError(f"文件类型不匹配，期望 {expected_type}，实际为 {file_info['file_type']}")

        logger.info(f"File validation successful: {file_info['original_name']} ({file_info['file_size']} bytes)")
        return file_info

    except ValidationError as e:
        logger.error(f"File validation failed for {uploaded_file.name}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file validation for {uploaded_file.name}: {e}")
        raise ValidationError(f"文件验证过程中发生错误: {str(e)}")