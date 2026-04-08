"""
地质数据加工包：地质知识图谱数据处理核心模块
对外暴露核心类/函数，简化外部调用
"""
from .geo_ontology import (
    GeoBaseModel, Deposit, OreBody, Rock, Mineral, Stratum, GeoTectonic,
    GeoRelationBase, GeoRelationEnum, GeoTriple, GeoEntity
)
from .pdf_loader import load_geology_pdfs
from .triple_extractor import GeoTripleExtractor
from .graph_builder import GeoGraphBuilder
from .config import Config

__all__ = [
    # 本体模型
    "GeoBaseModel", "Deposit", "OreBody", "Rock", "Mineral", "Stratum", "GeoTectonic",
    "GeoRelationBase", "GeoRelationEnum", "GeoTriple", "GeoEntity",
    # 核心工具类
    "Config", "load_geology_pdfs", "GeoTripleExtractor", "GeoGraphBuilder"
]