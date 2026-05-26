# 工业图纸智能解析多Agent协同系统 (IDMAS)
# Product Requirements Document (PRD)

**版本**: v1.0  
**日期**: 2026-05-22  
**产品代号**: IDMAS (Industrial Drawing Multi-Agent System)  
**核心模型**: Qwen3.5-9B-Instruct (Vision-Language LoRA微调)  

---

## 1. 产品背景与战略定位

### 1.1 行业趋势
2026年被业界定义为企业级多智能体规模化"上岗元年"。工业制造领域正从"流程驱动"向"智能驱动"转型，多Agent系统通过专业化分工实现跨部门协作，覆盖设计、质检、运维、工艺规划等核心环节。citeweb_search:10#1web_search:10#5 三菱电机等行业龙头已部署基于对抗辩论的多Agent AI，用于生产规划、安全分析与风险评估。citeweb_search:10#3

### 1.2 核心痛点
当前工业图纸管理存在以下瓶颈：
- **识图依赖专家经验**：专利图纸、机械结构图、电气原理图的标号识别与结构分析高度依赖资深工程师，知识传承困难
- **文本与图纸割裂**：传统PLM/MES系统中，图纸与文本说明书分离，工程师需在多系统间反复切换核对
- **跨部门协同低效**：设计、工艺、质检、运维部门对同一张图纸的理解维度不同，缺乏统一的智能解析中枢
- **知识沉淀困难**：图纸解析结论分散在个人电脑或邮件中，无法形成可检索、可复用的企业知识资产

### 1.3 产品目标
构建以**工业图纸视觉识别Agent**为核心的多Agent协同系统，实现：
- **单图深度解析**：标号识别准确率 >90%（ft_strict > 0.55），结构推理覆盖率 >85%
- **跨Agent协同**：图纸解析结果自动驱动设计审查、工艺规划、知识检索、报告生成等下游任务
- **人机共生**：工程师从"逐张看图"转向"指挥硅基识图军团"，聚焦决策与审核

---

## 2. 用户画像与场景

### 2.1 目标用户
| 角色 | 核心需求 | 使用场景 |
|------|---------|---------|
| **机械设计工程师** | 快速理解陌生专利/外协图纸的结构与标号含义 | 导入专利PDF附图，获取结构化BOM与装配关系 |
| **工艺规划工程师** | 基于图纸结构推断加工工艺、装配顺序 | 图纸解析后自动生成工艺路线建议 |
| **质量检测工程师** | 核对实物与图纸标号一致性，识别设计缺陷 | 上传现场照片与原始图纸比对，Agent自动标号对齐 |
| **知识产权专员** | 批量解析专利附图，提取技术特征与权利要求支撑点 | 批量导入专利族图纸，生成技术特征矩阵 |
| **设备运维工程师** | 根据设备维修图纸快速定位故障部件标号 | 故障代码关联图纸，Agent高亮相关标号区域 |

### 2.2 典型用户旅程
```
工程师上传图纸 → Vision Agent解析标号与结构 → 
Design Agent审查设计合规性 → Process Agent生成工艺建议 → 
Knowledge Agent检索相似案例 → Report Agent输出综合报告 → 
工程师审核确认 → 结论写入企业知识库
```

---

## 3. 系统架构：Multi-Agent协同框架

### 3.1 架构模式：混合式（层级+平等）
采用**混合式架构**：
- **层级维度**：由 Master Scheduler Agent 统一接收任务、拆解子任务、调度各专业Agent
- **平等维度**：各专业Agent之间可基于MCP/A2A协议直接交换中间结果，减少调度瓶颈citeweb_search:10#0

### 3.2 系统架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    用户交互层 (UI/API)                        │
│         Web端 / CAD插件 / 企业微信机器人 / PLM接口            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Master Scheduler Agent (主控调度)               |   
│   • 意图识别 • 任务拆解 • Agent路由 • 结果聚合 • 冲突仲裁       │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌──────────┬──────────┬──────────┬──────────┐
        ↓          ↓          ↓          ↓          ↓
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Vision  │ │  Design  │ │ Process  │ │Knowledge │ │  Report  │
│  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
│(图纸识别) │ │(设计审查) │ │(工艺规划)│ │(知识检索)│ │(报告生成)│
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
        ↑          ↑          ↑          ↑          ↑
        └──────────┴──────────┴──────────┴──────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    工具与数据层                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  图纸识别模型  │ │  企业知识库  │ │  CAD/PLM   │            │
│  │(Qwen3.5-VL  │ │ (Vector DB  │ │   API      │            │
│  │  LoRA微调)  │ │  + Graph DB)│ │            │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Agent角色定义与能力矩阵

### 4.1 Vision Agent (工业图纸视觉解析Agent) — 核心资产
**定位**：系统的"眼睛"，基于用户自研的 Qwen3.5-9B-Instruct LoRA 微调模型
**输入**：工业图纸图像（PNG/PDF/DWG转图）+ 可选的专利背景文本
**输出**：结构化标号映射、空间关系描述、功能原理推理、异常标注

**核心能力**：
| 能力项 | 技术实现 | 评估指标 |
|--------|---------|---------|
| 标号识别 | Qwen3.5-VL LoRA (rank=16/32) + 防捷径学习数据 | ft_strict term_f1 > 0.85 |
| 空间定位 | 视觉COT推理（先布局观察→再标号定位） | spatial_score > 0.70 |
| 功能推理 | 结合专利背景进行结构-功能关联推理 | functional_score > 0.65 |
| 矛盾检测 | 对抗性纠错模式（文本与图像不一致时以图为准） | consistency = 1.0 |
| 多图关联 | 跨图纸标号一致性校验（如图1→图3→图5的标号连续性） | cross_fig_accuracy > 0.90 |

**数据策略**：
- 训练数据：1000条防捷径学习样本（30%纯视觉 + 10%对抗性 + 15%多轮对话 + 35%标准视觉 + 5%反向 + 5%部分线索）
- 测试监控：每轮评估 ft_full / ft_strict 双轨指标，text_dependency_pct 目标 < 25%

### 4.2 Design Agent (设计审查Agent)
**定位**：系统的"设计规范守门员"
**输入**：Vision Agent输出的结构化标号 + 企业设计规范库
**输出**：设计合规性报告、潜在干涉/冲突预警、DFM建议
**能力**：
- 标号命名规范性检查（是否符合企业标准术语库）
- 装配关系逻辑校验（如"输入凸缘"是否确实连接"主动轴"）
- 与历史设计图纸比对，识别异常变更

### 4.3 Process Agent (工艺规划Agent)
**定位**：系统的"工艺大脑"
**输入**：图纸结构描述 + 标号部件清单 + 企业工艺知识库
**输出**：推荐工艺路线、装配顺序、工时估算、工装夹具建议
**能力**：
- 基于标号部件的材质/形态推断加工方法（车/铣/磨/热处理）
- 生成装配树（Assembly Tree）与BOM初稿
- 识别关键尺寸与公差标注缺失

