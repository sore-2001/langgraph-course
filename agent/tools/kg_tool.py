"""
Knowledge Graph Query Tool for Neo4j with GraphRAG Community Summaries

This tool provides a natural language interface to query the geological knowledge graph
using Neo4j Cypher queries, with access to GraphRAG-generated community summaries.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()


class KGQueryTool:
    """Knowledge Graph Query Tool using Neo4j Cypher + GraphRAG Community Summaries."""

    def __init__(self):
        self._driver = None
        self._initialized = False

    def _initialize(self) -> bool:
        """Lazy initialization of the Neo4j driver."""
        if self._initialized:
            return True

        try:
            # Neo4j configuration
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD")

            # Initialize Neo4j driver for direct queries
            self._driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            self._initialized = True
            print(f"KG initialized successfully (Neo4j + GraphRAG Community Summaries)")
            return True

        except Exception as e:
            print(f"Failed to initialize KG: {str(e)}")
            return False

    def query(self, query_text: str) -> str:
        """
        Query the geological knowledge graph with GraphRAG community summaries.

        Args:
            query_text: Natural language query (e.g., "川口矿区有哪些断层？")

        Returns:
            Query results as formatted string
        """
        if not self._initialized:
            self._initialize()
        if not self._driver:
            return "Error: Neo4j driver not initialized"

        try:
            with self._driver.session() as session:
                results = []

                # Step 1: Search for matching entities
                entity_cypher = """
                MATCH (n)
                WHERE n.name CONTAINS $q OR
                      (n.description IS NOT NULL AND n.description CONTAINS $q) OR
                      (n.type IS NOT NULL AND n.type CONTAINS $q)
                RETURN labels(n) as labels, n.name as name, n.description as desc, n.type as type
                LIMIT 10
                """
                entity_result = session.run(entity_cypher, q=query_text)
                entities = []
                for record in entity_result:
                    # Filter out internal labels
                    labels = [l for l in (list(record['labels']) if record['labels'] else [])
                              if not l.startswith('__')]
                    if not labels:
                        labels = ['Entity']

                    name = record['name'] or 'Unknown'
                    desc = record['desc'] or 'No description'
                    entity_type = record['type'] or ''

                    result_str = f"[{', '.join(labels)}] {name}"
                    if entity_type:
                        result_str += f" ({entity_type})"
                    result_str += f": {desc[:200] if desc else 'N/A'}"
                    entities.append(result_str)

                if entities:
                    results.append("【实体检索结果】")
                    results.append("\n\n".join(entities))

                # Step 2: Search for GraphRAG community summaries related to the query
                community_cypher = """
                MATCH (c:Community)
                WHERE c.name CONTAINS $q OR c.summary CONTAINS $q
                RETURN c.name as name, c.summary as summary
                LIMIT 3
                """
                community_result = session.run(community_cypher, q=query_text)
                communities = []
                for record in community_result:
                    summary = record['summary'] or 'No summary available'
                    communities.append(f"【{record['name']}】\n{summary}")

                if communities:
                    results.append("\n【GraphRAG 社区摘要】")
                    results.append("\n\n".join(communities))

                # Step 3: If no direct matches, search by relationships
                if not entities and not communities:
                    rel_cypher = """
                    MATCH (n)-[r]->(m)
                    WHERE n.name CONTAINS $q OR m.name CONTAINS $q
                    RETURN n.name as source, type(r) as rel, m.name as target,
                           labels(n) as source_labels, labels(m) as target_labels
                    LIMIT 10
                    """
                    rel_result = session.run(rel_cypher, q=query_text)
                    relationships = []
                    for record in rel_result:
                        source = record['source'] or 'Unknown'
                        rel = record['rel'] or 'RELATED'
                        target = record['target'] or 'Unknown'

                        source_labels = [l for l in (list(record['source_labels']) if record['source_labels'] else [])
                                         if not l.startswith('__')]
                        target_labels = [l for l in (list(record['target_labels']) if record['target_labels'] else [])
                                         if not l.startswith('__')]

                        source_label = source_labels[0] if source_labels else 'Entity'
                        target_label = target_labels[0] if target_labels else 'Entity'

                        relationships.append(f"{source_label}:{source} -[{rel}]-> {target_label}:{target}")

                    if relationships:
                        results.append("【关系检索结果】")
                        results.append("\n\n".join(relationships))

                if results:
                    return "\n\n".join(results)

                return f"未找到与'{query_text}'相关的记录"

        except Exception as e:
            return f"Error: {str(e)}"

    def query_with_graph_data(self, query_text: str, limit: int = 20) -> dict:
        """
        Query the knowledge graph and return structured graph data for visualization.

        Args:
            query_text: Natural language query
            limit: Maximum number of nodes and relationships to return

        Returns:
            dict with 'nodes' and 'edges' arrays for graph visualization
        """
        if not self._initialized:
            self._initialize()
        if not self._driver:
            return {"nodes": [], "edges": [], "error": "Neo4j driver not initialized"}

        try:
            with self._driver.session() as session:
                nodes = {}
                edges = []

                # Query entities and relationships
                cypher = """
                MATCH (n)
                WHERE n.name CONTAINS $q OR
                      (n.description IS NOT NULL AND n.description CONTAINS $q) OR
                      (n.type IS NOT NULL AND n.type CONTAINS $q)
                OPTIONAL MATCH (n)-[r]->(m)
                WHERE r IS NOT NULL
                RETURN n, r, m
                LIMIT $limit
                """
                result = session.run(cypher, q=query_text, limit=limit)

                node_id = 0
                node_id_map = {}

                for record in result:
                    # Process source node
                    n = record.get('n')
                    if n and n.id not in node_id_map:
                        labels = [l for l in list(n.labels) if not l.startswith('__')]
                        node_type = labels[0] if labels else 'Entity'
                        nodes[n.id] = {
                            "id": n.id,
                            "name": n.get('name', 'Unknown'),
                            "type": node_type,
                            "description": n.get('description', '')[:100] if n.get('description') else '',
                        }
                        node_id_map[n.id] = node_id
                        node_id += 1

                    # Process target node
                    m = record.get('m')
                    if m and m.id not in node_id_map:
                        labels = [l for l in list(m.labels) if not l.startswith('__')]
                        node_type = labels[0] if labels else 'Entity'
                        nodes[m.id] = {
                            "id": m.id,
                            "name": m.get('name', 'Unknown'),
                            "type": node_type,
                            "description": m.get('description', '')[:100] if m.get('description') else '',
                        }
                        node_id_map[m.id] = node_id
                        node_id += 1

                    # Process relationship
                    r = record.get('r')
                    if r and n and m:
                        edges.append({
                            "source": node_id_map[n.id],
                            "target": node_id_map[m.id],
                            "type": r.type,
                        })

                return {
                    "nodes": list(nodes.values()),
                    "edges": edges,
                }

        except Exception as e:
            return {"nodes": [], "edges": [], "error": str(e)}

    def query_community_summary(self, entity_name: str) -> str:
        """
        Query GraphRAG community summaries for a specific geological entity.

        Args:
            entity_name: The name of the geological entity

        Returns:
            Community summary as formatted string
        """
        if not self._driver:
            return "Error: Neo4j driver not initialized"

        try:
            with self._driver.session() as session:
                # Query the community that the entity belongs to
                result = session.run("""
                MATCH (c:Community)-[:HAS_MEMBER]->(e)
                WHERE e.name CONTAINS $entity_name
                RETURN c.name as name, c.summary as summary
                LIMIT 3
                """, entity_name=entity_name)

                summaries = []
                for record in result:
                    summary = record['summary'] or 'No summary available'
                    summaries.append(f"【{record['name']}】\n{summary}")

                if not summaries:
                    return f"未找到实体'{entity_name}'所属的社区摘要"

                return "\n\n".join(summaries)
        except Exception as e:
            return f"Error querying community summaries: {str(e)}"

    def get_graph_stats(self) -> dict:
        """Get knowledge graph statistics."""
        if not self._driver:
            return {"error": "Neo4j driver not initialized"}

        try:
            with self._driver.session() as session:
                stats = {}

                # Count nodes by label
                result = session.run("""
                MATCH (n)
                WITH labels(n)[0] as label
                RETURN label, count(*) as count
                ORDER BY count DESC
                """)
                stats['nodes_by_label'] = {r['label']: r['count'] for r in result}

                # Count relationships by type
                result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
                """)
                stats['relationships_by_type'] = {r['type']: r['count'] for r in result}

                # Count communities
                result = session.run("MATCH (c:Community) RETURN count(c) as count")
                stats['community_count'] = result.single()['count']

                return stats
        except Exception as e:
            return {"error": str(e)}


