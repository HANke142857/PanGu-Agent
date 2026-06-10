"""
Siemens Teamcenter PLM 适配器。

继承通用 HTTP 适配器，对接 Teamcenter REST API。
连接：Teamcenter SOA Web Service / REST；认证：服务账号（Vault 管理，90 天轮换）。
"""

from __future__ import annotations

from idmas.infrastructure.adapters.base import HTTPPLMAdapter


class TeamcenterAdapter(HTTPPLMAdapter):
    system = "teamcenter"
    # Teamcenter 以 item revision 维度回写属性
    writeback_path = "/tc/item-revisions/{doc_id}/properties"
    document_path = "/tc/item-revisions/{doc_id}"
