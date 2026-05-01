import pdfplumber
import streamlit as st
import base64
from config.app_config import MAX_PDF_PAGES
from utils.validators import validate_pdf_file, validate_report_content


def extract_pdf_text(pdf_file):
    """Extract and validate text content from an uploaded PDF file."""
    try:
        valid, error = validate_pdf_file(pdf_file)
        if not valid:
            return error

        extracted_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                return f"PDF has too many pages. Maximum allowed is {MAX_PDF_PAGES}."

            for page in pdf.pages:
                page_text = page.extract_text()
                if not page_text:
                    return "Could not read text from PDF. Please ensure it is not a scanned image — try uploading as an image instead."
                extracted_text += page_text + "\n"

        valid, error = validate_report_content(extracted_text)
        if not valid:
            return error

        return extracted_text

    except Exception as err:
        return f"Failed to process PDF: {str(err)}"


def extract_image_text(image_file):
    """Extract text from a medical report image using Groq vision AI."""
    try:
        image_bytes = image_file.read()
        image_file.seek(0)

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        filename = image_file.name.lower()
        if filename.endswith(".png"):
            media_type = "image/png"
        elif filename.endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif filename.endswith(".webp"):
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"

        from groq import Groq
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])

        # Vision-capable models on Groq (in priority order)
        vision_models = [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.2-90b-vision-preview",
            "llama-3.2-11b-vision-preview",
        ]

        last_error = None
        for model in vision_models:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{base64_image}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "This is a medical report image. It could be a lab report, "
                                        "thyroid profile, blood test, ultrasound report, or scan image. "
                                        "Please extract ALL visible text, numbers, measurements, and findings "
                                        "exactly as they appear. For ultrasound images, extract all measurements, "
                                        "organ descriptions, and any printed text on the image. "
                                        "Preserve all values, units, and reference ranges. "
                                        "Do not interpret — only extract the raw text content."
                                    )
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                )
                extracted_text = response.choices[0].message.content

                valid, error = validate_report_content(extracted_text)
                if not valid:
                    return error

                return extracted_text

            except Exception as e:
                last_error = str(e)
                continue  # Try next model

        return f"Failed to process image with all available models. Last error: {last_error}"

    except Exception as err:
        return f"Failed to process image: {str(err)}"


def extract_report_text(uploaded_file):
    """
    Universal extractor — handles both PDFs and images.
    Returns extracted text string, or an error message string.
    """
    if uploaded_file is None:
        return "No file provided"

    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)
    elif filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return extract_image_text(uploaded_file)
    else:
        return "Unsupported file type. Please upload a PDF or image (JPG, PNG)."
