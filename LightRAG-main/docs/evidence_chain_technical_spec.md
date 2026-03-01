# OpenEvidence 产品证据链技术方案

> 基于 LightRAG 实现的证据链系统技术方案文档
>
> 更新日期: 2026-03-01

---

## 一、系统概述

### 1.1 目标

构建一个支持证据链追溯的 RAG 系统，能够：
- 追踪每个答案的信息来源
- 支持证据等级评估 (S/A/B/C)
- 提供多级溯源 (文档 → 段落 → 句子)
- 支持因果、支持、反驳等关系类型

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户查询                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Query Processing Layer                                │
│  • 关键词提取 (high_level + low_level)                                       │
│  • 查询模式选择 (local/global/hybrid/naive)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐     ┌─────────────────────────────────────────┐
│   Vector Store (Milvus/    │     │   Graph Store (Neo4j/NetworkX)          │
│   Qdrant/PostgreSQL)       │     │                                         │
│   • Entity Embeddings       │     │   Nodes:                                │
│   • Chunk Embeddings        │     │   - entity_name                        │
│   • Evidence Level          │     │   - entity_type                        │
│   • Source Provenance       │     │   - evidence_level                     │
│   • Evidence Chain IDs      │     │   - scene_tags                         │
│                             │     │   - source_provenance                  │
│                             │     │   - evidence_chain_ids                 │
│                             │     │                                         │
│                             │     │   Edges:                               │
│                             │     │   - relation_type (causal/support/     │
│                             │     │                 contradict/related)     │
│                             │     │   - evidence_level                     │
│                             │     │   - source_provenance                  │
│                             │     │   - confidence                         │
└─────────────────────────────┘     └─────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LLM Generation Layer                                  │
│  • Chain-of-Evidence Prompt                                                 │
│  • Citation Generation                                                      │
│  • Evidence Bundle Construction                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Response Output                                    │
│  {answer} [Source 1] {answer} [Source 2]                                 │
│  ### References                                                            │
│  - [1] Document Title                                                     │
│  - [2] Document Title                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、证据链类型定义

> 参考: `lightrag/types.py`

### 2.1 证据等级 (EvidenceLevel)

```python
class EvidenceLevel(str, Enum):
    """证据等级枚举 - 四级分类体系"""
    
    S = "S"  # 监管机构/权威发布 - 最高可信度
    A = "A"  # 头部研报/顶刊论文
    B = "B"  # 中型机构报告
    C = "C"  # 普通报告/书籍章节
```

**等级定义:**

| 等级 | 来源类型 | 示例 |
|------|---------|------|
| S | 监管机构官方文件 | 央行发文、FDA批准、WHO指南 |
| A | 头部研报/顶刊论文 | 高盛研报、NEJM论文、WIND数据 |
| B | 中型机构报告 | 行业协会指南、深度分析报告 |
| C | 普通报告 | 书籍章节、行业周报/月报 |

### 2.2 溯源信息 (SourceProvenance)

```python
class SourceProvenance(TypedDict):
    """精准溯源 - 文档级来源信息"""
    
    doc_id: str           # 文档唯一ID
    file_name: str        # 文件名
    file_path: str       # 文件完整路径
    page_num: Optional[int]   # 页码 (可选)
    paragraph_id: Optional[str] # 段落ID (可选)
    chunk_id: str        # 对应的chunk ID
```

**溯源层级:**

```
文档级 (doc_id)
    │
    ├── 页面级 (page_num) - PDF文档
    │
    ├── 段落级 (paragraph_id)
    │
    └── Chunk级 (chunk_id) - 语义分割块
```

### 2.3 证据链关系类型 (EvidenceRelationType)

```python
class EvidenceRelationType(str, Enum):
    """证据链关系类型"""
    
    CAUSAL = "causal"      # 因果关系: A导致B
    SUPPORT = "support"    # 支持关系: A支持B
    CONTRADICT = "contradict"  # 反驳关系: A反驳B
    RELATED = "related"    # 一般相关
```

