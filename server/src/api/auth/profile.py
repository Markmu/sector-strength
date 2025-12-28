"""用户资料管理API端点"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import json
from datetime import datetime, timezone, timedelta
import uuid

from src.db.database import get_db
from src.models.user import User, UserPreferences, ActiveSession
from src.core.security import hash_password, verify_password
from src.core.deps import get_current_user
from src.schemas.auth import ProfileUpdate, PasswordChange, UserPreferencesUpdate
from src.core.settings import settings


router = APIRouter(prefix="/user", tags=["user-profile"])


@router.get("/profile", response_model=dict)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户资料信息

    Returns:
        dict: 包含用户基本信息的字典
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "timezone": current_user.timezone,
        "language": current_user.language,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }


@router.put("/profile", response_model=dict)
async def update_user_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户资料信息

    Args:
        profile_data: 包含要更新的资料字段

    Returns:
        dict: 更新后的用户信息
    """
    # 更新用户字段
    if profile_data.display_name is not None:
        current_user.display_name = profile_data.display_name
    if profile_data.timezone is not None:
        current_user.timezone = profile_data.timezone
    if profile_data.language is not None:
        current_user.language = profile_data.language

    # 更新updated_at时间
    current_user.updated_at = datetime.now(timezone.utc)

    try:
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新失败: {str(e)}"
        )

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "timezone": current_user.timezone,
        "language": current_user.language,
        "message": "资料更新成功"
    }


@router.get("/preferences", response_model=dict)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户偏好设置

    Returns:
        dict: 用户偏好设置
    """
    if not current_user.preferences:
        # 如果不存在，创建默认偏好设置
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    preferences = current_user.preferences
    return {
        "email_notifications": preferences.email_notifications,
        "push_notifications": preferences.push_notifications,
        "marketing_emails": preferences.marketing_emails,
        "created_at": preferences.created_at.isoformat() if preferences.created_at else None,
        "updated_at": preferences.updated_at.isoformat() if preferences.updated_at else None,
    }


@router.put("/preferences", response_model=dict)
async def update_user_preferences(
    preference_data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户偏好设置

    Args:
        preference_data: 包含要更新的偏好设置

    Returns:
        dict: 更新后的偏好设置
    """
    if not current_user.preferences:
        # 如果不存在，创建偏好设置
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    preferences = current_user.preferences

    # 更新偏好设置
    if preference_data.email_notifications is not None:
        preferences.email_notifications = preference_data.email_notifications
    if preference_data.push_notifications is not None:
        preferences.push_notifications = preference_data.push_notifications
    if preference_data.marketing_emails is not None:
        preferences.marketing_emails = preference_data.marketing_emails

    try:
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新失败: {str(e)}"
        )

    return {
        "email_notifications": preferences.email_notifications,
        "push_notifications": preferences.push_notifications,
        "marketing_emails": preferences.marketing_emails,
        "message": "偏好设置更新成功"
    }


@router.post("/change-password", response_model=dict)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更改用户密码

    Args:
        password_data: 包含当前密码和新密码

    Returns:
        dict: 操作结果
    """
    # 验证当前密码
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="当前密码不正确"
        )

    # 检查新密码是否与当前密码相同
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与当前密码相同"
        )

    # 更新密码
    current_user.password_hash = hash_password(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)

    try:
        db.add(current_user)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码更改失败: {str(e)}"
        )

    return {"message": "密码更改成功"}


@router.get("/sessions", response_model=dict)
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的活跃会话列表

    Returns:
        dict: 包含活跃会话列表
    """
    sessions = db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id,
        ActiveSession.expires_at > datetime.now(timezone.utc)
    ).all()

    session_list = []
    for session in sessions:
        try:
            device_info = json.loads(session.device_info) if session.device_info else {}
        except json.JSONDecodeError:
            device_info = {}

        session_list.append({
            "id": str(session.id),
            "session_id": session.session_id,
            "device_name": device_info.get("browser", "Unknown") + " on " + device_info.get("os", "Unknown"),
            "device_info": device_info,
            "ip_address": session.ip_address,
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        })

    return {"sessions": session_list}


@router.delete("/sessions/{session_id}", response_model=dict)
async def terminate_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    终止特定会话

    Args:
        session_id: 要终止的会话ID

    Returns:
        dict: 操作结果
    """
    session = db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id,
        ActiveSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话未找到"
        )

    try:
        db.delete(session)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"会话终止失败: {str(e)}"
        )

    return {"message": "会话已终止"}


@router.delete("/sessions/all", response_model=dict)
async def terminate_all_other_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    终止所有其他会话（当前会话除外）

    Returns:
        dict: 操作结果
    """
    # 获取当前会话ID（从token中获取）
    # 这里简化处理，实际应该从token解析会话ID
    current_session_id = None  # 需要实现从token获取会话ID的逻辑

    query = db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id
    )

    if current_session_id:
        query = query.filter(ActiveSession.session_id != current_session_id)

    try:
        deleted_count = query.delete()
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"会话终止失败: {str(e)}"
        )

    return {"message": f"已终止 {deleted_count} 个会话"}


@router.post("/deactivate", response_model=dict)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    停用用户账户

    Returns:
        dict: 操作结果
    """
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)

    try:
        db.add(current_user)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"账户停用失败: {str(e)}"
        )

    return {"message": "账户已停用"}


@router.delete("/account", response_model=dict)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    请求删除账户（实现宽限期）

    注意：实际实现应该标记账户为待删除，而不是立即删除
    这里简化处理，实际项目中应添加删除宽限期

    Returns:
        dict: 包含删除信息的操作结果
    """
    # 标记账户为待删除
    current_user.is_active = False
    # 可以添加删除标记和时间戳
    deletion_date = datetime.now(timezone.utc) + timedelta(days=30)  # 30天宽限期

    try:
        db.add(current_user)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"账户删除请求失败: {str(e)}"
        )

    return {
        "message": "账户删除请求已提交，账户将在30天后永久删除",
        "deletion_date": deletion_date.isoformat()
    }
