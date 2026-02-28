# LightRAG 模型配置完整指南

## 一、配置文件路径

### 1.1 主配置文件

| 文件路径 | 说明 |
|----------|------|
| `.env` | 主配置文件（项目根目录） |
| `lightrag_webui/env.local` | 前端环境配置 |

### 1.2 配置文件加载优先级

```
命令行参数 > 系统环境变量 > .env 文件 > 代码默认值
```

---

## 二、模型配置项汇总

### 2.1 LLM（大语言模型）配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LLM_BINDING` | `ollama` | LLM 后端类型 |
| `LLM_MODEL` | `mistral-nemo:latest` | LLM 模型名称 |
| `LLM_BINDING_HOST` | 详见下方表格 | LLM 服务地址 |
| `LLM_BINDING_API_KEY` | 无 | API 密钥 |
| `LLM_TIMEOUT` | 180 | 请求超时（秒） |

#### LLM Binding 默认主机地址

| Binding 类型 | 默认主机地址 |
|--------------|--------------|
| `ollama` | `http://localhost:11434` |
| `lollms` | `http://localhost:9600` |
| `openai` | `https://api.openai.com/v1` |
| `azure_openai` | `https://api.openai.com/v1` |
| `gemini` | `https://generativelanguage.googleapis.com` |

### 2.2 Embedding（向量化模型）配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EMBEDDING_BINDING` | `ollama` | Embedding 后端类型 |
| `EMBEDDING_MODEL` | `None` (各后端有自己的默认值) | Embedding 模型名称 |
| `EMBEDDING_DIM` | `None` | 向量维度 |
| `EMBEDDING_BINDING_HOST` | 同 LLM 默认地址 | Embedding 服务地址 |
| `EMBEDDING_BINDING_API_KEY` | 无 | API 密钥 |
| `EMBEDDING_SEND_DIM` | `false` | 是否发送维度参数 |
| `EMBEDDING_TOKEN_LIMIT` | `8192` | token 限制 |

#### Embedding 模型默认值

| Binding 类型 | 默认模型 |
|--------------|----------|
| `openai` | `text-embedding-3-small` |
| `jina` | `jina-embeddings-v4` |
| `ollama` | 需要手动指定 |
| 其他 | 需要手动指定 |

### 2.3 Rerank（重排序模型）配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `RERANK_BINDING` | `null` | Rerank 后端类型 |
| `RERANK_MODEL` | 无 | 重排序模型名称 |
| `RERANK_BINDING_HOST` | 无 | 重排序服务地址 |
| `RERANK_BINDING_API_KEY` | 无 | API 密钥 |
| `MIN_RERANK_SCORE` | `0.3` | 最小重排序分数 |
| `RERANK_BY_DEFAULT` | `True` | 默认启用重排序 |

#### Rerank Binding 类型

- `cohere` - Cohere AI / vLLM 部署
- `jina` - Jina AI
- `aliyun` - 阿里云

---

## 三、当前项目配置（.env）

根据 `E:\OPC-ZCKJ\LightRAG-main\LightRAG-main\.env` 文件：

### 3.1 LLM 配置

```bash
# LLM 后端
LLM_BINDING=openai
LLM_MODEL=gpt-20b
LLM_BINDING_HOST=http://172.16.0.28:30000/v1

# Ollama 模拟配置
OLLAMA_EMULATING_MODEL_TAG=latest

# 其他配置
OPENAI_LLM_MAX_COMPLETION_TOKENS=9000
OLLAMA_LLM_NUM_CTX=32768
```

### 3.2 Embedding 配置

```bash
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024
EMBEDDING_SEND_DIM=false
EMBEDDING_TOKEN_LIMIT=8192
EMBEDDING_BINDING_HOST=http://172.16.0.211:10000/v1
EMBEDDING_BINDING_API_KEY=your_api_key
```

### 3.3 Rerank 配置

```bash
RERANK_BINDING=cohere
RERANK_MODEL=bge-rerank-v2
RERERANK_BINDING_HOST=http://172.16.0.60:10000/v1/rerank
RERANK_BINDING_API_KEY=your_rerank_api_key_here
RERANK_BY_DEFAULT=True
MIN_RERANK_SCORE=0.3
```

