"""
地质本体定义：核心Pydantic模型，包含所有地质实体、关系、三元组定义
参考《大模型驱动的东天山-北山找矿知识图谱构建及应用》论文本体
"""
from pydantic import BaseModel, Field, field_validator, Discriminator
from typing import List, Optional, Literal, Union, Annotated
from enum import Enum

# ========== 基础枚举类型（论文地质术语规范）==========
class MineralizationAgeEnum(str, Enum):
    """成矿年代枚举（东天山-北山成矿带核心年代）"""
    元古宙 = "元古宙"
    古生代 = "古生代"
    晚古生代 = "晚古生代"
    中生代 = "中生代"
    石炭纪 = "石炭纪"
    泥盆纪 = "泥盆纪"
    奥陶纪 = "奥陶纪"
    白垩纪 = "白垩纪"
    古新世 = "古新世"

class RockTypeEnum(str, Enum):
    """岩石类型枚举（论文核心类型）"""
    岩浆岩 = "岩浆岩"
    沉积岩 = "沉积岩"
    变质岩 = "变质岩"
    花岗岩 = "花岗岩"
    闪长岩 = "闪长岩"
    辉长岩 = "辉长岩"
    橄榄岩 = "橄榄岩"
    碳酸盐岩 = "碳酸盐岩"
    火山岩 = "火山岩"

class AlterationTypeEnum(str, Enum):
    """围岩蚀变类型枚举（论文核心类型）"""
    硅化 = "硅化"
    绿泥石化 = "绿泥石化"
    高岭土化 = "高岭土化"
    绢云母化 = "绢云母化"
    钾长石化 = "钾长石化"
    黑云母化 = "黑云母化"
    泥化 = "泥化"

class DepositShapeEnum(str, Enum):
    """矿床形态枚举（论文核心类型）"""
    透镜状 = "透镜状"
    脉状 = "脉状"
    层状 = "层状"
    似层状 = "似层状"
    囊状 = "囊状"
    不规则状 = "不规则状"

class TectonicUnitEnum(str, Enum):
    """大地构造单元枚举（东天山-北山核心单元）"""
    哈萨克斯坦准噶尔板块 = "哈萨克斯坦-准噶尔板块"
    塔里木华北板块 = "塔里木-华北板块"
    旱山微板块 = "旱山微板块"
    敦煌微板块 = "敦煌微板块"
    觉罗塔格晚古生代岛弧 = "觉罗塔格晚古生代岛弧"
    北山断褶带 = "北山断褶带"

class OreStructureEnum(str, Enum):
    """矿石结构枚举（论文核心类型）"""
    自形结构 = "自形结构"
    半自形结构 = "半自形结构"
    他形结构 = "他形-半自形粒状结构"
    碎裂结构 = "碎裂结构"
    碎斑胶结结构 = "碎斑胶结结构"
    陨铁结构 = "陨铁结构"

# ========== 通用基础模型 ==========
class GeoBaseModel(BaseModel):
    """所有地质实体的通用基础模型"""
    name: str = Field(..., description="地质实体名称，如黄山铜镍矿床、闪长岩、萤石")
    code: Optional[str] = Field(None, description="地质实体编码（可选）")
    source: Optional[str] = Field(None, description="数据来源，如XX论文、XX地质报告")

# ========== 六大核心地质实体（均含 entity_type 鉴别器）==========
class Deposit(GeoBaseModel):
    """矿床实体（论文顶级核心概念）"""
    entity_type: Literal["矿床"] = "矿床"
    deposit_type: Optional[str] = Field(None, description="矿床类型，如铜镍矿床、金矿床")
    mineralization_type: Optional[str] = Field(None, description="成矿类型，如岩浆熔离-贯入型")
    shape: Optional[str] = Field(None, description="矿床形态，如透镜状、脉状")
    distribution: Optional[str] = Field(None, description="展布方向，如近东西向")
    area: Optional[str] = Field(None, description="矿床面积，如9.56km²")
    longitude: Optional[str] = Field(None, description="经度")
    latitude: Optional[str] = Field(None, description="纬度")
    location: Optional[str] = Field(None, description="地理位置，如东天山、北山")
    mineralization_age: Optional[str] = Field(None, description="成矿年代")
    tectonic_unit: Optional[str] = Field(None, description="大地构造单元")
    tectonic_location: Optional[str] = Field(None, description="大地构造位置")
    wall_rock_alteration: Optional[List[str]] = Field(None, description="围岩蚀变类型")
    dominant_elements: Optional[List[str]] = Field(None, description="主要成矿元素，如Cu、Ni")
    trace_elements: Optional[List[str]] = Field(None, description="微量元素")

class OreBody(GeoBaseModel):
    """矿体实体（矿床的组成部分）"""
    entity_type: Literal["矿体"] = "矿体"
    orebody_scale: Optional[str] = Field(None, description="矿体规模，如大型、中型、小型")
    grade: Optional[str] = Field(None, description="矿体品位，如Cu品位0.8%")
    length: Optional[str] = Field(None, description="矿体长度，如120m")
    thickness: Optional[str] = Field(None, description="矿体厚度，如5.6m")
    dip_angle: Optional[str] = Field(None, description="矿体倾角，如75°")
    occurrence: Optional[str] = Field(None, description="矿体产状，如陡倾、缓倾")
    host_rock: Optional[str] = Field(None, description="赋矿岩石")
    ore_structure: Optional[List[str]] = Field(None, description="矿石结构")

