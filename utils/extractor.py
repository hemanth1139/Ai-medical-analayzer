import fitz  # PyMuPDF
import io

def extract_content(uploaded_file):
    if uploaded_file is None:
        return {"type": "error", "message": "No file uploaded."}

    file_name = uploaded_file.name.lower()
    
    try:
        if file_name.endswith('.pdf'):
            pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            images = []
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("jpeg")
                images.append({
                    "mime_type": "image/jpeg",
                    "data": img_bytes
                })
            pdf_document.close()
            return {"type": "pdf_images", "content": images}
            
        elif file_name.endswith(('.png', '.jpg', '.jpeg')):
            raw_bytes = uploaded_file.read()
            mime_type = "image/png" if file_name.endswith('.png') else "image/jpeg"
            return {
                "type": "image", 
                "content": raw_bytes, 
                "mime_type": mime_type
            }
        else:
            return {
                "type": "error", 
                "message": "Unsupported file. Please upload a PDF, JPG, JPEG, or PNG file."
            }
    except Exception as e:
        return {"type": "error", "message": f"Error processing file: {str(e)}"}
