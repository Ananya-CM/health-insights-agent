import groq
import streamlit as st
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class ModelPriority(Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    BACKUP = "backup"


class ModelManager:
    """
    Handles LLM selection with automatic fallback across model tiers.
    Tries the most capable model first, falls back on failure or rate limits.
    """

    MODELS = {
        ModelPriority.FIRST: {
            "name": "meta-llama/llama-4-maverick-17b-128e-instruct",
            "max_tokens": 2000,
            "temperature": 0.7,
        },
        ModelPriority.SECOND: {
            "name": "llama-3.3-70b-versatile",
            "max_tokens": 2000,
            "temperature": 0.7,
        },
        ModelPriority.THIRD: {
            "name": "llama-3.1-8b-instant",
            "max_tokens": 2000,
            "temperature": 0.7,
        },
        ModelPriority.BACKUP: {
            "name": "llama3-70b-8192",
            "max_tokens": 2000,
            "temperature": 0.7,
        },
    }

    def __init__(self):
        self.groq_client = None
        self._setup_client()

    def _setup_client(self):
        """Initialize the Groq API client."""
        try:
            self.groq_client = groq.Groq(api_key=st.secrets["GROQ_API_KEY"])
        except Exception as err:
            logger.error(f"Groq client setup failed: {err}")

    def run_analysis(self, input_data, system_prompt, attempt=0):
        """
        Send data to the LLM and return the analysis.
        Automatically retries with lower-tier models on failure.
        """
        if attempt > 3:
            return {"success": False, "error": "All available models failed. Please try again later."}

        priority_map = {
            0: ModelPriority.FIRST,
            1: ModelPriority.SECOND,
            2: ModelPriority.THIRD,
            3: ModelPriority.BACKUP,
        }

        priority = priority_map[attempt]
        model_cfg = self.MODELS[priority]
        model_name = model_cfg["name"]

        if not self.groq_client:
            logger.error("No Groq client available")
            return self.run_analysis(input_data, system_prompt, attempt + 1)

        try:
            logger.info(f"Using model: {model_name} (attempt {attempt + 1})")
            response = self.groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": str(input_data)},
                ],
                temperature=model_cfg["temperature"],
                max_tokens=model_cfg["max_tokens"],
            )

            return {
                "success": True,
                "content": response.choices[0].message.content,
                "model_used": model_name,
            }

        except Exception as err:
            err_str = str(err).lower()
            logger.warning(f"Model {model_name} failed: {err_str}")

            if "rate limit" in err_str or "quota" in err_str:
                time.sleep(2)

            return self.run_analysis(input_data, system_prompt, attempt + 1)
