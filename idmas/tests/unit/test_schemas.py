"""
API Schema 单元测试。
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from idmas.api.schemas.common import ErrorDetail, ErrorResponse, PaginationParams
from idmas.api.schemas.knowledge import KnowledgeSearchRequest
from idmas.api.schemas.task import TaskCreateRequest
from idmas.domain.analysis.value_objects import PromptMode, TaskType


class TestTaskCreateRequest:
    def test_minimal_valid(self):
        req = TaskCreateRequest(drawing_id=uuid.uuid4())
        assert req.task_type is TaskType.label_recognition
        assert req.prompt_mode is PromptMode.standard_visual

    def test_missing_drawing_id_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateRequest()

    def test_invalid_drawing_id_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateRequest(drawing_id="not-a-uuid")

    def test_invalid_enum_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateRequest(drawing_id=uuid.uuid4(), task_type="bogus")


class TestKnowledgeSearchRequest:
    def test_defaults(self):
        r = KnowledgeSearchRequest(query="轴承座")
        assert r.top_k == 5 and r.search_type == "hybrid"

    @pytest.mark.parametrize("top_k", [0, 21, -1])
    def test_top_k_out_of_range(self, top_k):
        with pytest.raises(ValidationError):
            KnowledgeSearchRequest(query="x", top_k=top_k)

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            KnowledgeSearchRequest(query="")

    def test_invalid_search_type(self):
        with pytest.raises(ValidationError):
            KnowledgeSearchRequest(query="x", search_type="semantic")


class TestCommonSchemas:
    def test_pagination_defaults_and_bounds(self):
        assert PaginationParams().offset == 0
        assert PaginationParams().limit == 20
        with pytest.raises(ValidationError):
            PaginationParams(limit=999)

    def test_error_response_serialization(self):
        resp = ErrorResponse(error=ErrorDetail(code="IDMAS-404-001", message="未找到"))
        dumped = resp.model_dump()
        assert dumped["error"]["code"] == "IDMAS-404-001"
