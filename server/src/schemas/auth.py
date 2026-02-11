"""认证相关的Pydantic模型"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    """登录请求模型"""
    email: Optional[str] = Field(None, description="用户邮箱")
    username: Optional[str] = Field(None, description="用户名")
    password: str = Field(..., min_length=1, description="用户密码")
    remember_me: bool = Field(False, description="记住我")

    @model_validator(mode="after")
    def validate_identity(self):
        if not self.email and not self.username:
            raise ValueError("email or username is required")
        if self.email and "@" not in self.email:
            raise ValueError("invalid email format")
        return self


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")
    user: dict = Field(..., description="用户信息")
    data: Optional[dict] = Field(None, description="兼容旧响应结构")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应模型"""
    access_token: str = Field(..., description="新的访问令牌")
    refresh_token: str = Field(..., description="新的刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")


class LogoutRequest(BaseModel):
    """注销请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class LoginAttemptResponse(BaseModel):
    """登录尝试响应模型"""
    id: str = Field(..., description="尝试ID")
    email: str = Field(..., description="尝试登录的邮箱")
    success: bool = Field(..., description="是否登录成功")
    ip_address: Optional[str] = Field(None, description="IP地址")
    created_at: datetime = Field(..., description="尝试时间")


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: str = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    username: Optional[str] = Field(None, description="用户名")
    is_active: bool = Field(..., description="账户是否激活")
    is_verified: bool = Field(..., description="邮箱是否已验证")
    role: str = Field(..., description="用户角色: admin, user")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")


class ProfileUpdate(BaseModel):
    """用户资料更新请求模型"""
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    timezone: Optional[str] = Field(None, max_length=50, description="时区")
    language: Optional[str] = Field(None, max_length=10, description="语言偏好")


class ProfileResponse(BaseModel):
    """用户资料响应模型"""
    id: str = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    display_name: Optional[str] = Field(None, description="显示名称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    timezone: str = Field("UTC", description="时区")
    language: str = Field("en", description="语言偏好")
    message: Optional[str] = Field(None, description="操作消息")


class UserPreferencesUpdate(BaseModel):
    """用户偏好设置更新请求模型"""
    email_notifications: Optional[bool] = Field(None, description="邮件通知")
    push_notifications: Optional[bool] = Field(None, description="推送通知")
    marketing_emails: Optional[bool] = Field(None, description="营销邮件")


class UserPreferencesResponse(BaseModel):
    """用户偏好设置响应模型"""
    email_notifications: bool = Field(True, description="邮件通知")
    push_notifications: bool = Field(True, description="推送通知")
    marketing_emails: bool = Field(False, description="营销邮件")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    message: Optional[str] = Field(None, description="操作消息")


class PasswordChange(BaseModel):
    """密码更改请求模型"""
    current_password: str = Field(..., min_length=8, description="当前密码")
    new_password: str = Field(..., min_length=8, description="新密码")


class SessionResponse(BaseModel):
    """活跃会话响应模型"""
    id: str = Field(..., description="会话ID")
    session_id: str = Field(..., description="会话标识符")
    device_name: str = Field(..., description="设备名称")
    device_info: Optional[dict] = Field(None, description="设备信息")
    ip_address: Optional[str] = Field(None, description="IP地址")
    last_activity: Optional[datetime] = Field(None, description="最后活动时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class SessionsListResponse(BaseModel):
    """活跃会话列表响应模型"""
    sessions: List[SessionResponse] = Field(..., description="会话列表")
