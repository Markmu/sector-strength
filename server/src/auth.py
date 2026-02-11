"""Compatibility wrapper for legacy auth imports."""

from src.core.auth_service import AuthService


def get_password_hash(password: str) -> str:
    return AuthService.get_password_hash(password)


def hash_password(password: str) -> str:
    return AuthService.get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return AuthService.verify_password(plain_password, hashed_password)


__all__ = ["get_password_hash", "hash_password", "verify_password"]
