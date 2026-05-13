import streamlit as st
from config.prompts import ANALYSIS_PROMPTS
from config.sample_data import SAMPLE_REPORT
from config.app_config import MAX_UPLOAD_SIZE_MB
from utils.pdf_extractor import extract_report_text, extract_patient_info


def show_analysis_form():
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
        _render_patient_info_and_submit(report_text)


def _get_report_text(mode):
    if mode == "Upload Report":
        uploaded = st.file_uploader(
            f"Upload report (PDF, JPG, PNG — max {MAX_UPLOAD_SIZE_MB}MB)",
            type=["pdf", "jpg", "jpeg", "png", "webp"],
            help="Supports text-based PDFs and scanned/photographed reports",
        )
        if uploaded:
            size_mb = uploaded.size / (1024 * 1024)
            if size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(f"File is {size_mb:.1f}MB — exceeds the {MAX_UPLOAD_SIZE_MB}MB limit.")
                return None

            filename = uploaded.name.lower()
            is_image = any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])

            if is_image:
                with st.spinner("Reading image with AI vision..."):
                    text = extract_report_text(uploaded)
            else:
                with st.spinner("Extracting text from PDF..."):
                    text = extract_report_text(uploaded)

            error_triggers = ("File", "Could not", "Failed", "Only", "Unsupported",
                              "No file", "too short", "too large", "doesn't appear")
            if isinstance(text, str) and len(text) < 200:
                if any(text.startswith(e) or e.lower() in text.lower() for e in error_triggers):
                    st.error(text)
                    return None

            with st.expander("Preview Extracted Text"):
                st.text(text)
            return text
    else:
        with st.expander("View Sample Report"):
            st.text(SAMPLE_REPORT)
        return SAMPLE_REPORT
    return None


def _render_patient_info_and_submit(report_text):
    report_key = hash(report_text[:500])

    if st.session_state.get("extracted_report_key") != report_key:
        with st.spinner("Extracting patient details from report..."):
            info = extract_patient_info(report_text)
        st.session_state.extracted_patient_info = info
        st.session_state.extracted_report_key = report_key

    info = st.session_state.get("extracted_patient_info", {
        "name": "Not found", "age": "Not found", "gender": "Not found"
    })

    st.markdown("#### Patient Details (auto-extracted from report)")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div style="background:#EAF2F8;padding:0.75rem 1rem;border-radius:8px;border-left:4px solid #2A6F97;">
            <p style="margin:0;font-size:0.78rem;color:#555;">Patient Name</p>
            <p style="margin:0;font-size:1.05rem;font-weight:600;color:#1A2A38;">{info['name']}</p>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background:#EAF2F8;padding:0.75rem 1rem;border-radius:8px;border-left:4px solid #2A6F97;">
            <p style="margin:0;font-size:0.78rem;color:#555;">Age</p>
            <p style="margin:0;font-size:1.05rem;font-weight:600;color:#1A2A38;">{info['age']}</p>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div style="background:#EAF2F8;padding:0.75rem 1rem;border-radius:8px;border-left:4px solid #2A6F97;">
            <p style="margin:0;font-size:0.78rem;color:#555;">Gender</p>
            <p style="margin:0;font-size:1.05rem;font-weight:600;color:#1A2A38;">{info['gender']}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    any_missing = any(v == "Not found" for v in info.values())
    if any_missing:
        st.warning("Some details could not be found. Please enter them manually below.")
        with st.expander("Enter missing details manually", expanded=True):
            if info["name"] == "Not found":
                info["name"] = st.text_input("Patient Name", key="manual_name")
            if info["age"] == "Not found":
                info["age"] = str(st.number_input("Age", min_value=0, max_value=120, step=1, key="manual_age"))
            if info["gender"] == "Not found":
                info["gender"] = st.selectbox("Gender", ["Male", "Female", "Other"], key="manual_gender")
        st.session_state.extracted_patient_info = info

    if st.button("Analyze Report", type="primary", use_container_width=True):
        _process_submission(info["name"], info["age"], info["gender"], report_text)


def _process_submission(patient_name, age, gender, report_text):
    if not patient_name or patient_name == "Not found":
        st.error("Patient name could not be determined. Please enter it manually.")
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
            f"Analyzing report for: {patient_name}, Age: {age}, Gender: {gender}",
            role="user",
        )

        result = run_report_analysis(
            {"patient_name": patient_name, "age": age, "gender": gender, "report": report_text},
            ANALYSIS_PROMPTS["health_report_analyzer"],
        )

        if result["success"]:
            metadata = f"__REPORT_TEXT__\n{report_text}\n__END_REPORT_TEXT__"
            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"], metadata, role="system")

            output = result["content"]
            if "model_used" in result:
                output += f"\n\n*Analyzed using model: {result['model_used']}*"

            st.session_state.auth_service.save_message(
                st.session_state.current_session["id"], output, role="assistant")

            st.session_state.pop("extracted_patient_info", None)
            st.session_state.pop("extracted_report_key", None)
            st.rerun()
        else:
            st.error(result["error"])
            st.stop()