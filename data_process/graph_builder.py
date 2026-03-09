"""
知识图谱构建器：将三元组构建为 PropertyGraphIndex，写入 Neo4j
"""
from llama_index.core import PropertyGraphIndex
from llama_index.core.schema import TextNode
from llama_index.core.graph_stores.types import EntityNode, Relation
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from typing import List, Optional
import uuid
from .config import Config
from .geo_ontology import GeoTriple
from .triple_extractor import GeoTripleExtractor
from .utils import logger, triples_to_json

class GeoGraphBuilder:
    """地质知识图谱构建器"""
    def __init__(self):
        # 初始化 Neo4j 图存储
        self.graph_store = Neo4jPropertyGraphStore(
            username=Config.NEO4J_USER,
            password=Config.NEO4J_PASSWORD,
            url=Config.NEO4J_URI
        )
        # 初始化嵌入模型（使用智谱 AI）
        self.embed_model = OpenAILikeEmbedding(
            model_name=Config.EMBEDDING_MODEL_NAME,
            api_key=Config.EMBEDDING_API_KEY,
            api_base=Config.EMBEDDING_BASE_URL
        )
        # 初始化抽取器
        self.extractor = GeoTripleExtractor()

    @staticmethod
    def _create_node(entity) -> EntityNode:
        """将实体转换为 EntityNode，排除 null 属性"""
        props = entity.model_dump(exclude_none=True)
        return EntityNode(
            name=entity.name,
            label=type(entity).__name__,
            properties=props
        )

    def build_from_triples(self, triples: List[GeoTriple], source_nodes: Optional[List[TextNode]] = None) -> PropertyGraphIndex:
        """
        从三元组构建知识图谱索引

        Args:
            triples: 标准化三元组列表
            source_nodes: 原始文本块节点列表（用于支持 RAG）
        """
        try:
            # 引入去重
            from .utils import deduplicate_triples
            triples = deduplicate_triples(triples)

            logger.info(f"开始构建知识图谱，去重后三元组数量：{len(triples)}")

            # 初始化 PropertyGraphIndex
            index = PropertyGraphIndex.from_existing(
                property_graph_store=self.graph_store,
                embed_model=self.embed_model,
                show_progress=True
            )

            kg_nodes = []
            kg_relations = []

            # 1. 插入源文本节点（支持 RAG 必须）
            if source_nodes:
                logger.info(f"插入源文本节点：{len(source_nodes)}个")
                # 将 TextNode 转换为 EntityNode（以 Chunk 标签）
                for sn in source_nodes:
                    chunk_node = EntityNode(
                        name=sn.id_,
                        label="Chunk",
                        properties={"text": sn.text, "source": sn.metadata.get("source", "")}
                    )
                    kg_nodes.append(chunk_node)

            # 2. 处理三元组
            for triple in triples:
                subject_node = self._create_node(triple.subject_entity)
                object_node = self._create_node(triple.object_entity)
                kg_nodes.extend([subject_node, object_node])

                # 实体间的知识图谱关系（排除 null 属性）
                rel_props = triple.relation.model_dump(exclude_none=True)
                relation = Relation(
                    id=str(uuid.uuid4()),
                    label=triple.relation.relation_name,
                    source_id=subject_node.id,
                    target_id=object_node.id,
                    properties=rel_props
                )
                kg_relations.append(relation)

            # 3. 构建 Chunk -> Entity 的 MENTIONS 关系
            if source_nodes:
                entity_node_map = {}  # entity_name -> EntityNode.id
                for triple in triples:
                    for ent in [triple.subject_entity, triple.object_entity]:
                        if ent.name not in entity_node_map:
                            # 查找已创建的 EntityNode
                            for kn in kg_nodes:
                                if kn.name == ent.name and kn.label != "Chunk":
                                    entity_node_map[ent.name] = kn.id
                                    break

                for sn in source_nodes:
                    chunk_id = None
                    for kn in kg_nodes:
                        if kn.label == "Chunk" and kn.name == sn.id_:
                            chunk_id = kn.id
                            break
                    if not chunk_id:
                        continue
                    # 检查该 Chunk 的文本中提到了哪些实体
                    for ent_name, ent_id in entity_node_map.items():
                        if ent_name in sn.text:
                            mentions_rel = Relation(
                                id=str(uuid.uuid4()),
                                label="MENTIONS",
                                source_id=chunk_id,
                                target_id=ent_id,
                                properties={"source": "auto_linking"}
                            )
                            kg_relations.append(mentions_rel)

                logger.info(f"构建了 MENTIONS 关系，总关系数：{len(kg_relations)}")

            # 4. 将节点和关系写入图存储
            if kg_nodes:
                self.graph_store.upsert_nodes(kg_nodes)
                logger.info(f"插入了 {len(kg_nodes)} 个节点（含实体与文本Chunk）")

            if kg_relations:
                self.graph_store.upsert_relations(kg_relations)
                logger.info(f"插入了 {len(kg_relations)} 个关系")

            logger.info("知识图谱构建完成，已写入Neo4j")
            return index

        except Exception as e:
            logger.error(f"图谱构建失败：{str(e)}", exc_info=True)
            raise

    def build_from_pdfs(
        self, 
        pdf_dir: Optional[str] = None,
        save_triples_path: Optional[str] = "./triples_output.json"
    ) -> PropertyGraphIndex:
        """
        从PDF文件直接构建知识图谱
        
        Args:
            pdf_dir: PDF目录
            save_triples_path: 三元组保存路径
        
        Returns:
            PropertyGraphIndex: 图谱索引
        """
        # 1. 抽取三元组
        triples = self.extractor.extract_from_pdfs(pdf_dir)
        
        # 2. 保存三元组（可选）
        if save_triples_path:
            triples_to_json(triples, save_triples_path)
        
        # 3. 构建图谱
        index = self.build_from_triples(triples)
        
        return index
