# IDMAS MVP 开发任务清单（骨架 → 可用）

> 范围：PRD Phase 1（F-001 ~ F-005），目标 `ft_strict > 0.40`、单图端到端 < 30s、调度成功率 > 95%
> 周期参考：0–2 个月　|　工时为单人理想工时（人·天）粗估，需按团队规模折算
> 当前状态：117 个 `.py` 文件均为 docstring 骨架，无实现逻辑；文档（PRD/技术设计 v2）已就绪

---

## 总览

| 工作流 | 对应功能 | 优先级 | 粗估工时 |
|--------|---------|--------|---------|
| WS0 工程基建 | — | P0（前置） | ~6 人天 |
| WS1 基础设施层 | infrastructure/ | P0 | ~12 人天 |
| WS2 Vision Agent | F-001 | P0 | ~20 人天 |
| WS3 Master 调度 | F-002 | P0 | ~8 人天 |
| WS4 Report Agent | F-003 | P0 | ~5 人天 |
| WS5 API + Web 单图链路 | F-004 | P0 | ~14 人天 |
| WS6 人机协同审核台 | F-005 | P0 | ~10 人天 |
| WS7 评估与验收 | KR 验证 | P0 | ~7 人天 |

**关键路径**：WS0 → WS1 → WS2 → WS3 → WS5；WS4/WS6 依赖 WS2，WS7 贯穿全程。
**先打通最小链路**：上传 → Vision 推理 → JSON 输出 → 报告，再补审核台与评估。

---

## WS0 · 工程基建（前置，约 6 人天）

- [ ] **T0.1 依赖与项目初始化**：补齐 `pyproject.toml`/`requirements.txt`（LangGraph 0.3、FastAPI 0.115、vLLM client、PaddleOCR、SQLAlchemy、redis、pydantic-settings）；填空的 `docs/README.md`。_验收：`pip install` 一键成功，`python -c "import idmas"` 无报错。_（1d）
- [ ] **T0.2 配置体系落地**：实现 `config/settings.py`（pydantic-settings 读取 `.env`），打通 `.env.example` 全量变量。_验收：缺失必填项时启动报清晰错误。_（1d）
- [ ] **T0.3 本地依赖编排**：完善 `deploy/docker/docker-compose.yml`，拉起 PostgreSQL 16 + Redis 7 + MinIO（MVP 最小集，Milvus/Neo4j/ES 留到 Phase 2）。_验收：`docker compose up` 后各服务健康检查通过。_（1.5d）
- [ ] **T0.4 日志与错误骨架**：实现 `api/middleware/error_handler.py` 统一错误码（对齐技术设计 2.3 错误码规范）、结构化日志。_验收：异常返回统一 JSON 结构。_（1d）
- [ ] **T0.5 CI 流水线**：GitHub Actions 跑 lint（ruff）+ 单测 + 构建。_验收：PR 触发 CI 且通过。_（1.5d）

## WS1 · 基础设施层（约 12 人天，依赖 WS0）

- [ ] **T1.1 PostgreSQL 数据模型**：实现 `infrastructure/db/models.py` + 首个 Alembic migration（对齐技术设计 3.2 DDL：任务表、图纸表、标号结果表、审核记录表）。_验收：migration 可升级/回滚。_（2d）
- [ ] **T1.2 对象存储封装**：`infrastructure/storage/` 接 MinIO，支持图纸上传/取回、预签名 URL。_验收：上传 PDF/PNG 并能回读。_（1.5d）
- [ ] **T1.3 Redis 客户端 + 状态存储**：完善 `infrastructure/cache/redis_client.py`，承载 LangGraph checkpoint / 任务状态。_验收：可读写、TTL 生效。_（1.5d）
- [ ] **T1.4 vLLM 推理客户端**：实现 `infrastructure/llm/vllm_client.py`，封装 Qwen2.5-VL 多模态请求（image+prompt，max_tokens=2048,temperature=0.1）、超时与重试。_验收：对接 mock/真实 vLLM 返回结构化文本。_（2d）
- [ ] **T1.5 OCR 适配器**：`infrastructure/ocr/` 封装 PaddleOCR，返回文字+坐标框。_验收：给定图返回坐标列表。_（1.5d）
- [ ] **T1.6 仓储层实现**：`domain/*/repository.py` 落地（任务、图纸、分析结果的 CRUD）。_验收：单测覆盖主要读写路径。_（2d）
- [ ] **T1.7 vLLM 部署/接入**：MVP 期可先用云端 API 或单卡部署微调模型，明确 image_max_pixels 等参数。_验收：服务可用、延迟达标。_（1.5d）

