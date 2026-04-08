# 开发任务拆解 (Tasks)

## 阶段 1：智能体底层工具完善 (Tool Layer)
- [ ] **Task 1.1**: 完善 `vision_process` 模块，补充 `agent/tools/vision_tool.py` 的具体实现，支持主图中断层/矿点/岩性单元的坐标和分布提取。
- [ ] **Task 1.2**: 开发空间计算工具 (`spatial_calculator`)，支持计算提取到的不同地质要素之间的距离和邻接关系。
- [ ] **Task 1.3**: 测试并优化 `agent/tools/peace_geo_tool.py` 的容错处理，确保其输出结构对 LLM 友好。
- [ ] **Task 1.4**: 优化 `agent/tools/kg_tool.py`，支持针对 GraphRAG 社区摘要的高效检索。

## 阶段 2：LlamaIndex 智能体编排 (Agent Orchestration)
- [ ] **Task 2.1**: 重构 `agent/agent.py`，采用 LlamaIndex `AgentRunner` 或 `Workflows` 替代原有的基础实现。
- [ ] **Task 2.2**: 注册所有地质感知与分析工具，并配置工具的 Description 和参数 Schema，优化大模型的 Tool Selection 准确率。
- [ ] **Task 2.3**: 增加 `ChatMemoryBuffer`，实现跨轮次的地图上下文状态保持。
- [ ] **Task 2.4**: 编写定制化的 `SystemPrompt`，强化智能体的规划 (Planning) 与推理 (Reasoning) 行为准则。

## 阶段 3：多模态推理与端到端测试 (Testing)
- [ ] **Task 3.1**: 编写测试脚本，上传 `data/gouli_map` 下的测试地图。
- [ ] **Task 3.2**: 针对“感知-记忆-工具-推理”全链路进行测试（如提问“该图中的断层交汇处有哪些岩性？”）。
- [ ] **Task 3.3**: 评估并修正幻觉、死循环或工具调用失败的边界情况。

## 阶段 4：前端交互页面开发 (Frontend Web UI)
- [ ] **Task 4.1**: 技术选型（推荐使用 Streamlit 或 Gradio，便于快速与 Python 后端集成）。
- [ ] **Task 4.2**: 开发侧边栏或顶部的文件上传组件（支持图片上传）。
- [ ] **Task 4.3**: 开发聊天窗口组件，集成 LlamaIndex 的 Chat 接口，实现流式输出。
- [ ] **Task 4.4**: 开发结果可视化组件（渲染 PEACE 提取的 Bounding Box 以及查询到的 KG 节点关系图）。