### 2.4 证据增强实体 (EvidenceEntity)

```python
class EvidenceEntity(TypedDict):
    """Evidence 增强的实体"""
    
    entity_name: str
    entity_type: str
    description: str
    evidence_level: EvidenceLevel           # 证据等级
    source_provenance: list[SourceProvenance]  # 多级溯源
    scene_tags: list[str]                   # 场景标签
    evidence_chain_ids: list[str]           # 关联的证据链ID
```

### 2.5 证据增强关系 (EvidenceRelation)

```python
class EvidenceRelation(TypedDict):
    """Evidence 增强的关系"""
    
    src_id: str
    tgt_id: str
    keywords: str
    description: str
    relation_type: EvidenceRelationType     # 证据链关系类型
    evidence_level: EvidenceLevel          # 证据等级
    source_provenance: list[SourceProvenance]  # 溯源信息
    confidence: float                       # 置信度 0-1
```

---

## 二、证据链类型定义 (续)

> 参考: `lightrag/evidence_splitter.py`

### 2.6 场景标签系统 (SceneTags)

代码已实现**14个行业大类**，超过**100个场景标签**：

| 行业 | 场景标签 |
|------|---------|
| **金融** | 投研分析、风险控制、合规审核、产品设计、市场研判、政策法规、金融、投资 |
| **医疗健康** | 医疗健康、医药、医疗器械、公共卫生 |
| **城市治理** | 城市治理、智慧城市、公共服务、应急管理 |
| **教育** | 教育、职业教育、教育科技 |
| **工业制造** | 工业制造、供应链、质量管理、智能制造 |
| **能源** | 能源、电力、新能源 |
| **农业** | 农业、食品安全、乡村振兴 |
| **法律** | 法律、司法、合规法律 |
| **媒体与通信** | 媒体、公共关系 |
| **环境保护** | 环境保护、生态、气候变化 |
| **交通运输** | 交通运输、物流、自动驾驶 |
| **房地产与建筑** | 房地产、建筑、物业管理 |
| **信息技术** | 信息技术、网络安全、数据隐私 |
| **商业零售** | 商业零售、电子商务、消费者保护 |

#### 场景检测逻辑

```python
# evidence_splitter.py 实现的场景检测
def _detect_scene_type(self, text: str, metadata: Dict) -> SceneCategory:
    # 基于关键词匹配自动检测场景
    if any(kw in text for kw in ["央行", "银保监会", "货币政策"]):
        return SceneCategory.POLICY_REGULATION
    if any(kw in text for kw in ["股票", "债券", "基金"]):
        return SceneCategory.INVESTMENT_RESEARCH
    # ... 更多检测逻辑
```

### 2.7 证据等级自动判定

> 参考: `lightrag/evidence_splitter.py:1359-1375`

代码已实现基于文件名的证据等级自动判定：

```python
def _determine_evidence_level(self, metadata: Dict) -> str:
    # 1. 优先使用元数据中指定的等级
    if "evidence_level" in metadata:
        return metadata["evidence_level"]
    
    # 2. 根据文件路径关键词推断
    file_path = metadata.get("file_path", "").lower()
    
    # S级: 监管机构文件
    if any(kw in file_path for kw in ["监管", "央行", "证监会", "银保监会"]):
        return "S"
    
    # A级: 头部研报/权威数据/顶刊论文
    if any(kw in file_path for kw in ["研报", "wind", "bloomberg"]):
        return "A"
    if any(kw in file_path for kw in ["论文", "journal"]):
        return "A"
    
    # 默认B级
    return "B"
```

**注意**: 当前代码默认B级，未实现C级自动判定和高级加成（如影响因子、时间衰减）

---

---

## 三、图数据库 Schema 设计

> 参考: `lightrag/kg/neo4j_impl.py`

### 3.1 Neo4j 节点设计

```cypher
// 约束定义
CREATE CONSTRAINT entity_name_idx IF NOT EXISTS
FOR (e:__Entity__) REQUIRE e.entity_name IS UNIQUE;
```

