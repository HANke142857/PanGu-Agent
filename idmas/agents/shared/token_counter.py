"""
Token 计数器。

count_tokens 用启发式估算（无需加载分词器）：中日韩字符按 1 token/字，
其余按 ~4 字符/token。够用于成本核算/指标上报；精确计费可换真实 tokenizer。

TokenCounter 按 request_id 累计输入/输出 token，供 Prometheus 上报与
持久化到 analysis_tasks.total_tokens。
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


def _is_cjk(ch: str) -> bool:
    try:
        return "CJK" in unicodedata.name(ch, "")
    except ValueError:
        return False


def count_tokens(text: str, model: str = "qwen2.5-vl-7b") -> int:
    """启发式估算 token 数。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if _is_cjk(ch))
    rest = len(text) - cjk
    return cjk + (rest + 3) // 4


@dataclass
class _Usage:
    input_tokens:  int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class TokenCounter:
    """按 request_id 累计 token 使用。"""

    _usage: dict[str, _Usage] = field(default_factory=dict)

    def track_usage(self, request_id: str, model: str, input_tokens: int, output_tokens: int) -> None:
        u = self._usage.setdefault(request_id, _Usage())
        u.input_tokens += int(input_tokens)
        u.output_tokens += int(output_tokens)

    def track_text(self, request_id: str, model: str, prompt: str, completion: str) -> None:
        self.track_usage(request_id, model, count_tokens(prompt, model), count_tokens(completion, model))

    def get_total_usage(self, request_id: str) -> dict[str, int]:
        u = self._usage.get(request_id, _Usage())
        return {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "total_tokens": u.total}

    def reset(self, request_id: str) -> None:
        self._usage.pop(request_id, None)
