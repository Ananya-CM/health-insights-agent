import time
import streamlit as st
from auth.session_manager import AppSession
from config.app_config import APP_ICON, APP_NAME, APP_TAGLINE, APP_DESCRIPTION
from utils.validators import validate_signup_fields


def show_login_page():
    """Render the login or signup page based on current form state."""
    if "active_form" not in st.session_state:
        st.session_state.active_form = "login"

    form = st.session_state.active_form

    # Hide Streamlit form helper text
    st.markdown("""
        <style>
            div[data-testid="InputInstructions"] > span:nth-child(1) {
                visibility: hidden;
            }
        </style>
    """, unsafe_allow_html=True)

    heading = "Welcome back!" if form == "login" else "Create an account"
    st.markdown(f"""
        <div style="text-align: center; padding: 2rem;">
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>{APP_DESCRIPTION}</h3>
            <p style="font-size: 1.1em; color: #777; margin-bottom: 1em;">{APP_TAGLINE}</p>
            <h3>{heading}</h3>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if form == "login":
            _render_login_form()
        else:
            _render_signup_form()

        st.markdown("---")
        toggle_label = (
            "Don't have an account? Sign up"
            if form == "login"
            else "Already have an account? Log in"
        )
        if st.button(toggle_label, use_container_width=True, type="secondary"):
            st.session_state.active_form = "signup" if form == "login" else "login"
            st.rerun()


def _render_login_form():
    """Render the login form fields."""
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.form_submit_button("Log In", use_container_width=True, type="primary"):
            if email and password:
                success, result = AppSession.sign_in(email, password)
                if success:
                    with st.spinner("Logging in..."):
                        st.success("Login successful! Loading your dashboard...")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error(f"Login failed: {result}")
            else:
                st.error("Please enter your email and password")


def _render_signup_form():
    """Render the registration form fields."""
    with st.form("signup_form"):
        full_name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

        st.markdown("""
            **Password requirements:**
            - Minimum 8 characters
            - At least one uppercase letter
            - At least one lowercase letter
            - At least one number
        """)

        if st.form_submit_button("Create Account", use_container_width=True, type="primary"):
            valid, error = validate_signup_fields(full_name, email, password, confirm)
            if not valid:
                st.error(error)
                return

            with st.spinner("Setting up your account..."):
                success, response = st.session_state.auth_service.register(
                    email, password, full_name
                )
                if success:
                    st.session_state.user = response
                    st.success("Account created! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Sign up failed: {response}")
