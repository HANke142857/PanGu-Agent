# =============================================================================
# Redis 缓存客户端
#
# 职责:
#   - 连接管理 (支持Sentinel模式: 1主2从3哨兵)
#   - LangGraph Checkpoint存储
#   - 任务状态缓存
#   - vLLM结果缓存
#   - API限流计数
#   - SSE事件Pub/Sub
#   - 人工审核队列
#   - PLM回写重试队列
#
# 配置:
#   - REDIS_URL: 连接地址 (redis://localhost:6379/0)
#
# Key规范 (参见技术设计6.1节):
#   - lg:thread:{thread_id}      Hash   TTL=24h  LangGraph Checkpoint
#   - task:status:{task_id}      String TTL=1h   任务状态缓存
#   - vlm:cache:{image_hash}     String TTL=6h   vLLM结果缓存
#   - review:queue               List   无TTL    人工审核FIFO队列
#   - plm:retry                  SortedSet 无TTL PLM回写重试
#   - sse:task:{task_id}         Pub/Sub          SSE事件通道
#   - ratelimit:{user}:{path}    String TTL=1min  API限流计数
#
# 方法:
#   - get / set / delete / exists
#   - publish / subscribe (Pub/Sub)
#   - lpush / rpop (队列)
#   - zadd / zrangebyscore (有序集合)
#   - incr_with_ttl (限流计数)
#   - health_check() -> bool
#
# 降级策略: Redis不可用时Checkpoint改内存模式(重启丢失)
# =============================================================================
