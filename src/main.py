import streamlit as st
from auth.session_manager import AppSession
from components.auth_pages import show_login_page
from components.sidebar import show_sidebar
from components.analysis_form import show_analysis_form
from components.footer import show_footer
from config.app_config import APP_NAME, APP_ICON, APP_DESCRIPTION, APP_TAGLINE
from services.ai_service import get_followup_response

st.set_page_config(
    page_title=f"{APP_NAME} - AI Health Report Analyzer",
    page_icon=APP_ICON,
    layout="wide",
)

AppSession.initialize()

# Hide Streamlit input helper text
st.markdown("""
    <style>
        div[data-testid="InputInstructions"] > span:nth-child(1) {
            visibility: hidden;
        }
    </style>
""", unsafe_allow_html=True)


def render_welcome():
    """Show the welcome screen when no session is active."""
    st.markdown(f"""
        <div style="text-align: center; padding: 60px 20px;">
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3 style="color: #555;">{APP_DESCRIPTION}</h3>
            <p style="font-size: 1.15em; color: #888;">{APP_TAGLINE}</p>
            <p style="margin-top: 1.5rem; color: #aaa;">
                Create a new session to start analyzing a blood report
            </p>
        </div>
    """, unsafe_allow_html=True)

    _, center, _ = st.columns([2, 3, 2])
    with center:
        if st.button("＋ Start New Analysis Session", use_container_width=True, type="primary"):
            ok, session = AppSession.start_session()
            if ok:
                st.session_state.current_session = session
                st.rerun()
            else:
                st.error("Failed to create a new session. Please try again.")


def render_chat_history():
    """Display the message history for the current session."""
    ok, messages = st.session_state.auth_service.get_messages(
        st.session_state.current_session["id"]
    )
    if ok:
        for msg in messages:
            if msg.get("role") == "system":
                continue
            if msg["role"] == "user":
                st.info(msg["content"])
            else:
                st.success(msg["content"])
        return messages
    return []


def handle_followup(messages):
    """Handle follow-up questions from the chat input."""
    if user_input := st.chat_input("Ask a follow-up question about your report..."):
        st.info(user_input)

        st.session_state.auth_service.save_message(
            st.session_state.current_session["id"],
            user_input,
            role="user",
        )

        # Retrieve report text from session state or message history
        report_text = st.session_state.get("current_report_text", "")

        if not report_text and messages:
            for msg in messages:
                if msg.get("role") == "system" and "__REPORT_TEXT__" in msg.get("content", ""):
                    content = msg["content"]
                    start = content.find("__REPORT_TEXT__\n") + len("__REPORT_TEXT__\n")
                    end = content.find("\n__END_REPORT_TEXT__")
                    if start > 0 and end > start:
                        report_text = content[start:end]
                        st.session_state.current_report_text = report_text
                        break

        with st.spinner("Thinking..."):
            reply = get_followup_response(user_input, report_text, messages)
            st.success(reply)

            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"],
                reply,
                role="assistant",
            )
            st.rerun()


def render_user_greeting():
    """Show a personalized greeting at the top right."""
    user = st.session_state.get("user")
    if user:
        display = user.get("name") or user.get("email", "")
        st.markdown(f"""
            <div style="text-align: right; padding: 1rem; color: #4CAF93; font-size: 1.05em;">
                👋 Hello, {display}
            </div>
        """, unsafe_allow_html=True)


def main():
    AppSession.initialize()

    if not AppSession.is_logged_in():
        show_login_page()
        show_footer()
        return

    render_user_greeting()
    show_sidebar()

    if st.session_state.get("current_session"):
        st.title(f"📊 {st.session_state.current_session['title']}")
        messages = render_chat_history()

        if messages:
            with st.expander("🔄 Analyze a New / Updated Report", expanded=False):
                show_analysis_form()
            handle_followup(messages)
        else:
            show_analysis_form()
    else:
        render_welcome()


if __name__ == "__main__":
    main()
