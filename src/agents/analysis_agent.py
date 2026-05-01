from datetime import datetime, timedelta
import streamlit as st
from agents.model_manager import ModelManager


class ReportAnalyzer:
    """
    Manages the report analysis workflow including rate limiting,
    data preprocessing, and building context from previous analyses.
    """

    def __init__(self):
        self.model_manager = ModelManager()
        self._setup_state()

    def _setup_state(self):
        """Set up Streamlit session state variables for tracking."""
        defaults = {
            "reports_analyzed_today": 0,
            "last_reset_time": datetime.now(),
            "daily_limit": 15,
            "model_usage_stats": {},
            "insights_cache": {},
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    def check_rate_limit(self):
        """Check whether the user can perform another analysis today."""
        elapsed = datetime.now() - st.session_state.last_reset_time
        time_left = timedelta(days=1) - elapsed
        hrs, rem = divmod(time_left.seconds, 3600)
        mins, _ = divmod(rem, 60)

        if time_left.days < 0:
            st.session_state.reports_analyzed_today = 0
            st.session_state.last_reset_time = datetime.now()
            return True, None

        if st.session_state.reports_analyzed_today >= st.session_state.daily_limit:
            return False, f"Daily limit reached. Resets in {hrs}h {mins}m"

        return True, None

    def analyze_report(self, data, system_prompt, check_only=False, chat_history=None):
        """
        Analyze a blood report using available LLM models.

        Args:
            data: Dict containing patient info and report text
            system_prompt: Base instruction prompt for the model
            check_only: If True, only validate rate limit without analyzing
            chat_history: Optional previous messages for context
        """
        allowed, error = self.check_rate_limit()
        if not allowed:
            return {"success": False, "error": error}

        if check_only:
            return allowed, error

        clean_data = self._clean_input(data)
        final_prompt = (
            self._build_context_prompt(system_prompt, clean_data, chat_history)
            if chat_history
            else system_prompt
        )

        result = self.model_manager.run_analysis(clean_data, final_prompt)

        if result["success"]:
            self._record_usage(result)
            self._store_insights(clean_data, result["content"])

        return result

    def _record_usage(self, result):
        """Track successful analysis count and model usage."""
        st.session_state.reports_analyzed_today += 1
        st.session_state.last_reset_time = datetime.now()

        model = result.get("model_used", "unknown")
        stats = st.session_state.model_usage_stats
        stats[model] = stats.get(model, 0) + 1

    def _store_insights(self, data, analysis_text):
        """
        Cache key insights from the analysis for future in-context learning.
        Associates findings with specific biomarkers and patient profiles.
        """
        if not isinstance(data, dict) or "report" not in data:
            return

        report_lower = data["report"].lower()
        profile_key = f"{data.get('age', 'unknown')}-{data.get('gender', 'unknown')}"

        biomarkers = [
            "hemoglobin", "glucose", "cholesterol", "triglycerides",
            "hdl", "ldl", "wbc", "rbc", "platelet", "creatinine",
        ]

        for marker in biomarkers:
            if marker not in report_lower:
                continue
            if marker not in analysis_text.lower():
                continue

            cache = st.session_state.insights_cache
            if marker not in cache:
                cache[marker] = {}
            if profile_key not in cache[marker]:
                cache[marker][profile_key] = []

            relevant_lines = [
                line for line in analysis_text.split("\n") if marker in line.lower()
            ]
            if relevant_lines:
                entries = cache[marker][profile_key]
                if len(entries) >= 3:
                    entries.pop(0)
                entries.append(relevant_lines[0])

    def _build_context_prompt(self, base_prompt, data, chat_history):
        """Enrich the prompt with cached insights and session history."""
        enriched = base_prompt

        if isinstance(data, dict) and "report" in data:
            cached = self._retrieve_cached_insights(data)
            if cached:
                enriched += "\n\n## Insights from Previous Analyses\n" + cached

        if chat_history:
            history_ctx = self._summarize_history(chat_history)
            if history_ctx:
                enriched += "\n\n## Recent Conversation Context\n" + history_ctx

        return enriched

    def _retrieve_cached_insights(self, data):
        """Pull relevant cached insights for the current report."""
        cache = st.session_state.get("insights_cache", {})
        if not cache:
            return ""

        report_lower = data.get("report", "").lower()
        profile_key = f"{data.get('age', 'unknown')}-{data.get('gender', 'unknown')}"
        items = []

        for marker, profiles in cache.items():
            if marker not in report_lower:
                continue
            if profile_key in profiles:
                for note in profiles[profile_key]:
                    items.append(f"- {marker} (similar profile): {note}")
            for pk, notes in profiles.items():
                if pk != profile_key:
                    for note in notes:
                        items.append(f"- {marker} (other profile): {note}")

        return "\n".join(items[:5]) if items else ""

    def _summarize_history(self, chat_history):
        """Extract a brief summary from recent chat exchanges."""
        if not chat_history or len(chat_history) < 2:
            return ""

        snippets = []
        for i in range(len(chat_history) - 1, 0, -2):
            if (
                i >= 1
                and chat_history[i - 1]["role"] == "user"
                and chat_history[i]["role"] == "assistant"
            ):
                user_msg = chat_history[i - 1]["content"][:200]
                ai_msg = chat_history[i]["content"][:200]
                snippets.append(f"User: {user_msg}\nAssistant: {ai_msg}")
                if len(snippets) >= 2:
                    break

        return "\n\n".join(reversed(snippets))

    def _clean_input(self, data):
        """Strip unnecessary fields before sending to the model."""
        if isinstance(data, dict):
            return {
                "patient_name": data.get("patient_name", ""),
                "age": data.get("age", ""),
                "gender": data.get("gender", ""),
                "report": data.get("report", ""),
            }
        return data
