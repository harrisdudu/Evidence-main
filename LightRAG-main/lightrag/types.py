# Evidence 增强模块 - 证据链相关类型定义
from __future__ import annotations

from enum import Enum
from typing import TypedDict, Any, Optional

from pydantic import BaseModel


class EvidenceLevel(str, Enum):
    """证据等级枚举"""

    S = "S"  # 监管机构/权威发布 - 最高可信度
    A = "A"  # 头部研报/顶刊论文
    B = "B"  # 中型机构报告
    C = "C"  # 普通报告/书籍章节


class SourceProvenance(TypedDict):
    """精准溯源 - 文档级来源信息"""

    doc_id: str  # 文档唯一ID
    file_name: str  # 文件名
    file_path: str  # 文件完整路径
    page_num: Optional[int]  # 页码 (可选)
    paragraph_id: Optional[str]  # 段落ID (可选)
    chunk_id: str  # 对应的chunk ID


class EvidenceRelationType(str, Enum):
    """证据链关系类型"""

    CAUSAL = "causal"  # 因果关系: A导致B
    SUPPORT = "support"  # 支持关系: A支持B
    CONTRADICT = "contradict"  # 反驳关系: A反驳B
    RELATED = "related"  # 一般相关


class EvidenceChain(TypedDict):
    """证据链定义"""

    chain_id: str  # 证据链唯一ID
    chain_type: EvidenceRelationType  # 证据链类型
    entities: list[str]  # 涉及的实体列表
    evidence_level: EvidenceLevel  # 最低证据等级
    description: str  # 证据链描述
    provenance: SourceProvenance  # 主要来源


class EvidenceEntity(TypedDict):
    """Evidence 增强的实体"""

    entity_name: str
    entity_type: str
    description: str
    evidence_level: EvidenceLevel  # 证据等级
    source_provenance: list[SourceProvenance]  # 多级溯源
    scene_tags: list[str]  # 场景标签
    evidence_chain_ids: list[str]  # 关联的证据链ID


class EvidenceRelation(TypedDict):
    """Evidence 增强的关系"""

    src_id: str
    tgt_id: str
    keywords: str
    description: str
    relation_type: EvidenceRelationType  # 证据链关系类型
    evidence_level: EvidenceLevel  # 证据等级
    source_provenance: list[SourceProvenance]  # 溯源信息
    confidence: float  # 置信度 0-1


# 原有类型保持不变
class GPTKeywordExtractionFormat(BaseModel):
    high_level_keywords: list[str]
    low_level_keywords: list[str]


class KnowledgeGraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict[str, Any]  # anything else goes here


class KnowledgeGraphEdge(BaseModel):
    id: str
    type: Optional[str]
    source: str  # id of source node
    target: str  # id of target node
    properties: dict[str, Any]  # anything else goes here


class KnowledgeGraph(BaseModel):
    nodes: list[KnowledgeGraphNode] = []
    edges: list[KnowledgeGraphEdge] = []
    is_truncated: bool = False
