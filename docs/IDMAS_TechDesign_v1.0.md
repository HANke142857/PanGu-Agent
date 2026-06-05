# 工业图纸智能解析多Agent协同系统 (IDMAS)
# 技术设计文档

---

| 项目 | 内容 |
|------|------|
| **文档版本** | v1.0 |
| **产品代号** | IDMAS |
| **核心框架** | LangChain + LangGraph |
| **创建日期** | 2026-05-27 |
| **文档状态** | 草稿 |

---

## 一、架构设计

### 1.1 技术架构选型

| 维度 | 选型 | 理由 |
|------|------|------|
| **架构模式** | 微服务 + Agent 编排 | Agent 独立部署、独立扩展、独立升级 |
| **Agent 框架** | LangChain + LangGraph | 成熟的 Agent 编排框架，原生支持有状态图、条件路由、人机协同 |
| **技术栈语言** | Python 3.11+ | LangChain/LangGraph 原生语言，VLM 生态最完善 |
| **Web 框架** | FastAPI | 异步高性能，与 LangChain 无缝集成 |
| **前端** | React + TypeScript + TailwindCSS | 现代 SPA，SSE 流式展示 |
| **部署方式** | Docker Compose（MVP）→ K8s（生产） | 渐进式容器化 |
| **团队能力匹配** | Python 全栈 | LangChain 生态成熟，学习曲线平缓 |

### 1.2 为什么选 LangGraph 而非 AutoGen/CrewAI

| 对比维度 | LangGraph | AutoGen | CrewAI |
|---------|-----------|---------|--------|
| **状态管理** | ✅ 原生有状态图，State 持久化 | ⚠️ 对话级状态，需自建持久化 | ⚠️ 简单状态 |
| **流程控制** | ✅ 条件分支、循环、子图、中断恢复 | ⚠️ Group Chat 模式，灵活度低 | ⚠️ 线性流程为主 |
| **人机协同** | ✅ `interrupt_before` / `interrupt_after` 原生支持 | ❌ 需自行实现 | ❌ 需自行实现 |
| **流式输出** | ✅ `astream_events` 原生支持 | ⚠️ 有限支持 | ⚠️ 有限支持 |
| **持久化** | ✅ Checkpointer（Redis/PostgreSQL） | ❌ 无内置 | ❌ 无内置 |
| **可观测性** | ✅ LangSmith 全链路追踪 | ⚠️ 自建 | ⚠️ 自建 |
| **生产就绪** | ✅ LangGraph Platform 可选 | ⚠️ 社区驱动 | ⚠️ 社区驱动 |

### 1.3 整体架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                      用户交互层                                    │
│         React Web / CAD 插件 / 企业微信 / PLM Webhook             │
└──────────────────────────────────────────────────────────────────┘
                                ↓  REST + SSE
┌──────────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                          │
│          认证(JWT) · 限流 · 请求路由 · SSE 推送                    │
└──────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│              LangGraph 编排引擎 (Master Graph)                    │
│                                                                  │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│   │ Intent   │───→│ Task DAG │───→│ Router   │                  │
│   │ Node     │    │ Builder  │    │ Node     │                  │
│   └──────────┘    └──────────┘    └──────────┘                  │
│        │               │               │                         │
│        ↓               ↓               ↓                         │
│   ┌─────────────────────────────────────────────┐               │
│   │           Agent SubGraphs                    │               │
│   │                                              │               │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │               │
│   │  │ Vision  │ │ Design  │ │ Process │       │               │
│   │  │SubGraph │ │SubGraph │ │SubGraph │       │               │
│   │  └─────────┘ └─────────┘ └─────────┘       │               │
│   │  ┌─────────┐ ┌─────────┐                    │               │
│   │  │Knowledge│ │ Report  │                    │               │
│   │  │SubGraph │ │SubGraph │                    │               │
│   │  └─────────┘ └─────────┘                    │               │
│   └─────────────────────────────────────────────┘               │
│        │                                                         │
│        ↓                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│   │ Conflict │───→│ Human    │───→│ Result   │                  │
│   │ Detector │    │ Review   │    │Aggregator│                  │
│   └──────────┘    └──────────┘    └──────────┘                  │
│                                                                  │
│   State: Redis Checkpointer  │  Trace: LangSmith                │
└──────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                       工具与数据层                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │  vLLM     │ │ PaddleOCR │ │  Milvus   │ │   Neo4j   │       │
│  │(VLM推理)  │ │(标号OCR)  │ │(向量检索)  │ │(知识图谱)  │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                     │
│  │  Redis    │ │  MinIO    │ │  PostgreSQL│                     │
│  │(缓存/状态) │ │(对象存储)  │ │(业务数据)  │                     │
│  └───────────┘ └───────────┘ └───────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

### 1.4 LangGraph Master Graph 核心设计

