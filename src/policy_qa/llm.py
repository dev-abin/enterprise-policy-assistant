"""Use ChatOllama with policy-specific validation, repair retries, and tracing."""

import json
import os
import time

from httpx import Timeout
from langchain_ollama import ChatOllama
from ollama import Client

from .limits import MAX_OUTPUT_REPAIRS
from .prompts import SEARCH
from .schemas import Search


class Ollama:
    """Wrap ChatOllama with the output contracts used by the policy agents."""

    def __init__(self, model=None):
        """Check the installed model and configure the LangChain chat client."""
        self.model = model or os.getenv("POLICY_MODEL", "qwen3.5:4b")
        self.url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        tags = Client(host=self.url, trust_env=False, timeout=10).list()
        matches = [model for model in tags.models if model.model == self.model]
        if not matches:
            raise RuntimeError(f"Model {self.model} is not installed in Ollama")
        self.digest = matches[0].digest
        self.chat_model = ChatOllama(
            model=self.model,
            base_url=self.url,
            reasoning=False,
            num_ctx=4096,
            num_predict=700,
            temperature=0,
            seed=42,
            keep_alive="10m",
            client_kwargs={"trust_env": False, "timeout": Timeout(180, connect=10)},
        )

    def structured(self, role, prompt, context, schema, trace):
        """Use native structured output and validate the agent's schema and citations."""
        output_schema = schema.model_json_schema()
        ids = [e["chunk_id"] for e in context.get("evidence", [])]
        if "source_ids" in output_schema.get("properties", {}):
            if ids:
                output_schema["properties"]["source_ids"]["items"] = {
                    "type": "string",
                    "enum": ids,
                }
            else:
                output_schema["properties"]["source_ids"]["maxItems"] = 0
        client = self.chat_model.with_structured_output(
            output_schema, method="json_schema", include_raw=True
        )

        def validate(result):
            """Validate the parsed payload and reject unknown source references."""
            answer = schema.model_validate(result["parsed"])
            if not set(getattr(answer, "source_ids", [])) <= set(ids):
                raise ValueError("Agent referenced an unknown evidence ID")
            return answer

        return self._generate(
            role, prompt, context, client, validate, trace, schema=output_schema
        )

    def search_call(self, context, trace):
        """Read and validate a native search tool call without executing it."""
        tool = {
            **Search.model_json_schema(),
            "title": "search_documents",
            "description": "Search company policy sections for relevant evidence.",
        }
        client = self.chat_model.bind_tools([tool])

        def validate(message):
            """Accept exactly one search call with valid query arguments."""
            calls = message.tool_calls
            if len(calls) != 1 or calls[0]["name"] != "search_documents":
                raise ValueError("Expected exactly one search_documents call")
            return Search.model_validate(calls[0]["args"])

        return self._generate(
            "researcher", SEARCH, context, client, validate, trace, tools=[tool]
        )

    def _generate(self, role, prompt, context, client, validate, trace, **contract):
        """Share three repair retries and native response tracing across model calls."""
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(context)},
        ]
        for attempt in range(MAX_OUTPUT_REPAIRS + 1):
            payload = {
                "request": {"model": self.model, "messages": list(messages), **contract}
            }
            started = time.perf_counter()
            try:
                result = client.invoke(messages)
                response = result["raw"] if isinstance(result, dict) else result
                payload["response"] = response.model_dump(mode="json")
                if response.response_metadata.get("done_reason") == "length":
                    raise RuntimeError("Model output reached its token limit")
                if isinstance(result, dict) and result["parsing_error"]:
                    raise result["parsing_error"]
                return validate(result)
            except (ValueError, KeyError) as error:
                payload["error"] = str(error)
                if attempt == MAX_OUTPUT_REPAIRS:
                    raise ValueError(
                        f"Invalid {role} output after repair: {error}"
                    ) from error
                messages.append(
                    {
                        "role": "user",
                        "content": f"Correct your output to match the required schema or tool. Error: {error}",
                    }
                )
            finally:
                payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
                trace.emit(role, role, "model_call", payload)
