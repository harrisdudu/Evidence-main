"""
删除向量库脚本

用于删除现有的向量数据库，以便重新索引。
"""

import shutil
import os

# 向量库存储目录（根据你的 working_dir 修改）
VECTOR_STORE_DIR = "./rag_storage/vector_store"


def delete_vector_store():
    """删除向量库目录"""
    if os.path.exists(VECTOR_STORE_DIR):
        shutil.rmtree(VECTOR_STORE_DIR)
        print(f"✅ 已删除向量库目录: {VECTOR_STORE_DIR}")
    else:
        print(f"📁 向量库目录不存在: {VECTOR_STORE_DIR}")

    # 同时清理可能的缓存目录
    cache_dirs = [
        "./rag_storage/llm_response_cache",
        "./rag_storage/entity_chunks",
        "./rag_storage/relation_chunks",
    ]

    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            print(f"🗑️  清理缓存: {cache_dir}")


if __name__ == "__main__":
    delete_vector_store()
    print("\n请重新运行索引脚本以重建向量库！")