#### 实体节点属性

```python
# 存储在 Neo4j 节点中的关键属性
{
    "entity_name": "银发〔2025〕18号",
    "entity_type": "regulation",
    "description": "央行发布的关于完善结构性货币政策工具的通知文件",
    "evidence_level": "S",           # 证据等级
    "source_provenance": [          # 多级溯源
        {
            "doc_id": "doc_001",
            "file_name": "央行政策文件.pdf",
            "file_path": "/docs/央行政策文件.pdf",
            "page_num": 1,
            "chunk_id": "chunk_001"
        }
    ],
    "scene_tags": ["货币政策", "科技创新"],
    "evidence_chain_ids": ["chain_001", "chain_002"]
}
```

#### 证据链节点属性

```python
{
    "chain_id": "chain_银发_causal_001",
    "chain_type": "causal",
    "entities": ["银发〔2025〕18号", "科技创新领域"],
    "evidence_level": "S",
    "description": "该通知将结构性货币政策工具适用范围扩大至科技创新领域"
}
```

### 3.2 Neo4j 边设计

```cypher
// 关系类型定义
// 支持的关系属性
{
    "keywords": "政策扩大适用,结构性货币工具",
    "description": "该通知将结构性货币政策工具适用范围扩大至科技创新领域...",
    "relation_type": "causal",           // 因果/支持/反驳/相关
    "evidence_level": "S",                 // 证据等级
    "source_provenance": [...],           // 溯源信息
    "confidence": 0.95,                  // 置信度
    "valid_from": "2025-01-01",          # 有效期开始
    "valid_to": null                      // 有效期结束 (null=永久)
}
```

### 3.3 索引策略

```cypher
// 证据等级索引 - 快速筛选
CREATE INDEX evidence_level_idx IF NOT EXISTS
FOR (e:__Entity__) ON (e.evidence_level);

// 证据链ID索引 - 追溯查询
CREATE INDEX evidence_chain_idx IF NOT EXISTS
FOR (e:__Entity__) ON (e.evidence_chain_ids);

// 场景标签索引 - 按场景检索
CREATE INDEX scene_tags_idx IF NOT EXISTS
FOR (e:__Entity__) ON (e.scene_tags);

// 全文索引 - 证据描述搜索
CREATE FULLTEXT INDEX entity_description_idx IF NOT EXISTS
FOR (e:__Entity__) ON [e.description];
```

### 3.4 证据追溯查询示例

```cypher
// 查询某实体的完整证据链
MATCH (e:__Entity__ {entity_name: '银发〔2025〕18号'})
OPTIONAL MATCH (e)-[r:__Relation__]->(target)
RETURN e.entity_name, e.evidence_level, e.source_provenance,
       collect({
           target: target.entity_name,
           relation_type: r.relation_type,
           evidence_level: r.evidence_level,
           confidence: r.confidence
       }) as outgoing_relations

// 查询证据链完整路径
MATCH path = (e1:__Entity__)-[r:__Relation__]->(e2:__Entity__)
WHERE r.evidence_level IN ['S', 'A']
WITH path, r
WHERE r.relation_type = 'causal'
RETURN path, r.description
LIMIT 25
```

---

### 3.5 证据链查询 API

> 参考: `lightrag/kg/neo4j_impl.py`

代码已实现丰富的证据链查询API：

#### 3.5.1 按证据等级查询

```python
# 按证据等级查询实体
async def get_entities_by_evidence_level(
    self,
    evidence_level: str,  # "S"/"A"/"B"/"C"
    limit: int = 100
) -> list[dict]:
    """根据证据等级查询符合条件的实体"""
    # 返回: 符合条件的实体列表
```

```python
# 按证据等级查询关系
async def get_relations_by_evidence_level(
    self,
    evidence_level: str,
    limit: int = 100
) -> list[dict]:
    """根据证据等级查询关系"""
```

#### 3.5.2 按关系类型查询

