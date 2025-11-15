# ocr_service.py
from typing import List
from PIL import Image

import pytesseract
from PIL import Image

def run_ocr(image_path: str) -> str:
    """
    Run OCR on a document image using Tesseract.
    """
    try:
        image = Image.open(image_path).convert("RGB")
        text = pytesseract.image_to_string(image)
        return text.strip()
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

def run_tests():
    import os
    from search import extract_file_paths
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "data")
    filepaths = extract_file_paths(test_data_dir, ('jpg',))

    print(filepaths[:3])
    texts = [run_ocr(fp) for fp in filepaths[:3]]
    print(texts)

if __name__ == "__main__":
    run_tests()