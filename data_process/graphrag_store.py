"""
GraphRAG Store - 基于 LlamaIndex PropertyGraphIndex 的社区检测与摘要存储

基于官方文档实现：https://developers.llamaindex.ai/python/examples/cookbooks/graphrag_v2/
参考 Microsoft GraphRAG 的社区层次结构实现
"""
import re
import logging
import networkx as nx
from graspologic.partition import hierarchical_leiden
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from llama_index.core.llms import ChatMessage
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core import Settings

logger = logging.getLogger(__name__)


class GraphRAGStore(Neo4jPropertyGraphStore):
    """
    扩展 Neo4jPropertyGraphStore，实现社区检测和摘要存储到 Neo4j

    社区层次结构（基于 hierarchical_leiden 算法输出）：
    - Level 0: 最粗糙的社区划分 → Saga (大型叙事/超级社区)
    - Level 1: 对过大 Saga 的细分 → Episodic (主题情节/子社区)
    - Level 2+: 最细粒度的社区 → Community (基层社区)

    摘要生成策略（自底向上）：
    - Community 摘要：基于原始实体关系，用 LLM 生成
    - Episodic 摘要：基于下属 Community 的摘要，用 LLM 综合生成
    - Saga 摘要：基于下属 Episodic 的摘要，用 LLM 综合生成
    """

    def __init__(self, *args, max_cluster_size: int = 5, llm=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_cluster_size = max_cluster_size
        self.llm = llm or Settings.llm
        self.entity_info: Dict[str, List[int]] = {}
        self.community_summary: Dict[int, str] = {}
        self.cluster_hierarchy: Dict[int, List[int]] = {}  # parent_cluster_id -> [child_cluster_ids]

    def _create_nx_graph(self) -> nx.Graph:
        """
        从 Neo4j 创建 NetworkX 图

        只获取实体节点之间的关系（排除 Chunk 节点和 MENTIONS 关系）
        """
        nx_graph = nx.Graph()

        with self._driver.session() as session:
            result = session.run("""
            MATCH (s)-[r]->(t)
            WHERE NOT type(r) = 'MENTIONS'
            AND NOT s:Chunk
            AND NOT t:Chunk
            RETURN
                s.name as source_name,
                s.entity_type as source_type,
                t.name as target_name,
                t.entity_type as target_type,
                type(r) as relationship,
                r.relation_name as relation_name,
                r.source as source
            """)

            for record in result:
                source = record["source_name"]
                target = record["target_name"]
                rel_type = record["relationship"]
                relation_name = record.get("relation_name", rel_type)
                rel_source = record.get("source", "")

                description_parts = []
                if relation_name and relation_name != rel_type:
                    description_parts.append(f"{source} {relation_name} {target}")
                else:
                    description_parts.append(f"{source} {rel_type} {target}")
                if rel_source:
                    description_parts.append(f"（来源：{rel_source}）")
                description = " ".join(description_parts)

                nx_graph.add_node(source, entity_type=record["source_type"])
                nx_graph.add_node(target, entity_type=record["target_type"])
                nx_graph.add_edge(
                    source,
                    target,
                    relationship=rel_type,
                    description=description
                )

        print(f"NetworkX 图创建完成：{nx_graph.number_of_nodes()} 节点，{nx_graph.number_of_edges()} 边")
        return nx_graph

    def build_communities(self, levels: int = 3) -> None:
        """
        构建社区层次结构并生成摘要（自底向上）

        Args:
            levels: 层次结构层级数 (默认 3 层：Saga -> Episodic -> Community)
        """
        print("开始构建社区层次结构...")

        nx_graph = self._create_nx_graph()

        print("运行 Leiden 社区检测算法...")
        clusters = hierarchical_leiden(
            nx_graph,
            max_cluster_size=self.max_cluster_size
        )

        print("收集社区信息...")
        entity_info, community_relations, cluster_info = self._collect_community_info(
            nx_graph, clusters
        )
        self.entity_info = entity_info

        print("构建社区层次映射...")
        hierarchy = self._build_cluster_hierarchy(cluster_info)

        print(f"  层次结构：{len(hierarchy)} 个层级")
        for level, clusters_data in hierarchy.items():
            print(f"    Level {level}: {len(clusters_data)} 个社区")

        print("生成社区摘要（自底向上）...")
        self._summarize_communities_bottom_up(hierarchy, community_relations)

        print("将社区写入 Neo4j...")
        self._write_communities_to_neo4j(hierarchy)

        print("社区构建完成!")

    def _collect_community_info(
        self,
        nx_graph: nx.Graph,
        clusters
    ) -> Tuple[Dict, Dict, Dict]:
        """
        收集每个社区的信息

        Returns:
            entity_info: Dict[entity_name, Set[cluster_id]]
            community_relations: Dict[cluster_id, List[relationship_details]]
            cluster_info: Dict[cluster_id, {'level': int, 'parent': Optional[int], 'children': List[int]}]
        """
        entity_info = defaultdict(set)
        community_relations = defaultdict(list)
        cluster_info = {}

        for item in clusters:
            node = item.node
            cluster_id = item.cluster
            level = item.level
            parent = item.parent_cluster if hasattr(item, 'parent_cluster') else None

            entity_info[node].add(cluster_id)

            if cluster_id not in cluster_info:
                cluster_info[cluster_id] = {
                    'level': level,
                    'parent': parent,
                    'children': []
                }
            else:
                cluster_info[cluster_id]['level'] = level
                cluster_info[cluster_id]['parent'] = parent

            if parent is not None:
                if parent not in cluster_info:
                    cluster_info[parent] = {
                        'level': level - 1 if level > 0 else 0,
                        'parent': None,
                        'children': [cluster_id]
                    }
                else:
                    if cluster_id not in cluster_info[parent]['children']:
                        cluster_info[parent]['children'].append(cluster_id)

            for neighbor in nx_graph.neighbors(node):
                edge_data = nx_graph.get_edge_data(node, neighbor)
                if edge_data:
                    detail = (
                        f"{node} -> {neighbor} -> "
                        f"{edge_data['relationship']} -> "
                        f"{edge_data.get('description', '')}"
                    )
                    if cluster_id not in community_relations:
                        community_relations[cluster_id] = []
                    community_relations[cluster_id].append(detail)

        return dict(entity_info), dict(community_relations), dict(cluster_info)

    def _build_cluster_hierarchy(
        self,
        cluster_info: Dict
    ) -> Dict[int, Dict]:
        """
        构建社区层次结构

        hierarchical_leiden 的输出：
        - Level 0: 最粗糙的划分（最大的社区）→ Saga
        - Level 1+: 逐级细分 → Episodic → Community

        我们映射到：
        - Level 0 → Saga
        - Level 1 → Episodic
        - Level 2+ → Community
        """
        hierarchy = defaultdict(dict)

        for cluster_id, info in cluster_info.items():
            level = info['level']

            if level == 0:
                hierarchy[0][cluster_id] = {
                    'type': 'Saga',
                    'parent': None,
                    'children': info['children'],
                    'level': level
                }
            elif level == 1:
                hierarchy[1][cluster_id] = {
                    'type': 'Episodic',
                    'parent': info['parent'],
                    'children': info['children'],
                    'level': level
                }
            else:
                hierarchy[level][cluster_id] = {
                    'type': 'Community',
                    'parent': info['parent'],
                    'children': [],
                    'level': level
                }

        return dict(hierarchy)

    def _generate_summary_from_relations(self, relations: List[str]) -> str:
        """基于原始关系生成摘要"""
        if not relations:
            return ""

        details_text = "\n".join(relations)

        if len(relations) > 50:
            batch_size = 50
            batches = [relations[i:i+batch_size] for i in range(0, len(relations), batch_size)]
            summaries = []
            for batch in batches:
                batch_text = "\n".join(batch)
                try:
                    summary = self._call_llm_for_summary(batch_text)
                    summaries.append(summary)
                except Exception as e:
                    logger.warning(f"生成摘要失败：{e}")
                    summaries.append(batch_text)
            return "\n\n".join(summaries)
        else:
            try:
                return self._call_llm_for_summary(details_text)
            except Exception as e:
                logger.warning(f"生成摘要失败：{e}")
                return details_text

    def _generate_summary_from_child_summaries(
        self,
        child_summaries: List[str],
        level_name: str
    ) -> str:
        """基于子社区摘要生成父社区摘要"""
        if not child_summaries:
            return ""

        summaries_text = "\n\n---\n\n".join(child_summaries)

        prompt = f"""你是一位地质知识图谱分析师。以下是{level_name}下属多个子社区的摘要：

{summaries_text}

请将上述子社区摘要综合为一个连贯的{level_name}摘要。要求：
1. 识别并提炼核心主题和模式
2. 突出该{level_name}的独特地质特征
3. 保持摘要简洁（300 字以内）
4. 使用中文

{level_name}摘要："""

        messages = [
            ChatMessage(
                role="system",
                content="你是一位地质知识图谱专家，擅长综合多个相关摘要生成更高层次的连贯摘要。"
            ),
            ChatMessage(role="user", content=prompt),
        ]

        try:
            response = self.llm.chat(messages)
            clean_response = re.sub(r"^assistant:\s*", "", str(response)).strip()
            return clean_response
        except Exception as e:
            logger.warning(f"生成{level_name}摘要失败：{e}")
            return summaries_text[:2000]

    def _call_llm_for_summary(self, text: str) -> str:
        """调用 LLM 生成摘要的底层方法"""
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "你是一位地质知识图谱分析师。你将被提供一组知识图谱中的关系，"
                    "每个关系表示为 entity1->entity2->relation->relationship_description。"
                    "你的任务是为这些关系创建一个连贯的摘要。"
                    "摘要应包括所涉及的实体名称，以及对关系描述的简洁综合。"
                    "目标是捕捉最关键的信息，突出每组关系的核心特征和地质意义。"
                    "请确保摘要连贯，并整合信息以强调关系的关键方面。"
                    "使用中文回答。"
                ),
            ),
            ChatMessage(role="user", content=text),
        ]
        response = self.llm.chat(messages)
        clean_response = re.sub(r"^assistant:\s*", "", str(response)).strip()
        return clean_response

    def _summarize_communities_bottom_up(
        self,
        hierarchy: Dict[int, Dict],
        community_relations: Dict[int, List[str]]
    ) -> None:
        """
        自底向上生成社区摘要

        顺序：
        1. 先为所有 Community（最细层，level 最高）生成摘要
        2. 再为 Episodic 生成摘要（基于下属 Community 摘要）
        3. 最后为 Saga 生成摘要（基于下属 Episodic 摘要）
        """
        levels = sorted(hierarchy.keys(), reverse=True)

        for level in levels:
            clusters = hierarchy[level]
            cluster_type = list(clusters.values())[0]['type'] if clusters else 'Unknown'
            print(f"  生成 {cluster_type} 层级的摘要 (Level {level})...")

            for cluster_id, cluster_data in clusters.items():
                if cluster_data['type'] == 'Community':
                    relations = community_relations.get(cluster_id, [])
                    if relations:
                        self.community_summary[cluster_id] = self._generate_summary_from_relations(relations)
                    else:
                        self.community_summary[cluster_id] = ""

                elif cluster_data['type'] == 'Episodic':
                    child_summaries = [
                        self.community_summary[child_id]
                        for child_id in cluster_data['children']
                        if child_id in self.community_summary and self.community_summary[child_id]
                    ]
                    if child_summaries:
                        self.community_summary[cluster_id] = self._generate_summary_from_child_summaries(
                            child_summaries, "Episodic"
                        )
                    else:
                        relations = community_relations.get(cluster_id, [])
                        self.community_summary[cluster_id] = self._generate_summary_from_relations(relations) if relations else ""

                elif cluster_data['type'] == 'Saga':
                    child_summaries = [
                        self.community_summary[child_id]
                        for child_id in cluster_data['children']
                        if child_id in self.community_summary and self.community_summary[child_id]
                    ]
                    if child_summaries:
                        self.community_summary[cluster_id] = self._generate_summary_from_child_summaries(
                            child_summaries, "Saga"
                        )
                    else:
                        relations = community_relations.get(cluster_id, [])
                        self.community_summary[cluster_id] = self._generate_summary_from_relations(relations) if relations else ""

    def _write_communities_to_neo4j(self, hierarchy: Dict[int, Dict]) -> None:
        """
        将社区层次结构写入 Neo4j
        """
        with self._driver.session() as session:
            print("  清理现有社区数据...")
            session.run("MATCH (c:Saga) DETACH DELETE c")
            session.run("MATCH (c:Episodic) DETACH DELETE c")
            session.run("MATCH (c:Community) DETACH DELETE c")

            saga_count = 0
            episodic_count = 0
            community_count = 0

            saga_ids = []
            episodic_ids = []
            community_ids = []

            print("  创建 Saga 节点...")
            if 0 in hierarchy:
                for saga_id, saga_data in hierarchy[0].items():
                    summary = self.community_summary.get(saga_id, "")[:2000]
                    session.run("""
                    CREATE (s:Saga {
                        saga_id: $saga_id,
                        name: 'Saga_' + toString($saga_id),
                        summary: $summary,
                        level: 0,
                        created_at: datetime()
                    })
                    """, saga_id=saga_id, summary=summary)
                    saga_ids.append(saga_id)
                    saga_count += 1

            print("  创建 Episodic 节点...")
            if 1 in hierarchy:
                for episodic_id, episodic_data in hierarchy[1].items():
                    summary = self.community_summary.get(episodic_id, "")[:2000]
                    session.run("""
                    CREATE (e:Episodic {
                        episodic_id: $episodic_id,
                        name: 'Episodic_' + toString($episodic_id),
                        summary: $summary,
                        level: 1,
                        created_at: datetime()
                    })
                    """, episodic_id=episodic_id, summary=summary)
                    episodic_ids.append(episodic_id)
                    episodic_count += 1

            print("  创建 Community 节点...")
            if 2 in hierarchy:
                for community_id, community_data in hierarchy[2].items():
                    summary = self.community_summary.get(community_id, "")[:2000]
                    session.run("""
                    CREATE (c:Community {
                        community_id: $community_id,
                        name: 'Community_' + toString($community_id),
                        summary: $summary,
                        member_count: $member_count,
                        level: 2,
                        created_at: datetime()
                    })
                    """, community_id=community_id,
                        summary=summary,
                        member_count=community_data.get('member_count', 0))
                    community_ids.append(community_id)
                    community_count += 1

            print("  建立社区层次关系...")

            if saga_ids and episodic_ids:
                for episodic_id, episodic_data in hierarchy.get(1, {}).items():
                    parent_id = episodic_data.get('parent')
                    if parent_id and parent_id in saga_ids:
                        session.run("""
                        MATCH (s:Saga {saga_id: $saga_id})
                        MATCH (e:Episodic {episodic_id: $episodic_id})
                        MERGE (s)-[:HAS_EPISODIC]->(e)
                        """, saga_id=parent_id, episodic_id=episodic_id)

            if episodic_ids and community_ids:
                for community_id, community_data in hierarchy.get(2, {}).items():
                    parent_id = community_data.get('parent')
                    if parent_id and parent_id in episodic_ids:
                        session.run("""
                        MATCH (e:Episodic {episodic_id: $episodic_id})
                        MATCH (c:Community {community_id: $community_id})
                        MERGE (e)-[:HAS_MEMBER]->(c)
                        """, episodic_id=parent_id, community_id=community_id)

            print("  建立 Community -> Entity 关系...")
            entity_count = 0
            for entity_name, cluster_ids in self.entity_info.items():
                for cluster_id in cluster_ids:
                    if cluster_id in community_ids:
                        session.run("""
                        MATCH (c:Community {community_id: $community_id})
                        MATCH (e)
                        WHERE e.name = $entity_name
                        MERGE (c)-[:HAS_MEMBER]->(e)
                        """, community_id=cluster_id, entity_name=entity_name)
                        entity_count += 1

            print(f"  创建完成：{saga_count} 个 Saga, {episodic_count} 个 Episodic, "
                  f"{community_count} 个 Community, {entity_count} 个实体关系")

    def get_community_summaries(self) -> Dict[int, str]:
        """获取社区摘要"""
        return self.community_summary

    def close(self) -> None:
        """关闭数据库连接"""
        self._driver.close()
