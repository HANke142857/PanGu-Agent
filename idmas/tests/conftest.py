# =============================================================================
# Pytest 全局Fixtures
#
# Fixtures:
#   - app: FastAPI测试应用实例
#   - client: httpx.AsyncClient 测试客户端
#   - db_session: 测试数据库会话 (每个测试自动回滚)
#   - redis_client: 测试Redis客户端 (使用独立DB)
#   - mock_vllm: vLLM Mock服务 (返回预设响应)
#   - mock_ocr: PaddleOCR Mock
#   - sample_drawing: 示例图纸数据
#   - sample_task: 示例任务数据
#   - auth_token: 测试用JWT Token (engineer/reviewer/admin)
#
# 配置:
#   - 使用testcontainers启动临时PostgreSQL/Redis
#   - 或使用SQLite内存数据库 (快速单元测试)
# =============================================================================
