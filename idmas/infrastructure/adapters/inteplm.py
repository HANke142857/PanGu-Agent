"""
IntePLM 适配器。

继承通用 HTTP 适配器，对接 IntePLM REST API。
认证：API Key + Token。
"""

from __future__ import annotations

from idmas.infrastructure.adapters.base import HTTPPLMAdapter


class IntePLMAdapter(HTTPPLMAdapter):
    system = "inteplm"
    writeback_path = "/api/documents/{doc_id}/writeback"
    document_path = "/api/documents/{doc_id}"
