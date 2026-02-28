# 任务列表：为 operate.py 添加中文注释

## 任务说明
将5000行的 `operate.py` 文件按功能模块划分为多个任务，每个任务处理特定范围的代码并添加中文注释。

## 任务列表

- [x] 任务1：导入模块和工具函数部分（第1-200行）
  - [x] 1.1 导入语句注释
  - [x] 1.2 环境变量加载注释
  - [x] 1.3 `_truncate_entity_identifier` 函数注释
  - [x] 1.4 `chunking_by_token_size` 函数注释

- [x] 任务2：实体/关系摘要处理函数（第201-400行）
  - [x] 2.1 `_handle_entity_relation_summary` 函数注释
  - [x] 2.2 `_summarize_descriptions` 函数注释

- [x] 任务3：单个实体/关系提取处理（第401-550行）
  - [x] 3.1 `_handle_single_entity_extraction` 函数注释
  - [x] 3.2 `_handle_single_relationship_extraction` 函数注释

- [x] 任务4：从缓存重建知识图谱（第551-820行）
  - [x] 4.1 `rebuild_knowledge_from_chunks` 函数注释
  - [x] 4.2 `_get_cached_extraction_results` 函数注释

- [x] 任务5：提取结果处理（第821-1050行）
  - [x] 5.1 `_process_extraction_result` 函数注释
  - [x] 5.2 `_rebuild_from_extraction_result` 函数注释

- [x] 任务6：单个实体重建（第1051-1350行）
  - [x] 6.1 `_rebuild_single_entity` 函数注释
  - [x] 6.2 相关辅助函数注释

- [x] 任务7：单个关系重建（第1351-1650行）
  - [x] 7.1 `_rebuild_single_relationship` 函数注释

- [x] 任务8：实体合并与插入（第1651-1950行）
  - [x] 8.1 `_merge_nodes_then_upsert` 函数注释
  - [x] 8.2 实体插入相关逻辑注释

- [x] 任务9：关系合并与插入（第1951-2250行）
  - [x] 9.1 `_merge_edges_then_upsert` 函数注释

- [x] 任务10：剩余函数处理（第2251-5000行）
  - [x] 10.1 后续所有函数和类的注释

## 任务依赖关系
- 任务按顺序执行，每个任务完成后才开始下一个
- 同一任务内的子任务可以并行执行

## 验收标准
- 每个任务完成后，相关代码行数范围内所有函数都有中文注释
- 注释准确描述函数功能、参数和返回值
- 代码逻辑不改变
