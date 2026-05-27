# =============================================================================
# PLM适配器基类 (Abstract Base)
#
# 定义统一的PLM操作接口，各品牌PLM实现此接口
#
# 抽象方法:
#   - get_document(doc_id: str) -> dict
#     获取PLM文档信息
#
#   - get_bom(doc_id: str) -> dict
#     获取BOM清单
#
#   - writeback(doc_id: str, data: dict) -> dict
#     回写解析结果到PLM
#     包含: 幂等Key检查(Redis, TTL=7d) + 指数退避重试(30s,60s,120s,300s,600s)
#
#   - verify_webhook(signature: str, payload: bytes) -> bool
#     验证PLM Webhook签名 (HMAC + IP白名单)
#
#   - health_check() -> bool
#
# PLM回写幂等:
#   1. 生成幂等Key: plm:idempotent:{doc_id}:{data_hash}
#   2. 查Redis，已存在则跳过
#   3. 执行回写
#   4. 成功后记录幂等Key (TTL=7d)
# =============================================================================
