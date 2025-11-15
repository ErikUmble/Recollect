# ocr_service.py
from vllm import LLM, CompletionConfig

# Initialize the LLM with Nanonets OCR model
llm = LLM(model='nanonets/Nanonets-OCR2-3B')

# Function to run OCR on a given image file path
def run_ocr(image_path):
    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    config = CompletionConfig(max_output_tokens=1024)
    # The model expects the image bytes in a special input format
    # Here we assume the model can take raw bytes as input (adapt if needed)
    result = llm.complete([{"image": image_bytes}], config)

    # Extract predicted text
    # The exact structure may vary depending on the vLLM Nanonets wrapper
    text = result[0].text if result else ''
    return text

def extract_sentences(path: str) -> List[str]:
    """
    Get the list of sentences from the document file at path
    """
    raise NotImplementedError()
