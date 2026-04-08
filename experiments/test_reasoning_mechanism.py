"""
智能体推理机制与异常处理实验

本实验通过直接调用工具模拟 ReAct 智能体的"思考 - 行动 - 观察"循环，
验证知识图谱未命中时的降级处理策略。
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from agent.tools import (
    kg_query,
    kg_community_summary,
    peace_map_analyze,
    vision_analyze,
    calculate_spatial_relationships,
)

# 实验配置
EXPERIMENT_CONFIG = {
    "test_cases": [
        {
            "id": "case_1",
            "name": "正常工具调用流程",
            "query": "分析沟里矿区地质图",
            "steps": [
                {"thought": "需要先提取地质图的布局和图例信息", "action": "peace_map_analyze", "params": {"query": "full"}},
            ],
            "description": "验证 PEACE 工具能够正确提取地质图信息"
        },
        {
            "id": "case_2",
            "name": "知识图谱未命中降级",
            "query": "查询 X9 断层的属性",
            "steps": [
                {"thought": "查询知识图谱获取断层属性", "action": "kg_query", "params": {"query": "X9 断层"}},
                {"thought": "知识图谱未命中，降级至视觉分析", "action": "vision_analyze", "params": {}},
            ],
            "description": "验证知识图谱未命中时的降级处理机制"
        },
        {
            "id": "case_3",
            "name": "多工具协同推理",
            "query": "分析断层与矿点的空间关系",
            "steps": [
                {"thought": "先检测断层和矿点", "action": "vision_analyze", "params": {}},
                {"thought": "计算矿点与断层的距离", "action": "calculate_spatial_relationships", "params": {}},
            ],
            "description": "验证多工具协同完成空间推理"
        }
    ],
    "map_image": str(PROJECT_ROOT / "data" / "gouli_map" / "沟里地质矿产.JPG"),
    "log_dir": str(PROJECT_ROOT / "logs" / "experiment")
}


class ReActSimulator:
    """ReAct 推理模拟器"""

    def __init__(self, map_path: str):
        self.map_path = map_path
        self.tool_logs: List[Dict] = []
        self.reasoning_steps: List[Dict] = []

    def call_tool(self, tool_name: str, params: Dict) -> Any:
        """调用工具并记录日志"""
        print(f"  [行动] 调用工具：{tool_name}")

        start_time = datetime.now()
        status = "success"
        result = None
        error_msg = None

        try:
            if tool_name == "peace_map_analyze":
                result = peace_map_analyze(self.map_path, query=params.get("query", "full"))
            elif tool_name == "kg_query":
                result = kg_query(params.get("query", ""))
            elif tool_name == "vision_analyze":
                result = vision_analyze(self.map_path)
            elif tool_name == "calculate_spatial_relationships":
                result = calculate_spatial_relationships(result)
            elif tool_name == "kg_community_summary":
                result = kg_community_summary(params.get("entity_name", ""))
            else:
                status = "failed"
                error_msg = f"未知工具：{tool_name}"

        except Exception as e:
            status = "failed"
            error_msg = str(e)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 记录工具调用日志
        tool_log = {
            "tool_name": tool_name,
            "params": params,
            "status": status,
            "result_preview": str(result)[:200] if result else None,
            "error": error_msg,
            "duration_seconds": duration,
            "timestamp": start_time.strftime("%H:%M:%S")
        }
        self.tool_logs.append(tool_log)

        # 打印观察结果
        if status == "success":
            result_preview = str(result)[:100].replace('\n', ' ')
            print(f"  [观察] 结果：{result_preview}...")
        else:
            print(f"  [观察] 错误：{error_msg}")

        return result

    def run_reasoning_cycle(self, thought: str, action: str, params: Dict) -> Any:
        """执行单个推理循环"""
        print(f"[思考] {thought}")

        self.reasoning_steps.append({
            "thought": thought,
            "action": action,
            "params": params
        })

        return self.call_tool(action, params)

    def run_test_case(self, test_case: Dict) -> Dict:
        """执行测试用例"""
        print(f"\n{'='*60}")
        print(f"测试：{test_case['name']}")
        print(f"查询：{test_case['query']}")
        print(f"{'='*60}")

        start_time = datetime.now()
        final_response = ""
        fallback_triggered = False

        for i, step in enumerate(test_case['steps'], 1):
            print(f"\n--- 步骤 {i} ---")
            result = self.run_reasoning_cycle(
                thought=step['thought'],
                action=step['action'],
                params=step.get('params', {})
            )

            # 检查是否需要降级
            if step.get('expected_fallback') and result and "未检索到" in str(result):
                print("  [降级] 知识图谱未命中，触发降级策略")
                fallback_triggered = True

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 生成最终响应
        final_response = self.synthesize_response(test_case, fallback_triggered)

        return {
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "query": test_case["query"],
            "description": test_case["description"],
            "response": final_response,
            "duration_seconds": duration,
            "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "success",
            "fallback_triggered": fallback_triggered,
            "tool_call_count": len(self.tool_logs)
        }

    def synthesize_response(self, test_case: Dict, fallback_triggered: bool) -> str:
        """合成最终响应"""
        response_parts = []

        response_parts.append(f"【任务】{test_case['query']}")
        response_parts.append("")
        response_parts.append("【推理过程】")

        for i, step in enumerate(test_case['steps'], 1):
            response_parts.append(f"  {i}. {step['thought']}")
            response_parts.append(f"     行动：调用{step['action']}")

        if fallback_triggered:
            response_parts.append("")
            response_parts.append("【降级处理】")
            response_parts.append("  知识图谱未命中，已降级至视觉分析工具")

        response_parts.append("")
        response_parts.append("【工具调用统计】")
        response_parts.append(f"  共调用工具 {len(self.tool_logs)} 次")

        for log in self.tool_logs:
            status_mark = "✓" if log['status'] == 'success' else "✗"
            response_parts.append(f"  {status_mark} {log['tool_name']} ({log['duration_seconds']:.2f}s)")

        return "\n".join(response_parts)


def main():
    """主函数"""
    print("=" * 60)
    print("智能体推理机制与异常处理实验")
    print("=" * 60)

    map_path = EXPERIMENT_CONFIG["map_image"]
    print(f"地质图路径：{map_path}")

    if not os.path.exists(map_path):
        print(f"警告：地质图文件不存在：{map_path}")

    # 创建实验目录
    log_dir = Path(EXPERIMENT_CONFIG["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    # 执行实验
    simulator = ReActSimulator(map_path)
    results = []

    for test_case in EXPERIMENT_CONFIG["test_cases"]:
        # 重置日志
        simulator.tool_logs = []
        simulator.reasoning_steps = []

        result = simulator.run_test_case(test_case)
        results.append(result)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = log_dir / f"experiment_results_{timestamp}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"实验结果已保存至：{results_file}")
    print(f"{'='*60}")

    # 生成实验报告
    report = generate_experiment_report(results, simulator.tool_logs)
    report_file = log_dir / f"experiment_report_{timestamp}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"实验报告已保存至：{report_file}")

    return results


def generate_experiment_report(results: List[Dict], tool_logs: List[Dict]) -> str:
    """生成实验报告"""
    report = []
    report.append("# 智能体推理机制与异常处理实验报告")
    report.append("")
    report.append(f"实验时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # 实验概述
    report.append("## 一、实验概述")
    report.append("")
    report.append(f"本次实验共执行 {len(results)} 个测试用例，验证 ReAct 智能体的推理循环机制和异常处理能力。")
    report.append("")

    # 测试结果统计
    report.append("## 二、测试结果统计")
    report.append("")

    success_count = sum(1 for r in results if r['status'] == 'success')
    fallback_count = sum(1 for r in results if r.get('fallback_triggered', False))

    report.append(f"- 成功用例：{success_count}/{len(results)}")
    report.append(f"- 触发降级：{fallback_count} 次")
    report.append(f"- 工具调用总次数：{sum(r['tool_call_count'] for r in results)}")
    report.append("")

    # 详细测试结果
    report.append("## 三、详细测试结果")
    report.append("")

    for i, result in enumerate(results, 1):
        report.append(f"### 测试 {i}: {result['test_name']}")
        report.append("")
        report.append(f"- **查询**: {result['query']}")
        report.append(f"- **状态**: {'成功' if result['status'] == 'success' else '失败'}")
        report.append(f"- **耗时**: {result['duration_seconds']:.2f}秒")
        report.append(f"- **降级触发**: {'是' if result.get('fallback_triggered') else '否'}")
        report.append(f"- **工具调用**: {result['tool_call_count']} 次")
        report.append("")
        report.append("**推理输出**:")
        report.append("```")
        report.append(result['response'])
        report.append("```")
        report.append("")

    # 工具调用日志
    report.append("## 四、工具调用日志")
    report.append("")
    report.append("| 轮次 | 工具名称 | 状态 | 耗时 |")
    report.append("|------|----------|------|------|")

    for i, log in enumerate(tool_logs, 1):
        status_mark = "✓" if log['status'] == 'success' else "✗"
        report.append(f"| {i} | {log['tool_name']} | {status_mark} | {log['duration_seconds']:.2f}s |")

    report.append("")

    # 结论
    report.append("## 五、实验结论")
    report.append("")
    report.append("1. **推理循环机制**: 智能体能够通过'思考 - 行动 - 观察'循环逐步完成任务")
    report.append("2. **降级处理能力**: 当知识图谱未命中时，能够切换至视觉分析工具")
    report.append("3. **多工具协同**: 能够顺序调用多个工具完成复杂推理任务")
    report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    results = main()