---

## 四、代码中的配置加载

### 4.1 配置文件位置

**主配置文件**: `lightrag/api/config.py`

关键代码位置：

| 行号 | 配置项 |
|------|--------|
| 359 | `LLM_MODEL` 默认值 `mistral-nemo:latest` |
| 362 | `EMBEDDING_MODEL` 默认值 `None` |
| 365 | `EMBEDDING_DIM` 默认值 `None` |
| 407 | `RERANK_MODEL` 默认值 `None` |

### 4.2 配置读取流程

```python
# 1. 从环境变量或默认值获取
args.llm_model = get_env_value("LLM_MODEL", "mistral-nemo:latest")

# 2. 获取主机地址
args.llm_binding_host = get_env_value(
    "LLM_BINDING_HOST", get_default_host(args.llm_binding)
)

# 3. 获取 API 密钥
args.llm_binding_api_key = get_env_value("LLM_BINDING_API_KEY", None)
```

---

## 五、存储配置

### 5.1 存储类型配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `LIGHTRAG_KV_STORAGE` | `JsonKVStorage` | 键值存储 |
| `LIGHTRAG_VECTOR_STORAGE` | `NanoVectorDBStorage` | 向量存储 |
| `LIGHTRAG_GRAPH_STORAGE` | `NetworkXStorage` | 图谱存储 |
| `LIGHTRAG_DOC_STATUS_STORAGE` | `JsonDocStatusStorage` | 文档状态存储 |

### 5.2 当前项目存储配置

```bash
# 键值存储
LIGHTRAG_KV_STORAGE=JsonKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=JsonDocStatusStorage

# 向量存储
LIGHTRAG_VECTOR_STORAGE=MilvusVectorDBStorage

# 图谱存储
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage
```

### 5.3 外部存储配置

#### Neo4j
```bash
NEO4J_URI=bolt://192.168.0.197:27687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD='kps@2025'
NEO4J_DATABASE=neo4j
```

#### PostgreSQL
```bash
POSTGRES_HOST=192.168.0.197
POSTGRES_PORT=15432
POSTGRES_USER=kps
POSTGRES_PASSWORD='Kps@2025'
POSTGRES_DATABASE=light_rag
```

#### Milvus
```bash
MILVUS_URI=http://192.168.0.197:19530
MILVUS_DB_NAME=harris
```

---

## 六、常用配置示例

### 6.1 OpenAI LLM + Ollama Embedding

```bash
LLM_BINDING=openai
LLM_MODEL=gpt-4o
LLM_BINDING_HOST=https://api.openai.com/v1
LLM_BINDING_API_KEY=sk-xxx

EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_DIM=1024
EMBEDDING_BINDING_HOST=http://localhost:11434
```

### 6.2 Ollama 本地部署

```bash
LLM_BINDING=ollama
LLM_MODEL=qwen2.5:7b
LLM_BINDING_HOST=http://localhost:11434
OLLAMA_LLM_NUM_CTX=32768

EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_DIM=1024
```

### 6.3 Azure OpenAI

```bash
LLM_BINDING=azure_openai
LLM_MODEL=gpt-4o
LLM_BINDING_HOST=https://your-resource.openai.azure.com/
LLM_BINDING_API_KEY=your-azure-key
AZURE_OPENAI_API_VERSION=2024-08-01-preview

EMBEDDING_BINDING=azure_openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=3072
```

---

## 七、配置验证

### 7.1 检查服务是否正常运行

```bash
# 后端 API
curl http://localhost:9621/health

# 检查模型配置
lightrag-server --llm-binding openai --help
lightrag-server --embedding-binding openai --help
```

### 7.2 常见问题

1. **Embedding 模型维度不匹配**: 删除现有向量存储，重新初始化
2. **LLM 超时**: 调整 `LLM_TIMEOUT` 参数
3. **API 密钥错误**: 检查 `*_BINDING_API_KEY` 配置

---

*文档版本: v1.0*  
*更新时间: 2026-02-27*
