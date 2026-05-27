# =============================================================================
# Master Graph 构建
#
# 使用 LangGraph StateGraph 构建主编排图
# 节点:
#   - intent_recognition: 意图识别
#   - preprocess: 预处理(图片校验、参数规范化)
#   - vision_agent: Vision SubGraph (图纸视觉理解)
#   - ocr_extraction: OCR标号提取
#   - design_agent: Design SubGraph (设计规范分析)
#   - process_agent: Process SubGraph (工艺参数校验)
#   - knowledge_agent: Knowledge SubGraph (知识库RAG检索)
#   - conflict_detection: 冲突检测(多Agent结果比对)
#   - adversarial_debate: 对抗辩论(冲突自动裁决)
#   - human_review: 人工审核(interrupt_before中断点)
#   - report_agent: Report SubGraph (报告生成)
#   - result_aggregation: 结果聚合与持久化
#   - error_handler: 错误处理
#
# 条件路由:
#   - route_by_intent: 根据意图路由到不同Agent
#   - route_after_vision: Vision后续路由(design/process/knowledge/direct)
#   - check_conflicts: 冲突检查路由(has_conflict/low_confidence/no_conflict)
#   - check_debate: 辩论结果路由(resolved/unresolved)
#
# Checkpointer: Redis (TTL=24h)
# 中断点: human_review (interrupt_before)
# =============================================================================
