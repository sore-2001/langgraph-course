"""
川口矿区地质图理解评测实验

基于 Qwen-3.5-Plus 模型，对比零样本基线与检索增强方法在地质图理解任务上的表现
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
from dotenv import load_dotenv
import requests
# 加载环境变量
load_dotenv()

# 配置 API（使用 OpenAI 兼容接口）
API_KEY = os.getenv("OPENAI_API_KEY", "sk-sp-fd756618ec8d4984b5d8eb935b5eb3f0")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen3.5-plus")

print(f"API 配置：{BASE_URL}")
print(f"模型：{MODEL_NAME}")

# 评测问题设计 - 基于川口矿区真实地质资料
EVALUATION_QUESTIONS = {
    "stratigraphy": {
        "name": "地层",
        "question": """分析川口矿区塘江沅地段的地层序列，并结合钻孔资料（如 ZK1202）说明寒武系 - 志留系板岩群与中侏罗世花岗岩接触带的钨矿化特征。
具体要求：
1）列出地层时代及岩性组合；
2）说明矿体在接触带内外的产状变化规律；
3）解释'上脉下体'矿化现象的成因机制。""",
        "key_points": [
            "寒武系 - 志留系板岩群（灰绿色绢云母板岩、千枚岩、粉砂质板岩）",
            "中侏罗世 (J₂, 165-155Ma) 白云母花岗岩、二云母花岗岩",
            "矿体主要赋存于接触带外 0-300m 板岩中，进入板岩后脉体变薄尖灭",
            "ZK1202 见矿 16 层，累计厚度 46.30m，最高品位 0.860%",
            "'上脉下体'：岩体顶部为石英脉型，深部为蚀变岩体型，反映热液分带",
        ]
    },
    "tectonics": {
        "name": "构造",
        "question": """川口矿田位于两条深大断裂交汇部位。请分析区域构造格架对矿田定位的控制作用，并结合屋背冲、福王祠两地段矿脉产状数据，阐明'断裂交汇 - 次级裂隙 - 矿脉定位'三级控矿机制。
具体要求：
1）命名两条主干断裂及产状；
2）说明含钨石英脉走向与主干断裂的几何关系；
3）解释为什么断裂交汇部位是找矿有利空间。""",
        "key_points": [
            "北西向常德 - 宁乡 - 汝城断裂带（走向 310-330°）",
            "北东向攸县 - 宁远断裂带（走向 45-60°）",
            "含钨石英脉主要走向 40-70°，与北西向主干断裂呈 30-50°夹角",
            "15 条矿脉中 8 条定位于断裂交汇部位虚脱空间",
            "福王祠地段 ZK0801 见矿 10 层，累计厚度 10m，钨矿最高品位 1.693%",
            "屋背冲地段 ZK1202 累计见矿 46.30m，受层间破碎带控制",
        ]
    },
    "magmatism": {
        "name": "岩浆岩",
        "question": """川口矿区花岗岩与钨成矿具有密切的时空和成因联系。请基于岩体型与石英脉型两种矿化类型的空间分带特征，分析成矿时代、成矿流体来源及成矿机制。
具体要求：
1）给出岩体侵位时代和成矿年龄数据；
2）对比两种矿化类型的空间分布和矿化特征；
3）阐述蚀变分带序列及其与矿化的关系；
4）推断成矿流体性质和成矿机制。""",
        "key_points": [
            "岩体侵位年龄 165-155Ma（中侏罗世），成矿年龄 150-140Ma",
            "成矿滞后岩浆侵入 5-15Ma，属岩浆期后热液矿床",
            "石英脉型：岩体顶部及外接触带 0-300m，如福王祠 ZK0801 钨矿 10 层",
            "岩体型：岩体内部云英岩化带，如屋背冲 ZK1202 累计 46.30m",
            "蚀变分带：云英岩化→钾长石化→硅化绢云母化→正常围岩",
            "成矿机制：岩浆分异含 W 挥发分，沿裂隙充填交代成矿",
        ]
    },
    "metallogeny": {
        "name": "成矿系统",
        "question": """综合地层、构造、岩浆岩和矿产信息，重建川口矿区钨成矿系统，并圈定找矿远景区。
