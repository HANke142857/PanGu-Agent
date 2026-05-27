# =============================================================================
# LangChain Tools 定义
#
# 使用 @tool 装饰器定义，供各Agent节点调用
#
# Tools:
#   - vllm_vision_inference(image_url, prompt, max_tokens) -> str
#     调用vLLM进行图纸视觉推理
#     模型: qwen2.5-vl-7b-finetuned
#     参数: temperature=0.1
#
#   - ocr_extract_labels(image_url) -> dict
#     PaddleOCR提取标号文字和坐标
#     返回: {texts, boxes, scores}
#
#   - search_knowledge_base(query_text, top_k) -> list[dict]
#     Milvus向量检索企业知识库
#
#   - search_es_keywords(query, index, top_k) -> list[dict]
#     Elasticsearch BM25关键词检索
#
#   - query_knowledge_graph(label_name) -> dict
#     Neo4j图谱查询: Label → Part → Equipment → FaultRecord
#
#   - get_design_standards(drawing_type) -> list[dict]
#     获取设计标准文档
#
#   - plm_get_bom(doc_id, system) -> dict
#     从PLM获取BOM清单
#
#   - plm_writeback(doc_id, system, data) -> dict
#     向PLM回写解析结果 (含幂等Key + 重试)
#
#   - upload_to_minio(file_data, bucket, object_name) -> str
#     上传文件到MinIO，返回presigned URL
# =============================================================================
