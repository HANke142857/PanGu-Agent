# =============================================================================
# 知识库领域实体
#
# 包含:
#   - KnowledgeDocument: 知识文档实体
#     - id: UUID
#     - title: 文档标题
#     - content: 文档内容
#     - doc_type: 文档类型 (standard/manual/spec/faq)
#     - tags: 标签列表
#     - source: 来源
#     - embedding_id: 向量库ID
#
#   - Part: 部件实体 (图谱节点)
#     - id: UUID
#     - name: 部件名称
#     - material: 材质
#     - spec: 规格
#
#   - Equipment: 设备实体 (图谱节点)
#     - id: UUID
#     - name: 设备名称
#     - model: 设备型号
#
#   - FaultRecord: 故障记录实体 (图谱节点)
#     - id: UUID
#     - code: 故障代码
#     - description: 故障描述
# =============================================================================
