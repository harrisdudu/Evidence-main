from unittest.mock import AsyncMock

import pytest

from lightrag.base import QueryParam
from lightrag.operate import _get_node_data


@pytest.mark.offline
@pytest.mark.asyncio
async def test_get_node_data_merges_evidence_chain_ids_from_vdb():
    knowledge_graph_inst = AsyncMock()
    knowledge_graph_inst.get_nodes_batch.return_value = {"E1": {"entity_type": "x"}}
    knowledge_graph_inst.node_degrees_batch.return_value = {"E1": 3}
    knowledge_graph_inst.get_nodes_edges_batch.return_value = {"E1": []}
    knowledge_graph_inst.get_edges_batch.return_value = {}
    knowledge_graph_inst.edge_degrees_batch.return_value = {}

    entities_vdb = AsyncMock()
    entities_vdb.cosine_better_than_threshold = 0.2
    entities_vdb.query.return_value = [
        {
            "entity_name": "E1",
            "created_at": 1,
            "evidence_chain_ids": ["c1", "c2"],
            "evidence_level": "A",
            "scene_tags": ["t"],
            "source_provenance": [{"doc_id": "d"}],
        }
    ]

    node_datas, use_relations = await _get_node_data(
        query="q",
        knowledge_graph_inst=knowledge_graph_inst,
        entities_vdb=entities_vdb,
        query_param=QueryParam(top_k=1),
    )
    assert use_relations == []
    assert len(node_datas) == 1
    assert node_datas[0]["entity_name"] == "E1"
    assert node_datas[0]["evidence_chain_ids"] == ["c1", "c2"]
    assert node_datas[0]["evidence_level"] == "A"
    assert node_datas[0]["scene_tags"] == ["t"]
    assert node_datas[0]["source_provenance"][0]["doc_id"] == "d"

