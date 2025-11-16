

def is_image_path(path: str) -> bool:
    # naive check based on file extension
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
    return any(path.lower().endswith(ext) for ext in image_extensions)