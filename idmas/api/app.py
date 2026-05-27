# =============================================================================
# FastAPI 应用工厂
#
# 职责:
#   - 创建FastAPI实例
#   - 注册路由 (api/routes/)
#   - 注册中间件 (认证、限流、CORS、错误处理)
#   - 注册启动/关闭事件 (DB连接池、Redis、MQ消费者等)
#   - 挂载Prometheus metrics端点 (/metrics)
#
# 方法:
#   - create_app() -> FastAPI
#     创建并配置完整的FastAPI应用
#
# CORS配置:
#   - 非通配符(*)，通过APP_CORS_ORIGINS环境变量配置
#
# 文档:
#   - Swagger UI: /docs
#   - ReDoc: /redoc
#   - OpenAPI JSON: /openapi.json
# =============================================================================
