"""
增量知识图谱构建器：支持新增文档的知识图谱增量更新

核心功能:
1. 文档指纹追踪 - 避免重复处理相同文档
2. 增量三元组抽取 - 只处理新增文档
3. 智能实体融合 - 合并相同实体的属性
4. 增量社区更新 - 可选更新 GraphRAG 社区结构
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from llama_index.core.schema import TextNode

from .config import Config
from .graph_builder import GeoGraphBuilder
from .triple_extractor import GeoTripleExtractor
from .pdf_loader import load_geology_pdfs
from .geo_ontology import GeoTriple
from .utils import logger, deduplicate_triples


@dataclass
class DocumentRecord:
    """文档处理记录"""
    file_path: str
    file_hash: str  # 文件内容哈希，用于检测文件变更
    chunk_count: int  # 文本块数量
    triple_count: int  # 抽取的三元组数量
    processed_at: str  # 处理时间
    chunk_ids: List[str]  # 该文档包含的 chunk IDs

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentRecord':
        return cls(**data)


class IncrementalGraphBuilder:
    """
    增量知识图谱构建器

    使用示例:
        builder = IncrementalGraphBuilder()

        # 首次全量构建
        builder.build_initial(pdf_dir="./data/gouli_pdf")

        # 后续增量更新 (新增文档放入 same directory)
        builder.incremental_update(pdf_dir="./data/gouli_pdf")

        # 或者指定新增文档
        builder.add_documents(["./data/new_report.pdf"])
    """

    def __init__(self, registry_path: str = "./data/document_registry.json"):
        """
        Args:
            registry_path: 文档注册表路径，用于追踪已处理文档
        """
        self.registry_path = Path(registry_path)
        self.graph_builder = GeoGraphBuilder()
        self.extractor = GeoTripleExtractor()

        # 加载文档注册表
        self.registry: Dict[str, DocumentRecord] = {}
        self._load_registry()

        logger.info(f"增量构建器已初始化，已追踪 {len(self.registry)} 个文档")

    def _load_registry(self) -> None:
        """加载文档注册表"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.registry = {
                        k: DocumentRecord.from_dict(v)
                        for k, v in data.items()
                    }
                logger.info(f"已加载文档注册表：{len(self.registry)} 个文档")
            except Exception as e:
                logger.warning(f"加载注册表失败，将创建新的注册表：{e}")
                self.registry = {}
        else:
            logger.info("文档注册表不存在，将创建新的注册表")
            self.registry = {}

    def _save_registry(self) -> None:
        """保存文档注册表"""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            data = {k: v.to_dict() for k, v in self.registry.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存文档注册表：{len(self.registry)} 个文档")

    @staticmethod
    def _compute_file_hash(file_path: str) -> str:
        """计算文件内容哈希 (SHA-256)"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _scan_pdf_directory(self, pdf_dir: str) -> Dict[str, str]:
        """
        扫描 PDF 目录，返回文件路径哈希

        Returns:
            Dict[absolute_path, file_hash]
        """
        pdf_path = Path(pdf_dir)
        if not pdf_path.exists():
            raise ValueError(f"PDF 目录不存在：{pdf_dir}")

        pdf_files = list(pdf_path.glob("*.pdf")) + list(pdf_path.glob("*.PDF"))
        logger.info(f"扫描到 {len(pdf_files)} 个 PDF 文件")

        file_hashes = {}
        for pdf_file in pdf_files:
            abs_path = str(pdf_file.resolve())
            file_hash = self._compute_file_hash(abs_path)
            file_hashes[abs_path] = file_hash

        return file_hashes

    def _identify_new_documents(
        self,
        current_files: Dict[str, str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        识别新增、修改和未变更的文档

        Args:
            current_files: Dict[absolute_path, file_hash]

        Returns:
            (new_files, modified_files, unchanged_files)
        """
        new_files = []
        modified_files = []
        unchanged_files = []

        # 识别新增和修改的文件
        for file_path, current_hash in current_files.items():
            if file_path not in self.registry:
                new_files.append(file_path)
                logger.info(f"新增文档：{Path(file_path).name}")
            elif self.registry[file_path].file_hash != current_hash:
                modified_files.append(file_path)
                logger.info(f"修改文档：{Path(file_path).name}")
            else:
                unchanged_files.append(file_path)

        # 识别已删除的文件
        deleted_files = []
        for registered_path in self.registry:
            if registered_path not in current_files:
                deleted_files.append(registered_path)

        if deleted_files:
            logger.info(f"已删除文档：{len(deleted_files)} 个")
            # 可选：从注册表中移除已删除的文件记录
            # for path in deleted_files:
            #     del self.registry[path]

        return new_files, modified_files, unchanged_files

    def _process_document(
        self,
        file_path: str
    ) -> Tuple[List[TextNode], List[GeoTriple], Dict[str, List[GeoTriple]]]:
        """
        处理单个文档

        Returns:
            (nodes, all_triples, chunk_id_triples_map)
        """
        logger.info(f"处理文档：{file_path}")

        # 加载 PDF
        nodes = load_geology_pdfs(Path(file_path).parent, pattern=Path(file_path).name)
        if not nodes:
            logger.warning(f"文档未加载到文本块：{file_path}")
            return [], [], {}

        logger.info(f"文档切分为 {len(nodes)} 个文本块")

        # 抽取三元组
        all_triples = []
        chunk_id_triples_map = {}

        for i, node in enumerate(nodes):
            logger.info(f"处理文本块 {i+1}/{len(nodes)}")
            triples = self.extractor.extract_from_text(node.text)

            if triples:
                all_triples.extend(triples)
                chunk_id_triples_map[node.id_] = triples

        logger.info(f"文档抽取完成：{len(all_triples)} 条三元组")
        return nodes, all_triples, chunk_id_triples_map

    def _merge_triples(
        self,
        existing_triples: List[GeoTriple],
        new_triples: List[GeoTriple]
    ) -> List[GeoTriple]:
        """
        合并三元组，去重

        当前实现：简单的基于 (subject, relation, object) 去重
        未来优化：可以考虑实体属性融合
        """
        return deduplicate_triples(existing_triples + new_triples)

    def build_initial(self, pdf_dir: str) -> Dict:
        """
        首次全量构建知识图谱

        Args:
            pdf_dir: PDF 目录

        Returns:
            构建统计信息
        """
        logger.info("=" * 60)
        logger.info("开始全量构建知识图谱")
        logger.info("=" * 60)

        # 扫描目录
        current_files = self._scan_pdf_directory(pdf_dir)

        # 处理所有文档
        all_nodes = []
        all_triples = []
        chunk_id_triples_map = {}

        for file_path in current_files.keys():
            nodes, triples, chunk_map = self._process_document(file_path)

            all_nodes.extend(nodes)
            all_triples.extend(triples)
            chunk_id_triples_map.update(chunk_map)

            # 记录到注册表
            record = DocumentRecord(
                file_path=file_path,
                file_hash=current_files[file_path],
                chunk_count=len(nodes),
                triple_count=len(triples),
                processed_at=datetime.now().isoformat(),
                chunk_ids=[n.id_ for n in nodes]
            )
            self.registry[file_path] = record

        # 保存注册表
        self._save_registry()

        # 去重三元组
        final_triples = deduplicate_triples(all_triples)
        logger.info(f"全量构建完成：{len(final_triples)} 条唯一三元组")

        # 构建知识图谱
        index = self.graph_builder.build_from_triples(
            triples=final_triples,
            source_nodes=all_nodes,
            chunk_id_triples_map=chunk_id_triples_map
        )

        stats = {
            "total_documents": len(current_files),
            "total_chunks": len(all_nodes),
            "total_triples": len(final_triples),
            "operation": "initial_build"
        }

        logger.info("=" * 60)
        logger.info("全量构建统计")
        logger.info(f"  - 处理文档：{stats['total_documents']} 个")
        logger.info(f"  - 文本块数：{stats['total_chunks']} 个")
        logger.info(f"  - 三元组数：{stats['total_triples']} 条")
        logger.info("=" * 60)

        return stats

    def incremental_update(
        self,
        pdf_dir: str,
        rebuild_communities: bool = False
    ) -> Dict:
        """
        增量更新知识图谱

        Args:
            pdf_dir: PDF 目录
            rebuild_communities: 是否重建 GraphRAG 社区结构

        Returns:
            更新统计信息
        """
        logger.info("=" * 60)
        logger.info("开始增量更新知识图谱")
        logger.info("=" * 60)

        # 扫描目录，识别变更
        current_files = self._scan_pdf_directory(pdf_dir)
        new_files, modified_files, unchanged_files = self._identify_new_documents(current_files)

        if not new_files and not modified_files:
            logger.info("没有新增或修改的文档，跳过更新")
            return {
                "total_documents": len(self.registry),
                "new_documents": 0,
                "modified_documents": 0,
                "operation": "no_changes"
            }

        logger.info(f"新增文档：{len(new_files)} 个")
        logger.info(f"修改文档：{len(modified_files)} 个")
        logger.info(f"未变更文档：{len(unchanged_files)} 个")

        # 处理新增和修改的文档
        new_nodes = []
        new_triples = []
        new_chunk_map = {}

        files_to_process = new_files + modified_files

        for file_path in files_to_process:
            nodes, triples, chunk_map = self._process_document(file_path)

            new_nodes.extend(nodes)
            new_triples.extend(triples)
            new_chunk_map.update(chunk_map)

            # 更新注册表
            record = DocumentRecord(
                file_path=file_path,
                file_hash=current_files[file_path],
                chunk_count=len(nodes),
                triple_count=len(triples),
                processed_at=datetime.now().isoformat(),
                chunk_ids=[n.id_ for n in nodes]
            )
            self.registry[file_path] = record

        # 保存注册表
        self._save_registry()

        if not new_triples:
            logger.info("新增文档未抽取到有效三元组")
            return {
                "total_documents": len(self.registry),
                "new_documents": len(new_files),
                "modified_documents": len(modified_files),
                "new_triples": 0,
                "operation": "no_new_triples"
            }

        # 增量构建到图谱
        # 注意：GeoGraphBuilder.build_from_triples 使用 upsert，会自动合并
        logger.info(f"开始增量写入图谱：{len(new_triples)} 条三元组")

        index = self.graph_builder.build_from_triples(
            triples=new_triples,
            source_nodes=new_nodes,
            chunk_id_triples_map=new_chunk_map
        )

        # 可选：重建社区结构
        if rebuild_communities:
            logger.info("重建 GraphRAG 社区结构...")
            try:
                from .graphrag_store import GraphRAGStore
                from llama_index.llms.openai_like import OpenAILike

                llm = OpenAILike(
                    api_key=Config.OPENAI_API_KEY,
                    model=Config.OPENAI_MODEL,
                    api_base=Config.OPENAI_BASE_URL,
                    is_chat_model=True,
                    temperature=Config.OPENAI_TEMPERATURE,
                )

                store = GraphRAGStore(
                    username=Config.NEO4J_USER,
                    password=Config.NEO4J_PASSWORD,
                    url=Config.NEO4J_URI,
                    llm=llm,
                    max_cluster_size=5,
                )

                store.build_communities(levels=3)
                store.close()
                logger.info("社区结构重建完成")
            except Exception as e:
                logger.warning(f"社区重建失败：{e}")

        stats = {
            "total_documents": len(self.registry),
            "new_documents": len(new_files),
            "modified_documents": len(modified_files),
            "new_triples": len(new_triples),
            "operation": "incremental_update"
        }

        logger.info("=" * 60)
        logger.info("增量更新统计")
        logger.info(f"  - 累计文档：{stats['total_documents']} 个")
        logger.info(f"  - 新增文档：{stats['new_documents']} 个")
        logger.info(f"  - 修改文档：{stats['modified_documents']} 个")
        logger.info(f"  - 新增三元组：{stats['new_triples']} 条")
        logger.info("=" * 60)

        return stats

    def add_documents(self, file_paths: List[str]) -> Dict:
        """
        添加指定文档到知识图谱

        Args:
            file_paths: PDF 文件路径列表

        Returns:
            添加统计信息
        """
        logger.info("=" * 60)
        logger.info(f"开始添加 {len(file_paths)} 个文档")
        logger.info("=" * 60)

        new_nodes = []
        new_triples = []
        new_chunk_map = {}

        for file_path in file_paths:
            abs_path = str(Path(file_path).resolve())

            if not Path(abs_path).exists():
                logger.warning(f"文件不存在：{abs_path}")
                continue

            file_hash = self._compute_file_hash(abs_path)

            if abs_path in self.registry:
                if self.registry[abs_path].file_hash == file_hash:
                    logger.info(f"文档已存在且未变更，跳过：{abs_path}")
                    continue
                else:
                    logger.info(f"文档已存在但内容已变更，将更新：{abs_path}")

            # 处理文档
            nodes, triples, chunk_map = self._process_document(abs_path)

            new_nodes.extend(nodes)
            new_triples.extend(triples)
            new_chunk_map.update(chunk_map)

            # 更新注册表
            record = DocumentRecord(
                file_path=abs_path,
                file_hash=file_hash,
                chunk_count=len(nodes),
                triple_count=len(triples),
                processed_at=datetime.now().isoformat(),
                chunk_ids=[n.id_ for n in nodes]
            )
            self.registry[abs_path] = record

        # 保存注册表
        self._save_registry()

        if not new_triples:
            logger.info("未抽取到有效三元组")
            return {"operation": "no_new_triples", "added_documents": 0}

        # 增量构建
        logger.info(f"开始写入图谱：{len(new_triples)} 条三元组")

        index = self.graph_builder.build_from_triples(
            triples=new_triples,
            source_nodes=new_nodes,
            chunk_id_triples_map=new_chunk_map
        )

        stats = {
            "added_documents": len([n for n in new_nodes if n]),
            "new_triples": len(new_triples),
            "operation": "add_documents"
        }

        logger.info(f"添加完成：{stats['added_documents']} 个文档，{stats['new_triples']} 条三元组")
        return stats

    def get_registry_info(self) -> Dict:
        """获取注册表信息"""
        return {
            "total_documents": len(self.registry),
            "documents": [
                {
                    "file": Path(v.file_path).name,
                    "chunks": v.chunk_count,
                    "triples": v.triple_count,
                    "processed_at": v.processed_at
                }
                for v in self.registry.values()
            ]
        }

    def rebuild_communities(self) -> None:
        """
        重建 GraphRAG 社区结构

        当知识图谱发生重大变更时调用
        """
        logger.info("重建 GraphRAG 社区结构...")

        try:
            from .graphrag_store import GraphRAGStore
            from llama_index.llms.openai_like import OpenAILike

            llm = OpenAILike(
                api_key=Config.OPENAI_API_KEY,
                model=Config.OPENAI_MODEL,
                api_base=Config.OPENAI_BASE_URL,
                is_chat_model=True,
                temperature=Config.OPENAI_TEMPERATURE,
            )

            store = GraphRAGStore(
                username=Config.NEO4J_USER,
                password=Config.NEO4J_PASSWORD,
                url=Config.NEO4J_URI,
                llm=llm,
                max_cluster_size=5,
            )

            store.build_communities(levels=3)
            store.close()
            logger.info("社区结构重建完成")
        except Exception as e:
            logger.error(f"社区重建失败：{e}")
            raise


def main():
    """增量构建示例"""
    from data_process.config import Config

    # 初始化增量构建器
    builder = IncrementalGraphBuilder(
        registry_path="./data/document_registry.json"
    )

    # 模式 1: 首次全量构建
    # stats = builder.build_initial(pdf_dir=Config.PDF_DIR)

    # 模式 2: 增量更新 (检测新增/修改文档)
    stats = builder.incremental_update(
        pdf_dir=Config.PDF_DIR,
        rebuild_communities=False  # 可选：重建社区结构
    )

    # 模式 3: 添加指定文档
    # stats = builder.add_documents([
    #     "./data/new_reports/report1.pdf",
    #     "./data/new_reports/report2.pdf"
    # ])

    print(f"\n操作完成：{stats}")


if __name__ == "__main__":
    main()
