"""
JWT 认证 + RBAC 单元/集成测试。
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from idmas.api.middleware.auth import (
    AuthError,
    CurrentUser,
    create_access_token,
    get_current_user,
    require_permission,
    verify_jwt,
)
from idmas.api.middleware.error_handler import auth_exception_handler


class TestTokenRoundtrip:
    def test_create_and_verify(self):
        tok = create_access_token("u1", "engineer", "设计部")
        user = verify_jwt(tok)
        assert user.sub == "u1"
        assert user.role == "engineer"
        assert "task:create" in user.permissions

    def test_admin_wildcard(self):
        user = verify_jwt(create_access_token("a", "admin"))
        assert user.has_permission("anything:goes") is True

    def test_engineer_lacks_writeback(self):
        user = verify_jwt(create_access_token("e", "engineer"))
        assert user.has_permission("plm:writeback") is False

    def test_invalid_token(self):
        with pytest.raises(AuthError) as ei:
            verify_jwt("not-a-token")
        assert ei.value.status_code == 401

    def test_expired_token(self):
        tok = create_access_token("u", "engineer", expire_minutes=5)
        # 手工造一个已过期的 token（绕过 expire_minutes 下限）
        import datetime as dt
        from idmas.config.settings import get_settings
        past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        expired = jwt.encode(
            {"sub": "u", "role": "engineer", "iss": "idmas-auth",
             "iat": past, "exp": past},
            get_settings().JWT_SECRET, algorithm="HS256")
        with pytest.raises(AuthError) as ei:
            verify_jwt(expired)
        assert ei.value.code == "IDMAS-401-002"


# ── 依赖在真实路由上的行为 ──────────────────────────────────────────────

@pytest.fixture()
def app():
    app = FastAPI()
    app.add_exception_handler(AuthError, auth_exception_handler)

    @app.get("/me")
    async def me(user: CurrentUser = Depends(get_current_user)):
        return {"sub": user.sub, "role": user.role}

    @app.post("/writeback")
    async def wb(user: CurrentUser = Depends(require_permission("plm:writeback"))):
        return {"ok": True}

    return app


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


class TestProtectedRoutes:
    def test_no_token_401(self, client):
        assert client.get("/me").status_code == 401

    def test_valid_token_200(self, client):
        tok = create_access_token("u1", "engineer")
        r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        assert r.json()["sub"] == "u1"

    def test_permission_denied_403(self, client):
        tok = create_access_token("e", "engineer")     # 无 plm:writeback
        r = client.post("/writeback", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "IDMAS-403-001"

    def test_permission_granted(self, client):
        tok = create_access_token("r", "reviewer")     # 有 plm:writeback
        r = client.post("/writeback", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