```python
# 按证据链类型查询关系
async def get_relations_by_type(
    self,
    relation_type: str,  # "causal"/"support"/"contradict"/"related"
    limit: int = 100
) -> list[dict]:
    """根据证据链类型查询关系"""
```

#### 3.5.3 按证据等级+场景查询

```python
# 按证据等级和场景标签查询实体
async def get_entities_by_evidence_level_and_scene(
    self,
    evidence_level: str,
    scene: str,
    limit: int = 100
) -> list[dict]:
    """组合查询：证据等级 + 场景标签"""
```

#### 3.5.4 证据聚合分析

```python
# 证据聚合分析
async def aggregate_evidence(
    self,
    entity_name: str = None,
    evidence_level: str = None,
    min_count: int = 1
) -> dict:
    """
    聚合某实体的证据分布
    返回: 各证据等级的实体/关系数量统计
    """
```

#### 3.5.5 支持/反驳证据对比

```python
# 获取支持与反驳证据对比
async def get_support_contradict_evidence(
    self,
    entity_name: str,
    min_evidence_count: int = 1
) -> dict:
    """
    获取某实体的支持证据与反驳证据
    
    返回:
    - support_evidence: 支持该论点的证据列表
    - contradict_evidence: 反驳该论点的证据列表
    - support_count: 支持证据数量
    - contradict_count: 反驳证据数量
    - support_weight: 支持证据加权得分
    - contradict_weight: 反驳证据加权得分
    """
```

#### 3.5.6 PostgreSQL 证据列支持

> 参考: `lightrag/kg/postgres_impl.py:2582-2600`

PostgreSQL存储后端也支持证据链字段：

```python
# PostgreSQL 证据列定义
async def _pg_ensure_evidence_columns(db, table_name, base_table):
    required["evidence_level"] = "VARCHAR(8) NULL DEFAULT 'B'"
    required["evidence_chain_ids"] = "JSONB NULL DEFAULT '[]'::jsonb"
    # scene_tags 和 source_provenance 也已支持
```

---

## 四、RAG Prompt 优化

> 参考: `lightrag/prompt.py`

### 4.1 带证据的实体提取 Prompt

```python
PROMPTS["entity_extraction_with_evidence"] = """---Role---
You are a Knowledge Graph Specialist with expertise in Evidence-based reasoning. 
Your task is to extract entities and relationships with evidence chain attribution.

---Instructions---
1. **Entity Extraction & Output:**
    * **Identification:** Identify clearly defined and meaningful entities in the input text.
    * **Entity Details:** For each entity, extract:
        * `entity_name`: The name of the entity (title case if case-insensitive)
        * `entity_type`: Type from: {entity_types}
        * `entity_description`: Comprehensive description based *solely* on the input text
    * **Output Format (4 fields):**
        * Format: `entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description`

2. **Relationship & Evidence Chain Extraction:**
    * **Identification:** Identify relationships between extracted entities
    * **Evidence Chain Classification:** Classify each relationship type:
        * `causal`: A causes/leads to B (e.g., 政策变化 → 市场影响)
        * `support`: A supports/verifies B (e.g., 数据 → 投资观点)
        * `contradict`: A contradicts/refutes B (e.g., 不同观点)
        * `related`: A is generally related to B
    * **Evidence Level Assignment:**
        * `S`: 监管机构官方文件、政府发文、法律法规
        * `A`: 头部券商研报、顶刊论文、权威数据库(Wind/Bloomberg)
        * `B`: 中型机构报告、深度分析、行业协会指南
        * `C`: 普通报告、书籍章节、行业周报/月报
    * **Evidence Chain ID Assignment:** Generate unique chain_id for each evidence chain
    * **Output Format (8 fields):**
        * Format: `relation{tuple_delimiter}source_entity{tuple_delimiter}target_entity{tuple_delimiter}relation_type{tuple_delimiter}evidence_level{tuple_delimiter}keywords{tuple_delimiter}description{tuple_delimiter}chain_id`
"""
```

### 4.2 证据提取示例

