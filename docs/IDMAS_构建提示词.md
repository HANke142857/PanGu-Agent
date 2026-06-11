# IDMAS 项目构建提示词（Build Prompt）

> 用途：把本文件整体（或分段）交给一个具备文件读写 + 终端执行能力的 AI 编码代理（如 Claude Code），即可从零复刻出 IDMAS（工业图纸智能解析多 Agent 协同系统）的完整工程骨架与可运行实现。
>
> 配套阅读：[`IDMAS_Requirements_v1.0.md`](IDMAS_Requirements_v1.0.md)（PRD）、[`IDMAS_TechDesign_v2.0.md`](IDMAS_TechDesign_v2.0.md)（技术设计）、[`IDMAS_MVP_开发任务清单.md`](IDMAS_MVP_开发任务清单.md)（任务分解）。本文件是「让 AI 动手建项目」的总指令；前三者是它要遵循的需求与设计依据。

---

## 0. 角色与总目标

你是一名资深 Python 后端 / AI 系统架构师。请基于本文件的需求、约束与分步计划，构建一个名为 **IDMAS（Industrial Drawing Multi-Agent System，工业图纸智能解析多 Agent 协同系统）** 的工程。

系统要解决的业务问题：把一张工业图纸（机械图为主，PDF/PNG）通过多模态大模型（VLM）+ OCR + 多智能体协同，自动解析为**结构化标号清单**（标号 ID、名称、置信度、空间位置、功能描述），对低置信度结果进入**人机协同审核**，最终生成**技术报告**并可**回写到 PLM 系统**（Teamcenter / ENOVIA / IntePLM）。

**最高优先的工程原则（贯穿全程，违反即返工）：**

> **每一个外部依赖（LLM、数据库、消息队列、向量库、对象存储、全文检索、图数据库、OCR、PLM）都必须按「抽象接口 + Fake/内存实现 + 真实实现」三件套来落地，并由 `settings` 里的后端开关切换。默认全部走 fake/memory，使得整套系统在没有 GPU、没有任何外部中间件的纯 Python 环境里也能完整跑通、且全部测试通过。**

这条原则保证了：开发可离线、测试无外部依赖、CI 快速、演示零门槛，而生产只需改环境变量切到真实后端。

---

## 1. 技术栈与版本约束

| 分类 | 选型 | 备注 |
|------|------|------|
| 语言 | Python 3.11+（开发机用 3.12 conda env） | `from __future__ import annotations` 全开 |
| Agent 编排 | LangGraph 0.3+ / LangChain-core 0.3+ | 每个 Agent 是一张有状态子图 |
| LLM 推理 | vLLM（Qwen2.5-VL-7B 微调），客户端封装 | 必须有 `FakeVLLMClient` |
| OCR | PaddleOCR 2.8+ | 必须有 `FakeOCRClient` |
| Web | FastAPI 0.115+ / Uvicorn | 应用工厂 `create_app()` |
| 关系库 | PostgreSQL 16 + SQLAlchemy 2.0 async + asyncpg | 测试用 aiosqlite |
| 缓存/状态 | Redis 7 | LangGraph checkpoint（可后置） |
| 消息队列 | RabbitMQ 3.13（aio-pika） | 默认 `eager` 就地处理 |
| 向量库 | Milvus 2.4+（pymilvus） | 知识库语义检索，**不要用 pgvector 替代** |
| 图数据库 | Neo4j 5.x | 知识图谱 |
| 全文检索 | Elasticsearch 8.15+ | 关键词检索 |
| 对象存储 | MinIO（minio-py） | 图纸文件落地 |
| 配置 | pydantic-settings 2.5 | 单例 `get_settings()` |
| 校验/DTO | pydantic 2.9 | API schema |
| 容器 | Docker Compose（多阶段、非 root、healthcheck） | 一键起全栈 |
| 测试 | pytest + pytest-asyncio（auto 模式） | 目标全绿 |
| 质量 | ruff（line-length 100）+ mypy（strict） | — |