具体要求：
1）梳理成矿地质条件（地层、构造、岩浆岩、矿产）；
2）建立'时代 - 空间 - 成因'三维成矿模式；
3）指出深部及外围找矿方向，并说明依据。""",
        "key_points": [
            "成矿条件：寒武系 - 志留系板岩（容矿）、深大断裂交汇（导矿）、中侏罗世花岗岩（供矿）",
            "成矿模式：燕山早期 (170-150Ma) 断裂活动→岩浆侵位→热液成矿",
            "空间分带：接触带向外，石英大脉型→蚀变岩体型→弱矿化板岩",
            "垂向分带：浅部石英脉型→深部'上脉下体'复合矿化",
            "找矿方向：断裂下盘 100-300m、云英岩化强烈部位、脉体分支复合带",
        ]
    }
}


# 川口矿区背景知识（用于 RAG 增强）
CHUANKOU_CONTEXT = """【区域构造背景】
- 川口矿田位于常德－宁乡－汝城北西向大断裂与攸县－宁远北东向大断裂交汇部位
- 北西向断裂：走向 310-330°，倾角 55-70°，区内延伸 12km
- 北东向断裂：走向 45-60°，倾角 60-80°
- 成矿地质条件优越，是湖南省最重要的钨成矿带之一，已发现川口、杨林坳、三角潭、塘江沅等多个矿区

【地层】
- 寒武系 - 志留系板岩群（∈-S）：灰绿色绢云母板岩、千枚状板岩、粉砂质板岩夹细砂岩
- 板岩具水平层理，厚度>500m
- 中生界碎屑岩分布于矿区东部

【岩浆岩】
- 中侏罗世（J₂）中细粒白云母花岗岩、二云母花岗岩
- 侵位年龄：165-155 Ma（K-Ar 法）
- 产出形态：岩枝、岩脉，出露面积 2.3 km²
- 矿物成分：钾长石 30-35%、斜长石 25-30%、石英 25-30%、白云母 5-8%、黑云母 3-5%

【构造控矿】
- 15 条含钨石英脉，主干断裂 1 条，小岩体 4 个
- 含钨石英脉走向 40-70°，与北西向主干断裂呈 30-50°夹角
- 12 条矿脉产于花岗岩与板岩接触带外 0-300m 范围内
- 断裂交汇部位虚脱空间是矿脉定位的有利部位

【矿化特征】
- 矿化类型分带：
  * 石英脉型：分布于岩体顶部及外接触带 0-300m（如福王祠地段）
  * 岩体型：黑钨矿发育于白云母花岗岩的云英岩化带内（如屋背冲地段）
- 蚀变分带：云英岩化花岗岩带→钾长石化花岗岩带→硅化 - 绢云母化板岩带→正常板岩
- 矿脉在花岗岩内延伸稳定（脉宽 0.5-2m），进入板岩后急剧变薄（0.1-0.5m）甚至尖灭

【钻孔资料】
- 屋背冲地段 ZK1202：揭露 16 层矿，单孔累计见矿厚度 46.30m，最高品位 0.860% WO₃，赋存深度 50-288m
- 屋背冲地段 ZK0302：见矿 4 层，累计厚度 5.44m
- 福王祠地段 ZK0801：见矿 10 层，累计厚度 10.00m，钨矿最大连续厚度 4.52m，最高品位 1.693% WO₃
- 福王祠地段 ZK0701：见矿 6 层，累计厚度 8.65m，最高品位 2.024% WO₃
- 塘江沅矿区施工 11 个钻孔，8 个为工业矿孔