```python
# idmas/graphs/master_graph.py
from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import RedisSaver

# ==================== 全局状态定义 ====================
class IDMASState(TypedDict):
    """Master Graph 全局状态"""
    # 用户输入
    user_query: str
    image_url: str
    image_base64: str | None
    background_text: str | None
    figure_description: str | None

    # 意图识别结果
    intent: str  # single_parse | batch_parse | design_review | ...
    required_agents: list[str]
    task_dag: dict

    # Agent 输出（逐步填充）
    vision_result: dict | None
    ocr_result: dict | None
    design_result: dict | None
    process_result: dict | None
    knowledge_result: dict | None
    report_result: dict | None

    # 冲突与审核
    conflicts: list[dict]
    human_review_needed: bool
    human_decision: dict | None

    # 元数据
    request_id: str
    status: str  # processing | waiting_human | completed | failed
    messages: Annotated[list, "append"]  # 累积消息


# ==================== Master Graph 构建 ====================
def build_master_graph():
    graph = StateGraph(IDMASState)

    # 添加节点
    graph.add_node("intent_recognition", intent_recognition_node)
    graph.add_node("vision_agent", vision_agent_subgraph)
    graph.add_node("ocr_extraction", ocr_extraction_node)
    graph.add_node("design_agent", design_agent_subgraph)
    graph.add_node("process_agent", process_agent_subgraph)
    graph.add_node("knowledge_agent", knowledge_agent_subgraph)
    graph.add_node("conflict_detection", conflict_detection_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("report_agent", report_agent_subgraph)
    graph.add_node("result_aggregation", result_aggregation_node)

    # 入口 → 意图识别
    graph.set_entry_point("intent_recognition")

    # 意图识别 → 并行调度（Vision + OCR + Knowledge）
    graph.add_conditional_edges(
        "intent_recognition",
        route_by_intent,
        {
            "single_parse": "vision_agent",
            "design_review": "vision_agent",
            "process_planning": "vision_agent",
            "knowledge_query": "knowledge_agent",
            "batch_parse": "vision_agent",
        }
    )

    # Vision → OCR（并行辅助）
    graph.add_edge("vision_agent", "ocr_extraction")

    # OCR → 条件路由（根据意图决定下一步）
    graph.add_conditional_edges(
        "ocr_extraction",
        route_after_vision,
        {
            "design": "design_agent",
            "process": "process_agent",
            "knowledge": "knowledge_agent",
            "direct_report": "conflict_detection",
        }
    )

    # Design / Process / Knowledge → 冲突检测
    graph.add_edge("design_agent", "conflict_detection")
    graph.add_edge("process_agent", "conflict_detection")
    graph.add_edge("knowledge_agent", "conflict_detection")

    # 冲突检测 → 条件：有冲突转人工，无冲突直接出报告
    graph.add_conditional_edges(
        "conflict_detection",
        check_conflicts,
        {
            "has_conflict": "human_review",
            "no_conflict": "report_agent",
        }
    )

    # 人工审核（LangGraph interrupt）→ 报告生成
    graph.add_edge("human_review", "report_agent")

    # 报告 → 结果聚合 → END
    graph.add_edge("report_agent", "result_aggregation")
    graph.add_edge("result_aggregation", END)

    # 编译，使用 Redis 做状态持久化
    checkpointer = RedisSaver(redis_url="redis://localhost:6379/0")
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],  # 人工审核前中断
    )
```

### 1.5 Agent SubGraph 设计（以 Vision Agent 为例）

```python
# idmas/graphs/vision_subgraph.py
from langgraph.graph import StateGraph, END

class VisionState(TypedDict):
    """Vision Agent 内部状态"""
    image_url: str
    prompt_mode: str
    preprocessed_image: str | None
    cot_steps: list[dict]
    labels: dict | None
    spatial_info: dict | None
    confidence_scores: dict | None
    needs_retry: bool


def build_vision_subgraph():
    graph = StateGraph(VisionState)

    graph.add_node("preprocess", preprocess_image_node)
    graph.add_node("vllm_inference", vllm_inference_node)
    graph.add_node("parse_output", parse_structured_output_node)
    graph.add_node("confidence_check", confidence_check_node)
    graph.add_node("retry_with_ocr", retry_with_ocr_assistance_node)

    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "vllm_inference")
    graph.add_edge("vllm_inference", "parse_output")
    graph.add_edge("parse_output", "confidence_check")

    # 低置信度 → 用OCR辅助重试一次
    graph.add_conditional_edges(
        "confidence_check",
        lambda s: "retry" if s["needs_retry"] else "done",
        {"retry": "retry_with_ocr", "done": END}
    )
    graph.add_edge("retry_with_ocr", END)

    return graph.compile()
```

---

## 二、模块划分

### 2.1 DDD 领域划分

