"""
Geological Map Recognition Agent - Streamlit Frontend (Enhanced)
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import nest_asyncio
import streamlit as st
from PIL import Image

# Allow nested event loops in Streamlit (async agent + Streamlit runtime)
nest_asyncio.apply()

# Resolve project root and import backend modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from agent.agent import create_agent  # noqa: E402
from agent.config import AgentConfig  # noqa: E402
from agent.tools.kg_tool import kg_query_with_graph  # noqa: E402

# Paths & constants
LOGS_DIR = PROJECT_ROOT / "logs"
SESSION_MESSAGES_FILE = LOGS_DIR / "frontend_session_messages.json"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
DATASET_DIR = PROJECT_ROOT / "data" / "chuankou_maps"

ANALYSIS_PRESETS: List[Dict[str, str]] = [
    {
        "key": "legend",
        "label": "图例/基础解读",
        "instruction": "1) 调用 peace_map_analyze(query='legend') 和 peace_map_analyze(query='layout')，梳理图例、岩性、构造编号，输出结构化要素清单。",
    },
    {
        "key": "fault_mineral",
        "label": "断层 - 矿点关系",
        "instruction": "2) 使用 vision_analyze + calculate_spatial_relationships 量化最近的断层与矿点距离，并给出空间解释。",
    },
    {
        "key": "kg_verify",
        "label": "知识图谱交叉验证",
        "instruction": "3) 针对识别出的断层/矿点编号，调用 kg_query 或 kg_community_summary；若无结果需说明“知识库未命中”。",
    },
    {
        "key": "web_update",
        "label": "最新研究检索",
        "instruction": "4) 结合 web_search 获取近年公开研究或勘查进展，并引用信息来源。",
    },
]


@st.cache_data(show_spinner=False)
def list_map_samples() -> List[Dict[str, str]]:
    """Return available geological map metadata from data/chuankou_maps."""
    samples: List[Dict[str, str]] = []
    if not DATASET_DIR.exists():
        return samples

    supported_ext = (".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG")
    for file in sorted(DATASET_DIR.glob("*")):
        if file.suffix not in supported_ext:
            continue
        stat = file.stat()
        samples.append(
            {
                "title": file.stem,
                "path": str(file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "size_mb": round(stat.st_size / (1024 * 1024), 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
            }
        )
    return samples


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_text_content(value: Any) -> str:
    """Convert agent/LLM return objects into plain text for chat display/storage."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "response"):
        nested = getattr(value, "response")
        if isinstance(nested, str):
            return nested
    if hasattr(value, "content"):
        nested = getattr(value, "content")
        if isinstance(nested, str):
            return nested
    return str(value)


def make_json_safe(value: Any) -> Any:
    """Recursively convert runtime objects into JSON-serializable values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return make_json_safe(value.model_dump())
        except Exception:
            return str(value)
    if hasattr(value, "dict"):
        try:
            return make_json_safe(value.dict())
        except Exception:
            return str(value)
    if hasattr(value, "__dict__"):
        try:
            return make_json_safe(vars(value))
        except Exception:
            return str(value)
    return str(value)


def format_message_timestamp() -> str:
    """Format current timestamp for display in chat messages."""
    return datetime.now().strftime("%Y/%m/%d %H:%M")


def render_kg_graph(graph_data: dict) -> None:
    """
    Render knowledge graph visualization using AntV G6.

    Args:
        graph_data: dict with 'nodes' and 'edges' arrays
    """
    if not graph_data.get("nodes") or not graph_data.get("edges"):
        return

    # Node color mapping by type
    type_colors = {
        "Mineral": "#ff6b6b",
        "Formation": "#4ecdc4",
        "Fault": "#45b7d1",
        "Rock": "#96ceb4",
        "Community": "#ffeaa7",
        "Entity": "#dfe6e9",
    }

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>知识图谱可视化</title>
    <script src="https://gw.alipayobjects.com/os/lib/antv/g6/4.8.24/dist/g6.min.js"></script>
    <style>
        #container {{
            width: 100%;
            height: 350px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="container"></div>
    <script>
        const data = {json.dumps(graph_data, ensure_ascii=False)};
        const typeColors = {json.dumps(type_colors)};

        data.nodes.forEach(node => {{
            node.color = typeColors[node.type] || '#95a5a6';
            node.size = 35;
        }});

        data.edges.forEach(edge => {{
            edge.type = 'line';
            edge.style = {{ stroke: '#bdc3c7', lineWidth: 2 }};
            edge.label = edge.type;
            edge.labelCfg = {{ style: {{ fontSize: 10, fill: '#7f8c8d' }} }};
        }});

        const graph = new G6.Graph({{
            container: 'container',
            width: document.getElementById('container').clientWidth,
            height: 350,
            modes: {{ default: ['drag-canvas', 'zoom-canvas', 'drag-node'] }},
            layout: {{
                type: 'force',
                preventOverlap: true,
                linkDistance: 100,
                nodeStrength: -50,
                edgeStrength: 0.3,
            }},
            defaultNode: {{
                type: 'circle',
                style: {{ lineWidth: 2, stroke: '#2c3e50' }},
            }},
            defaultEdge: {{
                type: 'line',
                style: {{ stroke: '#bdc3c7', lineWidth: 1.5 }},
            }},
        }});

        graph.data(data);
        graph.render();
        graph.fitView();
    </script>
</body>
</html>
"""
    st.components.v1.html(html_content, height=380, scrolling=False)


