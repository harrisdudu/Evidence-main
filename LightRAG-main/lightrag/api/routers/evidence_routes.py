# Evidence Chain API Routes
# Based on: docs/evidence_chain_frontend_design.md

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from lightrag import LightRAG


def create_evidence_routes(rag, api_key: Optional[str] = None):
    """创建证据链路由"""
    router = APIRouter(prefix="/evidence", tags=["evidence"])

    class EvidenceQueryParams(BaseModel):
        evidence_levels: List[str] = []
        relation_types: List[str] = []
        scene_tags: List[str] = []
        keyword: str = ""
        page: int = 1
        page_size: int = 20
        sort_by: str = "relevance"
        sort_order: str = "desc"

    class EvidenceEntityResponse(BaseModel):
        entity_name: str
        entity_type: str
        description: str
        evidence_level: str
        scene_tags: List[str]
        source_provenance: List[Dict[str, Any]]
        evidence_chain_ids: List[str]
        related_entities: List[Dict[str, Any]] = []

    class EvidenceStatsResponse(BaseModel):
        total_entities: int
        by_evidence_level: Dict[str, int]
        by_relation_type: Dict[str, int]
        by_scene_tag: Dict[str, int]

    class EvidenceChainResponse(BaseModel):
        chain_id: str
        chain_type: str
        entities: List[str]
        description: str
        evidence_level: str
        source_provenance: Dict[str, Any]
        related_chains: List[str] = []

    class EvidenceGraphResponse(BaseModel):
        nodes: List[Dict[str, Any]]
        edges: List[Dict[str, Any]]

    @router.post("/query")
    async def query_evidence(request: EvidenceQueryParams):
        """查询证据链"""
        try:
            kg = rag.knowledge_graph
            if kg is None:
                return {
                    "items": [],
                    "total": 0,
                    "page": request.page,
                    "page_size": request.page_size,
                    "total_pages": 0,
                }

            all_nodes = []
            try:
                async with kg._driver.session(database=kg._DATABASE) as session:
                    result = await session.run("MATCH (n) RETURN n")
                    records = await result.data()
                    for record in records:
                        node = dict(record["n"])
                        all_nodes.append(node)
            except Exception as e:
                print(f"Error querying nodes: {e}")
                try:
                    all_nodes = await kg.get_all_nodes()
                except:
                    pass

            if request.keyword:
                all_nodes = [
                    n for n in all_nodes
                    if request.keyword.lower() in n.get("entity_id", "").lower()
                    or request.keyword.lower() in n.get("description", "").lower()
                ]

            all_nodes = [n for n in all_nodes if n.get("evidence_chain_ids")]

            items = []
            for node in all_nodes:
                entity_name = node.get("entity_id", "")

                related_entities = []
                try:
                    neighbors = await kg.get_neighbors(entity_name)
                    for neighbor in neighbors:
                        related_entities.append({
                            "entity_name": neighbor.get("entity_id", ""),
                            "relation_type": neighbor.get("keywords", ""),
                        })
                except:
                    pass

                items.append({
                    "entity_name": entity_name,
                    "entity_type": node.get("entity_type", "UNKNOWN"),
                    "description": node.get("description", ""),
                    "evidence_level": node.get("evidence_level", "B"),
                    "scene_tags": node.get("scene_tags", []),
                    "source_provenance": node.get("source_provenance", []),
                    "evidence_chain_ids": node.get("evidence_chain_ids", []),
                    "related_entities": related_entities[:5],
                })

            total = len(items)
            total_pages = (total + request.page_size - 1) // request.page_size
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_items = items[start_idx:end_idx]

            return {
                "items": paginated_items,
                "total": total,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": total_pages,
            }

        except Exception as e:
            print(f"Error in query_evidence: {e}")
            return {
                "items": [],
                "total": 0,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": 0,
            }

    @router.get("/stats")
    async def get_evidence_stats(scene_tag: Optional[str] = Query(None)):
        """获取证据统计信息"""
        try:
            kg = rag.knowledge_graph
            if kg is None:
                return {
                    "total_entities": 0,
                    "by_evidence_level": {},
                    "by_relation_type": {},
                    "by_scene_tag": {},
                }

            all_nodes = []
            try:
                async with kg._driver.session(database=kg._DATABASE) as session:
                    result = await session.run("MATCH (n) RETURN n")
                    records = await result.data()
                    for record in records:
                        node = dict(record["n"])
                        all_nodes.append(node)
            except:
                try:
                    all_nodes = await kg.get_all_nodes()
                except:
                    pass

            evidence_nodes = [n for n in all_nodes if n.get("evidence_chain_ids")]

            by_evidence_level = {}
            for node in evidence_nodes:
                level = node.get("evidence_level", "B")
                by_evidence_level[level] = by_evidence_level.get(level, 0) + 1

            by_relation_type = {}
            try:
                async with kg._driver.session(database=kg._DATABASE) as session:
                    result = await session.run("MATCH ()-[r]->() RETURN r")
                    records = await result.data()
                    for record in records:
                        rel = dict(record["r"])
                        rel_type = rel.get("relation_type", "related")
                        by_relation_type[rel_type] = by_relation_type.get(rel_type, 0) + 1
            except:
                pass

            by_scene_tag = {}
            for node in evidence_nodes:
                tags = node.get("scene_tags", [])
                for tag in tags:
                    by_scene_tag[tag] = by_scene_tag.get(tag, 0) + 1

            return {
                "total_entities": len(evidence_nodes),
                "by_evidence_level": by_evidence_level,
                "by_relation_type": by_relation_type,
                "by_scene_tag": by_scene_tag,
            }

        except Exception as e:
            print(f"Error in get_evidence_stats: {e}")
            return {
                "total_entities": 0,
                "by_evidence_level": {},
                "by_relation_type": {},
                "by_scene_tag": {},
            }

    @router.get("/entity/{entity_name}")
    async def get_entity_details(entity_name: str):
        """获取实体详情"""
        try:
            kg = rag.knowledge_graph
            if kg is None:
                raise ValueError("Knowledge graph not initialized")

            node = await kg.get_node(entity_name)
            if node is None:
                raise ValueError(f"Entity {entity_name} not found")

            related_entities = []
            try:
                neighbors = await kg.get_neighbors(entity_name)
                for neighbor in neighbors:
                    related_entities.append({
                        "entity_name": neighbor.get("entity_id", ""),
                        "relation_type": neighbor.get("keywords", ""),
                        "description": neighbor.get("description", ""),
                    })
            except:
                pass

            return {
                "entity_name": entity_name,
                "entity_type": node.get("entity_type", "UNKNOWN"),
                "description": node.get("description", ""),
                "evidence_level": node.get("evidence_level", "B"),
                "scene_tags": node.get("scene_tags", []),
                "source_provenance": node.get("source_provenance", []),
                "evidence_chain_ids": node.get("evidence_chain_ids", []),
                "related_entities": related_entities,
            }

        except Exception as e:
            print(f"Error in get_entity_details: {e}")
            raise

    @router.get("/chain/{chain_id}")
    async def get_chain_details(chain_id: str):
        """获取证据链详情"""
        try:
            kg = rag.knowledge_graph
            if kg is None:
                raise ValueError("Knowledge graph not initialized")

            chain_entities = []
            chain_description = ""
            chain_evidence_level = "B"
            chain_source_provenance = {}

            try:
                async with kg._driver.session(database=kg._DATABASE) as session:
                    query = """
                    MATCH (a)-[r]->(b)
                    WHERE r.evidence_chain_ids CONTAINS $chain_id
                    RETURN a, r, b
                    """
                    result = await session.run(query, chain_id=chain_id)
                    records = await result.data()

                    for record in records:
                        src = dict(record["a"])
                        rel = dict(record["r"])
                        tgt = dict(record["b"])

                        chain_entities.append(src.get("entity_id", ""))
                        chain_entities.append(tgt.get("entity_id", ""))

                        if not chain_description:
                            chain_description = rel.get("description", "")
                        if chain_evidence_level == "B":
                            chain_evidence_level = rel.get("evidence_level", "B")
                        if not chain_source_provenance:
                            chain_source_provenance = rel.get("source_provenance", {})

            except Exception as e:
                print(f"Error searching chain: {e}")

            chain_type = "related"
            try:
                async with kg._driver.session(database=kg._DATABASE) as session:
                    query = """
                    MATCH ()-[r]->()
                    WHERE r.evidence_chain_ids CONTAINS $chain_id
                    RETURN r.relation_type as type
                    LIMIT 1
                    """
                    result = await session.run(query, chain_id=chain_id)
                    records = await result.data()
                    if records:
                        chain_type = records[0].get("type", "related")
            except:
                pass

            return {
                "chain_id": chain_id,
                "chain_type": chain_type,
                "entities": list(set(chain_entities)),
                "description": chain_description,
                "evidence_level": chain_evidence_level,
                "source_provenance": chain_source_provenance,
                "related_chains": [],
            }

        except Exception as e:
            print(f"Error in get_chain_details: {e}")
            raise

    @router.post("/visualize")
    async def get_evidence_visualize(request: Dict[str, Any]):
        """获取证据链可视化数据"""
        try:
            entity_name = request.get("entity_name", "")
            depth = request.get("depth", 2)
            evidence_levels = request.get("evidence_levels", [])
            relation_types = request.get("relation_types", [])

            kg = rag.knowledge_graph
            if kg is None:
                return {"nodes": [], "edges": []}

            nodes = []
            edges = []
            visited = set()

            async def fetch_neighbors(node_name: str, current_depth: int):
                if current_depth > depth or node_name in visited:
                    return

                visited.add(node_name)

                node = await kg.get_node(node_name)
                if node:
                    nodes.append({
                        "id": node_name,
                        "label": node_name,
                        "type": node.get("entity_type", "UNKNOWN"),
                        "evidence_level": node.get("evidence_level", "B"),
                        "evidence_chain_ids": node.get("evidence_chain_ids", []),
                    })

                try:
                    neighbors = await kg.get_neighbors(node_name)
                    for neighbor in neighbors:
                        neighbor_name = neighbor.get("entity_id", "")
                        rel_type = neighbor.get("keywords", "")

                        if evidence_levels and neighbor.get("evidence_level") not in evidence_levels:
                            continue
                        if relation_types and rel_type not in relation_types:
                            continue

                        edges.append({
                            "source": node_name,
                            "target": neighbor_name,
                            "relation_type": rel_type,
                            "description": neighbor.get("description", ""),
                        })

                        await fetch_neighbors(neighbor_name, current_depth + 1)
                except:
                    pass

            if entity_name:
                await fetch_neighbors(entity_name, 0)
            else:
                try:
                    all_nodes = await kg.get_all_nodes()
                    for node in all_nodes:
                        node_name = node.get("entity_id", "")
                        if node.get("evidence_chain_ids") and node_name not in visited:
                            await fetch_neighbors(node_name, 0)
                            if len(nodes) >= 50:
                                break
                except:
                    pass

            return {"nodes": nodes, "edges": edges}

        except Exception as e:
            print(f"Error in get_evidence_visualize: {e}")
            return {"nodes": [], "edges": []}

    return router
