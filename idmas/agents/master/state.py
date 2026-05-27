# =============================================================================
# Master Graph 全局状态定义 (IDMASState)
#
# 使用 TypedDict + Annotated 定义 LangGraph 状态
#
# 状态字段:
#   输入:
#     - request_id: str              # 请求唯一ID
#     - user_id: str                 # 用户ID
#     - user_query: str              # 用户提问
#     - image_url: str               # 图纸MinIO地址
#     - background_text: str | None  # 背景信息
#     - prompt_mode: str             # Prompt模式
#
#   意图:
#     - intent: str                  # 识别的意图
#     - required_agents: list[str]   # 需要调用的Agent列表
#     - task_dag: dict               # 任务DAG
#
#   Agent输出:
#     - vision_result: dict | None   # Vision Agent结果
#     - ocr_result: dict | None      # OCR提取结果
#     - design_result: dict | None   # Design Agent结果
#     - process_result: dict | None  # Process Agent结果
#     - knowledge_result: dict | None # Knowledge Agent结果
#     - report_result: dict | None   # Report Agent结果
#
#   冲突与审核:
#     - conflicts: list[dict]        # 检测到的冲突列表
#     - debate_rounds: list[dict]    # 对抗辩论轮次
#     - human_review_needed: bool    # 是否需要人工审核
#     - human_decision: dict | None  # 人工审核决策
#
#   元数据:
#     - status: str                  # 当前状态
#     - error: str | None            # 错误信息
#     - total_tokens: int            # 累计Token消耗
#     - messages: Annotated[list, add]  # 消息列表(追加模式)
# =============================================================================
