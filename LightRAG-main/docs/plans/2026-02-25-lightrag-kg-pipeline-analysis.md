# LightRAG 知识图谱入图全流程逻辑分析

## 一、整体架构流程图

```
                           文档插入流程 (Insert Pipeline)                      

  ┌─────────┐    ┌──────────────┐    ┌─────────────────┐    ┌───────────────┐
  │  文档   │ →  │   文本分块   │ →  │ 实体/关系提取   │ →  │   图谱合并    │
  │ (Input) │    │ (Chunking)  │    │ (Extraction)   │    │   (Merge)    │
  └─────────┘    └──────────────┘    └─────────────────┘    └───────────────┘
                                         ↓                         ↓
                                  ┌──────────────┐         ┌──────────────┐
                                  │  LLM 调用    │         │ 存储写入     │
                                  │ (GPT/本地)  │         │ (Graph+VDB)  │
                                  └──────────────┘         └──────────────┘
```

---

## 二、详细流程阶段

### 阶段1: 文档入队 (Enqueue)

**入口方法**: `ainsert()` / `apipeline_enqueue_documents()`

```python
# lightrag/lightrag.py
async def ainsert(self, input, ids=None, file_paths=None, track_id=None):
    track_id = generate_track_id("insert")
    await self.apipeline_enqueue_documents(input, ids, file_paths, track_id)
    await self.apipeline_process_enqueue_documents(...)
    return track_id
```

**主要操作**:
1. 生成唯一文档ID (MD5哈希)
2. 生成track_id用于进度追踪
3. 检查重复文档并过滤
4. 初始化文档状态

---

### 阶段2: 文本分块 (Chunking)

**入口方法**: `chunking_by_token_size()`

**分块策略**:
- 基于tokenizer分块 (默认: tiktoken)
- 默认块大小: `chunk_token_size=1200` tokens
- 重叠大小: `chunk_overlap_token_size=100` tokens

```python
# 分块参数
chunk_token_size: int = 1200          # 每块最大token数
chunk_overlap_token_size: int = 100    # 块间重叠token数
```

**分块输出**:
```python
{
    "chunk-xxxxx": {
        "content": "文本内容...",
        "full_doc_id": "doc-xxxxx",
        "tokens": 1200,
        "chunk_order_index": 0,
        "file_path": "xxx.txt"
    }
}
```

---

### 阶段3: 实体/关系提取 (Entity Extraction)

**核心函数**: `extract_entities()` (lightrag/operate.py)

#### 3.1 LLM调用流程

```python
async def extract_entities(chunks, global_config, ...):
    # 1. 准备Prompt
    entity_extraction_system_prompt = PROMPTS["entity_extraction_system_prompt"].format(**context_base)
    entity_extraction_user_prompt = PROMPTS["entity_extraction_user_prompt"].format(**{**context_base, "input_text": content})
    
    # 2. 调用LLM (带缓存)
    final_result, timestamp = await use_llm_func_with_cache(
        entity_extraction_user_prompt,
        use_llm_func,
        system_prompt=entity_extraction_system_prompt,
        llm_response_cache=llm_response_cache,
        cache_type="extract",
    )
    
    # 3. Gleaning (可选) - 多次迭代补充实体
    for i in range(entity_extract_max_gleaning):
        # 继续提取更多实体...
```

#### 3.2 Prompt模板

**System Prompt** (lightrag/prompt.py):
```
---Role---
You are a knowledge graph builder...

---Task---
Extract entities and relationships from the given text.
Output Format:
- Entity: entity<|>entity_name<|>entity_type<|>entity_description
- Relation: relation<|>source_entity<|>target_entity<|>keywords<|>description
```

**User Prompt**:
```
Extract all entities and relationships from the below text:

<Entity_types>
{entity_types_list}
</Entity_types>

<Input Text>
{chunk_content}
</Input Text>

<Output>
```

#### 3.3 解析函数

```python
# 解析LLM输出
maybe_nodes, maybe_edges = await _process_extraction_result(
    final_result, chunk_key, timestamp, file_path
)
```

**输出格式**:
```python
# maybe_nodes: {entity_name: [entity_data, ...]}
{
    "Elon Musk": [
        {"entity_type": "PERSON", "description": "CEO of Tesla", "source_id": "chunk-xxx", ...}
    ]
}

# maybe_edges: {(src, tgt): [edge_data, ...]}
{
    ("Elon Musk", "Tesla"): [
        {"keywords": "CEO, founder", "description": "Elon is CEO of Tesla", ...}
    ]
}
```

---

### 阶段4: 图谱合并 (Graph Merge)

**核心函数**: `merge_nodes_and_edges()` (lightrag/operate.py)

采用**两阶段合并**策略:

```
                    两阶段合并流程                            

  ┌──────────────────┐    ┌──────────────────┐
  │   Phase 1        │    │   Phase 2        │
  │   合并实体        │ →  │   合并关系       │
  │ (Process Nodes)  │    │ (Process Edges)  │
  └──────────────────┘    └──────────────────┘
          ↓                         ↓
  ┌──────────────────┐    ┌──────────────────┐
  │ Graph Storage    │    │ Graph Storage    │
  │ Entities VDB     │    │ Relations VDB    │
  └──────────────────┘    └──────────────────┘
```

#### 4.1 实体合并逻辑 `_merge_nodes_then_upsert()`

```python
async def _merge_nodes_then_upsert(entity_name, nodes_data, ...):
    # 1. 获取已存在实体
    already_node = await knowledge_graph_inst.get_node(entity_name)
    
    # 2. 合并source_id列表
    full_source_ids = merge_source_ids(existing, new_source_ids)
    
    # 3. 实体类型选择 (最常见的类型)
    final_entity_type = most_common_type(existing_type, new_type)
    
    # 4. 去重 (按description)
    unique_nodes = {desc: dp for dp in nodes}
    
    # 5. 描述合并 (使用LLM生成摘要)
    if len(unique_nodes) > 1:
        final_description = await _handle_entity_relation_summary(...)
    
    # 6. 写入图数据库
    await knowledge_graph_inst.upsert_node(entity_name, node_data)
    
    # 7. 写入向量数据库
    await entities_vdb.upsert({entity_vdb_id: {...}})
```

#### 4.2 关系合并逻辑 `_merge_edges_then_upsert()`

类似实体的合并逻辑:
- 合并source_id和file_path
- 合并keywords
- 去重后更新描述

---

### 阶段5: 持久化 (Persistence)

**入口方法**: `_insert_done()`

```python
async def _insert_done(...):
    tasks = [
        # 13个存储实例同时持久化
        full_docs.index_done_callback(),
        doc_status.index_done_callback(),
        text_chunks.index_done_callback(),
        full_entities.index_done_callback(),
        full_relations.index_done_callback(),
        entity_chunks.index_done_callback(),
        relation_chunks.index_done_callback(),
        llm_response_cache.index_done_callback(),
        entities_vdb.index_done_callback(),
        relationships_vdb.index_done_callback(),
        chunks_vdb.index_done_callback(),
        chunk_entity_relation_graph.index_done_callback(),
    ]
    await asyncio.gather(*tasks)
```

---

## 三、数据存储目标

| 存储类型 | 存储内容 | 默认实现 |
|---------|---------|---------|
| **KV Storage** | 文档、文本块、LLM缓存 | JsonKVStorage |
| **Vector Storage** | 实体向量、关系向量、块向量 | NanoVectorDBStorage |
| **Graph Storage** | 实体关系图 | NetworkXStorage |
| **Doc Status** | 文档处理状态 | JsonDocStatusStorage |

---

## 四、关键配置参数

```python
# 提取配置
entity_extract_max_gleaning: int = 1  # 迭代提取次数
entity_types: list = ["person", "organization", "location", "event", ...]

# 分块配置
chunk_token_size: int = 1200
chunk_overlap_token_size: int = 100

# 并发配置
llm_model_max_async: int = 4
max_parallel_insert: int = 2
```

---

## 五、完整调用链总结

```
API: rag.insert(text)
    ↓
[1] ainsert() → 生成track_id
    ↓
[2] apipeline_enqueue_documents() → 文档入队，状态初始化
    ↓
[3] apipeline_process_enqueue_documents()
    ↓
[4] chunking_by_token_size() → 文本分块
    ↓
[5] extract_entities() → LLM提取实体/关系
    ├── System Prompt + User Prompt → LLM
    ├── _process_extraction_result() → 解析输出
    └── (可选) gleaning循环 → 补充提取
    ↓
[6] merge_nodes_and_edges() → 两阶段合并
    ├── Phase 1: _merge_nodes_then_upsert()
    │   └── upsert_node() + entities_vdb.upsert()
    └── Phase 2: _merge_edges_then_upsert()
        └── upsert_edge() + relationships_vdb.upsert()
    ↓
[7] _insert_done() → 持久化到磁盘
```

---

## 六、核心文件位置

| 功能 | 文件路径 |
|-----|---------|
| 主入口 | `lightrag/lightrag.py` (类LightRAG) |
| 提取逻辑 | `lightrag/operate.py` (extract_entities, merge_nodes_and_edges) |
| Prompt模板 | `lightrag/prompt.py` |
| 图存储 | `lightrag/kg/networkx_impl.py` |
| 向量存储 | `lightrag/kg/nano_vector_db_impl.py` |

---

## 七、附录: 节点搜索取数逻辑

### 7.1 API入口层

位置：`lightrag/api/routers/graph_routes.py`

| 端点 | 方法 | 功能 | 参数 |
|-----|------|------|------|
| `/graph/label/list` | GET | 获取所有标签 | 无 |
| `/graph/label/popular` | GET | 获取热门标签 | `limit` (默认300) |
| `/graph/label/search` | GET | 模糊搜索标签 | `q` (查询词), `limit` (默认50) |
| `/graphs` | GET | 获取子图 | `label`, `max_depth`, `max_nodes` |

### 7.2 存储层实现

位置：`lightrag/kg/networkx_impl.py`

```python
# 获取所有标签
async def get_all_labels(self) -> list[str]:
    """获取图中所有节点标签（实体名）"""
    graph = await self._get_graph()
    labels = set()
    for node in graph.nodes():
        labels.add(str(node))
    return sorted(list(labels))

# 获取热门标签（按节点度数排序）
async def get_popular_labels(self, limit: int = 300) -> list[str]:
    """按节点度数（连接数）获取最热门的标签"""
    graph = await self._get_graph()
    degrees = dict(graph.degree())
    sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
    return [str(node) for node, _ in sorted_nodes[:limit]]

# 模糊搜索标签
async def search_labels(self, query: str, limit: int = 50) -> list[str]:
    """带相关性评分的模糊匹配搜索"""
    # 精确匹配 = 1000分, 前缀匹配 = 500分, 包含匹配 = 100-长度
```

### 7.3 搜索调用链

```
前端请求
   ↓
[API层] graph_routes.py
   ├── /graph/label/list     → rag.get_graph_labels()
   ├── /graph/label/popular  → rag.chunk_entity_relation_graph.get_popular_labels()
   ├── /graph/label/search   → rag.chunk_entity_relation_graph.search_labels()
   └── /graphs               → rag.get_knowledge_graph()
   ↓
[主类层] lightrag.py → chunk_entity_relation_graph
   ↓
[存储层] networkx_impl.py
```

---

## 八、核心代码逻辑详解

### 8.1 完整Prompt模板 (prompt.py)

#### System Prompt - 实体关系提取系统指令

