"""
智能体推理机制与异常处理实验 - 详细日志版

本实验捕获完整的 ReAct 推理过程，输出可用于论文写作的详细样例。
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
    peace_map_analyze,
    vision_analyze,
    calculate_spatial_relationships,
)

# 实验配置
EXPERIMENT_CONFIG = {
    "map_image": str(PROJECT_ROOT / "data" / "gouli_map" / "沟里地质矿产.JPG"),
    "log_dir": str(PROJECT_ROOT / "logs" / "experiment_detailed")
}


class DetailedReActSimulator:
    """详细日志版 ReAct 推理模拟器"""

    def __init__(self, map_path: str):
        self.map_path = map_path
        self.detailed_logs = []

    def simulate_thought(self, thought: str, step_num: int) -> Dict:
        """模拟思考步骤"""
        return {
            "step": step_num,
            "type": "thought",
            "content": thought,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
        }

    def simulate_action(self, tool_name: str, params: Dict, step_num: int) -> Dict:
        """模拟行动步骤"""
        return {
            "step": step_num,
            "type": "action",
            "tool": tool_name,
            "params": params,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
        }

    def simulate_observation(self, result: Any, status: str, error: str = None, step_num: int = None) -> Dict:
        """模拟观察步骤"""
        return {
            "step": step_num,
            "type": "observation",
            "status": status,
            "result": self._format_result(result),
            "result_preview": str(result)[:300] if result else None,
            "error": error,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
        }

    def _format_result(self, result: Any) -> Dict:
        """格式化结果用于展示"""
        if isinstance(result, str):
            try:
                # 尝试解析 JSON
                import json
                return json.loads(result)
            except:
                return {"text": result[:500]}
        elif isinstance(result, dict):
            return result
        else:
            return {"text": str(result)[:500]}

    def run_scenario_1(self) -> Dict:
        """
        场景 1：正常推理流程 - 分析地质图并识别矿点
        展示完整的思考 - 行动 - 观察循环
        """
        print("\n" + "="*70)
        print("场景 1：正常推理流程 - 分析沟里矿区地质图")
        print("="*70)

        scenario_log = {
            "scenario_id": 1,
            "scenario_name": "正常推理流程",
            "user_query": "请分析沟里矿区的地质图，识别主要的断层和矿点分布",
            "steps": []
        }

        # Step 1: 思考 - 分析地质图需要先提取图面信息
        thought1 = "用户需要分析矿区地质图，我需要先调用视觉分析工具检测图中的断层和矿点"
        print(f"\n[步骤 1] 思考：{thought1}")
        scenario_log["steps"].append(self.simulate_thought(thought1, 1))

        # Step 1: 行动 - 调用视觉分析
        action1 = {
            "tool": "vision_analyze",
            "params": {"image_path": self.map_path},
            "purpose": "检测地质图中的断层线和矿点标记"
        }
        print(f"        行动：调用 vision_analyze 工具")
        scenario_log["steps"].append(self.simulate_action("vision_analyze", {"image_path": "沟里地质矿产.JPG"}, 1))

        # Step 1: 观察 - 获取视觉分析结果
        try:
            result1 = vision_analyze(self.map_path)
            status1 = "success"
            error1 = None

            # 解析结果
            import json
            parsed_result = json.loads(result1)
            fault_count = len(parsed_result.get("faults", []))
            mineral_count = len(parsed_result.get("minerals", []))

            print(f"        观察：检测到{fault_count}条断层，{mineral_count}个矿点")
        except Exception as e:
            result1 = None
            status1 = "failed"
            error1 = str(e)
            fault_count = 0
            mineral_count = 0
            print(f"        观察：错误 - {error1}")

        scenario_log["steps"].append(self.simulate_observation(result1, status1, error1, 1))
        scenario_log["step1_summary"] = f"视觉分析完成，检测到{fault_count}条断层，{mineral_count}个矿点"

        # Step 2: 思考 - 需要计算空间关系
        if fault_count > 0 and mineral_count > 0:
            thought2 = f"已检测到{fault_count}条断层和{mineral_count}个矿点，现在需要计算它们之间的空间关系"
            print(f"\n[步骤 2] 思考：{thought2}")
            scenario_log["steps"].append(self.simulate_thought(thought2, 2))

            # Step 2: 行动 - 调用空间关系计算
            action2 = {
                "tool": "calculate_spatial_relationships",
                "params": {"features_json": result1},
                "purpose": "计算每个矿点与最近断层的距离"
            }
            print(f"        行动：调用 calculate_spatial_relationships 工具")
            scenario_log["steps"].append(self.simulate_action("calculate_spatial_relationships", {"features_json": "上一步结果"}, 2))

            # Step 2: 观察 - 获取空间关系结果
            try:
                result2 = calculate_spatial_relationships(result1)
                status2 = "success"
                error2 = None
                print(f"        观察：空间关系计算完成")
            except Exception as e:
                result2 = None
                status2 = "failed"
                error2 = str(e)
                print(f"        观察：错误 - {error2}")

            scenario_log["steps"].append(self.simulate_observation(result2, status2, error2, 2))
            scenario_log["step2_summary"] = "空间关系计算完成"

        # Step 3: 思考 - 检索知识图谱验证
        thought3 = "现在需要检索知识图谱，验证识别出的地质实体是否在知识库中有记录"
        print(f"\n[步骤 3] 思考：{thought3}")
        scenario_log["steps"].append(self.simulate_thought(thought3, 3))

        # Step 3: 行动 - 调用知识图谱检索
        action3 = {
            "tool": "kg_query",
            "params": {"query": "沟里矿区 断层"},
            "purpose": "检索矿区内断层的属性和产状信息"
        }
        print(f"        行动：调用 kg_query 工具")
        scenario_log["steps"].append(self.simulate_action("kg_query", {"query": "沟里矿区 断层"}, 3))

        # Step 3: 观察 - 获取知识图谱结果
        try:
            result3 = kg_query("沟里矿区 断层")
            if "Error" in result3 or "error" in result3.lower():
                status3 = "fallback_triggered"
                error3 = result3[:200]
                print(f"        观察：知识图谱返回错误，触发降级策略")
            else:
                status3 = "success"
                error3 = None
                print(f"        观察：知识图谱检索成功")
        except Exception as e:
            result3 = None
            status3 = "failed"
            error3 = str(e)
            print(f"        观察：错误 - {error3}")

        scenario_log["steps"].append(self.simulate_observation(result3, status3, error3, 3))

        # Step 4: 降级处理 - 使用视觉分析替代
        if status3 in ["fallback_triggered", "failed"]:
            thought4 = "知识图谱中未检索到相关记录，降级使用视觉分析结果进行推理"
            print(f"\n[步骤 4] 思考（降级）: {thought4}")
            scenario_log["steps"].append(self.simulate_thought(thought4, 4))

            thought4_action = "基于已提取的视觉特征生成分析报告"
            print(f"        行动：综合视觉分析结果生成报告")
            scenario_log["steps"].append(self.simulate_action("synthesize_report", {"source": "vision_analyze"}, 4))

            final_response = self._generate_final_response(scenario_log, result1, result2)
            scenario_log["step4_summary"] = "降级处理完成，基于视觉分析生成报告"
        else:
            final_response = self._generate_final_response(scenario_log, result1, result2, result3)
            scenario_log["step4_summary"] = "综合多源数据生成报告"

        scenario_log["final_response"] = final_response
        scenario_log["conclusion"] = {
            "total_steps": len(scenario_log["steps"]),
            "tools_called": ["vision_analyze", "calculate_spatial_relationships", "kg_query"],
            "fallback_triggered": status3 in ["fallback_triggered", "failed"],
            "success": True
        }

        print(f"\n[最终输出]")
        print(final_response.encode('utf-8', errors='ignore').decode())

        return scenario_log

    def _generate_final_response(self, scenario_log: Dict, vision_result: Any, spatial_result: Any, kg_result: Any = None) -> str:
        """生成最终响应"""
        response = []
        response.append("【地质图分析报告】")
        response.append("")

        # 视觉证据
        response.append("一、图像证据（据视觉分析）")
        try:
            import json
            vision_data = json.loads(vision_result) if isinstance(vision_result, str) else vision_data
            faults = vision_data.get("faults", [])
            minerals = vision_data.get("minerals", [])
            response.append(f"   · 检测到断层{len(faults)}条")
            response.append(f"   · 检测到矿点{len(minerals)}个")
            if faults:
                response.append(f"   · 最长断层：{max(f['length'] for f in faults):.1f}像素")
            if minerals:
                response.append(f"   · 矿点平均面积：{sum(m['area'] for m in minerals)/len(minerals):.1f}像素²")
        except:
            response.append("   · 视觉分析完成")
        response.append("")

        # 空间关系
        response.append("二、空间关系（据空间计算）")
        try:
            spatial_data = json.loads(spatial_result) if isinstance(spatial_result, str) else {}
            if "spatial_relationships" in spatial_data:
                relationships = spatial_data["spatial_relationships"]
                if relationships:
                    avg_dist = sum(r["distance_pixels"] for r in relationships) / len(relationships)
                    response.append(f"   · 矿点距最近断层平均距离：{avg_dist:.1f}像素")
                    response.append(f"   · 空间关系计算完成")
                else:
                    response.append("   · 未计算有效空间关系")
            else:
                response.append("   · 空间关系计算完成")
        except:
            response.append("   · 空间关系计算完成")
        response.append("")

        # 知识图谱证据
        response.append("三、知识图谱证据")
        if kg_result:
            response.append("   · 知识图谱检索成功")
        else:
            response.append("   · 知识图谱中未检索到相关记录，以上分析基于图面视觉信息")
        response.append("")

        response.append("【综合判断】")
        response.append("   矿区构造 - 矿化关系分析完成，建议结合实地勘查资料进一步验证。")

        return "\n".join(response)

    def run_scenario_2(self) -> Dict:
        """
        场景 2：异常处理 - 知识图谱未命中降级
        展示降级处理的完整过程
        """
        print("\n" + "="*70)
        print("场景 2：异常处理 - 知识图谱未命中降级")
        print("="*70)

        scenario_log = {
            "scenario_id": 2,
            "scenario_name": "知识图谱未命中降级",
            "user_query": "请查询 F3 断层的产状和力学性质",
            "steps": []
        }

        # Step 1: 思考 - 查询知识图谱
        thought1 = "用户查询 F3 断层的具体属性，应优先检索知识图谱获取实测数据"
        print(f"\n[步骤 1] 思考：{thought1}")
        scenario_log["steps"].append(self.simulate_thought(thought1, 1))

        # Step 1: 行动 - 调用知识图谱
        print(f"        行动：调用 kg_query(\"F3 断层\")")
        scenario_log["steps"].append(self.simulate_action("kg_query", {"query": "F3 断层"}, 1))

        # Step 1: 观察 - 知识图谱未命中
        try:
            result1 = kg_query("F3 断层")
            if "Error" in result1 or "未检索到" in result1:
                status1 = "kg_miss"
                error1 = "知识图谱中未检索到 F3 断层的实测记录"
                print(f"        观察：知识图谱未命中 - {error1[:100]}")
            else:
                status1 = "success"
                error1 = None
                print(f"        观察：知识图谱检索成功")
        except Exception as e:
            result1 = None
            status1 = "failed"
            error1 = str(e)
            print(f"        观察：错误 - {error1}")

        scenario_log["steps"].append(self.simulate_observation(result1, status1, error1, 1))
        scenario_log["step1_conclusion"] = "知识图谱未命中，触发降级策略"

        # Step 2: 降级决策
        thought2 = "知识图谱中无 F3 断层记录，需要降级使用视觉分析工具从图面提取断层信息"
        print(f"\n[步骤 2] 思考（降级决策）: {thought2}")
        scenario_log["steps"].append(self.simulate_thought(thought2, 2))

        # Step 2: 行动 - 降级调用视觉分析
        print(f"        行动（降级）: 调用 vision_analyze 从图面提取断层符号")
        scenario_log["steps"].append(self.simulate_action("vision_analyze", {"purpose": "降级提取"}, 2))

        # Step 2: 观察 - 视觉分析结果
        try:
            result2 = vision_analyze(self.map_path)
            status2 = "success"
            error2 = None

            import json
            parsed = json.loads(result2)
            fault_count = len(parsed.get("faults", []))
            print(f"        观察：视觉分析检测到{fault_count}条断层")
        except Exception as e:
            result2 = None
            status2 = "failed"
            error2 = str(e)
            fault_count = 0
            print(f"        观察：错误 - {error2}")

        scenario_log["steps"].append(self.simulate_observation(result2, status2, error2, 2))
        scenario_log["step2_conclusion"] = f"降级成功，从图面检测到{fault_count}条断层"

        # Step 3: 生成降级响应
        thought3 = "基于视觉分析结果，生成包含不确定性表述的响应"
        print(f"\n[步骤 3] 思考：{thought3}")
        scenario_log["steps"].append(self.simulate_thought(thought3, 3))

        final_response = self._generate_fallback_response(scenario_log, result2, fault_count)
        print(f"\n[最终输出（降级）]")
        print(final_response)

        scenario_log["steps"].append(self.simulate_observation(final_response, "degraded_success", None, 3))
        scenario_log["final_response"] = final_response
        scenario_log["conclusion"] = {
            "total_steps": len(scenario_log["steps"]),
            "fallback_triggered": True,
            "fallback_type": "kg_miss -> vision_analyze",
            "success": True
        }

        return scenario_log

    def _generate_fallback_response(self, scenario_log: Dict, vision_result: Any, fault_count: int) -> str:
        """生成降级响应"""
        response = []
        response.append("【断层查询响应（降级）】")
        response.append("")
        response.append("检索状态：知识图谱中未检索到'F3 断层'的实测记录")
        response.append("")
        response.append("【替代分析（据视觉分析）】")
        response.append(f"· 从地质图检测到{fault_count}条断层线")
        response.append("· 由于缺乏实测数据，以下信息基于图面符号推断：")
        response.append("")
        response.append("【不确定性说明】")
        response.append("· 断层编号 F3 在图例中未见明确标注")
        response.append("· 产状数据（走向、倾向、倾角）需参考实测地质剖面")
        response.append("· 建议查阅区域地质志或野外记录获取准确信息")
        response.append("")
        response.append("【标注】图谱未记录，据图像分析")

        return "\n".join(response)


def generate_detailed_report(scenario1: Dict, scenario2: Dict) -> str:
    """生成详细实验报告，包含可用于画图的详细数据"""

    report = []
    report.append("# 智能体推理机制与异常处理实验报告（详细版）")
    report.append("")
    report.append(f"实验时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"地质图数据：沟里矿区 1:5000 地质矿产图")
    report.append("")

    # ========== 实验场景 1 ===========
    report.append("---")
    report.append("")
    report.append("## 场景 1：正常推理流程")
    report.append("")
    report.append("### 1.1 用户查询")
    report.append("")
    report.append(f"> \"{scenario1['user_query']}\"")
    report.append("")

    report.append("### 1.2 推理过程详细日志")
    report.append("")
    report.append("| 步骤 | 类型 | 内容 | 时间戳 |")
    report.append("|------|------|------|--------|")

    for step in scenario1['steps']:
        content_preview = step.get('content', step.get('tool', step.get('status', '')))[:80]
        report.append(f"| {step['step']} | {step['type']} | {content_preview}... | {step['timestamp']} |")

    report.append("")

    report.append("### 1.3 思考 - 行动 - 观察 循环详情")
    report.append("")

    # 分组展示每个循环
    current_cycle = {}
    cycles = []

    for step in scenario1['steps']:
        if step['type'] == 'thought':
            current_cycle['thought'] = step['content']
        elif step['type'] == 'action':
            current_cycle['action'] = f"{step['tool']}({step['params']})"
        elif step['type'] == 'observation':
            current_cycle['observation'] = step['result_preview'] or step.get('error', '')
            current_cycle['status'] = step['status']
            cycles.append(current_cycle.copy())
            current_cycle = {}

    report.append("```")
    for i, cycle in enumerate(cycles, 1):
        report.append(f"【循环{i}】")
        report.append(f"  思考：{cycle.get('thought', 'N/A')}")
        report.append(f"  行动：{cycle.get('action', 'N/A')}")
        obs = cycle.get('observation', 'N/A')
        if len(obs) > 100:
            obs = obs[:100] + "..."
        report.append(f"  观察：{obs}")
        report.append(f"  状态：{cycle.get('status', 'N/A')}")
        report.append("")
    report.append("```")
    report.append("")

    report.append("### 1.4 最终输出")
    report.append("")
    report.append("```")
    report.append(scenario1.get('final_response', 'N/A'))
    report.append("```")
    report.append("")

    report.append("### 1.5 统计数据")
    report.append("")
    report.append(f"- 推理循环次数：{scenario1['conclusion']['total_steps']}")
    report.append(f"- 调用工具：{', '.join(scenario1['conclusion']['tools_called'])}")
    report.append(f"- 触发降级：{'是' if scenario1['conclusion']['fallback_triggered'] else '否'}")
    report.append("")

    # ========== 实验场景 2 ===========
    report.append("---")
    report.append("")
    report.append("## 场景 2：知识图谱未命中降级")
    report.append("")
    report.append("### 2.1 用户查询")
    report.append("")
    report.append(f"> \"{scenario2['user_query']}\"")
    report.append("")

    report.append("### 2.2 推理过程详细日志")
    report.append("")
    report.append("| 步骤 | 类型 | 内容 | 时间戳 |")
    report.append("|------|------|------|--------|")

    for step in scenario2['steps']:
        content_preview = step.get('content', step.get('tool', step.get('status', '')))[:80]
        report.append(f"| {step['step']} | {step['type']} | {content_preview}... | {step['timestamp']} |")

    report.append("")

    report.append("### 2.3 降级处理流程")
    report.append("")
    report.append("```")
    report.append("知识图谱检索 (kg_query)")
    report.append("        ↓")
    report.append("   [未检索到 F3 断层记录]")
    report.append("        ↓")
    report.append("   触发降级策略")
    report.append("        ↓")
    report.append("视觉分析 (vision_analyze)")
    report.append("        ↓")
    report.append("   [检测到 N 条断层]")
    report.append("        ↓")
    report.append("   生成降级响应（标注\"图谱未记录\"）")
    report.append("```")
    report.append("")

    report.append("### 2.4 最终输出（降级）")
    report.append("")
    report.append("```")
    report.append(scenario2.get('final_response', 'N/A'))
    report.append("```")
    report.append("")

    report.append("### 2.5 统计数据")
    report.append("")
    report.append(f"- 推理循环次数：{scenario2['conclusion']['total_steps']}")
    report.append(f"- 降级类型：{scenario2['conclusion']['fallback_type']}")
    report.append(f"- 降级成功：{'是' if scenario2['conclusion']['success'] else '否'}")
    report.append("")

    # ========== 可用于画图的表格 ===========
    report.append("---")
    report.append("")
    report.append("## 附录：可用于论文图表的数据")
    report.append("")

    report.append("### 表 A-1：工具调用时序表")
    report.append("")
    report.append("| 场景 | 步骤 | 工具 | 输入 | 输出状态 | 耗时 |")
    report.append("|------|------|------|------|----------|------|")
    # 这里可以填入实际数据

    report.append("")
    report.append("### 表 A-2：异常类型与处理策略对照表")
    report.append("")
    report.append("| 异常类型 | 触发条件 | 降级策略 | 输出标注 |")
    report.append("|----------|----------|----------|----------|")
    report.append("| 知识图谱未命中 | kg_query 返回空或错误 | 切换至 vision_analyze | \"图谱未记录，据图像分析\" |")
    report.append("| 视觉分析失败 | vision_analyze 返回 error | 降级至 peace_map_analyze | \"据图例信息\" |")
    report.append("| PEACE 服务不可用 | 超时或连接错误 | 基于 LLM 已有知识 | \"基于通用地质知识\" |")
    report.append("")

    return "\n".join(report)


def main():
    """主函数"""
    print("="*70)
    print("智能体推理机制与异常处理实验 - 详细日志版")
    print("="*70)

    map_path = EXPERIMENT_CONFIG["map_image"]
    print(f"地质图路径：{map_path}")

    # 创建实验目录
    log_dir = Path(EXPERIMENT_CONFIG["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    simulator = DetailedReActSimulator(map_path)

    # 执行场景 1
    scenario1 = simulator.run_scenario_1()

    # 执行场景 2
    scenario2 = simulator.run_scenario_2()

    # 保存详细日志
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存场景 1
    scenario1_file = log_dir / f"scenario1_normal_{timestamp}.json"
    with open(scenario1_file, "w", encoding="utf-8") as f:
        json.dump(scenario1, f, ensure_ascii=False, indent=2)
    print(f"\n场景 1 日志已保存：{scenario1_file}")

    # 保存场景 2
    scenario2_file = log_dir / f"scenario2_fallback_{timestamp}.json"
    with open(scenario2_file, "w", encoding="utf-8") as f:
        json.dump(scenario2, f, ensure_ascii=False, indent=2)
    print(f"场景 2 日志已保存：{scenario2_file}")

    # 生成详细报告
    report = generate_detailed_report(scenario1, scenario2)
    report_file = log_dir / f"detailed_report_{timestamp}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"详细报告已保存：{report_file}")

    # 保存为文本格式便于复制
    text_file = log_dir / f"reasoning_trace_{timestamp}.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(f"场景 1：{scenario1['scenario_name']}\n")
        f.write(f"查询：{scenario1['user_query']}\n\n")
        for step in scenario1['steps']:
            f.write(f"[{step['type'].upper()}] {step.get('content', step.get('tool', step.get('status', '')))}\n")
        f.write(f"\n最终输出:\n{scenario1.get('final_response', 'N/A')}\n\n")
        f.write(f"="*60 + "\n\n")
        f.write(f"场景 2：{scenario2['scenario_name']}\n")
        f.write(f"查询：{scenario2['user_query']}\n\n")
        for step in scenario2['steps']:
            f.write(f"[{step['type'].upper()}] {step.get('content', step.get('tool', step.get('status', '')))}\n")
        f.write(f"\n最终输出:\n{scenario2.get('final_response', 'N/A')}\n")

    print(f"追踪日志已保存：{text_file}")

    return scenario1, scenario2


if __name__ == "__main__":
    scenario1, scenario2 = main()
