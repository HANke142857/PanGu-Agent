# =============================================================================
# JWT认证中间件
#
# 认证方式 (参见技术设计4.3节):
#   - Web用户: OAuth 2.0 Authorization Code → JWT (RS256)
#   - CAD插件: API Key + JWT 双重认证
#   - PLM Webhook: HMAC签名 + IP白名单
#   - 服务间: mTLS
#
# JWT配置:
#   - 算法: RS256
#   - 有效期: 1小时
#   - 签发者: idmas-auth
#   - 密钥轮换: 90天，双密钥过渡(新签旧验→全切)
#
# JWT Payload:
#   sub, role, department, permissions, exp, iat, iss
#
# RBAC权限:
#   engineer:  [task:create, task:view:own, drawing:upload]
#   reviewer:  [task:create, task:view:all, label:verify, plm:writeback, drawing:upload]
#   admin:     [*]
#
# 方法:
#   - verify_jwt(token: str) -> JWTPayload
#   - get_current_user(request) -> User  # FastAPI Depends
#   - require_permission(permission: str) -> Depends  # 权限检查依赖
# =============================================================================