### 4.4 Knowledge Agent (知识检索Agent)
**定位**：系统的"企业记忆库管理员"
**输入**：图纸特征向量 + 标号部件名称
**输出**：相似专利/图纸案例、历史故障记录、供应商信息
**能力**：
- Agentic RAG：基于图纸内容动态检索企业知识库，而非仅依赖关键词citeweb_search:10#8
- 跨模态检索：以图搜图、以标号搜案例、以结构搜专利
- 知识图谱关联：将图纸标号与企业设备台账、备件库、维修记录关联

### 4.5 Report Agent (报告生成Agent)
**定位**：系统的"文档工程师"
**输入**：各Agent的中间结果 + 用户指定的报告模板
**输出**：技术评审报告、专利分析简报、工艺方案书、标号对照表
**能力**：
- 多格式输出：Markdown / Word / PDF / 结构化JSON
- 图表自动生成：标号分布图、装配关系图、对比矩阵
- 结论溯源：每个结论标注来源Agent及置信度

### 4.6 Master Scheduler Agent (主控调度Agent)
**定位**：系统的"项目经理"
**核心职责**：
1. **意图识别**：解析用户query，判断需要激活哪些Agent
2. **任务拆解**：将"分析这张图纸"拆解为 [识图→审查→工艺→检索→报告]
3. **Agent路由**：根据各Agent负载与专长动态分配任务
4. **冲突仲裁**：当Design Agent与Process Agent结论矛盾时，触发对抗辩论机制citeweb_search:10#3
5. **人机协同**：当Agent置信度低于阈值时，自动转人工审核

---

## 5. 核心功能模块

### 5.1 模块一：智能图纸解析引擎
**功能描述**：
- 支持多格式图纸导入：PDF专利附图、CAD导出图、现场拍照图、扫描图纸
- 自动图纸预处理：去噪、纠偏、分辨率归一化（适配模型image_max_pixels）
- 多轮对话式识图：用户可追问"标号7和标号8是什么关系？"，Vision Agent基于图像上下文回答
- 标号高亮与定位：在原始图上用色块高亮已识别标号，生成可视化 overlay

**技术方案**：
- 模型底座：Qwen3.5-9B-Instruct (Vision-Language)
- 微调方式：LoRA (rank=16, alpha=32, target=all, 冻结ViT)
- 推理加速：vLLM / llama.cpp 部署，支持并发请求
- 显存优化：5090单卡32GB，batch推理4张图/次

### 5.2 模块二：跨图纸关联分析
**功能描述**：
- 专利族图纸关联：自动识别同一专利的不同附图（图1剖面图→图3局部平面→图5爆炸图）的标号连续性
- 版本比对：对比同一图纸的V1/V2版本，Agent自动标出新增/删除/变更的标号
- 跨文档标号一致性：检查说明书文字描述与附图标号是否一致（对抗性纠错）

### 5.3 模块三：Agentic RAG 知识增强
**功能描述**：

- 动态检索：Vision Agent识别出"摩擦块/锥形销帽"后，Knowledge Agent自动检索企业内所有含该部件的历史图纸
- 闭环反馈：工程师对Agent识别结果的修正，自动回流为训练数据（需人工审核后入库）
- 多模态知识库：存储图纸图像、标号解析结果、文本描述、三维模型的统一向量表示

### 5.4 模块四：人机协同审核工作台
**功能描述**：
- 低置信度标号人工复核：Vision Agent对置信度<0.8的标号标红，工程师一键确认或修正
- 多Agent结论对比看板：并列展示Vision/Design/Process三Agent的结论，差异项自动高亮
- 一键生成任务单：审核通过的图纸解析结果，可直接推送至PLM/MES系统生成工艺任务单

---

## 6. 数据流与协作流程

### 6.1 标准解析流程
```
用户上传图纸 (PDF/PNG)
    ↓
Master Scheduler 识别任务类型 = "单图深度解析"
    ↓
[并行调度]
    ├─→ Vision Agent: 输出标号JSON + 空间描述 + 功能推理
    ├─→ Knowledge Agent: 检索相似案例（基于图纸特征向量）
    ↓
[串行依赖]
    ├─→ Design Agent: 基于Vision输出进行设计合规审查
    ├─→ Process Agent: 基于Vision+Design输出进行工艺规划
    ↓
Master Scheduler 聚合结果
    ↓
Report Agent: 生成综合技术报告
    ↓
用户审核 → 确认/修正 → 结论入库
```

### 6.2 对抗性纠错流程（专利审核场景）
```
用户上传专利图纸 + 说明书文字
    ↓
Vision Agent: 基于图像独立识别标号（ft_strict模式）
Knowledge Agent: 提取说明书文字中的标号描述
    ↓
Master Scheduler: 对比Vision结果 vs 文字描述
    ↓
若发现不一致（如文字说"2是输出凸缘"，图像判为"主动轴"）
    ↓
触发对抗辩论: Vision Agent与Text Agent各陈述证据
    ↓
人工仲裁: 工程师在UI上查看图像证据与文字证据，一键裁决
    ↓
裁决结果 → 更新企业术语库 + 回流训练数据
```

---

## 7. 技术方案与集成

### 7.1 模型服务层
| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 图纸识别模型 | Qwen3.5-9B-Instruct + LoRA | 自研微调，ft_strict为核心指标 |
| 推理框架 | vLLM + FastAPI | 支持 continuous batching，5090单卡QPS ~8 |
| 多Agent框架 | AutoGen / CrewAI / 自研轻量框架 | 优先AutoGen（微软生态，支持Group Chat）citeweb_search:10#16 |
| Agent通信协议 | MCP (Model Context Protocol) | 标准化工具调用与上下文传递citeweb_search:10#0 |
| 向量数据库 | Milvus / Qdrant | 存储图纸特征向量与标号embedding |
| 图数据库 | Neo4j | 存储标号-部件-设备-故障的知识图谱 |

### 7.2 与现有技术栈对接
用户的现有资产直接嵌入：
- **模型权重**：`saves/qwen3.5-9b-1000/config*-prime` 的 LoRA checkpoint，通过 PEFT 加载为 Vision Agent 后端
- **评估体系**：`IndustrialDrawingEvaluator` 作为 Vision Agent 的在线评估模块，每次推理后实时计算 industrial_overall
- **数据模板**：6种防捷径学习模板作为 Vision Agent 的 system prompt 库，根据任务类型动态切换

### 7.3 部署架构
```
[5090 GPU服务器]
    ├─ vLLM服务 (Qwen3.5-VL + LoRA)  ← Vision Agent核心
    ├─ FastAPI Agent网关
    └─ Redis (Agent状态缓存)
         ↓
[CPU服务器]
    ├─ Master Scheduler (Python/asyncio)
    ├─ Design / Process / Report Agent (LLM调用层)
    ├─ Knowledge Agent (RAG管线: Milvus + Neo4j)
    └─ 企业知识库/PLM接口适配器
```

---

## 8. 评估体系与KPI

### 8.1 Vision Agent 核心指标
| 指标 | 目标值 | 监测方式 |
|------|--------|---------|
| ft_strict industrial_score | > 0.55 (及格) / > 0.70 (优秀) | 每轮训练后eval_dual_track.py |
| ft_full industrial_score | > 0.80 | 同上 |
| text_dependency_pct | < 25% | gap分析 |
| 标号识别semantic_f1 | > 0.90 | IndustrialDrawingEvaluator |
| 空间推理spatial_score | > 0.70 | 同上 |
| 推理一致性consistency | = 1.0 | 同上 |