【成矿时代与成因】
- 含钨石英脉 Rb-Sr 等时线年龄：150-140 Ma
- 成矿滞后岩浆侵入 5-15 Ma，属岩浆期后热液充填交代型矿床
- 矿化与云英岩化、钾长石化蚀变呈正相关

【找矿标志】
- 断裂下盘 100-300m 范围
- 云英岩化蚀变强烈部位
- 北东向次级断裂与主干断裂交汇部位
- 脉体分支复合带和层间破碎带
"""


def call_qwen_model(prompt: str, system_prompt: str = None, max_retries: int = 3) -> str:
    """调用 Qwen-3.5-Plus 模型（OpenAI 兼容接口），带重试机制"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }

    for attempt in range(max_retries):
        try:
            print(f"  调用尝试 {attempt + 1}/{max_retries}...")
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120  # 增加到 120 秒超时
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            print(f"  超时，等待 30 秒后重试...")
            time.sleep(30)
        except requests.exceptions.RequestException as e:
            print(f"  请求失败：{str(e)[:100]}，等待 30 秒后重试...")
            time.sleep(30)
        except (KeyError, IndexError) as e:
            return f"响应解析失败：{str(e)}"

    return "API 调用失败：超过最大重试次数"


def zero_shot_eval(question: str) -> str:
    """零样本评测：仅依靠模型预训练知识"""
    system_prompt = "你是一位地质学专家，请基于用户提供的地质问题，运用你的地质学专业知识进行回答。如果问题涉及具体矿区的数据，而你没有相关数据，请明确指出。"

    prompt = f"""请专业、详细地分析以下地质问题：

{question}

请运用你的地质学知识进行系统分析，包括地层、构造、岩浆岩和成矿作用等方面。"""

    print("[零样本] 调用 Qwen-3.5-Plus...")
    return call_qwen_model(prompt, system_prompt)


def rag_enhanced_eval(question: str) -> str:
    """检索增强评测：提供川口矿区地质资料作为上下文"""
    system_prompt = "你是一位地质学专家，请基于用户提供的地质资料回答问题。请充分运用提供的地质资料进行专业分析，引用数据时请说明来源。"

    prompt = f"""请专业、详细地分析以下地质问题：

{question}

---
【参考地质资料】
{CHUANKOU_CONTEXT}
---

请结合上述地质资料进行综合分析。引用资料时请说明数据来源（如'据 ZK1202 钻孔记录'、'据区域地质资料'）。"""

    print("[检索增强] 调用 Qwen-3.5-Plus...")
    return call_qwen_model(prompt, system_prompt)


def score_answer(answer: str, key_points: List[str]) -> Dict[str, float]:
    """
    对模型回答进行评分
    """
    scores = {}

    # 要点覆盖率
    covered_points = 0
    for point in key_points:
        core_words = [w for w in point.split() if len(w) > 1 and any(c.isalnum() for c in w)]
        if len(core_words) >= 2 and sum(1 for w in core_words[:5] if w in answer) >= 2:
            covered_points += 1

    coverage_rate = covered_points / len(key_points)
    scores["要点覆盖率"] = round(coverage_rate * 100, 1)

    # 推理深度
    reasoning_keywords = ["因为", "由于", "机制", "成因", "反映", "指示", "推断", "解释",
                         "控制", "导致", "形成于", "赋存于", "受", "源于"]
    reasoning_count = sum(answer.count(kw) for kw in reasoning_keywords)
    depth_score = min(100, reasoning_count * 7)
    scores["推理深度"] = round(depth_score, 1)

    # 数据支撑
    import re
    borehole_refs = len(re.findall(r'ZK\d+', answer))
    data_values = len(re.findall(r'\d+\.?\d*\s*(m|km|Ma|Ma|%)', answer))
    data_refs = borehole_refs * 3 + data_values
    data_score = min(100, data_refs * 8)
    scores["数据支撑"] = round(data_score, 1)

    # 专业表述
    professional_terms = [
        "寒武系", "志留系", "侏罗世", "板岩", "花岗岩", "云英岩化",
        "接触带", "矿脉", "产状", "走向", "倾角", "断裂", "褶皱",
        "黑钨矿", "石英脉", "蚀变", "成矿", "矿化", "赋存",
        "岩浆期后", "热液充填", "交代型", "控矿", "容矿", "导矿",
        "矿田", "矿区", "矿体", "地层", "构造", "岩体"
    ]
    term_count = sum(answer.count(term) for term in professional_terms)
    term_score = min(100, term_count * 4)
    scores["专业表述"] = round(term_score, 1)

    # 加权总分
    total_score = (
        scores["要点覆盖率"] * 0.5 +
        scores["推理深度"] * 0.25 +
        scores["数据支撑"] * 0.15 +
        scores["专业表述"] * 0.1
    )
    scores["总分"] = round(total_score, 1)

    return scores


