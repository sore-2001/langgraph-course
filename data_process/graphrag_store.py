"""
GraphRAG Store - 基于 LlamaIndex PropertyGraphIndex 的社区检测与摘要存储

基于官方文档实现：https://developers.llamaindex.ai/python/examples/cookbooks/graphrag_v2/
"""
import re
import networkx as nx
from graspologic.partition import hierarchical_leiden
from collections import defaultdict
from typing import Dict, List, Any, Optional
from llama_index.core.llms import ChatMessage
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core import Settings


class GraphRAGStore(Neo4jPropertyGraphStore):
    """
    扩展 Neo4jPropertyGraphStore，实现社区检测和摘要存储到 Neo4j

    社区层次结构：
    - Level 0: Community (基层社区)
    - Level 1: Episodic (主题情节/子社区)
    - Level 2: Saga (大型叙事/超级社区)
    """

    def __init__(self, *args, max_cluster_size: int = 5, llm=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_cluster_size = max_cluster_size
        self.llm = llm or Settings.llm
        self.entity_info: Dict[str, List[int]] = {}
        self.community_summary: Dict[int, str] = {}

        # 使用父类的 driver，无需重新创建
        # 父类已经创建了 self._driver

    def _create_nx_graph(self) -> nx.Graph:
        """
        从 Neo4j 创建 NetworkX 图

        只获取实体节点之间的关系（排除 Chunk 节点和 MENTIONS 关系）
        """
        nx_graph = nx.Graph()

        with self._driver.session() as session:
            # 获取所有实体间关系（排除 MENTIONS 和 Chunk 相关）
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
                r.description as description
            """)

            for record in result:
                source = record["source_name"]
                target = record["target_name"]
                rel_type = record["relationship"]
                description = record.get("description", "")

                # 添加节点
                nx_graph.add_node(source, entity_type=record["source_type"])
                nx_graph.add_node(target, entity_type=record["target_type"])

                # 添加边
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
        构建社区层次结构并生成摘要

        Args:
            levels: 层次结构层级数 (默认 3 层：Community -> Episodic -> Saga)
        """
        print("开始构建社区层次结构...")

        # 1. 创建 NetworkX 图
        nx_graph = self._create_nx_graph()

        # 2. 应用 hierarchical_leiden 算法
        print("运行 Leiden 社区检测算法...")
        clusters = hierarchical_leiden(
            nx_graph,
            max_cluster_size=self.max_cluster_size
        )

        # 3. 收集社区信息
        print("收集社区信息...")
        self.entity_info, community_info = self._collect_community_info(
            nx_graph, clusters
        )

        # 4. 按层次分组社区
        print("构建社区层次结构...")
        hierarchical_communities = self._group_communities_by_level(
            community_info, levels
        )

        # 5. 生成社区摘要
        print("生成社区摘要...")
        self._summarize_communities(hierarchical_communities)

        # 6. 将社区层次结构写入 Neo4j
        print("将社区写入 Neo4j...")
        self._write_communities_to_neo4j(hierarchical_communities)

        print("社区构建完成!")

    def _collect_community_info(
        self,
        nx_graph: nx.Graph,
        clusters
    ) -> tuple[Dict, Dict]:
        """
        收集每个社区的信息

        Returns:
            entity_info: Dict[entity_name, List[cluster_id]]
            community_info: Dict[cluster_id, List[relationship_details]]
        """
        entity_info = defaultdict(set)
        community_info = defaultdict(list)

        for item in clusters:
            node = item.node
            cluster_id = item.cluster

            # 记录实体所属的社区
            entity_info[node].add(cluster_id)

            # 收集社区内的关系详情
            for neighbor in nx_graph.neighbors(node):
                edge_data = nx_graph.get_edge_data(node, neighbor)
                if edge_data:
                    detail = (
                        f"{node} -> {neighbor} -> "
                        f"{edge_data['relationship']} -> "
                        f"{edge_data.get('description', '')}"
                    )
                    community_info[cluster_id].append(detail)

        # 转换集合为列表
        entity_info = {k: list(v) for k, v in entity_info.items()}

        return dict(entity_info), dict(community_info)

    def _group_communities_by_level(
        self,
        community_info: Dict,
        levels: int
    ) -> Dict[str, Dict]:
        """
        将社区按层次分组

        基于社区 ID 的层次结构：
        - Level 0 (Community): 基础社区
        - Level 1 (Episodic): 多个 Community 组成的主题社区
        - Level 2 (Saga): 多个 Episodic 组成的大型叙事社区
        """
        # 按社区大小排序
        sorted_communities = sorted(
            community_info.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        hierarchical = {
            "Community": {},
            "Episodic": {},
            "Saga": {}
        }

        # 简单地按社区大小分配层次
        # 最大的社区可能是 Saga，中等的是 Episodic，小的是 Community
        for i, (cluster_id, details) in enumerate(sorted_communities):
            if i < len(sorted_communities) // 10:  # 前 10% 为 Saga
                hierarchical["Saga"][cluster_id] = details
            elif i < len(sorted_communities) // 3:  # 前 10%-33% 为 Episodic
                hierarchical["Episodic"][cluster_id] = details
            else:  # 其余为 Community
                hierarchical["Community"][cluster_id] = details

        return hierarchical

    def generate_community_summary(self, text: str) -> str:
        """使用 LLM 生成社区摘要"""
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

    def _summarize_communities(self, hierarchical_communities: Dict) -> None:
        """为每个社区生成摘要"""
        for level, communities in hierarchical_communities.items():
            print(f"  生成 {level} 层级的摘要...")
            for community_id, details in communities.items():
                if len(details) == 0:
                    continue

                details_text = "\n".join(details) + "."

                # 限制输入长度，避免超出 token 限制
                if len(details_text) > 4000:
                    details_text = details_text[:4000] + "..."

                self.community_summary[community_id] = self.generate_community_summary(
                    details_text
                )

    def _write_communities_to_neo4j(self, hierarchical_communities: Dict) -> None:
        """
        将社区层次结构写入 Neo4j

        创建以下结构：
        - (:Saga)-[:HAS_EPISODIC]->(:Episodic)-[:HAS_MEMBER]->(:Community)
        - (:Community)-[:HAS_MEMBER]->(:Entity)
        """
        with self._driver.session() as session:
            # 1. 清理现有的社区节点
            print("  清理现有社区数据...")
            session.run("MATCH (c:Saga) DETACH DELETE c")
            session.run("MATCH (c:Episodic) DETACH DELETE c")
            session.run("MATCH (c:Community) DETACH DELETE c")

            # 2. 创建社区节点并建立关系
            saga_count = 0
            episodic_count = 0
            community_count = 0

            # 创建 Saga 节点
            print("  创建 Saga 节点...")
            saga_ids = list(hierarchical_communities["Saga"].keys())
            for saga_id in saga_ids:
                summary = self.community_summary.get(saga_id, "")[:2000]
                session.run("""
                CREATE (s:Saga {
                    saga_id: $saga_id,
                    name: 'Saga_' + toString($saga_id),
                    summary: $summary,
                    level: 2,
                    created_at: datetime()
                })
                """, saga_id=saga_id, summary=summary)
                saga_count += 1

            # 创建 Episodic 节点
            print("  创建 Episodic 节点...")
            episodic_ids = list(hierarchical_communities["Episodic"].keys())
            for episodic_id in episodic_ids:
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
                episodic_count += 1

            # 创建 Community 节点
            print("  创建 Community 节点...")
            community_ids = list(hierarchical_communities["Community"].keys())
            for community_id in community_ids:
                details = hierarchical_communities["Community"][community_id]
                summary = self.community_summary.get(community_id, "")[:2000]

                session.run("""
                CREATE (c:Community {
                    community_id: $community_id,
                    name: 'Community_' + toString($community_id),
                    summary: $summary,
                    member_count: $member_count,
                    level: 0,
                    created_at: datetime()
                })
                """, community_id=community_id,
                    summary=summary,
                    member_count=len(details))
                community_count += 1

            # 3. 建立层次关系
            print("  建立社区层次关系...")

            # Saga -> Episodic (简单按 ID 关联，实际应该更复杂的逻辑)
            if saga_ids and episodic_ids:
                for i, episodic_id in enumerate(episodic_ids):
                    saga_id = saga_ids[i % len(saga_ids)]
                    session.run("""
                    MATCH (s:Saga {saga_id: $saga_id})
                    MATCH (e:Episodic {episodic_id: $episodic_id})
                    MERGE (s)-[:HAS_EPISODIC]->(e)
                    """, saga_id=saga_id, episodic_id=episodic_id)

            # Episodic -> Community
            if episodic_ids and community_ids:
                for i, community_id in enumerate(community_ids):
                    episodic_id = episodic_ids[i % len(episodic_ids)]
                    session.run("""
                    MATCH (e:Episodic {episodic_id: $episodic_id})
                    MATCH (c:Community {community_id: $community_id})
                    MERGE (e)-[:HAS_MEMBER]->(c)
                    """, episodic_id=episodic_id, community_id=community_id)

            # 4. 创建 Community -> Entity 关系
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
        if not self.community_summary:
            self.build_communities()
        return self.community_summary

    def close(self) -> None:
        """关闭数据库连接"""
        self._driver.close()