### 8.2 系统级KPI
| KPI | 目标 | 说明 |
|-----|------|------|
| 单图端到端解析耗时 | < 30秒 | 从上传到报告生成 |
| Agent协同任务成功率 | > 95% | Master调度无崩溃、无死锁 |
| 人工复核率 | < 15% | 低置信度标号占比 |
| 知识检索准确率 | > 88% | Top-3召回率 |
| 用户满意度 (NPS) | > 50 | 工程师月度调研 |

---

## 9. 里程碑与路线图

### Phase 1: MVP (0-2个月)
- [ ] Vision Agent 服务化部署（vLLM + FastAPI）
- [ ] Master Scheduler + Report Agent 基础链路打通
- [ ] Web端单图上传 → 标号识别 → 结构化JSON输出
- [ ] ft_strict 突破 0.40

### Phase 2: 协同增强 (2-4个月)
- [ ] 接入 Design Agent（设计规范审查）
- [ ] 接入 Knowledge Agent（Agentic RAG检索）
- [ ] 多轮对话式追问功能上线
- [ ] ft_strict 突破 0.55，text_dependency < 30%

### Phase 3: 企业集成 (4-6个月)
- [ ] PLM/MES系统API对接（西门子Teamcenter / 达索ENOVIA / 国产PLM）
- [ ] CAD插件（SolidWorks / AutoCAD / 中望CAD）
- [ ] 批量图纸解析队列（支持1000+图纸 overnight 处理）
- [ ] ft_strict 突破 0.65，text_dependency < 20%

### Phase 4: 生态扩展 (6-12个月)
- [ ] Process Agent 工艺规划能力上线（与CAM系统联动）
- [ ] 跨图纸版本比对与专利族分析
- [ ] 开放Agent API，支持第三方Agent接入（供应商Agent、成本Agent）
- [ ] 数字孪生对接：图纸解析结果直接驱动三维模型生成

---

## 10. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Vision Agent 视觉能力不足 | 系统根基动摇 | 持续投入防捷径学习数据建设，保持ft_strict监控，低于0.4则冻结功能升级 |
| 多Agent协调开销过高 | 响应延迟、Token成本飙升 | 采用层级式调度为主，仅在冲突时触发平等协商；设置Agent调用预算上限 |
| 企业数据安全顾虑 | 图纸涉密，无法上云 | 全私有化部署，5090本地服务器，数据不出厂区 |
| PLM系统对接复杂 | 集成周期长 | 优先支持REST API通用接口，提供标准化中间件适配器 |
| 工程师抵触AI替代 | 采纳率低 | 定位为"硅基实习生"而非替代者，强调人机协同与决策权保留 |

---

## 11. 附录

### 11.1 术语表
- **ft_full**: 含完整文本提示的图纸识别评估模式
- **ft_strict**: 仅图像、零文本提示的严格视觉评估模式
- **Agentic RAG**: 智能体驱动的动态检索增强生成，区别于传统被动RAG
- **MCP**: Model Context Protocol，Anthropic提出的模型上下文协议，用于Agent与工具标准化通信

### 11.2 参考文档
- 《中国企业智能体2026六大预判》— 零一万物
- 用户自研：《Industrial Drawing Evaluator 评估脚本》
- 用户自研：《防捷径学习数据模板集（6种）》
- LLaMA-Factory Qwen3.5-VL LoRA 微调配置指南

---

**文档结束**




---

## 12. Vision Agent API 接口规范 (OpenAPI 3.0)

### 12.1 服务概述
Vision Agent 以独立微服务形式部署，对外暴露 RESTful API 与 SSE (Server-Sent Events) 流式接口。服务底座为 vLLM + FastAPI，单张 5090 承载 Qwen3.5-9B-Instruct + LoRA (rank=16)。

**服务基地址**: `http://vision-agent:8000`  
**协议**: HTTP/1.1 (REST) + SSE (Stream)  
**认证**: Bearer Token (企业内部 JWT)  
**并发限制**: 单卡 batch=4，最大并发请求 8（超出排队）

### 12.2 接口清单

#### 12.2.1 单图深度解析 (同步)
```yaml
POST /v1/vision/parse
Content-Type: application/json
Authorization: Bearer <jwt>
```

**Request Body:**
```json
{
  "image_url": "s3://drawings/CN1007281B/fig3.png",
  "image_base64": null,
  "prompt_mode": "standard_visual",
  "question": "请识别图中标记为2、3、4、7、8、9、15、16、S的部件名称，并解释径向狭槽S的作用。",
  "background": "专利CN1007281B涉及一种采矿机传动机构...",
  "figure_description": "图3为摩擦环区域局部平面图...",
  "output_format": "structured",
  "max_new_tokens": 2048,
  "temperature": 0.1,
  "stream": false
}
```

**字段说明:**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | string | 二选一 | 图纸对象存储地址，支持 s3:// / file:// / http:// |
| `image_base64` | string | 二选一 | Base64编码图像，用于前端直传小图 |
| `prompt_mode` | enum | 是 | `standard_visual` / `pure_vision` / `adversarial` / `multiturn` / `reverse` |
| `question` | string | 是 | 用户问题 |
| `background` | string | 否 | 专利背景文本（prompt_mode=standard时生效） |
| `figure_description` | string | 否 | 附图说明（会被系统过滤掉标号-名称映射，防作弊） |
| `output_format` | enum | 否 | `text` / `structured` / `json_only` |
| `temperature` | float | 否 | 评估时固定 0.1，生产环境可调至 0.3~0.7 |

**Response (200 OK):**
```json
{
  "request_id": "va-20260522-7f3a9b",
  "status": "success",
  "model": "qwen3.5-9b-instruct-drawing-lora",
  "checkpoint": "configC-prime-step-1200",
  "inference_time_ms": 2840,
  "result": {
    "raw_text": "**第一步：图纸整体布局观察**...",
    "structured": {
      "labels": {
        "2": {"name": "主动轴", "location": "图纸最下方", "confidence": 0.94},
        "3": {"name": "输出凸缘", "location": "图纸最上方", "confidence": 0.91},
        "4": {"name": "输入凸缘", "location": "图纸中部", "confidence": 0.89},
        "7": {"name": "啮合销", "location": "中部轴向", "confidence": 0.93},
        "8": {"name": "摩擦块/锥形销帽", "location": "啮合销7上下两端", "confidence": 0.87},
        "9": {"name": "定心环", "location": "输入凸缘4内侧下方", "confidence": 0.85},
        "15": {"name": "输入边摩擦环", "location": "下方圆形轨迹", "confidence": 0.92},
        "16": {"name": "输入边摩擦环", "location": "上方邻近圆形轨迹", "confidence": 0.90},
        "S": {"name": "径向狭槽", "location": "摩擦块旋转方向", "confidence": 0.88}
      },
      "slot_s_function": "建立油楔，过载时油滑行减小峰值应力",
      "comparison_table": {
        "input_side": "完整圆形摩擦块，位于两个邻近轨迹内",
        "output_side": "分为3-4个摩擦块，底部嵌入支撑凹座"
      }
    },
    "cot_summary": {
      "layout_observation": "纵向布局，下方轴状→中部凸缘→上方输出",
      "spatial_reasoning": "2在下/3在上/4在中/7轴向/8块状",
      "functional_reasoning": "S为旋转方向狭槽，用于油楔建立"
    }
  },
  "eval_metrics": {
    "ft_full_score": null,
    "ft_strict_score": null,
    "consistency": 1.0
  }
}
```

