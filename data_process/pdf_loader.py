"""
PDF加载器：加载地质PDF文件，提取文本块，适配LlamaIndex的Document格式
"""
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, TextNode
from typing import List, Optional
import os
from .config import Config
from .utils import logger

def load_geology_pdfs(
    pdf_dir: Optional[str] = None,
    chunk_size: int = Config.TEXT_CHUNK_SIZE,
    chunk_overlap: int = 200
) -> List[TextNode]:
    """
    加载地质 PDF 文件，切分为文本块（TextNode）
    
    Args:
        pdf_dir: PDF 文件目录，默认使用 Config 中的 PDF_DIR
        chunk_size: 文本块大小
        chunk_overlap: 文本块重叠长度
    
    Returns:
        List[TextNode]: 切分后的文本块列表
    """
    try:
        pdf_dir = pdf_dir or Config.PDF_DIR
        
        # 检查目录是否存在
        if not os.path.exists(pdf_dir):
            logger.warning(f"PDF 目录不存在：{pdf_dir}，返回空列表")
            return []
        
        # 加载 PDF 文件（LlamaIndex 自动解析 PDF）
        logger.info(f"开始加载 PDF 文件，目录：{pdf_dir}")
        reader = SimpleDirectoryReader(
            input_dir=pdf_dir,
            required_exts=[".pdf"]  # 仅加载 PDF 文件
        )
        documents = reader.load_data()
        
        if not documents:
            logger.warning("未加载到任何PDF文件")
            return []
        
        logger.info(f"成功加载{len(documents)}个PDF文件，开始切分文本块")
        
        # 文本切分器（适配地质文本的长句特性）
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator="。"  # 按中文句号切分
        )
        
        # 切分为TextNode
        nodes = splitter.get_nodes_from_documents(documents)
        logger.info(f"文本切分完成，共生成{len(nodes)}个文本块")
        
        # 为每个节点添加元数据
        for i, node in enumerate(nodes):
            node.metadata.update({
                "node_id": f"geo_node_{i}",
                "source": node.metadata.get("file_name", "unknown"),
                "chunk_size": chunk_size
            })
        
        return nodes
    
    except Exception as e:
        logger.error(f"PDF加载/切分失败：{str(e)}", exc_info=True)
        raise