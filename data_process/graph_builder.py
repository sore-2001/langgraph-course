"""
知识图谱构建器：将三元组构建为 PropertyGraphIndex，写入 Neo4j
"""
from llama_index.core import PropertyGraphIndex
from llama_index.core.schema import TextNode
from llama_index.core.graph_stores.types import EntityNode, Relation
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from typing import List, Optional, Dict
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
    def _create_node(entity, source_chunk_id: Optional[str] = None) -> EntityNode:
        """
        将实体转换为 EntityNode，排除 null 属性

        Args:
            entity: 实体对象
            source_chunk_id: 可选的源文本块 ID，用于追溯来源
        """
        props = entity.model_dump(exclude_none=True)
        # 添加来源追溯信息
        if source_chunk_id:
            props["source_chunk_id"] = source_chunk_id
        return EntityNode(
            name=entity.name,
            label=type(entity).__name__,
            properties=props
        )

    def build_from_triples(self, triples: List[GeoTriple], source_nodes: Optional[List[TextNode]] = None, chunk_id_triples_map: Optional[Dict[str, List[GeoTriple]]] = None) -> PropertyGraphIndex:
        """
        从三元组构建知识图谱索引

        Args:
            triples: 标准化三元组列表
            source_nodes: 原始文本块节点列表（用于支持 RAG）
            chunk_id_triples_map: 可选的 ChunkID-> 三元组 映射，用于建立准确的来源追溯
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
            chunk_id_map = {}  # chunk_id -> EntityNode.id
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
                    chunk_id_map[sn.id_] = chunk_node.id

            # 2. 处理三元组 - 同时构建实体节点和语义关系
            entity_node_map = {}  # entity_key (name+label) -> EntityNode.id

            for triple in triples:
                # 使用 (名称，标签) 作为唯一键，避免重复创建相同实体
                subject_key = f"{triple.subject_entity.name}_{type(triple.subject_entity).__name__}"
                object_key = f"{triple.object_entity.name}_{type(triple.object_entity).__name__}"

                # 创建或复用 subject 节点
                if subject_key not in entity_node_map:
                    subject_node = self._create_node(triple.subject_entity)
                    kg_nodes.append(subject_node)
                    entity_node_map[subject_key] = subject_node.id
                else:
                    subject_node = EntityNode(
                        name=triple.subject_entity.name,
                        label=type(triple.subject_entity).__name__,
                        properties=triple.subject_entity.model_dump(exclude_none=True)
                    )

                # 创建或复用 object 节点
                if object_key not in entity_node_map:
                    object_node = self._create_node(triple.object_entity)
                    kg_nodes.append(object_node)
                    entity_node_map[object_key] = object_node.id
                else:
                    object_node = EntityNode(
                        name=triple.object_entity.name,
                        label=type(triple.object_entity).__name__,
                        properties=triple.object_entity.model_dump(exclude_none=True)
                    )

                # 实体间的知识图谱关系（排除 null 属性）
                # 添加关系类型和来源追溯
                rel_props = triple.relation.model_dump(exclude_none=True)
                rel_props["relation_type"] = triple.relation.relation_name  # 显式保存关系类型

                # 如果有 source_nodes，尝试找到对应的 Chunk ID
                if source_nodes and chunk_id_triples_map:
                    for chunk_id, chunk_triples in chunk_id_triples_map.items():
                        if triple in chunk_triples and chunk_id in chunk_id_map:
                            rel_props["source_chunk_id"] = chunk_id
                            rel_props["source_document"] = source_nodes[
                                next(i for i, sn in enumerate(source_nodes) if sn.id_ == chunk_id)
                            ].metadata.get("source", "")
                            break

                relation = Relation(
                    id=str(uuid.uuid4()),
                    label=triple.relation.relation_name,
                    source_id=entity_node_map[subject_key],
                    target_id=entity_node_map[object_key],
                    properties=rel_props
                )
                kg_relations.append(relation)

            # 3. 构建 Chunk -> Entity 的 MENTIONS 关系（仅从 Chunk 指向 Entity）
            if source_nodes and chunk_id_triples_map:
                logger.info("构建 Chunk -> Entity 的 MENTIONS 关系...")

                # 为每个 Chunk 建立与其对应的实体的 MENTIONS 关系
                for chunk_id, chunk_triples in chunk_id_triples_map.items():
                    if chunk_id not in chunk_id_map:
                        continue

                    chunk_source_id = chunk_id_map[chunk_id]

                    # 收集该 Chunk 对应的所有实体
                    mentioned_entities = set()
                    for triple in chunk_triples:
                        subject_key = f"{triple.subject_entity.name}_{type(triple.subject_entity).__name__}"
                        object_key = f"{triple.object_entity.name}_{type(triple.object_entity).__name__}"

                        if subject_key in entity_node_map:
                            mentioned_entities.add(entity_node_map[subject_key])
                        if object_key in entity_node_map:
                            mentioned_entities.add(entity_node_map[object_key])

                    # 为每个实体建立 MENTIONS 关系
                    for entity_id in mentioned_entities:
                        mentions_rel = Relation(
                            id=str(uuid.uuid4()),
                            label="MENTIONS",
                            source_id=chunk_source_id,
                            target_id=entity_id,
                            properties={"source": "chunk_triple_mapping"}
                        )
                        kg_relations.append(mentions_rel)

                logger.info(f"构建了 MENTIONS 关系，总关系数：{len(kg_relations)}")
            elif source_nodes:
                # 向后兼容：如果没有 chunk_id_triples_map，使用原有的文本匹配方式
                logger.info("使用文本匹配方式构建 MENTIONS 关系...")

                # 重建 entity_name -> entity_id 映射
                entity_name_to_id = {}
                for kn in kg_nodes:
                    if kn.label != "Chunk":
                        entity_name_to_id[kn.name] = kn.id

                for sn in source_nodes:
                    chunk_id = chunk_id_map.get(sn.id_)
                    if not chunk_id:
                        continue
                    # 检查该 Chunk 的文本中提到了哪些实体
                    for ent_name, ent_id in entity_name_to_id.items():
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