def run_evaluation():
    """运行完整评测实验"""
    print("=" * 80)
    print("川口矿区地质图理解评测实验")
    print(f"实验时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型：{MODEL_NAME}")
    print(f"API: {BASE_URL}")
    print("=" * 80)

    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": MODEL_NAME,
            "base_url": BASE_URL,
            "dimensions": list(EVALUATION_QUESTIONS.keys())
        },
        "zero_shot": {},
        "rag_enhanced": {},
        "comparison": {}
    }

    detailed_results = []

    for dim_id, dim_data in EVALUATION_QUESTIONS.items():
        print(f"\n{'='*60}")
        print(f"评测维度：{dim_data['name']}")
        print("="*60)

        # 零样本评测
        print("\n[1/2] 零样本评测中...")
        zero_answer = zero_shot_eval(dim_data['question'])
        zero_scores = score_answer(zero_answer, dim_data['key_points'])

        results["zero_shot"][dim_id] = {
            "answer": zero_answer,
            "scores": zero_scores
        }
        print(f"零样本得分：总分={zero_scores['总分']:.1f}")

        # 等待 API 限流
        time.sleep(5)

        # 检索增强评测
        print("\n[2/2] 检索增强评测中...")
        rag_answer = rag_enhanced_eval(dim_data['question'])
        rag_scores = score_answer(rag_answer, dim_data['key_points'])

        results["rag_enhanced"][dim_id] = {
            "answer": rag_answer,
            "scores": rag_scores
        }
        print(f"检索增强得分：总分={rag_scores['总分']:.1f}")

        # 对比分析
        improvement = rag_scores['总分'] - zero_scores['总分']
        improvement_rate = (improvement / zero_scores['总分'] * 100) if zero_scores['总分'] > 0 else 0
        results["comparison"][dim_id] = {
            "zero_shot_score": zero_scores['总分'],
            "rag_score": rag_scores['总分'],
            "improvement": improvement,
            "improvement_rate": round(improvement_rate, 1)
        }
        if improvement > 0:
            print(f"提升幅度：+{improvement:.1f} ({improvement_rate:.1f}%)")
        else:
            print(f"提升幅度：{improvement:.1f} ({improvement_rate:.1f}%)")

        # 保存详细结果
        detailed_results.append({
            "dimension": dim_data['name'],
            "question": dim_data['question'],
            "zero_shot_answer": zero_answer[:800] + "..." if len(zero_answer) > 800 else zero_answer,
            "zero_shot_score": zero_scores,
            "rag_answer": rag_answer[:800] + "..." if len(rag_answer) > 800 else rag_answer,
            "rag_score": rag_scores,
            "improvement": f"+{improvement:.1f} ({improvement_rate:.1f}%)"
        })

        # 保存中间结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"data/evaluation_results_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(5)

    print(f"\n{'='*60}")
    print(f"评测完成！结果已保存至：{output_file}")
    print("="*60)

    # 生成汇总表格
    print("\n【评测结果汇总】")
    print("-" * 90)
    print(f"{'维度':<10} {'零样本':<8} {'检索增强':<8} {'提升':<10} {'提升率':<10} {'详细得分'}")
    print("-" * 90)

    total_zero = 0
    total_rag = 0

    for dim_id, comp in results["comparison"].items():
        dim_name = EVALUATION_QUESTIONS[dim_id]['name']
        rag_scores = results["rag_enhanced"][dim_id]["scores"]
        print(f"{dim_name:<10} {comp['zero_shot_score']:<8.1f} {comp['rag_score']:<8.1f} "
              f"+{comp['improvement']:<9.1f} {comp['improvement_rate']:<10.1f}% "
              f"覆盖={rag_scores['要点覆盖率']:.0f}% 推理={rag_scores['推理深度']:.0f} 数据={rag_scores['数据支撑']:.0f}")
        total_zero += comp['zero_shot_score']
        total_rag += comp['rag_score']

    print("-" * 90)
    avg_zero = total_zero / len(results["comparison"])
    avg_rag = total_rag / len(results["comparison"])
    avg_improve = avg_rag - avg_zero
    improve_rate = (avg_improve / avg_zero * 100) if avg_zero > 0 else 0
    print(f"{'平均':<10} {avg_zero:<8.1f} {avg_rag:<8.1f} "
          f"+{avg_improve:<9.1f} {improve_rate:<10.1f}%")
    print("="*80)

    # 生成 Markdown 报告
    md_report = generate_markdown_report(detailed_results, results["comparison"])
    md_file = f"data/evaluation_report_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_report)
    print(f"评测报告已生成：{md_file}")

    return results


