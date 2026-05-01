import streamlit as st
from auth.session_manager import AppSession
from components.footer import show_footer
from config.app_config import ANALYSIS_DAILY_LIMIT


def show_sidebar():
    """Render the sidebar with session management and user controls."""
    with st.sidebar:
        st.title("📋 Analysis Sessions")

        if st.button("＋ New Session", use_container_width=True, type="primary"):
            if st.session_state.user and "id" in st.session_state.user:
                ok, session = AppSession.start_session()
                if ok:
                    st.session_state.current_session = session
                    st.rerun()
                else:
                    st.error("Could not create session")
            else:
                st.error("Please log in again")
                AppSession.sign_out()
                st.rerun()

        # Daily usage tracker
        used = st.session_state.get("reports_analyzed_today", 0)
        remaining = ANALYSIS_DAILY_LIMIT - used
        bar_color = "#4CAF93" if remaining > 3 else "#e05252"

        st.markdown(
            f"""
            <div style="
                padding: 0.6rem;
                border-radius: 0.5rem;
                background: rgba(76, 175, 147, 0.08);
                margin: 0.5rem 0;
                text-align: center;
                font-size: 0.88em;
            ">
                <p style="margin: 0; color: #888;">Daily Analyses Used</p>
                <p style="margin: 0.2rem 0 0; color: {bar_color}; font-weight: 600;">
                    {remaining} / {ANALYSIS_DAILY_LIMIT} remaining
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        _render_session_list()
        st.markdown("---")

        if st.button("🚪 Log Out", use_container_width=True):
            AppSession.sign_out()
            st.rerun()

        show_footer(in_sidebar=True)


def _render_session_list():
    """Display the list of previous sessions."""
    user = st.session_state.get("user")
    if not user or "id" not in user:
        return

    ok, sessions = AppSession.fetch_sessions()
    if not ok:
        return

    if not sessions:
        st.info("No previous sessions found.")
        return

    st.subheader("Previous Sessions")

    if "pending_delete" not in st.session_state:
        st.session_state.pending_delete = None

    for session in sessions:
        _render_session_row(session)


def _render_session_row(session):
    """Render a single session row with select and delete options."""
    if not session or not isinstance(session, dict) or "id" not in session:
        return

    sid = session["id"]
    current_id = (
        st.session_state.get("current_session", {}).get("id")
        if isinstance(st.session_state.get("current_session"), dict)
        else None
    )

    with st.container():
        title_col, del_col = st.columns([4, 1])

        with title_col:
            label = f"{'▶ ' if sid == current_id else '📄 '}{session['title']}"
            if st.button(label, key=f"sel_{sid}", use_container_width=True):
                st.session_state.current_session = session
                st.rerun()

        with del_col:
            if st.button("🗑", key=f"del_{sid}", help="Delete session"):
                st.session_state.pending_delete = (
                    None if st.session_state.pending_delete == sid else sid
                )
                st.rerun()

        if st.session_state.pending_delete == sid:
            st.warning("Delete this session?")
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("Yes", key=f"yes_{sid}", type="primary", use_container_width=True):
                    ok, err = AppSession.end_session(sid)
                    if ok:
                        st.session_state.pending_delete = None
                        if current_id == sid:
                            st.session_state.current_session = None
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
            with no_col:
                if st.button("No", key=f"no_{sid}", use_container_width=True):
                    st.session_state.pending_delete = None
                    st.rerun()
