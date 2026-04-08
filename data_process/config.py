"""
配置文件：统一管理所有可配置参数，避免硬编码
使用 python-dotenv 加载.env 文件中的敏感信息（如 API 密钥）
"""
import os
from dotenv import load_dotenv

# 加载.env 文件（若存在）
load_dotenv()

class Config:
    """全局配置类"""
    # ===================== 路径配置 =====================
    # PDF 文件目录（相对于 data_process 目录）
    PDF_DIR = os.getenv("PDF_DIR", "../data/text_one")
    # Neo4j 数据持久化目录（可选）
    NEO4J_DATA_DIR = os.getenv("NEO4J_DATA_DIR", "./neo4j_data/")
    # 日志文件目录
    LOG_DIR = os.getenv("LOG_DIR", "./logs/")

    # ===================== LLM 配置 =====================
    # 主模型配置（通过本地代理调用 Gemini）
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "*")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8045/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL_NAME", "gemini-3-flash")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", 0.0))

    # ===================== Embedding 模型配置 =====================
    # 智谱 AI Embedding 配置
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "your_embedding_api_key")
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "embedding-3")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", 1024))

    # ===================== Neo4j 配置 =====================
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_neo4j_password")

    # ===================== Web Search 配置 =====================
    # Google Custom Search API 配置
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")
    GOOGLE_BASE_URL = os.getenv("GOOGLE_BASE_URL", "https://customsearch.googleapis.com/customsearch/v1")

    # ===================== 数据处理配置 =====================
    # 文本块大小
    TEXT_CHUNK_SIZE = int(os.getenv("TEXT_CHUNK_SIZE", 500))

    @classmethod
    def init_dirs(cls):
        """初始化必要的目录（日志、数据等）"""
        for dir_path in [cls.LOG_DIR, cls.NEO4J_DATA_DIR]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

# 初始化目录
Config.init_dirs()
