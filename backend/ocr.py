# ocr_service.py
from typing import List
from transformers import pipeline
from PIL import Image
import torch

# Determine device
device = 0 if torch.backends.mps.is_available() else -1  # 0 = MPS, -1 = CPU

# Initialize the OCR pipeline forcing float32 to avoid bf16 issues
ocr_pipeline = pipeline(
    "image-to-text",
    model="nanonets/Nanonets-OCR2-3B",
    device=device,             # MPS device
    torch_dtype=torch.float32  # Force FP32 (bf16 not supported on MPS)
)

def run_ocr(image_path: str) -> str:
    """
    Run OCR on a given image file path and return the extracted text.
    """
    try:
        # Open image to ensure compatibility
        image = Image.open(image_path).convert("RGB")
        result = ocr_pipeline(image)

        # Transformers pipeline returns a list of dicts with 'generated_text'
        if result and isinstance(result, list):
            text = '\n'.join([r.get('generated_text', '') for r in result])
        else:
            text = ''
        return text
    except Exception as e:
        print(f"OCR failed for {image_path}: {e}")
        return ''

def extract_sentences(path: str) -> List[str]:
    """
    Get the list of sentences from the document file at path
    """
    if path.endswith('.txt'):
        with open(path) as f:
            text = f.read()
    elif path.endswith('.png') or path.endswith('.jpg'):
        text = run_ocr(path)
    else:
        raise NotImplementedError(f"OCR not implemented for file type: {path}")
    
    # naive sentence splitting by periods
    sentences = [sentence.strip() for sentence in text.split('.') if sentence.strip()]
    return sentences
