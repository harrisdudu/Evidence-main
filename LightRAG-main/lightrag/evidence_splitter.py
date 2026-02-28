# Evidence 证据链增强 - 场景标签与自定义切分模块
"""
Evidence 语料库的场号标签体系和自定义切分器。

提供基于业务逻辑的精细化语料切分，支持：
- 监管政策类
- 投研报告类
- 学术论文类
- 处罚案例类
- 市场数据类
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

    def _split_default(self, text: str, metadata: Dict) -> List[EvidenceChunk]:
        """默认切分：按段落"""
        chunks = []
        paragraphs = re.split(r"\n+", text)

        for i, para in enumerate(paragraphs):
            if para.strip():
                chunks.append(
                    EvidenceChunk(
                        content=para,
                        chunk_index=i,
                        scene_category=SceneCategory.MARKET_RESEARCH,
                        scene_tags=[],
                        evidence_level=self._determine_evidence_level(metadata),
                        metadata=metadata,
                    )
                )

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
