# =============================================================================
# Agent层单元测试
#
# 测试:
#   - IDMASState 状态初始化
#   - Master Graph 条件路由函数
#     - route_by_intent: 各意图正确路由
#     - route_after_vision: Vision后续路由
#     - check_conflicts: 冲突/低置信度/无冲突路由
#     - check_debate: 辩论resolved/unresolved路由
#   - Vision SubGraph 节点 (Mock vLLM)
#   - Token计数器
#   - 重试装饰器
#   - 熔断器状态转换
# =============================================================================
