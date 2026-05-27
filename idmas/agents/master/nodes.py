# =============================================================================
# Master Graph 节点函数
#
# 每个节点函数接收 IDMASState，返回状态更新字典
#
# 节点:
#   - intent_node(state) -> dict
#     调用LLM识别用户意图，确定需要的Agent列表和任务DAG
#
#   - preprocess_node(state) -> dict
#     图片尺寸校验(>4096²拒绝)、URL规范化、参数校验
#
#   - ocr_node(state) -> dict
#     调用PaddleOCR提取标号文字和坐标
#
#   - conflict_node(state) -> dict
#     比对多个Agent的标号识别结果，检测命名/位置冲突
#     置信度差距 > 15% 且高方 > 85% → 自动裁决
#     否则 → 标记需人工审核
#
#   - debate_node(state) -> dict
#     对抗辩论: 最多2轮证据+反驳
#     计算加权置信度，判定是否自动解决
#
#   - human_review_node(state) -> dict
#     人工审核节点(Graph在此中断，等待人工输入后恢复)
#
#   - aggregation_node(state) -> dict
#     汇总所有结果，持久化到数据库
#
#   - error_node(state) -> dict
#     统一错误处理，记录错误码和消息
# =============================================================================
