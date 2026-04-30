import logging

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    presidio_available = True
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
except ImportError:
    presidio_available = False
    logging.warning("Presidio packages not found. Text anonymization will default to a safe state.")
except Exception as e:
    presidio_available = False
    logging.warning(f"Failed to initialize Presidio: {e}")

def sanitize_input(input_data, input_type):
    """
    Sanitizes the input data to remove PII.
    
    Args:
        input_data: The data to sanitize. For text, it's a string. 
                    For image/pdf_images, it's bytes or list of image dicts.
        input_type (str): 'text', 'image', or 'pdf_images'
        
    Returns:
        tuple: (sanitized_data, system_instruction_to_append)
    """
    system_instruction = ""
    sanitized_data = input_data
    
    if input_type == 'text':
        if not presidio_available:
            logging.warning("Presidio analyzer failed/unavailable. Defaulting to safe state: blocking text.")
            sanitized_data = "[TEXT REDACTED DUE TO UNAVAILABILITY OF PRIVACY SCANNER]"
        else:
            try:
                # Default entities cover PERSON, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION, etc.
                results = analyzer.analyze(text=input_data, language='en')
                anonymized_result = anonymizer.anonymize(text=input_data, analyzer_results=results)
                sanitized_data = anonymized_result.text
            except Exception as e:
                logging.error(f"Presidio anonymization failed: {e}")
                sanitized_data = "[TEXT REDACTED DUE TO PRIVACY SCANNER ERROR]"
                
    elif input_type in ['image', 'pdf_images']:
        system_instruction = 'CRITICAL: You are acting as a HIPAA-compliant parser. You MUST NOT transcribe, analyze, or output any patient names, hospital names, dates of birth, or contact information present in this image. Treat all such fields as strictly redacted.'
        # For image inputs, no modifications to the actual image data in this lightweight wrapper
        sanitized_data = input_data
        
    return sanitized_data, system_instruction
