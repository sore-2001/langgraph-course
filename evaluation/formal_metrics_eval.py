"""
川口矿区地质图理解评测 - 正式指标计算

基于论文 4.3.2 节定义的评估指标：
- 事实问答（Fact QA）：F1 值
- 结构化抽取：Precision、Recall、F1 值
- 解释性推理：ROUGE-L
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Set
import re

# 评测关键信息点（标准答案）
GOLD_ANSWERS = {
    "stratigraphy": {
        "entities": [  # 事实问答实体
            "寒武系 - 志留系板岩群", "灰绿色绢云母板岩", "千枚岩", "粉砂质板岩",
            "中侏罗世", "J₂", "165-155Ma", "白云母花岗岩", "二云母花岗岩",
            "接触带外 0-300m", "ZK1202", "16 层", "46.30m", "0.860%",
            "上脉下体", "石英脉型", "蚀变岩体型", "热液分带"
        ],
        "structured": {  # 结构化抽取要素
            "formations": ["寒武系 - 志留系板岩群", "灰绿色绢云母板岩", "千枚岩", "粉砂质板岩"],
            "intrusions": ["中侏罗世花岗岩", "白云母花岗岩", "二云母花岗岩", "165-155Ma"],
            "mineralization_zones": ["接触带外 0-300m", "石英脉型", "岩体型"],
            "drilling_data": ["ZK1202", "16 层", "46.30m", "0.860%"]
        },
        "reasoning_points": [  # 推理要点（用于 ROUGE-L）
            "矿体主要赋存于接触带外 0-300m 板岩中",
            "进入板岩后脉体变薄尖灭",
            "岩体顶部为石英脉型，深部为蚀变岩体型",
            "反映热液分带",
            "成矿滞后岩浆侵入 5-15Ma"
        ]
    },
    "tectonics": {
        "entities": [
            "北西向", "常德 - 宁乡 - 汝城断裂带", "310-330°", "55-70°", "12km",
            "北东向", "攸县 - 宁远断裂带", "45-60°", "60-80°",
            "40-70°", "30-50°夹角", "15 条", "12 条",
            "ZK0801", "10 层", "10m", "1.693%",
            "ZK1202", "46.30m", "层间破碎带"
        ],
        "structured": {
            "faults": ["常德 - 宁乡 - 汝城断裂带", "攸县 - 宁远断裂带"],
            "fault_strikes": ["310-330°", "45-60°"],
            "vein_strikes": ["40-70°"],
            "angles": ["30-50°夹角"],
            "vein_counts": ["15 条", "12 条"],
            "drilling_data": ["ZK0801", "10 层", "1.693%", "ZK1202", "46.30m"]
        },
        "reasoning_points": [
            "断裂交汇部位虚脱空间是矿脉定位的有利部位",
            "派生出北东向次级断裂和裂隙系统",
            "含矿热液沿充填形成石英脉",
            "北西向与北东向深大断裂交汇为岩浆侵位提供构造空间"
        ]
    },
    "magmatism": {
        "entities": [
            "165-155Ma", "中侏罗世", "150-140Ma", "5-15Ma", "岩浆期后热液",
            "石英脉型", "岩体型", "0-300m", "ZK0801", "10 层",
            "ZK1202", "46.30m", "云英岩化", "钾长石化", "硅化绢云母化",
            "岩浆分异", "充填交代"
        ],
        "structured": {
            "ages": ["165-155Ma", "150-140Ma", "5-15Ma"],
            "types": ["石英脉型", "岩体型", "岩浆期后热液"],
            "zones": ["0-300m", "云英岩化带"],
            "alterations": ["云英岩化", "钾长石化", "硅化绢云母化"]
        },
        "reasoning_points": [
            "成矿滞后岩浆侵入 5-15Ma，属岩浆期后热液矿床",
            "石英脉型分布于岩体顶部及外接触带 0-300m",
            "岩体型发育于白云母花岗岩的云英岩化带内",
            "岩浆分异含 W 挥发分，沿裂隙充填交代成矿"
        ]
    },
    "metallogeny": {
        "entities": [
            "寒武系 - 志留系板岩", "容矿", "深大断裂交汇", "导矿",
            "中侏罗世花岗岩", "供矿", "燕山早期", "170-150Ma",
            "石英大脉型", "蚀变岩体型", "上脉下体",
            "断裂下盘 100-300m", "云英岩化", "分支复合带"
        ],
        "structured": {
            "conditions": ["板岩容矿", "断裂导矿", "花岗岩供矿"],
            "model": ["燕山早期", "170-150Ma", "断裂活动", "岩浆侵位", "热液成矿"],
            "zones": ["石英大脉型", "蚀变岩体型"],
            "targets": ["断裂下盘 100-300m", "云英岩化", "分支复合带"]
        },
        "reasoning_points": [
            "成矿条件：寒武系 - 志留系板岩（容矿）、深大断裂交汇（导矿）、中侏罗世花岗岩（供矿）",
            "成矿模式：燕山早期 (170-150Ma) 断裂活动→岩浆侵位→热液成矿",
            "空间分带：接触带向外，石英大脉型→蚀变岩体型→弱矿化板岩",
            "找矿方向：断裂下盘 100-300m、云英岩化强烈部位、脉体分支复合带"
        ]
    }
}


def extract_entities(text: str) -> Set[str]:
    """从文本中提取地质实体（简化版，基于关键词匹配）"""
    # 实际应用中应使用 NER 模型
    return set()


def calculate_f1(pred_entities: Set[str], gold_entities: Set[str]) -> float:
    """计算事实问答 F1 值"""
    if not pred_entities or not gold_entities:
        return 0.0

    intersection = pred_entities & gold_entities
    precision = len(intersection) / len(pred_entities) if pred_entities else 0
    recall = len(intersection) / len(gold_entities) if gold_entities else 0

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return round(f1, 4)


def calculate_structured_metrics(pred_structured: Dict[str, List[str]],
                                  gold_structured: Dict[str, List[str]]) -> Dict[str, float]:
    """计算结构化抽取指标"""
    all_pred = []
    all_gold = []

    for category in gold_structured.keys():
        pred_items = set(pred_structured.get(category, []))
        gold_items = set(gold_structured[category])
        all_pred.extend(pred_items)
        all_gold.extend(gold_items)

    pred_set = set(all_pred)
    gold_set = set(all_gold)
    intersection = pred_set & gold_set

    precision = len(intersection) / len(pred_set) if pred_set else 0
    recall = len(intersection) / len(gold_set) if gold_set else 0

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1": round(f1, 4)
    }


def calculate_rouge_l(pred_text: str, gold_texts: List[str]) -> float:
    """计算 ROUGE-L 分数"""
    def lcs_length(s1: str, s2: str) -> int:
        """计算最长公共子序列长度"""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        return dp[m][n]

    # 取最长的 gold 文本作为参考
    max_lcs = 0
    max_gold_len = 0

    for gold_text in gold_texts:
        lcs = lcs_length(pred_text, gold_text)
        if lcs > max_lcs:
            max_lcs = lcs
            max_gold_len = len(gold_text)

    if max_gold_len == 0:
        return 0.0

    rouge_l = max_lcs / max_gold_len
    return round(rouge_l, 4)


def score_with_formal_metrics(answer: str, key_points: Dict) -> Dict[str, float]:
    """使用论文定义的正式指标评分"""
    scores = {}

    # 1. 事实问答 F1（基于关键词匹配）
    gold_entities = set(key_points.get("entities", []))
    # 简化的实体提取：检查答案中是否包含关键实体
    matched_entities = {e for e in gold_entities if e in answer}
    pred_entities = matched_entities  # 简化处理

    scores["事实问答_F1"] = calculate_f1(pred_entities, gold_entities)

    # 2. 结构化抽取指标
    gold_structured = key_points.get("structured", {})
    pred_structured = {}
    for category, items in gold_structured.items():
        matched = [item for item in items if item in answer]
        pred_structured[category] = matched

    structured_metrics = calculate_structured_metrics(pred_structured, gold_structured)
    scores["结构化抽取_Precision"] = structured_metrics["Precision"]
    scores["结构化抽取_Recall"] = structured_metrics["Recall"]
    scores["结构化抽取_F1"] = structured_metrics["F1"]

    # 3. 解释性推理 ROUGE-L
    gold_reasoning = key_points.get("reasoning_points", [])
    scores["解释性推理_ROUGE-L"] = calculate_rouge_l(answer, gold_reasoning)

    return scores


def run_formal_evaluation():
    """运行正式指标评估"""
    # 加载已有实验结果
    results_file = "data/evaluation_results_20260404_182228.json"
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    formal_results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": results["metadata"]["model"],
            "evaluation_metrics": ["F1 (Fact QA)", "Precision/Recall/F1 (Structured)", "ROUGE-L (Reasoning)"]
        },
        "zero_shot": {},
        "rag_enhanced": {},
        "comparison": {}
    }

    print("=" * 80)
    print("川口矿区地质图理解评测 - 正式指标计算")
    print("=" * 80)

    for dim_id in ["stratigraphy", "tectonics", "magmatism", "metallogeny"]:
        dim_name = {"stratigraphy": "地层", "tectonics": "构造",
                    "magmatism": "岩浆岩", "metallogeny": "成矿系统"}[dim_id]

        print(f"\n{'='*60}")
        print(f"评测维度：{dim_name}")
        print("="*60)

        gold_points = GOLD_ANSWERS[dim_id]

        # 零样本评估
        if dim_id in results["zero_shot"]:
            zero_answer = results["zero_shot"][dim_id]["answer"]
            zero_scores = score_with_formal_metrics(zero_answer, gold_points)
            formal_results["zero_shot"][dim_id] = zero_scores

            print(f"\n[零样本]")
            print(f"  事实问答 F1:        {zero_scores['事实问答_F1']:.4f}")
            print(f"  结构化抽取 Precision: {zero_scores['结构化抽取_Precision']:.4f}")
            print(f"  结构化抽取 Recall:    {zero_scores['结构化抽取_Recall']:.4f}")
            print(f"  结构化抽取 F1:      {zero_scores['结构化抽取_F1']:.4f}")
            print(f"  解释性推理 ROUGE-L: {zero_scores['解释性推理_ROUGE-L']:.4f}")

        # 检索增强评估
        if dim_id in results["rag_enhanced"]:
            rag_answer = results["rag_enhanced"][dim_id]["answer"]
            rag_scores = score_with_formal_metrics(rag_answer, gold_points)
            formal_results["rag_enhanced"][dim_id] = rag_scores

            print(f"\n[检索增强]")
            print(f"  事实问答 F1:        {rag_scores['事实问答_F1']:.4f}")
            print(f"  结构化抽取 Precision: {rag_scores['结构化抽取_Precision']:.4f}")
            print(f"  结构化抽取 Recall:    {rag_scores['结构化抽取_Recall']:.4f}")
            print(f"  结构化抽取 F1:      {rag_scores['结构化抽取_F1']:.4f}")
            print(f"  解释性推理 ROUGE-L: {rag_scores['解释性推理_ROUGE-L']:.4f}")

        # 对比分析
        if dim_id in results["zero_shot"] and dim_id in results["rag_enhanced"]:
            comparison = {}
            for metric in zero_scores.keys():
                zero_val = zero_scores[metric]
                rag_val = rag_scores[metric]
                improvement = rag_val - zero_val
                rate = (improvement / zero_val * 100) if zero_val > 0 else 0
                comparison[metric] = {
                    "zero_shot": zero_val,
                    "rag": rag_val,
                    "improvement": round(improvement, 4),
                    "improvement_rate": round(rate, 1)
                }
            formal_results["comparison"][dim_id] = comparison

            print(f"\n[提升幅度]")
            for metric, comp in comparison.items():
                print(f"  {metric}: {comp['zero_shot']:.4f} → {comp['rag']:.4f} "
                      f"(+{comp['improvement_rate']:.1f}%)")

    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"data/formal_evaluation_results_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formal_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"评测完成！结果已保存至：{output_file}")
    print("="*60)

    # 生成汇总表格
    generate_summary_table(formal_results)

    return formal_results


def generate_summary_table(formal_results: Dict):
    """生成汇总表格"""
    print("\n" + "=" * 90)
    print("评测结果汇总表")
    print("=" * 90)

    # 表头
    print(f"{'维度':<10} {'任务类型':<12} {'指标':<20} {'零样本':<10} {'检索增强':<10} {'提升率':<10}")
    print("-" * 90)

    dim_names = {"stratigraphy": "地层", "tectonics": "构造",
                 "magmatism": "岩浆岩", "metallogeny": "成矿系统"}

    metric_names = {
        "事实问答_F1": "F1",
        "结构化抽取_Precision": "Precision",
        "结构化抽取_Recall": "Recall",
        "结构化抽取_F1": "F1",
        "解释性推理_ROUGE-L": "ROUGE-L"
    }

    task_types = {
        "事实问答_F1": "事实问答",
        "结构化抽取_Precision": "结构化抽取",
        "结构化抽取_Recall": "结构化抽取",
        "结构化抽取_F1": "结构化抽取",
        "解释性推理_ROUGE-L": "解释性推理"
    }

    for dim_id, comp in formal_results["comparison"].items():
        dim_name = dim_names.get(dim_id, dim_id)
        first = True
        for metric, data in comp.items():
            metric_display = metric_names.get(metric, metric)
            task_display = task_types.get(metric, "")

            if first:
                print(f"{dim_name:<10} {task_display:<12} {metric_display:<20} "
                      f"{data['zero_shot']:<10.4f} {data['rag']:<10.4f} "
                      f"+{data['improvement_rate']:<9.1f}%")
                first = False
            else:
                print(f"{'':<10} {task_display:<12} {metric_display:<20} "
                      f"{data['zero_shot']:<10.4f} {data['rag']:<10.4f} "
                      f"+{data['improvement_rate']:<9.1f}%")

    print("=" * 90)


if __name__ == "__main__":
    run_formal_evaluation()