依赖用 `pyproject.toml`（Poetry，按模块拆 extras：`web/db/http/llm/mq/vector/storage/graph/search/all`）+ 同步一份 `requirements.txt`（给 Docker 用）。可选依赖懒加载：只有切到真实后端时才 `import` 对应的重型库，fake 路径绝不触碰它们。

---

## 2. 目录结构（DDD 分层 + 六边形）

包根是仓库根目录，源码在 `idmas/` 子包下。运行需 `PYTHONPATH=<仓库根>`。请精确生成如下结构：

```
idmas/
├── config/
│   ├── settings.py              # pydantic-settings 单例 + 所有后端开关
│   └── prompts/                 # intent/vision/debate/report 提示词模板
├── domain/                      # 领域层：纯业务，零外部依赖
│   ├── drawing/                 # 限界上下文：图纸（entities/value_objects/repository 接口）
│   ├── analysis/                # 限界上下文：解析任务与结果
│   ├── knowledge/               # 限界上下文：知识
│   └── shared/                  # 共享值对象 + 领域异常（IDMASError 体系）
├── agents/                      # 应用层：LangGraph 子图
│   ├── master/                  # 主调度：intent → router → 子 Agent → report
│   ├── vision/                  # 视觉解析（核心）：预处理→prompt→VLM→解析→置信检查→OCR重试→汇总
│   ├── design/                  # 设计校核
│   ├── process/                 # 工艺分析
│   ├── knowledge/               # 知识检索（RAG 三路）
│   ├── report/                  # 报告生成
│   └── shared/                  # tools / retry / token_counter / callbacks
├── infrastructure/             # 基础设施层：每个子目录 = 一种外部依赖的三件套
│   ├── llm/                     # vllm_client.py：BaseLLMClient / FakeVLLMClient / VLLMClient + build_llm_client 工厂
│   ├── ocr/                     # base.py(BaseOCRClient/FakeOCRClient) + paddle_client.py
│   ├── db/                      # models/mappers/repositories(SQL)/memory_repositories/session
│   ├── cache/                   # redis_client.py（薄壳，可后置）
│   ├── mq/                      # base.py(BaseTaskQueue/EagerTaskQueue) + publisher.py(RabbitMQ) + consumer.py
│   ├── vectordb/                # base.py(BaseVectorClient/InMemoryVectorClient/Embedder) + milvus_client.py
│   ├── search/                  # base.py(BaseSearchClient/InMemorySearchClient) + es_client.py
│   ├── graphdb/                 # base.py(BaseGraphClient/InMemoryGraphClient) + neo4j_client.py
│   ├── storage/                 # base.py(BaseStorageClient/InMemoryStorageClient) + minio_client.py
│   ├── adapters/                # PLM：base.py(BasePLMAdapter/FakePLMAdapter) + teamcenter/enovia/inteplm
│   └── observability/           # langfuse_handler / metrics / tracing（薄壳）
├── services/                   # 用例编排：task_processor.py / plm_writeback.py
├── api/
│   ├── app.py                   # create_app() 应用工厂 + lifespan + 依赖注入
│   ├── routes/                  # health / drawings / tasks / knowledge / plm
│   ├── schemas/                 # pydantic 请求/响应 DTO
│   └── middleware/              # auth(JWT RS256) / rate_limit / error_handler(统一错误码)
├── deploy/
│   ├── docker/                  # Dockerfile.api / Dockerfile.worker / docker-compose.yml / README
│   ├── k8s/ helm/ ansible/      # 生产编排骨架
├── tests/
│   ├── unit/ integration/ e2e/  # 分层测试
│   ├── fixtures/ conftest.py    # 样例数据 + 公共 fixture
├── main.py                      # API 入口（uvicorn 启动 create_app()）
├── worker.py                    # 独立 Worker 入口（消费 RabbitMQ）
├── pyproject.toml  requirements.txt  .env.example
```

---

## 3. 配置与依赖注入约定（务必照此实现）

### 3.1 `config/settings.py`

