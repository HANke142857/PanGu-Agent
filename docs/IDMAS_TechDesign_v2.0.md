# 工业图纸智能解析多Agent协同系统 (IDMAS)
# 技术设计文档 v2.0（工业级）

---

| 项目 | 内容 |
|------|------|
| **文档版本** | v2.0 |
| **产品代号** | IDMAS (Industrial Drawing Multi-Agent System) |
| **核心框架** | LangChain 0.3+ / LangGraph 0.3+ |
| **作者** | [待填写] |
| **评审人** | [待填写] |
| **创建日期** | 2026-05-27 |
| **密级** | 内部公开 |

### 变更记录

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.0 | 2026-05-27 | [待填写] | 初版 |
| v2.0 | 2026-05-27 | [待填写] | 工业级重写，补充ADR、时序图、容量规划、威胁建模、灾备 |

---

# 一、架构设计

## 1.1 架构约束与输入

### 业务约束

| 约束 | 说明 | 影响 |
|------|------|------|
| 全私有化部署 | 图纸涉密，数据不出厂区 | 排除SaaS、公有云依赖 |
| 5090单卡起步 | MVP阶段硬件有限 | 模型选7B/8B量级 |
| 对接多品牌PLM | Teamcenter/ENOVIA/IntePLM | 需抽象适配器层 |
| 人机协同 | 低置信度必须人工审核 | 需Graph中断/恢复 |

### 非功能需求摘要

| 指标 | 目标值 |
|------|--------|
| 单图端到端延迟 | < 30s |
| 并发解析能力 | ≥ 8图/分钟(单GPU) |
| 系统可用性 | ≥ 99.5%(工作时段) |
| 数据持久性 | ≥ 99.99% |

## 1.2 架构决策记录 (ADR)

### ADR-001：Agent编排框架 → LangGraph

**评估矩阵：**

| 维度(权重) | LangGraph | AutoGen | CrewAI | 自研 |
|-----------|-----------|---------|--------|------|
| 状态管理(25%) | 5-原生有状态图 | 3-对话级 | 2-简单 | 4 |
| 人机中断(20%) | 5-interrupt原生 | 1-需自建 | 1-需自建 | 3 |
| 流式输出(15%) | 5-astream_events | 3-有限 | 2-有限 | 3 |
| 持久化(15%) | 5-Checkpointer | 1-无 | 1-无 | 3 |
| 可观测性(10%) | 4-LangSmith | 2 | 2 | 2 |
| 学习曲线(10%) | 4 | 3 | 4 | 1 |
| **加权总分** | **4.75** | **2.30** | **1.80** | **2.80** |

**风险缓解：**
- LangGraph API变更 → 锁定版本0.3.x，封装Adapter层隔离依赖
- LangSmith依赖外部SaaS → 生产用自建LangFuse + OpenTelemetry
- Checkpointer性能 → Redis压测，必要时切PostgreSQL Checkpointer

### ADR-002：VLM推理 → 分层策略

| 方案 | 精度 | 延迟 | 隐私 | 决策 |
|------|------|------|------|------|
| GPT-4o API | ⭐⭐⭐⭐⭐ | 3-8s | ❌出境 | 仅蒸馏/验证 |
| Qwen2.5-VL-7B全量微调+vLLM | ⭐⭐⭐⭐ | 1-5s | ✅私有 | **生产推理** |
| InternVL2.5-26B+vLLM | ⭐⭐⭐⭐⭐ | 3-8s | ✅私有 | 高精度备选 |

### ADR-003：可观测性 → LangFuse(自建) + OpenTelemetry

**理由：** 生产环境可能无外网，LangFuse开源可私有部署，兼容LangChain回调。

### ADR-004：消息队列 → RabbitMQ(MVP) → Kafka(扩展)

| 对比 | RabbitMQ | Kafka |
|------|----------|-------|
| 吞吐 | 万级/秒 | 百万级/秒 |
| 运维 | 低 | 高 |
| 适用 | MVP~Phase2 | Phase3+ |

## 1.3 技术栈全景

| 分类 | 选型 |
|------|------|
| Agent框架 | LangChain 0.3.x / LangGraph 0.3.x |
| 可观测性 | LangFuse(自建) + OpenTelemetry + Jaeger |
| LLM推理 | vLLM 0.6+ (Qwen2.5-VL-7B全量微调) |
| OCR | PaddleOCR 2.8+ |
| Web框架 | FastAPI 0.115+ / Uvicorn |
| 前端 | React 19 + TypeScript 5 + TailwindCSS 4 |
| 关系DB | PostgreSQL 16 |
| 向量DB | Milvus 2.4+ |
| 图DB | Neo4j 5.x |
| 缓存/状态 | Redis 7 (Sentinel) |
| 消息队列 | RabbitMQ 3.13 → Kafka 3.8 |
| 全文检索 | Elasticsearch 8.15+ |
| 对象存储 | MinIO |
| 容器化 | Docker Compose(MVP) → K8s 1.30+(生产) |
| IaC | Ansible + Helm |
| CI/CD | GitLab CI / GitHub Actions |
| 监控 | Prometheus + Grafana + Alertmanager |
| 日志 | ELK (Filebeat + ES + Kibana) |
| 密钥管理 | HashiCorp Vault(生产) / .env(dev) |
| 认证 | JWT(RS256) + OAuth 2.0 |
| 网关 | Traefik 3.x(MVP) → Kong(生产) |

## 1.4 整体架构图

```
┌─ 用户交互层 ────────────────────────────────────────────────┐
│  React Web    CAD Plugin    企业微信Bot    PLM Webhook       │
└────────────────────────┬────────────────────────────────────┘
                         ↓ HTTPS
┌─ 网关层 ───────────────────────────────────────────────────┐
│  Traefik: TLS终止 · JWT验证 · 限流 · 路由 · 负载均衡        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─ 应用层 ───────────────────────────────────────────────────┐
│  FastAPI (×N) ──→ LangGraph Worker (×M)                    │
│                                                             │
│  Master Graph:                                              │
│    Intent → Router → [Vision|Design|Process|Knowledge]      │
│          → Conflict → Debate/HumanReview → Report → END    │
│                                                             │
│  State: Redis Checkpointer  |  Trace: LangFuse + OTel      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─ 工具层 (LangChain Tools) ─────────────────────────────────┐
│  vLLM(GPU)  PaddleOCR  Milvus  Neo4j  ES  PLM-Adapters    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─ 数据层 ───────────────────────────────────────────────────┐
│  PostgreSQL  Redis(Sentinel)  MinIO  RabbitMQ              │
└────────────────────────────────────────────────────────────┘
                         ↓
┌─ 监控层 ───────────────────────────────────────────────────┐
│  Prometheus  Grafana  Alertmanager  ELK  Jaeger  LangFuse  │
└────────────────────────────────────────────────────────────┘
```

## 1.5 LangGraph 编排引擎设计

### 1.5.1 全局状态定义