```python
PROMPTS["entity_extraction_with_evidence_examples"] = [
    """<Entity_types>
[Person, Organization, Location, Event, Concept, Product, Regulation, Market]

<Entity_extraction_with_evidence_Example>
Input Text:
```
2025年1月，央行发布《关于进一步完善结构性货币政策工具的通知》(银发〔2025〕18号)，明确提出将结构性货币政策工具的适用范围扩大至科技创新领域。业内人士指出，此举将显著降低科创企业融资成本。根据Wind数据显示，2024年四季度科创板企业整体融资规模已达1.2万亿元，同比增长15%。
```

Output:
entity{tuple_delimiter}央行{tuple_delimiter}organization{tuple_delimiter}央行是中国最高的货币金融管理机构，负责制定和执行货币政策。
entity{tuple_delimiter}银发〔2025〕18号{tuple_delimiter}regulation{tuple_delimiter}央行发布的关于完善结构性货币政策工具的通知文件。
entity{tuple_delimiter}科技创新领域{tuple_delimiter}concept{tuple_delimiter}指涉及新技术、新产品、新工艺等创新活动的经济领域。
entity{tuple_delimiter}科创企业{tuple_delimiter}organization{tuple_delimiter}指符合科创板上市条件的科技创新型企业。
entity{tuple_delimiter}科创板{tuple_delimiter}market{tuple_delimiter}为科技创新企业服务的股票交易板块。
entity{tuple_delimiter}Wind{tuple_delimiter}organization{tuple_delimiter}权威金融数据提供平台。

relation{tuple_delimiter}银发〔2025〕18号{tuple_delimiter}科技创新领域{tuple_delimiter}causal{tuple_delimiter}S{tuple_delimiter}政策扩大适用,结构性货币工具{tuple_delimiter}该通知将结构性货币政策工具适用范围扩大至科技创新领域，为科创企业提供融资支持。{tuple_delimiter}chain_银发_causal_001
relation{tuple_delimiter}银发〔2025〕18号{tuple_delimiter}科创企业{tuple_delimiter}support{tuple_delimiter}S{tuple_delimiter}融资成本降低,政策支持{tuple_delimiter}该通知明确将降低科创企业融资成本。{tuple_delimiter}chain_银发_support_002
relation{tuple_delimiter}Wind{tuple_delimiter}科创板{tuple_delimiter}support{tuple_delimiter}A{tuple_delimiter}数据来源,融资规模{tuple_delimiter}Wind数据显示科创板企业融资规模数据。{tuple_delimiter}chain_Wind_support_003
relation{tuple_delimiter}科技创新领域{tuple_delimiter}科创企业{tuple_delimiter}related{tuple_delimiter}B{tuple_delimiter}主体关系,领域企业{tuple_delimiter}科技创新领域包含科创板上市的科创企业。{tuple_delimiter}chain_科创板_related_004
<|COMPLETE|>
"""
]
```

### 4.3 RAG 响应 Prompt (含引用)

```python
PROMPTS["rag_response"] = """---Role---
You are an expert AI assistant specializing in synthesizing information from a 
provided knowledge base. Your primary function is to answer user queries 
accurately by ONLY using the information within the provided **Context**.

---Instructions---
1. Step-by-Step Instruction:
   - Carefully determine the user's query intent
   - Scrutinize both `Knowledge Graph Data` and `Document Chunks` in the **Context**
   - Track the reference_id of the document chunk which directly support the facts
   - Generate a references section at the end of the response

2. Content & Grounding:
   - Strictly adhere to the provided context; DO NOT invent any information
   - If the answer cannot be found in the **Context**, state that limitation

3. References Section Format:
   - The References section should be under heading: `### References`
   - Reference list entries: `* [n] Document Title`
   - Provide maximum of 5 most relevant citations

