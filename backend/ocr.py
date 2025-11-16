# ocr_service.py
from typing import List
from PIL import Image

import pytesseract
import re

from utils import is_image_path

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

def extract_chunks(path: str) -> List[str]:
    """
    Get the list of chunks of text from the document file at path
    """
    if path.endswith('.txt'):
        with open(path) as f:
            text = f.read()
    elif is_image_path(path):
        text = run_ocr(path)
    else:
        raise NotImplementedError(f"OCR not implemented for file type: {path}")
    
    return ocr_to_chunks(text, max_words=250)

def clean_ocr_text(text: str) -> str:
    """Normalize common OCR artifacts."""
    
    # Normalize Unicode quotes and dashes
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    
    # Fix common OCR split-hyphen line breaks ("ad-\nvanced" -> "advanced")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Remove hyphens before spaces (e.g., "men ad- vanced")
    text = re.sub(r"(\w)-\s+(\w)", r"\1 \2", text)

    # Reduce multiple newlines to paragraph breaks
    text = re.sub(r"\n{2,}", "\n\n", text)

    # Strip weird indentation
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def paragraphs(text: str) -> List[str]:
    """Split the cleaned text into paragraphs."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_paragraphs(paragraphs: List[str], max_words=250) -> List[str]:
    """
    Break paragraphs into semantic chunks.
    max_words=250 is good for modern embedding models.
    """
    chunks = []
    for p in paragraphs:
        words = p.split()
        if len(words) <= max_words:
            chunks.append(p)
            continue

        # Split long paragraphs into sub-chunks
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i:i+max_words])
            chunks.append(chunk)

    return chunks


def ocr_to_chunks(text: str, max_words=250) -> List[str]:
    """Full pipeline: clean → paragraphs → chunks."""
    cleaned = clean_ocr_text(text)
    paras = paragraphs(cleaned)
    return chunk_paragraphs(paras, max_words=max_words)

def run_tests():
    import os
    from search import extract_file_paths
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "data", "The_Rensselaer_Polytechnic:_April_1,_1957")
    filepaths = extract_file_paths(test_data_dir, ('jpg',))

    print(filepaths[:3])
    texts = [run_ocr(fp) for fp in filepaths[:3]]
    
    with open('ocr_test_output.txt', 'a') as f:
        for fp, text in zip(filepaths[:3], texts):
            f.write(f"File: {fp}\n")
            f.write(f"Extracted Text:\n{text}\n")
            f.write("="*40 + "\n")

if __name__ == "__main__":
    run_tests()