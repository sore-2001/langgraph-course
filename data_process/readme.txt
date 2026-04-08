your_project/
├── data_process/          # 数据加工核心目录（所有代码放这里）
│   ├── __init__.py        # 包初始化文件，声明对外暴露的类/函数
│   ├── geo_ontology.py    # 地质本体定义（Pydantic模型：实体+关系+三元组）
│   ├── pdf_loader.py      # PDF加载与文本提取（适配LlamaIndex）
│   ├── triple_extractor.py # LLM三元组抽取（基于本体的标准化抽取）
│   ├── graph_builder.py   # 知识图谱构建（对接LlamaIndex+Neo4j）
│   ├── config.py          # 配置文件（LLM/Neo4j/路径等参数）
│   └── utils.py           # 通用工具函数（校验、日志、格式转换）
├── geology_data/          # 地质PDF文件目录（存放你的找矿论文PDF）
│   └── 大模型驱动的东天山-北山找矿知识图谱构建及应用.pdf
├── chroma_db/             # 可选：向量数据库缓存目录
└── main.py                # 主执行文件（调用data_process中的模块）

