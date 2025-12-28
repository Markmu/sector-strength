"""输入清理和验证工具"""

import html
import re
from typing import Any


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    清理字符串输入

    Args:
        value: 要清理的字符串
        max_length: 最大允许长度

    Returns:
        str: 清理后的字符串
    """
    if not value:
        return ""

    # 转义 HTML 特殊字符
    value = html.escape(value)

    # 移除潜在的脚本标签
    value = re.sub(r'<script.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)

    # 移除危险的 HTML 属性
    dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'javascript:']
    for attr in dangerous_attrs:
        value = re.sub(attr, '', value, flags=re.IGNORECASE)

    # 限制长度
    if len(value) > max_length:
        value = value[:max_length]

    # 移除控制字符
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

    return value.strip()


def sanitize_email(email: str) -> str:
    """
    清理邮箱地址

    Args:
        email: 邮箱地址

    Returns:
        str: 清理后的邮箱地址
    """
    if not email:
        return ""

    # 转换为小写
    email = email.lower().strip()

    # 移除危险字符
    email = re.sub(r'[<>"\'\x00-\x1f\x7f-\xff]', '', email)

    # 验证基本格式
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return ""

    return email


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度

    Args:
        password: 密码字符串

    Returns:
        tuple: (是否有效, 错误信息)
    """
    if not password:
        return False, "密码不能为空"

    if len(password) < 8:
        return False, "密码长度至少8位"

    if len(password) > 128:
        return False, "密码长度不能超过128位"

    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含大写字母"

    if not re.search(r'[a-z]', password):
        return False, "密码必须包含小写字母"

    if not re.search(r'[0-9]', password):
        return False, "密码必须包含数字"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含特殊字符"

    # 检查常见的弱密码模式
    weak_patterns = [
        r'^123456',
        r'^password',
        r'^qwerty',
        r'^admin',
        r'^letmein'
    ]

    for pattern in weak_patterns:
        if re.match(pattern, password, re.IGNORECASE):
            return False, "密码过于简单，请使用更复杂的密码"

    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    """
    验证用户名

    Args:
        username: 用户名字符串

    Returns:
        tuple: (是否有效, 错误信息)
    """
    if not username:
        return True, ""  # 用户名是可选的

    username = username.strip()

    if len(username) < 2:
        return False, "用户名长度至少2个字符"

    if len(username) > 50:
        return False, "用户名长度不能超过50个字符"

    # 允许的字符：字母、数字、中文、下划线、连字符
    if not re.match(r'^[\w\u4e00-\u9fff-]+$', username):
        return False, "用户名只能包含字母、数字、中文、下划线和连字符"

    # 不能以特殊字符开头或结尾
    if username.startswith(('_', '-')) or username.endswith(('_', '-')):
        return False, "用户名不能以下划线或连字符开头或结尾"

    return True, ""


class InputValidator:
    """输入验证器类"""

    @staticmethod
    def validate_and_sanitize_register_data(data: dict) -> tuple[bool, dict, list]:
        """
        验证和清理注册数据

        Args:
            data: 原始输入数据

        Returns:
            tuple: (是否有效, 清理后的数据, 错误列表)
        """
        errors = []
        cleaned_data = {}

        # 验证和清理邮箱
        email = sanitize_email(data.get('email', ''))
        if not email:
            errors.append("邮箱格式无效")
        else:
            cleaned_data['email'] = email

        # 验证密码
        password = data.get('password', '')
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            errors.append(error_msg)
        else:
            cleaned_data['password'] = password

        # 验证和清理用户名（可选）
        username = sanitize_string(data.get('username', ''), max_length=50)
        if username:
            is_valid, error_msg = validate_username(username)
            if not is_valid:
                errors.append(error_msg)
            else:
                cleaned_data['username'] = username

        return len(errors) == 0, cleaned_data, errors