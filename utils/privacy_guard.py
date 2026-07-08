import logging
import re

# Regex fallbacks when Presidio is unavailable (common PII patterns)
_PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "<EMAIL>"),
    (re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "<PHONE>"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"), "<DATE>"),
    (re.compile(r"\b(?:MRN|Patient ID|ID)\s*[:#]?\s*\w+\b", re.IGNORECASE), "<PATIENT_ID>"),
]

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    presidio_available = True
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
except ImportError:
    presidio_available = False
    logging.warning("Presidio packages not found. Using regex-based text redaction fallback.")
except Exception as e:
    presidio_available = False
    logging.warning(f"Failed to initialize Presidio: {e}")


def _regex_redact(text: str) -> str:
    redacted = text
    for pattern, replacement in _PII_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text

    if presidio_available:
        try:
            results = analyzer.analyze(text=text, language="en")
            anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized_result.text
        except Exception as e:
            logging.error(f"Presidio anonymization failed: {e}")

    return _regex_redact(text)


def sanitize_input(input_data, input_type):
    """
    Sanitizes input data to reduce PII exposure before LLM inference.

    - text: Presidio redaction, or regex fallback
    - image / pdf_images: instruction-only (pixels are not modified); caller must
      avoid logging or storing raw uploads

    Returns:
        tuple: (sanitized_data, system_instruction_to_append)
    """
    system_instruction = ""
    sanitized_data = input_data

    if input_type == "text":
        sanitized_data = _redact_text(input_data)

    elif input_type in ("image", "pdf_images"):
        system_instruction = (
            "CRITICAL PRIVACY RULE: Do NOT output patient names, hospital names, "
            "addresses, phone numbers, dates of birth, MRN/ID numbers, or signatures "
            "visible in this image. Treat all identifying fields as redacted. "
            "Focus only on clinical values and medical findings."
        )
        sanitized_data = input_data

    return sanitized_data, system_instruction
