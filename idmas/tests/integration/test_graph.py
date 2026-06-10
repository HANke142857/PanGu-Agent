"""
Master Graph 集成测试。
全程内存运行：FakeVLLMClient + MemorySaver，无 GPU / DB / 网络。
"""
from __future__ import annotations
import uuid
import pytest
from idmas.agents.master.graph import build_master_graph
from idmas.infrastructure.llm.vllm_client import FakeVLLMClient
from idmas.domain.shared.exceptions import VLLMInferenceError


def _cfg(suffix: str = "") -> dict:
    """生成带唯一 thread_id 的 LangGraph config（有 checkpointer 时必须提供）。"""
    tid = suffix or str(uuid.uuid4())
    return {"configurable": {"thread_id": tid}}


# ── Fixtures ──────────────────────────────────────────────────────────────

def _base_input(task_type="label_recognition", prompt_mode="standard_visual") -> dict:
    return {
        "image_url":   "http://minio/test/gear_box.png",
        "prompt_mode": prompt_mode,
        "task_type":   task_type,
        "user_query":  "识别所有标号",
        "request_id":  "req-test-001",
        "messages":    [],
    }


# ── 基础流程 ───────────────────────────────────────────────────────────────

class TestMasterGraphBasic:
    @pytest.mark.asyncio
    async def test_label_recognition_flow(self):
        """最简流程：标号识别，无冲突，直接出报告。"""
        client       = FakeVLLMClient()
        graph, _     = await build_master_graph(client, enable_human_review=False)
        result       = await graph.ainvoke(_base_input("label_recognition"))

        assert result["status"] in ("completed", "waiting_review")
        assert result["vision_result"] is not None
        assert result["vision_result"].get("success") is True
        assert len(result["vision_result"].get("labels") or []) == 3
        assert result["report_result"] is not None
        assert result["report_result"].get("summary") is not None

    @pytest.mark.asyncio
    async def test_comprehensive_flow(self):
        """全链路：Vision + Design + Process + Knowledge + Report。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("comprehensive"))

        assert result["vision_result"] is not None
        assert result.get("design_result")   is not None
        assert result.get("process_result")  is not None
        assert result.get("knowledge_result") is not None
        assert result["report_result"]   is not None

    @pytest.mark.asyncio
    async def test_design_analysis_flow(self):
        """Vision + Design 链路。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("design_analysis"))

        assert result.get("vision_result")  is not None
        assert result.get("design_result")  is not None
        assert result.get("process_result") is None   # 不在此链路

    @pytest.mark.asyncio
    async def test_process_check_flow(self):
        """Vision + Process 链路。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("process_check"))

        assert result.get("vision_result")  is not None
        assert result.get("process_result") is not None
        assert result.get("design_result")  is None   # 不在此链路

    @pytest.mark.asyncio
    async def test_knowledge_query_flow(self):
        """Vision + Knowledge 链路。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("knowledge_query"))

        assert result["knowledge_result"] is not None
        assert result["knowledge_result"]["rag_answer"] is not None


# ── 意图路由 ───────────────────────────────────────────────────────────────

class TestIntentRouting:
    @pytest.mark.asyncio
    async def test_intent_sets_required_agents(self):
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("comprehensive"))
        agents   = result.get("required_agents") or []
        assert "vision" in agents
        assert "design" in agents
        assert "process" in agents
        assert "knowledge" in agents

    @pytest.mark.asyncio
    async def test_label_recognition_only_vision(self):
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("label_recognition"))
        assert result.get("required_agents") == ["vision"]


# ── 冲突检测 ───────────────────────────────────────────────────────────────

class TestConflictDetection:
    @pytest.mark.asyncio
    async def test_no_conflict_goes_to_report(self):
        """MVP 中 knowledge 无标号级结果，无冲突，直接进报告。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("knowledge_query"))

        assert result.get("conflicts") == []
        assert result.get("report_result") is not None


# ── 人工审核中断与恢复 ─────────────────────────────────────────────────────

class TestHumanReviewInterrupt:
    @pytest.mark.asyncio
    async def test_interrupt_before_human_review(self):
        """
        低置信度标号触发 human_review 中断，图停在该节点前。
        LangGraph 返回的 status 应为 waiting_review。
        """
        client    = FakeVLLMClient()   # 默认含低置信度标号
        graph, _  = await build_master_graph(client, enable_human_review=True)
        config    = _cfg("test-interrupt-001")

        result = await graph.ainvoke(_base_input("label_recognition"), config=config)
        # 有低置信度标号 → 触发中断 → status=waiting_review
        assert result.get("status") == "waiting_review"

    @pytest.mark.asyncio
    async def test_resume_after_human_decision(self):
        """人工审核后恢复图执行，最终 status 变 completed。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=True)
        config   = _cfg("test-resume-001")

        # 首次执行（中断于 human_review）
        result = await graph.ainvoke(_base_input("label_recognition"), config=config)
        assert result.get("status") == "waiting_review"

        # 注入人工决策并恢复
        await graph.aupdate_state(
            config,
            {
                "human_decision":      {"action": "confirm_all", "corrections": {}},
                "human_review_needed": False,
            },
        )
        final = await graph.ainvoke(None, config=config)
        assert final.get("status") == "completed"
        assert final.get("report_result") is not None


