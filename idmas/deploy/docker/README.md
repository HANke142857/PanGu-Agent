# IDMAS 本地一键部署

在本目录执行（需 Docker Desktop）：

```bash
docker compose up -d --build
```

启动后：

| 服务 | 地址 | 凭据 |
|------|------|------|
| API 文档 (Swagger) | http://localhost:8080/docs | — |
| 健康检查 | http://localhost:8080/api/v1/health | — |
| RabbitMQ 管理台 | http://localhost:15672 | idmas / idmas_pwd |
| MinIO 控制台 | http://localhost:9001 | minioadmin / minioadmin |
| Neo4j 浏览器 | http://localhost:7474 | neo4j / idmas_neo4j |
| Elasticsearch | http://localhost:9200 | — |

## 向量库（Milvus）

compose **不内置 Milvus**，默认复用你本机已运行的 `milvus-standalone`
（`host.docker.internal:19530`）。启动 compose 前请确认它在运行；
否则把 `docker-compose.yml` 里 `VECTOR_BACKEND` 改为 `memory`。

## 后端开关

默认 `LLM_BACKEND=fake`、`OCR_BACKEND=fake`、`PLM_BACKEND=fake`，
**无需 GPU 与外部 PLM 即可跑通全链路**。其余（DB/MQ/存储/搜索/图谱）均为真实中间件。
切换真实 LLM/OCR/PLM 见 `.env.example`。

## 冒烟验证

```bash
# 1. 上传图纸（触发 Vision 解析）
curl -F "title=齿轮箱图" -F "drawing_type=assembly" \
     -F "file=@some.png" http://localhost:8080/api/v1/drawings

# 2. 用返回的 id 建解析任务（异步入队，worker 处理）
curl -X POST http://localhost:8080/api/v1/tasks \
     -H "Content-Type: application/json" \
     -d '{"drawing_id":"<id>","question":"识别所有标号"}'

# 3. 查询任务结果
curl http://localhost:8080/api/v1/tasks/<task_id>
```

停止并清理：`docker compose down`（加 `-v` 连数据卷一并删除）。