```python
from typing import TypedDict, Annotated
from operator import add

class IDMASState(TypedDict):
    # 输入
    request_id: str
    user_id: str
    user_query: str
    image_url: str
    background_text: str | None
    prompt_mode: str

    # 意图
    intent: str
    required_agents: list[str]
    task_dag: dict

    # Agent输出
    vision_result: dict | None
    ocr_result: dict | None
    design_result: dict | None
    process_result: dict | None
    knowledge_result: dict | None
    report_result: dict | None

    # 冲突与审核
    conflicts: list[dict]
    debate_rounds: list[dict]
    human_review_needed: bool
    human_decision: dict | None

    # 元数据
    status: str
    error: str | None
    total_tokens: int
    messages: Annotated[list, add]
```

### 1.5.2 Master Graph 构建

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import RedisSaver

def build_master_graph(config):
    graph = StateGraph(IDMASState)

    graph.add_node("intent_recognition", intent_node)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("vision_agent", vision_subgraph)
    graph.add_node("ocr_extraction", ocr_node)
    graph.add_node("design_agent", design_subgraph)
    graph.add_node("process_agent", process_subgraph)
    graph.add_node("knowledge_agent", knowledge_subgraph)
    graph.add_node("conflict_detection", conflict_node)
    graph.add_node("adversarial_debate", debate_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("report_agent", report_subgraph)
    graph.add_node("result_aggregation", aggregation_node)
    graph.add_node("error_handler", error_node)

    graph.set_entry_point("intent_recognition")
    graph.add_edge("intent_recognition", "preprocess")

    graph.add_conditional_edges("preprocess", route_by_intent, {
        "vision_first": "vision_agent",
        "knowledge_only": "knowledge_agent",
        "error": "error_handler",
    })

    graph.add_edge("vision_agent", "ocr_extraction")

    graph.add_conditional_edges("ocr_extraction", route_after_vision, {
        "design": "design_agent",
        "process": "process_agent",
        "knowledge": "knowledge_agent",
        "direct": "conflict_detection",
    })

    graph.add_edge("design_agent", "conflict_detection")
    graph.add_edge("process_agent", "conflict_detection")
    graph.add_edge("knowledge_agent", "conflict_detection")

    graph.add_conditional_edges("conflict_detection", check_conflicts, {
        "has_conflict": "adversarial_debate",
        "low_confidence": "human_review",
        "no_conflict": "report_agent",
    })

    graph.add_conditional_edges("adversarial_debate", check_debate, {
        "resolved": "report_agent",
        "unresolved": "human_review",
    })

    graph.add_edge("human_review", "report_agent")
    graph.add_edge("report_agent", "result_aggregation")
    graph.add_edge("result_aggregation", END)
    graph.add_edge("error_handler", END)

    checkpointer = RedisSaver(redis_url=config.redis_url, ttl=86400)
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )
```

### 1.5.3 Vision SubGraph

```python
class VisionState(TypedDict):
    image_url: str
    prompt_mode: str
    cot_steps: list[dict]
    parsed_labels: list[dict] | None
    confidence_scores: dict | None
    needs_ocr_retry: bool
    retry_count: int
    final_result: dict | None

def build_vision_subgraph():
    graph = StateGraph(VisionState)
    graph.add_node("preprocess_image", preprocess_image_node)
    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("vllm_inference", vllm_inference_node)
    graph.add_node("parse_output", parse_output_node)
    graph.add_node("confidence_check", confidence_check_node)
    graph.add_node("ocr_retry", ocr_retry_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("preprocess_image")
    graph.add_edge("preprocess_image", "build_prompt")
    graph.add_edge("build_prompt", "vllm_inference")
    graph.add_edge("vllm_inference", "parse_output")
    graph.add_edge("parse_output", "confidence_check")
    graph.add_conditional_edges("confidence_check",
        lambda s: "retry" if s["needs_ocr_retry"] and s["retry_count"] < 1 else "done",
        {"retry": "ocr_retry", "done": "finalize"})
    graph.add_edge("ocr_retry", "vllm_inference")
    graph.add_edge("finalize", END)
    return graph.compile()
```

### 1.5.4 LangChain Tools

```python
from langchain_core.tools import tool

@tool
def vllm_vision_inference(image_url: str, prompt: str, max_tokens: int = 2048) -> str:
    """调用vLLM进行图纸视觉推理"""
    client = get_vllm_client()
    response = client.chat.completions.create(
        model="qwen2.5-vl-7b-finetuned",
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": prompt},
        ]}],
        max_tokens=max_tokens, temperature=0.1,
    )
    return response.choices[0].message.content

@tool
def ocr_extract_labels(image_url: str) -> dict:
    """PaddleOCR提取标号文字和坐标"""
    result = get_ocr_client().predict(image_url=image_url)
    return {"texts": result.texts, "boxes": result.boxes, "scores": result.scores}

@tool
def search_knowledge_base(query_text: str, top_k: int = 5) -> list[dict]:
    """从企业知识库检索相关文档"""
    vector = get_embedder().encode(query_text)
    results = milvus_client.search("label_vectors", [vector], limit=top_k)
    return [hit.entity.to_dict() for hit in results[0]]
```

## 1.6 核心时序图

### 1.6.1 单图解析全链路

```
用户       Web        FastAPI      RabbitMQ    LangGraph     vLLM      OCR      Redis
 │──上传──→│──POST────→│──publish──→│           │             │         │         │
 │         │←─202─────│            │──consume─→│             │         │         │
 │         │──SSE─────→│            │           │             │         │         │
 │         │           │            │      [Intent Node]      │         │         │
 │         │←SSE:intent│            │           │             │         │         │
 │         │           │            │      [Vision SubGraph]  │         │         │
 │         │           │            │           │──推理──────→│         │         │
 │         │           │            │           │←─COT结果───│         │         │
 │         │←SSE:vision│            │           │──OCR请求───────────→│         │
 │         │           │            │           │←─标号坐标──────────│         │
 │         │←SSE:ocr   │            │      [Conflict Check]   │         │         │
 │         │           │            │           │──checkpoint──────────────────→│
 │         │           │            │      [Report SubGraph]  │         │         │
 │         │←SSE:done  │            │           │             │         │         │
```

### 1.6.2 人工审核中断与恢复

```
LangGraph         Redis           FastAPI          Web            工程师
    │                │               │              │               │
    │──[发现低置信度]─│               │              │               │
    │──save checkpoint→│              │              │               │
    │──interrupt─────→│              │              │               │
    │  (Graph暂停)    │              │              │               │
    │                │  ←─查询状态───│←─轮询────────│               │
    │                │  ─→waiting───→│──→展示审核面板→│               │
    │                │               │              │←─修改+确认────│
    │                │  ←─POST review│              │               │
    │←─resume────────│              │              │               │
    │  (Graph恢复)    │              │              │               │
    │──[Report]──────→│              │──SSE:done──→│               │
```

### 1.6.3 对抗辩论时序

```
Conflict Node     Vision Agent    Knowledge Agent
     │                │                 │
     │──检测到命名冲突──│                 │
     │  (标号7: V="轴承座" K="支撑架")   │
     │                │                 │
     │──[Round 1] 请求证据──→│           │
     │                │──视觉证据──→     │
     │──[Round 1] 请求证据───────────→│  │
     │                │              │──知识证据──→
     │──[Round 2] 请求反驳──→│           │
     │──[Round 2] 请求反驳───────────→│  │
     │                │                 │
     │──计算置信度: V=0.72, K=0.85       │
     │  差距>15% && K>85% → 自动裁决(K胜)│
     │  否则 → 转人工仲裁                │
