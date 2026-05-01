import re
from config.app_config import MAX_UPLOAD_SIZE_MB


def check_password_strength(pwd):
    """Validate password meets minimum security requirements."""
    if len(pwd) < 8:
        return False, "Password must be at least 8 characters"
    if not any(ch.isupper() for ch in pwd):
        return False, "Password must include at least one uppercase letter"
    if not any(ch.islower() for ch in pwd):
        return False, "Password must include at least one lowercase letter"
    if not any(ch.isdigit() for ch in pwd):
        return False, "Password must include at least one digit"
    return True, None


def is_valid_email(email):
    """Check if email address format is valid."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))


def validate_signup_fields(full_name, email, password, confirm_password):
    """Run all validations for the signup form."""
    if not all([full_name, email, password, confirm_password]):
        return False, "All fields are required"

    if not is_valid_email(email):
        return False, "Enter a valid email address"

    if password != confirm_password:
        return False, "Passwords do not match"

    ok, msg = check_password_strength(password)
    if not ok:
        return False, msg

    return True, None


def validate_pdf_file(uploaded_file):
    """Validate the uploaded PDF for size and MIME type."""
    if not uploaded_file:
        return False, "No file provided"

    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        return False, f"File too large ({size_mb:.1f}MB). Limit is {MAX_UPLOAD_SIZE_MB}MB"

    if uploaded_file.type != 'application/pdf':
        return False, "Only PDF files are accepted"

    return True, None


def validate_image_file(uploaded_file):
    """Validate the uploaded image file for size and type."""
    if not uploaded_file:
        return False, "No file provided"

    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        return False, f"File too large ({size_mb:.1f}MB). Limit is {MAX_UPLOAD_SIZE_MB}MB"

    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if uploaded_file.type not in allowed_types:
        return False, "Unsupported format. Please upload JPG or PNG."

    return True, None


def validate_report_content(text):
    """Check if extracted text looks like a medical report."""
    medical_keywords = [
        # Blood test
        'blood', 'test', 'report', 'laboratory', 'lab', 'patient',
        'reference range', 'analysis', 'results', 'medical', 'diagnostic',
        'hemoglobin', 'wbc', 'rbc', 'platelet', 'glucose', 'creatinine',
        # Thyroid
        'thyroid', 'tsh', 'thyroxin', 't3', 't4', 'hormome', 'serum',
        'immunology', 'diagnostics', 'cmia',
        # Ultrasound / Radiology
        'ultrasound', 'ultrasonography', 'usg', 'scan', 'liver', 'kidney',
        'uterus', 'ovaries', 'spleen', 'pancreas', 'impression', 'radiologist',
        'echo', 'sonology', 'pelvic', 'abdominal', 'gallbladder',
        # General medical
        'doctor', 'physician', 'hospital', 'clinic', 'specimen', 'sample',
        'normal', 'abnormal', 'finding', 'value', 'unit', 'range'
    ]

    if len(text.strip()) < 30:
        return False, "Extracted text is too short. Please upload a clearer image."

    text_lower = text.lower()
    matches = sum(1 for kw in medical_keywords if kw in text_lower)

    if matches < 2:
        return False, "This doesn't appear to be a medical report. Please upload a valid report."

    return True, None