**错误响应:**
```json
{
  "request_id": "va-20260522-7f3a9b",
  "status": "error",
  "error_code": "VISION_OOM",
  "message": "图像分辨率过高导致显存溢出，建议 image_max_pixels <= 262144",
  "suggestion": "请压缩图像至 512x512 以下重新提交"
}
```

#### 12.2.2 流式解析 (SSE)
```yaml
POST /v1/vision/parse/stream
Content-Type: application/json
Accept: text/event-stream
```

**Request Body:** 同 `/parse`，但 `stream: true` 固定

**SSE 事件流:**
```
event: start
data: {"request_id": "va-20260522-7f3a9b", "status": "processing"}

event: cot_step
data: {"step": 1, "type": "layout_observation", "content": "图纸呈纵向布局..."}

event: cot_step
data: {"step": 2, "type": "label_identification", "content": "标号2位于最下方，判断为主动轴..."}

event: result
data: {"structured": {"labels": {"2": {"name": "主动轴", "confidence": 0.94}}, ...}}

event: done
data: {"inference_time_ms": 2840, "total_tokens": 1567}
```

**用途**: 前端实时展示 COT 推理过程，提升用户信任感。

#### 12.2.3 双轨评估 (ft_full / ft_strict)
```yaml
POST /v1/vision/evaluate
Content-Type: application/json
```

**Request Body:**
```json
{
  "image_url": "s3://drawings/CN1007281B/fig3.png",
  "reference": "标准答案文本...",
  "background": "专利背景...",
  "figure_description": "附图说明...",
  "question": "请识别..."
}
```

**Response:**
```json
{
  "request_id": "va-eval-20260522-7f3a9b",
  "ft_full": {
    "prediction": "...",
    "industrial_score": 0.8234,
    "term_f1": 0.8912,
    "reasoning": 0.7567
  },
  "ft_strict": {
    "prediction": "...",
    "industrial_score": 0.4211,
    "term_f1": 0.5234,
    "reasoning": 0.3890
  },
  "gap_analysis": {
    "absolute_gap": 0.4023,
    "text_dependency_pct": 48.86,
    "visual_ability_pct": 51.14,
    "verdict": "CRITICAL"
  }
}
```

**用途**: 内部模型监控、CI/CD 自动化测试、训练数据质量 gate。

#### 12.2.4 批量异步解析
```yaml
POST /v1/vision/batch
Content-Type: application/json
```

**Request Body:**
```json
{
  "job_name": "patent_family_CN1007281B",
  "items": [
    {"image_url": ".../fig1.png", "question": "..."},
    {"image_url": ".../fig3.png", "question": "..."},
    {"image_url": ".../fig5.png", "question": "..."}
  ],
  "callback_url": "http://master-scheduler:8080/callback/vision"
}
```

**Response:**
```json
{
  "job_id": "batch-20260522-abc123",
  "status": "queued",
  "estimated_seconds": 45,
  "queue_position": 3
}
```

**回调 Payload:**
```json
{
  "job_id": "batch-20260522-abc123",
  "status": "completed",
  "results": [
    {"image_url": ".../fig1.png", "structured": {...}, "inference_time_ms": 2840},
    {"image_url": ".../fig3.png", "structured": {...}, "inference_time_ms": 3120}
  ]
}
```

#### 12.2.5 模型健康与指标
```yaml
GET /v1/vision/health
GET /v1/vision/metrics
```

**Response (/metrics):**
```json
{
  "model": "qwen3.5-9b-instruct-drawing-lora",
  "checkpoint_loaded": "configC-prime-step-1200",
  "gpu_utilization": 0.87,
  "gpu_memory_used_gb": 28.4,
  "gpu_memory_total_gb": 32.0,
  "avg_inference_time_ms": 2840,
  "qps": 1.4,
  "ft_strict_rolling_avg": 0.578,
  "text_dependency_rolling_avg": 0.329,
  "last_eval_time": "2026-05-22T14:30:00Z"
}
```

### 12.3 调用示例 (Python)

```python
import requests

# 单图解析
resp = requests.post(
    "http://vision-agent:8000/v1/vision/parse",
    headers={"Authorization": "Bearer <jwt>"},
    json={
        "image_url": "s3://drawings/CN1007281B/fig3.png",
        "prompt_mode": "standard_visual",
        "question": "请识别图中标记为2、3、4、7、8、9、15、16、S的部件名称",
        "background": "专利CN1007281B涉及采矿机传动机构...",
        "output_format": "structured"
    },
    timeout=60
)
result = resp.json()["result"]["structured"]
print(result["labels"]["2"]["name"])  # 主动轴

# 双轨评估（监控模型健康）
eval_resp = requests.post(
    "http://vision-agent:8000/v1/vision/evaluate",
    headers={"Authorization": "Bearer <jwt>"},
    json={
        "image_url": "s3://drawings/test/fig3.png",
        "reference": "标准答案...",
        "background": "...",
        "question": "..."
    }
)
metrics = eval_resp.json()["gap_analysis"]
if metrics["verdict"] == "CRITICAL":
    alert_engineer("模型严重依赖文本，需检查数据质量")
```

---

## 13. Master Scheduler Agent 技术实现

### 13.1 架构定位
Master Scheduler 是系统的"项目经理"，负责：
1. **意图识别 (Intent Recognition)**：解析用户 query，映射为任务类型
2. **任务拆解 (Task Decomposition)**：将复合任务拆分为可并行/串行的子任务
3. **Agent 路由 (Agent Routing)**：根据子任务类型与 Agent 负载选择执行者
4. **冲突仲裁 (Conflict Arbitration)**：当多 Agent 结论矛盾时，触发对抗辩论或人工介入
5. **结果聚合 (Result Aggregation)**：将多 Agent 输出整合为统一响应

### 13.2 状态机与流程图

```
┌─────────────┐
│   Start     │
└──────┬──────┘
       ↓
┌─────────────────┐
│ 意图识别模块     │ ← LLM + 规则引擎
│ (Intent Classifier)
└────────┬────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
┌───────┐ ┌─────────┐
│单图解析 │ │批量解析  │
│(Type A)│ │(Type B) │
└───┬───┘ └────┬────┘
    ↓          ↓
┌─────────────────┐
│   任务拆解 DAG   │ ← 有向无环图
│ (Task DAG Builder)
└────────┬────────┘
         ↓
┌─────────────────┐
│   Agent 调度器   │ ← 负载均衡 + 专长匹配
│ (Agent Dispatcher)
└────────┬────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
┌───────┐ ┌─────────┐
│并行执行 │ │串行执行  │
└───┬───┘ └────┬────┘
    ↓          ↓
┌─────────────────┐
│   结果收集器     │
│ (Result Collector)
└────────┬────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
┌───────┐ ┌─────────┐
│无冲突   │ │有冲突    │
└───┬───┘ └────┬────┘
    ↓          ↓
┌───────┐ ┌─────────┐
│Report  │ │冲突仲裁   │
│Agent   │ │(对抗辩论) │
└───┬───┘ └────┬────┘
    ↓          ↓
┌─────────────────┐
│    输出/回调     │
└─────────────────┘
```

