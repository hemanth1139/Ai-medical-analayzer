import os
import io
import json
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import google.generativeai as genai
from dotenv import load_dotenv

from utils.agent import run_agent

# Load environment variables
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

app_model = genai.GenerativeModel('gemini-2.5-flash')

def create_base_image():
    """Generates a clean synthetic medical report image."""
    img = Image.new('RGB', (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    try:
        # Try to use a standard font if available, else fallback
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
        
    text = "PATIENT LAB REPORT\n\nTotal Cholesterol: 280 mg/dL  (High)\nHDL: 35 mg/dL  (Low)\nLDL: 190 mg/dL  (High)\n\nDiagnosis: Severe Hyperlipidemia"
    d.text((50, 50), text, fill=(0, 0, 0), font=font)
    return img

def apply_blur(img, radius=5):
    """Applies Gaussian Blur to simulate an out-of-focus smartphone camera."""
    return img.filter(ImageFilter.GaussianBlur(radius))

def apply_noise(img):
    """Adds salt and pepper noise to simulate poor sensor quality or dirty lenses."""
    pixels = img.load()
    for i in range(img.size[0]):
        for j in range(img.size[1]):
            rand = random.random()
            if rand < 0.05: # 5% black dots
                pixels[i, j] = (0, 0, 0)
            elif rand < 0.10: # 5% white dots
                pixels[i, j] = (255, 255, 255)
    return img

def apply_low_lighting(img):
    """Reduces brightness drastically to simulate poorly lit rural clinics."""
    enhancer = ImageEnhance.Brightness(img)
    return enhancer.enhance(0.2) # 80% darker

def evaluate_robustness():
    print("Starting Adversarial Robustness Evaluation for Low-Quality Scans...")
    
    clean_img = create_base_image()
    
    # 1. Define our adversarial test suite
    test_cases = [
        {"name": "Clean Baseline", "img": clean_img},
        {"name": "Gaussian Blur (Radius 3)", "img": apply_blur(clean_img.copy(), 3)},
        {"name": "Heavy Blur (Radius 6)", "img": apply_blur(clean_img.copy(), 6)},
        {"name": "Sensor Noise (10%)", "img": apply_noise(clean_img.copy())},
        {"name": "Extreme Low Light", "img": apply_low_lighting(clean_img.copy())}
    ]
    
    results = {}
    
    # 2. Iterate through degraded images and run through the LLM pipeline
    for case in test_cases:
        print(f"Testing optical condition: {case['name']}...")
        
        # Convert PIL image to bytes for the API
        img_byte_arr = io.BytesIO()
        case["img"].save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        
        # Format payload matching `utils/extractor.py` image output
        extracted_data = {
            "type": "image",
            "content": img_bytes,
            "mime_type": "image/jpeg"
        }
        
        try:
            # We use a fixed 45-year-old male persona to keep the diagnostic baseline identical
            result = run_agent("45", "Male", "English", extracted_data, app_model)
        except Exception as e:
            result = {"error": str(e)}
            
        results[case['name']] = result
        
    # 3. Analyze Robustness and Degradation Curve
    baseline_status = results["Clean Baseline"].get("health_status", "Unknown")
    success_count = 0
    
    # 4. Generate IEEE-ready markdown table
    markdown_output = "## Adversarial Robustness Evaluation Results (Visual Degradation)\n\n"
    markdown_output += "This experiment tests the Medical Vision LLM's **Diagnostic Degradation Curve** when presented with increasingly corrupted medical imagery, simulating real-world low-resource clinic conditions (poor lighting, old smartphones, out-of-focus lenses).\n\n"
    
    markdown_output += "| Image Condition | Extracted Health Status | Extracted Diet Advice | Diagnostic Drift (Pass/Fail) |\n"
    markdown_output += "|-----------------|-------------------------|-----------------------|------------------------------|\n"
    
    for name, result in results.items():
        if "error" in result:
            status = f"ERROR: {result['error']}"
            diet = ""
            drift = "❌ FAIL"
        else:
            status = result.get('health_status', 'Failed to Extract')
            # Extract first two foods to keep the table clean
            diet = ", ".join(result.get('foods_to_avoid', [])[:2])
            
            if name == "Clean Baseline":
                drift = "✅ BASELINE"
            else:
                if status == baseline_status:
                    drift = "✅ PASS (Robust)"
                    success_count += 1
                elif status in ["Good", "Unknown"]:
                    # Failing to diagnose high cholesterol because of blur is a critical false negative
                    drift = "❌ FAIL (Dangerous False Negative)"
                else:
                    drift = "⚠️ PARTIAL DRIFT"
                    
        markdown_output += f"| **{name}** | {status} | {diet} | {drift} |\n"
        
    robustness_score = (success_count / (len(test_cases) - 1)) * 100
    markdown_output += f"\n**Overall Visual Robustness Score**: **{robustness_score:.1f}%**\n"
    markdown_output += "\n> Note: A pass indicates the model correctly saw through the adversarial noise to extract the high cholesterol values and maintain the 'Needs Attention / Critical' health status pipeline.\n"
    
    output_filename = "robustness_evaluation_results.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(markdown_output)
        
    print(f"\nEvaluation Complete! Visual Robustness Score: {robustness_score:.1f}%")
    print(f"Results successfully saved to '{output_filename}'.")

if __name__ == "__main__":
    evaluate_robustness()
