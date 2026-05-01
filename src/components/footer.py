import streamlit as st
from config.app_config import PRIMARY_COLOR, SECONDARY_COLOR, APP_NAME


def show_footer(in_sidebar=False):
    """Render the app footer."""
    margin_top = "0" if in_sidebar else "2rem"

    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 0.75rem;
            background: linear-gradient(to right,
                rgba(76, 175, 147, 0.03),
                rgba(76, 175, 147, 0.07),
                rgba(76, 175, 147, 0.03)
            );
            border-top: 1px solid rgba(76, 175, 147, 0.2);
            margin-top: {margin_top};
            box-shadow: 0 -2px 10px rgba(76, 175, 147, 0.05);
        ">
            <p style="
                font-family: 'Source Sans Pro', sans-serif;
                color: {SECONDARY_COLOR};
                font-size: 0.78rem;
                letter-spacing: 0.02em;
                margin: 0;
                opacity: 0.9;
            ">
                🏥 <strong style="color: {PRIMARY_COLOR};">{APP_NAME}</strong>
                &nbsp;·&nbsp; AI-powered health report analysis
                &nbsp;·&nbsp; For informational use only
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