- 用 `BaseSettings`，`env_file=".env"`，`extra="ignore"`，`case_sensitive=False`。
- 提供 `@lru_cache` 的 `get_settings()` 单例，并导出 `settings = get_settings()`。测试用 `get_settings.cache_clear()` 重置。
- **后端开关（核心）**——每个都默认 fake/memory：
  - `DB_BACKEND = memory | sql`
  - `MQ_BACKEND = eager | rabbitmq`
  - `LLM_BACKEND = fake | vllm`
  - `OCR_BACKEND = fake | paddle`
  - `STORAGE_BACKEND = memory | minio`
  - `VECTOR_BACKEND = memory | milvus`
  - `SEARCH_BACKEND = memory | es`
  - `GRAPH_BACKEND = memory | neo4j`
  - `PLM_BACKEND = fake | real`
- 各后端的连接参数（URL/host/port/credentials/bucket 等）、vLLM 推理参数（`VLLM_MAX_TOKENS=2048`、`VLLM_TEMPERATURE=0.1`、`VLLM_TIMEOUT`、`VLLM_MAX_CONCURRENT=8`）、JWT、可观测性端点。
- 业务阈值放配置、运行时可覆盖：`CONFIDENCE_HIGH_THRESHOLD=0.85`、`CONFIDENCE_LOW_THRESHOLD=0.60`、`IMAGE_MAX_DIMENSION=4096`。
- `APP_CORS_ORIGINS` 支持逗号分隔字符串（用 `field_validator(mode="before")` 解析）。
- 所有数值字段用 `Field(ge=..., le=...)` 加边界约束，缺失必填项时启动报清晰错误。
- 同步维护一份 `.env.example` 覆盖全部变量。

### 3.2 `api/app.py` 应用工厂

- `create_app(llm_client=None, drawing_repo=None, task_repo=None, task_queue=None, storage=None, plm_factory=None)`：所有外部依赖都可注入，`None` 时按 `settings` 自动组装。这是测试可替换的关键。
- 用 `lifespan`（asynccontextmanager）在启动时把依赖挂到 `app.state`：`llm_client / drawing_repo / task_repo / storage / plm_adapter_factory / task_queue`，关闭时清理（`task_queue.close()`、SQL 模式 `close_db()`）。
- 提供 `_build_task_queue / _build_storage / _build_plm_factory` 等私有工厂，依据后端开关选择实现；重型库在分支内部 `import`（懒加载）。
- `eager` 队列：`EagerTaskQueue(handler=TaskProcessor(...).handle)`，发布即就地处理，保持同步语义。`rabbitmq`：只发布，结果由 `worker.py` 异步回写。
- fake PLM：所有 system 共用同一个 `FakePLMAdapter` 实例（跨调用保留幂等记录）；real：按 system 名称缓存品牌适配器实例。
- 注册中间件（CORS、异常处理器：`IDMASError` → 统一错误码 JSON，`Exception` → 兜底）与路由（health/drawings/tasks/plm，knowledge 视进度）。

---

## 4. 分步构建计划（严格按此顺序，每步必须先写抽象+fake、跑通测试再进入下一步）

> 提交信息用**中文**，按步骤编号（例：「实现 OCR 抽象（第8步）：…」）。每步结束跑全套 `pytest` 必须全绿。

### 第 1 步 · 领域层
四个限界上下文 `drawing / analysis / knowledge / shared`，每个含实体（entities）、值对象（value_objects）、仓储接口（repository，抽象基类/Protocol）。`shared/exceptions.py` 定义 `IDMASError` 体系（带错误码，供统一异常处理器映射）。领域层零外部依赖、可独立单测。

