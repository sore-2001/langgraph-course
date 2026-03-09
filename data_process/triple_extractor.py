"""
三元组抽取器：调用 LLM，基于地质本体从文本块中抽取标准化三元组
"""
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.llms import ChatMessage, MessageRole
from typing import List, Optional
import json
import re
from .config import Config
from .geo_ontology import GeoTriple, GeoRelationEnum
from .utils import logger, validate_triple
from .pdf_loader import load_geology_pdfs

class GeoTripleExtractor:
    """地质三元组抽取器"""
    def __init__(self):
        # 初始化 LLM（使用本地代理调用 Gemini）
        self.llm = OpenAILike(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            api_base=Config.OPENAI_BASE_URL,
            is_chat_model=True,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=8192
        )
        # 构建抽取提示词
        self.extract_prompt = self._build_extract_prompt()

    @staticmethod
    def _extract_json_array(text: str) -> Optional[list]:
        """从 LLM 响应中鲁棒地提取 JSON 数组，处理思考过程、markdown包裹、截断等情况"""
        content = text.strip()

        # 策略1：尝试直接解析
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # 策略2：提取 markdown 代码块中的 JSON
        md_match = re.search(r'```(?:json)?\s*\n?(.*?)```', content, re.DOTALL)
        if md_match:
            try:
                result = json.loads(md_match.group(1).strip())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # 策略3：找到最外层的 [ ... ] 并解析（跳过思考过程文本）
        bracket_match = re.search(r'\[.*\]', content, re.DOTALL)
        if bracket_match:
            try:
                result = json.loads(bracket_match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # 策略4：处理截断的 JSON（找到 [ 开头，逐步回退找到最后一个完整的 } 闭合）
        start = content.find('[')
        if start != -1:
            fragment = content[start:]
            # 从末尾往回找最后一个 }，尝试用 }] 闭合
            for i in range(len(fragment) - 1, 0, -1):
                if fragment[i] == '}':
                    candidate = fragment[:i+1] + ']'
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, list) and result:
                            logger.warning(f"JSON被截断，成功恢复 {len(result)} 条三元组")
                            return result
                    except json.JSONDecodeError:
                        continue

        return None

    def _build_extract_prompt(self) -> str:
        """构建LLM抽取提示词"""
        relation_list = [e.value for e in GeoRelationEnum]
        prompt = f"""你是专业的地质找矿知识图谱三元组抽取专家。

【核心规则】
1. 主体和客体都必须是带entity_type的实体对象，entity_type仅限以下6种：
   "矿床"、"矿体"、"岩石"、"矿物"、"地层"、"地质构造"
2. 关系名称必须从以下列表选择：{relation_list}
3. 实体只需填写 entity_type、name 和文本中明确提及的少量关键属性（1-3个即可），不要强行填充所有字段
4. 没有明确信息的属性直接省略，不要写null
5. 仅输出JSON数组，禁止输出任何分析、思考过程或解释文字

【重要：禁止自引用】
- 主体和客体必须是不同的实体，禁止subject_entity和object_entity的name相同
- 属性值（如品位、面积、厚度、倾角等数值）应直接写入实体的属性字段，而非创建三元组
  错误示范：塘江沅矿区 --面积为--> 塘江沅矿区（自引用，禁止！）
  正确做法：将面积值写入subject_entity的area字段即可，不需要为此创建三元组

【实体可用属性速查】
- 矿床：deposit_type, location, mineralization_age, area, shape
- 矿体：grade, length, thickness, dip_angle, host_rock
- 岩石：rock_type, lithology
- 矿物：mineral_type
- 地层：stratum_era, stratum_type
- 地质构造：tectonic_type, tectonic_function

【输出格式】仅输出JSON数组，示例：
[
  {{
    "subject_entity": {{"entity_type":"矿床","name":"黄山铜镍矿床","deposit_type":"铜镍矿床","location":"东天山"}},
    "relation": {{"relation_name":"赋存于","relation_type":"包含关系","subject":"黄山铜镍矿床","object":"镁铁-超镁铁质岩体"}},
    "object_entity": {{"entity_type":"岩石","name":"镁铁-超镁铁质岩体","rock_type":"岩浆岩"}}
  }},
  {{
    "subject_entity": {{"entity_type":"矿床","name":"黄山铜镍矿床"}},
    "relation": {{"relation_name":"主要矿物为","relation_type":"功能关系","subject":"黄山铜镍矿床","object":"黄铜矿"}},
    "object_entity": {{"entity_type":"矿物","name":"黄铜矿","mineral_type":"金属矿物"}}
  }}
]"""
        return prompt.strip()

    def extract_from_text(self, text: str) -> List[GeoTriple]:
        """
        从单段文本中抽取三元组
        
        Args:
            text: 地质文本块
        
        Returns:
            List[GeoTriple]: 标准化三元组列表
        """
        try:
            # 构建聊天消息
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=self.extract_prompt),
                ChatMessage(role=MessageRole.USER, content=f"请从以下文本中抽取三元组：\n{text}")
            ]
            
            # 调用LLM
            logger.info("调用LLM抽取三元组...")
            response = self.llm.chat(messages)
            
            # 解析响应（从混杂内容中提取 JSON 数组）
            triples_dict = self._extract_json_array(response.message.content)
            if triples_dict is None:
                logger.error(f"LLM响应中未找到有效JSON数组，响应内容：{response.message.content[:500]}")
                return []
            
            # 转换为GeoTriple对象并校验
            valid_triples = []
            for triple_dict in triples_dict:
                try:
                    triple = GeoTriple(**triple_dict)
                    if validate_triple(triple):
                        valid_triples.append(triple)
                    else:
                        logger.warning(f"无效三元组：{triple_dict}")
                except Exception as e:
                    logger.error(f"三元组转换失败：{str(e)}，原始数据：{triple_dict}")
                    continue
            
            logger.info(f"文本块抽取完成，有效三元组：{len(valid_triples)}条")
            return valid_triples
        
        except Exception as e:
            logger.error(f"单文本块抽取失败：{str(e)}", exc_info=True)
            return []

    def extract_from_pdfs(self, pdf_dir: Optional[str] = None) -> List[GeoTriple]:
        """
        从PDF目录中抽取所有三元组
        
        Args:
            pdf_dir: PDF目录
        
        Returns:
            List[GeoTriple]: 所有有效三元组
        """
        # 加载并切分PDF
        nodes = load_geology_pdfs(pdf_dir)
        if not nodes:
            return []
        
        # 批量抽取
        all_triples = []
        for i, node in enumerate(nodes):
            logger.info(f"处理文本块 {i+1}/{len(nodes)}：{node.metadata.get('source')}")
            triples = self.extract_from_text(node.text)
            all_triples.extend(triples)
        
        logger.info(f"PDF抽取完成，总计有效三元组：{len(all_triples)}条")
        return all_triples