```

### 1.6.4 PLM回写（含重试幂等）

```
Report       FastAPI       PLM Adapter      Teamcenter     Redis(重试队列)
  │──回写请求──→│──幂等Key──→│                 │               │
  │             │            │──查Redis────────────────────→│
  │             │            │←─未找到───────────────────────│
  │             │            │──SOA写入───────→│              │
  │             │            │                │              │
  │   [成功]    │            │←─200 OK────────│              │
  │             │            │──记幂等Key(TTL=7d)────────→│  │
  │             │            │                │              │
  │   [失败]    │            │←─500/Timeout───│              │
  │             │            │──加入重试队列──────────────→│  │
  │             │            │  (指数退避: 30s,60s,120s,300s,600s, 共5次)
  │   [5次全败] │            │──告警→Alertmanager           │
```

## 1.7 容量规划

### 用户规模与负载

| 维度 | Phase 1(MVP) | Phase 2 | Phase 3(生产) |
|------|-------------|---------|--------------|
| 日活用户 | 5-10 | 20-50 | 50-200 |
| 日均任务 | 20-50 | 100-300 | 500-2000 |
| 峰值(图/分钟) | 3 | 8 | 20 |
| 日增存储 | 100MB | 600MB | 4GB |
| 年累计存储 | 36GB | 216GB | 1.5TB |

### GPU推理容量

| 配置 | 5090单卡(32GB) | 2×5090 | 1×A100(80GB) |
|------|---------------|--------|-------------|
| 模型 | Qwen2.5-VL-7B FP16 | +InternVL2.5-26B | Qwen2.5-VL-7B |
| 单图延迟 | 2-5s | 2-5s/5-10s | 1-3s |
| QPS | ~8 | ~12 | ~16 |
| 峰值(图/分) | ~30 | ~45 | ~60 |

**结论：** 5090单卡Phase1-2足够，Phase3需扩至2×5090或A100。

### 计算资源总览(MVP)

| 组件 | CPU | 内存 | 磁盘 | GPU |
|------|-----|------|------|-----|
| FastAPI ×2 | 4c | 8GB | 20GB | - |
| LangGraph Worker ×2 | 8c | 16GB | 20GB | - |
| vLLM ×1 | 4c | 16GB | 50GB | 1×5090 |
| PaddleOCR ×1 | 2c | 4GB | 5GB | - |
| PostgreSQL | 2c | 4GB | 100GB SSD | - |
| Redis(Sentinel) | 2c | 4GB | 10GB | - |
| Milvus | 2c | 4GB | 50GB | - |
| Neo4j | 2c | 4GB | 20GB | - |
| Elasticsearch | 2c | 4GB | 50GB | - |
| MinIO | 1c | 2GB | 500GB | - |
| RabbitMQ | 1c | 1GB | 10GB | - |
| 监控栈 | 2c | 4GB | 50GB | - |
| **合计** | **32c** | **71GB** | **885GB** | **1×5090** |

---

# 二、模块划分

## 2.1 DDD领域划分与目录结构

```
idmas/
├── domain/                       # 领域层（零框架依赖）
│   ├── drawing/                  #   图纸聚合根
│   ├── analysis/                 #   解析任务聚合根
│   ├── knowledge/                #   知识库聚合根
│   └── shared/                   #   共享值对象、领域异常
├── agents/                       # Agent层（LangChain/LangGraph）
│   ├── master/                   #   Master Graph编排
│   ├── vision/                   #   Vision SubGraph
│   ├── design/                   #   Design SubGraph
│   ├── process/                  #   Process SubGraph
│   ├── knowledge/                #   Knowledge SubGraph + RAG
│   ├── report/                   #   Report SubGraph
│   └── shared/                   #   回调、重试、Token计数
├── infrastructure/               # 基础设施层
│   ├── llm/                      #   vLLM/OpenAI客户端
│   ├── ocr/                      #   PaddleOCR客户端
│   ├── vectordb/                 #   Milvus客户端
│   ├── graphdb/                  #   Neo4j客户端
│   ├── search/                   #   ES客户端
│   ├── storage/                  #   MinIO客户端
│   ├── cache/                    #   Redis客户端
│   ├── mq/                       #   RabbitMQ发布/消费
│   ├── adapters/                 #   PLM适配器(TC/ENOVIA/IntePLM)
│   ├── observability/            #   OTel/LangFuse/Prometheus
│   └── db/                       #   SQLAlchemy + Alembic
├── api/                          # API层（FastAPI）
│   ├── routes/                   #   路由定义
│   ├── middleware/               #   认证、限流、错误处理
│   └── schemas/                  #   Pydantic模型
├── config/                       # 配置
│   ├── settings.py               #   环境变量管理
│   └── prompts/                  #   Prompt模板(Jinja2)
├── tests/                        # 测试
│   ├── unit/ integration/ e2e/
│   └── fixtures/
└── deploy/                       # 部署配置
    ├── docker/
    ├── k8s/
    ├── helm/
    └── ansible/
```

## 2.2 API契约

| 方法 | 路径 | 说明 | 限流 |
|------|------|------|------|
| POST | `/api/v1/tasks` | 创建解析任务 | 10/min |
| GET | `/api/v1/tasks/{id}` | 查询任务结果 | 60/min |
| GET | `/api/v1/tasks/{id}/stream` | SSE流式进度 | 10/min |
| POST | `/api/v1/tasks/{id}/review` | 提交审核结果 | 30/min |
| POST | `/api/v1/tasks/batch` | 批量任务 | 2/min |
| POST | `/api/v1/drawings` | 上传图纸 | 20/min |
| POST | `/api/v1/knowledge/search` | 知识检索 | 30/min |
| POST | `/api/v1/plm/writeback` | PLM回写 | 10/min |
| GET | `/api/v1/health` | 健康检查 | — |
| GET | `/metrics` | Prometheus指标 | 内网 |

## 2.3 错误码规范

| 错误码 | HTTP | 含义 | 重试 |
|--------|------|------|------|
| IDMAS-400-001 | 400 | 参数校验失败 | 否 |
| IDMAS-400-003 | 400 | 图片尺寸超限(>4096²) | 否,需压缩 |
| IDMAS-401-001 | 401 | JWT无效或过期 | 否,重新认证 |
| IDMAS-403-001 | 403 | 无权操作 | 否 |
| IDMAS-404-001 | 404 | 资源不存在 | 否 |
| IDMAS-429-001 | 429 | 频率超限 | 是,等待 |
| IDMAS-500-001 | 500 | 内部错误 | 是 |
| IDMAS-503-001 | 503 | vLLM不可用 | 是,30s后 |
| IDMAS-503-002 | 503 | GPU OOM | 否,压缩图片 |
| IDMAS-503-003 | 503 | PLM连接超时 | 是,自动5次 |
| IDMAS-504-001 | 504 | 推理超时(>60s) | 是,减小图片 |

**响应格式：**
```json
{
  "error": {
    "code": "IDMAS-503-001",
    "message": "Vision Agent推理服务暂不可用",
    "detail": "vLLM连接超时",
    "retry_after": 30,
    "request_id": "req_abc123"
  }
}
```

## 2.4 依赖关系与职责边界

| 模块 | 职责 | 不负责 |
|------|------|--------|
| **api/** | 请求验证、认证、限流、SSE推送 | 业务逻辑、模型调用 |
| **agents/** | Agent编排、Prompt管理、Tool调用、状态流转 | 持久化细节、外部API协议 |
| **domain/** | 业务实体、领域规则、值对象 | 框架依赖、外部调用 |
| **infrastructure/** | 外部服务封装、连接管理、重试 | 业务逻辑 |

## 2.5 API版本管理

| 策略 | 说明 |
|------|------|
| URL路径版本 | `/api/v1/...` → `/api/v2/...` |
| 向后兼容 | 同版本内只增不删字段 |
| 废弃流程 | 标记Deprecated → 90天过渡 → 下线 |

---

# 三、数据库设计

## 3.1 存储选型矩阵

| 存储类型 | 选型 | 内容 | 一致性 |
|---------|------|------|--------|
| 关系型 | PostgreSQL 16 | 任务、图纸、用户、标号、审计 | 强一致 |
| 向量库 | Milvus 2.4 | 图纸特征、标号Embedding | 最终一致 |
| 图DB | Neo4j 5.x | 标号-部件-设备关系 | 最终一致 |
| 缓存 | Redis 7 | Agent状态、Checkpoint、热数据 | 最终一致 |
| 对象存储 | MinIO | 图纸文件、报告、模型权重 | 写后一致 |
| 搜索 | Elasticsearch 8 | 标号全文、知识文档 | 近实时 |

## 3.2 PostgreSQL数据模型

### ER关系图

```
users (1) ──→ (N) analysis_tasks ←── (1) drawings
                      │ (1)
                      ↓ (N)
              drawing_labels ←── review_records
                                       │
                                       ↓
                                 audit_logs