```
idmas/
├── domain/                          # 领域层（纯业务逻辑）
│   ├── drawing/                     # 图纸聚合根
│   │   ├── models.py                # DrawingDocument, DrawingLabel, BOMItem
│   │   ├── services.py              # 图纸预处理、格式转换
│   │   └── repository.py            # 图纸持久化接口
│   ├── analysis/                    # 解析任务聚合根
│   │   ├── models.py                # AnalysisTask, TaskStatus, Conflict
│   │   ├── services.py              # 任务创建、状态流转
│   │   └── repository.py            # 任务持久化接口
│   └── knowledge/                   # 知识库聚合根
│       ├── models.py                # KnowledgeEntry, SearchResult
│       └── services.py              # 知识检索、入库
│
├── agents/                          # Agent 层（LangChain/LangGraph）
│   ├── vision/
│   │   ├── agent.py                 # Vision Agent 定义
│   │   ├── tools.py                 # vLLM调用、OCR调用 等 LangChain Tools
│   │   ├── prompts.py               # 6种防捷径Prompt模板
│   │   └── subgraph.py              # Vision SubGraph
│   ├── design/
│   │   ├── agent.py
│   │   ├── tools.py                 # 规范库查询、历史比对
│   │   └── subgraph.py
│   ├── process/
│   │   ├── agent.py
│   │   ├── tools.py                 # 工艺知识库、材料库查询
│   │   └── subgraph.py
│   ├── knowledge/
│   │   ├── agent.py
│   │   ├── tools.py                 # Milvus检索、Neo4j查询
│   │   ├── rag_chain.py             # Agentic RAG 链
│   │   └── subgraph.py
│   ├── report/
│   │   ├── agent.py
│   │   ├── tools.py                 # 模板渲染、图表生成
│   │   └── subgraph.py
│   └── master/
│       ├── graph.py                 # Master LangGraph（主编排图）
│       ├── intent.py                # 意图识别节点
│       ├── router.py                # 条件路由逻辑
│       ├── conflict.py              # 冲突检测与对抗辩论
│       └── state.py                 # IDMASState 定义
│
├── infrastructure/                  # 基础设施层
│   ├── llm/
│   │   ├── vllm_client.py           # vLLM 推理客户端
│   │   └── openai_client.py         # OpenAI兼容API客户端
│   ├── ocr/
│   │   └── paddle_ocr.py            # PaddleOCR 封装
│   ├── vectordb/
│   │   └── milvus_client.py         # Milvus 向量检索
│   ├── graphdb/
│   │   └── neo4j_client.py          # Neo4j 知识图谱
│   ├── storage/
│   │   └── minio_client.py          # MinIO 对象存储
│   ├── cache/
│   │   └── redis_client.py          # Redis 缓存与状态
│   ├── adapters/                    # PLM/MES/CAD 适配器
│   │   ├── base.py                  # 适配器抽象基类
│   │   ├── teamcenter.py
│   │   ├── enovia.py
│   │   └── inteplm.py
│   └── db/
│       ├── postgres.py              # PostgreSQL 连接
│       └── migrations/              # Alembic 迁移
│
├── api/                             # API 层（FastAPI）
│   ├── main.py                      # FastAPI 应用入口
│   ├── routes/
│   │   ├── tasks.py                 # POST /tasks（创建解析任务）
│   │   ├── drawings.py              # 图纸 CRUD
│   │   ├── knowledge.py             # 知识库查询
│   │   ├── stream.py                # SSE 流式推送
│   │   └── health.py                # 健康检查 & 指标
│   ├── middleware/
│   │   ├── auth.py                  # JWT 认证
│   │   ├── rate_limit.py            # 限流
│   │   └── logging.py               # 请求日志
│   └── schemas/
│       ├── task.py                  # Pydantic 请求/响应模型
│       └── drawing.py
│
├── config/
│   ├── settings.py                  # Pydantic Settings（环境变量）
│   └── prompts/                     # Prompt 模板文件
│       ├── vision_standard.jinja2
│       ├── vision_pure.jinja2
│       ├── vision_adversarial.jinja2
│       └── ...
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

### 2.2 API 契约

#### 核心接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/tasks` | 创建解析任务（入口） | JWT |
| GET  | `/api/v1/tasks/{id}` | 查询任务状态与结果 | JWT |
| GET  | `/api/v1/tasks/{id}/stream` | SSE 流式获取推理进度 | JWT |
| POST | `/api/v1/tasks/{id}/review` | 提交人工审核结果 | JWT |
| POST | `/api/v1/tasks/batch` | 批量创建任务 | JWT |
| GET  | `/api/v1/drawings/{id}` | 获取图纸详情 | JWT |
| POST | `/api/v1/knowledge/search` | 知识库检索 | JWT |
| GET  | `/api/v1/health` | 健康检查 | 无 |
| GET  | `/api/v1/metrics` | Prometheus 指标 | 内网 |

#### 创建任务请求 / 响应示例

