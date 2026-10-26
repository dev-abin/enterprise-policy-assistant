# Reused code

Adapted from [dev-abin/pdf-chatbot](https://github.com/dev-abin/pdf-chatbot), revision `1e6861bfad3108b5b0c46f181544e6878bccc2e2`, under its MIT license (included in `LICENSE`).

- `src/policy_qa/ui.py`: chat input/messages and source/trace expander layout from `apps/web/rag_ui/layout/chat_page.py`; session-state and sidebar patterns from `state.py` and `layout/sidebar.py`.
- `src/policy_qa/llm.py`: simplified local Ollama configuration/factory concept from `core/llm_client.py`; native HTTP schema/tool calls are new.
- `src/policy_qa/retrieval.py`: persistent Chroma and provenance pattern from `rag/chroma_store.py` and retrieval/upload modules. Section loading and CPU ONNX embedding implementation are adapted for this fixed text corpus.

The three-agent graph, clarification handling, payload contracts, synthetic policies, evaluation scripts, and focused tests were written for this assessment. The original HTTP API, authentication, OCR, Wikipedia fallback, and full UI feature set were not copied into the runtime.
