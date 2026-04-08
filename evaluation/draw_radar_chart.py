"""
基于评测数据绘制雷达图
五个维度：Fact QA (F1), Extraction (P), Extraction (R), Extraction (F1), Reasoning (ROUGE-L)
三个模型：Base model, Base + metadata, Geo-MAG
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import rcParams

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei']  # 黑体
rcParams['axes.unicode_minus'] = False  # 负号正常显示

# =====================
# 数据准备
# =====================
# 五个维度（只用英文标签，避免字体冲突）
categories = ['Fact QA (F1)', 'Extraction (P)', 'Extraction (R)',
              'Extraction (F1)', 'Reasoning (ROUGE-L)']

# 三个模型的数据
data = {
    'Base Model (Qwen-3.5-Plus)': [0.308, 0.374, 0.361, 0.367, 0.259],
    'Base Model + Metadata': [0.798, 0.745, 0.724, 0.735, 0.418],
    'Geo-MAG (Ours)': [0.831, 0.831, 0.880, 0.855, 0.787]
}

# 颜色配置（对齐参考图风格）
colors = {
    'Base Model (Qwen-3.5-Plus)': '#1f77b4',  # 蓝色
    'Base Model + Metadata': '#ff7f0e',       # 橙色
    'Geo-MAG (Ours)': '#d62728'               # 红色
}

fill_alphas = {
    'Base Model (Qwen-3.5-Plus)': 0.0,  # 不填充
    'Base Model + Metadata': 0.12,      # 浅填充
    'Geo-MAG (Ours)': 0.12              # 浅填充
}

# =====================
# 雷达图绘制
# =====================
num_vars = len(categories)
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]  # 闭合

fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(polar=True))

# 绘制每个模型
for model_name, values in data.items():
    values = values + values[:1]  # 闭合
    ax.plot(angles, values, color=colors[model_name],
            linewidth=3.5, label=model_name, linestyle='-')
    ax.fill(angles, values, color=colors[model_name], alpha=fill_alphas[model_name])

# 设置标签
ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)

# 设置角度标签（维度名称）- 单独设置字体
ax.set_thetagrids(np.degrees(angles[:-1]), categories)
for label in ax.get_xticklabels():
    label.set_fontsize(16)
    label.set_fontname('Times New Roman')

# 设置径向标签（刻度值）- 单独设置字体
ax.set_ylim(0, 1.0)
ax.set_yticks(np.arange(0.2, 1.01, 0.2))
ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'])
for label in ax.get_yticklabels():
    label.set_fontsize(16)
    label.set_fontname('Times New Roman')

# 添加网格 - 加粗
ax.grid(True, linestyle='--', color='gray', alpha=0.6, linewidth=2.0)

# 图例 - 字体大小 13px，新罗马体
handles, labels = ax.get_legend_handles_labels()
legend = ax.legend(handles, labels, loc='lower right',
                   bbox_to_anchor=(1.15, 0.1), fontsize=13,
                   framealpha=0.9, prop={'family': 'Times New Roman', 'size': 16})
legend.get_frame().set_edgecolor('lightgray')
legend.get_frame().set_linewidth(1.5)

# 调整布局
plt.tight_layout()

# 保存图片
output_path = 'data/evaluation_radar_chart_v2.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"雷达图已保存：{output_path}")

plt.show()