```python
PROMPTS["entity_extraction_system_prompt"] = """---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

---Instructions---
1. **Entity Extraction & Output:**
    * **Identification:** Identify clearly defined and meaningful entities in the input text.
    * **Entity Details:** For each identified entity, extract:
        * `entity_name`: The name of the entity (title case)
        * `entity_type`: One of: {entity_types} (person, organization, location, event, concept, method, etc.)
        * `entity_description`: Concise description based on input text
    * **Output Format:** `entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description`

2. **Relationship Extraction & Output:**
    * **N-ary Relationship Decomposition:** Split relationships into binary pairs
    * **Output Format:** `relation{tuple_delimiter}source_entity{tuple_delimiter}target_entity{tuple_delimiter}relationship_keywords{tuple_delimiter}relationship_description`

3. **Delimiter:** Use `{tuple_delimiter}` (default: `<|#|>`) as field separator
4. **Direction:** Treat relationships as **undirected** unless explicitly stated
5. **Language:** Output in `{language}` (default: English)
6. **Completion:** End with `{completion_delimiter}` (default: `<|COMPLETE|>`)

---Examples---
{examples}
"""
```

#### User Prompt - 实体关系提取任务指令

```python
PROMPTS["entity_extraction_user_prompt"] = """---Task---
Extract entities and relationships from the input text in Data to be Processed below.

---Instructions---
1. Strictly adhere to all format requirements
2. Output only the extracted list
3. End with {completion_delimiter}
4. Output language: {language}

---Data to be Processed---
<Entity_types>
[{entity_types}]

<Input Text>
```
{input_text}
```

<Output>
"""
```

#### Gleaning Prompt - 补充提取指令

```python
PROMPTS["entity_continue_extraction_user_prompt"] = """---Task---
Based on the last extraction, identify **missed or incorrectly formatted** entities and relationships.

---Instructions---
1. Do NOT re-output correctly extracted items
2. Focus on missed or incorrectly formatted items
3. Output format same as before
4. End with {completion_delimiter}

<Output>
"""
```

---

#### 中文翻译版 Prompt

**System Prompt 中文说明**:
```
---角色---
你是一个知识图谱专家，负责从输入文本中提取实体和关系。

---指令---
1. **实体提取与输出：**
    * **识别：** 识别输入文本中明确定义且有意义的实体。
    * **实体详情：** 对每个识别的实体，提取以下信息：
        * `entity_name`：实体名称（首字母大写）
        * `entity_type`：实体类型，可选值：{entity_types}（人物、组织、地点、事件、概念、方法等）
        * `entity_description`：基于输入文本的简洁描述
    * **输出格式：** `entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description`

2. **关系提取与输出：**
    * **N元关系分解：** 将多实体关系分解为二元关系对
    * **输出格式：** `relation{tuple_delimiter}source_entity{tuple_delimiter}target_entity{tuple_delimiter}relationship_keywords{tuple_delimiter}relationship_description`

3. **分隔符：** 使用 `{tuple_delimiter}`（默认：`<|#|>`）作为字段分隔符
4. **方向：** 将关系视为**无向**（除非明确指定）
5. **语言：** 输出语言为 `{language}`（默认：English）
6. **完成信号：** 以 `{completion_delimiter}`（默认：`<|COMPLETE|>`）结束

---示例---
{examples}
```

**User Prompt 中文说明**:
```
---任务---
从下方"待处理数据"部分的输入文本中提取实体和关系。

---指令---
1. 严格遵守所有格式要求
2. 仅输出提取的列表
3. 以 {completion_delimiter} 结尾
4. 输出语言：{language}

---待处理数据---
<Entity_types>
[{entity_types}]

<Input Text>
```
{input_text}
```

<Output>
```
```

**Gleaning Prompt 中文说明**:
```
---任务---
基于上一次提取任务，识别并提取**遗漏的或格式错误的**实体和关系。

---指令---
1. 不要重新输出已正确提取的项目
2. 专注于遗漏或格式错误的项目
3. 输出格式与之前相同
4. 以 {completion_delimiter} 结尾

<Output>
```
```

---

### 8.2 LLM缓存机制 (utils.py)

---

### 8.2 LLM缓存机制 (utils.py)

#### 核心函数: `use_llm_func_with_cache()`

```python
async def use_llm_func_with_cache(
    user_prompt: str,
    use_llm_func: callable,
    llm_response_cache: BaseKVStorage = None,
    system_prompt: str = None,
    max_tokens: int = None,
    history_messages: list = None,
    cache_type: str = "extract",  # "extract" | "summary"
    chunk_id: str = None,
    cache_keys_collector: list = None,
) -> tuple[str, int]:
    """带缓存的LLM调用函数"""
    
    # 1. 文本 sanitizer (防止UTF-8编码错误)
    safe_user_prompt = sanitize_text_for_encoding(user_prompt)
    safe_system_prompt = sanitize_text_for_encoding(system_prompt) if system_prompt else None
    
    # 2. 缓存命中检测
    if llm_response_cache:
        # 生成缓存键: cache_key = generate_cache_key(mode, cache_type, arg_hash)
        arg_hash = compute_args_hash(prompt)  # 对prompt内容哈希
        cache_key = generate_cache_key("default", cache_type, arg_hash)
        
        cached_result = await handle_cache(
            llm_response_cache, arg_hash, prompt, "default", cache_type=cache_type
        )
        
        if cached_result:
            # 缓存命中! 直接返回
            statistic_data["llm_cache"] += 1
            return content, timestamp  # 返回缓存的时间和内容
    
    # 3. 缓存未命中 - 调用LLM
    statistic_data["llm_call"] += 1
    res = await use_llm_func(safe_user_prompt, system_prompt=safe_system_prompt, **kwargs)
    
    # 4. 保存到缓存
    timestamp = int(time.time())
    await llm_response_cache.upsert({
        cache_key: {
            "prompt": prompt,
            "return": res,
            "create_time": timestamp,
            "cache_type": cache_type
        }
    })
    
    return res, timestamp
```

**缓存键生成逻辑**:
```python
def generate_cache_key(mode: str, cache_type: str, arg_hash: str) -> str:
    """生成缓存键: {mode}:{cache_type}:{hash}"""
    return f"{mode}:{cache_type}:{arg_hash}"

def compute_args_hash(args_str: str) -> str:
    """计算参数哈希: MD5(prompt)"""
    return compute_mdhash_id(args_str, prefix="cache-")
```

---

### 8.3 实体合并核心算法 (_merge_nodes_then_upsert)

#### 完整合并流程

```python
async def _merge_nodes_then_upsert(entity_name, nodes_data, ...):
    """
    实体合并核心算法 - 共9个步骤
    """
    
    # ========== Step 1: 获取已存在实体 ==========
    already_node = await knowledge_graph_inst.get_node(entity_name)
    if already_node:
        already_entity_types.append(already_node["entity_type"])
        already_source_ids.extend(already_node["source_id"].split(GRAPH_FIELD_SEP))
        already_file_paths.extend(already_node["file_path"].split(GRAPH_FIELD_SEP))
        already_description.extend(already_node["description"].split(GRAPH_FIELD_SEP))
    
    # ========== Step 2: 合并source_id列表 ==========
    # 从已有实体和entity_chunks_storage获取已有source_ids
    existing_full_source_ids = ...
    
    # 合并新旧source_ids (去重)
    full_source_ids = merge_source_ids(existing_full_source_ids, new_source_ids)
    
    # 更新entity_chunks_storage (记录每个实体关联的chunk列表)
    await entity_chunks_storage.upsert({
        entity_name: {"chunk_ids": full_source_ids, "count": len(full_source_ids)}
    })
    
    # ========== Step 3: 应用source_ids限制 ==========
    # max_source_limit: 最多保留的source数量 (默认10)
    # limit_method: KEEP (保留最早的) | FIFO (保留最新的)
    source_ids = apply_source_ids_limit(full_source_ids, max_source_limit, limit_method)
    
    # ========== Step 4: 根据限制过滤节点 ==========
    if limit_method == "KEEP":
        # 只保留未被过滤的节点
        filtered_nodes = [dp for dp in nodes_data if dp.get("source_id") in allowed_source_ids]
        nodes_data = filtered_nodes
    
    # ========== Step 5: 最终确定entity_type ==========
    # 选择出现次数最多的类型
    entity_type = Counter(
        [dp["entity_type"] for dp in nodes_data] + already_entity_types
    ).most_common(1)[0][0]
    
    # ========== Step 6: 去重 (按description) ==========
    unique_nodes = {}
    for dp in nodes_data:
        desc = dp.get("description")
        if desc and desc not in unique_nodes:
            unique_nodes[desc] = dp
    
    # 按时间戳+描述长度排序
    sorted_nodes = sorted(
        unique_nodes.values(),
        key=lambda x: (x.get("timestamp", 0), -len(x.get("description", "")))
    )
    
    # ========== Step 7: LLM描述摘要 (Map-Reduce) ==========
    # 如果多个描述, 使用LLM生成摘要
    description_list = already_description + [dp["description"] for dp in sorted_nodes]
    final_description, llm_used = await _handle_entity_relation_summary(
        "Entity", entity_name, description_list, GRAPH_FIELD_SEP, global_config, llm_cache
    )
    
    # ========== Step 8: 构建file_path ==========
    # 限制最大文件路径数量
    file_paths_list = ...  # 合并已有和新file_paths, 去重, 截断
    
    # ========== Step 9: 写入存储 ==========
    # 写入图数据库
    await knowledge_graph_inst.upsert_node(entity_name, {
        "entity_id": entity_name,
        "entity_type": entity_type,
        "description": final_description,
        "source_id": GRAPH_FIELD_SEP.join(source_ids),
        "file_path": GRAPH_FIELD_SEP.join(file_paths_list),
        "created_at": timestamp,
    })
    
    # 写入向量数据库 (用于语义搜索)
    entity_vdb_id = compute_mdhash_id(entity_name, prefix="ent-")
    await entities_vdb.upsert({
        entity_vdb_id: {
            "content": f"{entity_name}\n{final_description}",
            "entity_name": entity_name,
            "entity_type": entity_type,
            "description": final_description,
            "source_id": ...
        }
    })
```

---

### 8.4 描述摘要Map-Reduce算法 (_handle_entity_relation_summary)

#### 算法流程

```python
async def _handle_entity_relation_summary(
    description_type: str,           # "Entity" | "Relation"
    entity_or_relation_name: str,
    description_list: list[str],
    seperator: str,
    global_config: dict,
    llm_response_cache = None
) -> tuple[str, bool]:
    """
    使用Map-Reduce策略对多个描述进行摘要
    
    决策逻辑:
    - 如果只有1个描述 → 直接返回, 无需LLM
    - 如果总token < summary_context_size 且 len < force_llm_summary_on_merge → 直接拼接
    - 否则 → 进入Map-Reduce流程
    """
    
    # 配置参数
    summary_context_size = global_config["summary_context_size"]      # 默认3000
    summary_max_tokens = global_config["summary_max_tokens"]           # 默认500
    force_llm_summary_on_merge = global_config["force_llm_summary_on_merge"]  # 默认5
    
    # ========== Map阶段: 分块 ==========
    # 将描述列表按token限制分成多块
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for desc in description_list:
        desc_tokens = len(tokenizer.encode(desc))
        
        if current_tokens + desc_tokens > summary_context_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [desc]
            current_tokens = desc_tokens
        else:
            current_chunk.append(desc)
            current_tokens += desc_tokens
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # ========== Reduce阶段: 摘要每块 ==========
    new_summaries = []
    for chunk in chunks:
        if len(chunk) == 1:
            # 单描述不需LLM
            new_summaries.append(chunk[0])
        else:
            # 多描述调用LLM摘要
            summary = await _summarize_descriptions(
                description_type, entity_or_relation_name, chunk, global_config, llm_cache
            )
            new_summaries.append(summary)
    
    # ========== 递归处理直到满足条件 ==========
    # 如果新摘要列表仍超过限制, 递归处理
    if len(new_summaries) > 2 or total_tokens > summary_context_size:
        return await _handle_entity_relation_summary(
            description_type, entity_or_relation_name, new_summaries, ...
        )
    
    # 最终摘要
    final_summary = await _summarize_descriptions(..., new_summaries, ...)
    return final_summary, True
```

#### LLM摘要Prompt

```python
PROMPTS["summarize_entity_descriptions"] = """---Task---
Summarize multiple description for {description_type}: {description_name}

