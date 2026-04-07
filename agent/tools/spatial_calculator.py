"""
Spatial Calculator Tool

This tool provides spatial reasoning capabilities by calculating
distances and spatial relationships between geological features
extracted from the map (e.g., minerals and faults).
"""
import json
import math
from typing import List, Dict, Any, Tuple

def point_to_line_distance(point: Tuple[float, float], line_start: Tuple[float, float], line_end: Tuple[float, float]) -> float:
    """Calculate the shortest distance from a point to a line segment."""
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    
    line_mag = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    if line_mag == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2)
        
    # Projection of point onto line
    u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
    
    if u < 0.0:
        # Closest to start point
        return math.sqrt((px - x1)**2 + (py - y1)**2)
    elif u > 1.0:
        # Closest to end point
        return math.sqrt((px - x2)**2 + (py - y2)**2)
    else:
        # Closest to line segment
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        return math.sqrt((px - ix)**2 + (py - iy)**2)

def calculate_spatial_relationships(features_json: str) -> str:
    """
    Calculate distances between minerals and faults from vision_analyze output.
    
    Args:
        features_json: JSON string containing 'faults' and 'minerals'
        
    Returns:
        JSON string with calculated relationships
    """
    try:
        data = json.loads(features_json)
        faults = data.get("faults", [])
        minerals = data.get("minerals", [])
        
        if not faults or not minerals:
            return json.dumps({"message": "Need both faults and minerals to calculate relationships."})
            
        relationships = []
        for mineral in minerals:
            min_pos = mineral.get("position")
            if not min_pos: continue
            
            closest_fault = None
            min_dist = float('inf')
            
            for fault in faults:
                start = fault.get("start")
                end = fault.get("end")
                if not start or not end: continue
                
                dist = point_to_line_distance(min_pos, start, end)
                if dist < min_dist:
                    min_dist = dist
                    closest_fault = fault.get("id")
                    
            if closest_fault:
                relationships.append({
                    "mineral_id": mineral.get("id"),
                    "closest_fault_id": closest_fault,
                    "distance_pixels": round(min_dist, 2)
                })
                
        return json.dumps({"spatial_relationships": relationships}, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Spatial calculation failed: {str(e)}"})
