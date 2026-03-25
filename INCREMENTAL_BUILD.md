 增量构建模块已创建完成。让我总结一下：                                                                                                              
  
  1. data_process/incremental_builder.py - 核心增量构建模块
    - IncrementalGraphBuilder 类
    - 文档指纹追踪（SHA-256）
    - 自动检测新增/修改/删除文档
    - 增量写入知识图谱
  2. run_incremental.py - 命令行入口工具
  3. INCREMENTAL_BUILD.md - 详细使用文档

  使用方法

  # 1. 首次全量构建
  python run_incremental.py --init

  # 2. 增量更新（日常使用）
  python run_incremental.py --update

  # 3. 添加指定文档
  python run_incremental.py --add report1.pdf report2.pdf

  # 4. 查看已处理文档
  python run_incremental.py --list

  # 5. 重建社区结构
  python run_incremental.py --rebuild-communities

  核心特性

  ┌──────────────┬──────────────────────────────────────────────┐
  │     特性     │                     说明                     │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 文档指纹     │ SHA-256 哈希检测文件变更                     │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 注册表持久化 │ ./data/document_registry.json 追踪已处理文档 │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 增量 upsert  │ 只写入新增/修改的数据，不删除已有数据        │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 实体去重     │ 基于 (name, entity_type) 自动去重            │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 来源追溯     │ 保留每个 Chunk 的来源信息                    │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 可选社区重建 │ 增量更新后可选重建 GraphRAG 社区             │
  └──────────────┴──────────────────────────────────────────────┘

  推荐工作流

  1. 首次：python run_incremental.py --init
  2. 新增文档后：python run_incremental.py --update
  3. 每 10-20 个文档：python run_incremental.py --update --rebuild-communities

  需要我帮你测试一下增量更新功能吗？

✻ Brewed for 4m 21s · 1 shell still running

● Background command "Run full community detection" completed (exit code 0)                                                                           

  Read 1 file (ctrl+o to expand)                                                                                                                      
                                                                                                                                                      
● 社区检测任务已成功完成。结果显示：                                                                                                                  
                                                                                                                                                      
  GraphRAG 社区构建完成                                                                                                                               
                                                                                                                                                        ============================================================                                                                                        
  社区构建完成统计                                                                                                                                    
  ============================================================
  实体信息：1040 个实体
  社区摘要：375 个社区

  最终结果：
  - 37 个 Saga 节点 (Level 2 - 大型叙事社区)
  - 88 个 Episodic 节点 (Level 1 - 主题情节社区)
  - 250 个 Community 节点 (Level 0 - 基层社区)
  - 787 个 Community -> Entity 关系

  社区层次结构已成功写入 Neo4j：
  (Saga:37)-[:HAS_EPISODIC]->(Episodic:88)-[:HAS_MEMBER]->(Community:250)-[:HAS_MEMBER]->(Entity:1040)

  ---
  现在你的知识图谱系统包含：

  1. 完整知识图谱 - 1040 个实体节点，带社区层次结构
  2. 增量构建模块 - 支持后续新增文档，无需删除重建
  3. GraphRAG 社区 - 三层社区结构，支持分层检索