## WS2 · Vision Agent（F-001，约 20 人天，核心，依赖 WS1）

- [ ] **T2.1 VisionState 定义**：实现 `agents/vision/state.py`（image、prompt_mode、labels、confidence、ocr_hint 等字段）。_验收：状态可序列化。_（1d）
- [ ] **T2.2 图像预处理节点** `preprocess_image_node`：尺寸检查、格式转换、按 image_max_pixels 缩放、纠偏。_验收：超大/异常图被正确归一化。_（2d）
- [ ] **T2.3 Prompt 构建节点** `build_prompt_node`：Jinja2 模板（standard / cot_visual / few_shot），接 `config/prompts/vision_prompts.py`。_验收：三种模式产出正确 prompt。_（2d）
- [ ] **T2.4 VLM 推理节点** `vllm_inference_node`：调用 T1.4 客户端。_验收：返回原始推理文本。_（1.5d）
- [ ] **T2.5 输出解析节点** `parse_output_node`：解析为结构化标号列表（label_id/name/confidence/spatial_info），容错非法 JSON。_验收：脏输出不致崩溃，解析率达标。_（3d）
- [ ] **T2.6 置信度检查节点** `confidence_check_node`：阈值 0.60 标记低置信标号。_验收：低于阈值正确标记。_（1d）
- [ ] **T2.7 OCR 重试节点** `ocr_retry_node`：融合 OCR 坐标补充 prompt 后重试。_验收：低置信场景触发重试且结果改善。_（3d）
- [ ] **T2.8 汇总节点** `finalize_node` + 可视化 overlay（在原图高亮标号）。_验收：输出最终 JSON + overlay 图。_（2.5d）
- [ ] **T2.9 Vision SubGraph 组装** `agents/vision/graph.py`：连边、条件路由、checkpoint。_验收：端到端跑通单图，输出标号 JSON。_（2d）
- [ ] **T2.10 Vision 单元/集成测试**：`tests/unit` + `tests/integration` 覆盖各节点与子图。_验收：覆盖率 > 70%。_（2d）

## WS3 · Master Scheduler（F-002，约 8 人天，依赖 WS2）

- [ ] **T3.1 全局状态** `agents/master/state.py`：任务类型、子 Agent 结果聚合槽位。_验收：状态完整可序列化。_（1d）
- [ ] **T3.2 意图识别/路由** `agents/master/routes.py` + `intent_prompts.py`：MVP 仅需识别"单图深度解析"。_验收：正确路由到 Vision。_（1.5d）
- [ ] **T3.3 调度节点** `agents/master/nodes.py`：调用 Vision 子图、结果聚合、错误兜底（无死锁/崩溃）。_验收：异常子图不拖垮主流程。_（2d）
- [ ] **T3.4 Master Graph 组装** `agents/master/graph.py`：MVP 串行（Vision → Report）。_验收：上传到报告全链路贯通。_（2d）
- [ ] **T3.5 共享工具/重试/Token 计数**：`agents/shared/`（tools、retry、token_counter、callbacks）落地。_验收：重试与计数可观测。_（1.5d）

## WS4 · Report Agent（F-003，约 5 人天，依赖 WS2）

- [ ] **T4.1 ReportState + 节点**：`agents/report/`，将 Vision 结构化结果汇总为技术报告。_验收：输入标号 JSON 产出报告草稿。_（2d）
- [ ] **T4.2 报告模板**：接 `config/prompts/report_prompts.py`，输出 Markdown/JSON 双格式。_验收：报告含标号清单、空间/功能描述、置信度。_（2d）
- [ ] **T4.3 Report 测试**。_验收：核心路径单测通过。_（1d）

