"""
PEACE Geological Map Analysis Tool

This tool integrates the PEACE module for hierarchical information extraction
from geological map images.

PEACE: Empowering Geologic Map Holistic Understanding with MLLMs
- HIE (Hierarchical Information Extraction): Extract map components, legends, and metadata
- DKI (Domain Knowledge Injection): Inject geological domain knowledge
- PEQA (Prompt-enhanced Question Answering): Enhanced QA for geological maps
"""
import os
import sys

# Add PEACE module to path
_current_dir = os.path.dirname(os.path.realpath(__file__))
_peace_path = os.path.join(_current_dir, "..", "..", "PEACE")
if _peace_path not in sys.path:
    sys.path.append(_peace_path)

from typing import Optional, Dict, Any


def analyze_geological_map(
    image_path: str,
    extract_mode: str = "full",
    cache_enabled: bool = True
) -> Dict[str, Any]:
    """
    Analyze a geological map image using PEACE module's HIE (Hierarchical Information Extraction).

    Args:
        image_path: Path to the geological map image (JPG, PNG, etc.)
        extract_mode: Extraction mode - "full", "layout", "legend", or "info"
            - "full": Extract all metadata including layout, legend, and information
            - "layout": Extract only map layout (regions, components)
            - "legend": Extract legend metadata (colors, text, rock types)
            - "info": Extract basic information (title, scale, coordinates)
        cache_enabled: Whether to use cached results if available

    Returns:
        Dictionary containing extracted metadata:
        {
            "name": str,              # Map name derived from filename
            "size": {"width": int, "height": int},
            "regions": dict,          # Map component regions (main_map, legend, title, etc.)
            "legend": dict,           # Legend entries with color, text, rock_type, area
            "information": dict,      # Basic info (title, scale, longitude, latitude, etc.)
            "faults": list,           # Detected fault lines (if any)
        }

    Raises:
        FileNotFoundError: If image_path does not exist
        ImportError: If PEACE module dependencies are missing
        Exception: If analysis fails
    """
    # Validate image path
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        from PEACE.modules.HIE import hierarchical_information_extraction
    except ImportError as e:
        raise ImportError(
            f"PEACE module not available: {e}. "
            "Ensure PEACE dependencies are installed."
        )

    # Initialize HIE module
    hie = hierarchical_information_extraction()

    # Run digitalization (extracts metadata from the image)
    # The HIE module handles caching internally
    meta = hie.digitalize(image_path)

    # Filter results based on extract_mode
    if extract_mode == "layout":
        return {
            "name": meta.get("name"),
            "size": meta.get("size"),
            "regions": meta.get("regions"),
        }
    elif extract_mode == "legend":
        return {
            "name": meta.get("name"),
            "legend": meta.get("legend"),
        }
    elif extract_mode == "info":
        return {
            "name": meta.get("name"),
            "information": meta.get("information"),
        }
    else:  # "full"
        return meta


def get_rock_knowledge(rock_name: str) -> Dict[str, str]:
    """
    Get geological knowledge about a rock type from PEACE knowledge base.

    Args:
        rock_name: Name of the rock/stratigraphic unit from map legend

    Returns:
        Dictionary containing rock knowledge:
        {
            "rock_type": str,      # Lithology classification
            "rock_age": str,       # Stratigraphic age
        }
    """
    try:
        from PEACE.agents.geologist import geologist_agent
        from PEACE.tool_pool import geological_knwoledge_type
    except ImportError as e:
        return {"error": f"PEACE module not available: {e}"}

    agent = geologist_agent()

    result = {}

    # Get rock type
    rock_type_result = agent.get_knowledge(
        geological_knwoledge_type.Rock_Type,
        rock_name
    )
    result["rock_type"] = rock_type_result.get("rock_type", "unknown")

    # Get rock age
    rock_age_result = agent.get_knowledge(
        geological_knwoledge_type.Rock_Age,
        rock_name
    )
    result["rock_age"] = rock_age_result.get("rock_age", "unknown")

    return result


def detect_map_components(image_path: str) -> Dict[str, list]:
    """
    Detect map components (layout regions) using PEACE's YOLOv10 model.

    Args:
        image_path: Path to the geological map image

    Returns:
        Dictionary mapping component names to bounding boxes:
        {
            "main_map": [[x0, y0, x1, y1], ...],
            "legend": [[x0, y0, x1, y1], ...],
            "title": [[x0, y0, x1, y1], ...],
            "scale": [[x0, y0, x1, y1], ...],
            ...
        }
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        from PEACE.tool_pool import map_component_detector
    except ImportError as e:
        raise ImportError(f"PEACE module not available: {e}")

    detector = map_component_detector()
    result = detector.detect(image_path)

    # Convert result to dictionary format
    components = {}
    if hasattr(result, "names") and hasattr(result, "boxes"):
        for box in result.boxes:
            cls_id = int(box.cls)
            class_name = result.names[cls_id]
            bbox = box.xyxy[0].tolist()  # [x0, y0, x1, y1]
            if class_name not in components:
                components[class_name] = []
            components[class_name].append(bbox)

    return components


# Tool function for agent
def peace_map_analyze(image_path: str, query: str = "analyze") -> str:
    """
    PEACE geological map analysis tool for the agent.

    Use this tool to analyze geological map images and extract structured metadata.
    The PEACE module uses MLLMs (Multimodal Large Language Models) to understand
    geological maps holistically.

    Args:
        image_path: Path to the geological map image
        query: Analysis query type:
            - "analyze": Full analysis (default)
            - "layout": Extract map layout only
            - "legend": Extract legend information
            - "rock": Get rock type knowledge for legend entries

    Returns:
        JSON-formatted string with analysis results
    """
    import json

    try:
        if not os.path.exists(image_path):
            return json.dumps({"error": f"Image not found: {image_path}"}, ensure_ascii=False)

        if query == "layout":
            result = analyze_geological_map(image_path, extract_mode="layout")
        elif query == "legend":
            result = analyze_geological_map(image_path, extract_mode="legend")
        elif query == "info":
            result = analyze_geological_map(image_path, extract_mode="info")
        else:
            result = analyze_geological_map(image_path, extract_mode="full")

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
