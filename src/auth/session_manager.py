import json
import streamlit as st
from datetime import datetime, timedelta
from config.app_config import SESSION_TIMEOUT_MINUTES


class AppSession:
    """Manages user session lifecycle, authentication state, and timeout handling."""

    @staticmethod
    def initialize():
        """Set up session on first load and validate on subsequent loads."""
        if "session_ready" not in st.session_state:
            st.session_state.session_ready = True
            AppSession._inject_storage_js()

        if "auth_service" not in st.session_state:
            from auth.auth_service import UserAuthService
            st.session_state.auth_service = UserAuthService()

        # Enforce session timeout
        if "last_active" in st.session_state:
            idle = datetime.now() - st.session_state.last_active
            if idle > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                AppSession.wipe_session()
                st.error("Your session expired. Please log in again.")
                st.rerun()

        st.session_state.last_active = datetime.now()

        # Validate existing user token
        if "user" in st.session_state:
            valid = st.session_state.auth_service.validate_session_token()
            if not valid:
                AppSession.wipe_session()
                st.error("Session is no longer valid. Please log in again.")
                st.rerun()

    @staticmethod
    def is_logged_in():
        """Return True if a user is currently authenticated."""
        return bool(st.session_state.get("user"))

    @staticmethod
    def wipe_session():
        """Clear all session state except the initialization flag."""
        AppSession._clear_storage_js()
        keep = {"session_ready"}
        for key in list(st.session_state.keys()):
            if key not in keep:
                del st.session_state[key]

    @staticmethod
    def sign_in(email, password):
        """Authenticate user and persist session."""
        if "auth_service" not in st.session_state:
            from auth.auth_service import UserAuthService
            st.session_state.auth_service = UserAuthService()

        success, result = st.session_state.auth_service.login(email, password)
        if success and "auth_token" in st.session_state:
            AppSession._save_to_storage(result, st.session_state.auth_token)
        return success, result

    @staticmethod
    def sign_out():
        """Log the user out and clear all state."""
        if "auth_service" in st.session_state:
            st.session_state.auth_service.logout()
        AppSession.wipe_session()

    @staticmethod
    def start_session():
        """Create a new analysis chat session."""
        if not AppSession.is_logged_in():
            return False, "Not logged in"
        return st.session_state.auth_service.create_session(st.session_state.user["id"])

    @staticmethod
    def fetch_sessions():
        """Get all sessions for the current user."""
        if not AppSession.is_logged_in():
            return False, []
        return st.session_state.auth_service.get_sessions(st.session_state.user["id"])

    @staticmethod
    def end_session(session_id):
        """Delete a specific session."""
        if not AppSession.is_logged_in():
            return False, "Not logged in"
        return st.session_state.auth_service.remove_session(session_id)

    # ── Persistent storage helpers ──────────────────────────────────────────

    @staticmethod
    def _inject_storage_js():
        """Inject JS utilities for localStorage-based session persistence."""
        script = """
        <script>
        window.addEventListener('DOMContentLoaded', function() {
            const stored = localStorage.getItem('hia_session');
            if (stored) {
                try { window.hia_session = JSON.parse(stored); }
                catch(e) { localStorage.removeItem('hia_session'); }
            }
        });
        window.saveSession = d => localStorage.setItem('hia_session', JSON.stringify(d));
        window.clearSession = () => localStorage.removeItem('hia_session');
        window.getSession = () => { const s = localStorage.getItem('hia_session'); return s ? JSON.parse(s) : null; };
        </script>
        """
        st.markdown(script, unsafe_allow_html=True)

    @staticmethod
    def _save_to_storage(user_data, token):
        """Persist auth data to localStorage."""
        payload = {
            "user": user_data,
            "token": token,
            "saved_at": datetime.now().isoformat(),
        }
        script = f"""
        <script>
        if (typeof window.saveSession === 'function') {{
            window.saveSession({json.dumps(payload)});
        }}
        </script>
        """
        st.markdown(script, unsafe_allow_html=True)

    @staticmethod
    def _clear_storage_js():
        """Clear localStorage session data."""
        st.markdown(
            "<script>if (typeof window.clearSession==='function') window.clearSession();</script>",
            unsafe_allow_html=True,
        )
