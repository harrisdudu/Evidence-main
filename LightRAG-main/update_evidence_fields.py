"""
证据链字段更新脚本

用于为现有向量数据库中的实体和关系添加证据链字段。
此脚本会：
1. 从图数据库获取所有现有实体和关系
2. 为它们添加证据链字段（evidence_level, scene_tags, source_provenance, relation_type）
3. 重新写入向量数据库

使用方法:
    python update_evidence_fields.py
"""

import asyncio
import json
import logging
from typing import Any

from lightrag import LightRAG
from lightrag.utils import logger, compute_mdhash_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_evidence_fields(rag: LightRAG):
    """更新现有实体和关系的证据链字段"""

    logger.info("=" * 50)
    logger.info("开始更新证据链字段...")
    logger.info("=" * 50)

    # 1. 获取图数据库中的所有实体
    logger.info("正在获取图数据库中的所有实体...")
    try:
        all_nodes = await rag.chunk_entity_relation_graph.get_all_nodes()
        logger.info(f"找到 {len(all_nodes)} 个实体节点")
    except Exception as e:
        logger.error(f"获取实体节点失败: {e}")
        all_nodes = []

    # 2. 更新实体向量数据库
    if rag.entities_vdb and all_nodes:
        logger.info("正在更新实体向量数据库...")

        entity_updates = {}
        for node in all_nodes:
            node_data = dict(node)  # 复制数据

            # 生成向量ID
            from lightrag.operate import compute_mdhash_id

            entity_name = node_data.get("entity_name") or node_data.get("entity_id", "")
            if not entity_name:
                continue

            entity_vdb_id = compute_mdhash_id(str(entity_name), prefix="ent-")

            # 构建更新数据
            entity_content = f"{entity_name}\n{node_data.get('description', '')}"

            entity_updates[entity_vdb_id] = {
                "content": entity_content,
                "entity_name": entity_name,
                "entity_type": node_data.get("entity_type", "UNKNOWN"),
                "source_id": node_data.get("source_id", ""),
                "description": node_data.get("description", ""),
                "file_path": node_data.get("file_path", ""),
                # 证据链增强字段
                "evidence_level": node_data.get("evidence_level", "B"),
                "scene_tags": node_data.get("scene_tags", []),
                "source_provenance": node_data.get("source_provenance", []),
                "evidence_chain_ids": node_data.get("evidence_chain_ids", []),
            }

        if entity_updates:
            logger.info(f"正在写入 {len(entity_updates)} 个实体到向量数据库...")
            await rag.entities_vdb.upsert(entity_updates)
            logger.info(f"✅ 实体向量数据库更新完成")
        else:
            logger.info("没有实体需要更新")

    # 3. 获取图数据库中的所有关系
    logger.info("正在获取图数据库中的所有关系...")
    try:
        all_edges = await rag.chunk_entity_relation_graph.get_all_edges()
        logger.info(f"找到 {len(all_edges)} 个关系边")
    except Exception as e:
        logger.error(f"获取关系边失败: {e}")
        all_edges = []

    # 4. 更新关系向量数据库
    if rag.relationships_vdb and all_edges:
        logger.info("正在更新关系向量数据库...")

        relationship_updates = {}
        for edge in all_edges:
            edge_data = dict(edge)  # 复制数据

            src_id = edge_data.get("src_id", "")
            tgt_id = edge_data.get("tgt_id", "")

            if not src_id or not tgt_id:
                continue

            # 生成关系向量ID (正序和逆序)
            rel_vdb_id = compute_mdhash_id(src_id + tgt_id, prefix="rel-")

            # 构建关系内容
            keywords = edge_data.get("keywords", "")
            description = edge_data.get("description", "")
            rel_content = f"{keywords}\t{src_id}\n{tgt_id}\n{description}"

            relationship_updates[rel_vdb_id] = {
                "src_id": src_id,
                "tgt_id": tgt_id,
                "source_id": edge_data.get("source_id", ""),
                "content": rel_content,
                "keywords": keywords,
                "description": description,
                "weight": edge_data.get("weight", 1.0),
                "file_path": edge_data.get("file_path", ""),
                # 证据链增强字段
                "relation_type": edge_data.get("relation_type", "related"),
                "evidence_level": edge_data.get("evidence_level", "B"),
                "source_provenance": edge_data.get("source_provenance", []),
            }

        if relationship_updates:
            logger.info(f"正在写入 {len(relationship_updates)} 个关系到向量数据库...")
            await rag.relationships_vdb.upsert(relationship_updates)
            logger.info(f"✅ 关系向量数据库更新完成")
        else:
            logger.info("没有关系需要更新")

    logger.info("=" * 50)
    logger.info("证据链字段更新完成!")
    logger.info("=" * 50)


async def main():
    """主函数"""
    # 初始化 LightRAG
    # 请根据你的实际情况修改工作目录
    rag = LightRAG(
        working_dir="./rag_storage",
    )

    await update_evidence_fields(rag)


if __name__ == "__main__":
    asyncio.run(main())
