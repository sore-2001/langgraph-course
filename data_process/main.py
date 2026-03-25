"""
主执行文件：调用 data_process 模块完成从 PDF 到知识图谱的全流程
"""
from pathlib import Path
import sys
from collections import Counter
from typing import List, Dict, Any
import json

# 确保项目根目录在搜索路径中
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from data_process.config import Config
from data_process.graph_builder import GeoGraphBuilder
from data_process.utils import logger, triples_to_json
from data_process.pdf_loader import load_geology_pdfs
from data_process.geo_ontology import GeoTriple
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike


def log_extraction_statistics(triples: List[GeoTriple], nodes: List, output_path: str) -> Dict[str, Any]:
    """
    统计并记录知识抽取效果

    Args:
        triples: 抽取的三元组列表
        nodes: 原始文本块节点列表
        output_path: 统计报告输出路径

    Returns:
        统计信息字典
    """
    stats = {
        "total_chunks": len(nodes),
        "total_triples": len(triples),
        "avg_triples_per_chunk": round(len(triples) / len(nodes), 2) if nodes else 0,
        "entity_type_distribution": {},
        "relation_type_distribution": {},
        "source_file_distribution": {},
        "triple_validation": {
            "valid": len(triples),
            "invalid": 0
        }
    }

    # 统计实体类型分布
    subject_entities = [t.subject_entity.entity_type for t in triples]
    object_entities = [t.object_entity.entity_type for t in triples]
    all_entities = subject_entities + object_entities
    stats["entity_type_distribution"] = dict(Counter(all_entities))

    # 统计关系类型分布
    relations = [t.relation.relation_name for t in triples]
    stats["relation_type_distribution"] = dict(Counter(relations))

    # 统计源文件分布
    source_files = [n.metadata.get('source', 'unknown') for n in nodes]
    stats["source_file_distribution"] = dict(Counter(source_files))

    # 记录统计信息到日志
    logger.info("=" * 60)
    logger.info("知识抽取效果统计报告")
    logger.info("=" * 60)
    logger.info(f"【数据概况】")
    logger.info(f"  - 处理文本块数量：{stats['total_chunks']} 个")
    logger.info(f"  - 抽取三元组总数：{stats['total_triples']} 条")
    logger.info(f"  - 平均每文本块三元组数：{stats['avg_triples_per_chunk']} 条/块")
    logger.info("")

    logger.info(f"【实体类型分布】")
    for entity_type, count in sorted(stats['entity_type_distribution'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  - {entity_type}: {count} 次")
    logger.info("")

    logger.info(f"【关系类型分布】")
    for relation_type, count in sorted(stats['relation_type_distribution'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  - {relation_type}: {count} 次")
    logger.info("")

    logger.info(f"【源文件分布】")
    for source_file, count in sorted(stats['source_file_distribution'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  - {source_file}: {count} 个文本块")
    logger.info("")

    # 保存统计报告到文件
    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info(f"统计报告已保存到：{report_path}")
    logger.info("=" * 60)

    return stats


def main():
    """主流程：PDF 加载→三元组抽取→图谱构建"""
    try:
        # 配置全局 LLM 供 LlamaIndex 查询引擎使用
        Settings.llm = OpenAILike(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            api_base=Config.OPENAI_BASE_URL,
            is_chat_model=True,
            temperature=Config.OPENAI_TEMPERATURE,
        )

        # 1. 初始化图谱构建器
        graph_builder = GeoGraphBuilder()

        # 2. 从 PDF 构建图谱 (完整文档模式)
        logger.info("=" * 60)
        logger.info("开始全流程构建地质知识图谱 (完整文档模式)")
        logger.info("=" * 60)

        # 加载所有 PDF 文档
        nodes = load_geology_pdfs(Config.PDF_DIR)

        if not nodes:
            logger.error("未加载到任何 PDF 文档，请检查 PDF_DIR 配置")
            return

        logger.info(f"共加载 {len(nodes)} 个文本块，开始全量抽取...")

        # 抽取三元组，同时记录每个 Chunk 对应的三元组
        all_triples = []
        failed_chunks = 0
        chunk_id_triples_map = {}  # chunk_id -> 该 chunk 抽取的三元组列表

        for i, node in enumerate(nodes):
            logger.info(f"处理文本块 {i+1}/{len(nodes)}：{node.metadata.get('source')}")
            triples = graph_builder.extractor.extract_from_text(node.text)

            if not triples:
                failed_chunks += 1
                logger.warning(f"文本块 {i+1} 未抽取到有效三元组")
            else:
                # 记录 chunk_id 与三元组的映射关系
                chunk_id_triples_map[node.id_] = triples

            all_triples.extend(triples)

        logger.info(f"三元组抽取完成，共 {len(all_triples)} 条")
        logger.info(f"抽取失败/空结果的文本块数：{failed_chunks}/{len(nodes)}")

        # 保存三元组到 JSON
        triples_output_path = "./geology_triples_full.json"
        triples_to_json(all_triples, triples_output_path)

        # 3. 统计抽取效果并记录到日志
        stats = log_extraction_statistics(
            triples=all_triples,
            nodes=nodes,
            output_path=str(Path(Config.LOG_DIR) / "extraction_stats.json")
        )

        # 4. 构建知识图谱（传入 chunk_id_triples_map 以建立准确的来源追溯）
        logger.info("开始构建知识图谱索引...")
        index = graph_builder.build_from_triples(
            all_triples,
            source_nodes=nodes,
            chunk_id_triples_map=chunk_id_triples_map
        )
        logger.info("知识图谱构建完成！")

        # 5. 测试查询
        logger.info("测试图谱查询...")
        query_engine = index.as_query_engine(include_text=True)
        response = query_engine.query("塘江沅钨矿主要赋存于什么岩石中？")
        logger.info(f"查询结果：{str(response)}")

        logger.info("=" * 60)
        logger.info("全流程执行完成！")
        logger.info(f"最终统计：{stats['total_chunks']} 个文本块 → {stats['total_triples']} 条三元组")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"主流程执行失败：{str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