### 13.3 核心模块伪代码

#### 13.3.1 意图识别 (Intent Recognition)
```python
class IntentRecognizer:
    """
    基于规则 + 轻量LLM的意图识别器
    输入: 用户原始 query + 附件类型
    输出: 任务类型 + 置信度 + 所需Agent列表
    """

    INTENT_RULES = {
        "single_parse": {
            "patterns": ["识别.*图", "解析.*标号", "看图.*是什么", "分析.*图纸"],
            "required_agents": ["Vision", "Report"],
            "optional_agents": ["Design", "Process"]
        },
        "batch_parse": {
            "patterns": ["批量.*图纸", "全部.*解析", " patent family", "专利族.*分析"],
            "required_agents": ["Vision", "Knowledge", "Report"],
            "max_parallel": 4
        },
        "design_review": {
            "patterns": ["审查.*设计", "合规.*检查", "DFM.*分析"],
            "required_agents": ["Vision", "Design", "Report"],
            "dependency": {"Design": ["Vision"]}  # Design依赖Vision输出
        },
        "process_planning": {
            "patterns": ["工艺.*规划", "生成.*BOM", "装配.*顺序"],
            "required_agents": ["Vision", "Process", "Report"],
            "dependency": {"Process": ["Vision"]}
        },
        "knowledge_query": {
            "patterns": ["查找.*类似", "历史.*案例", "故障.*记录"],
            "required_agents": ["Vision", "Knowledge", "Report"],
            "dependency": {"Knowledge": ["Vision"]}
        },
        "adversarial_audit": {
            "patterns": ["审核.*附图", "纠错.*标号", "文字.*图像.*不一致"],
            "required_agents": ["Vision", "Knowledge", "Report"],
            "trigger_debate": True
        }
    }

    def recognize(self, query: str, attachments: List[str]) -> Intent:
        # 第一层：规则匹配（O(1) 快速过滤）
        for intent_type, config in self.INTENT_RULES.items():
            if any(re.search(p, query) for p in config["patterns"]):
                return Intent(
                    type=intent_type,
                    confidence=0.95,
                    agents=config["required_agents"],
                    dependencies=config.get("dependency", {}),
                    trigger_debate=config.get("trigger_debate", False)
                )

        # 第二层：LLM兜底（复杂query或规则未命中）
        prompt = f"""请判断以下用户请求属于哪种任务类型：
        可选类型：单图解析、批量解析、设计审查、工艺规划、知识查询、对抗审核
        用户请求：{query}
        附件类型：{attachments}
        只输出JSON：{{"type":"...", "confidence":0.x}}"""

        llm_result = self.llm.generate(prompt)
        return Intent.parse(llm_result)
```

#### 13.3.2 任务拆解 DAG 构建
```python
class TaskDAGBuilder:
    """
    将意图拆解为可执行的有向无环图（DAG）
    节点 = 子任务，边 = 依赖关系
    """

    def build(self, intent: Intent, user_input: UserInput) -> TaskDAG:
        dag = TaskDAG()

        # 根节点：图像预处理
        root = dag.add_node(Task(
            id="T0",
            name="image_preprocessing",
            agent="Vision",
            action="preprocess",
            input={"image": user_input.image},
            output_schema=["normalized_image", "resolution", "format"]
        ))

        # 第一层：Vision Agent 解析（所有任务的基础）
        vision_task = dag.add_node(Task(
            id="T1",
            name="vision_parse",
            agent="Vision",
            action="parse",
            input={"image": root.output["normalized_image"], "prompt_mode": intent.prompt_mode},
            dependencies=[root],
            timeout_sec=30,
            retry=2
        ))

        # 第二层：根据意图并行/串行扩展
        if intent.type == "design_review":
            design_task = dag.add_node(Task(
                id="T2",
                name="design_compliance_check",
                agent="Design",
                action="review",
                input={"vision_result": vision_task.output, "standards": "enterprise_design_db"},
                dependencies=[vision_task],
                timeout_sec=20
            ))
            report_task = dag.add_node(Task(
                id="T3",
                name="generate_review_report",
                agent="Report",
                action="generate",
                input={"sources": [vision_task.output, design_task.output], "template": "design_review"},
                dependencies=[vision_task, design_task]
            ))

        elif intent.type == "process_planning":
            process_task = dag.add_node(Task(
                id="T2",
                name="process_planning",
                agent="Process",
                action="plan",
                input={"vision_result": vision_task.output, "material_db": "enterprise_materials"},
                dependencies=[vision_task]
            ))
            report_task = dag.add_node(Task(
                id="T3",
                name="generate_process_report",
                agent="Report",
                action="generate",
                input={"sources": [vision_task.output, process_task.output], "template": "process_plan"},
                dependencies=[vision_task, process_task]
            ))

        elif intent.type == "adversarial_audit":
            # 对抗性任务：Vision 与 Text 并行，结果对比
            text_task = dag.add_node(Task(
                id="T2_text",
                name="text_extraction",
                agent="Knowledge",
                action="extract_text_labels",
                input={"document": user_input.attached_pdf},
                dependencies=[root]
            ))

            compare_task = dag.add_node(Task(
                id="T3",
                name="conflict_detection",
                agent="Master",
                action="compare",
                input={"vision_labels": vision_task.output, "text_labels": text_task.output},
                dependencies=[vision_task, text_task]
            ))

            # 若发现冲突，触发对抗辩论子DAG
            if compare_task.output["has_conflict"]:
                debate_dag = self._build_debate_dag(compare_task.output["conflicts"])
                dag.merge(debate_dag)

        return dag

    def _build_debate_dag(self, conflicts: List[Conflict]) -> TaskDAG:
        """构建对抗辩论子DAG"""
        debate_dag = TaskDAG()

        # Agent A (Vision 辩护方): 基于图像证据辩护
        defender = debate_dag.add_node(Task(
            id="D1",
            name="vision_defense",
            agent="Vision",
            action="defend",
            input={"conflict": conflicts, "evidence_type": "visual"}
        ))

        # Agent B (Text 辩护方): 基于文本/规范辩护
        challenger = debate_dag.add_node(Task(
            id="D2",
            name="text_challenge",
            agent="Knowledge",
            action="challenge",
            input={"conflict": conflicts, "evidence_type": "textual"}
        ))

        # 仲裁节点：综合双方证据，输出裁决建议
        judge = debate_dag.add_node(Task(
            id="D3",
            name="arbitration",
            agent="Master",
            action="arbitrate",
            input={"defense": defender.output, "challenge": challenger.output},
            dependencies=[defender, challenger]
        ))

        return debate_dag
```

