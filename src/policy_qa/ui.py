"""Chat/source/trace layout adapted from dev-abin/pdf-chatbot under MIT."""
import streamlit as st
from .retrieval import PolicyIndex
from .llm import Ollama
from .service import Run


def render_sources(sources):
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for source in sources:
                st.markdown(f"**{source['chunk_id']}**")
                st.caption(source["text"])


def app():
    st.set_page_config(page_title="Policy document assistant", layout="wide")
    st.title("Policy document assistant")
    st.caption("Answers from synthetic company policies. The assistant asks when your request needs clarification.")
    for key, default in (("messages", []), ("run", None), ("index", None), ("llm", None)):
        if key not in st.session_state:
            st.session_state[key] = default
    st.sidebar.title("Company policies")
    st.sidebar.caption("Synthetic demonstration data")
    st.sidebar.markdown("- Expenses\n- Leave\n- System access\n- Security incidents")
    if st.sidebar.button("New question"):
        old = st.session_state.run
        if old and old.pending:
            old.resume(cancel=True)
        st.session_state.run = None
        st.session_state.messages = []
        st.rerun()

    run = st.session_state.run
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])
            render_sources(message.get("sources", []))
    if run:
        with st.expander("Agent interaction trace"):
            st.json(run.trace.events)
        if run.pending:
            st.info("Waiting for your clarification. Your next reply continues this question.")
            if st.button("Cancel question"):
                run.resume(cancel=True)
                st.session_state.messages.append({"role": "assistant", "text": "Question cancelled."})
                st.rerun()

    finished = run is not None and (run.failed or bool(run.state.get("final")))
    if finished:
        st.caption("Choose New question to start another run.")
    text = st.chat_input("Reply to the clarification" if run and run.pending else "Ask about a company policy", disabled=finished)
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
                prompt += "\n\n" + "\n".join("- " + item for item in run.pending["options"])
            st.session_state.messages.append({"role": "assistant", "text": prompt})
        else:
            final = run.state["final"]
            sources = [e for e in run.state.get("evidence", []) if e["chunk_id"] in final["source_ids"]]
            st.session_state.messages.append({"role": "assistant", "text": final["answer"], "sources": sources})
    except Exception as error:
        st.session_state.messages.append({"role": "assistant", "text": "The run failed: " + str(error) + ". Start a new question after fixing the issue."})
    st.rerun()
