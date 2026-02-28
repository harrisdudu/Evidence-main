# 图数据库 API 接口说明（LightRAG）

本文档汇总 LightRAG 代码库中“图数据库 / 知识图谱（KG）”相关的 **对外 HTTP API**（前端可直接调用）与 **底层 GraphStorage（Python）接口**，并给出主要调用链路与代码位置，便于前端按需接入查询能力。

---

## 1. 路由挂载位置（图谱 API 入口）

- 图谱路由在服务启动时挂载：在 [lightrag_server.py:L1119-L1133](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/lightrag_server.py#L1119-L1133) 中 `app.include_router(create_graph_routes(...))`。
- 图谱路由文件： [graph_routes.py](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py)

---

## 2. 对外 HTTP API（前端可直接调用）

以下接口均来自 [graph_routes.py](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py)（`tags=["graph"]`），用于图谱查询与维护。

### 2.1 标签（实体名）相关

- `GET /graph/label/list`
  - 功能：获取全部实体标签（实体名列表）
  - 调用链：
    - 路由：[graph_routes.py:L89-L108](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L89-L108)
    - `rag.get_graph_labels()`：[lightrag.py:L1135-L1144](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L1135-L1144)
    - `chunk_entity_relation_graph.get_all_labels()`（GraphStorage）：[base.py:L638-L646](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L638-L646)

- `GET /graph/label/popular?limit=...`
  - 功能：按节点度数返回热门实体标签
  - 调用链：
    - 路由：[graph_routes.py:L109-L132](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L109-L132)
    - GraphStorage：`get_popular_labels(limit)`：[base.py:L681-L690](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L681-L690)

- `GET /graph/label/search?q=...&limit=...`
  - 功能：模糊搜索实体标签
  - 调用链：
    - 路由：[graph_routes.py:L133-L158](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L133-L158)
    - GraphStorage：`search_labels(query, limit)`：[base.py:L692-L702](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L692-L702)

### 2.2 子图查询（知识图谱可视化查询的核心接口）

- `GET /graphs?label=...&max_depth=...&max_nodes=...`
  - 功能：从指定实体（label）出发，获取连通子图（带截断策略）
  - 调用链：
    - 路由：[graph_routes.py:L159-L196](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L159-L196)
    - `rag.get_knowledge_graph(...)`：[lightrag.py:L1146-L1173](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L1146-L1173)
    - GraphStorage：`get_knowledge_graph(node_label, max_depth, max_nodes)`：[base.py:L647-L663](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L647-L663)
  - 返回结构：`KnowledgeGraph`（包含 `nodes[]/edges[]/is_truncated`），类型定义见 [types.py](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/types.py)

### 2.3 实体存在性检查

- `GET /graph/entity/exists?name=...`
  - 功能：检查实体是否存在（返回 `{"exists": bool}`）
  - 调用链：
    - 路由：[graph_routes.py:L197-L219](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L197-L219)
    - GraphStorage：`has_node(node_id)`：[base.py:L410-L420](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L410-L420)

### 2.4 图谱写操作（增改合并）

这些接口会同时维护图结构与索引一致性（如实体/关系向量、关系迁移等），主要调用 `LightRAG` 的异步方法，再落到图谱工具层。

- `POST /graph/entity/edit`
  - 功能：更新实体属性；可选重命名与冲突合并
  - 请求体：`EntityUpdateRequest`：[graph_routes.py:L16-L21](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L16-L21)
  - 路由：[graph_routes.py:L220-L408](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L220-L408)
  - 业务入口：`LightRAG.aedit_entity`：[lightrag.py:L3907-L3940](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L3907-L3940)

- `POST /graph/relation/edit`
  - 功能：更新关系（边）属性
  - 请求体：`RelationUpdateRequest`：[graph_routes.py:L23-L27](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L23-L27)
  - 路由：[graph_routes.py:L410-L444](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L410-L444)
  - 业务入口：`LightRAG.aedit_relation`：[lightrag.py:L3967-L3994](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L3967-L3994)

- `POST /graph/entity/create`
  - 功能：创建新实体
  - 请求体：`EntityCreateRequest`：[graph_routes.py:L44-L61](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L44-L61)
  - 路由：[graph_routes.py:L445-L517](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L445-L517)
  - 业务入口：`LightRAG.acreate_entity`：[lightrag.py:L4003-L4026](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L4003-L4026)

- `POST /graph/relation/create`
  - 功能：创建关系（在两个已存在实体之间创建边）
  - 请求体：`RelationCreateRequest`：[graph_routes.py:L63-L87](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L63-L87)
  - 路由：[graph_routes.py:L518-L606](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L518-L606)
  - 业务入口：`LightRAG.acreate_relation`：[lightrag.py:L4033-L4058](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L4033-L4058)

- `POST /graph/entities/merge`
  - 功能：合并多个实体到一个目标实体（迁移关系、去重关系、更新索引）
  - 请求体：`EntityMergeRequest`：[graph_routes.py:L29-L42](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L29-L42)
  - 路由：[graph_routes.py:L607-L688](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/graph_routes.py#L607-L688)
  - 业务入口：`LightRAG.amerge_entities`：[lightrag.py:L4067-L4106](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L4067-L4106)

---

## 3. 与图谱检索数据相关的 Query 端点（返回结构化 entities/relationships）

- `POST /query/data`
  - 功能：不进行最终 LLM 生成，直接返回结构化检索结果（entities / relationships / chunks / references）
  - 路由与响应模型：`QueryDataResponse` 见 [query_routes.py:L167-L176](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/query_routes.py#L167-L176)，端点定义见 [query_routes.py:L742-L825](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/api/routers/query_routes.py#L742-L825)
  - 调用链：路由调用 `rag.aquery_data(...)`（函数定义/返回说明见 [lightrag.py:L2602-L2691](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/lightrag.py#L2602-L2691)）

---

## 4. 底层图数据库接口（Python：BaseGraphStorage）

> 说明：GraphStorage 的统一抽象为 `BaseGraphStorage`，定义了图的核心读写能力。  
> 接口约束：`BaseGraphStorage` 标注“边相关操作应当按无向图语义处理”。见 [base.py:L405-L407](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L405-L407)。

### 4.1 BaseGraphStorage 方法（抽象定义）

接口定义位置：[base.py:BaseGraphStorage](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L405-L703)

- 基础判断/度数
  - `has_node(node_id)`：[base.py:L410-L420](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L410-L420)
  - `has_edge(src, tgt)`：[base.py:L421-L432](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L421-L432)
  - `node_degree(node_id)`：[base.py:L433-L443](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L433-L443)
  - `edge_degree(src, tgt)`：[base.py:L444-L455](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L444-L455)

- 读取
  - `get_node(node_id)`：[base.py:L456-L466](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L456-L466)
  - `get_edge(src, tgt)`：[base.py:L468-L479](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L468-L479)
  - `get_node_edges(node_id)`：[base.py:L481-L491](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L481-L491)

- 批量读取（默认实现可被后端覆盖以提速）
  - `get_nodes_batch(...)`：[base.py:L493-L505](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L493-L505)
  - `node_degrees_batch(...)`：[base.py:L507-L518](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L507-L518)
  - `edge_degrees_batch(...)`：[base.py:L520-L533](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L520-L533)
  - `get_edges_batch(...)`：[base.py:L535-L552](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L535-L552)
  - `get_nodes_edges_batch(...)`：[base.py:L553-L567](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L553-L567)

- 写入/删除
  - `upsert_node(node_id, data)`：[base.py:L568-L581](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L568-L581)
  - `upsert_edge(src, tgt, data)`：[base.py:L582-L598](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L582-L598)
  - `delete_node(node_id)`：[base.py:L599-L611](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L599-L611)
  - `remove_nodes(nodes)`：[base.py:L612-L624](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L612-L624)
  - `remove_edges(edges)`：[base.py:L625-L637](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L625-L637)

- 标签/子图/全量导出
  - `get_all_labels()`：[base.py:L638-L646](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L638-L646)
  - `get_knowledge_graph(label, max_depth, max_nodes)`：[base.py:L647-L663](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L647-L663)
  - `get_all_nodes()`：[base.py:L664-L672](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L664-L672)
  - `get_all_edges()`：[base.py:L673-L680](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L673-L680)
  - `get_popular_labels(limit)`：[base.py:L681-L690](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L681-L690)
  - `search_labels(query, limit)`：[base.py:L692-L702](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/base.py#L692-L702)

### 4.2 GraphStorage 后端实现类（代码位置）

- NetworkX（本地 GraphML）
  - 类：`NetworkXStorage`：[networkx_impl.py:L23-L35](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/networkx_impl.py#L23-L35)
  - 典型实现示例：
    - `get_knowledge_graph(...)`：[networkx_impl.py:L297-L472](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/networkx_impl.py#L297-L472)
    - `get_all_nodes/get_all_edges(...)`：[networkx_impl.py:L474-L501](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/networkx_impl.py#L474-L501)

- Neo4j
  - 类：`Neo4JStorage`：[neo4j_impl.py:L64-L83](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/neo4j_impl.py#L64-L83)
  - 核心方法实现位置（示例）：
    - `has_node/has_edge/get_node(...)`：[neo4j_impl.py:L428-L541](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/neo4j_impl.py#L428-L541)
    - `get_knowledge_graph(...)`：[neo4j_impl.py:L1105-L1483](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/neo4j_impl.py#L1105-L1483)

- Memgraph
  - 类：`MemgraphStorage`：[memgraph_impl.py](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/memgraph_impl.py)
  - 核心方法实现位置（示例）：
    - `has_node/has_edge/get_node(...)`：[memgraph_impl.py:L123-L240](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/memgraph_impl.py#L123-L240)

- PostgreSQL + Apache AGE
  - 类：`PGGraphStorage`：[postgres_impl.py:L3863-L3883](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/postgres_impl.py#L3863-L3883)
  - 初始化与图名隔离规则（workspace + namespace）：[postgres_impl.py:L3866-L3894](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/postgres_impl.py#L3866-L3894)

- MongoDB
  - 类：`MongoGraphStorage`：[mongo_impl.py:L726-L733](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/mongo_impl.py#L726-L733)
  - 说明：基于 MongoDB 集合（节点/边集合）与 `$graphLookup` 进行多跳查询，命名空间含 workspace 前缀用于隔离：[mongo_impl.py:L746-L779](file:///e:/OPC-ZCKJ/LightRAG-main/LightRAG-main/lightrag/kg/mongo_impl.py#L746-L779)

---

## 5. 前端查询接入建议（现状与缺口）

### 5.1 已可直接用于前端的“查询类”端点

- 标签类：`/graph/label/list`、`/graph/label/popular`、`/graph/label/search`
- 子图：`/graphs`
- 实体存在性：`/graph/entity/exists`
- 结构化 KG 检索数据：`/query/data`

### 5.2 目前缺失但常见的“图数据库查询”能力（如需可补齐）

BaseGraphStorage 具备但当前未暴露为 HTTP 的查询能力（便于前端做点选展开/详情面板/邻接边列表）：

- 单节点属性：`get_node(node_id)`
- 单边属性：`get_edge(src, tgt)`
- 邻接边列表：`get_node_edges(node_id)`
- 度数：`node_degree(node_id)` / `edge_degree(src, tgt)`
- 批量读取：`get_nodes_batch` / `get_edges_batch` / `get_nodes_edges_batch`（前端一次展开多个节点时更高效）