```python
# POST /api/v1/tasks
# Request
class CreateTaskRequest(BaseModel):
    image_url: str | None = None
    image_base64: str | None = None
    prompt_mode: Literal[
        "standard_visual", "pure_vision",
        "adversarial", "multiturn", "reverse"
    ] = "standard_visual"
    question: str
    background: str | None = None
    figure_description: str | None = None
    output_format: Literal["text", "structured", "json_only"] = "structured"

# Response
class CreateTaskResponse(BaseModel):
    task_id: str
    status: Literal["processing", "queued"]
    stream_url: str  # SSE 地址

# GET /api/v1/tasks/{id}
class TaskResult(BaseModel):
    task_id: str
    status: Literal[
        "processing", "waiting_human_review",
        "completed", "failed"
    ]
    vision_result: VisionOutput | None
    design_result: DesignOutput | None
    knowledge_result: KnowledgeOutput | None
    report_url: str | None
    conflicts: list[ConflictInfo]
    created_at: datetime
    completed_at: datetime | None
```

### 2.3 模块依赖关系图

```
┌──────────────────────────────────────────────────┐
│                  api/ (FastAPI)                   │
│         依赖: agents/, domain/, config/           │
└──────────────────────┬───────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────┐
│           agents/ (LangChain + LangGraph)         │
│         依赖: domain/, infrastructure/            │
│                                                   │
│  master/graph.py 编排所有 SubGraph                 │
│  各 agent 通过 LangChain Tools 调用基础设施        │
└──────────────────────┬───────────────────────────┘
                       ↓
┌──────────────┐  ┌──────────────┐
│  domain/     │  │infrastructure/│
│  纯业务模型   │  │ 外部服务封装  │
│  无外部依赖   │  │ vLLM/OCR/DB  │
└──────────────┘  └──────────────┘
```

### 2.4 职责边界

