# 地质识图智能体 (Geological Map Recognition Agent) 规格说明书 (Spec)

## 1. 项目概述

本项目旨在构建一个多模态地质读图智能体，能够融合地质图图像信息与外部领域知识图谱（Neo4j），解答复杂的地质与找矿问题。系统全面基于 LlamaIndex 框架构建。

## 2. 架构设计

智能体架构采用 LlamaIndex 官方推荐的 `AgentRunner` 或 `Workflows` 事件驱动架构，摒弃 LangGraph。

### 2.1 核心组件

* **LLM 引擎**：qwen-3.5-plus

* **Embedding 引擎**：智谱 AI (`embedding-3`)

* **图数据库**：Neo4j (存储地质本体及 GraphRAG 社区摘要)

* **视觉模型**：YOLOv10 (布局/图例检测) + OpenCV + OCR (位于 `PEACE` 模块)

## 3. 智能体五大核心能力规范

### 3.1 感知能力 (Perception)

* **地图基础信息感知**：调用 PEACE 的 HIE 模块获取图幅名、比例尺、经纬度。

* **图例要素感知**：裁剪图例区域，提取色块 RGB 及 OCR 文本（岩性、时代、断层类型）。

* **空间要素感知 (vision\_process)**：在主图上识别特定颜色/纹理的岩性单元分布、断层线走向与矿点标志。

### 3.2 记忆能力 (Memory)

* **短期记忆**：集成 `ChatMemoryBuffer`，维持多轮问答上下文，支持用户对同一张地图进行追问。

* **长期记忆**：通过 LlamaIndex 的 `PropertyGraphIndex` 对接基于 Neo4j 构建的地质知识图谱，实现持久化的地质先验知识检索。

### 3.3 工具调用能力 (Tools)

提供标准化的 LlamaIndex `FunctionTool`：

1. `peace_map_analyze`: 提取地图元数据与图例。
2. `kg_query`: 检索 Neo4j 知识图谱。
3. `vision_analyze` (待完善): 提取主图空间要素（断层线、矿点位置等）。
4. `spatial_calculator`: 计算空间邻接与距离（基于 Python/GeoPandas）。
5. `web_search`: Google/DuckDuckGo 搜索引擎。

### 3.4 规划能力 (Planning)

* **任务拆解**：对于复合指令（如“分析断层对矿点的影响”），智能体能够将其拆解为：(1)感知矿点和断层位置 -> (2)计算空间距离 -> (3)查询知识图谱中该类断层的控矿规律 -> (4)综合推理。

* 采用 `ReAct` 范式进行 Step-by-Step 规划。

### 3.5 推理能力 (Reasoning)

* **空间与逻辑联合推理**：融合视觉感知的物理距离和图谱感知的逻辑联系，输出可靠的成矿预测或地质解释。

* **信息冲突解决**：在视觉提取错误或图谱信息缺失时，具备回退（Fallback）或容错提示机制。

## 4. 前端交互设计 (Frontend)

在完成智能体核心逻辑后，需要开发一个 Web 前端页面：

* **上传区**：支持用户上传地质图文件。

* **对话区**：类似 ChatGPT 的多轮对话界面。

* **可视化区**：展示地图解析结果（高亮边界框）、知识图谱子图可视化（如 PyVis/Plotly）。

