"""
直接清空 Milvus 向量库脚本

连接到 Milvus 并清空所有向量数据
"""

import os

from dotenv import load_dotenv

try:
    from pymilvus import MilvusClient  # type: ignore
except ModuleNotFoundError as e:
    raise SystemExit(
        "缺少依赖：pymilvus。请先安装：pip install 'pymilvus>=2.6.2'"
    ) from e

load_dotenv(dotenv_path=".env", override=False)

MILVUS_URI = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "lightrag")


def clear_milvus():
    print("=" * 50)
    print("清空 Milvus 向量库...")
    print("=" * 50)

    try:
        client = MilvusClient(uri=MILVUS_URI, db_name=MILVUS_DB_NAME)

        # 获取所有 collection
        collections = client.list_collections()
        print(f"找到 {len(collections)} 个 collection: {collections}")

        # 删除所有 collection
        for coll in collections:
            print(f"删除 collection: {coll}")
            client.drop_collection(coll)

        print("\nMilvus 向量库已清空！")
        print("重新启动服务后会自动创建新的 collection")

    except Exception as e:
        print(f"错误: {e}")
        print("请检查 Milvus 连接配置")


if __name__ == "__main__":
    clear_milvus()
