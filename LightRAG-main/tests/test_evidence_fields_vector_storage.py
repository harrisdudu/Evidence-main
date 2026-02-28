import datetime
import importlib.util

import numpy as np
import pytest

from lightrag.kg.nano_vector_db_impl import NanoVectorDBStorage
from lightrag.kg.shared_storage import initialize_share_data
from lightrag.namespace import NameSpace
from lightrag.utils import EmbeddingFunc


@pytest.mark.offline
@pytest.mark.asyncio
async def test_nanovectordb_persists_evidence_fields(tmp_path):
    initialize_share_data(workers=1)

    async def mock_embedding_func(texts: list[str], _priority: int = 0) -> np.ndarray:
        return np.ones((len(texts), 8), dtype=np.float32)

    embedding_func = EmbeddingFunc(
        embedding_dim=8, func=mock_embedding_func, model_name="test-embed"
    )
    global_config = {
        "working_dir": str(tmp_path),
        "embedding_batch_num": 32,
        "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.2},
    }
    storage = NanoVectorDBStorage(
        namespace=NameSpace.VECTOR_STORE_ENTITIES,
        workspace="ws",
        global_config=global_config,
        embedding_func=embedding_func,
        meta_fields={
            "content",
            "evidence_level",
            "scene_tags",
            "source_provenance",
            "evidence_chain_ids",
        },
    )
    await storage.initialize()

    await storage.upsert(
        {
            "id1": {
                "content": "hello",
                "evidence_level": "A",
                "scene_tags": ["x"],
                "source_provenance": [
                    {
                        "doc_id": "d",
                        "file_name": "f",
                        "file_path": "p",
                        "chunk_id": "c",
                    }
                ],
                "evidence_chain_ids": ["ch1", "ch2"],
                "extra": "no",
            }
        }
    )
    record = await storage.get_by_id("id1")
    assert record is not None
    assert record["evidence_level"] == "A"
    assert record["scene_tags"] == ["x"]
    assert record["source_provenance"][0]["doc_id"] == "d"
    assert record["evidence_chain_ids"] == ["ch1", "ch2"]
    assert "extra" not in record


@pytest.mark.offline
def test_pgvector_normalizes_evidence_fields():
    if importlib.util.find_spec("pgvector") is None:
        pytest.skip("pgvector not installed")

    from lightrag.kg.postgres_impl import PGVectorStorage

    async def mock_embedding_func(texts: list[str], _priority: int = 0) -> np.ndarray:
        return np.ones((len(texts), 8), dtype=np.float32)

    embedding_func = EmbeddingFunc(
        embedding_dim=8, func=mock_embedding_func, model_name="test-embed"
    )
    global_config = {
        "working_dir": "unused",
        "embedding_batch_num": 32,
        "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.2},
    }
    storage = PGVectorStorage(
        namespace=NameSpace.VECTOR_STORE_RELATIONSHIPS,
        workspace="ws",
        global_config=global_config,
        embedding_func=embedding_func,
    )
    now = datetime.datetime(2024, 1, 1)
    upsert_sql, values = storage._upsert_relationships(
        {
            "__id__": "rid",
            "src_id": "s",
            "tgt_id": "t",
            "source_id": "chunk-1",
            "content": "c",
            "__vector__": np.zeros(8, dtype=np.float32),
            "file_path": "p",
            "relation_type": None,
            "evidence_level": "Z",
            "source_provenance": "bad",
        },
        now,
    )
    assert "relation_type" in upsert_sql
    assert "evidence_level" in upsert_sql
    assert len(values) == 13
    assert values[8] == "related"
    assert values[9] == "B"
    assert values[10] == []


@pytest.mark.offline
def test_pgvector_normalizes_evidence_chain_ids():
    if importlib.util.find_spec("pgvector") is None:
        pytest.skip("pgvector not installed")

    from lightrag.kg.postgres_impl import PGVectorStorage

    async def mock_embedding_func(texts: list[str], _priority: int = 0) -> np.ndarray:
        return np.ones((len(texts), 8), dtype=np.float32)

    embedding_func = EmbeddingFunc(
        embedding_dim=8, func=mock_embedding_func, model_name="test-embed"
    )
    global_config = {
        "working_dir": "unused",
        "embedding_batch_num": 32,
        "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.2},
    }
    storage = PGVectorStorage(
        namespace=NameSpace.VECTOR_STORE_ENTITIES,
        workspace="ws",
        global_config=global_config,
        embedding_func=embedding_func,
    )
    now = datetime.datetime(2024, 1, 1)
    _, values = storage._upsert_entities(
        {
            "__id__": "eid",
            "entity_name": "e",
            "source_id": "chunk-1",
            "content": "c",
            "__vector__": np.zeros(8, dtype=np.float32),
            "file_path": "p",
            "evidence_chain_ids": "bad",
        },
        now,
    )
    assert len(values) == 13
    assert values[10] == []