---Instructions---
1. Create a comprehensive summary that combines information from all descriptions
2. Remove redundant information, keep unique details
3. Maintain key facts, attributes, and relationships
4. Output in {language}
5. Keep summary under {summary_length} tokens

---Descriptions to Summarize---
{description_list}

---Summary---
"""
```

---

### 8.5 关系合并核心算法 (_merge_edges_then_upsert)

```python
async def _merge_edges_then_upsert(
    src_id: str,                    # 源实体名
    tgt_id: str,                    # 目标实体名
    edges_data: list[dict],          # 待合并的关系数据
    knowledge_graph_inst,
    relationships_vdb,
    entity_vdb,
    global_config,
    ...
):
    """
    关系合并逻辑 - 与实体合并类似
    """
    
    # 1. 获取已存在的关系
    already_edge = await knowledge_graph_inst.get_edge(src_id, tgt_id)
    
    # 2. 合并keywords (去重, 保留所有关键词)
    already_keywords = already_edge.get("keywords", "").split(",") if already_edge else []
    new_keywords = [dp.get("keywords", "") for dp in edges_data]
    all_keywords = list(set(already_keywords + new_keywords))
    
    # 3. 合并source_id和file_path
    full_source_ids = merge_source_ids(...)
    
    # 4. 描述合并 (与实体相同)
    description_list = already_description + [dp["description"] for dp in edges_data]
    final_description, llm_used = await _handle_entity_relation_summary(
        "Relation", f"{src_id}-{tgt_id}", description_list, ...
    )
    
    # 5. 写入图数据库 (无向边, 双向存储)
    await knowledge_graph_inst.upsert_edge(src_id, tgt_id, {
        "src_id": src_id,
        "tgt_id": tgt_id,
        "keywords": ",".join(all_keywords),
        "description": final_description,
        "weight": sum([dp.get("weight", 1.0) for dp in edges_data]),
        "source_id": full_source_ids,
        "file_path": ...
    })
    
    # 6. 写入关系向量数据库
    rel_vdb_id = compute_mdhash_id(f"{src_id}->{tgt_id}", prefix="rel-")
    await relationships_vdb.upsert({
        rel_vdb_id: {
            "src_id": src_id,
            "tgt_id": tgt_id,
            "content": f"{src_id} {keywords} {tgt_id}: {final_description}",
            "keywords": ",".join(all_keywords),
            "description": final_description,
            "weight": ...
        }
    })
```

---

### 8.6 数据结构汇总

#### 实体数据结构

```python
# 图数据库存储 (NetworkX)
node_data = {
    "entity_id": "Elon Musk",           # 实体名
    "entity_type": "person",             # 实体类型
    "description": "CEO of Tesla...",   # 合并后的描述
    "source_id": "chunk-1<|>chunk-2<|>chunk-3",  # 来源chunk ID列表
    "file_path": "doc1.txt<|>doc2.txt", # 来源文件列表
    "created_at": 1706123456,           # 创建时间戳
    "truncate": False
}

# 向量数据库存储 (用于语义搜索)
entity_vdb_data = {
    "id": "ent-abc123...",              # MD5哈希
    "content": "Elon Musk\nCEO of Tesla, founder of SpaceX...",  # 检索内容
    "entity_name": "Elon Musk",
    "entity_type": "person",
    "description": "CEO of Tesla...",
    "source_id": "chunk-1<|>chunk-2",
    "file_path": "doc1.txt"
}
```

#### 关系数据结构

```python
# 图数据库存储
edge_data = {
    "src_id": "Elon Musk",
    "tgt_id": "Tesla",
    "keywords": "CEO,founder,lead",    # 合并后的关键词
    "description": "Elon Musk is the CEO of Tesla...",
    "weight": 2.0,                      # 权重累加
    "source_id": "chunk-1<|>chunk-2",
    "file_path": "doc1.txt",
    "created_at": 1706123456,
    "truncate": False
}

# 向量数据库存储
relation_vdb_data = {
    "id": "rel-xyz789...",
    "src_id": "Elon Musk",
    "tgt_id": "Tesla",
    "content": "Elon Musk CEO,founder,lead Tesla: Elon Musk is the CEO of Tesla...",
    "keywords": "CEO,founder,lead",
    "description": "Elon Musk is the CEO of Tesla...",
    "weight": 2.0
}
```

---

#NW|---

#QB|## 九、入图谱完整数据结构详解

#KM|### 9.1 文档输入数据结构

#XZ|```python
#HM|# 文档原始输入
#XZ|input: str | list[str]  # 单个文档字符串或文档列表
#HV|
#JB|# 可选参数
#HV|ids: str | list[str] | None      # 文档ID列表，默认MD5哈希生成
#HV|file_paths: str | list[str] | None  # 文件路径，用于引用
#HV|track_id: str | None              # 追踪ID，用于进度查询
#WR|```

#VB|---

#KM|### 9.2 文本块数据结构 (TextChunkSchema)

#XZ|```python
#HM|# 文本块 (TextChunkSchema) - 分块后的基本数据单元
#KV|class TextChunkSchema(TypedDict):
#KM|    tokens: int              # token数量
#XZ|    content: str            # 文本内容
#HV|    full_doc_id: str       # 所属文档ID
#XZ|    chunk_order_index: int # 块在文档中的顺序索引
#WR|
#XZ|# 分块输出示例
#HM|{
#HV|    "chunk-abc123": {
#XZ|        "tokens": 1150,
#HV|        "content": "LightRAG is a retrieval-augmented generation system...",
#HV|        "full_doc_id": "doc-xyz789",
#XZ|        "chunk_order_index": 0,
#HV|        "file_path": "intro.txt"
#XZ|    }
#WR|}
#XZ|```

#QM|---

#KM|### 9.3 LLM提取的原始实体数据结构

#XZ|```python
#HM|# LLM提取后的单个实体 (从 _handle_single_entity_extraction 返回)
#XZ|# 格式: entity<|#|>entity_name<|#|>entity_type<|#|>entity_description
#XZ|#
#XZ|# 返回字典结构:
#KN|{
#XZ|    "entity_name": "Elon Musk",           # 实体名称 (已标准化)
#XZ|    "entity_type": "person",              # 实体类型 (小写)
#XZ|    "description": "CEO of Tesla and SpaceX...",  # 实体描述
#XZ|    "source_id": "chunk-abc123",         # 来源文本块ID
#XZ|    "file_path": "intro.txt",            # 来源文件路径
#XZ|    "timestamp": 1706123456              # 提取时间戳
#XZ|}
#XZ|```

#QV|#### 字段说明

#KN|- **entity_name**: 实体名称，经过`sanitize_and_normalize_extracted_text`处理
#XZ|  - 移除内部引号
#XZ|  - 首字母大写
#XZ|  - 去除前后空格
#KN|- **entity_type**: 实体类型
#XZ|  - 转换为小写
#XZ|  - 移除空格
#XZ|  - 验证不含特殊字符
#XZ|- **description**: 实体描述
#XZ|  - 基于输入文本生成
#XZ|  - 经过文本清洗
#XZ|- **source_id**: 来源文本块ID (chunk-xxx格式)
#XZ|- **file_path**: 来源文件路径
#XZ|- **timestamp**: Unix时间戳

#VB|---

#KM|### 9.4 LLM提取的原始关系数据结构

#XZ|```python
#HM|# LLM提取后的单个关系 (从 _handle_single_relationship_extraction 返回)
#XZ|# 格式: relation<|#|>source_entity<|#|>target_entity<|#|>keywords<|#|>description
#XZ|#
#XZ|# 返回字典结构:
#KN|{
#XZ|    "src_id": "Elon Musk",                # 源实体名称
#XZ|    "tgt_id": "Tesla",                    # 目标实体名称
#XZ|    "weight": 1.0,                        # 关系权重 (默认1.0)
#XZ|    "description": "Elon Musk is the CEO of Tesla...",  # 关系描述
#XZ|    "keywords": "CEO,founder,lead",       # 关键词 (逗号分隔)
#XZ|    "source_id": "chunk-abc123",         # 来源文本块ID
#XZ|    "file_path": "intro.txt",            # 来源文件路径
#XZ|    "timestamp": 1706123456              # 提取时间戳
#XZ|}
#XZ|```

#QV|#### 字段说明

#KN|- **src_id**: 源实体名称
#XZ|- **tgt_id**: 目标实体名称
#XZ|- **weight**: 关系权重
#XZ|  - 从LLM输出的第5个字段解析
#XZ|  - 默认为1.0
#XZ|- **keywords**: 关键词
#XZ|  - 逗号分隔
#XZ|  - 中文逗号自动转换为英文逗号
#XZ|- **description**: 关系描述
#XZ|- **source_id/file_path/timestamp**: 同实体结构

#VB|---

#KM|### 9.5 合并后的实体数据结构

#XZ|```python
#HM|# ======== 图数据库存储 (NetworkX) ========
#XZ|# 最终写入图数据库的实体节点数据
#KN|{
#XZ|    "entity_id": "Elon Musk",                    # 实体ID (同entity_name)
#XZ|    "entity_type": "person",                      # 实体类型 (出现次数最多)
#XZ|    "description": "CEO of Tesla and SpaceX, founded X...",  # LLM合并后的描述
#XZ|    "source_id": "chunk-1<|>chunk-2<|>chunk-3",   # 所有来源chunk ID (分隔符连接)
#XZ|    "file_path": "doc1.txt<|>doc2.txt",          # 所有来源文件 (分隔符连接)
#XZ|    "created_at": 1706123456,                    # 创建时间戳
#XZ|    "truncate": False                              # 是否被截断
#XZ|}

#HM|# ======== 向量数据库存储 (Vector DB) ========
#XZ|# 用于语义搜索的向量数据
#XZ|# ID生成: compute_mdhash_id(entity_name, prefix="ent-")
#KN|{
#XZ|    "id": "ent-8f14e45f-ceea-46...",              # MD5哈希ID
#XZ|    "content": "Elon Musk\nCEO of Tesla and SpaceX...",  # 检索内容 (name + description)
#XZ|    "entity_name": "Elon Musk",                    # 实体名称
#XZ|    "entity_type": "person",                       # 实体类型
#XZ|    "description": "CEO of Tesla and SpaceX...",   # 实体描述
#XZ|    "source_id": "chunk-1<|>chunk-2<|>chunk-3",   # 来源chunk ID
#XZ|    "file_path": "doc1.txt<|>doc2.txt"           # 来源文件
#XZ|}

#HM|# ======== 实体-Chunk关联存储 (Entity Chunks Storage) ========
#XZ|# 记录每个实体关联的所有chunk ID
#KN|{
#XZ|    "Elon Musk": {                                  # 实体名称作为key
#XZ|        "chunk_ids": ["chunk-1", "chunk-2", "chunk-3"],  # 关联chunk列表
#XZ|        "count": 3                                    # 关联数量
#XZ|}
#XZ|```

#VB|---

#KM|### 9.6 合并后的关系数据结构

#XZ|```python
#HM|# ======== 图数据库存储 (NetworkX) ========
#XZ|# 最终写入图数据库的边数据
#KN|{
#XZ|    "src_id": "Elon Musk",                       # 源实体
#XZ|    "tgt_id": "Tesla",                           # 目标实体
#XZ|    "keywords": "CEO,founder,lead,ownership",     # 合并后的关键词 (去重)
#XZ|    "description": "Elon Musk is the CEO and founder of Tesla...",  # LLM合并后的描述
#XZ|    "weight": 3.0,                               # 权重累加 (1.0 + 1.0 + 1.0)
#XZ|    "source_id": "chunk-1<|>chunk-2",           # 来源chunk ID
#XZ|    "file_path": "doc1.txt<|>doc2.txt",         # 来源文件
#XZ|    "created_at": 1706123456,
#XZ|    "truncate": False
#XZ|}

#HM|# ======== 向量数据库存储 (Vector DB) ========
#XZ|# 用于关系语义搜索的向量数据
#XZ|# ID生成: compute_mdhash_id(f"{src_id}->{tgt_id}", prefix="rel-")
#KN|{
#XZ|    "id": "rel-7c4a8f9b-2d1e-4...",             # MD5哈希ID
#XZ|    "src_id": "Elon Musk",                       # 源实体
#XZ|    "tgt_id": "Tesla",                          # 目标实体
#XZ|    "content": "Elon Musk CEO,founder,lead Tesla: Elon Musk is the CEO of Tesla...",
#XZ|    "keywords": "CEO,founder,lead,ownership",     # 合并后关键词
#XZ|    "description": "Elon Musk is the CEO and founder of Tesla...",
#XZ|    "weight": 3.0,                               # 累加权重
#XZ|    "file_path": "doc1.txt<|>doc2.txt"
#XZ|}

#HM|# ======== 关系-Chunk关联存储 (Relation Chunks Storage) ========
#XZ|# 记录每个关系关联的所有chunk ID
#XZ|# Key格式: (源实体, 目标实体) 元组序列化
#KN|{
#XZ|    "(Elon Musk, Tesla)": {                       # (src_id, tgt_id) 作为key
#XZ|        "chunk_ids": ["chunk-1", "chunk-2"],     # 关联chunk列表
#XZ|        "count": 2
#XZ|}
#XZ|```

#VB|---

#KM|### 9.7 完整数据流示意图

#XZ|```
#XZ|┌─────────────────────────────────────────────────────────────────────────────┐
#XZ|│                          文档入图完整数据流                                   │
#XZ|└─────────────────────────────────────────────────────────────────────────────┘

#XZ|  ┌─────────────┐
#XZ|  │  原始文档    │
#XZ|  │  (str/list) │
#XZ|  └──────┬──────┘
#XZ|         │
#XZ|         ▼
#XZ|  ┌─────────────────────────────────────┐
#XZ|  │  chunking_by_token_size()           │
#XZ|  │  输出: TextChunkSchema              │
#XZ|  │  - content                         │
#XZ|  │  - tokens                          │
#XZ|  │  - full_doc_id                    │
#XZ|  │  - chunk_order_index              │
#XZ|  └──────┬──────────────────────────────┘
#XZ|         │
#XZ|         ▼
#XZ|  ┌─────────────────────────────────────┐
#XZ|  │  extract_entities()                 │
#XZ|  │  调用LLM + 解析                     │
#XZ|  │                                     │
#XZ|  │  实体提取 → maybe_nodes            │
#XZ|  │  {entity_name: [entity_data]}      │
#XZ|  │                                     │
#XZ|  │  关系提取 → maybe_edges            │
#XZ|  │  {(src,tgt): [edge_data]}         │
#XZ|  └──────┬──────────────────────────────┘
#XZ|         │
#XZ|         ▼
#XZ|  ┌─────────────────────────────────────┐
#XZ|  │  merge_nodes_and_edges()            │
#XZ|  │  两阶段合并                         │
#XZ|  │                                     │
#XZ|  │  Phase1: 实体合并                  │
#XZ|  │  - merge source_id                 │
#XZ|  │  - merge file_path                 │
#XZ|  │  - select entity_type              │
#XZ|  │  - LLM summary description         │
#XZ|  │  Phase2: 关系合并                  │
#XZ|  │  - merge keywords                  │
#XZ|  │  - merge source_id                 │
#XZ|  │  - LLM summary description         │
#XZ|  └──────┬──────────────────────────────┘
#XZ|         │
#XZ|         ▼
#XZ|  ┌──────────────────────────────────────────────────────────────────────────┐
#XZ|  │                          存储写入 (13个存储实例)                          │
#XZ|  └──────────────────────────────────────────────────────────────────────────┘
#XZ|         │
#XZ|    ┌────┴────┬──────────┬──────────┬──────────┬──────────┐
#XZ|    ▼         ▼          ▼          ▼          ▼          ▼
#XZ| ┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
#XZ| │ full │ │ text │ │ entity │ │ entity │ │entity │ │relation│
#XZ| │_docs │ │chunks │ │ _chunks│ │  _vdb  │ │_graph │ │ _vdb  │
#XZ| └──────┘ └──────┘ └────────┘ └────────┘ └────────┘ └────────┘
#XZ|    │       │        │          │           │          │
#XZ|    ▼       ▼        ▼          ▼           ▼          ▼
#XZ| ┌──────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
#XZ| │KV存储│ │向量存储│ │KV关联  │ │向量搜索│ │图搜索  │ │向量搜索│
#XZ| │文档  │ │文本块 │ │实体-块 │ │实体   │ │实体   │ │关系   │
#XZ| └──────┘ └──────┘ └────────┘ └────────┘ └────────┘ └────────┘
#XZ|```

#VB|---

#KM|### 9.8 关键配置参数汇总

#XZ|```python
#HM|# ========== 分块配置 ==========
#XZ|chunk_token_size: int = 1200              # 每块最大token数
#XZ|chunk_overlap_token_size: int = 100        # 块间重叠token数

#HM|# ========== 提取配置 ==========
#XZ|entity_extract_max_gleaning: int = 1       # 迭代提取次数
#XZ|entity_types: list = [...]                 # 实体类型列表
#XZ|DEFAULT_TUPLE_DELIMITER: str = "<|#|>"     # 字段分隔符
#XZ|DEFAULT_COMPLETION_DELIMITER: str = "<|COMPLETE|>"  # 完成信号

#HM|# ========== 摘要配置 ==========
#XZ|summary_context_size: int = 3000           # 摘要上下文token限制
#XZ|summary_max_tokens: int = 500              # 摘要最大token数
#XZ|force_llm_summary_on_merge: int = 5        # 强制LLM摘要的描述数量阈值

#HM|# ========== 限制配置 ==========
#XZ|max_source_ids_per_entity: int = 10       # 实体最大source数量
#XZ|max_source_ids_per_relation: int = 10    # 关系最大source数量
#XZ|max_file_paths: int = 5                   # 最大文件路径数量
#XZ|source_ids_limit_method: str = "KEEP"     # KEEP(保留最早) | FIFO(保留最新)

#HM|# ========== 并发配置 ==========
#XZ|llm_model_max_async: int = 4               # 最大并发LLM请求
#XZ|max_parallel_insert: int = 2               # 并行处理文件数
#XZ|```

#VB|---

#KM|### 9.9 数据流向追踪示例

#XZ|```
#XZ|# 假设输入文档: "Elon Musk founded Tesla. He is the CEO of Tesla."

#XZ|# 1. 分块后 (假设1个chunk)
#XZ|{
#XZ|    "chunk-001": {
#XZ|        "content": "Elon Musk founded Tesla. He is the CEO of Tesla.",
#XZ|        "tokens": 20,
#XZ|        "full_doc_id": "doc-001",
#XZ|        "chunk_order_index": 0,
#XZ|        "file_path": "test.txt"
#XZ|}

#XZ|# 2. LLM提取后 (maybe_nodes)
#XZ|{
#XZ|    "Elon Musk": [{
#XZ|        "entity_name": "Elon Musk",
#XZ|        "entity_type": "person",
#XZ|        "description": "Founder of Tesla and CEO of Tesla",
#XZ|        "source_id": "chunk-001",
#XZ|        "file_path": "test.txt",
#XZ|        "timestamp": 1706123456
#XZ|    }],
#XZ|    "Tesla": [{
#XZ|        "entity_name": "Tesla",
#XZ|        "entity_type": "organization",
#XZ|        "description": "Electric vehicle company founded by Elon Musk",
#XZ|        "source_id": "chunk-001",
#XZ|        "file_path": "test.txt",
#XZ|        "timestamp": 1706123456
#XZ|    }]
#XZ|}

#XZ|# 3. LLM提取后 (maybe_edges)
#XZ|{
#XZ|    ("Elon Musk", "Tesla"): [{
#XZ|        "src_id": "Elon Musk",
#XZ|        "tgt_id": "Tesla",
#XZ|        "keywords": "founder,CEO",
#XZ|        "description": "Elon Musk founded Tesla and is the CEO",
#XZ|        "weight": 1.0,
#XZ|        "source_id": "chunk-001",
#XZ|        "file_path": "test.txt",
#XZ|        "timestamp": 1706123456
#XZ|    }]
#XZ|}

#XZ|# 4. 合并后 - 图数据库实体
#XZ|{
#XZ|    "entity_id": "Elon Musk",
#XZ|    "entity_type": "person",
#XZ|    "description": "Founder of Tesla and CEO of Tesla",
#XZ|    "source_id": "chunk-001",
#XZ|    "file_path": "test.txt",
#XZ|    "created_at": 1706123456,
#XZ|    "truncate": False
#XZ|}

#XZ|# 5. 合并后 - 图数据库关系
#XZ|{
#XZ|    "src_id": "Elon Musk",
#XZ|    "tgt_id": "Tesla",
#XZ|    "keywords": "founder,CEO",
#XZ|    "description": "Elon Musk founded Tesla and is the CEO",
#XZ|    "weight": 1.0,
#XZ|    "source_id": "chunk-001",
#XZ|    "file_path": "test.txt",
#XZ|    "created_at": 1706123456,
#XZ|    "truncate": False
#XZ|}
#XZ|```

#VB|---

---

#KM|## 十、向量数据库三表结构详解

#XZ|### 10.1 向量存储初始化配置

#XZ|```python
#XZ|# lightrag/lightrag.py 中的初始化代码
#XZ|
#XZ|# 实体向量存储
#XZ|self.entities_vdb = vector_db_storage_cls(
#XZ|    namespace=NameSpace.VECTOR_STORE_ENTITIES,  # "entities"
#XZ|    workspace=self.workspace,
#XZ|    embedding_func=self.embedding_func,
#XZ|    meta_fields={"entity_name", "source_id", "content", "file_path"},
#XZ|)
#XZ|
#XZ|# 关系向量存储
#XZ|self.relationships_vdb = vector_db_storage_cls(
#XZ|    namespace=NameSpace.VECTOR_STORE_RELATIONSHIPS,  # "relationships"
#XZ|    workspace=self.workspace,
#XZ|    embedding_func=self.embedding_func,
#XZ|    meta_fields={"src_id", "tgt_id", "source_id", "content", "file_path"},
#XZ|)
#XZ|
#XZ|# 文本块向量存储
#XZ|self.chunks_vdb = vector_db_storage_cls(
#XZ|    namespace=NameSpace.VECTOR_STORE_CHUNKS,  # "chunks"
#XZ|    workspace=self.workspace,
#XZ|    embedding_func=self.embedding_func,
#XZ|    meta_fields={"full_doc_id", "content", "file_path"},
#XZ|)
#XZ|```

#VB|---

#KM|### 10.2 实体向量表 (entities)

#QV|#### 表信息

#XZ|- **命名空间**: `entities`
#XZ|- **存储文件**: `vdb_entities.json`
#XZ|- **用途**: 存储实体向量，用于实体语义搜索

#QV|#### 数据结构

#XZ|```python
#XZ|# 写入数据 (upsert)
#XZ|{
#XZ|    "ent-8f14e45f-ceea-46...": {           # ID: MD5哈希(entity_name)
#XZ|        "entity_name": "Elon Musk",          # 实体名称
#XZ|        "source_id": "chunk-1<|>chunk-2",    # 来源chunk ID列表 (分隔符连接)
#XZ|        "content": "Elon Musk\nCEO of Tesla and SpaceX, founder of X...",  # 检索内容
#XZ|        "file_path": "doc1.txt<|>doc2.txt", # 来源文件列表
#XZ|        "vector": "base64_encoded..."        # 向量 (Float16压缩)
#XZ|    }
#XZ|},
#XZ|
#XZ|# 向量维度: embedding_func.embedding_dim (通常1536/768/1024等)
#XZ|# 存储格式: Float16 + zlib压缩 + Base64编码
#XZ|```

#QV|#### 查询使用

#XZ|- 查询模式: `local` / `mix` 模式下的实体检索
#XZ|- 匹配字段: `content` (实体名 + 描述)
#XZ|- 返回字段: `entity_name`, `entity_type`, `description`, `source_id`, `file_path`

#VB|---

#KM|### 10.3 关系向量表 (relationships)

#QV|#### 表信息

#XZ|- **命名空间**: `relationships`
#XZ|- **存储文件**: `vdb_relationships.json`
#XZ|- **用途**: 存储关系向量，用于关系语义搜索

#QV|#### 数据结构

#XZ|```python
#XZ|# 写入数据 (upsert)
#XZ|{
#XZ|    "rel-7c4a8f9b-2d1e-4...": {             # ID: MD5哈希(f"{src_id}->{tgt_id}")
#XZ|        "src_id": "Elon Musk",                # 源实体名称
#XZ|        "tgt_id": "Tesla",                    # 目标实体名称
#XZ|        "source_id": "chunk-1<|>chunk-2",    # 来源chunk ID
#XZ|        "content": "Elon Musk CEO,founder Tesla: Elon Musk is the CEO of Tesla...",
#XZ|        "file_path": "doc1.txt<|>doc2.txt", # 来源文件
#XZ|        "vector": "base64_encoded..."        # 向量
#XZ|    }
#XZ|}
#XZ|
#XZ|# 检索内容格式: "{src_id} {keywords} {tgt_id}: {description}"
#XZ|```

#QV|#### 查询使用

#XZ|- 查询模式: `global` / `mix` 模式下的关系检索
#XZ|- 匹配字段: `content` (源+关键词+目标+描述)
#XZ|- 返回字段: `src_id`, `tgt_id`, `keywords`, `description`, `weight`, `source_id`

#VB|---

#KM|### 10.4 文本块向量表 (chunks)

#QV|#### 表信息

#XZ|- **命名空间**: `chunks`
#XZ|- **存储文件**: `vdb_chunks.json`
#XZ|- **用途**: 存储文本块向量，用于基础RAG检索

#QV|#### 数据结构

#XZ|```python
#XZ|# 写入数据 (upsert)
#XZ|{
#XZ|    "chunk-abc123...": {                    # ID: MD5哈希(chunk内容)
#XZ|        "full_doc_id": "doc-xyz789",        # 所属文档ID
#XZ|        "content": "LightRAG is a retrieval-augmented generation system...",  # 文本内容
#XZ|        "file_path": "intro.txt",           # 来源文件
#XZ|        "vector": "base64_encoded..."        # 向量
#XZ|    }
#XZ|}
#XZ|```

#QV|#### 查询使用

#XZ|- 查询模式: `naive` 模式下的纯向量检索
#XZ|- 匹配字段: `content` (文本块内容)
#XZ|- 返回字段: `content`, `full_doc_id`, `chunk_order_index`, `file_path`

#VB|---

#KM|### 10.5 三表对比总结

#XZ|```
#XZ|+------------------+----------------+----------------------+-----------------------+
#XZ||     表名         |   命名空间      |      存储文件         |      用途             |
#XZ|+------------------+----------------+----------------------+-----------------------+
#XZ|| entities        | entities       | vdb_entities.json    | 实体语义搜索          |
#XZ|| relationships   | relationships  | vdb_relationships.json | 关系语义搜索        |
#XZ|| chunks          | chunks         | vdb_chunks.json      | 文本块向量检索        |
#XZ|+------------------+----------------+----------------------+-----------------------+

#XZ|
#XZ|+------------------+------------------------------------------+
#XZ|| 表名             | 检索内容 (content字段)                    |
#XZ|+------------------+------------------------------------------+
#XZ|| entities        | {entity_name}\n{entity_description}         |
#XZ|| relationships   | {src} {keywords} {tgt}: {description}   |
#XZ|| chunks          | {chunk文本内容}                         |
#XZ|+------------------+------------------------------------------+

#XZ|
#XZ|+------------------+------------------------------------------+
#XZ|| 表名             | 元字段 (meta_fields)                    |
#XZ|+------------------+------------------------------------------+
#XZ|| entities        | entity_name, source_id, content, file_path |
#XZ|| relationships   | src_id, tgt_id, source_id, content, file_path |
#XZ|| chunks          | full_doc_id, content, file_path         |
#XZ|+------------------+------------------------------------------+
#XZ|```

#VB|---

#KM|### 10.6 向量存储实现类 (NanoVectorDBStorage)

#XZ|```python
#XZ|# 默认实现: lightrag/kg/nano_vector_db_impl.py
#XZ|
#XZ|@dataclass
#XZ|class NanoVectorDBStorage(BaseVectorStorage):
#XZ|    """基于nano_vectordb的向量存储实现"""
#XZ|
#XZ|    def __post_init__(self):
#XZ|        self._client = NanoVectorDB(
#XZ|            self.embedding_func.embedding_dim,
#XZ|            storage_file=self._client_file_name,
#XZ|        )
#XZ|
#XZ|    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
#XZ|        """批量写入向量数据"""
#XZ|        # 1. 提取content字段
#XZ|        contents = [v["content"] for v in data.values()]
#XZ|        
#XZ|        # 2. 批量计算embedding
#XZ|        embeddings = await self.embedding_func(contents)
#XZ|        
#XZ|        # 3. 向量压缩存储 (Float16 + zlib + Base64)
#XZ|        vector_f16 = embeddings.astype(np.float16)
#XZ|        compressed_vector = zlib.compress(vector_f16.tobytes())
#XZ|        encoded_vector = base64.b64encode(compressed_vector).decode("utf-8")
#XZ|        
#XZ|        # 4. 写入存储
#XZ|        client.upsert(datas=list_data)
#XZ|
#XZ|    async def query(self, query: str, top_k: int) -> list[dict]:
#XZ|        """向量相似度查询"""
#XZ|        # 1. 计算查询向量
#XZ|        query_embedding = await self.embedding_func([query])
#XZ|        
#XZ|        # 2. 向量相似度搜索
#XZ|        results = client.search(
#XZ|            query_embedding[0],
#XZ|            top_k=top_k,
#XZ|            filters=...  # 可选过滤条件
#XZ|        )
#XZ|        
#XZ|        # 3. 返回结果 (包含meta_fields中的字段)
#XZ|        return results
#XZ|```

#QV|#### 向量压缩机制

#XZ|```
#XZ|原始向量: float32 (4 bytes per element)
#XZ|    ↓
#XZ|Float16转换: float16 (2 bytes per element)
#XZ|    ↓
#XZ|zlib压缩: 压缩数据 (通常可减少50-70%)
#XZ|    ↓
#XZ|Base64编码: 字符串存储
#XZ|```

#QV|#### 其他向量存储实现

#XZ|- **PGVectorStorage** (PostgreSQL) - `lightrag/kg/postgres_impl.py`
#XZ|- **MilvusVectorDBStorage** (Milvus) - `lightrag/kg/milvus_impl.py`
#XZ|- **QdrantVectorDBStorage** (Qdrant) - `lightrag/kg/qdrant_impl.py`
#XZ|- **MongoVectorDBStorage** (MongoDB) - `lightrag/kg/mongo_impl.py`
#XZ|- **FaissVectorDBStorage** (Faiss) - `lightrag/kg/faiss_impl.py`

#VB|---

---

#KM|## 十一、向量库与图数据库删除逻辑

#XZ|### 11.1 文档级删除 (adelete_by_doc_id)

#QM|#### 功能说明

#XZ|删除指定文档及其所有关联数据，包括：
#XZ|- 文档本身 (full_docs)
#XZ|- 文档状态 (doc_status)
#XZ|- 文本块 (chunks_vdb, text_chunks)
#XZ|- 实体 (entities_vdb, entity_chunks)
#XZ|- 关系 (relationships_vdb, relation_chunks)
#XZ|- 可选的LLM缓存

#QV|#### 核心流程 (7步删除)

#XZ|```
#XZ|adelete_by_doc_id(doc_id, delete_llm_cache=False)
#XZ|    │
#XZ|    ├── Step 1: 获取文档状态和chunk列表
#XZ|    │         doc_status.get_by_id(doc_id) → chunks_list
#XZ|    │
#XZ|    ├── Step 2: 收集LLM缓存ID (可选)
#XZ|    │         从text_chunks获取llm_cache_list
#XZ|    │
#XZ|    ├── Step 3: 分析受影响的实体和关系
#XZ|    │         full_entities.get_by_id(doc_id) → entity_names
#XZ|    │         full_relations.get_by_id(doc_id) → relation_pairs
#XZ|    │
#XZ|    │         判断: 删除/重建/保留
#XZ|    │         - 无剩余chunk → 删除
#XZ|    │         - 有变化 → 重建
#XZ|    │         - 无变化 → 保留
#XZ|    │
#XZ|    ├── Step 4: 删除文本块
#XZ|    │         chunks_vdb.delete(chunk_ids)
#XZ|    │         text_chunks.delete(chunk_ids)
#XZ|    │
#XZ|    ├── Step 5: 删除无剩余来源的关系
#XZ|    │         relationships_vdb.delete(rel_ids)
#XZ|    │         chunk_entity_relation_graph.remove_edges()
#XZ|    │         relation_chunks.delete()
#XZ|    │
#XZ|    ├── Step 6: 删除无剩余来源的实体
#XZ|    │         (先清理关联边)
#XZ|    │         relationships_vdb.delete(残留边)
#XZ|    │         chunk_entity_relation_graph.remove_nodes()
#XZ|    │         entities_vdb.delete(entity_ids)
#XZ|    │         entity_chunks.delete()
#XZ|    │
#XZ|    └── Step 7: 重建受影响的实体/关系
#XZ|              使用LLM缓存重建仍有来源的元素
#XZ|```

#QV|#### 并发控制设计

#XZ|```python
#XZ|# 单文档删除: 设置job_name = "Single document deletion"
#XZ|# 批量删除: 设置job_name = "Deleting {N} Documents"
#XZ|#
#XZ|# 验证逻辑: if not job_name.startswith("deleting") or "document" not in job_name
#XZ|#   - 管道空闲时允许单文档删除
#XZ|#   - 批量删除期间允许多个单文档删除加入队列
#XZ|#   - 拒绝非删除任务的并发操作
#XZ|```

#VB|---

#KM|### 11.2 向量数据库删除实现

#XZ|#### NanoVectorDBStorage 删除

#XZ|```python
#XZ|# lightrag/kg/nano_vector_db_impl.py
#XZ|
#XZ|async def delete(self, ids: list[str]):
#XZ|    """删除指定ID的向量"""
#XZ|    client = await self._get_client()
#XZ|    before_count = len(client)
#XZ|    
#XZ|    client.delete(ids)  # 批量删除
#XZ|    
#XZ|    after_count = len(client)
#XZ|    deleted_count = before_count - after_count
#XZ|    logger.debug(f"Deleted {deleted_count} vectors")
#XZ|
#XZ|async def delete_entity(self, entity_name: str):
#XZ|    """删除指定实体的向量"""
#XZ|    entity_id = compute_mdhash_id(entity_name, prefix="ent-")
#XZ|    client = await self._get_client()
#XZ|    
#XZ|    if client.get([entity_id]):
#XZ|        client.delete([entity_id])
#XZ|
#XZ|async def delete_entity_relation(self, entity_name: str):
#XZ|    """删除与指定实体相关的所有关系向量"""
#XZ|    # 查找所有src_id或tgt_id等于entity_name的记录
#XZ|    relations = [
#XZ|        dp for dp in storage["data"]
#XZ|        if dp["src_id"] == entity_name or dp["tgt_id"] == entity_name
#XZ|    ]
#XZ|    
#XZ|    ids_to_delete = [relation["__id__"] for relation in relations]
#XZ|    if ids_to_delete:
#XZ|        client.delete(ids_to_delete)
#XZ|```

#QV|#### 三表删除汇总

#XZ|```
#XZ|+------------------+------------------------------------------+
#XZ|| 存储类型        | 删除方法                                  |
#XZ|+------------------+------------------------------------------+
#XZ|| chunks_vdb      | delete(chunk_ids)                        |
#XZ|| entities_vdb    | delete(entity_vdb_ids) / delete_entity() |
#XZ|| relationships_vdb | delete(rel_ids) / delete_entity_relation() |
#XZ|+------------------+------------------------------------------+

#XZ|
#XZ|# 删除ID生成规则
#XZ|chunk_ids: 直接使用chunk-xxx格式
#XZ|entity_vdb_ids: compute_mdhash_id(entity_name, prefix="ent-")
#XZ|rel_ids: compute_mdhash_id(src + tgt, prefix="rel-") (双向)
#XZ|```

#VB|---

#KM|### 11.3 图数据库删除实现

#XZ|#### NetworkXStorage 删除

#XZ|```python
#XZ|# lightrag/kg/networkx_impl.py
#XZ|
#XZ|async def remove_nodes(self, node_names: list[str]):
#XZ|    """批量删除节点 (同时删除关联的边)"""
#XZ|    graph = await self._get_graph()
#XZ|    
#XZ|    for node_name in node_names:
#XZ|        if graph.has_node(node_name):
#XZ|            graph.remove_node(node_name)  # NetworkX会自动删除关联边
#XZ|
#XZ|async def remove_edges(self, edges: list[tuple]):
#XZ|    """批量删除边"""
#XZ|    graph = await self._get_graph()
#XZ|    
#XZ|    for src, tgt in edges:
#XZ|        if graph.has_edge(src, tgt):
#XZ|            graph.remove_edge(src, tgt)
#XZ|```

#QV|#### 删除流程中的图操作

#XZ|```python
#XZ|# Step 6: 删除实体时的边清理
#XZ|# 
#XZ|# 1. 批量获取所有实体关联的边
#XZ|nodes_edges_dict = await graph.get_nodes_edges_batch(list(entities_to_delete))
#XZ|
#XZ|# 2. 识别需要删除的残留边
#XZ|#    - 边的两端都在待删除实体中 → 随节点删除
#XZ|#    - 边的一端不在待删除实体中 → 需单独删除
#XZ|
#XZ|# 3. 先删除向量库中的关系
#XZ|await relationships_vdb.delete(rel_ids_to_delete)
#XZ|
#XZ|# 4. 删除关联存储
#XZ|await relation_chunks.delete(relation_storage_keys)
#XZ|
#XZ|# 5. 最后删除图节点 (边会自动清理)
#XZ|await graph.remove_nodes(list(entities_to_delete))
#XZ|```

#VB|---

#KM|### 11.4 实体/关系级删除API

#XZ|```python
#XZ|# lightrag/lightrag.py
#XZ|
#XZ|# 删除单个实体 (同时删除关联关系)
def delete_by_entity(self, entity_name: str) -> DeletionResult:
#XZ|    # 1. 获取实体在图中的所有边
#XZ|    edges = await self.chunk_entity_relation_graph.get_edges(entity_name)
#XZ|    
#XZ|    # 2. 删除向量库中的关系
#XZ|    rel_ids = [compute_mdhash_id(e[0]+e[1], prefix="rel-") for e in edges]
#XZ|    await self.relationships_vdb.delete(rel_ids)
#XZ|    
#XZ|    # 3. 删除图节点 (边自动删除)
#XZ|    await self.chunk_entity_relation_graph.remove_nodes([entity_name])
#XZ|    
#XZ|    # 4. 删除实体向量
#XZ|    entity_id = compute_mdhash_id(entity_name, prefix="ent-")
#XZ|    await self.entities_vdb.delete([entity_id])
#XZ|    
#XZ|    # 5. 删除实体-chunk关联
#XZ|    if self.entity_chunks:
#XZ|        await self.entity_chunks.delete([entity_name])
#XZ|
#XZ|# 删除单个关系
#XZ|def delete_by_relation(self, src_id: str, tgt_id: str) -> DeletionResult:
#XZ|    # 1. 删除向量库中的关系
#XZ|    rel_id = compute_mdhash_id(src_id + tgt_id, prefix="rel-")
#XZ|    await self.relationships_vdb.delete([rel_id])
#XZ|    
#XZ|    # 2. 删除图中的边
#XZ|    await self.chunk_entity_relation_graph.remove_edges([(src_id, tgt_id)])
#XZ|    
#XZ|    # 3. 删除关系-chunk关联
#XZ|    storage_key = make_relation_chunk_key(src_id, tgt_id)
#XZ|    if self.relation_chunks:
#XZ|        await self.relation_chunks.delete([storage_key])
#XZ|```

#VB|---

#KM|### 11.5 删除返回结果

#XZ|```python
#XZ|# DeletionResult 数据结构
#XZ|@dataclass
#XZ|class DeletionResult:
#XZ|    status: str           # "success" | "not_found" | "not_allowed" | "failure"
#XZ|    doc_id: str          # 被删除的文档ID
#XZ|    message: str         # 操作结果描述
#XZ|    status_code: int     # HTTP状态码 (200/404/403/500)
#XZ|    file_path: str | None  # 被删除文件的路径
#XZ|```

#QV|#### 状态码说明

#XZ|```
#XZ|+-------------+-----------------------------------------------------------+
#XZ|| 状态码      | 说明                                                      |
#XZ|+-------------+-----------------------------------------------------------+
#XZ|| 200 (success) | 删除成功                                                |
#XZ|| 404 (not_found) | 文档不存在                                              |
#XZ|| 403 (not_allowed) | 管道忙碌中,不允许删除                                    |
#XZ|| 500 (failure) | 删除失败                                                  |
#XZ|+-------------+-----------------------------------------------------------+
#XZ|```

#VB|---

#KM|### 11.6 删除数据一致性保证

#QV|#### 事务性保证

#XZ|1. **Pipeline锁机制**: 通过pipeline_status控制并发,确保同一时间只有一个删除操作
#XZ|2. **分析-删除顺序**: 先分析受影响元素,再执行删除,避免误删
#XZ|3. **实体关联边处理**: 删除实体前先清理关联边,防止孤立边残留
#XZ|4. **向量库与图库同步**: 在删除图节点前先删除向量库数据

#QV|#### 重建机制

#XZ|```
#XZ|当实体/关系仍有其他文档来源时:
#XZ|  - 不执行删除
#XZ|  - 更新entity_chunks/relation_chunks中的chunk_ids
#XZ|  - 触发LLM缓存重建 (使用剩余chunk)
#XZ|
#XZ|重建流程:
#XZ|  1. 从LLM缓存获取剩余chunk的提取结果
#XZ|  2. 重新调用 _merge_nodes_then_upsert()
#XZ|  3. 重新调用 _merge_edges_then_upsert()
#XZ|  4. 更新图数据库和向量库
#XZ|```

#VB|---

---

#KM|## 十二、配置信息统一入口

#XZ|### 12.1 配置统一入口: LightRAG类

#QV|#### 核心配置类

#XZ|```python
#XZ|# lightrag/lightrag.py
#XZ|
#XZ|@dataclass
#XZ|class LightRAG:
#XZ|    """LightRAG配置统一入口 - 使用dataclass管理所有配置"""
#XZ|    
#XZ|    # 目录配置
#XZ|    working_dir: str = field(default="./rag_storage")
#XZ|    
#XZ|    # 存储后端配置
#XZ|    kv_storage: str = field(default="JsonKVStorage")
#XZ|    vector_storage: str = field(default="NanoVectorDBStorage")
#XZ|    graph_storage: str = field(default="NetworkXStorage")
#XZ|    doc_status_storage: str = field(default="JsonDocStatusStorage")
#XZ|    
#XZ|    # 工作区隔离
#XZ|    workspace: str = field(default_factory=lambda: os.getenv("WORKSPACE", ""))
#XZ|    
#XZ|    # 查询参数
#XZ|    top_k: int = field(default=get_env_value("TOP_K", DEFAULT_TOP_K, int))
#XZ|    chunk_top_k: int = field(default=...)
#XZ|    max_entity_tokens: int = field(default=...)
#XZ|    max_relation_tokens: int = field(default=...)
#XZ|    max_total_tokens: int = field(default=...)
#XZ|    
#XZ|    # 实体提取配置
#XZ|    entity_extract_max_gleaning: int = field(default=...)
#XZ|    force_llm_summary_on_merge: int = field(default=...)
#XZ|    
#XZ|    # 分块配置
#XZ|    chunk_token_size: int = field(default=int(os.getenv("CHUNK_SIZE", 1200)))
#XZ|    chunk_overlap_token_size: int = field(default=int(os.getenv("CHUNK_OVERLAP_SIZE", 100)))
#XZ|    
#XZ|    # Embedding配置
#XZ|    embedding_func: EmbeddingFunc | None = field(default=None)
#XZ|    embedding_batch_num: int = field(default=int(os.getenv("EMBEDDING_BATCH_NUM", 10)))
#XZ|    embedding_func_max_async: int = field(default=...)
#XZ|    
#XZ|    # LLM配置
#XZ|    llm_model_func: Callable[..., object] | None = field(default=None)
#XZ|    llm_model_name: str = field(default="gpt-4o-mini")
#XZ|    llm_model_max_async: int = field(default=int(os.getenv("MAX_ASYNC", 4)))
#XZ|    llm_model_kwargs: dict = field(default_factory=dict)
#XZ|    
#XZ|    # 摘要配置
#XZ|    summary_max_tokens: int = field(default=...)
#XZ|    summary_context_size: int = field(default=...)
#XZ|    summary_length_recommended: int = field(default=...)
#XZ|    
#XZ|    # 扩展配置
#XZ|    addon_params: dict = field(default_factory=lambda: {
#XZ|        "language": get_env_value("SUMMARY_LANGUAGE", DEFAULT_SUMMARY_LANGUAGE, str),
#XZ|        "entity_types": get_env_value("ENTITY_TYPES", DEFAULT_ENTITY_TYPES, list),
#XZ|    })
#XZ|```

#QV|#### 配置优先级

#XZ|```
#XZ|优先级 (从高到低):
#XZ|1. 构造函数参数 (最高优先级)
#XZ|2. 环境变量 (os.getenv)
#XZ|3. 默认常量 (DEFAULT_*) (最低优先级)
#XZ|```

#XZ|```python
#XZ|# 配置读取示例
#XZ|chunk_token_size: int = field(default=int(os.getenv("CHUNK_SIZE", 1200)))
#XZ|#                     ↑              ↑            ↑
#XZ|#                   环境变量        默认值       优先级最低
#XZ|```

#VB|---

#KM|### 12.2 默认常量定义 (constants.py)

#XZ|```python
#XZ|# lightrag/constants.py
#XZ|
#XZ|# ========== 查询参数 ==========
#XZ|DEFAULT_TOP_K = 40
#XZ|DEFAULT_CHUNK_TOP_K = 20
#XZ|DEFAULT_MAX_ENTITY_TOKENS = 6000
#XZ|DEFAULT_MAX_RELATION_TOKENS = 8000
#XZ|DEFAULT_MAX_TOTAL_TOKENS = 30000
#XZ|DEFAULT_COSINE_THRESHOLD = 0.2
#XZ|DEFAULT_RELATED_CHUNK_NUMBER = 5
#XZ|DEFAULT_KG_CHUNK_PICK_METHOD = "VECTOR"
#XZ|
#XZ|# ========== 实体提取 ==========
#XZ|DEFAULT_MAX_GLEANING = 1
#XZ|DEFAULT_FORCE_LLM_SUMMARY_ON_MERGE = 8
#XZ|DEFAULT_ENTITY_TYPES = ["person", "organization", "location", "event", "artifact"]
#XZ|
#XZ|# ========== 摘要配置 ==========
#XZ|DEFAULT_SUMMARY_LANGUAGE = "English"
#XZ|DEFAULT_SUMMARY_MAX_TOKENS = 1200
#XZ|DEFAULT_SUMMARY_LENGTH_RECOMMENDED = 600
#XZ|DEFAULT_SUMMARY_CONTEXT_SIZE = 12000
#XZ|
#XZ|# ========== 并发配置 ==========
#XZ|DEFAULT_MAX_ASYNC = 4
#XZ|DEFAULT_MAX_PARALLEL_INSERT = 2
#XZ|DEFAULT_EMBEDDING_FUNC_MAX_ASYNC = 8
#XZ|DEFAULT_EMBEDDING_BATCH_NUM = 10
#XZ|
#XZ|# ========== 限制配置 ==========
#XZ|DEFAULT_MAX_SOURCE_IDS_PER_ENTITY = 300
#XZ|DEFAULT_MAX_SOURCE_IDS_PER_RELATION = 300
#XZ|DEFAULT_MAX_FILE_PATHS = 100
#XZ|DEFAULT_MAX_GRAPH_NODES = 1000
#XZ|
#XZ|# ========== 超时配置 ==========
#XZ|DEFAULT_LLM_TIMEOUT = 180
#XZ|DEFAULT_EMBEDDING_TIMEOUT = 30
#XZ|```

#VB|---

#KM|### 12.3 配置初始化流程 (__post_init__)

#XZ|```python
#XZ|def __post_init__(self):
#XZ|    """配置初始化入口 - 在__init__后自动调用"""
#XZ|    
#XZ|    # 1. 初始化共享数据
#XZ|    initialize_share_data()
#XZ|    
#XZ|    # 2. 创建工作目录
#XZ|    if not os.path.exists(self.working_dir):
#XZ|        os.makedirs(self.working_dir)
#XZ|    
#XZ|    # 3. 验证存储实现兼容性
#XZ|    verify_storage_implementation(storage_type, storage_name)
#XZ|    
#XZ|    # 4. 检查环境变量
#XZ|    check_storage_env_vars(storage_name)
#XZ|    
#XZ|    # 5. 初始化Tokenizer
#XZ|    if self.tokenizer is None:
#XZ|        self.tokenizer = TiktokenTokenizer(self.tiktoken_model_name)
#XZ|    
#XZ|    # 6. 验证配置
#XZ|    if self.force_llm_summary_on_merge < 3:
#XZ|        logger.warning(...)
#XZ|    if self.summary_context_size > self.max_total_tokens:
#XZ|        logger.warning(...)
#XZ|    
#XZ|    # 7. 初始化Embedding
#XZ|    original_embedding_func = self.embedding_func
#XZ|    embedding_max_token_size = self.embedding_func.max_token_size
#XZ|    self.embedding_token_limit = embedding_max_token_size
#XZ|    
#XZ|    # 8. 生成global_config (字典形式)
#XZ|    global_config = asdict(self)
#XZ|    global_config["embedding_func"] = original_embedding_func
#XZ|    
#XZ|    # 9. 应用优先级装饰器
#XZ|    self.embedding_func = create_embedding_func_with_priority(...)
#XZ|```

#QV|#### global_config 生成

#XZ|```python
#XZ|# __post_init__中生成全局配置字典
#XZ|global_config = asdict(self)
#XZ|global_config["embedding_func"] = original_embedding_func
#XZ|global_config["llm_model_func"] = self.llm_model_func
#XZ|global_config["tokenizer"] = self.tokenizer
#XZ|...
#XZ|#
#XZ|# global_config 包含所有配置,传递给各个存储实例
#XZ|self.full_docs = self.kv_storage_cls(
#XZ|    namespace=...,
#XZ|    global_config=global_config,  # 传递全局配置
#XZ|    ...
#XZ|)
#XZ|```

#VB|---

#KM|### 12.4 配置向存储层的传递

#QV|#### StorageNameSpace基类

#XZ|```python
#XZ|# lightrag/base.py
#XZ|
#XZ|@dataclass
#XZ|class StorageNameSpace(ABC):
#XZ|    namespace: str
#XZ|    workspace: str
#XZ|    global_config: dict[str, Any]  # 接收全局配置字典
#XZ|```

#QV|#### 存储初始化示例

#XZ|```python
#XZ|# LightRAG.__init__中的初始化
#XZ|
#XZ|# 生成global_config
#XZ|global_config = asdict(self)
#XZ|global_config["embedding_func"] = original_embedding_func
#XZ|
#XZ|# 初始化KV存储 (文档存储)
#XZ|self.full_docs = self.kv_storage_cls(
#XZ|    namespace=NameSpace.KV_STORE_DOCS,
#XZ|    workspace=self.workspace,
#XZ|    global_config=global_config,  # 传递
#XZ|)
#XZ|
#XZ|# 初始化向量存储 (实体)
#XZ|self.entities_vdb = self.vector_db_storage_cls(
#XZ|    namespace=NameSpace.VECTOR_STORE_ENTITIES,
#XZ|    workspace=self.workspace,
#XZ|    embedding_func=self.embedding_func,
#XZ|    global_config=global_config,  # 传递
#XZ|)
#XZ|
#XZ|# 初始化图存储
#XZ|self.chunk_entity_relation_graph = self.graph_storage_cls(
#XZ|    namespace=NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION,
#XZ|    workspace=self.workspace,
#XZ|    embedding_func=self.embedding_func,
#XZ|    global_config=global_config,  # 传递
#XZ|)
#XZ|```

#VB|---

#KM|### 12.5 环境变量配置

#QV|#### 常用环境变量

#XZ|```
#XZ|+---------------------------+------------------------------------------+
#XZ|| 环境变量                 | 说明                                    |
#XZ|+---------------------------+------------------------------------------+
#XZ|| WORKSPACE                | 工作区隔离名称                           |
#XZ|| CHUNK_SIZE               | 文本块大小 (默认1200)                    |
#XZ|| CHUNK_OVERLAP_SIZE       | 块重叠大小 (默认100)                     |
#XZ|| TOP_K                    | 查询返回数量 (默认40)                     |
#XZ|| MAX_ASYNC                | LLM并发数 (默认4)                        |
#XZ|| SUMMARY_LANGUAGE          | 摘要语言 (默认English)                   |
#XZ|| ENTITY_TYPES             | 实体类型列表                             |
#XZ|| LLM_MODEL                | LLM模型名称                             |
#XZ|| LLM_API_KEY              | LLM API密钥                            |
#XZ|| EMBEDDING_MODEL          | Embedding模型名称                       |
#XZ|| EMBEDDING_API_KEY        | Embedding API密钥                      |
#XZ|| COSINE_THRESHOLD         | 向量相似度阈值 (默认0.2)                |
#XZ|+---------------------------+------------------------------------------+
#XZ|```

#QV|#### get_env_value辅助函数

#XZ|```python
#XZ|# lightrag/utils.py
#XZ|
def get_env_value(key: str, default: T, value_type: type[T]) -> T:
#XZ|    """从环境变量读取配置"""
#XZ|    value = os.getenv(key)
#XZ|    if value is None:
#XZ|        return default
#XZ|    try:
#XZ|        return value_type(value)
#XZ|    except (ValueError, TypeError):
#XZ|        logger.warning(f"Invalid {key}={value}, using default {default}")
#XZ|        return default
#XZ|```

#VB|---

#KM|### 12.6 配置分类汇总

#XZ|```
#XZ|+---------------------+-----------------------------------------------+
#XZ|| 配置类别            | 主要参数                                      |
#XZ|+---------------------+-----------------------------------------------+
#XZ|| 目录/工作区         | working_dir, workspace                        |
#XZ|| 存储后端           | kv_storage, vector_storage, graph_storage     |
#XZ|| 查询参数           | top_k, chunk_top_k, max_*_tokens            |
#XZ|| 分块配置           | chunk_token_size, chunk_overlap_token_size   |
#XZ|| Embedding          | embedding_func, embedding_batch_num          |
#XZ|| LLM               | llm_model_func, llm_model_name, llm_model_kwargs |
#XZ|| 摘要生成           | summary_max_tokens, summary_context_size     |
#XZ|| 实体提取           | entity_extract_max_gleaning, entity_types     |
#XZ|| 缓存             | enable_llm_cache, embedding_cache_config     |
#XZ|| 并发控制           | llm_model_max_async, max_parallel_insert    |
#XZ|| 扩展参数           | addon_params (language, entity_types)       |
#XZ|+---------------------+-----------------------------------------------+
#XZ|```

#VB|---

---

## 十三、模型配置统一入口

**文件路径汇总**:

| 章节 | 功能说明 | 文件路径 |
|------|---------|---------|
| 13.1 | BindingOptions基类 | `lightrag/llm/binding_options.py` |
| 13.2 | 模型Provider定义 | `lightrag/llm/binding_options.py` |
| 13.3 | LLM配置参数 | `lightrag/llm/binding_options.py` |
| 13.4 | API层配置入口 | `lightrag/api/config.py` |
| 13.5 | EmbeddingFunc封装 | `lightrag/utils.py` |
| 13.6 | 环境变量配置 | `lightrag/api/config.py`, `lightrag/constants.py` |
| 13.7 | 完整配置流程 | `lightrag/lightrag.py`, `lightrag/api/config.py` |

**相关LLM Provider实现文件**:

| Provider | 文件路径 |
|----------|---------|
| Ollama | `lightrag/llm/ollama.py` |
| OpenAI | `lightrag/llm/openai.py` |
| Azure OpenAI | `lightrag/llm/azure_openai.py` |
| Gemini | `lightrag/llm/gemini.py` |
| Anthropic | `lightrag/llm/anthropic.py` |
| HuggingFace | `lightrag/llm/hf.py` |
| vLLM (lmdeploy) | `lightrag/llm/lmdeploy.py` |
| NVIDIA OpenAI | `lightrag/llm/nvidia_openai.py` |
| Bedrock | `lightrag/llm/bedrock.py` |
| Jina | `lightrag/llm/jina.py` |
| LoLLMs | `lightrag/llm/lollms.py` |
| Zhipu | `lightrag/llm/zhipu.py` |
| LlamaIndex | `lightrag/llm/llama_index_impl.py` |

### 13.1 BindingOptions基类

**文件路径**: `lightrag/llm/binding_options.py`


#QV|#### 设计目标

#XZ|LightRAG使用BindingOptions作为模型配置的**统一抽象层**：

#XZ|```python
#XZ|# lightrag/llm/binding_options.py
#XZ|
#XZ|@dataclass
#XZ|class BindingOptions:
#XZ|    """所有LLM/Embedding Provider配置的基类"""
#XZ|    
#XZ|    _binding_name: ClassVar[str]      # 绑定名称
#XZ|    _help: ClassVar[dict[str, str]]  # 参数说明
#XZ|    
#XZ|    @classmethod
#XZ|    def add_args(cls, parser):  # 添加命令行参数
#XZ|    
#XZ|    @classmethod
#XZ|    def args_env_name_type_value(cls):  # 获取所有配置项
#XZ|    
#XZ|    @classmethod
#XZ|    def options_dict(cls, args):  # 从参数提取配置
#XZ|    
#XZ|    @classmethod
#XZ|    def generate_dot_env_sample(cls):  # 生成.env示例
#XZ|    
#XZ|    def asdict(self) -> dict:  # 转换为字典
#XZ|```

#QV|#### 核心功能

#XZ|1. **配置管理**: 定义每个Provider的配置参数结构
#XZ|2. **环境集成**: 自动从环境变量读取配置
#XZ|3. **CLI支持**: 动态生成命令行参数
#XZ|4. **可扩展性**: 添加新Provider只需定义子类

#VB|---

#KM|### 13.2 支持的模型Provider

#XZ|```
#XZ|+-------------------+------------------------+---------------------------+
#XZ|| Provider          | LLM Options类          | Embedding Options类       |
#XZ|+-------------------+------------------------+---------------------------+
#XZ|| Ollama           | OllamaLLMOptions       | OllamaEmbeddingOptions    |
#XZ|| OpenAI           | OpenAILLMOptions       | -                        |
#XZ|| Azure OpenAI    | OpenAILLMOptions       | -                        |
#XZ|| Gemini           | GeminiLLMOptions        | GeminiEmbeddingOptions    |
#XZ|| Anthropic        | (在anthropic.py中)     | -                        |
#XZ|| HuggingFace     | (在hf.py中)           | -                        |
#XZ|| vLLM            | (在lmdeploy.py中)     | -                        |
#XZ|+-------------------+------------------------+---------------------------+
#XZ|```

#VB|---

#KM|### 13.3 LLM配置参数示例

#XZ|#### Ollama配置 (OllamaLLMOptions)

#XZ|```python
#XZ|@dataclass
#XZ|class OllamaLLMOptions(_OllamaOptionsMixin, BindingOptions):
#XZ|    _binding_name: ClassVar[str] = "ollama_llm"
#XZ|
#XZ|# 核心参数
#XZ|num_ctx: int = 32768          # 上下文窗口大小
#XZ|num_predict: int = 128       # 最大生成token数
#XZ|temperature: float = 1.0     # 随机性控制 (0.0-2.0)
#XZ|top_k: int = 40              # Top-k采样
#XZ|top_p: float = 0.9           # Top-p (nucleus)采样
#XZ|
#XZ|# 重复控制
#XZ|repeat_penalty: float = 1.1   # 重复惩罚
#XZ|presence_penalty: float = 0.0 # 存在惩罚
#XZ|frequency_penalty: float = 0.0 # 频率惩罚
#XZ|
#XZ|# 硬件参数
#XZ|num_gpu: int = -1            # GPU数量 (-1=自动)
#XZ|num_thread: int = 0         # CPU线程数 (0=自动)
#XZ|numa: bool = False           # NUMA优化
#XZ|
#XZ|# 输出控制
#XZ|stop: List[str] = []          # 停止序列
#XZ|```

#XZ|#### OpenAI配置 (OpenAILLMOptions)

#XZ|```python
#XZ|@dataclass
#XZ|class OpenAILLMOptions(BindingOptions):
#XZ|    _binding_name: ClassVar[str] = "openai_llm"
#XZ|
#XZ|# 采样参数
#XZ|frequency_penalty: float = 0.0
#XZ|max_completion_tokens: int = None
#XZ|presence_penalty: float = 0.0
#XZ|reasoning_effort: str = "medium"  # o1模型推理努力程度
#XZ|stop: List[str] = []
#XZ|temperature: float = 1.0
#XZ|top_p: float = 1.0
#XZ|```

#XZ|#### Gemini配置 (GeminiLLMOptions)

#XZ|```python
#XZ|@dataclass
#XZ|class GeminiLLMOptions(BindingOptions):
#XZ|    _binding_name: ClassVar[str] = "gemini_llm"
#XZ|
#XZ|temperature: float = 1.0
#XZ|top_p: float = 0.95
#XZ|top_k: int = 40
#XZ|max_output_tokens: int = None
#XZ|candidate_count: int = 1
#XZ|stop_sequences: List[str] = []
#XZ|thinking_config: dict = None  # 思考配置
#XZ|```

#VB|---

#KM|### 13.4 API层配置入口 (api/config.py)

#QV|#### parse_args() 函数

#XZ|```python
#XZ|# lightrag/api/config.py
#XZ|
#XZ|def parse_args() -> argparse.Namespace:
#XZ|    """解析命令行参数,支持环境变量回退"""
#XZ|    
#XZ|    parser = ArgumentParser(description="LightRAG API Server")
#XZ|    
#XZ|    # 服务器配置
#XZ|    parser.add_argument("--host", default=get_env_value("HOST", "0.0.0.0"))
#XZ|    parser.add_argument("--port", default=get_env_value("PORT", 9621, int))
#XZ|    
#XZ|    # RAG配置
#XZ|    parser.add_argument("--max-async", default=get_env_value("MAX_ASYNC", DEFAULT_MAX_ASYNC, int))
#XZ|    parser.add_argument("--summary-max-tokens", ...)
#XZ|    
#XZ|    # LLM/Embedding绑定选择
#XZ|    parser.add_argument(
#XZ|        "--llm-binding",
#XZ|        choices=["ollama", "openai", "azure_openai", "gemini", "aws_bedrock", "lollms"],
#XZ|        default=get_env_value("LLM_BINDING", "ollama")
#XZ|    )
#XZ|    parser.add_argument(
#XZ|        "--embedding-binding",
#XZ|        choices=["ollama", "openai", "jina", "gemini", "azure_openai", "aws_bedrock", "lollms"],
#XZ|        default=get_env_value("EMBEDDING_BINDING", "ollama")
#XZ|    )
#XZ|    
#XZ|    # 根据绑定类型动态添加Provider特定参数
#XZ|    if llm_binding_value == "ollama":
#XZ|        OllamaLLMOptions.add_args(parser)
#XZ|    elif llm_binding_value in ["openai", "azure_openai"]:
#XZ|        OpenAILLMOptions.add_args(parser)
#XZ|    elif llm_binding_value == "gemini":
#XZ|        GeminiLLMOptions.add_args(parser)
#XZ|    
#XZ|    return parser.parse_args()
#XZ|```

#QV|#### 全局配置单例

#XZ|```python
#XZ|# 全局配置访问
#XZ|global_args = _GlobalArgsProxy()  # 自动初始化
#XZ|
#XZ|# 使用示例
#XZ|from lightrag.api.config import get_config, initialize_config
#XZ|
#XZ|# 方式1: 自动初始化
#XZ|config = get_config()
#XZ|print(config.llm_model)
#XZ|print(config.embedding_dim)
#XZ|
#XZ|# 方式2: 手动初始化
#XZ|initialize_config(args=custom_args)
#XZ|```

#VB|---

#KM|### 13.5 EmbeddingFunc封装类

#XZ|```python
#XZ|# lightrag/utils.py
#XZ|
#XZ|class EmbeddingFunc:
#XZ|    """Embedding函数封装类,支持维度验证和属性注入"""
#XZ|    
#XZ|    embedding_dim: int       # 向量维度 (用于验证和工作区隔离)
#XZ|    func: callable           # 实际embedding函数
#XZ|    max_token_size: int | None  # token数限制 (用于摘要)
#XZ|    send_dimensions: bool = False  # 是否注入维度参数
#XZ|    model_name: str | None = None  # 模型名称 (用于工作区数据隔离)
#XZ|    
#XZ|    async def __call__(self, texts: list[str]) -> np.ndarray:
#XZ|        """调用embedding函数"""
#XZ|        return await self.func(texts)
#XZ|```

#QV|#### 创建EmbeddingFunc示例

#XZ|```python
#XZ|# 方式1: 使用装饰器
#XZ|from lightrag.llm import ollama_embedding
#XZ|
#XZ|embed_func = EmbeddingFunc(
#XZ|    embedding_dim=1024,
#XZ|    func=ollama_embedding.func,  # 使用.func避免双层包装
#XZ|    embed_model="nomic-embed-text:v1.5",
#XZ|    host="http://localhost:11434"
#XZ|)
#XZ|
#XZ|# 方式2: 使用partial
#XZ|from functools import partial
#XZ|from lightrag.llm import openai_embedding
#XZ|
#XZ|embed_func = EmbeddingFunc(
#XZ|    embedding_dim=1536,
#XZ|    func=partial(openai_embedding, model="text-embedding-3-small")
#XZ|)
#XZ|```

#VB|---

#KM|### 13.6 环境变量配置

#QV|#### 模型相关环境变量

#XZ|```
#XZ|+-------------------------------+------------------------------------------+
#XZ|| 环境变量                    | 说明                                   |
#XZ|+-------------------------------+------------------------------------------+
#XZ|| LLM_BINDING                 | LLM Provider类型 (ollama/openai/gemini) |
#XZ|| EMBEDDING_BINDING           | Embedding Provider类型                   |
#XZ|| LLM_MODEL                   | LLM模型名称                            |
#XZ|| EMBEDDING_MODEL             | Embedding模型名称                      |
#XZ|| EMBEDDING_DIM               | Embedding向量维度                       |
#XZ|| LLM_BINDING_HOST           | LLM服务地址                            |
#XZ|| EMBEDDING_BINDING_HOST     | Embedding服务地址                      |
#XZ|| LLM_BINDING_API_KEY       | LLM API密钥                           |
#XZ|| EMBEDDING_BINDING_API_KEY | Embedding API密钥                      |
#XZ|+-------------------------------+------------------------------------------+
#XZ|```

#QV|#### Provider特定环境变量

#XZ|```
#XZ|# Ollama
#XZ|OLLAMA_LLM_TEMPERATURE=0.8
#XZ|OLLAMA_LLM_NUM_CTX=4096
#XZ|OLLAMA_LLM_TOP_P=0.9
#XZ|
#XZ|# OpenAI
#XZ|OPENAI_LLM_TEMPERATURE=0.7
#XZ|OPENAI_LLM_MAX_COMPLETION_TOKENS=2000
#XZ|
#XZ|# Gemini
#XZ|GEMINI_LLM_TEMPERATURE=0.9
#XZ|GEMINI_LLM_TOP_P=0.95
#XZ|```

#QV|#### 生成.env示例

#XZ|```bash
#XZ|# 运行生成.env模板
#XZ|python -m lightrag.llm.binding_options
#XZ|```

#VB|---

#KM|### 13.7 完整配置流程

#XZ|```
#XZ|+-------------------------+------------------------------------------+
#XZ|| 配置层次               | 配置来源                                 |
#XZ|+-------------------------+------------------------------------------+
#XZ|| 1. API层              | parse_args() → global_args              |
#XZ|| 2. LightRAG类        | __init__参数 / 环境变量                  |
#XZ|| 3. Provider选项       | BindingOptions子类                       |
#XZ|| 4. 运行时             | llm_model_func / embedding_func         |
#XZ|+-------------------------+------------------------------------------+
#XZ|```

#XZ|```
#XZ|# 配置流程示例
#XZ|
#XZ|# 1. API入口 (lightrag_server.py)
#XZ|from lightrag.api.config import initialize_config
#XZ|args = initialize_config()
#XZ|
#XZ|# 2. 创建LLM函数
#XZ|llm_func = create_llm_func(
#XZ|    binding=args.llm_binding,
#XZ|    model=args.llm_model,
#XZ|    options=OpenAILLMOptions.options_dict(args)  # Provider选项
#XZ|)
#XZ|
#XZ|# 3. 创建Embedding函数  
#XZ|embed_func = create_embedding_func(
#XZ|    binding=args.embedding_binding,
#XZ|    model=args.embedding_model,
#XZ|    dim=args.embedding_dim
#XZ|)
#XZ|
#XZ|# 4. 初始化LightRAG
#XZ|rag = LightRAG(
#XZ|    working_dir="./rag_storage",
#XZ|    llm_model_func=llm_func,
#XZ|    embedding_func=embed_func,
#XZ|)
#XZ|```

#VB|---

#KM|*文档生成时间: 2026-02-25*