## WS5 · API + Web 单图链路（F-004，约 14 人天，依赖 WS3）

- [ ] **T5.1 FastAPI 应用骨架** `api/app.py`：路由注册、CORS、lifespan。_验收：`/health` 返回 200。_（1d）
- [ ] **T5.2 认证与限流中间件**：`auth.py`（JWT/RS256）+ `rate_limit.py`。MVP 可简化为单一服务令牌。_验收：未授权请求被拦截。_（2d）
- [ ] **T5.3 图纸上传接口** `routes/drawings.py` + `schemas/drawing.py`：接收 PDF/PNG，存 MinIO，建任务。_验收：返回 task_id。_（2d）
- [ ] **T5.4 任务接口** `routes/tasks.py`：触发解析、查询状态、SSE 进度推送。_验收：可查询 pending→done 状态流转。_（2.5d）
- [ ] **T5.5 结果接口**：返回标号 JSON + overlay URL + 报告。_验收：结构对齐 schema。_（1.5d）
- [ ] **T5.6 前端：上传页**（React 19 + TS + Tailwind）：拖拽上传、进度条。_验收：可上传并显示进度。_（2d）
- [ ] **T5.7 前端：结果展示页**：原图 + overlay 高亮、标号列表、报告查看。_验收：标号与图像联动高亮。_（3d）

## WS6 · 人机协同审核工作台（F-005，约 10 人天，依赖 WS2/WS5）

- [ ] **T6.1 审核数据模型与接口**：低置信标号列表、修正提交、裁决记录入库。_验收：修正可持久化。_（2d）
- [ ] **T6.2 审核 UI**：低置信标号高亮、逐项确认/修正、图像证据查看。_验收：工程师可逐项裁决并保存。_（4d）
- [ ] **T6.3 结论入库 + 数据回流**：确认结果落库，导出为可用于再训练的数据格式。_验收：人工复核率可统计（目标 < 15%）。_（2d）
- [ ] **T6.4 审核链路测试**。_验收：上传→识别→审核→入库 E2E 通过。_（2d）

## WS7 · 评估与验收（KR 验证，约 7 人天，贯穿全程）

- [ ] **T7.1 评估脚本** `eval_dual_track.py`：实现 ft_strict（term_f1）、spatial_score、functional_score 指标。_验收：给定标注集输出各指标。_（2.5d）
- [ ] **T7.2 标注测试集**：构建 MVP 基准图纸集（含金标准标号）。_验收：≥ N 张覆盖典型场景。_（2d）
- [ ] **T7.3 端到端性能基准**：测单图全链路耗时。_验收：P95 < 30s（KR2）。_（1d）
- [ ] **T7.4 E2E 测试套件** `tests/e2e`：覆盖标准解析流程。_验收：调度成功率 > 95%（KR3）。_（1.5d）
- [ ] **T7.5 MVP 验收门禁**：`ft_strict > 0.40`（Phase 1 目标）、链路稳定、审核台可用。_验收：达标即 MVP 完成。_

---

## MVP 范围外（不在本清单，留待后续）

Knowledge Agent / Agentic RAG（F-007，需 Milvus+Neo4j+ES）、Design/Process Agent（F-006/F-013）、多轮对话追问（F-008）、跨图关联（F-009）、对抗辩论纠错、PLM/MES/CAD 对接（F-010/F-011）、批量队列（F-012）。MVP 阶段仅支持机械工业图纸，不做建筑/PCB/地图。

## 建议执行顺序

1. **第 1–2 周**：WS0 + WS1（基建 + 基础设施跑通）
2. **第 3–5 周**：WS2（Vision Agent，核心攻坚）+ WS7 评估脚本并行起步
3. **第 6–7 周**：WS3 + WS4（调度 + 报告，打通后端最小链路）
4. **第 8 周**：WS5（API + Web 上传/结果页）→ 首个可演示 Demo
5. **第 9–10 周**：WS6（审核台）+ WS7 收尾，跑 MVP 验收门禁
