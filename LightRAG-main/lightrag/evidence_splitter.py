# Evidence 证据链增强 - 场景标签与自定义切分模块
"""
Evidence 语料库的场号标签体系和自定义切分器。

提供基于业务逻辑的精细化语料切分，支持多行业场景：

## 金融行业
- 投研分析、风险控制、合规审核、产品设计、市场研判、政策法规
- 金融、银行、保险、证券、基金、投资

## 医疗健康行业  [NEW]
- 医疗健康、医药、医疗器械、公共卫生

## 城市治理行业  [NEW]
- 城市治理、智慧城市、公共服务、应急管理

## 教育行业  [NEW]
- 教育、职业教育、教育科技

## 工业制造行业  [NEW]
- 工业制造、供应链、质量管理、智能制造

## 能源行业  [NEW]
- 能源、电力、新能源

## 农业行业  [NEW]
- 农业、食品安全、乡村振兴

## 法律行业  [NEW]
- 法律、司法、合规法律

## 媒体与通信  [NEW]
- 媒体、公共关系

## 环境保护  [NEW]
- 环境保护、生态、气候变化

## 交通运输  [NEW]
- 交通运输、物流、自动驾驶

## 房地产与建筑  [NEW]
- 房地产、建筑、物业管理

## 信息技术  [NEW]
- 信息技术、网络安全、数据隐私

## 商业零售  [NEW]
- 商业零售、电子商务、消费者保护

特性：
- 自动行业检测
- 行业特定切分逻辑
- 跨行业标签支持
- 证据等级管理
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class SceneCategory(str, Enum):
    """场景大类枚举"""

    INVESTMENT_RESEARCH = "投研分析"  # 权益/固收/量化
    RISK_CONTROL = "风险控制"  # 信贷/市场/操作
    COMPLIANCE = "合规审核"  # 反洗钱/监管
    PRODUCT_DESIGN = "产品设计"
    MARKET_RESEARCH = "市场研判"
    POLICY_REGULATION = "政策法规"  # 监管政策
    ACADEMIC_RESEARCH = "学术研究"  # 论文研究
    CASE_ANALYSIS = "案例分析"  # 处罚案例
    
    # ============ Cross-industry Extensions ============
    # 金融行业
    FINANCE = "金融"  # 银行/保险/证券/基金
    INVESTMENT = "投资"  # 股权投资/债权投资/并购
    
    # 医疗健康行业
    HEALTHCARE = "医疗健康"  # 医疗/医药/公共卫生
    PHARMACEUTICAL = "医药"  # 药物研发/临床/注册
    MEDICAL_DEVICE = "医疗器械"  # 设备/耗材/IVD
    PUBLIC_HEALTH = "公共卫生"  # 疾控/卫健/应急
    
    # 城市治理行业
    URBAN_GOVERNANCE = "城市治理"  # 城市管理/政务/公共服务
    SMART_CITY = "智慧城市"  # 数字政务/城市大脑
    PUBLIC_SERVICE = "公共服务"  # 市政/公用事业
    EMERGENCY_MANAGEMENT = "应急管理"  # 应急/消防/安防
    
    # 教育行业
    EDUCATION = "教育"  # 教育/培训/科研
    VOCATIONAL_TRAINING = "职业教育"  # 技能培训/产教融合
    EDU_TECH = "教育科技"  # 在线教育/智慧教育
    
    # 工业制造行业
    MANUFACTURING = "工业制造"  # 制造/生产/供应链
    SUPPLY_CHAIN = "供应链"  # 采购/物流/仓储
    QUALITY_CONTROL = "质量管理"  # QA/QC/标准化
    INDUSTRY_40 = "智能制造"  # 工业4.0/自动化/数字化
    
    # 能源行业
    ENERGY = "能源"  # 电力/油气/新能源
    POWER = "电力"  # 电网/发电/配电
    NEW_ENERGY = "新能源"  # 光伏/风电/储能
    
    # 农业行业
    AGRICULTURE = "农业"  # 农业/农村/食品安全
    FOOD_SAFETY = "食品安全"  # 检测/追溯/标准
    RURAL_DEV = "乡村振兴"  # 农村发展/扶贫
    
    # 法律行业
    LEGAL = "法律"  # 法律/司法/仲裁
    JUDICIAL = "司法"  # 法院/检察/公安
    COMPLIANCE_LEGAL = "合规法律"  # 法务/合规/风控
    
    # 媒体与通信
    MEDIA = "媒体"  # 传媒/舆情/内容
    PR = "公共关系"  # 品牌/公关/危机管理
    
    # 环境保护
    ENVIRONMENT = "环境保护"  # 环保/生态/应急
    ECOLOGY = "生态"  # 生态保护/自然资源
    CLIMATE = "气候变化"  # 双碳/减排/ESG
    
    # 交通运输
    TRANSPORTATION = "交通运输"  # 交通/物流/出行
    LOGISTICS = "物流"  # 快递/货运/仓储
    AUTONOMOUS = "自动驾驶"  # 车联网/智能交通
    
    # 房地产与建筑
    REAL_ESTATE = "房地产"  # 地产/建筑/物业
    CONSTRUCTION = "建筑"  # 工程/BIM/装配式
    PROPERTY = "物业管理"  # 物业/社区/资产
    
    # 信息技术
    TELECOM = "信息技术"  # IT/通信/互联网
    CYBERSECURITY = "网络安全"  # 信息安全/数据安全
    DATA_PRIVACY = "数据隐私"  # 数据保护/合规
    
    # 商业零售
    RETAIL = "商业零售"  # 零售/消费/电商
    E_COMMERCE = "电子商务"  # 电商平台/跨境电商
    CONSUMER = "消费者保护"  # 消费者权益/监管
    
    # 通用场景
    GENERAL = "通用"  # 通用/其他


# 场景标签映射表
SCENE_TAG_MAPPING: Dict[str, List[str]] = {
    # 投研分析
    "投研分析": [
        "权益投研",
        "固收投研",
        "量化分析",
        "行业研究",
        "个股研究",
        "债券研究",
    ],
    # 风险控制
    "风险控制": [
        "信贷风控",
        "市场风控",
        "操作风控",
        "信用风险",
        "流动性风险",
        "合规风险",
    ],
    # 合规审核
    "合规审核": ["反洗钱", "监管合规", "内控合规", "KYC", "AML", "合规审查"],
    # 产品设计
    "产品设计": ["理财产品", "基金产品", "保险产品", "结构化产品", "衍生品设计"],
    # 市场研判
    "市场研判": ["宏观经济", "行业趋势", "市场情绪", "资金流向", "政策解读"],
    # 政策法规
    "政策法规": ["监管政策", "法律法规", "行业规范", "指导意见", "管理办法"],
    # 学术研究
    "学术研究": ["实证研究", "理论研究", "案例研究", "文献综述", "方法论"],
    # 案例分析
    "案例分析": ["处罚案例", "典型案例", "风险事件", "处置案例", "合规案例"],
    
    # ============ Cross-industry Scene Tags ============
    # 金融行业
    "金融": ["银行", "保险", "证券", "基金", "信托", "期货", "租赁", "保理"],
    "投资": ["股权投资", "债权投资", "并购", "VC", "PE", "天使投资", "定增"],
    
    # 医疗健康行业
    "医疗健康": ["医疗服务", "医院", "诊所", "健康管理", "养老", "康复"],
    "医药": ["药物研发", "临床试验", "药品注册", "生产制造", "流通销售", "GMP"],
    "医疗器械": ["医疗设备", "耗材", "体外诊断", "植入物", "家用医疗", "数字医疗"],
    "公共卫生": ["疾病防控", "卫生监督", "应急疾控", "疫苗", "爱国卫生"],
    
    # 城市治理行业
    "城市治理": ["城市管理", "市政管理", "公共服务", "社会治理", "网格化管理"],
    "智慧城市": ["数字政务", "城市大脑", "智慧交通", "智慧环保", "智慧社区"],
    "公共服务": ["供水", "供电", "供气", "供热", "公共交通", "污水处理"],
    "应急管理": ["应急预案", "应急响应", "灾害救助", "消防安全", "安全生产"],
    
    # 教育行业
    "教育": ["学前教育", "基础教育", "高等教育", "继续教育", "特殊教育"],
    "职业教育": ["技能培训", "产教融合", "双师型", "1+X证书", "职业技能"],
    "教育科技": ["在线教育", "智慧教室", "学习平台", "AI教育", "教育信息化"],
    
    # 工业制造行业
    "工业制造": ["离散制造", "流程制造", "智能制造", "精益生产", "工业自动化"],
    "供应链": ["采购管理", "仓储物流", "供应商管理", "冷链", "跨境供应链"],
    "质量管理": ["质量体系", "ISO", "QC", "QA", "计量", "标准化"],
    "智能制造": ["工业4.0", "数字化车间", "MES", "PLC", "机器人", "工业互联网"],
    
    # 能源行业
    "能源": ["传统能源", "新能源", "能源管理", "能耗", "碳排放"],
    "电力": ["发电", "输电", "配电", "售电", "电网", "电力市场"],
    "新能源": ["光伏", "风电", "储能", "氢能", "核电", "分布式能源"],
    
    # 农业行业
    "农业": ["种植业", "养殖业", "农产品加工", "农业机械", "智慧农业"],
    "食品安全": ["质量检测", "溯源体系", "标准体系", "监管", "召回"],
    "乡村振兴": ["产业兴旺", "生态宜居", "乡风文明", "精准扶贫", "农村电商"],
    
    # 法律行业
    "法律": ["民商法", "刑法", "行政法", "经济法", "国际法", "知识产权"],
    "司法": ["审判", "检察", "公安", "仲裁", "调解", "公证"],
    "合规法律": ["法务", "合规", "尽职调查", "合同管理", "法律风险"],
    
    # 媒体与通信
    "媒体": ["传统媒体", "新媒体", "自媒体", "舆情监测", "内容管理"],
    "公共关系": ["品牌管理", "危机公关", "媒体关系", "社会责任", "ESG传播"],
    
    # 环境保护
    "环境保护": ["污染防治", "生态保护", "环境影响评价", "环保督察"],
    "生态": ["生态保护", "自然资源", "生物多样性", "湿地保护", "荒漠化治理"],
    "气候变化": ["碳达峰", "碳中和", "减排", "ESG", "碳交易", "绿色金融"],
    
    # 交通运输
    "交通运输": ["公路", "铁路", "航空", "航运", "城市交通", "综合交通"],
    "物流": ["快递", "货运", "仓储", "多式联运", "智慧物流"],
    "自动驾驶": ["车联网", "智能驾驶", "高精地图", "V2X", "智能交通"],
    
    # 房地产与建筑
    "房地产": ["住宅地产", "商业地产", "工业地产", "养老地产", "文旅地产"],
    "建筑": ["房屋建筑", "市政工程", "BIM", "装配式", "工程监理"],
    "物业管理": ["住宅物业", "商业物业", "资产运营", "社区服务", "设施管理"],
    
    # 信息技术
    "信息技术": ["软件开发", "系统集成", "IT服务", "云计算", "大数据", "人工智能"],
    "网络安全": ["信息安全", "数据安全", "主机安全", "应用安全", "安全运营"],
    "数据隐私": ["个人信息保护", "数据合规", "GDPR", "数据跨境", "隐私计算"],
    
    # 商业零售
    "商业零售": ["实体零售", "连锁经营", "品牌零售", "渠道管理", "客户体验"],
    "电子商务": ["电商平台", "跨境电商", "社交电商", "直播电商", "社区团购"],
    "消费者保护": ["消费者权益", "投诉处理", "售后", "七天无理由", "三包"],
    
    # 通用场景
    "通用": ["通用场景", "综合", "其他"],
}


@dataclass
class EvidenceChunk:
    """证据块数据结构"""

    content: str  # 证据内容
    chunk_index: int  # 块索引
    scene_category: SceneCategory  # 场景大类
    scene_tags: List[str] = field(default_factory=list)  # 场景标签
    provenance: Optional[Dict] = None  # 溯源信息
    evidence_level: str = "B"  # 证据等级
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    # Cross-industry support fields
    industry: str = ""  # 行业领域 (医疗/金融/城市治理/教育等)
    sub_industry: str = ""  # 子行业
    cross_domain_tags: List[str] = field(default_factory=list)  # 跨域标签


class EvidenceSplitter:
    """基于业务逻辑的证据切分器"""

    def __init__(self, scene_type: Optional[str] = None):
        """
        初始化切分器。

        Args:
            scene_type: 场景类型，如不指定则自动检测
        """
        self.scene_type = scene_type

    def split(
        self,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> List[EvidenceChunk]:
        """
        根据场景类型切分文本。

        Args:
            text: 待切分文本
            metadata: 元数据，包含 file_path, page_num 等

        Returns:
            证据块列表
        """
        metadata = metadata or {}

        # 自动检测场景类型
        scene_type = self.scene_type or self._detect_scene_type(text, metadata)

        # 根据场景类型选择切分方法
        if scene_type == "政策法规":
            return self._split_policy(text, metadata)
        elif scene_type == "投研报告":
            return self._split_research_report(text, metadata)
        elif scene_type == "学术论文":
            return self._split_academic_paper(text, metadata)
        elif scene_type == "案例分析":
            return self._split_case_analysis(text, metadata)
        elif scene_type == "市场数据":
            return self._split_market_data(text, metadata)
        
        # ============ Cross-industry Splitting ============
        # 医疗健康行业
        elif scene_type in ["医疗健康", "医药", "医疗器械", "公共卫生"]:
            return self._split_healthcare(text, metadata, scene_type)
        
        # 城市治理行业
        elif scene_type in ["城市治理", "智慧城市", "公共服务", "应急管理"]:
            return self._split_urban_governance(text, metadata, scene_type)
        
        # 教育行业
        elif scene_type in ["教育", "职业教育", "教育科技"]:
            return self._split_education(text, metadata, scene_type)
        
        # 工业制造行业
        elif scene_type in ["工业制造", "供应链", "质量管理", "智能制造"]:
            return self._split_manufacturing(text, metadata, scene_type)
        
        # 能源行业
        elif scene_type in ["能源", "电力", "新能源"]:
            return self._split_energy(text, metadata, scene_type)
        
        # 农业行业
        elif scene_type in ["农业", "食品安全", "乡村振兴"]:
            return self._split_agriculture(text, metadata, scene_type)
        
        # 法律行业
        elif scene_type in ["法律", "司法", "合规法律"]:
            return self._split_legal(text, metadata, scene_type)
        
        # 媒体与通信
        elif scene_type in ["媒体", "公共关系"]:
            return self._split_media(text, metadata, scene_type)
        
        # 环境保护
        elif scene_type in ["环境保护", "生态", "气候变化"]:
            return self._split_environment(text, metadata, scene_type)
        
        # 交通运输
        elif scene_type in ["交通运输", "物流", "自动驾驶"]:
            return self._split_transportation(text, metadata, scene_type)
        
        # 房地产与建筑
        elif scene_type in ["房地产", "建筑", "物业管理"]:
            return self._split_real_estate(text, metadata, scene_type)
        
        # 信息技术
        elif scene_type in ["信息技术", "网络安全", "数据隐私"]:
            return self._split_it(text, metadata, scene_type)
        
        # 商业零售
        elif scene_type in ["商业零售", "电子商务", "消费者保护"]:
            return self._split_retail(text, metadata, scene_type)
        
        # 金融行业
        elif scene_type in ["金融", "投资"]:
            return self._split_finance(text, metadata, scene_type)
        
        else:
            return self._split_default(text, metadata)

    def _detect_scene_type(self, text: str, metadata: Dict) -> str:
        """自动检测场景类型"""
        # 基于文件扩展名检测
        file_path = metadata.get("file_path", "")
        if file_path:
            file_lower = file_path.lower()
            if (
                "policy" in file_lower
                or "regulation" in file_lower
                or "办法" in file_lower
                or "条例" in file_lower
            ):
                return "政策法规"
            if "research" in file_lower or "研报" in file_lower or "报告" in file_lower:
                return "投研报告"
            if "paper" in file_lower or "论文" in file_lower or "journal" in file_lower:
                return "学术论文"
            if "case" in file_lower or "案例" in file_lower or "处罚" in file_lower:
                return "案例分析"

        # 基于内容关键词检测
        text_sample = text[:500]
        if any(
            kw in text_sample
            for kw in ["第", "条", "第一章", "第二章", "办法", "条例", "规定"]
        ):
            return "政策法规"
        if any(
            kw in text_sample
            for kw in ["研究表明", "研究发现", "数据表明", "分析师认为"]
        ):
            return "投研报告"
        if any(kw in text_sample for kw in ["本文", "研究方法", "实证结果", "结论"]):
            return "学术论文"
        if any(kw in text_sample for kw in ["处罚", "违规", "罚款", "行政"]):
            return "案例分析"
        
        # ============ Cross-industry Detection ============
        # 医疗健康行业检测
        if any(kw in text_sample for kw in ["医院", "医生", "患者", "诊疗", "治疗", "手术", "药品", "药物", "临床", "医疗器械", "公共卫生", "疾控", "疫苗"]):
            return "医疗健康"
        
        # 城市治理行业检测
        if any(kw in text_sample for kw in ["城市管理", "政务服务", "智慧城市", "城市大脑", "网格化", "应急管理", "安全生产", "消防", "防汛", "市政"]):
            return "城市治理"
        
        # 教育行业检测
        if any(kw in text_sample for kw in ["学校", "教育", "学生", "教师", "教学", "课程", "培训", "职业教育", "高等教育", "基础教育"]):
            return "教育"
        
        # 工业制造行业检测
        if any(kw in text_sample for kw in ["制造", "生产", "工厂", "供应链", "采购", "质量", "MES", "工业4.0", "智能制造", "自动化"]):
            return "工业制造"
        
        # 能源行业检测
        if any(kw in text_sample for kw in ["电力", "能源", "发电", "电网", "光伏", "风电", "储能", "油气", "新能源", "碳排放"]):
            return "能源"
        
        # 农业行业检测
        if any(kw in text_sample for kw in ["农业", "农村", "农产品", "种植", "养殖", "粮食", "食品安全", "乡村振兴", "扶贫"]):
            return "农业"
        
        # 法律行业检测
        if any(kw in text_sample for kw in ["法院", "判决", "诉讼", "律师", "法律", "司法", "仲裁", "调解", "合规", "法务"]):
            return "法律"
        
        # 媒体与通信检测
        if any(kw in text_sample for kw in ["媒体", "舆情", "新闻", "报道", "公关", "品牌", "传播", "新媒体"]):
            return "媒体"
        
        # 环境保护检测
        if any(kw in text_sample for kw in ["环保", "污染", "生态", "碳中和", "ESG", "减排", "气候变化", "节能", "减排"]):
            return "环境保护"
        
        # 交通运输检测
        if any(kw in text_sample for kw in ["交通", "物流", "运输", "货运", "快递", "港口", "机场", "铁路", "公路", "自动驾驶", "车联网"]):
            return "交通运输"
        
        # 房地产与建筑检测
        if any(kw in text_sample for kw in ["房地产", "地产", "建筑", "施工", "物业", "拆迁", "BIM", "工程"]):
            return "房地产"
        
        # 信息技术检测
        if any(kw in text_sample for kw in ["软件", "系统", "IT", "网络", "数据", "云计算", "AI", "人工智能", "网络安全", "信息安全"]):
            return "信息技术"
        
        # 商业零售检测
        if any(kw in text_sample for kw in ["零售", "电商", "销售", "消费者", "店铺", "超市", "购物", "订单", "商品"]):
            return "商业零售"
        
        # 金融行业检测
        if any(kw in text_sample for kw in ["银行", "保险", "证券", "基金", "投资", "理财", "贷款", "金融", "风控", "合规"]):
            return "金融"
        
        return "通用"

        return "通用"

    def _split_policy(self, text: str, metadata: Dict) -> List[EvidenceChunk]:
        """政策法规类：按条款/子目切分"""
        chunks = []

        # 匹配条款模式：第X条、第X章、第X款
        patterns = [
            r"第[一二三四五六七八九十百千\d]+条",  # 第1条
            r"第[一二三四五六七八九十百千\d]+章",  # 第一章
            r"第[一二三四五六七八九十百千\d]+款",  # 第一款
            r"（[一二三四五六七八九十\d]+）",  # （一）
        ]

        # 简单的段落分割
        paragraphs = re.split(r"\n+", text)
        current_chunk = []
        chunk_index = 0

        for para in paragraphs:
            if not para.strip():
                continue
            current_chunk.append(para)

            # 如果包含条款编号，作为独立证据单元
            if any(re.search(p, para) for p in patterns):
                if current_chunk:
                    content = "\n".join(current_chunk)
                    chunks.append(
                        EvidenceChunk(
                            content=content,
                            chunk_index=chunk_index,
                            scene_category=SceneCategory.POLICY_REGULATION,
                            scene_tags=["政策法规", "条款"],
                            evidence_level=self._determine_evidence_level(metadata),
                            metadata=metadata,
                        )
                    )
                    chunk_index += 1
                    current_chunk = []

        # 处理剩余内容
        if current_chunk:
            content = "\n".join(current_chunk)
            if content.strip():
                chunks.append(
                    EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.POLICY_REGULATION,
                        scene_tags=["政策法规"],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    )
                )

        return chunks

    def _split_research_report(self, text: str, metadata: Dict) -> List[EvidenceChunk]:
        """投研报告类：按观点+论据切分"""
        chunks = []

        # 匹配观点模式
        patterns = [
            r"我们认为",
            r"分析师认为",
            r"研究显示",
            r"数据显示",
            r"预期",
            r"展望",
            r"投资建议",
            r"风险提示",
        ]

        paragraphs = re.split(r"\n+", text)
        current_content = []
        current_tags = []
        chunk_index = 0

        for para in paragraphs:
            if not para.strip():
                continue

            # 检测是否包含观点关键词
            matched = False
            for p in patterns:
                if re.search(p, para):
                    matched = True
                    break

            if matched and current_content:
                # 保存之前的块
                chunks.append(
                    EvidenceChunk(
                        content="\n".join(current_content),
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.INVESTMENT_RESEARCH,
                        scene_tags=current_tags if current_tags else ["投研分析"],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    )
                )
                chunk_index += 1
                current_content = []
                current_tags = []

            current_content.append(para)

            # 添加场景标签
            if "风险" in para or "风控" in para:
                current_tags.append("风险控制")
            if "合规" in para or "监管" in para:
                current_tags.append("合规审核")

        # 处理剩余内容
        if current_content:
            chunks.append(
                EvidenceChunk(
                    content="\n".join(current_content),
                    chunk_index=chunk_index,
                    scene_category=SceneCategory.INVESTMENT_RESEARCH,
                    scene_tags=current_tags if current_tags else ["投研分析"],
                    evidence_level=self._determine_evidence_level(metadata),
                    metadata=metadata,
                )
            )

        return chunks

    def _split_academic_paper(self, text: str, metadata: Dict) -> List[EvidenceChunk]:
        """学术论文类：按研究结论/方法切分"""
        chunks = []

        patterns = [
            r"研究结论",
            r"本文结论",
            r"实证结果",
            r"研究发现",
            r"研究方法",
            r"数据来源",
        ]

        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0

        for para in paragraphs:
            if not para.strip():
                continue

            current_content.append(para)

            # 检测研究相关关键词
            if any(re.search(p, para) for p in patterns):
                chunks.append(
                    EvidenceChunk(
                        content="\n".join(current_content),
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.ACADEMIC_RESEARCH,
                        scene_tags=["学术研究"],
                        evidence_level="A",  # 论文默认 A 级
                        metadata=metadata,
                    )
                )
                chunk_index += 1
                current_content = []

        if current_content:
            chunks.append(
                EvidenceChunk(
                    content="\n".join(current_content),
                    chunk_index=chunk_index,
                    scene_category=SceneCategory.ACADEMIC_RESEARCH,
                    scene_tags=["学术研究"],
                    evidence_level="A",
                    metadata=metadata,
                )
            )

        return chunks

    def _split_case_analysis(self, text: str, metadata: Dict) -> List[EvidenceChunk]:
        """案例分析类：按案例核心事实/违规点/处罚结果切分"""
        chunks = []

        patterns = [
            r"违规事实",
            r"违规行为",
            r"处罚结果",
            r"行政处罚",
            r"罚款",
            r"监管依据",
        ]

        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0

        for para in paragraphs:
            if not para.strip():
                continue

            current_content.append(para)

            if any(re.search(p, para) for p in patterns):
                chunks.append(
                    EvidenceChunk(
                        content="\n".join(current_content),
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.CASE_ANALYSIS,
                        scene_tags=["案例分析"],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    )
                )
                chunk_index += 1
                current_content = []

        if current_content:
            chunks.append(
                EvidenceChunk(
                    content="\n".join(current_content),
                    chunk_index=chunk_index,
                    scene_category=SceneCategory.CASE_ANALYSIS,
                    scene_tags=["案例分析"],
                    evidence_level=self._determine_evidence_level(metadata),
                    metadata=metadata,
                )
            )

        return chunks

    def _split_market_data(self, text: str, metadata: Dict) -> List[EvidenceChunk]:
        """市场数据类：按数据指标/结论切分"""
        chunks = []

        # 匹配数据模式
        pattern = r"\d+\.?\d*[%亿万元]?"

        paragraphs = re.split(r"\n+", text)

        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue

            # 如果包含数据，作为独立证据单元
            if re.search(pattern, para):
                chunks.append(
                    EvidenceChunk(
                        content=para,
                        chunk_index=i,
                        scene_category=SceneCategory.MARKET_RESEARCH,
                        scene_tags=["市场数据"],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    )
                )

        return chunks

    # ============ Cross-industry Splitting Methods ============
    
    def _split_healthcare(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """医疗健康类：按诊疗环节/药品信息/临床数据切分"""
        chunks = []
        patterns = [
            r"诊断|治疗|手术|用药|处方|病历",
            r"临床试验|临床研究|GMP",
            r"药品|药物|制剂|原料",
            r"医疗器械|设备|耗材",
            r"公共卫生|疾控|疫苗",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.HEALTHCARE,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.HEALTHCARE,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_urban_governance(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """城市治理类：按治理事项/应急事件/服务事项切分"""
        chunks = []
        patterns = [
            r"城市管理|市政|公用",
            r"政务服务|行政办事|窗口",
            r"应急预案|应急响应|灾害",
            r"安全生产|消防|安防",
            r"网格化|社区|街道",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.URBAN_GOVERNANCE,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.URBAN_GOVERNANCE,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_education(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """教育类：按教学环节/课程内容/评估结果切分"""
        chunks = []
        patterns = [
            r"教学|课程|教材|课件",
            r"学生|教师|师资|培训",
            r"考试|评估|考核|测评",
            r"学校|学院|机构|培训",
            r"职业教育|技能|产教融合",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.EDUCATION,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.EDUCATION,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_manufacturing(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """工业制造类：按生产工序/质量控制/供应链切分"""
        chunks = []
        patterns = [
            r"生产|制造|加工|工艺",
            r"质量|检测|标准|ISO",
            r"供应链|采购|物流|仓储",
            r"设备|维护|保养|检修",
            r"MES|工业4.0|自动化",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.MANUFACTURING,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.MANUFACTURING,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_energy(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """能源类：按能源类型/发电环节/电网运行切分"""
        chunks = []
        patterns = [
            r"发电|输电|配电|售电",
            r"光伏|风电|储能|氢能",
            r"电网|调度|运行",
            r"油气|勘探|开采",
            r"碳排放|能耗|节能",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.ENERGY,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.ENERGY,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_agriculture(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """农业类：按农业生产/食品安全/农村发展切分"""
        chunks = []
        patterns = [
            r"种植|养殖|农业",
            r"农产品|粮食|蔬菜",
            r"食品安全|检测|溯源",
            r"农村|农民|扶贫",
            r"乡村振兴|农业现代化",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.AGRICULTURE,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.AGRICULTURE,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_legal(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """法律类：按案件事实/法律依据/裁判结果切分"""
        chunks = []
        patterns = [
            r"原告|被告|上诉人|被上诉人",
            r"法院|判决|裁定|调解",
            r"法律依据|条款|法规",
            r"诉讼|仲裁|争议",
            r"合规|法务|风控",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.LEGAL,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.LEGAL,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_media(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """媒体类：按新闻要素/舆情事件/传播效果切分"""
        chunks = []
        patterns = [
            r"新闻|报道|采访",
            r"舆情|热点|事件",
            r"传播|转发|评论",
            r"公关|品牌|危机",
            r"新媒体|自媒体|短视频",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.MEDIA,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.MEDIA,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_environment(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """环境保护类：按环境要素/治理措施/监测数据切分"""
        chunks = []
        patterns = [
            r"污染|排放|废气|废水",
            r"生态|保护|修复",
            r"碳中和|碳达峰|减排",
            r"节能|降耗|环保",
            r"监测|检测|治理",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.ENVIRONMENT,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.ENVIRONMENT,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_transportation(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """交通运输类：按运输方式/运营管理/安全监管切分"""
        chunks = []
        patterns = [
            r"铁路|公路|航空|航运",
            r"物流|货运|快递",
            r"交通|道路|桥梁",
            r"自动驾驶|车联网|V2X",
            r"安全|监管|运营",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.TRANSPORTATION,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.TRANSPORTATION,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_real_estate(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """房地产与建筑类：按项目阶段/工程内容/物业管理切分"""
        chunks = []
        patterns = [
            r"地产|房地产|项目",
            r"施工|建筑|工程",
            r"物业|管理|服务",
            r"拆迁|征收|土地",
            r"BIM|设计|规划",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.REAL_ESTATE,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.REAL_ESTATE,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_it(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """信息技术类：按系统架构/安全防护/数据管理切分"""
        chunks = []
        patterns = [
            r"软件|系统|平台",
            r"网络|安全|防护",
            r"数据|存储|处理",
            r"云|计算|AI",
            r"开发|部署|运维",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.TELECOM,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.TELECOM,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_retail(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """商业零售类：按商品信息/销售数据/客户服务切分"""
        chunks = []
        patterns = [
            r"商品|产品|SKU",
            r"销售|订单|营收",
            r"客户|消费者|会员",
            r"店铺|门店|渠道",
            r"电商|平台|直播",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.RETAIL,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.RETAIL,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks
    
    def _split_finance(self, text: str, metadata: Dict, scene_type: str) -> List[EvidenceChunk]:
        """金融类：按金融产品/投资策略/风险控制切分"""
        chunks = []
        patterns = [
            r"银行|保险|证券",
            r"基金|理财|投资",
            r"贷款|融资|信贷",
            r"风控|风险|合规",
            r"交易|结算|清算",
        ]
        paragraphs = re.split(r"\n+", text)
        current_content = []
        chunk_index = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            current_content.append(para)
            
            if any(re.search(p, para) for p in patterns):
                if current_content:
                    content = "\n".join(current_content)
                    chunks.append(EvidenceChunk(
                        content=content,
                        chunk_index=chunk_index,
                        scene_category=SceneCategory.FINANCE,
                        scene_tags=[scene_type],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_content = []
        
        if current_content:
            chunks.append(EvidenceChunk(
                content="\n".join(current_content),
                chunk_index=chunk_index,
                scene_category=SceneCategory.FINANCE,
                scene_tags=[scene_type],
                evidence_level=self._determine_evidence_level(metadata),
                metadata=metadata,
            ))
        return chunks

    def _determine_evidence_level(self, metadata: Dict) -> str:
        """根据元数据确定证据等级"""
        # 从元数据中获取
        if "evidence_level" in metadata:
            return metadata["evidence_level"]

        # 根据文件来源推断
        file_path = metadata.get("file_path", "").lower()

        if "监管" in file_path or "央行" in file_path or "证监会" in file_path:
            return "S"
        if "研报" in file_path or "wind" in file_path or "bloomberg" in file_path:
            return "A"
        if "论文" in file_path or "journal" in file_path:
            return "A"

        return "B"  # 默认


def get_scene_tags(scene_category: str) -> List[str]:
    """获取场景类别下的所有标签"""
    return SCENE_TAG_MAPPING.get(scene_category, [])


def detect_scene_from_text(text: str) -> str:
    """从文本内容检测场景类型"""
    splitter = EvidenceSplitter()
    return splitter._detect_scene_type(text, {})


# ============ Cross-industry Helper Functions ============

# Industry classification mapping
INDUSTRY_MAPPING: Dict[str, List[str]] = {
    "金融": ["投研分析", "风险控制", "合规审核", "产品设计", "市场研判", "政策法规", "金融", "投资"],
    "医疗健康": ["医疗健康", "医药", "医疗器械", "公共卫生"],
    "城市治理": ["城市治理", "智慧城市", "公共服务", "应急管理"],
    "教育": ["教育", "职业教育", "教育科技"],
    "工业制造": ["工业制造", "供应链", "质量管理", "智能制造"],
    "能源": ["能源", "电力", "新能源"],
    "农业": ["农业", "食品安全", "乡村振兴"],
    "法律": ["法律", "司法", "合规法律"],
    "媒体": ["媒体", "公共关系"],
    "环境保护": ["环境保护", "生态", "气候变化"],
    "交通运输": ["交通运输", "物流", "自动驾驶"],
    "房地产": ["房地产", "建筑", "物业管理"],
    "信息技术": ["信息技术", "网络安全", "数据隐私"],
    "商业零售": ["商业零售", "电子商务", "消费者保护"],
}


def get_industry_from_scene(scene_type: str) -> str:
    """
    根据场景类型获取所属行业。
    
    Args:
        scene_type: 场景类型，如 "医疗健康", "城市治理", "智慧城市" 等
        
    Returns:
        行业名称，如 "医疗健康", "城市治理" 等
    """
    for industry, scenes in INDUSTRY_MAPPING.items():
        if scene_type in scenes:
            return industry
    return "通用"


def get_all_industries() -> List[str]:
    """获取所有支持行业列表"""
    return list(INDUSTRY_MAPPING.keys())


def get_scenes_by_industry(industry: str) -> List[str]:
    """
    根据行业获取所有相关场景类型。
    
    Args:
        industry: 行业名称
        
    Returns:
        场景类型列表
    """
    return INDUSTRY_MAPPING.get(industry, [])


def is_cross_industry_compatible(scene_type1: str, scene_type2: str) -> bool:
    """
    判断两个场景类型是否跨行业兼容（可用于跨行业检索）。
    
    Args:
        scene_type1: 场景类型1
        scene_type2: 场景类型2
        
    Returns:
        是否兼容
    """
    industry1 = get_industry_from_scene(scene_type1)
    industry2 = get_industry_from_scene(scene_type2)
    return industry1 == industry2 or industry1 == "通用" or industry2 == "通用"


def create_evidence_chunk_with_industry(
    content: str,
    chunk_index: int,
    scene_type: str,
    scene_tags: List[str] = None,
    evidence_level: str = "B",
    metadata: Dict = None,
) -> EvidenceChunk:
    """
    创建带有行业信息的证据块。
    
    Args:
        content: 证据内容
        chunk_index: 块索引
        scene_type: 场景类型
        scene_tags: 场景标签列表
        evidence_level: 证据等级
        metadata: 元数据
        
    Returns:
        EvidenceChunk对象
    """
    # Map scene_type to SceneCategory enum
    scene_category_map = {
        "投研分析": SceneCategory.INVESTMENT_RESEARCH,
        "风险控制": SceneCategory.RISK_CONTROL,
        "合规审核": SceneCategory.COMPLIANCE,
        "产品设计": SceneCategory.PRODUCT_DESIGN,
        "市场研判": SceneCategory.MARKET_RESEARCH,
        "政策法规": SceneCategory.POLICY_REGULATION,
        "学术研究": SceneCategory.ACADEMIC_RESEARCH,
        "案例分析": SceneCategory.CASE_ANALYSIS,
        # Cross-industry
        "金融": SceneCategory.FINANCE,
        "投资": SceneCategory.INVESTMENT,
        "医疗健康": SceneCategory.HEALTHCARE,
        "医药": SceneCategory.PHARMACEUTICAL,
        "医疗器械": SceneCategory.MEDICAL_DEVICE,
        "公共卫生": SceneCategory.PUBLIC_HEALTH,
        "城市治理": SceneCategory.URBAN_GOVERNANCE,
        "智慧城市": SceneCategory.SMART_CITY,
        "公共服务": SceneCategory.PUBLIC_SERVICE,
        "应急管理": SceneCategory.EMERGENCY_MANAGEMENT,
        "教育": SceneCategory.EDUCATION,
        "职业教育": SceneCategory.VOCATIONAL_TRAINING,
        "教育科技": SceneCategory.EDU_TECH,
        "工业制造": SceneCategory.MANUFACTURING,
        "供应链": SceneCategory.SUPPLY_CHAIN,
        "质量管理": SceneCategory.QUALITY_CONTROL,
        "智能制造": SceneCategory.INDUSTRY_40,
        "能源": SceneCategory.ENERGY,
        "电力": SceneCategory.POWER,
        "新能源": SceneCategory.NEW_ENERGY,
        "农业": SceneCategory.AGRICULTURE,
        "食品安全": SceneCategory.FOOD_SAFETY,
        "乡村振兴": SceneCategory.RURAL_DEV,
        "法律": SceneCategory.LEGAL,
        "司法": SceneCategory.JUDICIAL,
        "合规法律": SceneCategory.COMPLIANCE_LEGAL,
        "媒体": SceneCategory.MEDIA,
        "公共关系": SceneCategory.PR,
        "环境保护": SceneCategory.ENVIRONMENT,
        "生态": SceneCategory.ECOLOGY,
        "气候变化": SceneCategory.CLIMATE,
        "交通运输": SceneCategory.TRANSPORTATION,
        "物流": SceneCategory.LOGISTICS,
        "自动驾驶": SceneCategory.AUTONOMOUS,
        "房地产": SceneCategory.REAL_ESTATE,
        "建筑": SceneCategory.CONSTRUCTION,
        "物业管理": SceneCategory.PROPERTY,
        "信息技术": SceneCategory.TELECOM,
        "网络安全": SceneCategory.CYBERSECURITY,
        "数据隐私": SceneCategory.DATA_PRIVACY,
        "商业零售": SceneCategory.RETAIL,
        "电子商务": SceneCategory.E_COMMERCE,
        "消费者保护": SceneCategory.CONSUMER,
        "通用": SceneCategory.GENERAL,
    }
    
    scene_category = scene_category_map.get(scene_type, SceneCategory.GENERAL)
    industry = get_industry_from_scene(scene_type)
    
    return EvidenceChunk(
        content=content,
        chunk_index=chunk_index,
        scene_category=scene_category,
        scene_tags=scene_tags or [],
        evidence_level=evidence_level,
        metadata=metadata or {},
        industry=industry,
        sub_industry=scene_type,
        cross_domain_tags=[],
    )



# ============ LightRAG Integration ============


def evidence_chunking_func(
    tokenizer,
    content: str,
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    chunk_overlap_token_size: int = 100,
    chunk_token_size: int = 1200,
    scene_type: str | None = None,
    metadata: dict | None = None,
) -> list[dict]:
    """
    LightRAG 兼容的证据链分块函数。

    Args:
        tokenizer: LightRAG 的 tokenizer
        content: 待分块文本
        split_by_character: 按特定字符分割
        split_by_character_only: 仅按字符分割
        chunk_overlap_token_size: 重叠 token 数
        chunk_token_size: 每块 token 数
        scene_type: 场景类型（可选，不指定则自动检测）
        metadata: 元数据（如 file_path, page_num 等）

    Returns:
        符合 LightRAG 要求的 dict 列表
    """
    import re
    from typing import Dict, List

    metadata = metadata or {}

    # 如果指定了 scene_type，直接使用
    if scene_type:
        splitter = EvidenceSplitter(scene_type=scene_type)
        chunks = splitter.split(content, metadata)
        return [
            {
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "scene_category": chunk.scene_category.value if hasattr(chunk.scene_category, 'value') else str(chunk.scene_category),
                "scene_tags": chunk.scene_tags,
                "evidence_level": chunk.evidence_level,
                "source_provenance": chunk.provenance or {},
                "industry": chunk.industry,
                "sub_industry": chunk.sub_industry,
            }
            for chunk in chunks
        ]

    # 自动检测场景类型
    splitter = EvidenceSplitter()
    detected_scene = splitter._detect_scene_type(content, metadata)

    # 根据场景类型分块
    if detected_scene:
        splitter = EvidenceSplitter(scene_type=detected_scene)
        chunks = splitter.split(content, metadata)
        return [
            {
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "scene_category": chunk.scene_category.value if hasattr(chunk.scene_category, 'value') else str(chunk.scene_category),
                "scene_tags": chunk.scene_tags,
                "evidence_level": chunk.evidence_level,
                "source_provenance": chunk.provenance or {},
                "industry": chunk.industry,
                "sub_industry": chunk.sub_industry,
            }
            for chunk in chunks
        ]

    # 如果无法检测场景类型，回退到默认分块方式
    from lightrag.utils import chunking_by_token_size

    # 调用默认分块函数
    default_chunks = chunking_by_token_size(
        tokenizer,
        content,
        split_by_character,
        split_by_character_only,
        chunk_overlap_token_size,
        chunk_token_size,
    )

    # 添加默认证据字段
    return [
        {
            **chunk,
            "scene_tags": ["通用"],
            "evidence_level": "B",
            "scene_category": "general",
            "provenance": {},
            "industry": "通用",
            "sub_industry": "通用",
        }
        for chunk in default_chunks
    ]