### 第 2 步 · Agents 骨架 + LLM 客户端
- `infrastructure/llm/vllm_client.py`：`BaseLLMClient`（抽象 `generate(image, prompt, ...)`）、`FakeVLLMClient`（返回确定性结构化文本，供测试断言）、`VLLMClient`（真实 HTTP 调用，含超时/重试/并发限制），以及 `build_llm_client(settings)` 工厂按 `LLM_BACKEND` 选择。
- 六个 Agent 子图：`master / vision / design / process / knowledge / report`，每个含 `state.py`（TypedDict/Pydantic 状态，可序列化）、`nodes.py`（节点函数）、`graph.py`（`StateGraph` 组装、连边、条件路由）。`agents/shared/` 落地 `tools / retry / token_counter / callbacks`。
- Vision 子图是核心，节点链：`preprocess_image → build_prompt → vllm_inference → parse_output → confidence_check →（低置信）ocr_retry → finalize`。`parse_output` 要容错脏 JSON 不崩溃；`confidence_check` 按 `CONFIDENCE_LOW_THRESHOLD` 标记低置信标号。

### 第 3 步 · 持久化
`infrastructure/db/`：`models.py`（SQLAlchemy ORM）、`mappers.py`（ORM↔领域实体）、`repositories.py`（SQL 仓储，实现领域仓储接口）、`memory_repositories.py`（进程内仓储）、`session.py`（async engine/session、`init_db/close_db`）。`DB_BACKEND` 切换 memory/sql，默认 memory；SQL 路径仅在选用时才触碰数据库依赖。测试用 aiosqlite 覆盖 SQL 仓储读写。

### 第 4 步 · 消息队列 + Worker
`infrastructure/mq/`：`BaseTaskQueue`、`EagerTaskQueue`（就地同步处理）、`RabbitMQTaskQueue`（aio-pika 发布）。`services/task_processor.py` 封装「取图纸→跑 Agent→落结果」的用例。`worker.py` 独立进程消费 RabbitMQ。`MQ_BACKEND` 切换，默认 eager（发布即处理，保持单机/测试同步语义）。

### 第 5 步 · 向量库 / 知识检索
`infrastructure/vectordb/`：`BaseVectorClient`、`InMemoryVectorClient`（带预置 KB）、`MilvusVectorClient`；`BaseEmbedder` + `HashingEmbedder`（无需模型的确定性嵌入，供 fake）。knowledge agent 的 `vector_search` 改为注入式（工厂模式）。`VECTOR_BACKEND` 切换，默认 memory。**保留 Milvus 做知识库，不用 pgvector 替代。**

### 第 6 步 · 对象存储
`infrastructure/storage/`：`BaseStorageClient`、`InMemoryStorageClient`、`MinioStorageClient`（含 `ensure_bucket`）。上传路由真正写入存储，`file_url` 由存储返回，metadata 存 `object_name/sha256`；新增 `GET /api/v1/drawings/{id}/file` 下载端点。`STORAGE_BACKEND` 切换，默认 memory。

### 第 7 步 · RAG 三路检索
`infrastructure/search/`（`BaseSearchClient/InMemorySearchClient/ESSearchClient`）+ `infrastructure/graphdb/`（`BaseGraphClient/InMemoryGraphClient/Neo4jGraphClient`）。knowledge agent 的 `keyword_search/graph_query` 改注入式工厂；`merge_context` 把**向量 + 关键词 + 图谱**三路结果融合去重。`SEARCH_BACKEND/GRAPH_BACKEND` 切换，默认 memory（内存实现预置 KB + 图谱种子）。

### 第 8 步 · OCR
`infrastructure/ocr/`：`BaseOCRClient`、`FakeOCRClient`（确定性文字+坐标框）、`PaddleOCRClient`（`_normalize` 兼容多种响应形态）。vision 的 `ocr_retry` 节点统一走注入的 `ocr_client`，`build_vision_graph` 按 `OCR_BACKEND` 选择，默认 fake。低置信场景融合 OCR 坐标补充 prompt 后重试。

