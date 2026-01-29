from guillotina.contrib.ai_query.result_processor import ResultProcessor
from guillotina.contrib.ai_query.schema_analyzer import SchemaAnalyzer
from guillotina.contrib.ai_query.handler import AIQueryHandler
from guillotina.tests import utils

import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings({"applications": ["guillotina.contrib.ai_query"]})
async def test_schema_analyzer_discovers_content_types(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/db/guillotina")
        assert status == 200

        container = await utils.get_container(requester)
        analyzer = SchemaAnalyzer(container)
        schema_info = await analyzer.get_schema_info()

        assert "content_types" in schema_info
        assert "behaviors" in schema_info
        assert "field_types" in schema_info
        assert len(schema_info["content_types"]) > 0


@pytest.mark.app_settings({"applications": ["guillotina.contrib.ai_query"]})
async def test_result_processor_sum_aggregation():
    items = [
        {"hours": 8.0, "developer": "Alice"},
        {"hours": 6.0, "developer": "Bob"},
        {"hours": 7.5, "developer": "Alice"},
    ]

    results = {"items": items, "items_total": 3}
    aggregation = {"operation": "sum", "field": "hours"}

    processed = ResultProcessor.process_results(results, aggregation)
    assert processed["total"] == 21.5
    assert processed["items_count"] == 3


@pytest.mark.app_settings({"applications": ["guillotina.contrib.ai_query"]})
async def test_result_processor_count_aggregation():
    items = [
        {"type": "Document"},
        {"type": "Folder"},
        {"type": "Document"},
    ]

    results = {"items": items, "items_total": 3}
    aggregation = {"operation": "count", "group_by": "type"}

    processed = ResultProcessor.process_results(results, aggregation)
    assert "by_type" in processed
    assert processed["by_type"]["Document"] == 2
    assert processed["by_type"]["Folder"] == 1


@pytest.mark.app_settings({"applications": ["guillotina.contrib.ai_query"]})
async def test_llm_query_handler_available(container_requester):
    async with container_requester as requester:
        handler = AIQueryHandler()
        assert handler is not None
        assert hasattr(handler, "translate_query")
        assert hasattr(handler, "generate_response")
        assert hasattr(handler, "generate_response_stream")
        assert hasattr(handler, "get_schema_info")


@pytest.mark.app_settings(
    {
        "applications": ["guillotina.contrib.ai_query"],
        "ai_query": {"enabled": False},
    }
)
async def test_ai_query_disabled(container_requester):
    async with container_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/@ai-query",
            data=json.dumps({"query": "test query"}),
        )
        assert status == 503
