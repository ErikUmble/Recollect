#!/usr/bin/env python3
"""
Improved Newspaper Image Detection Script
Addresses false positives from ad boxes and overlapping detections.
"""

import cv2
import numpy as np
import argparse
from pathlib import Path
import sys


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


def non_max_suppression(boxes, iou_threshold=0.3):
    """
    Remove overlapping bounding boxes using Non-Maximum Suppression.
    Keeps smaller boxes when there's significant overlap.
    """
    if len(boxes) == 0:
        return []
    
    # Sort by area (smallest first)
    boxes_with_area = [(box, box[2] * box[3]) for box in boxes]
    boxes_with_area.sort(key=lambda x: x[1], reverse=False)
    
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


def detect_images_improved(img_path, 
                          min_area=5000, 
                          max_area_ratio=0.5,
                          min_aspect_ratio=0.3,
                          max_aspect_ratio=3.0,
                          iou_threshold=0.3,
                          filter_text_boxes=True,
                          debug=False):
    """
    Improved image detection with overlap removal and text box filtering.
    
    Parameters:
    - min_area: Minimum area in pixels for detected regions
    - max_area_ratio: Maximum area as fraction of total image
    - min_aspect_ratio: Minimum width/height ratio
    - max_aspect_ratio: Maximum width/height ratio
    - iou_threshold: IoU threshold for non-max suppression (lower = more aggressive)
    - filter_text_boxes: Whether to filter out likely text boxes
    - debug: Show intermediate processing steps
    """
    print(f"Processing: {img_path}")
    
    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Could not read image: {img_path}")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_area = gray.shape[0] * gray.shape[1]
    max_area = img_area * max_area_ratio
    
    # Step 1: Basic thresholding and contour detection
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    if debug:
        cv2.imwrite('debug_1_binary.jpg', binary)
        print("Saved debug_1_binary.jpg")
    
    # Step 2: Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Found {len(contours)} initial contours")
    
    # Step 3: Filter by size and aspect ratio
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        aspect_ratio = w / h if h > 0 else 0
        
        if (area > min_area and 
            area < max_area and 
            min_aspect_ratio < aspect_ratio < max_aspect_ratio):
            boxes.append((x, y, w, h))
    
    print(f"After size/aspect filtering: {len(boxes)} boxes")
    
    # Step 4: Apply non-maximum suppression to remove overlaps
    boxes = non_max_suppression(boxes, iou_threshold=iou_threshold)
    print(f"After overlap removal: {len(boxes)} boxes")
    
    # Step 5: Filter out text boxes/ads if enabled
    if filter_text_boxes:
        filtered_boxes = []
        for x, y, w, h in boxes:
            roi = gray[y:y+h, x:x+w]
            if not is_likely_text_box(roi, gray, x, y, w, h):
                filtered_boxes.append((x, y, w, h))
            else:
                if debug:
                    print(f"  Filtered out text box at ({x}, {y}) - {w}x{h}")
        
        boxes = filtered_boxes
        print(f"After text box filtering: {len(boxes)} boxes")

    # Step 6: filter out images with too high proportion of white pixels (likely false positive, or text only)
    final_boxes = []
    for x, y, w, h in boxes[:]:
        roi = gray[y:y+h, x:x+w]
        num_white = np.sum(roi > 180)
        num_white_ratio = num_white / (w * h)
        if num_white_ratio > 0.5:
            continue
        final_boxes.append((x, y, w, h))
    
    return final_boxes, img, gray


def draw_results(img, boxes, color=(0, 255, 0), thickness=3):
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


def main():
    parser = argparse.ArgumentParser(
        description='Improved newspaper image detection with overlap removal and ad filtering',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s newspaper.png
  %(prog)s scan.jpg --min-area 8000 --iou-threshold 0.2
  %(prog)s page.png --no-filter-text --debug
  
Parameters to adjust:
  --min-area: Increase to filter out smaller regions (default: 5000)
  --iou-threshold: Lower values remove more overlaps (default: 0.3)
  --no-filter-text: Disable text box filtering if removing real images
  --debug: Save intermediate processing images
        """
    )
    
    parser.add_argument('input_file', type=str, 
                       help='Path to the newspaper scan image')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output file path (default: improved_<input_name>)')
    parser.add_argument('--min-area', type=int, default=5000,
                       help='Minimum area for detected regions (default: 5000)')
    parser.add_argument('--max-area-ratio', type=float, default=0.5,
                       help='Maximum area as fraction of page (default: 0.5)')
    parser.add_argument('--iou-threshold', type=float, default=0.3,
                       help='IoU threshold for overlap removal (default: 0.3, lower=more aggressive)')
    parser.add_argument('--no-filter-text', action='store_true',
                       help='Disable text box filtering')
    parser.add_argument('--debug', action='store_true',
                       help='Save debug images showing processing steps')
    
    args = parser.parse_args()
    
    # Validate input
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist")
        sys.exit(1)
    
    # Set output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"improved_{input_path.name}"
    
    print("\n" + "="*60)
    print("IMPROVED IMAGE DETECTION")
    print("="*60 + "\n")
    
    # Run detection
    try:
        boxes, img, gray = detect_images_improved(
            input_path,
            min_area=args.min_area,
            max_area_ratio=args.max_area_ratio,
            iou_threshold=args.iou_threshold,
            filter_text_boxes=not args.no_filter_text,
            debug=args.debug
        )
        
        # Draw results
        result = draw_results(img, boxes)
        
        # Save output
        cv2.imwrite(str(output_path), result)
        
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"\nDetected {len(boxes)} images:")
        for i, (x, y, w, h) in enumerate(boxes):
            print(f"  #{i+1}: Position ({x}, {y}), Size {w}x{h} pixels, Area {w*h:,}")
        
        print(f"\nOutput saved to: {output_path}")
        
        if args.debug:
            print("\nDebug images saved:")
            print("  - debug_1_binary.jpg (thresholded image)")
        
        print("\n" + "="*60)
        print("TIPS FOR ADJUSTMENT")
        print("="*60)
        print("\nIf you're getting false positives:")
        print("  • Increase --min-area (try 8000, 10000)")
        print("  • Decrease --iou-threshold (try 0.2, 0.15)")
        print("\nIf you're missing real images:")
        print("  • Decrease --min-area (try 3000, 2000)")
        print("  • Use --no-filter-text flag")
        print("  • Increase --iou-threshold (try 0.4, 0.5)")
        print("\n")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()