# ── 错误处理 ───────────────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_image_url(self):
        """空 URL → preprocess 拦截 → error_handler → status=failed。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        state    = _base_input()
        state["image_url"] = ""
        result   = await graph.ainvoke(state)
        assert result.get("status") == "failed"

    @pytest.mark.asyncio
    async def test_vllm_failure_handled(self):
        """LLM 故障 → Vision 出错 → 流程继续到 aggregation（不崩溃）。"""
        client   = FakeVLLMClient(raise_on_call=VLLMInferenceError("GPU OOM"))
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input())
        # 不论成败，流程应该走完不抛异常
        assert result.get("status") in ("completed", "failed", "waiting_review")


# ── Report 内容校验 ────────────────────────────────────────────────────────

class TestReportContent:
    @pytest.mark.asyncio
    async def test_report_has_summary(self):
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("comprehensive"))
        report   = result.get("report_result") or {}
        assert "summary" in report
        assert "sections" in report
        assert "markdown" in report

    @pytest.mark.asyncio
    async def test_report_markdown_contains_labels(self):
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("label_recognition"))
        md       = (result.get("report_result") or {}).get("markdown", "")
        assert "IDMAS" in md
        assert "视觉识别" in md

    @pytest.mark.asyncio
    async def test_messages_accumulate(self):
        """messages 字段应随流程追加（Annotated list[..., operator.add]）。"""
        client   = FakeVLLMClient()
        graph, _ = await build_master_graph(client, enable_human_review=False)
        result   = await graph.ainvoke(_base_input("label_recognition"))
        msgs     = result.get("messages") or []
        assert len(msgs) >= 3   # intent + vision + report 至少各一条


# ── Sub-Agent 独立测试 ─────────────────────────────────────────────────────

class TestSubAgents:
    @pytest.mark.asyncio
    async def test_design_graph_standalone(self):
        from idmas.agents.design.graph import build_design_graph
        labels = [
            {"label_id": "1", "name": "轴承座", "confidence": 0.92,
             "spatial_description": "", "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.1, "height": 0.1}},
            {"label_id": "2", "name": "未知",   "confidence": 0.55,
             "spatial_description": "", "bounding_box": {"x": 0.2, "y": 0.2, "width": 0.1, "height": 0.1}},
        ]
        graph  = build_design_graph()
        result = await graph.ainvoke({"labels": labels, "drawing_type": "assembly"})
        final  = result.get("final_result") or {}
        assert "compliant" in final
        assert len(final.get("issues") or []) > 0   # "未知" 和低置信度触发问题

    @pytest.mark.asyncio
    async def test_process_graph_standalone(self):
        from idmas.agents.process.graph import build_process_graph
        labels = [
            {"label_id": "1", "name": "轴承", "confidence": 0.90,
             "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.1, "height": 0.1}},
        ]
        graph  = build_process_graph()
        result = await graph.ainvoke({"labels": labels})
        final  = result.get("final_result") or {}
        assert "process_label_count" in final

    @pytest.mark.asyncio
    async def test_knowledge_graph_standalone(self):
        from idmas.agents.knowledge.graph import build_knowledge_graph
        labels = [{"label_id": "1", "name": "轴承座", "confidence": 0.92}]
        graph  = build_knowledge_graph()
        result = await graph.ainvoke({"query": "轴承座是什么", "labels": labels})
        final  = result.get("final_result") or {}
        assert final.get("rag_answer") is not None
        assert "轴承座" in final.get("rag_answer", "")

    @pytest.mark.asyncio
    async def test_report_graph_standalone(self):
        from idmas.agents.report.graph import build_report_graph
        graph  = build_report_graph()
        result = await graph.ainvoke({
            "vision_result":  {"labels": [{"label_id": "1", "name": "轴承座"}], "success": True},
            "design_result":  {"pass_rate": 1.0, "issues": [], "compliant": True},
        })
        final = result.get("final_report") or {}
        assert "summary"  in final
        assert "markdown" in final