class Rock(GeoBaseModel):
    """岩石实体（成矿物质基础）"""
    entity_type: Literal["岩石"] = "岩石"
    rock_type: Optional[str] = Field(None, description="岩石类型，如岩浆岩、沉积岩、变质岩")
    rock_structure: Optional[str] = Field(None, description="岩石结构")
    rock_tectonic: Optional[str] = Field(None, description="岩石构造")
    lithology: Optional[str] = Field(None, description="岩性特征")

class Mineral(GeoBaseModel):
    """矿物实体（矿石组成部分）"""
    entity_type: Literal["矿物"] = "矿物"
    mineral_type: Optional[str] = Field(None, description="矿物类型，如金属矿物、脉石矿物")
    color: Optional[List[str]] = Field(None, description="矿物颜色")
    hardness: Optional[str] = Field(None, description="莫氏硬度")
    density: Optional[str] = Field(None, description="矿物密度，如4.2g/cm³")
    mineral_association: Optional[List[str]] = Field(None, description="矿物组合")

class Stratum(GeoBaseModel):
    """地层实体（岩层序列）"""
    entity_type: Literal["地层"] = "地层"
    stratum_era: Optional[str] = Field(None, description="地层年代")
    stratum_type: Optional[str] = Field(None, description="地层类型")
    exposed_rock: Optional[List[str]] = Field(None, description="出露岩石类型")
    lithology_combination: Optional[str] = Field(None, description="岩性组合")

class GeoTectonic(GeoBaseModel):
    """地质构造实体（地壳运动形成的构造形态）"""
    entity_type: Literal["地质构造"] = "地质构造"
    tectonic_type: Optional[str] = Field(None, description="构造类型，如断裂、褶皱、韧性剪切带")
    tectonic_function: Optional[str] = Field(None, description="构造功能，如控矿构造")
    developed_rock: Optional[List[str]] = Field(None, description="发育岩石类型")
    associated_ore: Optional[List[str]] = Field(None, description="伴生矿床")

# ========== 鉴别联合类型 ==========
GeoEntity = Annotated[
    Union[Deposit, OreBody, Rock, Mineral, Stratum, GeoTectonic],
    Discriminator("entity_type")
]

# ========== 关系模型 ==========
class GeoRelationEnum(str, Enum):
    """地质细分关系枚举（39种，参考论文）"""
    # 包含关系
    包含 = "包含"
    分别为 = "分别为"
    赋存于 = "赋存于"
    # 空间关系
    位于 = "位于"
    展布于 = "展布于"
    分布于 = "分布于"
    顺序关系 = "顺序关系"
    度量关系 = "度量关系"
    # 时间关系
    晚于 = "晚于"
    同生成矿 = "同生成矿"
    后生成矿 = "后生成矿"
    成矿期为 = "成矿期为"
    形成于 = "形成于"
    # 属性关系
    成矿类型为 = "成矿类型为"
    矿石结构为 = "矿石结构为"
    矿石构造为 = "矿石构造为"
    形态为 = "形态为"
    颜色为 = "颜色为"
    长度为 = "长度为"
    倾角为 = "倾角为"
    厚度为 = "厚度为"
    面积为 = "面积为"
    品位为 = "品位为"
    属于 = "属于"
    含有 = "含有"
    为 = "为"
    地质年代为 = "地质年代为"
    # 功能关系
    发育 = "发育"
    控矿构造为 = "控矿构造为"
    受控于 = "受控于"
    围岩蚀变为 = "围岩蚀变为"
    岩性为 = "岩性为"
    主要矿物为 = "主要矿物为"
    次要矿物为 = "次要矿物为"
    金属矿物为 = "金属矿物为"
    脉石矿物为 = "脉石矿物为"
    矿石矿物为 = "矿石矿物为"
    地层为 = "地层为"
    出露 = "出露"
    大地构造单元为 = "大地构造单元为"
    主要元素为 = "主要元素为"
    微量元素为 = "微量元素为"
    矿物组合为 = "矿物组合为"
    # 语义关系
    层次关系 = "层次关系"

# 标准关系名称集合（用于快速查找）
_VALID_RELATION_NAMES = frozenset(e.value for e in GeoRelationEnum)

class GeoRelationBase(BaseModel):
    """地质关系基础模型"""
    relation_name: str = Field(..., description="细分关系名称，参考GeoRelationEnum")
    relation_type: Optional[str] = Field(None, description="基础关系类型：空间/时间/包含/属性/功能/语义关系")
    subject: str = Field(..., description="关系主体")
    object: str = Field(..., description="关系客体")
    source: Optional[str] = Field(None, description="关系来源")

# ========== 三元组模型 ==========
class GeoTriple(BaseModel):
    """找矿知识图谱三元组模型（LLM抽取最终格式）"""
    subject_entity: GeoEntity = Field(..., description="主体实体")
    relation: GeoRelationBase = Field(..., description="关系")
    object_entity: GeoEntity = Field(..., description="客体实体")