#### 13.3.3 Agent 调度器 (Dispatcher)
```python
class AgentDispatcher:
    """
    基于负载与专长的动态调度器
    """

    def __init__(self):
        self.agent_pools = {
            "Vision": AgentPool(backend="vllm", max_concurrent=4, gpu="5090"),
            "Design": AgentPool(backend="openai-api", max_concurrent=10, model="gpt-4o"),
            "Process": AgentPool(backend="openai-api", max_concurrent=10, model="gpt-4o"),
            "Knowledge": AgentPool(backend="rag-pipeline", max_concurrent=5),
            "Report": AgentPool(backend="openai-api", max_concurrent=8, model="gpt-4o")
        }

    def dispatch(self, dag: TaskDAG) -> ExecutionPlan:
        plan = ExecutionPlan()

        # 拓扑排序，确定执行顺序
        sorted_tasks = dag.topological_sort()

        for task in sorted_tasks:
            agent_type = task.agent
            pool = self.agent_pools[agent_type]

            # 等待依赖完成
            if task.dependencies:
                plan.add_wait_condition(task.id, [d.id for d in task.dependencies])

            # 负载均衡：选择当前负载最低的实例
            instance = pool.select_least_loaded()

            # 超时与重试策略
            execution = ExecutionUnit(
                task=task,
                agent_instance=instance,
                timeout_sec=task.timeout_sec,
                retry_policy=RetryPolicy(max_retry=task.retry, backoff="exponential")
            )
            plan.add_unit(execution)

        return plan

    async def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        results = {}

        async with asyncio.TaskGroup() as tg:
            for unit in plan.parallelizable_units():
                tg.create_task(self._run_unit(unit, results))

        return results
```

#### 13.3.4 冲突仲裁与对抗辩论
```python
class ConflictArbitrator:
    """
    当多Agent结论矛盾时，触发对抗辩论机制
    灵感来源：三菱电机对抗辩论型Multi-Agent AI
    """

    THRESHOLD_CONFIDENCE_GAP = 0.15  # 置信度差距超过15%触发辩论
    THRESHOLD_CONTENT_CONTRADICTION = 0.30  # 内容矛盾度（基于embedding相似度）

    def detect_conflicts(self, agent_outputs: Dict[str, AgentOutput]) -> List[Conflict]:
        conflicts = []
        labels = defaultdict(list)

        # 收集所有Agent对同一标号的识别结果
        for agent_name, output in agent_outputs.items():
            for label_id, label_info in output.labels.items():
                labels[label_id].append({
                    "agent": agent_name,
                    "name": label_info["name"],
                    "confidence": label_info.get("confidence", 0.5),
                    "evidence": label_info.get("evidence", "")
                })

        # 检测冲突
        for label_id, predictions in labels.items():
            if len(predictions) < 2:
                continue

            names = [p["name"] for p in predictions]
            confidences = [p["confidence"] for p in predictions]

            # 判断1：名称不一致
            if len(set(names)) > 1:
                max_conf = max(confidences)
                min_conf = min(confidences)
                if max_conf - min_conf > self.THRESHOLD_CONFIDENCE_GAP:
                    conflicts.append(Conflict(
                        label_id=label_id,
                        type="naming_dispute",
                        predictions=predictions,
                        severity="high" if max_conf - min_conf > 0.3 else "medium"
                    ))

            # 判断2：空间位置描述矛盾（通过语义相似度）
            # ...

        return conflicts

    async def run_debate(self, conflict: Conflict) -> DebateResult:
        """
        组织对抗辩论，各Agent陈述证据
        """
        debate_rounds = []

        for round_num in range(1, 4):  # 最多3轮
            round_statements = []

            for pred in conflict.predictions:
                agent = self.get_agent(pred["agent"])

                # 构造辩护/挑战 prompt
                if round_num == 1:
                    prompt = f"请基于你的分析证据，论证为什么标号{conflict.label_id}是'{pred['name']}'。必须引用图像/文本中的具体特征。"
                else:
                    # 后续轮次：回应对方观点
                    opponent = [p for p in conflict.predictions if p["agent"] != pred["agent"]][0]
                    prompt = f"对方认为标号{conflict.label_id}是'{opponent['name']}'。请反驳并强化你的论据。"

                statement = await agent.defend(prompt)
                round_statements.append({
                    "agent": pred["agent"],
                    "statement": statement,
                    "confidence": pred["confidence"]
                })

            debate_rounds.append({"round": round_num, "statements": round_statements})

            # 若某一方置信度显著下降，提前终止
            if self._check_convergence(round_statements):
                break

        # 综合裁决：优先采信置信度高且证据充分的Agent
        winner = max(debate_rounds[-1]["statements"], key=lambda x: x["confidence"])

        return DebateResult(
            conflict=conflict,
            winner=winner["agent"],
            final_answer=winner["statement"],
            rounds=debate_rounds,
            needs_human_review=conflict.severity == "high"
        )
```

### 13.5 Master Scheduler 部署配置

```yaml
# master_scheduler.yaml
master_scheduler:
  # 意图识别
  intent_recognition:
    mode: "hybrid"  # rule + llm_fallback
    llm_model: "gpt-4o-mini"  # 轻量模型即可
    cache_ttl_sec: 300

  # 任务执行
  execution:
    max_parallel_tasks: 8
    default_timeout_sec: 60
    retry_policy:
      max_retry: 2
      backoff_base: 2.0

  # 冲突仲裁
  arbitration:
    enabled: true
    debate_max_rounds: 3
    auto_resolve_threshold: 0.85  # 置信度>85%自动裁决，否则转人工
    human_review_queue: "redis://redis:6379/0"

  # 状态持久化
  state_store:
    type: "redis"
    ttl_hours: 24

  # 监控
  metrics:
    export_interval_sec: 15
    endpoints:
      - "prometheus:9090"
```

---

## 14. 企业PLM/MES适配器中间件方案

### 14.1 对接目标系统
| 系统类型 | 代表产品 | 对接优先级 | 技术难点 |
|---------|---------|-----------|---------|
| **PLM (产品生命周期管理)** | 西门子 Teamcenter、达索 ENOVIA、PTC Windchill、国产天喻IntePLM | P0 | 图纸版本管理、BOM同步、权限体系复杂 |
| **MES (制造执行系统)** | 西门子 Opcenter、SAP ME、鼎捷、赛意 | P1 | 工艺路线下发、工单关联、实时性要求高 |
| **CAD (设计软件)** | SolidWorks、AutoCAD、CATIA、中望CAD、浩辰CAD | P0 | 插件开发、图纸格式转换、实时标注回写 |
| **ERP (企业资源计划)** | SAP、Oracle、用友、金蝶 | P2 | 物料主数据同步、成本核算 |
| **QMS (质量管理系统)** | 国产QMS、西门子QMS | P1 | 检验标准关联、不合格品追溯 |

### 14.2 适配器架构：抽象层 + 驱动层