| 模块 | 职责 | 不负责 |
|------|------|--------|
| **api/** | 请求验证、认证鉴权、SSE推送、响应序列化 | 业务逻辑、模型调用 |
| **agents/** | Agent编排、Prompt管理、Tool调用、状态流转 | 数据持久化、外部API细节 |
| **domain/** | 业务实体定义、领域规则、聚合根 | 框架依赖、外部调用 |
| **infrastructure/** | 外部服务客户端封装、数据库操作、文件存储 | 业务逻辑 |

---

## 三、数据库设计

### 3.1 存储选型矩阵

| 存储类型 | 技术选型 | 存储内容 | 数据特征 |
|---------|---------|---------|---------|
| **关系型** | PostgreSQL 16 | 任务、图纸元数据、用户、审计日志 | 结构化、事务性、强一致 |
| **向量库** | Milvus 2.4 | 图纸特征向量、标号Embedding | 高维向量、ANN检索 |
| **图数据库** | Neo4j 5.x | 标号-部件-设备-故障关系 | 图结构、多跳查询 |
| **缓存** | Redis 7 | Agent状态、LangGraph Checkpoint、热数据 | KV、TTL、Pub/Sub |
| **对象存储** | MinIO | 图纸文件、报告文件、模型权重 | 大文件、二进制 |
| **搜索** | Elasticsearch 8 | 图纸全文检索、标号文字搜索 | 倒排索引、模糊匹配 |

### 3.2 PostgreSQL 核心表结构

```sql
-- 图纸文档表
CREATE TABLE drawings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system   VARCHAR(50) NOT NULL,           -- teamcenter/enovia/manual
    source_doc_id   VARCHAR(200),                   -- 源系统原始ID
    version         VARCHAR(50),
    title           VARCHAR(500) NOT NULL,
    drawing_type    VARCHAR(50) NOT NULL,            -- mechanical/electrical/patent
    file_format     VARCHAR(20) NOT NULL,            -- pdf/png/dwg
    file_url        VARCHAR(1000) NOT NULL,          -- MinIO 地址
    image_urls      JSONB DEFAULT '[]',              -- 转换后的图像地址列表
    lifecycle_state VARCHAR(50) DEFAULT 'draft',     -- draft/review/published/archived
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_drawings_source ON drawings(source_system, source_doc_id);
CREATE INDEX idx_drawings_type ON drawings(drawing_type);

-- 解析任务表
CREATE TABLE analysis_tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id      UUID REFERENCES drawings(id),
    user_id         UUID NOT NULL,
    task_type       VARCHAR(50) NOT NULL,            -- single_parse/batch_parse/design_review
    prompt_mode     VARCHAR(50) DEFAULT 'standard_visual',
    question        TEXT NOT NULL,
    background      TEXT,
    status          VARCHAR(50) DEFAULT 'created',   -- created/processing/waiting_review/completed/failed
    langgraph_thread_id VARCHAR(200),                -- LangGraph 线程ID（用于恢复）
    
    -- Agent 输出（JSONB 存储完整结果）
    vision_result   JSONB,
    design_result   JSONB,
    process_result  JSONB,
    knowledge_result JSONB,
    report_result   JSONB,
    
    -- 冲突与审核
    conflicts       JSONB DEFAULT '[]',
    human_decision  JSONB,
    
    -- 指标
    inference_time_ms INTEGER,
    total_tokens    INTEGER,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    
    CONSTRAINT valid_status CHECK (status IN (
        'created', 'processing', 'waiting_review', 'completed', 'failed'
    ))
);
CREATE INDEX idx_tasks_status ON analysis_tasks(status);
CREATE INDEX idx_tasks_user ON analysis_tasks(user_id, created_at DESC);
CREATE INDEX idx_tasks_drawing ON analysis_tasks(drawing_id);

-- 图纸标号表（从 vision_result 中提取，便于独立查询）
CREATE TABLE drawing_labels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id      UUID REFERENCES drawings(id),
    task_id         UUID REFERENCES analysis_tasks(id),
    label_id        VARCHAR(50) NOT NULL,            -- "2", "S", "15"
    label_type      VARCHAR(20) NOT NULL,            -- number/letter/symbol
    name            VARCHAR(200) NOT NULL,           -- 部件名称
    name_synonyms   TEXT[] DEFAULT '{}',
    spatial_info    JSONB,                           -- 空间位置描述
    confidence      FLOAT NOT NULL,
    source          VARCHAR(50) DEFAULT 'vision_agent',  -- vision_agent/manual/legacy
    verified_by     UUID,                            -- 审核人
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_labels_drawing ON drawing_labels(drawing_id);
CREATE INDEX idx_labels_name ON drawing_labels USING GIN (to_tsvector('simple', name));

-- 审计日志表
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID,
    action          VARCHAR(100) NOT NULL,           -- task.create/label.verify/plm.writeback
    resource_type   VARCHAR(50),
    resource_id     UUID,
    detail          JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);
```

### 3.3 Milvus 向量集合设计

```python
# 图纸特征向量集合
drawing_vectors = Collection(
    name="drawing_vectors",
    schema={
        "drawing_id": FieldSchema(dtype=DataType.VARCHAR, max_length=36, is_primary=True),
        "embedding": FieldSchema(dtype=DataType.FLOAT_VECTOR, dim=1024),
        "drawing_type": FieldSchema(dtype=DataType.VARCHAR, max_length=50),
        "source_system": FieldSchema(dtype=DataType.VARCHAR, max_length=50),
    },
    index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "nlist": 128}
)

# 标号 Embedding 集合（用于以标号搜案例）
label_vectors = Collection(
    name="label_vectors",
    schema={
        "label_id": FieldSchema(dtype=DataType.VARCHAR, max_length=36, is_primary=True),
        "drawing_id": FieldSchema(dtype=DataType.VARCHAR, max_length=36),
        "name": FieldSchema(dtype=DataType.VARCHAR, max_length=200),
        "embedding": FieldSchema(dtype=DataType.FLOAT_VECTOR, dim=768),
    },
    index_params={"index_type": "HNSW", "metric_type": "COSINE", "M": 16, "efConstruction": 200}
)
```

### 3.4 Neo4j 知识图谱模型

```cypher
// 节点类型
(:Drawing {id, title, type, version})
(:Label {id, label_id, name})
(:Part {id, name, material, spec})
(:Equipment {id, name, model, location})
(:FaultRecord {id, code, description, date})
(:Supplier {id, name, contact})

// 关系类型
(:Drawing)-[:HAS_LABEL]->(:Label)
(:Label)-[:REFERS_TO]->(:Part)
(:Part)-[:INSTALLED_IN]->(:Equipment)
(:Equipment)-[:HAS_FAULT]->(:FaultRecord)
(:Part)-[:SUPPLIED_BY]->(:Supplier)
(:Drawing)-[:VERSION_OF]->(:Drawing)  // 版本链
(:Label)-[:SAME_AS]->(:Label)         // 跨图标号关联
```

### 3.5 索引优化策略

| 表/集合 | 索引类型 | 索引字段 | 用途 |
|---------|---------|---------|------|
| analysis_tasks | B-Tree | (status) | 任务队列轮询 |
| analysis_tasks | B-Tree | (user_id, created_at DESC) | 用户历史查询 |
| drawing_labels | GIN | to_tsvector(name) | 标号全文检索 |
| drawing_vectors | IVF_FLAT | embedding | 以图搜图 ANN |
| label_vectors | HNSW | embedding | 以标号搜案例 ANN |

---

## 四、安全设计

### 4.1 认证与授权

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   用户/插件    │────→│  API Gateway  │────→│  LangGraph    │
│  (JWT Bearer)  │     │  (验证JWT)     │     │  (携带用户上下文) │
└───────────────┘     └───────────────┘     └───────────────┘
```

| 组件 | 认证方式 | 说明 |
|------|---------|------|
| **用户 → API** | JWT (RS256) | OAuth 2.0 授权码流程，Token 有效期 1h |
| **API → vLLM** | 内网 mTLS | 服务间通信双向证书 |
| **API → PLM** | mTLS + OAuth2 Client Credentials | 独立服务账号，90天轮换 |
| **CAD插件 → API** | JWT + API Key | 双重认证 |

### 4.2 RBAC 权限模型

```python
class Permission(str, Enum):
    TASK_CREATE = "task:create"          # 创建解析任务
    TASK_VIEW_OWN = "task:view:own"      # 查看自己的任务
    TASK_VIEW_ALL = "task:view:all"      # 查看所有任务
    LABEL_VERIFY = "label:verify"        # 审核标号
    PLM_WRITEBACK = "plm:writeback"      # 回写PLM
    KNOWLEDGE_MANAGE = "knowledge:manage" # 管理知识库
    ADMIN = "admin:all"                  # 系统管理


ROLE_PERMISSIONS = {
    "engineer":  [TASK_CREATE, TASK_VIEW_OWN, LABEL_VERIFY],
    "reviewer":  [TASK_CREATE, TASK_VIEW_ALL, LABEL_VERIFY, PLM_WRITEBACK],
    "admin":     [ADMIN],
}
```

### 4.3 数据安全

| 安全项 | 实现方式 |
|--------|---------|
| **传输加密** | HTTPS/TLS 1.3（外部）；mTLS（内部服务间） |
| **存储加密** | PostgreSQL 透明加密；MinIO 服务端 AES-256 加密 |
| **数据脱敏** | 涉密图纸降分辨率、去水印后再供外部访问；精密尺寸对未授权角色脱敏 |
| **审计日志** | 所有 API 调用记录到 audit_logs 表；敏感操作留存 365 天 |
| **图纸隔离** | 按企业/部门划分 MinIO Bucket，配合 RBAC 控制访问 |

---

## 五、高可用设计

### 5.1 可用性目标

| 指标 | 目标 |
|------|------|
| 整体系统可用性 | ≥ 99.5%（工作时间） |
| 单次请求超时 | 60s（含模型推理） |
| 数据持久性 | 99.99%（PostgreSQL + MinIO 备份） |

### 5.2 负载均衡与水平扩展

```
                    ┌─── FastAPI 实例 1 ─── LangGraph Worker 1
Nginx / Traefik ───├─── FastAPI 实例 2 ─── LangGraph Worker 2
  (L7 负载均衡)     └─── FastAPI 实例 3 ─── LangGraph Worker 3
                                                   ↓
                              ┌─── vLLM 实例 1 (GPU 1)
                    vLLM Pool ├─── vLLM 实例 2 (GPU 2)  ← 可选扩展
                              └─── ...
```

| 组件 | 扩展方式 | 扩展粒度 |
|------|---------|---------|
| FastAPI + LangGraph Worker | 水平扩展（多进程/多容器） | CPU 密集 |
| vLLM 推理 | 垂直（更大卡）+ 水平（多卡） | GPU 密集，瓶颈 |
| Milvus | 分片扩展 | 数据量驱动 |
| PostgreSQL | 读写分离 | 读多写少 |
| Redis | Sentinel / Cluster | 高可用 |

### 5.3 熔断降级策略

| 故障场景 | 熔断策略 | 降级方案 |
|---------|---------|---------|
| vLLM 推理超时(>30s) | 熔断器打开（5次连续超时） | 返回"服务繁忙"提示，任务入队等待 |
| vLLM OOM | 立即熔断 | 拒绝大图请求，建议压缩 |
| Milvus 不可用 | 检测到连接失败后降级 | Knowledge Agent 降级为关键词检索（Elasticsearch） |
| Neo4j 不可用 | 降级 | 知识图谱功能暂不可用，不影响核心解析 |
| Redis 不可用 | 降级 | LangGraph Checkpoint 改为内存，重启后任务丢失 |
| PLM 适配器超时 | 重试 3 次 + 指数退避 | 缓存回写请求至 Redis，后台定时重试 |

### 5.4 限流策略

```python
# 基于 SlowAPI (FastAPI 限流中间件)
rate_limits = {
    "/api/v1/tasks":          "10/minute per user",    # 创建任务
    "/api/v1/tasks/batch":    "2/minute per user",     # 批量任务
    "/api/v1/knowledge/search": "30/minute per user",  # 知识检索
}

# vLLM 层面限流
vllm_config = {
    "max_concurrent_requests": 8,    # 5090 单卡上限
    "max_queue_size": 50,            # 排队上限
    "request_timeout": 60,           # 单次推理超时
}
```

---

## 六、中间件选型

### 6.1 Redis（缓存 + 状态 + 消息）

| 用途 | 数据结构 | TTL | 说明 |
|------|---------|-----|------|
| LangGraph Checkpointer | Hash | 24h | Agent 执行状态持久化，支持中断恢复 |
| 任务状态缓存 | String | 1h | 热任务状态加速查询 |
| vLLM 结果缓存 | String | 6h | 相同图纸重复查询命中缓存 |
| 人工审核队列 | List (FIFO) | 无 | 待人工审核的任务队列 |
| PLM 回写重试队列 | Sorted Set | 无 | 按重试时间排序 |
| SSE 订阅通道 | Pub/Sub | — | 流式推理事件分发 |

```python
# LangGraph 使用 Redis Checkpointer
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver(
    redis_url="redis://redis:6379/0",
    ttl=86400,  # 24h
)
graph = master_graph.compile(checkpointer=checkpointer)
```

### 6.2 Kafka / RabbitMQ（事件总线）

选型：**RabbitMQ**（MVP阶段更轻量，后续可迁移 Kafka）

| Topic/Queue | 生产者 | 消费者 | 说明 |
|-------------|--------|--------|------|
| `task.created` | API | LangGraph Worker | 新任务触发 |
| `task.completed` | LangGraph | API (SSE) / PLM Adapter | 任务完成通知 |
| `plm.event.item_released` | PLM Webhook | Task Service | PLM图纸发布→自动触发解析 |
| `plm.writeback.request` | Review Service | PLM Adapter | 回写请求 |
| `data.feedback` | Review Service | Training Pipeline | 人工修正回流 |

### 6.3 Elasticsearch（全文检索）

| 索引 | 数据来源 | 用途 |
|------|---------|------|
| `idmas-drawings` | PostgreSQL 同步 | 图纸标题/描述全文检索 |
| `idmas-labels` | drawing_labels 表 | 标号名称模糊搜索、企业术语匹配 |
| `idmas-knowledge` | 知识库文档 | Agentic RAG 的 BM25 召回通道 |

### 6.4 中间件部署配置

```yaml
# docker-compose.middleware.yml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    ports: ["6379:6379"]
    volumes: ["redis-data:/data"]

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports: ["5672:5672", "15672:15672"]
    environment:
      RABBITMQ_DEFAULT_USER: idmas
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}

  elasticsearch:
    image: elasticsearch:8.15.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ports: ["9200:9200"]
    volumes: ["es-data:/usr/share/elasticsearch/data"]

  milvus:
    image: milvusdb/milvus:v2.4-latest
    ports: ["19530:19530"]
    volumes: ["milvus-data:/var/lib/milvus"]

  neo4j:
    image: neo4j:5-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes: ["neo4j-data:/data"]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    environment:
      MINIO_ROOT_USER: idmas
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes: ["minio-data:/data"]
```

---

## 七、部署架构

### 7.1 环境规划

| 环境 | 用途 | 硬件 | 模型 |
|------|------|------|------|
| **dev** | 本地开发 | CPU only | Mock VLM / 小模型 |
| **staging** | 集成测试 | 1× 4090 | Qwen2.5-VL-7B (INT4) |
| **production** | 生产环境 | 1× 5090 (32GB) | Qwen2.5-VL-7B 全量微调 |
| **production-ha** | 高可用生产 | 2× 5090 | 主备 + InternVL2.5-26B 可选 |

### 7.2 Docker Compose 部署（MVP）

```yaml
# docker-compose.yml
version: "3.9"

services:
  # ============ 应用层 ============
  api-gateway:
    build: ./api
    ports: ["8080:8080"]
    environment:
      - DATABASE_URL=postgresql://idmas:${PG_PASSWORD}@postgres:5432/idmas
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://idmas:${RABBITMQ_PASSWORD}@rabbitmq:5672
      - VLLM_URL=http://vllm:8000
      - MILVUS_HOST=milvus
      - MINIO_ENDPOINT=minio:9000
      - JWT_SECRET=${JWT_SECRET}
    depends_on: [postgres, redis, rabbitmq]
    deploy:
      replicas: 2
      resources:
        limits: { cpus: "2", memory: "4G" }

  langgraph-worker:
    build: ./agents
    environment:
      - REDIS_URL=redis://redis:6379/0
      - VLLM_URL=http://vllm:8000
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - LANGSMITH_PROJECT=idmas-production
    depends_on: [redis, vllm, milvus]
    deploy:
      replicas: 2
      resources:
        limits: { cpus: "4", memory: "8G" }

  # ============ 模型层 ============
  vllm:
    image: vllm/vllm-openai:latest
    command: >
      --model /models/qwen2.5-vl-7b-finetuned
      --max-model-len 4096
      --gpu-memory-utilization 0.92
      --max-num-seqs 8
    ports: ["8000:8000"]
    volumes:
      - model-weights:/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  paddleocr:
    build: ./infrastructure/ocr
    ports: ["8100:8100"]
    deploy:
      resources:
        limits: { cpus: "2", memory: "4G" }

  # ============ 数据层 ============
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: idmas
      POSTGRES_USER: idmas
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pg-data:/var/lib/postgresql/data"]

  # Redis / RabbitMQ / Milvus / Neo4j / MinIO / ES
  # ... (见 6.4 中间件配置)

  # ============ 监控层 ============
  prometheus:
    image: prom/prometheus:latest
    volumes: ["./config/prometheus.yml:/etc/prometheus/prometheus.yml"]
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}

  # ============ 前端 ============
  web:
    build: ./web
    ports: ["3001:80"]
    depends_on: [api-gateway]

volumes:
  pg-data:
  redis-data:
  es-data:
  milvus-data:
  neo4j-data:
  minio-data:
  model-weights:
```

### 7.3 CI/CD 流水线

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Git Push │───→│  Lint +  │───→│  Unit +  │───→│  Build   │
│           │    │  Type    │    │  Integ   │    │  Docker  │
│           │    │  Check   │    │  Tests   │    │  Images  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                              ┌────────────────────────┘
                              ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Push to     │───→│  Deploy to   │───→│  E2E Tests   │
│  Registry    │    │  Staging     │    │  (Playwright) │
└──────────────┘    └──────────────┘    └──────────────┘
                                              │
                                    ┌─────────┘
                                    ↓
                          ┌──────────────┐
                          │  Manual Gate │──→ Deploy to Production
                          │  (审核通过)   │
                          └──────────────┘
```

| 阶段 | 工具 | 触发条件 |
|------|------|---------|
| 代码检查 | Ruff + mypy | 每次 Push |
| 单元测试 | pytest | 每次 Push |
| 集成测试 | pytest + testcontainers | PR 合并 |
| 构建镜像 | Docker Build | main 分支 |
| 部署 Staging | Docker Compose / K8s | 镜像构建成功 |
| E2E 测试 | Playwright | Staging 部署成功 |
| 部署 Production | Docker Compose / K8s | 手动审批 |

### 7.4 监控与告警

| 监控项 | 工具 | 告警阈值 |
|--------|------|---------|
| API P99 延迟 | Prometheus + Grafana | > 5s |
| vLLM GPU 利用率 | nvidia-smi exporter | > 95% 持续 5min |
| vLLM 推理延迟 | Prometheus | 单次 > 30s |
| LangGraph 任务失败率 | LangSmith | > 5% |
| 任务队列积压 | RabbitMQ exporter | > 100 |
| PostgreSQL 连接池 | pg_exporter | > 80% |
| Redis 内存 | Redis exporter | > 80% |
| 磁盘使用率 | node_exporter | > 85% |

### 7.5 日志规范

```python
# 统一日志格式（JSON）
{
    "timestamp": "2026-05-27T10:30:00.123Z",
    "level": "INFO",
    "service": "langgraph-worker",
    "trace_id": "abc123",               # 全链路追踪ID
    "task_id": "task-uuid-xxx",
    "agent": "vision",
    "event": "inference_complete",
    "duration_ms": 2840,
    "metadata": {
        "model": "qwen2.5-vl-7b-ft",
        "tokens": 1567,
        "labels_found": 9
    }
}
```

日志收集：`应用 → Filebeat → Elasticsearch → Kibana`

---

## 附录：技术栈全景

```
┌─────────────────────────────────────────────────────────────┐
│                        技术栈全景                             │
├─────────────┬───────────────────────────────────────────────┤
│ Agent 框架   │ LangChain 0.3+ / LangGraph 0.3+              │
│ 可观测性     │ LangSmith (Agent 追踪)                         │
│ LLM 推理    │ vLLM (Qwen2.5-VL-7B 全量微调)                  │
│ OCR         │ PaddleOCR                                      │
│ Web 框架    │ FastAPI + Uvicorn                               │
│ 前端        │ React + TypeScript + TailwindCSS                │
│ 关系数据库   │ PostgreSQL 16                                   │
│ 向量数据库   │ Milvus 2.4                                     │
│ 图数据库    │ Neo4j 5.x                                      │
│ 缓存/状态   │ Redis 7                                        │
│ 消息队列    │ RabbitMQ 3 (MVP) → Kafka (生产)                 │
│ 全文检索    │ Elasticsearch 8                                 │
│ 对象存储    │ MinIO                                           │
│ 容器化      │ Docker + Docker Compose (MVP) → K8s (生产)      │
│ CI/CD       │ GitHub Actions / GitLab CI                      │
│ 监控        │ Prometheus + Grafana                            │
│ 日志        │ ELK (Elasticsearch + Logstash + Kibana)         │
│ 认证        │ JWT (RS256) + OAuth 2.0                         │
└─────────────┴───────────────────────────────────────────────┘
```

---

**文档结束**
