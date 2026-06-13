import fitz  # PyMuPDF
import os
import re
from claude_client import extract_requirements


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF given its raw bytes.
    Returns concatenated text from all pages.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    full_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            full_text.append(f"[Page {page_num + 1}]\n{text.strip()}")

    doc.close()
    return "\n\n".join(full_text)


def clean_text(text: str) -> str:
    """
    Remove excessive whitespace, null bytes, and garbage characters
    that often appear in government PDF extractions.
    """
    # Remove null bytes
    text = text.replace("\x00", "")

    # Normalize multiple newlines to double newline
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Remove non-printable characters except newlines and tabs
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u0080-\uFFFF]", "", text)

    return text.strip()


def parse_rfp(file_bytes: bytes) -> dict:
    """
    Full pipeline: PDF bytes → clean text → Claude extraction → structured dict.

    Returns:
    {
        "raw_text": str,
        "requirements": {
            "mandatory_requirements": [...],
            "evaluation_criteria": [...],
            "deadlines": [...],
            "key_questions": [...],
            "sector": str,
            "budget_pkr": int
        }
    }
    """
    # Step 1: Extract raw text
    raw_text = extract_text_from_pdf(file_bytes)

    if not raw_text.strip():
        raise ValueError("PDF appears to be empty or image-based (no extractable text).")

    # Step 2: Clean the text
    cleaned_text = clean_text(raw_text)

    # Step 3: Send to Claude for structured extraction
    requirements = extract_requirements(cleaned_text)

    # Step 4: Validate required keys exist
    required_keys = [
        "mandatory_requirements",
        "evaluation_criteria",
        "deadlines",
        "key_questions",
        "sector",
        "budget_pkr"
    ]
    for key in required_keys:
        if key not in requirements:
            if key in ("sector",):
                requirements[key] = "Other"
            elif key in ("budget_pkr",):
                requirements[key] = 0
            else:
                requirements[key] = []

    # Step 5: Ensure list fields are actually lists
    for list_key in ["mandatory_requirements", "evaluation_criteria", "deadlines", "key_questions"]:
        if not isinstance(requirements[list_key], list):
            requirements[list_key] = [str(requirements[list_key])]

    # Step 6: Ensure budget is int
    try:
        requirements["budget_pkr"] = int(requirements["budget_pkr"])
    except (ValueError, TypeError):
        requirements["budget_pkr"] = 0

    # Step 7: Split any bundled requirements into individual items
    split_markers = [
        ". The firm MUST",
        ". Bidders MUST",
        ". The vendor MUST",
        ". The contractor MUST",
        ". Vendor MUST",
    ]
    split_reqs = []
    for req in requirements["mandatory_requirements"]:
        # Replace each marker with a split sentinel
        modified = req
        for marker in split_markers:
            sentinel_marker = marker.replace(". ", ".|SPLIT|")
            modified = modified.replace(marker, sentinel_marker)
        parts = [p.strip() for p in modified.split(".|SPLIT|")]
        split_reqs.extend([p for p in parts if p.strip()])

    requirements["mandatory_requirements"] = split_reqs

    return {
        "raw_text": cleaned_text,
        "requirements": requirements
    }
