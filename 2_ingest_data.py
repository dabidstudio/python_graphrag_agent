import json
import asyncio
from neo4j import GraphDatabase
from pydantic import validate_call
from neo4j_graphrag.experimental.components.types import (
    Neo4jGraph,
    Neo4jNode,
    Neo4jRelationship,
)
from neo4j_graphrag.experimental.components.kg_writer import KGWriter, KGWriterModel


class Neo4jCreateWriter(KGWriter):
    """Custom KGWriter that uses CREATE instead of MERGE for relationships."""

    def __init__(self, driver, neo4j_database=None):
        self.driver = driver
        self.neo4j_database = neo4j_database


    def _wipe_database(self) -> None:
        self.driver.execute_query(
            "MATCH (n) DETACH DELETE n",
            database_=self.neo4j_database,
        )

    @validate_call
    async def run(self, graph: Neo4jGraph) -> KGWriterModel:
        try:
            self._wipe_database()
            with self.driver.session(database=self.neo4j_database) as session:
                # 1. Write nodes
                for node in graph.nodes:
                    labels = f":{node.label}"
                    session.run(
                        f"""
                        MERGE (n{labels} {{id: $id}})
                        SET n += $props
                        """,
                        {"id": node.id, "props": node.properties or {}},
                    )

                # 2. Write relationships (always CREATE)
                for rel in graph.relationships:
                    session.run(
                        f"""
                        MATCH (a {{id: $start_id}}), (b {{id: $end_id}})
                        CREATE (a)-[r:{rel.type} $props]->(b)
                        """,
                        {
                            "start_id": rel.start_node_id,
                            "end_id": rel.end_node_id,
                            "props": rel.properties or {},
                        },
                    )

            return KGWriterModel(
                status="SUCCESS",
                metadata={
                    "node_count": len(graph.nodes),
                    "relationship_count": len(graph.relationships),
                },
            )
        except Exception as e:
            return KGWriterModel(status="FAILURE", metadata={"error": str(e)})


# -------------------------------
# Example Usage
# -------------------------------
async def write_to_neo4j(graph: Neo4jGraph):
    uri = "neo4j://127.0.0.1:7687"
    user = "neo4j"
    password = "12345678"  # Change to your real password!
    driver = GraphDatabase.driver(uri, auth=(user, password))

    writer = Neo4jCreateWriter(driver)
    result = await writer.run(graph)
    print(result)


if __name__ == "__main__":
    with open("output/지식그래프_최종.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = [Neo4jNode(**node) for node in data["nodes"]]
    relationships = [Neo4jRelationship(**rel) for rel in data.get("relationships", [])]
    graph = Neo4jGraph(nodes=nodes, relationships=relationships)

    asyncio.run(write_to_neo4j(graph))
