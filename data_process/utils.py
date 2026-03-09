"""
通用工具函数：日志、数据校验、格式转换等
"""
import logging
import json
from typing import List
from .config import Config
from .geo_ontology import GeoTriple

# ========== 日志配置 ==========
def setup_logger(name: str) -> logging.Logger:
    """配置日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 文件处理器
    file_handler = logging.FileHandler(f"{Config.LOG_DIR}/data_process.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 全局日志器
logger = setup_logger("geo_data_process")

# ========== 数据校验 ==========
def validate_triple(triple: GeoTriple) -> bool:
    """校验三元组的有效性"""
    try:
        if not triple.subject_entity.name:
            logger.error("主体实体名称为空")
            return False
        if not triple.object_entity.name:
            logger.error("客体实体名称为空")
            return False
        if not triple.relation.relation_name:
            logger.error("关系名称为空")
            return False
        # 过滤自引用三元组（只要主客体名称相同，就视为自引用）
        if triple.subject_entity.name == triple.object_entity.name:
            logger.warning(
                f"过滤自引用三元组（主客体同名）：[{triple.subject_entity.entity_type}]{triple.subject_entity.name} "
                f"--{triple.relation.relation_name}--> [{triple.object_entity.entity_type}]{triple.object_entity.name}"
            )
            return False
        return True
    except Exception as e:
        logger.error(f"三元组校验失败：{str(e)}", exc_info=True)
        return False

def deduplicate_triples(triples: List[GeoTriple]) -> List[GeoTriple]:
    """
    对三元组列表进行全局去重
    去重规则：主体名称 + 关系名称 + 客体名称 相同即视为重复
    """
    unique_triples = []
    seen = set()

    for triple in triples:
        # 生成唯一标识
        identifier = f"{triple.subject_entity.name}|{triple.relation.relation_name}|{triple.object_entity.name}"
        if identifier not in seen:
            seen.add(identifier)
            unique_triples.append(triple)

    logger.info(f"三元组去重：原始 {len(triples)} 条 -> 去重后 {len(unique_triples)} 条")
    return unique_triples

# ========== 格式转换 ==========
def triples_to_json(triples: List[GeoTriple], output_path: str) -> None:
    """将三元组列表保存为JSON文件"""
    try:
        # 转换为字典（支持Pydantic模型序列化）
        triples_dict = [triple.model_dump(exclude_none=True) for triple in triples]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(triples_dict, f, ensure_ascii=False, indent=4)
        logger.info(f"三元组已保存到：{output_path}，共{len(triples)}条")
    except Exception as e:
        logger.error(f"三元组保存为JSON失败：{str(e)}", exc_info=True)
        raise

def json_to_triples(input_path: str) -> List[GeoTriple]:
    """从JSON文件加载三元组"""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            triples_dict = json.load(f)
        # 转换为GeoTriple对象
        triples = [GeoTriple(**item) for item in triples_dict]
        logger.info(f"从{input_path}加载{len(triples)}条三元组")
        return triples
    except Exception as e:
        logger.error(f"加载JSON三元组失败：{str(e)}", exc_info=True)
        raise