# Create singleton instance
_kg_tool = None


def get_kg_tool() -> KGQueryTool:
    """Get or create the KG query tool singleton."""
    global _kg_tool
    if _kg_tool is None:
        _kg_tool = KGQueryTool()
    return _kg_tool


def kg_query(query: str) -> str:
    """
    Query the geological knowledge graph with GraphRAG community summaries.

    This tool searches the Neo4j-backed knowledge graph for information about:
    - Mineral deposits and their characteristics
    - Geological formations and rock types
    - Fault systems and tectonic features
    - Metallogenic conditions and predictions
    - GraphRAG community summaries for broader context

    Args:
        query: Natural language query about geological knowledge

    Returns:
        Retrieved information from the knowledge graph
    """
    return get_kg_tool().query(query)


def kg_community_summary(entity_name: str) -> str:
    """
    Query GraphRAG community summaries for a specific geological entity.

    This tool retrieves community summaries for the given entity,
    providing broader context and structural relationships.

    Args:
        entity_name: Name of the geological entity (e.g., '第四系', '断层')

    Returns:
        Community summary context
    """
    return get_kg_tool().query_community_summary(entity_name)


def kg_query_with_graph(query: str, limit: int = 20) -> dict:
    """
    Query the geological knowledge graph and return graph data for visualization.

    This tool returns structured graph data (nodes and edges) that can be
    visualized using graph visualization libraries like AntV G6.

    Args:
        query: Natural language query about geological knowledge
        limit: Maximum number of nodes to return (default: 20)

    Returns:
        dict with 'nodes' and 'edges' arrays for visualization
    """
    return get_kg_tool().query_with_graph_data(query, limit)
