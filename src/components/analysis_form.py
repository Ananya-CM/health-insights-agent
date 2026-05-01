import streamlit as st
from config.prompts import ANALYSIS_PROMPTS
from config.sample_data import SAMPLE_REPORT
from config.app_config import MAX_UPLOAD_SIZE_MB
from utils.pdf_extractor import extract_report_text


def show_analysis_form():
    """Display the report upload form and trigger analysis on submission."""
    if "current_session" in st.session_state and "input_mode" not in st.session_state:
        st.session_state.input_mode = "Upload Report"

    input_mode = st.radio(
        "Report source",
        ["Upload Report", "Use Sample Report"],
        index=0 if st.session_state.get("input_mode") == "Upload Report" else 1,
        horizontal=True,
        key="input_mode",
    )

    report_text = _get_report_text(input_mode)
    if report_text:
        _render_patient_form(report_text)


def _get_report_text(mode):
    """Extract and return report text based on user's chosen input mode."""
    if mode == "Upload Report":
        uploaded = st.file_uploader(
            f"Upload report (PDF, JPG, PNG — max {MAX_UPLOAD_SIZE_MB}MB)",
            type=["pdf", "jpg", "jpeg", "png", "webp"],
            help="Supports text-based PDFs and scanned image reports (JPG, PNG)",
        )
        if uploaded:
            size_mb = uploaded.size / (1024 * 1024)
            if size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(f"File is {size_mb:.1f}MB — exceeds the {MAX_UPLOAD_SIZE_MB}MB limit.")
                return None

            # Show spinner while extracting (images need AI OCR)
            filename = uploaded.name.lower()
            is_image = any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])

            if is_image:
                with st.spinner("Reading image with AI vision... this may take a moment"):
                    text = extract_report_text(uploaded)
            else:
                text = extract_report_text(uploaded)

            # Check for error messages returned as strings
            error_indicators = (
                "File", "Could not", "Failed", "Only", "PDF",
                "Unsupported", "error", "doesn't appear", "too large",
                "No file", "too short"
            )
            if isinstance(text, str) and any(text.startswith(e) or e.lower() in text.lower() for e in error_indicators):
                # Only show as error if it's clearly an error (not actual report content)
                if len(text) < 200:
                    st.error(text)
                    return None

            with st.expander("📄 Preview Extracted Text"):
                st.text(text)
            return text

    else:
        with st.expander("📄 View Sample Report"):
            st.text(SAMPLE_REPORT)
        return SAMPLE_REPORT

    return None


def _render_patient_form(report_text):
    """Render the patient details form."""
    with st.form("patient_form"):
        patient_name = st.text_input("Patient Name")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, step=1)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        submitted = st.form_submit_button("🔍 Analyze Report", type="primary")
        if submitted:
            _process_submission(patient_name, age, gender, report_text)


def _process_submission(patient_name, age, gender, report_text):
    """Validate inputs and trigger the report analysis."""
    if not all([patient_name, age, gender]):
        st.error("Please fill in all patient details.")
        return

    from services.ai_service import run_report_analysis

    can_proceed, limit_error = run_report_analysis(None, None, check_only=True)
    if not can_proceed:
        st.error(limit_error)
        st.stop()
        return

    with st.spinner("Analyzing your report..."):
        st.session_state.current_report_text = report_text

        st.session_state.auth_service.save_message(
            st.session_state.current_session["id"],
            f"Analyzing report for: {patient_name}",
            role="user",
        )

        result = run_report_analysis(
            {
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "report": report_text,
            },
            ANALYSIS_PROMPTS["health_report_analyzer"],
        )

        if result["success"]:
            metadata = f"__REPORT_TEXT__\n{report_text}\n__END_REPORT_TEXT__"
            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"],
                metadata,
                role="system",
            )

            output = result["content"]
            if "model_used" in result:
                output += f"\n\n*Analyzed using model: {result['model_used']}*"

            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"],
                output,
                role="assistant",
            )
            st.rerun()
        else:
            st.error(result["error"])
            st.stop()


def _render_patient_form(report_text):
    """Render the patient details form."""
    with st.form("patient_form"):
        patient_name = st.text_input("Patient Name")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, step=1)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        submitted = st.form_submit_button("🔍 Analyze Report", type="primary")
        if submitted:
            _process_submission(patient_name, age, gender, report_text)


def _process_submission(patient_name, age, gender, report_text):
    """Validate inputs and trigger the report analysis."""
    if not all([patient_name, age, gender]):
        st.error("Please fill in all patient details.")
        return

    from services.ai_service import run_report_analysis

    can_proceed, limit_error = run_report_analysis(None, None, check_only=True)
    if not can_proceed:
        st.error(limit_error)
        st.stop()
        return

    with st.spinner("Analyzing your report..."):
        st.session_state.current_report_text = report_text

        st.session_state.auth_service.save_message(
            st.session_state.current_session["id"],
            f"Analyzing report for: {patient_name}",
            role="user",
        )

        result = run_report_analysis(
            {
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "report": report_text,
            },
            ANALYSIS_PROMPTS["health_report_analyzer"],
        )

        if result["success"]:
            # Persist report text as a system message for future retrieval
            metadata = f"__REPORT_TEXT__\n{report_text}\n__END_REPORT_TEXT__"
            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"],
                metadata,
                role="system",
            )

            output = result["content"]
            if "model_used" in result:
                output += f"\n\n*Analyzed using model: {result['model_used']}*"

            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"],
                output,
                role="assistant",
            )
            st.rerun()
        else:
            st.error(result["error"])
            st.stop()