```

### 核心DDL

```sql
-- 用户表
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'engineer',
    department      VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_role CHECK (role IN ('engineer','reviewer','admin'))
);

-- 图纸文档表
CREATE TABLE drawings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system   VARCHAR(50) NOT NULL,
    source_doc_id   VARCHAR(200),
    title           VARCHAR(500) NOT NULL,
    drawing_type    VARCHAR(50) NOT NULL,
    file_format     VARCHAR(20) NOT NULL,
    file_url        VARCHAR(1000) NOT NULL,
    file_size_bytes BIGINT,
    image_width     INTEGER,
    image_height    INTEGER,
    lifecycle_state VARCHAR(50) DEFAULT 'draft',
    uploaded_by     UUID REFERENCES users(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_drawings_source ON drawings(source_system, source_doc_id);
CREATE INDEX idx_drawings_type ON drawings(drawing_type);
CREATE INDEX idx_drawings_title_trgm ON drawings USING GIN (title gin_trgm_ops);

-- 解析任务表
CREATE TABLE analysis_tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id          UUID REFERENCES drawings(id),
    user_id             UUID NOT NULL REFERENCES users(id),
    task_type           VARCHAR(50) NOT NULL,
    prompt_mode         VARCHAR(50) DEFAULT 'standard_visual',
    question            TEXT NOT NULL,
    background          TEXT,
    status              VARCHAR(50) DEFAULT 'created',
    langgraph_thread_id VARCHAR(200),
    vision_result       JSONB,
    ocr_result          JSONB,
    design_result       JSONB,
    process_result      JSONB,
    knowledge_result    JSONB,
    report_result       JSONB,
    conflicts           JSONB DEFAULT '[]',
    human_decision      JSONB,
    inference_time_ms   INTEGER,
    total_tokens        INTEGER,
    model_version       VARCHAR(100),
    error_code          VARCHAR(20),
    error_message       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);
CREATE INDEX idx_tasks_status ON analysis_tasks(status)
    WHERE status NOT IN ('completed','failed');
CREATE INDEX idx_tasks_user ON analysis_tasks(user_id, created_at DESC);
CREATE INDEX idx_tasks_langgraph ON analysis_tasks(langgraph_thread_id);

-- 标号表
CREATE TABLE drawing_labels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id      UUID NOT NULL REFERENCES drawings(id),
    task_id         UUID REFERENCES analysis_tasks(id),
    label_id        VARCHAR(50) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    confidence      FLOAT NOT NULL,
    spatial_info    JSONB,
    bounding_box    JSONB,
    source          VARCHAR(50) DEFAULT 'vision_agent',
    verified_by     UUID REFERENCES users(id),
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_labels_drawing ON drawing_labels(drawing_id);
CREATE INDEX idx_labels_name ON drawing_labels
    USING GIN (to_tsvector('simple', name));

-- 审核记录表
CREATE TABLE review_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID NOT NULL REFERENCES analysis_tasks(id),
    reviewer_id     UUID NOT NULL REFERENCES users(id),
    label_id        VARCHAR(50) NOT NULL,
    original_name   VARCHAR(200),
    corrected_name  VARCHAR(200),
    action          VARCHAR(20) NOT NULL,  -- confirm/correct/reject
    feedback_status VARCHAR(20) DEFAULT 'pending',  -- pending/approved/rejected
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 审计日志表
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID,
    action      VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    detail      JSONB DEFAULT '{}',
    ip_address  INET,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);
-- 按月分区
CREATE TABLE audit_logs_partitioned (LIKE audit_logs INCLUDING ALL)
    PARTITION BY RANGE (created_at);
```

## 3.3 向量数据库(Milvus)

```python
# 图纸特征向量
Collection("drawing_vectors", schema={
    "drawing_id": VARCHAR(36, primary=True),
    "embedding":  FLOAT_VECTOR(dim=1024),
    "drawing_type": VARCHAR(50),
}, index={"type": "IVF_FLAT", "metric": "COSINE", "nlist": 128})

# 标号Embedding（以标号搜案例）
Collection("label_vectors", schema={
    "label_id":   VARCHAR(36, primary=True),
    "drawing_id": VARCHAR(36),
    "name":       VARCHAR(200),
    "embedding":  FLOAT_VECTOR(dim=768),
}, index={"type": "HNSW", "metric": "COSINE", "M": 16, "efConstruction": 200})
```

## 3.4 图数据库(Neo4j)

```cypher
// 节点
(:Drawing {id, title, type})
(:Label {id, label_id, name})
(:Part {id, name, material, spec})
(:Equipment {id, name, model})
(:FaultRecord {id, code, description})

