"""
PLM 适配器单元测试：幂等回写、Webhook 签名、品牌子类。
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from idmas.infrastructure.adapters.base import FakePLMAdapter, HTTPPLMAdapter, PLMDocument
from idmas.infrastructure.adapters.enovia import EnoviaAdapter
from idmas.infrastructure.adapters.inteplm import IntePLMAdapter
from idmas.infrastructure.adapters.teamcenter import TeamcenterAdapter


class TestFakeAdapterWriteback:
    async def test_writeback_records(self):
        adapter = FakePLMAdapter()
        result = await adapter.writeback("DOC-1", {"a": 1})
        assert result.success and not result.skipped
        assert adapter.writebacks == [("DOC-1", {"a": 1})]

    async def test_idempotent_skip_same_payload(self):
        adapter = FakePLMAdapter()
        await adapter.writeback("DOC-1", {"a": 1})
        again = await adapter.writeback("DOC-1", {"a": 1})
        assert again.success and again.skipped
        assert len(adapter.writebacks) == 1          # 第二次未真正写入

    async def test_different_payload_not_skipped(self):
        adapter = FakePLMAdapter()
        await adapter.writeback("DOC-1", {"a": 1})
        r2 = await adapter.writeback("DOC-1", {"a": 2})
        assert not r2.skipped
        assert len(adapter.writebacks) == 2

    async def test_get_document_default(self):
        adapter = FakePLMAdapter(documents={"X": PLMDocument(doc_id="X", title="已知")})
        assert (await adapter.get_document("X")).title == "已知"
        assert (await adapter.get_document("Y")).doc_id == "Y"   # 兜底


class TestWebhookSignature:
    def test_valid_signature(self):
        secret = "s3cr3t"
        adapter = FakePLMAdapter(webhook_secret=secret)
        payload = b'{"event":"updated"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert adapter.verify_webhook(sig, payload) is True

    def test_invalid_signature(self):
        adapter = FakePLMAdapter(webhook_secret="s3cr3t")
        assert adapter.verify_webhook("deadbeef", b"x") is False

    def test_no_secret_rejects(self):
        adapter = FakePLMAdapter(webhook_secret="")
        assert adapter.verify_webhook("anything", b"x") is False


class TestBrandAdapters:
    def test_systems_and_paths(self):
        tc = TeamcenterAdapter("http://tc/", "tok")
        en = EnoviaAdapter("http://en", "tok")
        ip = IntePLMAdapter("http://ip", "tok")
        assert tc.system == "teamcenter"
        assert en.system == "enovia"
        assert ip.system == "inteplm"
        assert tc._base_url == "http://tc"               # 去尾斜杠
        assert "{doc_id}" in tc.writeback_path

    def test_headers_with_token(self):
        a = HTTPPLMAdapter("http://x", token="abc")
        assert a._headers()["Authorization"] == "Bearer abc"

    def test_headers_without_token(self):
        a = HTTPPLMAdapter("http://x")
        assert a._headers() == {}
