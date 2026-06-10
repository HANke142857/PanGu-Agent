"""
Dassault ENOVIA (3DEXPERIENCE) PLM 适配器。

继承通用 HTTP 适配器，对接 3DEXPERIENCE REST（3DSpace）。
认证：OAuth 2.0 Client Credentials。
"""

from __future__ import annotations

from idmas.infrastructure.adapters.base import HTTPPLMAdapter


class EnoviaAdapter(HTTPPLMAdapter):
    system = "enovia"
    writeback_path = "/resources/v1/modeler/documents/{doc_id}/attributes"
    document_path = "/resources/v1/modeler/documents/{doc_id}"
