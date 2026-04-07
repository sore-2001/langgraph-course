"""
Vision Analysis Tool for Geological Maps

This module provides geological map image analysis capabilities,
using OpenCV to detect structural features (faults/lines) and
potential mineral deposit markers.
"""
import cv2
import numpy as np
import json
import os
from typing import Dict, Any, List

def analyze_geological_map(image_path: str) -> Dict[str, Any]:
    """
    Core function to process the image and extract features.
    """
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}"}
        
    # Handle Chinese paths in Windows with cv2
    img_data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    
    if img is None:
        return {"error": f"Failed to load image: {image_path}"}
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Detect Lines (Potential Faults)
    # Using Canny edge detector and Hough Transform
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
    
    faults = []
    if lines is not None:
        for i, line in enumerate(lines[:10]):  # Limit to top 10 to avoid noise
            x1, y1, x2, y2 = line[0]
            faults.append({
                "id": f"fault_{i+1}",
                "start": [int(x1), int(y1)],
                "end": [int(x2), int(y2)],
                "length": float(np.sqrt((x2-x1)**2 + (y2-y1)**2))
            })
            
    # 2. Detect Red/Distinct Markers (Potential Mineral Deposits)
    # Convert to HSV to find specific colors (e.g., red marks often used for minerals)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Red color range in HSV
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 + mask2
    
    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    minerals = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if 10 < area < 500:  # Filter by size
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                minerals.append({
                    "id": f"mineral_{i+1}",
                    "position": [cX, cY],
                    "area": float(area)
                })
                if len(minerals) >= 10:  # Limit to top 10
                    break
                    
    return {
        "image_size": {"width": img.shape[1], "height": img.shape[0]},
        "faults": faults,
        "minerals": minerals
    }


def vision_analyze(image_path: str, analysis_type: str = "full") -> str:
    """
    Analyze a geological map image to extract spatial features.

    Args:
        image_path: Path to the geological map image
        analysis_type: Type of analysis to perform
            - "full": Complete analysis (default)
            - "faults": Extract fault lines only
            - "minerals": Detect mineral deposit markers

    Returns:
        JSON-formatted string with analysis results
    """
    try:
        results = analyze_geological_map(image_path)
        
        if "error" in results:
            return json.dumps(results, ensure_ascii=False)
            
        if analysis_type == "faults":
            return json.dumps({"faults": results.get("faults", [])}, ensure_ascii=False, indent=2)
        elif analysis_type == "minerals":
            return json.dumps({"minerals": results.get("minerals", [])}, ensure_ascii=False, indent=2)
        else:
            return json.dumps(results, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({"error": f"Vision analysis failed: {str(e)}"}, ensure_ascii=False)
