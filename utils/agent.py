import json
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration
from utils.builder import build_prompt, validate_output
from utils.privacy_guard import sanitize_input

analyze_text_document = FunctionDeclaration(
    name="analyze_text_document",
    description="This tool analyzes medical documents that contain text or typed content such as lab reports, blood tests, prescriptions, discharge summaries, and typed MRI or radiology reports.",
    parameters={
        "type": "object",
        "properties": {
            "document_description": {"type": "string", "description": "Short description saying it is a typed or text-based medical document"}
        },
        "required": ["document_description"]
    }
)

analyze_visual_document = FunctionDeclaration(
    name="analyze_visual_document",
    description="This tool analyzes medical documents that are images or visual in nature such as ECG strips, X-ray images, CT scan images, echo test images, photos of handwritten prescriptions, and any scanned document image.",
    parameters={
        "type": "object",
        "properties": {
            "document_description": {"type": "string", "description": "Short description saying it is a visual, scanned, or handwritten medical image document"}
        },
        "required": ["document_description"]
    }
)

def _call_gemini_with_prompt_and_data(model, extracted_data, prompt):
    config = genai.types.GenerationConfig(response_mime_type="application/json")
    if extracted_data["type"] == "pdf_images":
        contents = [prompt] + extracted_data["content"]
        response = model.generate_content(contents, generation_config=config)
    elif extracted_data["type"] == "image":
        contents = [prompt, {"mime_type": extracted_data["mime_type"], "data": extracted_data["content"]}]
        response = model.generate_content(contents, generation_config=config)
    elif extracted_data["type"] == "text":
        contents = [prompt, extracted_data["content"]]
        response = model.generate_content(contents, generation_config=config)
    else:
        return None
    return response

def _parse_and_validate_json(text_output, model, extracted_data, prompt):
    def extract_json_str(text):
        # Handle case where API might still wrap in markdown
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    json_str = extract_json_str(text_output)
    try:
        parsed = json.loads(json_str)
        if validate_output(parsed):
            return parsed
    except json.JSONDecodeError:
        pass
        
    # Retry once
    retry_prompt = prompt + "\n\nCRITICAL FIX: Your last response was invalid JSON. You must return ONLY valid parsable JSON matching the exact schema. Do not use markdown code blocks like ```json."
    retry_response = _call_gemini_with_prompt_and_data(model, extracted_data, retry_prompt)
    if not retry_response:
        return None
        
    json_str = extract_json_str(retry_response.text)
    try:
        parsed = json.loads(json_str)
        if validate_output(parsed):
            return parsed
    except json.JSONDecodeError:
        pass
    
    return None

def _file_type_hint(extracted_data):
    t = extracted_data.get("type")
    if t == "pdf_images":
        return "A PDF document rendered as page images"
    if t == "image":
        return "An image file (JPG/PNG) such as a scan or photo"
    if t == "text":
        return "A text-based medical report"
    return "A medical document"


def run_agent(age, gender, language, extracted_data, model, skip_routing=False):
    file_type_hint = _file_type_hint(extracted_data)

    # Plain text inputs (evaluation path) skip routing — no visual ambiguity
    if extracted_data.get("type") == "text":
        skip_routing = True

    try:
        tool_name = "analyze_text_document"
        doc_desc = "typed or text-based medical document"

        if not skip_routing:
            routing_prompt = (
                f"The user uploaded {file_type_hint}. "
                "Which tool is more appropriate to analyze this type of file?"
            )
            routing_response = model.generate_content(
                routing_prompt,
                tools=[analyze_text_document, analyze_visual_document],
            )
            if routing_response.candidates and routing_response.candidates[0].content.parts:
                part = routing_response.candidates[0].content.parts[0]
                if hasattr(part, "function_call") and part.function_call:
                    tool_name = part.function_call.name
                    doc_desc = dict(part.function_call.args).get("document_description", doc_desc)

        analysis_mode = "visual" if tool_name == "analyze_visual_document" else "text"
        prompt = build_prompt(age, gender, language, doc_desc, analysis_mode=analysis_mode)
        
        sanitized_content, privacy_instruction = sanitize_input(extracted_data.get("content"), extracted_data.get("type"))
        extracted_data["content"] = sanitized_content
        if privacy_instruction:
            prompt += "\n\n" + privacy_instruction
        
        # 3. Main call
        response = _call_gemini_with_prompt_and_data(model, extracted_data, prompt)
        if not response:
            return {"error": "Failed to communicate with Gemini."}
            
        # 4. Parse and Validate
        parsed = _parse_and_validate_json(response.text, model, extracted_data, prompt)
        
        # Retry entire call once if validation fails
        if not parsed:
            response_retry = _call_gemini_with_prompt_and_data(model, extracted_data, prompt)
            parsed = _parse_and_validate_json(response_retry.text, model, extracted_data, prompt)
            
        if parsed:
            return parsed
        else:
             return {"error": "Failed to generate a valid action plan structure. Please try again."}

    except Exception as e:
        return {"error": f"An error occurred during analysis: {str(e)}"}
