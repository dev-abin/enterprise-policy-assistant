"""Check model-output repair budgets without contacting Ollama."""

from unittest.mock import Mock

import httpx
import pytest
from langchain_ollama import ChatOllama
from ollama import Client

import policy_qa.llm as llm_module
from policy_qa.llm import Ollama
from policy_qa.schemas import Draft, Search
from policy_qa.traces import Trace


@pytest.fixture
def mock_ollama(monkeypatch):
    """Exercise the real ChatOllama integration through an in-memory HTTP transport."""
    import json

    requests = []
    responses = []

    def handle(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "test-model",
                            "model": "test-model",
                            "digest": "test-digest",
                        }
                    ]
                },
            )
        assert request.url.path == "/api/chat"
        requests.append(json.loads(request.content))
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 12,
                "eval_count": 8,
                **response,
            },
        )

    transport = httpx.MockTransport(handle)

    def chat_model(**kwargs):
        kwargs["client_kwargs"]["transport"] = transport
        return ChatOllama(**kwargs)

    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.test")
    monkeypatch.setattr(
        llm_module, "Client", lambda **kwargs: Client(**kwargs, transport=transport)
    )
    monkeypatch.setattr(llm_module, "ChatOllama", chat_model)
    return Ollama("test-model"), requests, responses


def test_chatollama_structured_output_preserves_settings_citations_and_trace(
    mock_ollama,
    tmp_path,
):
    llm, requests, responses = mock_ollama
    responses.append(
        {
            "message": {
                "role": "assistant",
                "content": '{"answer": "30 days", "source_ids": ["expenses/travel"], "abstain": false}',
            }
        }
    )
    trace = Trace(tmp_path / "native-trace.jsonl", "native-test")
    result = llm.structured(
        "writer",
        "Use policy evidence",
        {
            "evidence": [{"chunk_id": "expenses/travel"}],
        },
        Draft,
        trace,
    )
    assert result.source_ids == ["expenses/travel"]
    assert llm.digest == "test-digest"
    request = requests[0]
    assert request["model"] == "test-model"
    assert request["think"] is False
    assert request["keep_alive"] == "10m"
    assert {
        key: request["options"][key]
        for key in ("num_ctx", "num_predict", "temperature", "seed")
    } == {
        "num_ctx": 4096,
        "num_predict": 700,
        "temperature": 0,
        "seed": 42,
    }
    assert request["format"]["properties"]["source_ids"]["items"]["enum"] == [
        "expenses/travel"
    ]
    event = trace.events[0]
    assert (event["sender"], event["recipient"], event["kind"]) == (
        "writer",
        "writer",
        "model_call",
    )
    payload = event["payload"]
    import json

    assert json.loads(trace.path.read_text(encoding="utf-8"))["payload"] == payload
    assert payload["response"]["content"]
    assert payload["response"]["usage_metadata"]["input_tokens"] == 12
    assert payload["response"]["usage_metadata"]["output_tokens"] == 8
    assert payload["response"]["response_metadata"]["done_reason"] == "stop"


def test_chatollama_search_tool_call_is_executed_by_the_caller(mock_ollama):
    llm, requests, responses = mock_ollama
    responses.append(
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search_documents",
                            "arguments": {"query": "travel", "k": 3},
                        },
                    }
                ],
            }
        }
    )
    trace = Mock()
    assert llm.search_call({}, trace).query == "travel"
    assert len(requests) == 1
    assert requests[0]["tools"][0]["function"]["name"] == "search_documents"
    tool_call = trace.emit.call_args.args[3]["response"]["tool_calls"][0]
    assert tool_call["name"] == "search_documents"
    assert tool_call["args"] == {"query": "travel", "k": 3}


def test_chatollama_repairs_malformed_tool_arguments(mock_ollama):
    llm, requests, responses = mock_ollama
    for arguments in ("not JSON", {"query": "travel", "k": 3}):
        responses.append(
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search_documents",
                                "arguments": arguments,
                            },
                        }
                    ],
                }
            }
        )
    trace = Mock()
    assert llm.search_call({}, trace).query == "travel"
    assert len(requests) == 2
    assert trace.emit.call_count == 2
    assert "error" in trace.emit.call_args_list[0].args[3]


def test_chatollama_token_limit_is_traced_and_raised(mock_ollama):
    llm, requests, responses = mock_ollama
    responses.append(
        {
            "message": {"role": "assistant", "content": "partial"},
            "done_reason": "length",
        }
    )
    trace = Mock()
    with pytest.raises(RuntimeError, match="token limit"):
        llm.structured("writer", "Answer", {}, Draft, trace)
    assert len(requests) == 1
    assert (
        trace.emit.call_args.args[3]["response"]["response_metadata"]["done_reason"]
        == "length"
    )


def test_chatollama_connection_failure_is_not_a_repair_retry(mock_ollama):
    llm, requests, responses = mock_ollama
    responses.append(httpx.ConnectError("Ollama unavailable"))
    with pytest.raises((ConnectionError, httpx.ConnectError)):
        llm.search_call({}, Mock())
    assert len(requests) == 1


@pytest.mark.parametrize("method", ["structured", "search_call"])
@pytest.mark.parametrize("succeeds", [True, False])
def test_three_repairs_after_initial_attempt(mock_ollama, method, succeeds):
    llm, requests, responses = mock_ollama
    responses.extend(
        [
            {"message": {"role": "assistant", "content": "invalid JSON"}}
            for _ in range(4)
        ]
    )
    if succeeds:
        message = {"role": "assistant", "content": '{"query": "travel", "k": 3}'}
        if method == "search_call":
            message["tool_calls"] = [
                {
                    "function": {
                        "name": "search_documents",
                        "arguments": {"query": "travel", "k": 3},
                    }
                }
            ]
        responses[-1] = {"message": message}
    trace = Mock()

    def invoke():
        if method == "structured":
            return llm.structured("researcher", "Search policies", {}, Search, trace)
        return llm.search_call({}, trace)

    if succeeds:
        assert invoke().query == "travel"
    else:
        with pytest.raises(ValueError, match="after repair"):
            invoke()
    assert len(requests) == 4
    assert trace.emit.call_count == 4


@pytest.mark.parametrize("evidence", [[], [{"chunk_id": "expenses/travel"}]])
def test_structured_output_rejects_unknown_citations(mock_ollama, evidence):
    llm, requests, responses = mock_ollama
    responses.extend(
        [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"answer": "30 days", "source_ids": ["invented/id"], "abstain": false}',
                }
            }
            for _ in range(4)
        ]
    )
    with pytest.raises(ValueError, match="unknown evidence ID"):
        llm.structured("writer", "Use evidence", {"evidence": evidence}, Draft, Mock())
    assert len(requests) == 4
    if not evidence:
        assert requests[0]["format"]["properties"]["source_ids"]["maxItems"] == 0