---Context---
{context_data}
"""
```

### 4.4 参数配置建议

| 参数 | 推荐值 | 原因 |
|------|--------|------|
| temperature | 0.1 - 0.3 | 降低随机性,提高一致性 |
| top_p | 0.9 | 与temperature配合 |
| max_tokens | 2048+ | 足够空间容纳引用 |
| presence_penalty | 0 | 不惩罚重复(引用需要) |
| frequency_penalty | 0 | 同上 |

---

## 五、证据分级算法

### 5.1 基础分级实现

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class EvidenceLevel(Enum):
    S = "S"  # 监管机构/权威发布
    A = "A"  # 头部研报/顶刊论文
    B = "B"  # 中型机构报告
    C = "C"  # 普通报告/书籍章节

@dataclass
class EvidenceGrade:
    level: EvidenceLevel
    confidence: float  # 0-1
    factors: List[str]  # 降级/升级因素

def calculate_grade(publication: dict) -> EvidenceGrade:
    """基于文献元数据计算证据等级"""
    
    # 1. 基础等级判定
    source_type = publication.get('source_type', '').lower()
    
    # 监管机构文件
    if source_type in ['regulation', 'government', 'official']:
        base_level = EvidenceLevel.S
        confidence = 0.98
    # 头部研报/顶刊
    elif source_type in ['research_report', 'top_journal']:
        base_level = EvidenceLevel.A
        confidence = 0.95
    # 中型机构
    elif source_type in ['industry_report', 'association']:
        base_level = EvidenceLevel.B
        confidence = 0.85
    # 普通报告
    else:
        base_level = EvidenceLevel.C
        confidence = 0.70
    
    factors = []
    
    # 2. 期刊影响因子加成
    impact_factor = publication.get('impact_factor', 0)
    if impact_factor > 50:
        confidence = min(0.99, confidence + 0.03)
        factors.append("高影响因子期刊")
    elif impact_factor > 20:
        confidence = min(0.95, confidence + 0.02)
        factors.append("较高影响因子")
    
    # 3. 同行评审
    if publication.get('is_peer_reviewed', False):
        confidence = min(0.98, confidence + 0.02)
        factors.append("同行评审")
    
    # 4. 数据来源权威性
    if publication.get('data_source') in ['wind', 'bloomberg', 'reuters']:
        confidence = min(0.97, confidence + 0.02)
        factors.append("权威数据源")
    
    # 5. 时间衰减
    pub_year = publication.get('publication_year', 2020)
    years_old = 2026 - pub_year
    if years_old > 5:
        confidence = max(0.5, confidence - 0.05 * (years_old - 5))
        factors.append(f"文献较旧({years_old}年)")
    
    return EvidenceGrade(
        level=base_level,
        confidence=confidence,
        factors=factors
    )
```

### 5.2 多源聚合评分

```python
def aggregate_evidence_score(publications: List[dict]) -> dict:
    """聚合多个证据来源的评分"""
    
    if not publications:
        return {
            'aggregate_level': 'insufficient',
            'confidence': 0.0,
            'total_sources': 0
        }
    
    # 等级权重映射
    level_weights = {'S': 1.0, 'A': 0.8, 'B': 0.6, 'C': 0.4}
    
    weighted_sum = 0
    weight_total = 0
    
    for pub in publications:
        grade = calculate_grade(pub)
        relevance = pub.get('relevance_score', 1.0)
        
        weight = relevance * grade.confidence
        weighted_sum += level_weights[grade.level.value] * weight
        weight_total += weight
    
    avg_score = weighted_sum / weight_total if weight_total > 0 else 0
    
    # 确定聚合等级
    if avg_score >= 0.85:
        aggregate_level = "strong"     # 强证据
    elif avg_score >= 0.65:
        aggregate_level = "moderate"   # 中等证据
    elif avg_score >= 0.45:
        aggregate_level = "weak"       # 弱证据
    else:
        aggregate_level = "insufficient"  # 证据不足
    
    return {
        'aggregate_level': aggregate_level,
        'confidence': round(avg_score, 2),
        'total_sources': len(publications),
        'grade_distribution': {
            'S': sum(1 for p in publications if calculate_grade(p).level == EvidenceLevel.S),
            'A': sum(1 for p in publications if calculate_grade(p).level == EvidenceLevel.A),
            'B': sum(1 for p in publications if calculate_grade(p).level == EvidenceLevel.B),
            'C': sum(1 for p in publications if calculate_grade(p).level == EvidenceLevel.C),
        }
    }
```

---

## 六、数据流与处理

### 6.1 文档索引流程

```
文档输入
    │
    ▼
┌─────────────────────────────────────────────┐
│  1. Document Parsing                       │
│     • 文本提取 (PDF/DOCX/TXT)              │
│     • 元数据提取 (标题、作者、日期)         │
│     • 文件路径记录                          │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  2. Chunking (证据 Splitter)                │
│     • 滑动窗口分块                          │
│     • 保留段落边界                          │
│     • 生成 chunk_id                         │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  3. Entity & Relation Extraction            │
│     • 使用 evidence_extraction_prompt       │
│     • 生成 evidence_level                   │
│     • 生成 evidence_chain_id                │
│     • 记录 source_provenance                │
└─────────────────────────────────────────────┘
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
┌──────────┐    ┌──────────────┐   ┌──────────────┐
│  Graph   │    │   Vector     │   │    KV       │
│  Store   │    │   Store      │   │   Store     │
│          │    │              │   │              │
│ Nodes    │    │  Embeddings │   │  Documents  │
│ + Edges  │    │  + Metadata  │   │  + Chunks   │
└──────────┘    └──────────────┘   └──────────────┘
```

### 6.2 查询流程

```
用户查询
    │
    ▼
┌─────────────────────────────────────────────┐
│  Query Understanding                         │
│  • 关键词提取 (high_level + low_level)       │
│  • 查询意图分类                              │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Hybrid Retrieval                            │
│  ┌─────────────────┐ ┌─────────────────┐    │
│  │ Vector Search   │ │  Graph Search   │    │
│  │ (语义相似度)    │ │  (关系推理)     │    │
│  └────────┬────────┘ └────────┬────────┘    │
│           │                   │              │
│           └────────┬───────────┘              │
│                    ▼                         │
│            Reranking & Fusion               │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Evidence Processing                        │
│  • 证据等级排序                             │
│  • 溯源信息附加                             │
│  • 证据链关联                               │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  LLM Generation                             │
│  • Chain-of-Evidence Prompt                 │
│  • 引用标注                                 │
│  • Evidence Bundle 输出                      │
└─────────────────────────────────────────────┘
    │
    ▼
响应 + 引用列表
```

---

## 七、存储配置

### 7.1 支持的存储后端

| 类型 | 支持实现 |
|------|---------|
| **KV Storage** | JsonKVStorage, PGKVStorage, RedisKVStorage, MongoKVStorage |
| **Vector Storage** | NanoVectorDBStorage, PGVectorStorage, MilvusVectorDBStorage, FaissVectorDBStorage, QdrantVectorDBStorage, MongoVectorDBStorage |
| **Graph Storage** | NetworkXStorage, Neo4JStorage, PGGraphStorage, MemgraphStorage |
| **Doc Status** | JsonDocStatusStorage, PGDocStatusStorage, MongoDocStatusStorage |

### 7.2 Neo4j 连接配置

```python
# 环境变量配置
export NEO4J_URI="neo4j://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
export NEO4J_DATABASE="neo4j"
export NEO4J_WORKSPACE="evidence_chain"  # 数据隔离

# 初始化 LightRAG
rag = LightRAG(
    working_dir="./rag_storage",
    graph_storage="Neo4JStorage",  # 使用 Neo4j
    # ...其他配置
)
```

---

## 八、使用示例

### 8.1 初始化与索引

```python
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed

WORKING_DIR = "./evidence_rag_storage"

async def main():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=gpt_4o_mini_complete,
        embedding_func=openai_embed,
    )
    
    await rag.initialize_storages()
    
    # 插入文档 (支持文件路径追溯)
    documents = [
        "央行发布《关于进一步完善结构性货币政策工具的通知》...",
        "根据Wind数据显示，2024年四季度科创板企业融资规模..."
    ]
    file_paths = [
        "/docs/央行政策文件.pdf",
        "/docs/市场数据.xlsx"
    ]
    
    await rag.ainsert(documents, file_paths=file_paths)
```

### 8.2 查询与证据追溯

```python
# 基础查询
result = await rag.aquery(
    "科技创新领域的融资政策有哪些?",
    param=QueryParam(
        mode="hybrid",
        top_k=10,
    )
)

# 查询结果包含:
# - 生成的回答 (带引用)
# - 引用的文档列表
# - 证据等级信息

# 获取检索到的证据详情
result_with_evidence = await rag.aquery(
    "银发〔2025〕18号的主要内容是什么?",
    param=QueryParam(
        mode="hybrid",
        only_need_context=True,  # 只获取检索上下文
    )
)
```

---

## 九、扩展与优化

### 9.1 可扩展方向

1. **证据时效性管理**
   - 添加 `valid_from` / `valid_to` 时间属性
   - 自动过期处理

2. **多模态证据**
   - 图表、公式的证据标注
   - 图像内容的实体识别

3. **自动化证据分级**
   - 集成 GRADE 系统
   - 风险偏倚评估

4. **证据链可视化**
   - 因果关系图谱
   - 证据溯源路径

### 9.2 性能优化

- 批量嵌入 (embedding_batch_num)
- 异步并发 (llm_model_max_async)
- 缓存策略 (enable_llm_cache)
- 图数据库索引优化

---

## 十、附录

### A. 相关文件

| 文件路径 | 说明 |
|---------|------|
| `lightrag/types.py` | 证据链类型定义 (EvidenceLevel, SourceProvenance等) |
| `lightrag/prompt.py` | 证据提取 Prompt (entity_extraction_with_evidence) |
| `lightrag/kg/neo4j_impl.py` | Neo4j 存储实现 (证据查询API) |
| `lightrag/kg/postgres_impl.py` | PostgreSQL 证据列支持 |
| `lightrag/evidence_splitter.py` | 场景标签系统、证据等级自动判定 |
| `lightrag/utils.py` | 证据字段处理工具 |
| `lightrag/utils_graph.py` | 证据图操作工具 |
| `lightrag/lightrag.py` | 主入口 (enable_evidence配置) |
| `tests/test_query_evidence_chain_ids.py` | 证据链查询测试 |
| `tests/test_evidence_fields_vector_storage.py` | 证据字段存储测试 |
| `lightrag/prompt.py` | 证据提取 Prompt |
| `lightrag/kg/neo4j_impl.py` | Neo4j 存储实现 |
| `lightrag/lightrag.py` | 主入口 |
| `tests/test_query_evidence_chain_ids.py` | 证据链测试 |

### B. 参考标准

- **GRADE**: Grading of Recommendations Assessment, Development and Evaluation
- **UMLS**: Unified Medical Language System
- **MeSH**: Medical Subject Headings
- **SNOMED CT**: Systematized Nomenclature of Medicine

---

### C. 证据等级与代码对应表

| 等级 | 判定来源 | 代码位置 |
|------|---------|----------|
| S | 文件名含"监管"/"央行"/"证监会" | evidence_splitter.py:1368 |
| A | 文件名含"研报"/"wind"/"journal" | evidence_splitter.py:1370 |
| B | 默认级别 | evidence_splitter.py:1375 |
| C | 未实现自动判定 | - |

### D. 关键配置参数

| 参数 | 环境变量 | 说明 |
|------|---------|------|
| enable_evidence | LIGHTRAG_ENABLE_EVIDENCE | 启用证据链功能 |
| Neo4j工作空间 | NEO4J_WORKSPACE | 数据隔离 |
| 证据字段 | evidence_level | 证据等级 (S/A/B/C) |
| 证据链ID | evidence_chain_ids | JSON数组 |
| 场景标签 | scene_tags | JSON数组 |

---

*文档版本: v1.1* (更新于 2026-03-01)
