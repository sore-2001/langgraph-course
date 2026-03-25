# PEACE 地质图解析模块集成说明

## 概述

PEACE (Empowering Geologic Map Holistic Understanding with MLLMs) 是一个基于多模态大语言模型的地质图 holistic 理解系统。

### 核心功能

1. **HIE (Hierarchical Information Extraction)** - 分层信息提取
   - 地图布局检测（主图、图例、标题、比例尺等）
   - 图例元数据提取（颜色、文本、岩性、地层时代）
   - 基本信息提取（图幅名、经纬度范围、邻接区域）

2. **DKI (Domain Knowledge Injection)** - 领域知识注入
   - 岩石类型知识库
   - 地层时代知识库
   - 活动断裂数据库
   - 历史地震数据库

3. **PEQA (Prompt-enhanced Question Answering)** - 提示增强问答

## 依赖配置

PEACE 模块的依赖已集成到项目的 uv 环境中。主要依赖包括：

```
- llama-index>=0.10.0
- opencv-python>=4.8.0
- paddlepaddle>=2.5.0
- paddleocr>=2.7.0
- pandas>=2.2.2
- geopandas>=1.0.1
- matplotlib>=3.9.2
- transformers>=4.50.0
- sentence_transformers>=3.1.1
- azure-identity>=1.17.1
- earthengine-api>=1.1.1
- torchvision>=0.15.2
```

## API 配置

PEACE 模块使用项目统一的 API 配置（通过 `.env` 文件）：

```env
# OpenAI 兼容 API 配置（推荐使用本地代理）
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=http://127.0.0.1:8045/v1
OPENAI_MODEL_NAME=gemini-3-flash

# Azure OpenAI 配置（可选）
AZURE_OPENAI_ENDPOINT=
AZURE_IDENTITY_ID=
AZURE_API_VERSION=2024-08-01-preview
```

**注意：** PEACE 模块会自动检测配置，优先使用 Azure OpenAI（如果配置），否则使用标准 OpenAI 兼容 API。

## 使用方法

### 1. 作为 Agent 工具使用

在 agent 交互模式中，直接使用 `peace_map_analyze` 工具：

```python
# 在 agent 对话中
用户：请分析这张地质图 data/gouli_map/sample.jpg
Agent: [使用 peace_map_analyze 工具分析地图]
```

### 2. 直接调用 PEACE 模块

```python
from agent.tools.peace_geo_tool import (
    analyze_geological_map,
    get_rock_knowledge,
    detect_map_components
)

# 分析地质图
result = analyze_geological_map("data/gouli_map/sample.jpg", extract_mode="full")
print(result)

# 获取岩石知识
knowledge = get_rock_knowledge("第四系")
print(knowledge)

# 检测地图组件
components = detect_map_components("data/gouli_map/sample.jpg")
print(components)
```

### 3. 使用 PEACE 原始模块

```python
import sys
sys.path.append("PEACE")

from PEACE.modules.HIE import hierarchical_information_extraction
from PEACE.agents.geologist import geologist_agent

# HIE 模块 - 地质图数字化
hie = hierarchical_information_extraction()
meta = hie.digitalize("sample.jpg")

# 地质学家 Agent - 图例分析
geologist = geologist_agent()
map_layout = geologist.get_map_layout("sample.jpg")
legend_metadata = geologist.get_legend_metadata("legend.jpg", legend_bndbox)
```

## PEACE 模块结构

```
PEACE/
├── modules/                 # 核心功能模块
│   ├── HIE.py              # 分层信息提取
│   ├── DKI.py              # 领域知识注入
│   └── PEQA.py             # 提示增强问答
├── agents/                  # 领域专家 Agent
│   ├── geologist.py        # 地质学家 Agent
│   ├── geographer.py       # 地理学家 Agent
│   └── seismologist.py     # 地震学家 Agent
├── tool_pool/              # 工具池
│   ├── map_component_detector.py   # 地图组件检测
│   ├── map_legend_detector.py      # 图例检测
│   ├── rock_type_and_age_db.py     # 岩石类型和时代数据库
│   ├── k2_knowledge_db.py          # 知识库
│   ├── active_fault_db.py          # 活动断裂数据库
│   └── history_earthquake_db.py    # 历史地震数据库
├── utils/                  # 工具函数
│   ├── api.py              # API 客户端（已适配本地配置）
│   ├── vision.py           # 视觉处理函数
│   ├── prompt.py           # Prompt 模板
│   └── common.py           # 通用工具函数
└── dependencies/           # 依赖资源
    ├── models/             # YOLOv10 检测模型权重
    └── knowledge/          # 知识库数据
```

## 配置文件

### 模型权重配置

PEACE 使用 YOLOv10 模型进行地图组件和图例检测。模型权重位于：

```
PEACE/dependencies/models/
├── det_component/weights/best.pt    # 地图组件检测模型
└── det_legend/weights/best.pt       # 图例检测模型
```

### 知识库数据

```
PEACE/dependencies/knowledge/
├── k2_rock_type.json         # 岩石类型知识库
├── k2_rock_age.json          # 地层时代知识库
├── k2_rock_detail.json       # 岩石详细描述
├── k2_usage.json             # 岩石用途知识
├── k2_expertise.json         # 专家经验知识
├── gem_active_faults_harmonized.geojson  # 活动断裂数据
└── earthquake_1970_4.5mag.csv            # 历史地震数据
```

## 输出示例

分析地质图后，返回的元数据结构：

```json
{
  "name": "sample",
  "size": {"width": 1920, "height": 1080},
  "regions": {
    "main_map": [[100, 100, 1500, 800]],
    "legend": [[1600, 100, 1900, 500]],
    "title": [[100, 20, 500, 80]],
    "scale": [[100, 900, 300, 950]]
  },
  "legend": [
    {
      "color": [255, 0, 0],
      "color_name": "Red",
      "color_hex": "#FF0000",
      "text": "第四系",
      "rock_type": "沉积岩",
      "rock_age": "第四纪",
      "area": 0.35
    }
  ],
  "information": {
    "title": "某区域地质图",
    "scale": [1, 100000],
    "longitude": ["109°40'E", "110°40'E"],
    "latitude": ["19°20'N", "20°00'N"]
  }
}
```

## 注意事项

1. **Google Earth Engine**: PEACE 模块中的 `utils/common.py` 包含 Earth Engine 初始化代码，如果不需要相关功能可以忽略。

2. **模型权重**: 确保 YOLOv10 模型权重文件存在于 `PEACE/dependencies/models/` 目录下。

3. **API 限流**: 使用 MLLM API 时注意 rate limit，代码中已包含自动重试逻辑。

4. **缓存机制**: PEACE 模块会自动缓存分析结果到 `.cache/` 目录，避免重复处理。

## 故障排除

### 问题：ImportError: No module named 'PEACE'

**解决**: PEACE 工具会自动将 `PEACE/` 目录添加到 Python 路径。如果仍有问题，检查路径配置：

```python
import sys
sys.path.append("./PEACE")
```

### 问题：API client not initialized

**解决**: 检查 `.env` 文件中的 API 配置是否正确：

```env
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=http://127.0.0.1:8045/v1
```

### 问题：模型权重文件未找到

**解决**: 检查模型文件是否存在：

```bash
ls PEACE/dependencies/models/det_component/weights/best.pt
ls PEACE/dependencies/models/det_legend/weights/best.pt
```