def get_serializable_messages() -> List[dict]:
    """Return a JSON-safe snapshot of current messages."""
    raw_messages = st.session_state.get("messages", [])
    safe_messages = make_json_safe(raw_messages)
    return safe_messages if isinstance(safe_messages, list) else []


def load_messages_from_disk() -> List[dict]:
    if not SESSION_MESSAGES_FILE.exists():
        return []
    try:
        with SESSION_MESSAGES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def persist_messages_to_disk():
    ensure_directory(LOGS_DIR)
    with SESSION_MESSAGES_FILE.open("w", encoding="utf-8") as f:
        json.dump(get_serializable_messages(), f, ensure_ascii=False, indent=2)


def resolve_media_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def export_messages_bytes() -> bytes:
    return json.dumps(get_serializable_messages(), ensure_ascii=False, indent=2).encode("utf-8")


def clear_conversation_state():
    st.session_state.messages = []
    st.session_state.last_upload_sig = None
    persist_messages_to_disk()


def get_last_image_message():
    for message in reversed(st.session_state.messages):
        if message.get("type") == "image":
            return message
    return None


def build_structured_prompt(sample: Dict[str, str], selected_steps: List[str], notes: str) -> str:
    """Build a guided instruction string from sidebar selections."""
    if not selected_steps:
        selected_steps = [preset["key"] for preset in ANALYSIS_PRESETS]

    instructions_lookup = {preset["key"]: preset["instruction"] for preset in ANALYSIS_PRESETS}
    ordered_instructions = [
        instructions_lookup[key]
        for key in selected_steps
        if key in instructions_lookup
    ]

    body = "\n".join(ordered_instructions)
    extra = notes.strip()
    prompt = (
        f"针对地质图 `{sample['path']}`（约 {sample['size_mb']} MB，更新于 {sample['modified']}），"
        "请作为多模态地质识图智能体执行以下分析流程：\n"
        f"{body}\n"
        '输出需按"图像证据 / 知识图谱证据 / 综合判断"三段格式，总结关键依据并引用工具结果。'
    )
    if extra:
        prompt += f"\n补充要求：{extra}"
    return prompt