### 第 9 步 · PLM 适配器 + 回写链路
`infrastructure/adapters/`：`BasePLMAdapter`（**幂等回写模板** + HMAC Webhook 校验）、`HTTPPLMAdapter`、`FakePLMAdapter`，以及三品牌子类 `teamcenter / enovia / inteplm`。`services/plm_writeback.py` 编排回写；`api/routes/plm.py` 暴露 `POST /api/v1/plm/writeback` 与 `/webhook`。`PLM_BACKEND` 切换；`app.state.plm_adapter_factory` 注入（fake 模式共享实例以保留幂等/记录）。

### 第 10 步 · Docker 部署编排
`requirements.txt` + `deploy/docker/Dockerfile.api|worker`（多阶段、非 root、健康检查）+ `docker-compose.yml`（postgres / redis / rabbitmq / minio / es / neo4j + api + worker，全部 healthcheck；Milvus 复用宿主机 standalone，经 `host.docker.internal:19530` 连接）+ 部署 README。确保 `LLM_BACKEND=fake` 时全栈无需 GPU 即可跑通。

---

## 5. 跨切面约定（每步都要遵守）

1. **三件套模式**：抽象基类（定义契约）→ Fake/内存实现（确定性、零依赖、供测试）→ 真实实现（连外部）。工厂函数按 settings 选择。
2. **可注入依赖**：凡是外部依赖，都通过构造参数 / `create_app` 参数 / `app.state` 注入，绝不在业务逻辑里硬 `import` 真实客户端。
3. **懒加载重型库**：`pymilvus/neo4j/elasticsearch/minio/aio-pika/asyncpg/paddle` 等只在真实分支内部 import。
4. **默认全 fake/memory**：克隆仓库 → 装基础依赖 → 直接 `pytest` 全绿，无需任何中间件。
5. **异步优先**：IO 路径全 `async`；pytest-asyncio 用 auto 模式。
6. **错误码统一**：领域异常继承 `IDMASError`，由 `error_handler` 中间件映射成统一 JSON 结构。
7. **类型与质量**：开 `from __future__ import annotations`；过 ruff（select E,F,I,UP,B,C4,SIM）与 mypy strict。
8. **测试分层**：`unit`（领域/客户端/schema）、`integration`（API/DB/队列/RAG/存储/PLM）、`e2e`（上传→解析→结果全链路）；fixtures 提供样例图纸数据。

---

## 6. 验收标准（Definition of Done）

- 纯 Python 环境（无 GPU、无任何中间件）下 `pytest` 全部通过（参考基线：约 220+ 用例全绿）。
- `python -c "import idmas"` 无报错；`uvicorn` 起 `create_app()`，`GET /api/v1/health` 返回 200。
- 九个后端开关每个都能在 fake/memory 与 real 间切换，且 fake 路径不触碰真实库。
- 端到端：上传图纸 → 建任务 → Vision 解析 → 低置信标记 →（可）审核 → 报告 →（可）PLM 回写，链路贯通。
- `docker compose up` 一键拉起全栈，各服务 healthcheck 通过，`LLM_BACKEND=fake` 时无需 GPU。
- 业务目标对齐 PRD Phase 1：`ft_strict > 0.40`、单图端到端 < 30s、调度成功率 > 95%。

---

## 7. 给执行代理的工作方式提示

- **先读三份配套文档**（PRD / 技术设计 v2 / 任务清单）再动手，本文件第 4 节的步骤顺序与任务清单的 WS0–WS7 对应。
- 一次只推进一步：写抽象 → 写 fake → 写真实 → 写测试 → 跑全套 → 提交（中文、带步骤号）。不要跳步、不要一次性铺开所有真实集成。
- 遇到外部依赖先问自己：「fake 版长什么样？测试怎么不依赖它？」——先把这条路打通。
- 标记薄壳：Redis 缓存接 checkpointer、可观测性（langfuse/metrics/tracing）、k8s/helm 编排可先留骨架并在代码里注明「待填」，不阻塞主链路。
- 完成后在 `docs/README.md` 与本文件同步实际进度。
```python

> 备注：以上分步顺序、后端开关命名、三件套模式，是本项目已验证可行的构建路径——按它走，能得到一个「离线可测、生产可切」的工业级多 Agent 系统骨架。

```

