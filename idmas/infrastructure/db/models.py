# =============================================================================
# SQLAlchemy ORM 模型定义
#
# 对应PostgreSQL DDL (参见技术设计3.2节)
#
# 模型:
#   - UserModel: 用户表 (users)
#     字段: id, username, email, hashed_password, role, department, is_active
#     约束: role IN (engineer, reviewer, admin)
#
#   - DrawingModel: 图纸文档表 (drawings)
#     字段: id, source_system, source_doc_id, title, drawing_type, file_format,
#            file_url, file_size_bytes, image_width, image_height,
#            lifecycle_state, uploaded_by, metadata
#     索引: idx_drawings_source, idx_drawings_type, idx_drawings_title_trgm(GIN)
#
#   - AnalysisTaskModel: 解析任务表 (analysis_tasks)
#     字段: id, drawing_id, user_id, task_type, prompt_mode, question, background,
#            status, langgraph_thread_id, vision_result, ocr_result, design_result,
#            process_result, knowledge_result, report_result, conflicts,
#            human_decision, inference_time_ms, total_tokens, model_version,
#            error_code, error_message
#     索引: idx_tasks_status(partial), idx_tasks_user, idx_tasks_langgraph
#
#   - DrawingLabelModel: 标号表 (drawing_labels)
#     字段: id, drawing_id, task_id, label_id, name, confidence,
#            spatial_info, bounding_box, source, verified_by, verified_at
#     索引: idx_labels_drawing, idx_labels_name(GIN tsvector)
#
#   - ReviewRecordModel: 审核记录表 (review_records)
#     字段: id, task_id, reviewer_id, label_id, original_name, corrected_name,
#            action, feedback_status
#
#   - AuditLogModel: 审计日志表 (audit_logs)
#     字段: id, user_id, action, resource_type, resource_id, detail, ip_address
#     索引: idx_audit_time
#     分区: 按月分区 (RANGE on created_at)
# =============================================================================
