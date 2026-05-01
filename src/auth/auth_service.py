import re
import streamlit as st
from supabase import create_client
from datetime import datetime


class UserAuthService:
    """Handles all authentication and user data operations via Supabase."""

    def __init__(self):
        try:
            self.db = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"],
            )
        except Exception as err:
            st.error(f"Database connection failed: {err}")
            raise

        self._restore_session()

        if "auth_token" in st.session_state:
            self._validate_token()

    def _restore_session(self):
        """Attempt to resume an existing Supabase session."""
        try:
            if "auth_token" in st.session_state and "refresh_token" in st.session_state:
                try:
                    self.db.auth.set_session(
                        st.session_state.auth_token,
                        st.session_state.refresh_token,
                    )
                except Exception:
                    pass

            session = self.db.auth.get_session()
            if session and session.access_token:
                stored_token = st.session_state.get("auth_token")
                if not stored_token or stored_token != session.access_token:
                    user = self.db.auth.get_user()
                    if user and user.user:
                        user_data = self.fetch_user_data(user.user.id)
                        if user_data:
                            st.session_state.auth_token = session.access_token
                            st.session_state.refresh_token = session.refresh_token
                            st.session_state.user = user_data
        except Exception:
            pass

    def _validate_token(self):
        """Refresh and sync the current auth token."""
        try:
            session = self.db.auth.get_session()
            if not session or not session.access_token:
                if "auth_token" in st.session_state and "refresh_token" in st.session_state:
                    try:
                        self.db.auth.set_session(
                            st.session_state.auth_token,
                            st.session_state.refresh_token,
                        )
                        session = self.db.auth.get_session()
                    except Exception:
                        pass

            if not session or not session.access_token:
                return None

            if session.access_token != st.session_state.get("auth_token"):
                st.session_state.auth_token = session.access_token
                if session.refresh_token:
                    st.session_state.refresh_token = session.refresh_token

            user = self.db.auth.get_user()
            return self.fetch_user_data(user.user.id) if user and user.user else None
        except Exception:
            return None

    def register(self, email, password, full_name):
        """Create a new user account."""
        try:
            response = self.db.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"name": full_name}},
            })

            if not response.user:
                return False, "Account creation failed"

            profile = {
                "id": response.user.id,
                "email": email,
                "name": full_name,
                "created_at": datetime.now().isoformat(),
            }
            self.db.table("users").insert(profile).execute()

            if response.session:
                st.session_state.auth_token = response.session.access_token
                st.session_state.refresh_token = response.session.refresh_token
                st.session_state.user = profile

            return True, profile

        except Exception as err:
            msg = str(err).lower()
            if "duplicate" in msg or "already registered" in msg:
                return False, "This email is already registered"
            return False, f"Registration error: {err}"

    def login(self, email, password):
        """Sign in with email and password."""
        try:
            try:
                self.db.auth.sign_out()
            except Exception:
                pass

            response = self.db.auth.sign_in_with_password({"email": email, "password": password})

            if response and response.user:
                profile = self.fetch_user_data(response.user.id)
                if not profile:
                    return False, "User profile not found"

                st.session_state.auth_token = response.session.access_token
                st.session_state.refresh_token = response.session.refresh_token
                st.session_state.user = profile
                return True, profile

            return False, "Login failed — unexpected response"
        except Exception as err:
            return False, str(err)

    def logout(self):
        """Sign out and wipe session state."""
        try:
            self.db.auth.sign_out()
        except Exception:
            pass

        try:
            from auth.session_manager import AppSession
            AppSession.wipe_session()
            return True, None
        except Exception as err:
            return False, str(err)

    def fetch_user_data(self, user_id):
        """Retrieve user profile from the database."""
        try:
            res = self.db.table("users").select("*").eq("id", user_id).single().execute()
            return res.data if res else None
        except Exception:
            return None

    def create_session(self, user_id, title=None):
        """Create a new analysis session for the user."""
        try:
            now = datetime.now()
            session_title = title or f"{now.strftime('%d-%m-%Y')} | {now.strftime('%H:%M:%S')}"
            payload = {
                "user_id": user_id,
                "title": session_title,
                "created_at": now.isoformat(),
            }
            res = self.db.table("chat_sessions").insert(payload).execute()
            return True, res.data[0] if res.data else None
        except Exception as err:
            return False, str(err)

    def get_sessions(self, user_id):
        """Retrieve all sessions for a user, newest first."""
        try:
            res = (
                self.db.table("chat_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return True, res.data
        except Exception as err:
            st.error(f"Could not fetch sessions: {err}")
            return False, []

    def save_message(self, session_id, content, role="user"):
        """Save a chat message to the database."""
        try:
            payload = {
                "session_id": session_id,
                "content": content,
                "role": role,
                "created_at": datetime.now().isoformat(),
            }
            res = self.db.table("chat_messages").insert(payload).execute()
            return True, res.data[0] if res.data else None
        except Exception as err:
            return False, str(err)

    def get_messages(self, session_id):
        """Retrieve all messages in a session, ordered by time."""
        try:
            res = (
                self.db.table("chat_messages")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            return True, res.data
        except Exception as err:
            return False, str(err)

    def remove_session(self, session_id):
        """Delete a session and all its messages."""
        try:
            self.db.table("chat_messages").delete().eq("session_id", session_id).execute()
            self.db.table("chat_sessions").delete().eq("id", session_id).execute()
            return True, None
        except Exception as err:
            st.error(f"Delete failed: {err}")
            return False, str(err)

    def validate_session_token(self):
        """Public method to validate the current session token."""
        return self._validate_token()
