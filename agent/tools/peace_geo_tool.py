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

# Cache for rock knowledge databases (loaded once, reused across calls)
_rock_type_db = None
_rock_age_db = None


def _get_rock_dbs():
    """Lazy load rock knowledge databases with caching."""
    global _rock_type_db, _rock_age_db
    if _rock_type_db is None or _rock_age_db is None:
        from PEACE.tool_pool.rock_type_and_age_db import rock_type_and_age_db
        _rock_type_db = rock_type_and_age_db("type")
        _rock_age_db = rock_type_and_age_db("age")
    return _rock_type_db, _rock_age_db


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
    Get geological knowledge about a rock type from PEACE local knowledge base.
    Uses cached JSON files instead of API calls for fast batch queries.

    Args:
        rock_name: Name of the rock/stratigraphic unit from map legend

    Returns:
        Dictionary containing rock knowledge:
        {
            "rock_type": str,      # Lithology classification
            "rock_age": str,       # Stratigraphic age
        }
    """
    # Use cached database instances (lazy loaded)
    rock_type_db, rock_age_db = _get_rock_dbs()

    result = {}

    # Get rock type from local cache
    result["rock_type"] = rock_type_db.get_rock_type_or_age(rock_name)

    # Get rock age from local cache
    result["rock_age"] = rock_age_db.get_rock_type_or_age(rock_name)

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

    缓存策略：
    - 首次分析：调用 PEACE HIE 模块完整提取元数据
    - 再次分析：通过图名匹配从 .cache/local_dataset/*/meta/ 直接返回缓存结果

    Args:
        image_path: Path to the geological map image
        query: Analysis query type:
            - "analyze": Full analysis (default)
            - "layout": Extract map layout only
            - "legend": Extract legend information
            - "info": Extract basic information

    Returns:
        JSON-formatted string with analysis results
    """
    import json
    from pathlib import Path

    try:
        if not os.path.exists(image_path):
            return json.dumps({"error": f"Image not found: {image_path}"}, ensure_ascii=False)

        # 尝试从缓存加载元数据（图名匹配）
        cache_root = Path(__file__).resolve().parent.parent.parent / ".cache" / "local_dataset"
        map_name = Path(image_path).stem  # 不含扩展名的文件名

        cached_meta = None
        if cache_root.exists():
            for meta_file in cache_root.rglob("meta/*.json"):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        cached_name = meta.get('name')
                        # 精确匹配 或 前缀匹配（处理带 UUID 后缀的情况）
                        # 如：输入"成矿预测图"，缓存"成矿预测图_3c9f927c" 也应命中
                        if cached_name == map_name or (cached_name and cached_name.startswith(map_name + '_')):
                            cached_meta = meta
                            break
                except Exception:
                    continue

        if cached_meta:
            # 缓存命中，直接返回
            if query == "layout":
                result = {
                    "name": cached_meta.get("name"),
                    "size": cached_meta.get("size"),
                    "regions": cached_meta.get("regions"),
                }
            elif query == "legend":
                result = {
                    "name": cached_meta.get("name"),
                    "legend": cached_meta.get("legend"),
                }
            elif query == "info":
                result = {
                    "name": cached_meta.get("name"),
                    "information": cached_meta.get("information"),
                }
            else:
                result = cached_meta
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 缓存未命中，调用 PEACE HIE 模块分析
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
        return json.dumps({"error": f"PEACE map analysis failed: {str(e)}"}, ensure_ascii=False)

def peace_rock_knowledge(rock_name: str) -> str:
    """
    Get geological knowledge about a specific rock type from the PEACE local knowledge base.

    Args:
        rock_name: Name of the rock or stratigraphic unit (e.g., '第四系', '大理岩')

    Returns:
        JSON-formatted string containing rock type and age knowledge
    """
    import json
    try:
        result = get_rock_knowledge(rock_name)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to get rock knowledge: {str(e)}"}, ensure_ascii=False)
