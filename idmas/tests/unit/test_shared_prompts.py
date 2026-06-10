"""
shared.token_counter + config.prompts 单元测试。
"""

from __future__ import annotations

from idmas.agents.shared.token_counter import TokenCounter, count_tokens
from idmas.config.prompts.debate_prompts import auto_resolve, build_judge_prompt
from idmas.config.prompts.intent_prompts import agents_for_intent, build_intent_prompt
from idmas.config.prompts.report_prompts import build_section_prompt, build_summary_prompt


class TestTokenCounter:
    def test_count_cjk_and_ascii(self):
        assert count_tokens("") == 0
        assert count_tokens("轴承座") == 3                 # 3 CJK 字
        assert count_tokens("abcd") == 1                   # 4 ascii ≈ 1 token

    def test_track_and_total(self):
        tc = TokenCounter()
        tc.track_usage("r1", "m", 100, 50)
        tc.track_usage("r1", "m", 10, 5)
        assert tc.get_total_usage("r1") == {
            "input_tokens": 110, "output_tokens": 55, "total_tokens": 165}

    def test_track_text(self):
        tc = TokenCounter()
        tc.track_text("r2", "m", "轴承座", "支撑轴")
        u = tc.get_total_usage("r2")
        assert u["input_tokens"] == 3 and u["output_tokens"] == 3

    def test_reset_and_unknown(self):
        tc = TokenCounter()
        tc.track_usage("r3", "m", 1, 1)
        tc.reset("r3")
        assert tc.get_total_usage("r3")["total_tokens"] == 0
        assert tc.get_total_usage("nope")["total_tokens"] == 0


class TestIntentPrompts:
    def test_agents_for_intent(self):
        assert agents_for_intent("comprehensive") == ["vision", "design", "process", "knowledge"]
        assert agents_for_intent("unknown") == ["vision"]   # 退化

    def test_build_intent_prompt(self):
        p = build_intent_prompt("识别标号", has_drawing=True)
        assert "识别标号" in p and "是" in p


class TestDebatePrompts:
    def test_auto_resolve_high_gap(self):
        assert auto_resolve(0.92, 0.70) == "vision"
        assert auto_resolve(0.70, 0.92) == "knowledge"

    def test_auto_resolve_small_gap_or_low(self):
        assert auto_resolve(0.86, 0.84) is None            # 差距太小
        assert auto_resolve(0.60, 0.40) is None            # 高方不够高

    def test_build_judge_prompt(self):
        p = build_judge_prompt("轴承座", 0.9, "端盖", 0.7)
        assert "轴承座" in p and "端盖" in p


class TestReportPrompts:
    def test_builders_nonempty(self):
        assert "齿轮" in build_section_prompt("vision", "齿轮箱标号")
        assert build_summary_prompt("") .strip() != ""