```
┌─────────────────────────────────────────────────────────────┐
│                    IDMAS 核心平台                             │
│              (Vision Agent / Master Scheduler)                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Enterprise Adapter Gateway                       │
│         (统一抽象层：REST API + 消息队列 + 数据转换)            │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│   │  协议适配器   │ │  数据转换器  │ │  事件总线   │           │
│   │ (SOAP/REST/ │ │ (BOM/图纸/  │ │ (Kafka/     │           │
│   │  OPC UA/     │ │  工艺/标号)  │ │  RabbitMQ)  │           │
│   │  WebSocket)  │ │             │ │             │           │
│   └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
         ↓              ↓              ↓              ↓
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Teamcenter│ │  ENOVIA  │ │  国产PLM │ │   MES    │
   │  Adapter  │ │  Adapter │ │  Adapter │ │  Adapter │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 14.3 核心适配器设计

#### 14.3.1 抽象数据模型 (Canonical Model)
所有外部系统的数据在进入IDMAS前，必须转换为统一抽象模型：

```python
class DrawingDocument:
    """图纸文档抽象模型"""
    doc_id: str                    # 统一ID (UUID)
    source_system: str             # 来源系统 (teamcenter/enovia/inteplm)
    source_doc_id: str             # 源系统原始ID
    version: str                   # 版本号 (遵循源系统规则)
    title: str
    drawing_type: Enum             # mechanical / electrical / hydraulic / patent
    file_format: Enum              # pdf / dwg / dxf / png / tiff
    image_urls: List[str]          # 转换后的标准图像地址
    native_file_url: str           # 原始文件地址
    bom_items: List[BOMItem]       # 结构化BOM项
    labels: List[DrawingLabel]     # 标号列表 (来自Vision Agent)
    metadata: DrawingMeta          # 创建者、审核状态、密级等
    lifecycle_state: str           # 设计/审核/发布/归档
    acl: AccessControlList         # 权限控制

class DrawingLabel:
    """图纸标号抽象模型"""
    label_id: str                  # 标号字符串 (如 "2", "S", "15")
    label_type: Enum               # number / letter / symbol
    name: str                      # 部件名称
    name_synonyms: List[str]       # 同义词 (用于检索)
    spatial: SpatialInfo           # 空间位置描述
    confidence: float              # Vision Agent置信度
    verified_by: str               # 人工审核者 (null=未审核)
    source: Enum                   # vision_agent / manual / legacy_system
    related_bom_id: str            # 关联BOM项ID

class BOMItem:
    """BOM项抽象模型"""
    item_id: str
    parent_id: Optional[str]       # 父项ID (装配树)
    drawing_label_id: str          # 关联图纸标号
    part_name: str
    material: str
    quantity: int
    unit: str
    process_route: Optional[ProcessRoute]
```

#### 14.3.2 西门子 Teamcenter 适配器

```python
class TeamcenterAdapter(EnterpriseAdapter):
    """
    Teamcenter 适配器
    基于 SOA 客户端 (Java/.NET) 或 REST API (Active Workspace)
    """

    def __init__(self, config: TeamcenterConfig):
        self.client = TeamcenterSOAClient(
            host=config.host,
            port=config.port,
            username=config.service_account,
            password=config.service_password
        )
        self.session = None

    def authenticate(self) -> str:
        """建立SOA会话"""
        self.session = self.client.login(
            credentials={"username": self.username, "password": self.password},
            group=config.group,
            role=config.role
        )
        return self.session.token

    def fetch_drawing(self, item_id: str, revision: str) -> DrawingDocument:
        """从Teamcenter获取图纸及元数据"""
        # 1. 查询 ItemRevision
        item_rev = self.client.query_item_revision(item_id, revision)

        # 2. 获取关联数据集 (Dataset)
        datasets = self.client.get_datasets(item_rev.uid, type="PDF|DirectModel")

        # 3. 下载文件到临时存储
        file_path = self.client.download_dataset(datasets[0].uid, local_dir="/tmp/tc_files")

        # 4. 转换为标准图像 (PDF→PNG)
        image_urls = self._convert_to_images(file_path, dpi=300)

        # 5. 提取BOM (PSConnection)
        ps_bom = self.client.get_precise_bom(item_rev.uid)
        bom_items = [self._convert_bom_line(line) for line in ps_bom.lines]

        # 6. 组装抽象模型
        return DrawingDocument(
            doc_id=generate_uuid(),
            source_system="teamcenter",
            source_doc_id=item_id,
            version=revision,
            title=item_rev.name,
            image_urls=image_urls,
            bom_items=bom_items,
            metadata=self._extract_metadata(item_rev),
            lifecycle_state=item_rev.release_status
        )

    def writeback_labels(self, doc_id: str, labels: List[DrawingLabel]) -> bool:
        """
        将Vision Agent识别结果回写至Teamcenter
        回写方式：创建 Named Reference 或更新 ItemRevision 属性
        """
        item_rev = self.client.query_item_revision_by_external_id(doc_id)

        # 方式1：写入 ItemRevision 的自定义属性 (IMAN_attr)
        label_json = json.dumps([l.dict() for l in labels])
        self.client.set_property(
            item_rev.uid,
            property_name="idmas_vision_labels",
            value=label_json,
            type="string"
        )

        # 方式2：创建新的 Dataset (JSON格式)，与图纸关联
        dataset = self.client.create_dataset(
            parent=item_rev.uid,
            name="IDMAS_Vision_Analysis",
            type="Text",
            file_content=label_json
        )

        # 方式3：触发 Workflow (若图纸处于审核中，自动推送解析结果给审核人)
        if item_rev.workflow_state == "In Review":
            self.client.add_workflow_comment(
                item_rev.workflow_uid,
                comment=f"AI识图完成：共识别 {len(labels)} 个标号，置信度均值 {avg_conf(labels):.2f}",
                attachments=[dataset.uid]
            )

        return True

    def subscribe_events(self, callback_url: str):
        """订阅Teamcenter事件 (图纸发布、版本变更)"""
        self.client.subscribe_events(
            event_types=["ITEM_RELEASED", "ITEM_REVISION_CREATED", "DATASET_MODIFIED"],
            callback=callback_url,
            filter={"item_types": ["Drawing", "Part"]}
        )
```

#### 14.3.3 达索 ENOVIA 适配器

```python
class EnoviaAdapter(EnterpriseAdapter):
    """
    达索 ENOVIA (3DEXPERIENCE Platform) 适配器
    基于 REST API (MQL/REST) 或 Java EKL 脚本
    """

    def __init__(self, config: EnoviaConfig):
        self.client = EnoviaRESTClient(
            platform_url=config.platform_url,
            tenant=config.tenant,
            passport=config.passport_credentials  # 3DPassport认证
        )

    def fetch_drawing(self, physical_id: str) -> DrawingDocument:
        """通过物理ID获取图纸"""
        # ENOVIA 使用 Physical ID 作为唯一标识
        bus_object = self.client.query_bus(
            type="Drawing Print",
            name="*",
            revision="*",
            where_clause=f"physicalid=='{physical_id}'"
        )

        # 获取文件 (Check Out + Download)
        file_info = self.client.download_file(
            object_id=bus_object.id,
            format="generic",
            store_path="/tmp/enovia_files"
        )

        # ENOVIA 的 BOM 通过 EBOM 或 MBOM 查询
        ebom = self.client.get_ebom(parent_id=bus_object.id, level=3)

        return DrawingDocument(
            source_system="enovia",
            source_doc_id=physical_id,
            # ...
        )

    def writeback_labels(self, doc_id: str, labels: List[DrawingLabel]):
        """回写至 ENOVIA 的 Experience"""
        # 在 ENOVIA 中创建自定义 Experience (Widget)
        # 或通过 MQL 更新属性
        self.client.modify_bus(
            object_id=doc_id,
            attributes={
                "IDMAS_Labels": json.dumps([l.dict() for l in labels]),
                "IDMAS_AnalysisDate": datetime.now().isoformat(),
                "IDMAS_ModelVersion": "qwen3.5-drawing-lora-v2.1"
            }
        )
