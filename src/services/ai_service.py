import streamlit as st
from agents.analysis_agent import ReportAnalyzer


def _init_agents():
    """Initialize AI agents into session state if not already present."""
    if "report_analyzer" not in st.session_state:
        st.session_state.report_analyzer = ReportAnalyzer()

    if "chat_agent" not in st.session_state:
        try:
            from agents.chat_agent import ChatAgent

            if "GROQ_API_KEY" not in st.secrets:
                st.session_state.chat_agent = None
                st.session_state.chat_agent_error = (
                    "GROQ_API_KEY missing. Add it to .streamlit/secrets.toml"
                )
            else:
                st.session_state.chat_agent = ChatAgent()
                st.session_state.chat_agent_error = None

        except KeyError as err:
            st.session_state.chat_agent = None
            st.session_state.chat_agent_error = f"Config error: {err}"
        except ImportError as err:
            st.session_state.chat_agent = None
            st.session_state.chat_agent_error = f"Missing dependency: {err}"
        except Exception as err:
            st.session_state.chat_agent = None
            st.session_state.chat_agent_error = f"Initialization failed: {err}"


def get_rate_limit_status():
    """Return whether the user can still analyze reports today."""
    _init_agents()
    return st.session_state.report_analyzer.check_rate_limit()


def run_report_analysis(data, system_prompt, check_only=False):
    """Run analysis on report data using the ReportAnalyzer agent."""
    _init_agents()

    if check_only:
        return st.session_state.report_analyzer.check_rate_limit()

    return st.session_state.report_analyzer.analyze_report(
        data=data,
        system_prompt=system_prompt,
        check_only=False,
    )


def get_followup_response(user_query, report_text, message_history):
    """Get a follow-up answer using RAG over the report content."""
    _init_agents()

    if st.session_state.chat_agent is None:
        err = st.session_state.get(
            "chat_agent_error",
            "Chat is unavailable. Check your GROQ_API_KEY in secrets.toml",
        )
        return f"Error: {err}"

    # Try to recover report text from message history if missing
    if not report_text and message_history:
        for msg in message_history:
            if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get("content", ""):
                content = msg["content"]
                start = content.find("__REPORT_TEXT__\n") + len("__REPORT_TEXT__\n")
                end = content.find("\n__END_REPORT_TEXT__")
                if start > 0 and end > start:
                    report_text = content[start:end]
                    st.session_state.current_report_text = report_text
                    break

        if not report_text:
            for msg in reversed(message_history):
                if msg["role"] == "assistant" and len(msg.get("content", "")) > 100:
                    report_text = msg["content"][:5000]
                    break

    if not report_text:
        report_text = "No report context available."

    # Build or reuse vector store
    store_key = len(report_text)
    if (
        "vector_store" not in st.session_state
        or st.session_state.get("vector_store_key") != store_key
    ):
        try:
            with st.spinner("Preparing context..."):
                st.session_state.vector_store = st.session_state.chat_agent.build_vector_store(report_text)
                st.session_state.vector_store_key = store_key
        except Exception as err:
            st.warning(f"Vector store error: {err}. Falling back.")
            try:
                st.session_state.vector_store = st.session_state.chat_agent.build_vector_store("No report available.")
                st.session_state.vector_store_key = 0
            except Exception as fallback_err:
                return f"Error: Could not set up context store. {fallback_err}"

    return st.session_state.chat_agent.answer(
        user_query, st.session_state.vector_store, message_history
    )
