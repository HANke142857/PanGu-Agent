# IDMAS 前端 · 工业图纸审阅工作台

IDMAS（工业图纸智能解析系统）的 Web 前端。设计定位为 **浅色工业工作台 + CAD 图纸审阅交互 + Agent Pipeline 状态可视化**，面向机械设计、工艺、质检、知识产权、运维工程师的高频日常作业，强调图纸清晰度、标注准确性与 Agent 可追溯性。

参考气质：Siemens Teamcenter / Autodesk Viewer / Grafana / GitLab CI Pipeline，而非消费级 AI 聊天产品或营销官网。

## 技术栈

- Vite + React 18 + TypeScript
- Tailwind CSS（自定义 `IDMAS Industrial Workspace Theme` 色板）
- react-router-dom · lucide-react

## 启动

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

默认使用 mock 数据离线运行，无需后端即可预览全部界面。

接入真实后端：

```bash
# 1) 启动 FastAPI（默认 :8080），vite 已将 /api 代理过去
# 2) 关闭 mock
VITE_USE_MOCK=false npm run dev
```

`IDMAS_API_BASE` 可覆盖代理目标（默认 `http://localhost:8080`）。

## 目录结构

```
src/
  api/          # client.ts(fetch封装+SSE预留) · resources.ts(mock/真实切换)
  components/
    layout/     # AppShell · TopBar · SideNav
    common/     # Tag · ConfidenceBadge · AgentPipeline
    viewer/     # DrawingLibrary · DrawingViewer(CAD) · DrawingArtwork
    results/    # ResultsPanel(识别/冲突/知识引用/报告 Tabs + 复核操作)
  pages/        # Workbench · Tasks · Knowledge · Drawings · PLM
  lib/          # constants(状态/置信/Agent 元数据) · format
  mock/         # 离线预览数据
  types/        # 镜像后端 idmas/api/schemas 的 TS 类型
```

## 已实现界面

- **工作台（主页）** — 三栏：左图纸库 / 中 CAD Viewer（棋盘格画布、标注框 overlay、缩放拖拽、显隐标注、只看待复核）/ 右识别结果（标号列表 + 置信度 + 确认/修正/拒绝复核 + 冲突/知识引用/报告 Tabs）；底部 Agent 执行链路 Pipeline。
- **任务中心** — 任务表格 + 状态筛选 + 展开查看 Pipeline、耗时、Token、错误（GitLab/Grafana 风格）。
- **知识检索** — 查询框 + 向量/关键词/图谱/混合检索切换 + 评分结果卡片。
- **图纸库 / PLM 回写** — 完整图纸表格；PLM 回写审批确认弹窗（选择 Teamcenter/ENOVIA/IntePLM）。

## 主题色板

| 用途 | 色值 |
| --- | --- |
| 主背景（冷灰白） | `#F6F8FA` |
| 面板 | `#FFFFFF` |
| 边框 | `#E5E7EB` |
| 主操作（工业蓝） | `#2563EB` / `#1D4ED8` |
| 成功 / 高置信 | `#16A34A` |
| 待复核 / 低置信 | `#D97706` |
| 冲突 / 错误 | `#DC2626` |
| 处理中 | `#0284C7` |