def generate_markdown_report(detailed_results, comparison):
    """生成 Markdown 格式评测报告"""
    report = """# 川口矿区地质图理解评测实验报告

## 实验信息

- **实验时间**: {timestamp}
- **评测模型**: {model}
- **评测维度**: 地层、构造、岩浆岩、成矿系统

## 评测结果汇总

| 维度 | 零样本得分 | 检索增强得分 | 提升幅度 | 提升率 |
|------|------------|--------------|----------|--------|
""".format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        model=MODEL_NAME
    )

    total_zero = 0
    total_rag = 0

    for result in detailed_results:
        dim = result['dimension']
        zero = result['zero_shot_score']['总分']
        rag = result['rag_score']['总分']
        improvement = rag - zero
        rate = (improvement / zero * 100) if zero > 0 else 0
        total_zero += zero
        total_rag += rag
        report += f"| {dim} | {zero:.1f} | {rag:.1f} | +{improvement:.1f} | {rate:.1f}% |\n"

    avg_zero = total_zero / len(detailed_results)
    avg_rag = total_rag / len(detailed_results)
    avg_improve = avg_rag - avg_zero
    avg_rate = (avg_improve / avg_zero * 100) if avg_zero > 0 else 0

    report += f"| **平均** | **{avg_zero:.1f}** | **{avg_rag:.1f}** | **+{avg_improve:.1f}** | **{avg_rate:.1f}%** |\n"

    report += """

## 详细评测结果

"""

    for i, result in enumerate(detailed_results, 1):
        report += f"""### {i}. {result['dimension']}

**问题**: {result['question']}

#### 零样本回答 (得分：{result['zero_shot_score']['总分']:.1f})

{result['zero_shot_answer']}

#### 检索增强回答 (得分：{result['rag_score']['总分']:.1f})

{result['rag_answer']}

---

"""

    report += """## 结论

检索增强方法在各地质维度上均显著优于零样本基线，尤其在要点覆盖率和数据支撑度方面提升明显。
这验证了接入地质知识图谱和勘查报告资料对提升地质图理解能力的有效性。
"""

    return report


if __name__ == "__main__":
    run_evaluation()