// 关系
(:Drawing)-[:HAS_LABEL]->(:Label)
(:Label)-[:REFERS_TO]->(:Part)
(:Part)-[:INSTALLED_IN]->(:Equipment)
(:Equipment)-[:HAS_FAULT]->(:FaultRecord)
(:Label)-[:SAME_AS]->(:Label)         // 跨图标号关联
(:Drawing)-[:VERSION_OF]->(:Drawing)  // 版本链
```

## 3.5 容量估算

| 数据 | 年增量(Phase3) | 单条大小 | 年存储 |
|------|-------------|---------|--------|
| drawings表 | ~5000条 | ~2KB | ~10MB |
| analysis_tasks表 | ~50万条 | ~10KB | ~5GB |
| drawing_labels表 | ~500万条 | ~1KB | ~5GB |
| audit_logs表 | ~200万条 | ~500B | ~1GB |
| 图纸文件(MinIO) | ~5000个 | ~2MB | ~10GB |
| 向量(Milvus) | ~500万条 | ~4KB | ~20GB |
| 图谱节点(Neo4j) | ~50万 | ~500B | ~250MB |

**总计年增：** 关系数据~11GB + 文件~10GB + 向量~20GB + 图谱~250MB ≈ **~41GB/年**

## 3.6 备份与恢复策略

| 存储 | 备份方式 | 频率 | 保留期 | RTO |
|------|---------|------|--------|-----|
| PostgreSQL | WAL归档 + pg_basebackup全量 | WAL实时 + 每日全量 | 30天 | < 1h |
| Redis | RDB快照 + AOF | RDB每6h + AOF always | 7天 | < 5min |
| Milvus | 快照备份 | 每日 | 14天 | < 2h |
| Neo4j | neo4j-admin dump | 每日 | 14天 | < 1h |
| MinIO | 跨磁盘镜像(RAID) + 异地复制 | 实时 | 永久 | < 30min |
| ES | Snapshot to MinIO | 每日 | 7天 | < 2h |

**恢复SOP：**
1. PostgreSQL: 恢复最近全量 → 重放WAL至故障点(PITR)
2. Redis: 加载最近RDB → 重放AOF
3. 其他: 从快照恢复 → 从PG重建增量

## 3.7 数据迁移与演进策略

| 策略 | 工具 | 说明 |
|------|------|------|
| Schema迁移 | Alembic | 每次变更生成版本化迁移脚本 |
| 零停机迁移 | expand-contract模式 | 先加新列→双写→迁移→删旧列 |
| 回滚 | Alembic downgrade | 每个迁移必须有reverse |
| 大表DDL | pg_repack / `CREATE INDEX CONCURRENTLY` | 避免锁表 |
| 数据回填 | 批量脚本(每次1000条+sleep) | 避免峰值IO |

## 3.8 数据保留与归档

| 数据类型 | 热存储 | 温存储 | 冷归档 |
|---------|--------|--------|--------|
| 活跃任务 | PostgreSQL | — | — |
| 已完成任务 | PG(90天) | PG分区(1年) | MinIO Parquet(永久) |
| 审计日志 | PG分区(30天) | ES(1年) | 归档删除 |
| 图纸文件 | MinIO(热) | MinIO(永久) | — |
| LangGraph Checkpoint | Redis(24h TTL) | — | 自动过期 |

---

# 四、安全设计

## 4.1 威胁建模 (STRIDE)

| 威胁类型 | 攻击面 | 风险场景 | 缓解措施 |
|---------|--------|---------|---------|
| **S-仿冒** | API网关 | 伪造JWT令牌访问系统 | RS256签名验证 + 短期Token(1h) + Refresh机制 |
| **S-仿冒** | PLM适配器 | 冒充PLM回调注入恶意数据 | Webhook签名验证 + IP白名单 |
| **T-篡改** | 图纸传输 | 中间人篡改图纸内容 | HTTPS/TLS 1.3 + 文件SHA256校验 |
| **T-篡改** | 标号结果 | 恶意修改已确认的解析结果 | 审计日志 + 数据变更触发器 |
| **R-否认** | 人工审核 | 工程师否认自己的审核操作 | 操作审计(user+时间+IP+操作内容) |
| **I-信息泄露** | vLLM推理 | 模型权重或Prompt被窃取 | 内网隔离 + 无外网访问 + 最小端口暴露 |
| **I-信息泄露** | 图纸文件 | 涉密图纸被未授权下载 | MinIO Bucket策略 + RBAC + presigned URL(5min过期) |
| **D-拒绝服务** | API网关 | 大量请求耗尽GPU资源 | 多级限流 + 请求队列 + 熔断 |
| **D-拒绝服务** | vLLM | 超大图纸OOM | 图片尺寸校验(>4096²拒绝) + GPU显存监控 |
| **E-权限提升** | 用户API | 普通工程师执行管理员操作 | RBAC严格校验 + 最小权限原则 |

## 4.2 数据分级

| 级别 | 定义 | 数据示例 | 存储要求 | 传输要求 |
|------|------|---------|---------|---------|
| **L4-绝密** | 核心技术/军工图纸 | — (当前不涉及) | — | — |
| **L3-机密** | 企业核心工艺图纸 | 自主设计图纸、核心BOM | 加密存储 + 访问审计 | mTLS + 日志 |
| **L2-内部** | 一般业务数据 | 解析结果、标号信息 | 标准存储 + 访问控制 | HTTPS |
| **L1-公开** | 系统配置、公开文档 | API文档、健康检查 | 标准存储 | HTTP/HTTPS |

**数据流动规则：**
- L3数据不得复制到开发/测试环境（需脱敏）
- 模型训练数据使用前必须经过脱敏审批
- presigned URL过期时间：L3=5分钟，L2=1小时

## 4.3 认证与授权

### 认证流程

```
用户 → [OAuth 2.0 Authorization Code] → 获取 JWT (RS256)
CAD插件 → [API Key + JWT] → 双重认证
PLM Webhook → [HMAC签名 + IP白名单] → 验证来源
服务间 → [mTLS] → 双向证书
```

### RBAC权限

```python
PERMISSIONS = {
    "engineer":  ["task:create", "task:view:own", "drawing:upload"],
    "reviewer":  ["task:create", "task:view:all", "label:verify",
                  "plm:writeback", "drawing:upload"],
    "admin":     ["*"],
}
```

### JWT结构

```json
{
  "sub": "user-uuid",
  "role": "reviewer",
  "department": "设计部",
  "permissions": ["task:create", "task:view:all", "label:verify"],
  "exp": 1716800000,
  "iat": 1716796400,
  "iss": "idmas-auth"
}
```

## 4.4 密钥与凭据管理

| 环境 | 方案 | 说明 |
|------|------|------|
| 开发 | `.env` 文件 (gitignored) | 本地开发用，不入库 |
| 测试 | GitLab CI Variables (masked) | CI流水线注入 |
| 生产 | **HashiCorp Vault** | 集中管理、动态凭据、审计 |

**Vault管理的密钥：**
- JWT RS256 私钥（90天轮换）
- PostgreSQL 密码（动态凭据，TTL=1h）
- Redis AUTH 密码
- MinIO Access Key
- PLM系统服务账号凭据
- RabbitMQ 连接密码

**轮换策略：**
| 凭据类型 | 轮换周期 | 方式 |
|---------|---------|------|
| JWT签名密钥 | 90天 | 双密钥过渡(新签旧验→全切) |
| DB密码 | Vault动态(1h) | Vault lease自动续期 |
| PLM服务账号 | 90天 | 手动轮换+双账号过渡 |
| TLS证书 | 1年 | cert-manager自动续期 |

## 4.5 传输与存储加密

| 层面 | 方案 |
|------|------|
| 外部→网关 | TLS 1.3 (ECDHE + AES-256-GCM) |
| 服务间 | mTLS (自签CA，cert-manager管理) |
| PostgreSQL存储 | 透明数据加密 (TDE) 或 pgcrypto列加密(L3数据) |
| MinIO存储 | 服务端加密 SSE-S3 (AES-256) |
| Redis传输 | TLS + AUTH |
| 备份文件 | GPG加密后存储 |

## 4.6 审计日志

**必须记录的操作：**

| 操作 | 记录内容 |
|------|---------|
| 用户登录/登出 | user, IP, UA, 时间, 成功/失败 |
| 创建解析任务 | user, drawing_id, task_type |
| 查看/下载图纸 | user, drawing_id, 数据级别 |
| 人工审核标号 | user, task_id, label, 原值, 新值 |
| PLM回写 | user, target_system, doc_id, 成功/失败 |
| 管理员操作 | user, 操作类型, 影响范围 |
| API鉴权失败 | IP, 请求路径, 失败原因 |

**保留期：** 365天(PostgreSQL分区) → 超期归档至MinIO(Parquet格式)

## 4.7 安全测试计划

| 测试类型 | 频率 | 工具 | 范围 |
|---------|------|------|------|
| SAST (静态分析) | 每次CI | Bandit + Semgrep | Python代码 |
| 依赖漏洞扫描 | 每次CI | pip-audit + Trivy | 依赖+镜像 |
| DAST (动态测试) | 每周 | OWASP ZAP | API接口 |
| 渗透测试 | 每季度/上线前 | 人工+Burp Suite | 全系统 |
| 密钥泄露检测 | 每次CI | gitleaks | Git仓库 |

**上线前安全检查清单：**
- [ ] 无硬编码密钥/密码
- [ ] 所有API有认证保护
- [ ] 输入参数有校验和长度限制
- [ ] SQL查询使用参数化（ORM）
- [ ] 文件上传有类型和大小限制
- [ ] 错误响应不泄露内部细节
- [ ] CORS配置正确（非`*`）
- [ ] 敏感数据日志脱敏

## 4.8 安全事件响应流程

```
检测 → 分类 → 遏制 → 根因分析 → 修复 → 复盘