# ---------------------------------------------------------------------------
# Streamlit page configuration & global state
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Geological AI Assistant",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_file = Path(__file__).with_name("style.css")
if css_file.exists():
    with css_file.open("r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = create_agent(verbose=True)

if "messages" not in st.session_state:
    st.session_state.messages = load_messages_from_disk()
if "last_upload_sig" not in st.session_state:
    st.session_state.last_upload_sig = None

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
map_samples = list_map_samples()

with st.sidebar:
    st.title("地质图分析系统")
    st.caption("基于知识图谱与多模态大模型的地质图智能分析")

    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("地质图样本", len(map_samples))
    model_name = AgentConfig.OPENAI_MODEL_NAME or "未配置"
    metric_col2.metric("模型", model_name)

    st.caption("工具链：PEACE 地图分析 · 视觉识别 · Neo4j 知识图谱 · 网络检索")

    action_col1, action_col2 = st.columns(2)
    if action_col1.button("清空会话", use_container_width=True):
        clear_conversation_state()
        st.rerun()
    if st.session_state.messages:
        action_col2.download_button(
            "导出对话",
            data=export_messages_bytes(),
            file_name=f"geo-agent-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        action_col2.button("导出对话", disabled=True, use_container_width=True)

    uploaded_file = st.file_uploader(
        "上传地质图",
        type=["jpg", "jpeg", "png"],
        key="chat_uploader",
        help="上传后会自动加入当前会话。",
    )

    last_img_msg = get_last_image_message()
    if last_img_msg:
        st.markdown("**最近上传的地质图**")
        try:
            img_path = resolve_media_path(last_img_msg["path"])
            with Image.open(img_path) as preview_img:
                preview_img.thumbnail((280, 280))
                st.image(preview_img, caption=os.path.basename(last_img_msg["path"]))
        except Exception:
            st.code(last_img_msg.get("path"))

    with st.expander("可用地质图样本", expanded=False):
        if not map_samples:
            st.info("data/chuankou_maps 目录下暂无样本。")
        else:
            for sample in map_samples[:6]:
                st.write(f"- `{sample['title']}` · {sample['size_mb']} MB · {sample['modified']}")

    if map_samples:
        with st.expander("分析任务配置", expanded=not st.session_state.messages):
            default_steps = [preset["key"] for preset in ANALYSIS_PRESETS[:3]]
            with st.form("task_builder", clear_on_submit=True):
                selected_sample = st.selectbox(
                    "选择地质图样本",
                    map_samples,
                    format_func=lambda item: f"{item['title']} · {item['size_mb']} MB",
                )
                selected_steps = st.multiselect(
                    "选择分析流程",
                    options=[preset["key"] for preset in ANALYSIS_PRESETS],
                    default=default_steps,
                    format_func=lambda key: next(
                        (preset["label"] for preset in ANALYSIS_PRESETS if preset["key"] == key), key
                    ),
                )
                custom_notes = st.text_area("补充约束（选填）", placeholder="例如：重点关注 F1 断层附近的矿点。")
                submitted = st.form_submit_button("生成分析指令", use_container_width=True)
                if submitted and selected_sample:
                    structured_prompt = build_structured_prompt(selected_sample, selected_steps, custom_notes)
                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "type": "text",
                            "content": structured_prompt,
                            "timestamp": format_message_timestamp(),
                            "meta": {
                                "source": "task_builder",
                                "map_path": selected_sample["path"],
                                "steps": selected_steps,
                            },
                        }
                    )
                    persist_messages_to_disk()
                    st.success("已将结构化指令加入对话。")
                    st.rerun()
    else:
        st.warning("未检测到任何地质图样本，请将图像放入 data/chuankou_maps。")


