"""
重建向量库索引脚本

通过 API 重新索引现有文档
"""

import requests
import json

# 配置
API_BASE = "http://localhost:9621"
API_KEY = ""  # 如果设置了 LIGHTRAP_API_KEY，在这里填写

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY


def rebuild_index():
    print("=" * 50)
    print("开始重建索引...")
    print("=" * 50)

    # 方式1：扫描 inputs 目录重新索引
    print("\n[方式1] 扫描 inputs 目录...")
    response = requests.post(f"{API_BASE}/documents/scan", headers=HEADERS, json={})
    print(f"扫描结果: {response.status_code}")
    print(response.text)

    # 方式2：通过文本直接索引
    # print("\n[方式2] 通过文本索引...")
    # response = requests.post(
    #     f"{API_BASE}/documents/text",
    #     headers=HEADERS,
    #     json={
    #         "texts": ["你的文档内容1", "你的文档内容2"]
    #     }
    # )
    # print(f"索引结果: {response.status_code}")
    # print(response.text)

    print("\n" + "=" * 50)
    print("索引任务已提交！")
    print("请通过 Web UI 或 API 查看进度: /documents/pipeline_status")
    print("=" * 50)


if __name__ == "__main__":
    rebuild_index()