Level 1 (低): 非核心服务异常 → 工程师值班处理 → 24h内
Level 2 (中): 数据泄露风险  → 安全负责人 → 4h内遏制
Level 3 (高): 确认数据泄露  → CTO + 法务 → 1h内遏制 + 上报
```

---

# 五、高可用设计

## 5.1 SLA定义

| 服务级别 | 可用性 | 月允许宕机 | 适用环境 |
|---------|--------|-----------|---------|
| **Gold** | 99.9% | 43分钟 | 未来生产(多活) |
| **Silver** | 99.5% | 3.6小时 | **当前生产目标** |
| **Bronze** | 99.0% | 7.2小时 | MVP/测试 |

## 5.2 RPO / RTO目标

| 组件 | RPO(可容忍丢失) | RTO(恢复时间) | 策略 |
|------|----------------|-------------|------|
| PostgreSQL | 0 (零丢失) | < 1h | WAL流复制 + PITR |
| Redis | < 1s | < 5min | AOF always + Sentinel |
| MinIO | 0 | < 30min | 纠删码(EC) + 跨盘 |
| Milvus | < 1h | < 2h | 每小时快照 |
| 应用服务 | — | < 10min | 多实例 + 健康检查自动重启 |
| vLLM | — | < 15min | 单实例重启(GPU预热) |

## 5.3 负载均衡与水平扩展

```
Traefik (L7)
  ├─ /api/* → FastAPI ×2 (Round Robin, 健康检查)
  ├─ /stream/* → FastAPI ×2 (Sticky Session by task_id)
  └─ /metrics → 内网直通

FastAPI → RabbitMQ → LangGraph Worker ×2 (消费者模式扩展)
LangGraph Worker → vLLM (单实例, 靠vLLM内部continuous batching)
```

| 组件 | 扩展方式 | 触发条件 |
|------|---------|---------|
| FastAPI | 水平(+实例) | CPU > 70% 持续5min |
| LangGraph Worker | 水平(+实例) | 队列积压 > 20 |
| vLLM | 垂直(+GPU) / 水平(+实例) | GPU利用率 > 90% 持续5min |
| PostgreSQL | 读写分离(+只读副本) | 读QPS > 1000 |

## 5.4 熔断降级策略

| 故障 | 检测条件 | 熔断动作 | 降级方案 | 恢复条件 |
|------|---------|---------|---------|---------|
| vLLM超时 | 5次连续>30s | 熔断器开 | 返回503+排队 | 3次连续成功 |
| vLLM OOM | 1次OOM错误 | 拒绝大图 | 建议压缩+等待 | GPU显存恢复 |
| Milvus不可用 | 连接失败 | 标记不可用 | Knowledge降级为ES关键词检索 | 连接恢复 |
| Neo4j不可用 | 连接失败 | 标记不可用 | 图谱功能跳过(不影响核心解析) | 连接恢复 |
| Redis不可用 | 连接失败 | 告警 | Checkpoint改内存(重启丢失) | 连接恢复 |
| PLM超时 | 3次重试失败 | 缓存回写请求 | 后台队列重试(5次) | PLM恢复 |

## 5.5 限流策略

```python
# API层限流 (SlowAPI + Redis后端)
RATE_LIMITS = {
    "/api/v1/tasks":          "10/minute",
    "/api/v1/tasks/batch":    "2/minute",
    "/api/v1/knowledge":      "30/minute",
    "global_per_user":        "100/minute",
}

# vLLM层限流
VLLM_LIMITS = {
    "max_concurrent": 8,      # 5090单卡上限
    "max_queue":      50,     # 排队上限
    "request_timeout": 60,    # 单次超时
}

# 限流响应: 429 + Retry-After header
```

## 5.6 灾备方案

### 单节点灾备(MVP/Phase1-2)

```
主节点(5090服务器)
  ├─ PostgreSQL: WAL归档到MinIO
  ├─ Redis: RDB + AOF 持久化
  ├─ MinIO: 双盘纠删码
  └─ 每日全量备份 → NAS/异地存储

恢复流程:
  1. 新服务器部署Docker环境
  2. 恢复PostgreSQL(PITR)
  3. 恢复Redis(RDB)
  4. 恢复MinIO数据
  5. 启动应用栈
  预计RTO: 2-4小时
```

### 双节点高可用(Phase3)

```
节点A (主)           节点B (备)
  vLLM(GPU)           vLLM(GPU) ← 热备
  FastAPI ×2          FastAPI ×2
  LangGraph ×2        LangGraph ×2
       ↓                   ↓
  PostgreSQL(主) ←→ PostgreSQL(流复制备)
  Redis(主)      ←→ Redis(Sentinel备)
  MinIO(主)      ←→ MinIO(复制)
  
  Traefik 健康检查 → 主故障自动切流量到备
```

## 5.7 故障演练计划

| 演练项 | 频率 | 方式 | 验证点 |
|--------|------|------|--------|
| vLLM进程Kill | 每月 | `kill -9` | 自动重启 < 5min，任务重试成功 |
| PostgreSQL主库切换 | 每季 | 手动触发Failover | 数据零丢失，应用自动重连 |
| Redis Sentinel切换 | 每季 | Kill主节点 | Sentinel选举 < 30s |
| 网络分区模拟 | 每季 | iptables规则 | 熔断器正确触发，降级生效 |
| 全栈恢复演练 | 每半年 | 从备份恢复到新服务器 | RTO < 4h |

---

# 六、中间件选型

## 6.1 Redis

| 用途 | 数据结构 | TTL | Key格式 |
|------|---------|-----|---------|
| LangGraph Checkpoint | Hash | 24h | `lg:thread:{thread_id}` |
| 任务状态缓存 | String(JSON) | 1h | `task:status:{task_id}` |
| vLLM结果缓存 | String | 6h | `vlm:cache:{image_hash}` |
| 人工审核队列 | List(FIFO) | 无 | `review:queue` |
| PLM回写重试 | Sorted Set | 无 | `plm:retry` |
| SSE事件通道 | Pub/Sub | — | `sse:task:{task_id}` |
| API限流计数 | String+INCR | 1min | `ratelimit:{user}:{path}` |

**部署模式：** Redis Sentinel (1主+2从+3哨兵)

## 6.2 消息队列

### RabbitMQ(MVP)

| Queue | 生产者 | 消费者 | 说明 |
|-------|--------|--------|------|
| `task.created` | FastAPI | LangGraph Worker | 新任务分发 |
| `task.completed` | LangGraph | Notification Service | 完成通知 |
| `plm.writeback` | Review Service | PLM Adapter | 回写请求 |
| `plm.writeback.dlq` | — | 运维 | 死信队列(5次失败) |
| `data.feedback` | Review Service | Training Pipeline | 修正数据回流 |

### Kafka迁移触发条件(Phase3+)
- 日均任务 > 1000
- 需要事件回溯/重放
- 需要多消费者组并行处理

## 6.3 Elasticsearch

| 索引 | 映射 | 用途 |
|------|------|------|
| `idmas-drawings` | title(text) + metadata(object) | 图纸搜索 |
| `idmas-labels` | name(text+keyword) + synonyms(text) | 标号模糊匹配 |
| `idmas-knowledge` | content(text) + tags(keyword) | RAG的BM25通道 |

## 6.4 中间件容量估算

| 中间件 | Phase1内存 | Phase3内存 | 磁盘(Phase3) |
|--------|-----------|-----------|-------------|
| Redis | 512MB | 2GB | 10GB(AOF) |
| RabbitMQ | 256MB | 1GB | 5GB |
| Elasticsearch | 1GB | 4GB | 50GB |
| Milvus | 2GB | 4GB | 50GB |
| Neo4j | 1GB | 4GB | 20GB |

## 6.5 中间件集群配置(生产)

| 中间件 | MVP | 生产 |
|--------|-----|------|
| Redis | 单节点+持久化 | Sentinel(1主2从3哨兵) |
| RabbitMQ | 单节点 | 镜像队列(2节点) |
| ES | 单节点 | 3节点集群(1主2数据) |
| Milvus | Standalone | 分布式(etcd+minio+worker) |
| Neo4j | Community单节点 | Community单节点(读性能足够) |

---

# 七、部署架构

## 7.1 环境规划

| 环境 | 用途 | 硬件 | 模型 | 数据 |
|------|------|------|------|------|
| dev | 本地开发 | CPU | Mock VLM | 测试数据 |
| staging | 集成测试 | 1×4090 | 7B INT4 | 脱敏数据 |
| production | 生产 | 1×5090 | 7B全量微调 | 真实数据 |
| production-ha | 高可用生产 | 2×5090 | 主备 | 真实数据 |

## 7.2 网络架构

```
┌─ DMZ ─────────────────────┐   ┌─ 内网(生产) ─────────────────┐
│                           │   │                               │
│  Traefik (TLS终止)        │   │  FastAPI + LangGraph Worker   │
│  ↕ 443 (HTTPS)            │───│  ↕ 内网HTTP                    │
│                           │   │  vLLM (8000)                  │
│  仅暴露:                   │   │  PaddleOCR (8100)             │
│    - 443/tcp (Web+API)    │   │  PostgreSQL (5432)            │
│    - PLM Webhook端口       │   │  Redis (6379)                 │
│                           │   │  其他中间件                    │
└───────────────────────────┘   │                               │
                                │  全部内网端口，不暴露           │
                                └───────────────────────────────┘
```

**防火墙规则：**
- 外部→DMZ: 仅443/tcp
- DMZ→内网: 仅Traefik→FastAPI(8080)
- 内网互通: 允许
- 内网→外部: 默认拒绝(生产无外网)

## 7.3 Kubernetes部署方案(生产)

```yaml
# deploy/k8s/api-deployment.yaml (示例)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: idmas-api
  namespace: idmas
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate: {maxUnavailable: 0, maxSurge: 1}
  template:
    spec:
      containers:
      - name: api
        image: registry.internal/idmas/api:${VERSION}
        resources:
          requests: {cpu: "500m", memory: "1Gi"}
          limits:   {cpu: "2000m", memory: "4Gi"}
        livenessProbe:
          httpGet: {path: /api/v1/health, port: 8080}
          periodSeconds: 30
        readinessProbe:
          httpGet: {path: /api/v1/health/ready, port: 8080}
          periodSeconds: 10
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef: {name: idmas-secrets, key: database-url}
---
# vLLM StatefulSet (GPU节点)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: idmas-vllm
spec:
  replicas: 1
  template:
    spec:
      nodeSelector:
        nvidia.com/gpu.present: "true"
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args: ["--model", "/models/qwen2.5-vl-7b-ft",
               "--max-model-len", "4096",
               "--gpu-memory-utilization", "0.92"]
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "32Gi"
        volumeMounts:
        - name: model-weights
          mountPath: /models
```

## 7.4 Docker Compose部署(MVP)

```yaml
# deploy/docker/docker-compose.yml
services:
  api:
    build: {context: ../.., dockerfile: deploy/docker/Dockerfile.api}
    ports: ["8080:8080"]
    environment:
      DATABASE_URL: postgresql://idmas:${PG_PWD}@postgres:5432/idmas
      REDIS_URL: redis://redis:6379/0
      VLLM_URL: http://vllm:8000
      RABBITMQ_URL: amqp://idmas:${MQ_PWD}@rabbitmq:5672
    depends_on: [postgres, redis, rabbitmq]
    deploy: {replicas: 2}

  worker:
    build: {context: ../.., dockerfile: deploy/docker/Dockerfile.worker}
    environment:
      REDIS_URL: redis://redis:6379/0
      VLLM_URL: http://vllm:8000
    depends_on: [redis, vllm]
    deploy: {replicas: 2}

  vllm:
    image: vllm/vllm-openai:latest
    command: --model /models/qwen2.5-vl-7b-ft --max-model-len 4096
             --gpu-memory-utilization 0.92 --max-num-seqs 8
    volumes: [model-weights:/models]
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]

  postgres:
    image: postgres:16-alpine
    environment: {POSTGRES_DB: idmas, POSTGRES_PASSWORD: ${PG_PWD}}
    volumes: [pg-data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 2gb --appendonly yes

  rabbitmq:
    image: rabbitmq:3-management-alpine

  milvus:
    image: milvusdb/milvus:v2.4-latest

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes: [minio-data:/data]

  prometheus:
    image: prom/prometheus:latest
  grafana:
    image: grafana/grafana:latest
```

## 7.5 CI/CD流水线

```
Git Push → Lint(Ruff+mypy) → Unit Tests → Build Image
  → Push Registry → Deploy Staging → Integration Tests
  → [Manual Gate] → Deploy Production (Rolling Update)
```

| 阶段 | 工具 | 触发 | 阻断条件 |
|------|------|------|---------|
| 代码检查 | Ruff + mypy + Bandit | 每次Push | 任何Error |
| 单元测试 | pytest | 每次Push | 覆盖率<80% |
| 依赖扫描 | pip-audit + Trivy | 每次Push | Critical漏洞 |
| 镜像构建 | Docker Build | main分支 | 构建失败 |
| Staging部署 | Docker Compose | 镜像成功 | — |
| 集成测试 | pytest + testcontainers | Staging就绪 | 任何失败 |
| E2E测试 | Playwright | Staging就绪 | 核心流程失败 |
| 生产部署 | K8s Rolling | **人工审批** | — |

## 7.6 蓝绿/金丝雀发布

| 阶段 | 策略 | 说明 |
|------|------|------|
| MVP | 滚动更新 | Docker Compose maxUnavailable=0 |
| 生产 | **金丝雀** | 先10%流量→观察30min→全量 |
| 紧急回滚 | 镜像回退 | `kubectl rollout undo` / Compose切标签 |

**金丝雀发布检查指标：**
- API P99延迟未增长 > 20%
- 错误率未增长 > 1%
- vLLM推理成功率 > 95%

## 7.7 监控告警体系

### 黄金指标(Golden Signals)

| 指标 | 采集方式 | 告警阈值 | 通知方式 |
|------|---------|---------|---------|
| **延迟** P99 | Prometheus histogram | > 10s | 企业微信 |
| **流量** QPS | Prometheus counter | > 容量80% | Grafana面板 |
| **错误率** | Prometheus counter ratio | > 5% | 企业微信+电话 |
| **饱和度** GPU | nvidia-smi exporter | > 95% 5min | 企业微信 |
| **饱和度** CPU | node_exporter | > 85% 5min | 企业微信 |
| **饱和度** 内存 | node_exporter | > 85% | 企业微信 |
| **饱和度** 磁盘 | node_exporter | > 85% | 企业微信+电话 |
| 任务队列积压 | RabbitMQ exporter | > 50 | 企业微信 |
| LangGraph失败率 | LangFuse | > 5% | 企业微信 |
| vLLM单次推理 | 自定义metric | > 30s | Grafana面板 |

### Grafana Dashboard布局

```
Dashboard 1: 系统总览
  ├─ 任务成功率 (实时)
  ├─ 端到端延迟 P50/P95/P99
  ├─ GPU利用率+显存
  └─ 队列深度

Dashboard 2: Agent详情
  ├─ 各Agent执行时间
  ├─ 冲突触发频率
  ├─ 人工审核队列长度
  └─ Token消耗趋势

Dashboard 3: 基础设施
  ├─ PostgreSQL QPS/连接数
  ├─ Redis内存/命中率
  ├─ MinIO IO
  └─ 网络流量
```

## 7.8 日志规范

```json
{
  "timestamp": "2026-05-27T10:30:00.123Z",
  "level": "INFO",
  "service": "langgraph-worker",
  "trace_id": "abc123",
  "span_id": "def456",
  "task_id": "task-uuid",
  "agent": "vision",
  "event": "inference_complete",
  "duration_ms": 2840,
  "metadata": {"model": "qwen2.5-vl-7b-ft", "tokens": 1567}
}
```

**日志级别约定：**
- ERROR: 需要人工介入的故障
- WARN: 可自愈但需关注的异常(如重试成功)
- INFO: 关键业务事件(任务创建/完成/审核)
- DEBUG: 调试信息(仅dev/staging开启)

**收集链路：** 应用 → Filebeat → Elasticsearch → Kibana

## 7.9 变更管理流程

| 变更类型 | 审批 | 窗口 | 回滚方案 |
|---------|------|------|---------|
| 常规发布 | Tech Lead | 工作日10:00-16:00 | 镜像回退 |
| 数据库迁移 | Tech Lead + DBA | 工作日10:00-14:00 | Alembic downgrade |
| 中间件升级 | Tech Lead + 运维 | 周末维护窗口 | 快照恢复 |
| 模型权重更新 | Tech Lead + 算法 | 工作日(金丝雀) | 切回旧权重 |
| 紧急修复 | 任意2人 | 任何时间 | 镜像回退 |

---

# 附录

## A. 技术栈版本锁定

```toml
# pyproject.toml 核心依赖
[tool.poetry.dependencies]
python = "^3.11"
langchain-core = "~0.3.0"
langgraph = "~0.3.0"
langchain-openai = "~0.3.0"
fastapi = "~0.115.0"
uvicorn = {extras = ["standard"], version = "~0.32.0"}
sqlalchemy = {extras = ["asyncio"], version = "~2.0.0"}
asyncpg = "~0.30.0"
redis = "~5.0.0"
pydantic = "~2.9.0"
httpx = "~0.27.0"
pymilvus = "~2.4.0"
neo4j = "~5.25.0"
elasticsearch = "~8.15.0"
minio = "~7.2.0"
aio-pika = "~9.4.0"  # RabbitMQ
opentelemetry-api = "~1.27.0"
langfuse = "~2.50.0"
```

## B. 性能测试计划

| 测试场景 | 工具 | 目标 | 执行时机 |
|---------|------|------|---------|
| API压测 | Locust | P99<5s@50并发 | 每次发布前 |
| vLLM吞吐 | 自研benchmark | QPS≥8@5090 | 模型更新后 |
| 端到端延迟 | Playwright | <30s@单图 | 每次发布前 |
| 长稳测试 | Locust(持续) | 24h无OOM/泄漏 | 每月 |
| 极限测试 | Locust(递增) | 确定系统瓶颈 | 每季 |

## C. 术语表

| 缩写 | 全称 | 说明 |
|------|------|------|
| ADR | Architecture Decision Record | 架构决策记录 |
| STRIDE | Spoofing/Tampering/Repudiation/Information Disclosure/DoS/Elevation | 威胁建模方法 |
| RPO | Recovery Point Objective | 可容忍数据丢失量 |
| RTO | Recovery Time Objective | 恢复时间目标 |
| PITR | Point-In-Time Recovery | 时间点恢复 |
| SLA | Service Level Agreement | 服务等级协议 |
| mTLS | Mutual TLS | 双向TLS认证 |
| IaC | Infrastructure as Code | 基础设施即代码 |
| DDD | Domain-Driven Design | 领域驱动设计 |
| COT | Chain of Thought | 思维链推理 |
| VLM | Vision-Language Model | 视觉语言模型 |
| ANN | Approximate Nearest Neighbor | 近似最近邻搜索 |

---

**文档结束**