# ---------------------------------------------------------------------------
# File upload handling
# ---------------------------------------------------------------------------
def handle_file_upload(uploaded_file):
    if uploaded_file is None:
        return False

    upload_sig = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.last_upload_sig == upload_sig:
        return False

    ensure_directory(UPLOAD_DIR)
    base_name, ext = os.path.splitext(uploaded_file.name)
    ext = ext or ".jpg"
    # 直接使用原文件名，不加 UUID 后缀，以便缓存命中
    unique_name = f"{base_name}{ext}"
    save_path = UPLOAD_DIR / unique_name

    # 如果文件已存在，检查大小是否相同
    if save_path.exists():
        if save_path.stat().st_size == uploaded_file.size:
            # 文件相同，直接复用
            relative_path = str(save_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            return True
        else:
            # 文件不同，覆盖保存
            pass

    with save_path.open("wb") as f:
        f.write(uploaded_file.getbuffer())

    relative_path = str(save_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if not any(msg.get("type") == "image" and msg.get("path") == relative_path for msg in st.session_state.messages):
        st.session_state.messages.append(
            {
                "role": "user",
                "type": "image",
                "path": relative_path,
                "content": f"已上传地质图附件：`{relative_path}`，请结合该图进行分析。",
                "timestamp": format_message_timestamp(),
            }
        )
        persist_messages_to_disk()

    st.session_state.last_upload_sig = upload_sig
    return True


# ---------------------------------------------------------------------------
# Main layout + chat area
# ---------------------------------------------------------------------------
USER_AVATAR = "👤"
AGENT_AVATAR = "🗺️"

# Welcome / empty state
if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome-container">
            <h1 class="welcome-title">地质图谱智能分析系统</h1>
            <p class="welcome-subtitle">
                基于知识图谱与多模态大模型的地质图智能分析系统，支持空间特征识别、
                知识图谱交叉验证与找矿预测推理。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

if handle_file_upload(uploaded_file):
    st.success("图片上传成功！已加入对话。")
    st.rerun()

# Display chat history with avatar timestamps
for msg in st.session_state.messages:
    timestamp = msg.get("timestamp", "")
    avatar = USER_AVATAR if msg["role"] == "user" else AGENT_AVATAR

    # Create avatar with timestamp overlay using HTML
    avatar_html = f"""<div class="chat-avatar-with-time">
        <div class="chat-avatar-emoji">{avatar}</div>
        <div class="chat-avatar-timestamp">{timestamp}</div>
    </div>"""

    with st.chat_message(msg["role"]):
        # Display custom avatar with timestamp
        st.markdown(avatar_html, unsafe_allow_html=True)

        if msg.get("type") == "image":
            try:
                img_path = resolve_media_path(msg["path"])
                img = Image.open(img_path)
                st.image(img, width=300, caption="📎 附件图片")
            except Exception:
                st.markdown(f"📎 附件：`{msg['path']}`")
        else:
            if msg.get("meta", {}).get("source") == "task_builder":
                st.caption("🧱 由任务工坊生成的多步指令")
            st.markdown(ensure_text_content(msg.get("content")))

# Chat input
if prompt := st.chat_input("输入地质问题，或引用上传的图片路径..."):
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt, "timestamp": format_message_timestamp()})
    persist_messages_to_disk()
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AGENT_AVATAR):
        with st.status("正在执行分析流程...", expanded=True) as status:
            st.write("正在解析地质图要素...")
            try:
                full_prompt = prompt
                last_img_path = None
                for history_msg in reversed(st.session_state.messages):
                    if history_msg.get("type") == "image":
                        last_img_path = history_msg.get("path")
                        break

                if last_img_path and last_img_path not in prompt:
                    full_prompt = (
                        f"结合地质图 {last_img_path}：\n"
                        f"{prompt}\n\n"
                        "请严格按以下流程执行并在最终回答中给出证据来源：\n"
                        "1) 必须先调用 peace_map_analyze 提取图例、构造、矿产相关元数据。\n"
                        "2) 对提取出的断层编号、矿点编号、岩性名称，必须调用 kg_query 或 kg_community_summary 检索知识图谱。\n"
                        "3) 若图中编号在知识图谱中不存在，明确写'知识库未命中'，禁止臆造。\n"
                        "4) 最终报告按'图像证据 / 知识图谱证据 / 综合结论'三段输出。\n"
                    )

                async def _run_agent_once(user_msg: str):
                    # 增加 max_iterations 防止复杂任务提前终止
                    return await st.session_state.agent.run(user_msg=user_msg, max_iterations=30)

                response = asyncio.run(_run_agent_once(full_prompt))
                status.update(label="分析已完成", state="complete", expanded=False)
            except Exception as e:
                error_msg = f"发生错误：{str(e)}"
                st.error(error_msg)
                status.update(label="分析过程中出现错误", state="error", expanded=True)
                response = None
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": error_msg})
                persist_messages_to_disk()

        if response:
            response_text = ensure_text_content(response)
            st.markdown(response_text)

            # 检测是否是地质报告相关问题，如果是则显示知识图谱可视化
            kg_keywords = ["地质报告", "知识图谱", "断层", "矿点", "岩层", "地层", "矿床", "成矿", "构造"]
            is_geo_report_query = any(kw in prompt for kw in kg_keywords)

            if is_geo_report_query:
                with st.spinner("正在加载知识图谱..."):
                    try:
                        # 从 prompt 中提取查询关键词
                        graph_data = kg_query_with_graph(prompt[:50], limit=15)
                        if graph_data.get("nodes") and graph_data.get("edges"):
                            st.markdown("### 📊 知识图谱可视化")
                            render_kg_graph(graph_data)
                            with st.expander("查看图谱数据"):
                                st.json(graph_data)
                        else:
                            st.info("暂无可用的知识图谱数据")
                    except Exception as e:
                        st.warning(f"知识图谱加载失败：{str(e)}")

            st.session_state.messages.append({"role": "assistant", "type": "text", "content": response_text, "timestamp": format_message_timestamp()})
            persist_messages_to_disk()
