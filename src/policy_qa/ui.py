import logging
from html import escape

import streamlit as st

from .llm import Ollama
from .retrieval import PolicyIndex
from .service import Run

logger = logging.getLogger(__name__)


def format_answer(answer, sources):
    """Show numbered citations with native hover tooltips, without source blocks."""
    answer = escape(answer, quote=False)
    remaining = []
    for number, source in enumerate(sources, start=1):
        title = source["text"].split("\n", 1)[0].strip()
        tooltip = escape(f"{source['document_id']}.txt · {title}")
        citation = f'<abbr title="{tooltip}" style="cursor:help">[{number}]</abbr>'
        marker = escape(f"[{source['chunk_id']}]", quote=False)
        if marker in answer:
            answer = answer.replace(marker, citation)
        else:
            remaining.append(citation)
    return answer + (" " + " ".join(remaining) if remaining else "")


def render_answer(message):
    """Render the answer with escaped text and hover-only source citations."""
    st.markdown(
        format_answer(message["text"], message.get("sources", [])),
        unsafe_allow_html=True,
    )


def main():
    """Render the policy chat UI and handle questions and clarification replies."""
    st.set_page_config(page_title="Policy document assistant", layout="wide")
    st.title("Policy document assistant")
    st.caption(
        "Ask about company policies. The assistant will request clarification when needed."
    )
    for key, default in (
        ("messages", []),
        ("run", None),
        ("index", None),
        ("llm", None),
    ):
        if key not in st.session_state:
            st.session_state[key] = default
    run = st.session_state.run
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_answer(message)
            else:
                st.markdown(message["text"])
    if run and run.pending:
        st.info(
            "Waiting for your clarification. Your next reply continues this question."
        )
        if st.button("Cancel question"):
            run.resume(cancel=True)
            st.session_state.messages.append(
                {"role": "assistant", "text": "Question cancelled."}
            )
            st.rerun()

    text = st.chat_input(
        "Reply to the clarification"
        if run and run.pending
        else "Ask about a company policy",
    )
    if not text or not text.strip():
        return
    if len(text) > 2000:
        st.error("Please keep your message within 2,000 characters.")
        return
    st.session_state.messages.append({"role": "user", "text": text})
    try:
        with st.spinner("Checking policy evidence..."):
            if run and run.pending:
                run.resume(text)
            else:
                if st.session_state.index is None:
                    st.session_state.index = PolicyIndex()
                if st.session_state.llm is None:
                    st.session_state.llm = Ollama()
                run = Run(st.session_state.llm, st.session_state.index)
                st.session_state.run = run
                run.start(text)
        if run.pending:
            prompt = run.pending["question"]
            if run.pending["options"]:
                prompt += "\n\n" + "\n".join(
                    "- " + item for item in run.pending["options"]
                )
            st.session_state.messages.append({"role": "assistant", "text": prompt})
        else:
            final = run.state["final"]
            sources = [
                e
                for e in run.state.get("evidence", [])
                if e["chunk_id"] in final["source_ids"]
            ]
            st.session_state.messages.append(
                {"role": "assistant", "text": final["answer"], "sources": sources}
            )
    except Exception:
        logger.exception("Policy question failed")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "text": "I couldn't process your question. Please try again in a moment.",
            }
        )
    st.rerun()
