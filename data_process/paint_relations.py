# -*- coding: utf-8 -*-
"""
知识图谱关系类型数量统计图（论文级高级配色版）
适配地质类大论文，参考示例图多彩渐变风格，数据更新+配色优化
"""
import matplotlib.pyplot as plt
import numpy as np

# ===================== 基础配置（论文标准） =====================
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 适配中文
plt.rcParams['axes.unicode_minus'] = False                      # 解决负号显示
plt.rcParams['figure.dpi'] = 300                                # 高清输出
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['axes.spines.top'] = False                         # 隐藏顶部边框
plt.rcParams['axes.spines.right'] = False                       # 隐藏右侧边框

# ===================== 最新数据 =====================
relations = [
    ("包含", 887),
    ("位置", 308),
    ("形成于", 294),
    ("主要矿物为", 271),
    ("围岩蚀变为", 205),
    ("产状为", 189),
    ("为", 186),
    ("分布于", 176),
    ("矿化显示", 172),
    ("规模", 166),
    ("走向", 149),
    ("分别为", 139),
    ("赋存于", 105),
    ("矿体为", 102),
    ("出露", 92),
    ("主要元素为", 79),
    ("成矿阶段为", 73),
    ("倾向", 71),
    ("矿为", 65),
]

labels = [r[0] for r in relations]
values = [r[1] for r in relations]

# ===================== 高级配色（莫兰迪+渐变，贴合地质学术风格） =====================
# 定制渐变色系，避免花哨，兼顾辨识度和高级感
colors = [
    '#E63946', '#F77F00', '#FCBF49', '#E9C46A', '#43AA8B', 
    '#577590', '#277DA1', '#4D908E', '#F9844A', '#90BE6D',
    '#F8961E', '#97266D', '#800020', '#8B4513', '#2F4F4F',
    '#6A0572', '#AB83A1', '#FFBA08', '#3F37C9'
]

# ===================== 绘图布局（适配论文宽度） =====================
fig, ax = plt.subplots(figsize=(12, 8))  # 比例适配论文排版

# 绘制柱状图（保留示例图的柱形质感）
bars = ax.bar(
    labels, values, 
    color=colors,        # 高级渐变配色
    edgecolor='white',   # 白色描边增强层次感
    linewidth=0.8,       # 描边宽度
    width=0.75           # 柱宽适配示例图风格
)

# ===================== 标签与标题（论文规范） =====================
ax.set_xlabel('关系类别', fontsize=13, fontweight='normal', labelpad=10)
ax.set_ylabel('三元组个数', fontsize=10, fontweight='normal', labelpad=10)
ax.set_title('知识图谱关系类型数量统计', fontsize=15, fontweight='normal', pad=15)

# X轴标签旋转（避免重叠，适配长标签）
plt.xticks(rotation=45, ha='right', fontsize=11)
plt.yticks(fontsize=11)

# ===================== 柱子顶部数值标注（示例图风格） =====================
for bar, val in zip(bars, values):
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width()/2,
        height + 12,  # 数值与柱子间距
        f'{val}',
        ha='center', va='bottom',
        fontsize=10, fontweight='normal',
        color='black'  # 数值颜色统一为黑色，增强可读性
    )

# ===================== 轴域优化（贴合示例图视觉） =====================
ax.set_ylim(0, max(values) * 1.15)  # Y轴范围预留数值空间
ax.set_xlim(-0.5, len(labels)-0.5)  # 去掉左右冗余空白
ax.yaxis.grid(True, linestyle='--', alpha=0.3)  # 浅色网格线，不干扰主体
ax.set_axisbelow(True)  # 网格线置于柱子下层

# ===================== 紧凑布局+保存（无冗余白边） =====================
plt.tight_layout()
output_path = r'd:\项目数据\毕业流程\大论文\langgraph-course\data_process\relation_statistics_advanced.png'
plt.savefig(output_path, bbox_inches='tight', pad_inches=0.08)
print(f"高级配色版图表已保存至：{output_path}")

# 显示图表
plt.show()