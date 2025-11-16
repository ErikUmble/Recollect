"""
Image utility functions.
Specifically, this provides functions for extracting sub-images
from document scans such as from newspapers.
"""

import cv2
import numpy as np
import argparse
from pathlib import Path
import sys
from PIL import Image
from typing import List

def calculate_iou(box1, box2):
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Boxes are in format (x, y, w, h).
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Calculate intersection rectangle
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - intersection_area
    
    return intersection_area / union_area if union_area > 0 else 0

def non_max_suppression(boxes, iou_threshold=0.3, keep_smallest=True):
    """
    Remove overlapping bounding boxes using Non-Maximum Suppression.
    Keeps smaller boxes when there's significant overlap (or larger boxes if keep_smallest is False).
    """
    if len(boxes) == 0:
        return []
    
    # Sort by area (smallest first if keep_smallest is True, largest first otherwise)
    boxes_with_area = [(box, box[2] * box[3]) for box in boxes]
    boxes_with_area.sort(key=lambda x: x[1], reverse=not keep_smallest)
    
    keep = []
    while boxes_with_area:
        current_box, _ = boxes_with_area.pop(0)
        keep.append(current_box)
        
        # Remove boxes that overlap significantly with current box
        boxes_with_area = [
            (box, area) for box, area in boxes_with_area
            if calculate_iou(current_box, box) < iou_threshold
        ]
    
    return keep

def is_likely_text_box(region, gray_img, x, y, w, h):
    """
    Determine if a region is likely to be a text box/ad rather than an image.
    Text boxes typically have:
    - Higher edge density (lots of fine edges from text)
    - More uniform intensity distribution
    - Horizontal line patterns (text lines)
    """
    # Extract the region
    roi = gray_img[y:y+h, x:x+w]
    
    # 1. Check edge density (text has many fine edges)
    edges = cv2.Canny(roi, 50, 150)
    edge_density = np.sum(edges > 0) / (w * h)
    
    # 2. Check for horizontal line patterns (text lines)
    # Use horizontal morphological operation
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 4, 1))
    horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, horizontal_kernel)
    horizontal_line_density = np.sum(horizontal_lines > 0) / (w * h)
    
    # 3. Check variance (images typically have higher variance)
    variance = np.var(roi)
    
    # 4. Check if region is mostly white/empty (borders of ad boxes)
    mean_intensity = np.mean(roi)
    
    # Heuristics for text detection:
    # High edge density + horizontal lines + low variance = likely text
    is_text = False
    
    if edge_density > 0.15:  # High edge density suggests text
        is_text = True
    
    if horizontal_line_density > 0.1:  # Strong horizontal patterns suggest text lines
        is_text = True
    
    if variance < 500:  # Low variance suggests uniform content (text or border)
        is_text = True
    
    if mean_intensity > 200:  # Mostly white suggests empty ad box
        is_text = True
    
    # Images typically have moderate variance and lower edge density
    if variance > 1000 and edge_density < 0.1:
        is_text = False
    
    return is_text

def detect_images(img_path, 
                min_area=5000, 
                max_area_ratio=1.0,
                min_aspect_ratio=0.3,
                max_aspect_ratio=3.0,
                iou_threshold=0.3,
                filter_text_boxes=False,):
    """
    Improved image detection with overlap removal and text box filtering.
    
    Parameters:
    - min_area: Minimum area in pixels for detected regions
    - max_area_ratio: Maximum area as fraction of total image
    - min_aspect_ratio: Minimum width/height ratio
    - max_aspect_ratio: Maximum width/height ratio
    - iou_threshold: IoU threshold for non-max suppression (lower = more aggressive)
    - filter_text_boxes: Whether to filter out likely text boxes
    """
    
    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Could not read image: {img_path}")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_area = gray.shape[0] * gray.shape[1]
    max_area = img_area * max_area_ratio
    
    # Basic thresholding and contour detection
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter by size and aspect ratio
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        aspect_ratio = w / h if h > 0 else 0
        
        if (area > min_area and 
            area < max_area and 
            min_aspect_ratio < aspect_ratio < max_aspect_ratio):
            boxes.append((x, y, w, h))
    
    
    # Apply non-maximum suppression to remove overlaps
    boxes = non_max_suppression(boxes, iou_threshold=iou_threshold)

    if filter_text_boxes:
        filtered_boxes = []
        for x, y, w, h in boxes:
            roi = gray[y:y+h, x:x+w]
            if not is_likely_text_box(roi, gray, x, y, w, h):
                filtered_boxes.append((x, y, w, h))
        
        boxes = filtered_boxes
    

    # filter out images with too high proportion of white pixels (likely false positive, or text only)
    final_boxes = []
    for x, y, w, h in boxes[:]:
        roi = gray[y:y+h, x:x+w]
        num_white = np.sum(roi > 180)
        num_white_ratio = num_white / (w * h)
        if num_white_ratio > 0.5:
            continue
        final_boxes.append((x, y, w, h))
    
    return final_boxes, img, gray

def draw_boxes(img, boxes, color=(0, 255, 0), thickness=3):
    """Draw bounding boxes with labels on the image."""
    result = img.copy()
    
    for i, (x, y, w, h) in enumerate(boxes):
        # Draw rectangle
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
        
        # Add label with number and dimensions
        label = f"#{i+1}: {w}x{h}"
        
        # Put label background
        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(result, (x, y - label_h - 10), (x + label_w + 10, y), color, -1)
        
        # Put label text
        cv2.putText(result, label, (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (255, 255, 255), 2)
    
    return result

def visualize_detections(img_path, output_path=None):
    """Visualize detected images on the document."""
    boxes, img, _ = detect_images(img_path)
    img_with_boxes = draw_boxes(img, boxes)
    
    if output_path:
        cv2.imwrite(output_path, img_with_boxes)
        print(f"Saved visualization to {output_path}")
    else:
        cv2.imshow("Detected Images", img_with_boxes)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

def extract_images_from_document(img_path: str) -> List[Image.Image]:
    """Extract detected images from the document and return as list of PIL Images."""
    boxes, img, _ = detect_images(img_path)
    pil_images = []
    
    for (x, y, w, h) in boxes:
        roi = img[y:y+h, x:x+w]
        pil_img = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        pil_images.append(Image.fromarray(pil_img))
    
    return pil_images

def run_tests():
    import os
    from search import extract_file_paths
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "data")
    filepaths = extract_file_paths(test_data_dir, ('jpg',))

    os.makedirs('image_detection_visualizations', exist_ok=True)
    os.makedirs('extracted_images', exist_ok=True)
    for fp in filepaths[:3]:
        output_path = os.path.join('image_detection_visualizations', os.path.basename(fp))
        visualize_detections(fp, output_path=output_path)
        images = extract_images_from_document(fp)
        for i, img in enumerate(images):
            img.save(os.path.join('extracted_images', f"{os.path.basename(fp)}_img_{i+1}.png"))

if __name__ == "__main__":
    run_tests()