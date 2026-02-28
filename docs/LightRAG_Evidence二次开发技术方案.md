# LightRAG 二次开发 - Evidence 语料库建设技术方案

## 一、整体架构设计

### 1.1 核心目标

基于 LightRAG 项目进行二次开发，实现 **Evidence 语料库** 核心功能：

- **证据分级**: S/A/B/C 四级证据分类
- **精准溯源**: 文档→页码→段落级别的来源追踪
- **知识图谱增强**: 证据链关联 + 跨实体关系绑定
- **场景适配**: 行业场景标签体系
- **自定义切分**: 基于业务逻辑的精细化语料切分

### 1.2 实施顺序

```
Phase 3 (优先) → Phase 1 → Phase 2
知识图谱增强   → 证据分级+溯源 → 场景标签+切分
```

### 1.3 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Evidence 增强层 (新增)                       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: 知识图谱增强 ← 先做                                    │
│    - 证据链关联                                                 │
│    - 跨实体关系绑定                                             │
│    - 图谱可视化增强                                             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: 证据分级 + 精准溯源                                   │
│    - S/A/B/C 证据等级                                          │
│    - 多级溯源 (文档→页码→段落)                                 │
│    - 来源绑定                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: 场景标签 + 自定义切分                                  │
│    - 行业场景标签体系                                            │
│    - 业务逻辑切分器                                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  LightRAG 核心层 (修改)                          │
│  operate.py | types.py | prompt.py | kg/*.py                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、Phase 3: 知识图谱增强（优先实施）

### 2.1 数据模型扩展 (`types.py`)

新增 Evidence 增强类型定义：

```python
from enum import Enum
from typing import TypedDict, List

class EvidenceLevel(str, Enum):
    """证据等级枚举"""
    S = "S"  # 监管机构/权威发布 - 最高可信度
    A = "A"  # 头部研报/顶刊论文
    B = "B"  # 中型机构报告
    C = "C"  # 普通报告/书籍章节

class SourceProvenance(TypedDict):
    """精准溯源 - 文档级来源信息"""
    doc_id: str                    # 文档唯一ID
    file_name: str                 # 文件名
    file_path: str                 # 文件完整路径
    page_num: Optional[int]        # 页码 (可选)
    paragraph_id: Optional[str]    # 段落ID (可选)
    chunk_id: str                 # 对应的chunk ID

class EvidenceRelationType(str, Enum):
    """证据链关系类型"""
    CAUSAL = "causal"        # 因果关系: A导致B
    SUPPORT = "support"      # 支持关系: A支持B
    CONTRADICT = "contradict" # 反驳关系: A反驳B
    RELATED = "related"      # 一般相关

class EvidenceChain(TypedDict):
    """证据链定义"""
    chain_id: str                          # 证据链唯一ID
    chain_type: EvidenceRelationType       # 证据链类型
    entities: List[str]                    # 涉及的实体列表
    evidence_level: EvidenceLevel          # 最低证据等级
    description: str                       # 证据链描述
    provenance: SourceProvenance          # 主要来源

class EvidenceEntity(TypedDict):
    """Evidence 增强的实体"""
    entity_name: str
    entity_type: str
    description: str
    evidence_level: EvidenceLevel          # 证据等级
    source_provenance: List[SourceProvenance]  # 多级溯源
    scene_tags: List[str]                 # 场景标签
    evidence_chain_ids: List[str]          # 关联的证据链ID

class EvidenceRelation(TypedDict):
    """Evidence 增强的关系"""
    src_id: str
    tgt_id: str
    keywords: str
    description: str
    relation_type: EvidenceRelationType   # 证据链关系类型
    evidence_level: EvidenceLevel          # 证据等级
    source_provenance: List[SourceProvenance]  # 溯源信息
    confidence: float                      # 置信度 0-1
```

### 2.2 提示词扩展 (`prompt.py`)

新增证据链提取提示词：

```python
PROMPTS["entity_extraction_with_evidence"] = """---Role---
You are a Knowledge Graph Specialist with expertise in Evidence-based reasoning. Your task is to extract entities and relationships with evidence chain attribution.

---Instructions---
1. **Entity Extraction & Output:**
    *   Identify clearly defined and meaningful entities
    *   Extract: entity_name, entity_type, entity_description
    *   Output Format: entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description

2. **Relationship & Evidence Chain Extraction:**
    *   Identify relationships between extracted entities
    *   **Evidence Chain Classification:**
        - `causal`: A causes/leads to B (政策变化 → 市场影响)
        - `support`: A supports/verifies B (数据 → 投资观点)
        - `contradict`: A contradicts/refutes B
        - `related`: A is generally related to B
    *   **Evidence Level Assignment:**
        - `S`: 监管机构官方文件、政府发文、法律法规
        - `A`: 头部券商研报、顶刊论文、权威数据库(Wind/Bloomberg)
        - `B`: 中型机构报告、深度分析、行业协会指南
        - `C`: 普通报告、书籍章节、行业周报/月报
    *   Output Format (7 fields):
        - relation{tuple_delimiter}source{tuple_delimiter}target{tuple_delimiter}relation_type{tuple_delimiter}evidence_level{tuple_delimiter}keywords{tuple_delimiter}description

3. **Key Rules:**
    *   Output entities first, then relationships
    *   Relationships are undirected
    *   Avoid duplicates
    *   Output in {language}
"""
```

### 2.3 核心改造点

| 文件 | 改动内容 |
|------|---------|
| `types.py` | 新增 EvidenceLevel, SourceProvenance, EvidenceRelation 等类 |
| `prompt.py` | 新增 entity_extraction_with_evidence 提示词 |
| `operate.py` | 修改 `_handle_single_relationship_extraction`，支持证据链类型 |
| `kg/neo4j_impl.py` | 扩展节点/边属性，支持证据链查询 |

---

## 三、Phase 1: 证据分级 + 精准溯源

### 3.1 溯源字段设计

```python
class EvidenceEntitySchema(TypedDict):
    entity_name: str
    entity_type: str
    description: str
    # Evidence 增强字段
    evidence_level: EvidenceLevel           # 证据等级
    source_provenance: List[SourceProvenance] # 多级溯源
    source_confidence: float                 # 来源可信度

class EvidenceRelationSchema(TypedDict):
    src_id: str
    tgt_id: str
    keywords: str
    description: str
    # Evidence 增强字段
    evidence_level: EvidenceLevel
    source_provenance: List[SourceProvenance]
    relation_type: str                      # 因果/支持/反驳/相关
    confidence: float
```

### 3.2 溯源追踪机制

```python
async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
    timestamp: int,
    file_path: str = "unknown_source",
    # 新增参数
    page_num: Optional[int] = None,
    paragraph_id: Optional[str] = None,
):
    # 构建溯源信息
    provenance = SourceProvenance(
        doc_id=compute_mdhash_id(file_path),
        file_name=os.path.basename(file_path),
        file_path=file_path,
        page_num=page_num,
        paragraph_id=paragraph_id,
        chunk_id=chunk_key,
    )
    
    return dict(
        entity_name=entity_name,
        entity_type=entity_type,
        description=entity_description,
        evidence_level=evidence_level,      # 新增
        source_provenance=[provenance],       # 新增
        source_id=chunk_key,
        file_path=file_path,
        timestamp=timestamp,
    )
```

---

## 四、Phase 2: 场景标签 + 自定义切分

### 4.1 场景标签体系

```python
class SceneTags:
    # 大类
    INVESTMENT_RESEARCH = "投研分析"      # 权益/固收/量化
    RISK_CONTROL = "风险控制"              # 信贷/市场/操作
    COMPLIANCE = "合规审核"                # 反洗钱/监管
    PRODUCT_DESIGN = "产品设计"
    MARKET_RESEARCH = "市场研判"
    
    # 细分标签示例
    SCENE_TAGS = {
        "投研分析": ["权益投研", "固收投研", "量化分析", "行业研究"],
        "风险控制": ["信贷风控", "市场风控", "操作风控", "信用风险"],
        "合规审核": ["反洗钱", "监管合规", "内控合规"],
    }
```

### 4.2 自定义切分器

```python
class EvidenceSplitter:
    """基于业务逻辑的证据切分"""
    
    def __init__(self, scene_type: str):
        self.scene_type = scene_type
    
    def split(self, text: str, metadata: dict) -> List[EvidenceChunk]:
        if self.scene_type == "监管政策":
            return self._split_policy(text, metadata)
        elif self.scene_type == "投研报告":
            return self._split_research_report(text, metadata)
        elif self.scene_type == "学术论文":
            return self._split_academic_paper(text, metadata)
    
    def _split_policy(self, text: str, metadata: dict) -> List[EvidenceChunk]:
        """政策类：按条款/子目切分"""
        # 识别条款编号，拆分为独立证据单元
    
    def _split_research_report(self, text: str, metadata: dict) -> List[EvidenceChunk]:
        """研报类：按观点+论据切分"""
        # 提取核心观点，搭配论据形成独立证据
```

---

## 五、实施顺序与文件清单

### 5.1 开发顺序

```
Phase 3: 知识图谱增强
├─ 3.1 扩展 types.py 数据模型
├─ 3.2 增强 prompt.py 提取提示词
├─ 3.3 修改 operate.py 解析逻辑
├─ 3.4 扩展 kg/ 存储实现
└─ 3.5 测试验证

Phase 1: 证据分级 + 精准溯源
├─ 1.1 实现 SourceProvenance 追踪
├─ 1.2 实现 EvidenceLevel 分级
├─ 1.3 增强入库逻辑
└─ 1.4 查询排序优化

Phase 2: 场景标签 + 自定义切分
├─ 2.1 实现 SceneTags 标签体系
├─ 2.2 实现 EvidenceSplitter 切分器
├─ 2.3 集成到 chunking 流程
└─ 2.4 场景检索优化
```

### 5.2 核心文件改动清单

| Phase | 文件 | 改动类型 |
|-------|------|---------|
| 3 | `types.py` | 新增 EvidenceRelation, EvidenceLevel |
| 3 | `prompt.py` | 新增 evidence_extraction_with_evidence 提示词 |
| 3 | `operate.py` | 修改关系提取，增加证据链类型 |
| 3 | `kg/neo4j_impl.py` | 扩展节点/边属性 |
| 1 | `operate.py` | 增加溯源字段处理 |
| 1 | `utils.py` | 新增溯源构建函数 |
| 2 | `evidence_splitter.py` | **新增文件** |
| 2 | `operate.py` | 集成自定义切分器 |

---

## 六、证据等级划分标准（金融行业）

### 6.1 S 级 - 最高等级

- 监管机构官方发文（央行、银保监会、证监会、交易所）
- 国家法律法规条文
- 国际顶级监管组织文件

### 6.2 A 级

- 头部券商/公募/私募投研报告
- 金融顶刊论文（Journal of Finance 等）
- 权威金融数据库核心数据（Wind、Choice、Bloomberg）
- 行业协会官方指南

### 6.3 B 级

- 中型金融机构投研报告
- 核心财经媒体深度分析
- 金融行业经典案例
- 公司内部核心投研/风控成果

### 6.4 C 级

- 普通金融机构研究报告
- 行业周报/月报
- 金融专业书籍章节

---

## 七、证据链类型定义

### 7.1 因果链 (CAUSAL)

- 定义: A 导致/影响 B
- 示例: 监管政策变化 → 市场影响
- 适用: 政策解读、风险传导分析

### 7.2 支持链 (SUPPORT)

- 定义: A 支持/验证 B
- 示例: 数据 → 投资观点
- 适用: 投资决策、观点验证

### 7.3 反驳链 (CONTRADICT)

- 定义: A 反驳/否定 B
- 示例: 不同观点碰撞
- 适用: 争议分析、多空观点

### 7.4 相关链 (RELATED)

- 定义: A 与 B 一般相关
- 示例: 行业 → 关联公司
- 适用: 背景信息检索

---

## 八、溯源字段模板

```json
{
  "type": "meta",
  "origin_file_name": "28000-北京市地方金融监督管理条例.pdf",
  "origin_file_path": "/path/to/file.pdf",
  "business_unique_id": 28000,
  "时间": "2026年01月",
  "适用范围": "上海市",
  "知识库-大类": "管理类",
  "知识库-中类": "政策法规",
  "知识库-小类": "其他规范性文件",
  "知识领域-组别": "法律法规",
  "知识领域-一级分类": "金融",
  "知识领域-二级分类": "法律法规",
  "知识领域-三级分类": "北京地方监督管理",
  "优先级": "1",
  "contents": [
    {
      "type": "text",
      "level_0": "北京市地方金融监督管理条例",
      "level_1": "第一章 总 则",
      "level_2": "第一条",
      "keywords": ["地方金融监督管理", "金融风险防范"],
      "summary": "北京市地方金融监督管理条例旨在规范...",
      "page_num": 0,
      "content": "第一条 为了规范地方金融组织..."
    }
  ]
}
```

---

*文档版本: v1.0*  
*创建日期: 2026-02-26*  
*项目: LightRAG Evidence 语料库二次开发*

---

## 九、Phase 1 开发完成内容

### 9.1 新增/修改文件清单

| 文件 | 改动内容 |
|------|---------|
| `utils.py` | 新增溯源工具函数 |
| `operate.py` | 新增 `_handle_single_entity_extraction_with_provenance()` |
| `kg/neo4j_impl.py` | 新增溯源查询方法 |

### 9.2 新增 API

```python
# 溯源工具函数
from lightrag.utils import (
    create_source_provenance,
    parse_provenance_from_chunk,
    merge_provenances,
)

# 溯源查询 API
await kg.get_entity_provenance("实体名称")
await kg.get_relation_provenance("源实体", "目标实体")
await kg.get_entities_by_file("/path/to/file.pdf", limit=100)
```

### 9.3 溯源数据结构

```python
{
    "doc_id": "md5hash...",           # 文档唯一ID
    "file_name": "政策文件.pdf",      # 文件名
    "file_path": "/path/to/file.pdf", # 完整路径
    "page_num": 5,                    # 页码
    "paragraph_id": "p123",           # 段落ID
    "chunk_id": "chunk_xxx",          # chunk ID
}
```

---

*Phase 1 完成时间: 2026-02-26*
---

## 十、Phase 2 开发完成内容

### 10.1 新增/修改文件清单

| 文件 | 改动内容 |
|------|---------|
| `evidence_splitter.py` | **新增文件** - 场景标签与自定义切分模块 |
| `operate.py` | 新增场景化 chunking 集成函数 |
| `kg/neo4j_impl.py` | 新增场景检索方法 |

### 10.2 新增 API

```python
# 1. 场景标签模块
from lightrag.evidence_splitter import (
    EvidenceSplitter,
    EvidenceChunk,
    SceneCategory,
    SCENE_TAG_MAPPING,
    get_scene_tags,
    detect_scene_from_text,
)

# 2. 场景化切分函数
from lightrag.operate import (
    chunking_by_evidence_splitter,
    chunking_with_scene_detection,
)

# 3. 场景检索 API
await kg.get_entities_by_scene("投研分析")
await kg.get_relations_by_scene("风险控制")
await kg.get_entities_by_evidence_level_and_scene("S", "政策法规")
```

### 10.3 场景标签体系

| 大类 | 细分标签 |
|------|---------|
| 投研分析 | 权益投研、固收投研、量化分析、行业研究 |
| 风险控制 | 信贷风控、市场风控、操作风控、信用风险 |
| 合规审核 | 反洗钱、监管合规、内控合规 |
| 产品设计 | 理财产品、基金产品、保险产品 |
| 市场研判 | 宏观经济、行业趋势、市场情绪 |
| 政策法规 | 监管政策、法律法规、行业规范 |
| 学术研究 | 实证研究、理论研究、案例研究 |
| 案例分析 | 处罚案例、典型案例、风险事件 |

### 10.4 证据块数据结构

```python
@dataclass
class EvidenceChunk:
    content: str                      # 证据内容
    chunk_index: int                  # 块索引
    scene_category: SceneCategory     # 场景大类
    scene_tags: List[str]            # 场景标签
    provenance: Optional[Dict]        # 溯源信息
    evidence_level: str                # 证据等级
    metadata: Dict[str, Any]          # 额外元数据
```

---

## 十一、开发总结

### 11.1 完成的代码修改

| Phase | 状态 | 核心文件 |
|-------|------|---------|
| Phase 3 | ✅ 完成 | types.py, prompt.py, operate.py, kg/neo4j_impl.py |
| Phase 1 | ✅ 完成 | utils.py, operate.py, kg/neo4j_impl.py |
| Phase 2 | ✅ 完成 | evidence_splitter.py, operate.py, kg/neo4j_impl.py |

### 11.2 新增文件清单

- `lightrag/evidence_splitter.py` - 场景标签与自定义切分模块

### 11.3 核心 API 列表

**溯源相关：**
- `create_source_provenance()`
- `parse_provenance_from_chunk()`
- `merge_provenances()`
- `kg.get_entity_provenance()`
- `kg.get_relation_provenance()`
- `kg.get_entities_by_file()`

**证据链相关：**
- `_handle_single_relationship_extraction_with_evidence()`
- `kg.get_entities_by_evidence_level()`
- `kg.get_relations_by_evidence_level()`
- `kg.get_relations_by_type()`

**场景相关：**
- `EvidenceSplitter`
- `chunking_by_evidence_splitter()`
- `chunking_with_scene_detection()`
- `kg.get_entities_by_scene()`
- `kg.get_relations_by_scene()`
- `kg.get_entities_by_evidence_level_and_scene()`

---

*All Phases Completed - 2026-02-26*
---

## 十二、Phase 4: 证据推理功能（扩展开发）

### 12.1 功能说明

在完成证据链基础功能后，进一步实现高级推理能力：

| 功能 | 说明 |
|------|------|
| 因果链追溯 | 从某实体出发，追溯完整的因果链路径 |
| 证据聚合 | 聚合相同主题/类型/场景的证据 |
| 交叉验证 | 检测支持/反驳关系，验证证据一致性 |

### 12.2 新增 API

```python
# 1. 因果链追溯
await kg.get_causal_chain(
    entity_id="降准政策",
    max_depth=5,           # 最大深度
    evidence_level="S",   # 证据等级过滤
    limit=20
)

# 2. 证据聚合
await kg.aggregate_evidence(
    topic="科创板",          # 主题关键词
    scene_tag="投研分析",   # 场景标签
    evidence_level="S",      # 证据等级
    min_weight=3,           # 最小权重
    limit=50
)

# 3. 交叉验证
await kg.cross_validate(
    claim_entity="货币政策将利好股市",
    min_evidence_count=1
)
```

### 12.3 返回示例

**因果链追溯返回：**
```python
[
    {
        "start_entity": "降准政策",
        "end_entity": "银行负债成本降低",
        "chain_entities": [
            {"entity_id": "降准政策", "entity_name": "降准政策", ...},
            {"entity_id": "银行负债成本降低", "entity_name": "银行负债成本降低", ...}
        ],
        "chain_relations": [
            {"description": "降准释放流动性...", "evidence_level": "S", "keywords": "降准"}
        ],
        "chain_length": 3,
        "chain_weight": 12
    }
]
```

**交叉验证返回：**
```python
{
    "claim": "货币政策将利好股市",
    "conclusion": "证据支持",  # 或: 证据反驳/证据存在分歧/证据不足
    "support_evidence": [
        {"entity": "降准", "description": "释放流动性...", "level": "S", "type": "support"}
    ],
    "contradict_evidence": [],
    "support_count": 3,
    "contradict_count": 0,
    "support_weight": 10,
    "contradict_weight": 0
}
```

### 12.4 验证结论规则

| 条件 | 结论 |
|------|------|
| support > contradict × 1.5 | 证据支持 |
| contradict > support × 1.5 | 证据反驳 |
| support > 0 且 contradict > 0 | 证据存在分歧 |
| 仅支持证据 | 证据支持(单方面) |
| 仅反驳证据 | 证据反驳(单方面) |
| 都为0 | 证据不足 |

### 12.5 证据等级权重

| 等级 | 权重 |
|------|------|
| S | 4 |
| A | 3 |
| B | 2 |
| C | 1 |

---

## 十三、开发总结（更新）

### 13.1 完成的代码修改

| Phase | 状态 | 核心文件 |
|-------|------|---------|
| Phase 3 | ✅ 完成 | types.py, prompt.py, operate.py, kg/neo4j_impl.py |
| Phase 1 | ✅ 完成 | utils.py, operate.py, kg/neo4j_impl.py |
| Phase 2 | ✅ 完成 | evidence_splitter.py, operate.py, kg/neo4j_impl.py |
| Phase 4 | ✅ 完成 | kg/neo4j_impl.py (证据推理) |

### 13.2 新增文件清单

- `lightrag/evidence_splitter.py` - 场景标签与自定义切分模块

### 13.3 核心 API 列表（完整版）

**溯源相关：**
- `create_source_provenance()`
- `parse_provenance_from_chunk()`
- `merge_provenances()`
- `kg.get_entity_provenance()`
- `kg.get_relation_provenance()`
- `kg.get_entities_by_file()`

**证据链相关：**
- `_handle_single_relationship_extraction_with_evidence()`
- `kg.get_entities_by_evidence_level()`
- `kg.get_relations_by_evidence_level()`
- `kg.get_relations_by_type()`

**场景相关：**
- `EvidenceSplitter`
- `chunking_by_evidence_splitter()`
- `chunking_with_scene_detection()`
- `kg.get_entities_by_scene()`
- `kg.get_relations_by_scene()`
- `kg.get_entities_by_evidence_level_and_scene()`

**证据推理相关：**
- `kg.get_causal_chain()` - 因果链追溯
- `kg.aggregate_evidence()` - 证据聚合
- `kg.cross_validate()` - 交叉验证

---

*All Phases Completed - 2026-02-27*