```

#### 14.3.4 国产PLM适配器 (以天喻IntePLM为例)

```python
class IntePLMAdapter(EnterpriseAdapter):
    """
    国产PLM适配器 (天喻IntePLM / 金蝶PLM / 用友PLM)
    通常提供标准REST API或数据库直连
    """

    def __init__(self, config: IntePLMConfig):
        self.api = IntePLMOpenAPI(
            base_url=config.base_url,
            app_key=config.app_key,
            app_secret=config.app_secret
        )

    def fetch_drawing(self, doc_code: str, version: str) -> DrawingDocument:
        """通过文档编码获取图纸"""
        doc = self.api.get_document(code=doc_code, version=version)

        # 获取文件流
        file_stream = self.api.download_file(file_id=doc.main_file_id)
        image_urls = self._convert_stream_to_images(file_stream)

        # 获取产品结构 (Product Structure)
        structure = self.api.get_product_structure(doc.product_id)

        return DrawingDocument(
            source_system="inteplm",
            source_doc_id=doc_code,
            version=version,
            image_urls=image_urls,
            # ...
        )
```

#### 14.3.5 CAD插件适配器 (SolidWorks / 中望CAD)

```python
class CADPluginAdapter:
    """
    CAD插件不是传统适配器，而是嵌入CAD进程的DLL/JS插件
    通过COM API (Windows) 或 JS API (跨平台) 与IDMAS通信
    """

    def __init__(self, cad_type: str):
        self.cad_type = cad_type  # solidworks / zwcad / autocad
        self.api_url = "http://idmas-gateway:8080/api/v1"

    def on_drawing_open(self, drawing_path: str):
        """当用户在CAD中打开图纸时触发"""
        # 1. 提取当前图纸的缩略图
        thumbnail = self._capture_viewport()

        # 2. 调用 Vision Agent 解析
        resp = requests.post(
            f"{self.api_url}/vision/parse",
            json={
                "image_base64": thumbnail,
                "prompt_mode": "standard_visual",
                "question": "请识别当前图纸中的所有标号"
            }
        )
        labels = resp.json()["result"]["structured"]["labels"]

        # 3. 在CAD视图上高亮标号 (Overlay)
        for label_id, info in labels.items():
            # 通过CAD API在对应位置绘制高亮框和标注
            self._draw_highlight_box(
                position=self._estimate_position(label_id),  # 或通过OCR定位
                label_text=f"{label_id}: {info['name']}",
                color="green" if info["confidence"] > 0.8 else "orange"
            )

        # 4. 在属性面板展示结构化结果
        self._show_property_panel(labels)

    def on_label_click(self, label_id: str):
        """用户点击CAD视图上的高亮标号"""
        # 查询知识库
        knowledge = requests.post(
            f"{self.api_url}/knowledge/query",
            json={"label_name": label_id, "context": "current_drawing"}
        ).json()

        # 弹出知识卡片：历史故障、供应商、库存、工艺要求
        self._show_knowledge_card(label_id, knowledge)
```

### 14.4 事件驱动的实时同步

```yaml
# event_bridge.yaml
# 基于 Kafka / RabbitMQ 的事件总线，实现PLM与IDMAS的实时联动

event_bridge:
  source: "teamcenter"  # 或 enovia / inteplm / mes
  sink: "idmas_platform"

  mappings:
    - event: "ITEM_RELEASED"
      action: "trigger_vision_parse"
      payload_template: |
        {
          "doc_id": "{{item_id}}",
          "revision": "{{revision}}",
          "image_url": "{{dataset_primary_file}}",
          "callback": "http://idmas-platform:8080/callback/plm/{{item_id}}"
        }

    - event: "ITEM_REVISION_CREATED"
      action: "trigger_version_diff"
      # 自动对比新旧版本图纸的标号变更

    - event: "WORKFLOW_APPROVAL_COMPLETED"
      action: "archive_labels_to_knowledge_base"
      # 审核通过的图纸，其AI解析结果正式入知识库

    - event: "QMS_NONCONFORMANCE_CREATED"
      action: "reverse_lookup_drawing"
      # 质量不合格品创建时，反向查询关联图纸标号，辅助根因分析
```

### 14.5 安全与权限

```yaml
# security_policy.yaml
enterprise_adapter_security:
  # 1. 网络隔离
  network:
    idmas_platform_zone: "DMZ"
    plm_system_zone: "Internal"
    adapter_gateway: "Bastion Host with IP Whitelist"

  # 2. 认证
  authentication:
    method: "mTLS + OAuth2"
    token_ttl: "1h"
    service_account_rotation: "90d"

  # 3. 数据脱敏
  data_masking:
    drawing_export:
      - rule: "remove_watermark_if_confidential"
      - rule: "downscale_resolution_for_external_vendor"
    label_export:
      - rule: "mask_precision_dimensions_for_unauthorized_roles"

  # 4. 审计
  audit:
    log_all_adapter_calls: true
    retain_days: 365
    sensitive_actions: ["writeback_labels", "delete_drawing", "export_batch"]
```

---

## 15. 附录：快速启动清单 (Quick Start)

### 15.1 环境准备
```bash
# 1. 硬件
- GPU服务器: 1x RTX 5090 (32GB) 或 2x A100 (40GB)
- CPU服务器: 16核64GB内存 (运行Master Scheduler + 适配器)
- 存储: 2TB SSD (图纸文件 + 向量数据库)

# 2. 基础服务
- Docker + Docker Compose
- Redis (状态缓存)
- Kafka / RabbitMQ (事件总线)
- Milvus (向量数据库)
- Neo4j (图数据库，可选)
- MinIO / S3 (对象存储)

# 3. 模型部署
vllm serve "Qwen/Qwen3.5-9B-Instruct" \
    --enable-lora \
    --lora-modules drawing-lora=/path/to/configC-prime \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.92
```

### 15.2 最小可运行示例
```bash
# 启动 Vision Agent 服务
docker-compose up vision-agent

# 启动 Master Scheduler
docker-compose up master-scheduler

# 启动 Teamcenter 适配器 (需配置企业PLM地址)
docker-compose up adapter-teamcenter

# 测试端到端链路
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "请解析专利CN1007281B的图3，识别所有标号",
    "source_system": "teamcenter",
    "source_doc_id": "CN1007281B",
    "revision": "A"
  }'
```

---

**文档结束 (v1.1 扩展版)**
