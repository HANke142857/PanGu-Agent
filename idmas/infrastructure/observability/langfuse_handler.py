# =============================================================================
# LangFuse 可观测性处理器
#
# 职责:
#   - 初始化LangFuse客户端 (自建私有部署)
#   - 创建LangChain回调处理器
#   - 记录每个Agent节点的Trace/Span
#   - 记录Prompt模板、输入输出、Token消耗、延迟
#
# 配置:
#   - LANGFUSE_HOST: LangFuse服务地址 (自建)
#   - LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY: 认证
#
# 方法:
#   - get_callback_handler(trace_name, user_id, session_id) -> CallbackHandler
#   - flush() -> None
#
# 替代说明:
#   生产环境不使用LangSmith(SaaS)，用自建LangFuse + OTel替代
# =============================================================================
