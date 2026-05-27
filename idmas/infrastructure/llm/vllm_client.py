# =============================================================================
# vLLM 推理客户端
#
# 职责:
#   - 封装vLLM OpenAI兼容API调用
#   - 支持Vision (图片+文本) 和 Text-only 两种模式
#   - 连接池管理 (httpx.AsyncClient)
#   - 熔断器集成 (5次连续>30s → 熔断)
#   - GPU OOM检测与告警
#
# 配置:
#   - VLLM_URL: vLLM服务地址 (默认 http://localhost:8000)
#   - VLLM_MODEL: 模型名称 (qwen2.5-vl-7b-finetuned)
#   - VLLM_MAX_TOKENS: 最大生成Token (2048)
#   - VLLM_TEMPERATURE: 温度 (0.1)
#   - VLLM_TIMEOUT: 超时时间 (60s)
#   - VLLM_MAX_CONCURRENT: 最大并发 (8, 5090单卡上限)
#
# 方法:
#   - chat_completion(messages, **kwargs) -> ChatCompletionResponse
#   - vision_inference(image_url, prompt, **kwargs) -> str
#   - health_check() -> bool
#   - get_model_info() -> dict
#
# 缓存策略:
#   - 基于image_hash的结果缓存 (Redis, TTL=6h)
#   - Key格式: vlm:cache:{image_hash}
# =============================================================================
