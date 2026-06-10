"""
JWT 认证 + RBAC 权限（FastAPI 依赖）。

MVP 用 HS256 对称密钥（JWT_SECRET），便于本地/测试；生产可换 RS256 + 密钥轮换。
认证为按需挂载：路由用 Depends(get_current_user) / Depends(require_permission(...))
即生效，不全局强制——未受保护的端点不受影响。

JWT Payload: sub, role, department, permissions, exp, iat, iss
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from idmas.config.settings import get_settings

ISSUER = "idmas-auth"

# RBAC：角色 → 权限
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "engineer": ["task:create", "task:view:own", "drawing:upload"],
    "reviewer": ["task:create", "task:view:all", "label:verify", "plm:writeback", "drawing:upload"],
    "admin":    ["*"],
}


class AuthError(Exception):
    """认证/授权失败。"""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class CurrentUser(BaseModel):
    sub:         str
    role:        str
    department:  str = ""
    permissions: list[str] = []

    def has_permission(self, required: str) -> bool:
        return "*" in self.permissions or required in self.permissions


def create_access_token(
    sub: str,
    role: str,
    department: str = "",
    *,
    secret: str | None = None,
    expire_minutes: int | None = None,
) -> str:
    settings = get_settings()
    secret = secret or settings.JWT_SECRET
    expire_minutes = expire_minutes or settings.JWT_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "department": department,
        "permissions": ROLE_PERMISSIONS.get(role, []),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "iss": ISSUER,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt(token: str, *, secret: str | None = None) -> CurrentUser:
    settings = get_settings()
    secret = secret or settings.JWT_SECRET
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], issuer=ISSUER)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError(401, "IDMAS-401-002", "令牌已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(401, "IDMAS-401-001", "无效令牌") from exc
    return CurrentUser(
        sub=claims.get("sub", ""),
        role=claims.get("role", ""),
        department=claims.get("department", ""),
        permissions=claims.get("permissions", []),
    )


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if creds is None or not creds.credentials:
        raise AuthError(401, "IDMAS-401-001", "缺少 Bearer 令牌")
    return verify_jwt(creds.credentials)


def require_permission(permission: str):
    """返回一个校验指定权限的 FastAPI 依赖。"""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_permission(permission):
            raise AuthError(403, "IDMAS-403-001", f"缺少权限: {permission}")
        return user

    return _checker
