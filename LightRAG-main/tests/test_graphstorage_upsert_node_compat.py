from unittest.mock import AsyncMock

import pytest

from lightrag.kg.neo4j_impl import Neo4JStorage


@pytest.mark.offline
@pytest.mark.asyncio
async def test_neo4j_upsert_node_accepts_entity_id_kwargs():
    storage = Neo4JStorage(
        namespace="test",
        global_config={"working_dir": "tmp"},
        embedding_func=None,
        workspace="base",
    )

    tx = AsyncMock()
    run_result = AsyncMock()
    run_result.consume = AsyncMock()
    tx.run.return_value = run_result

    session = AsyncMock()

    async def execute_write(fn):
        await fn(tx)

    session.execute_write.side_effect = execute_write

    class _SessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _Driver:
        def session(self, database=None):
            return _SessionCM()

    storage._driver = _Driver()
    storage._DATABASE = None

    await storage.upsert_node(
        entity_id="E1",
        entity_type="T",
        description="D",
        source_id="S",
        file_path="F",
    )

    _, kwargs = tx.run.call_args
    assert kwargs["entity_id"] == "E1"
    assert kwargs["properties"]["entity_id"] == "E1"
