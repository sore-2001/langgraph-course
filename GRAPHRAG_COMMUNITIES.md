# GraphRAG 社区检测完成报告

## 实现日期
2026-03-23

## 实现依据
基于 LlamaIndex 官方 GraphRAG 文档：
https://developers.llamaindex.ai/python/examples/cookbooks/graphrag_v2/

## 社区层次结构

已成功在 Neo4j 中构建三层社区层次结构：

```
(Saga:38)-[:HAS_EPISODIC]->(Episodic:88)-[:HAS_MEMBER]->(Community:254)-[:HAS_MEMBER]->(Entity:1040)
```

### 节点统计

| 层级 | 标签 | 节点数 | 说明 |
|------|------|--------|------|
| Level 2 | Saga | 38 | 大型叙事社区（顶层） |
| Level 1 | Episodic | 88 | 主题情节社区（中层） |
| Level 0 | Community | 254 | 基层社区（底层） |
| - | Entity | 1040 | 地质实体节点 |

### 关系统计

| 关系类型 | 数量 | 说明 |
|----------|------|------|
| HAS_EPISODIC | 88 | Saga -> Episodic |
| HAS_MEMBER | 1070 | Episodic -> Community + Community -> Entity |

## 实现文件

### 1. `data_process/graphrag_store.py`
扩展 `Neo4jPropertyGraphStore` 实现社区检测与存储：

```python
class GraphRAGStore(Neo4jPropertyGraphStore):
    """
    扩展 Neo4jPropertyGraphStore，实现社区检测和摘要存储到 Neo4j
    """

    def build_communities(self, levels: int = 3):
        """构建社区层次结构并生成摘要"""

    def _create_nx_graph(self):
        """从 Neo4j 创建 NetworkX 图"""

    def _summarize_communities(self, hierarchical_communities):
        """使用 LLM 为每个社区生成摘要"""

    def _write_communities_to_neo4j(self, hierarchical_communities):
        """将社区层次结构写入 Neo4j"""
```

### 2. `run_graphrag.py`
运行社区检测的脚本：

```bash
python run_graphrag.py
```

## 核心算法

使用 **Hierarchical Leiden** 算法进行社区检测：

```python
from graspologic.partition import hierarchical_leiden

clusters = hierarchical_leiden(
    nx_graph,
    max_cluster_size=self.max_cluster_size  # 默认 5
)
```

## 社区摘要示例

### Community_318 (成员数：19)
```
## 地质知识图谱关系摘要

### 一、实体类型与关系
本研究主要涉及地质实体元素的含量关系，包括**主要元素**、**矿体**以及各地层单元如**灰岩**、**白云岩**、**硅质岩**和**粉砂岩**等。
```

### Community_322 (成员数：19)
```
## 矿体空间分布与构造背景关系摘要

**矿体空间分布**是该知识图谱的核心构造架构，控制着矿体的空间展布...
```

### Community_82 (成员数：18)
```
## 矿床勘探地质知识图谱摘要

### 一、矿床类型与空间关系
**xx 钨矿床**是该知识图谱的核心地质单元，属于一个完整的多金属矿床系统...
```

## 查询增强

使用 GraphRAG 后，查询可以：
1. **定位实体所属社区** - 快速找到相关上下文
2. **利用社区摘要** - 无需遍历所有实体关系
3. **分层检索** - 从 Saga -> Episodic -> Community 逐步细化

## 依赖安装

```bash
uv pip install graspologic
```

## 使用说明

### 1. 运行社区检测
```bash
python run_graphrag.py
```

### 2. 查询社区摘要
```python
from data_process.graphrag_store import GraphRAGStore

store = GraphRAGStore(
    username="neo4j",
    password="your_password",
    url="bolt://localhost:7687",
)

# 获取社区摘要
summaries = store.get_community_summaries()
for community_id, summary in summaries.items():
    print(f"Community {community_id}: {summary}")
```

### 3. Cypher 查询社区
```cypher
// 查询所有 Saga 节点
MATCH (s:Saga) RETURN s.name, s.summary

// 查询特定 Saga 下的所有 Community
MATCH (s:Saga)-[:HAS_EPISODIC]->(e:Episodic)-[:HAS_MEMBER]->(c:Community)
WHERE s.saga_id = 1
RETURN c.name, c.summary, c.member_count

// 查询实体所属的社区
MATCH (c:Community)-[:HAS_MEMBER]->(e)
WHERE e.name = '塘江沅钨矿'
RETURN c.name, c.summary
```

## 注意事项

1. **LLM 调用次数**：每个社区都会调用一次 LLM 生成摘要，254 个社区约需 254 次 API 调用
2. **摘要长度限制**：输入限制为 4000 token，输出限制为 2000 token
3. **社区大小**：`max_cluster_size` 参数控制每个社区的最大实体数，越小社区越多
4. **持久化**：社区节点和关系已持久化到 Neo4j，但 `entity_info` 和 `community_summary` 字典仅在内存中

## 后续优化建议

1. **缓存社区摘要**：避免重复生成
2. **批量生成摘要**：减少 LLM 调用次数
3. **动态层次结构**：根据图谱大小自动调整层级数
4. **GraphRAG 查询引擎**：实现完整的 `GraphRAGQueryEngine` 类
