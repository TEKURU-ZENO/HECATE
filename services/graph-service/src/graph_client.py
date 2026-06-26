import time
from datetime import datetime, timedelta
import structlog

log = structlog.get_logger()


class BaseGraphClient:
    def close(self):
        pass

    def initialize_topology(self, topology: list):
        pass

    def create_or_update_node(self, label: str, identifier: str, properties: dict):
        pass

    def create_relationship(self, from_label: str, from_key: str, to_label: str, to_key: str, rel_type: str, properties: dict = None):
        pass

    def get_rca_root_cause(self, target_service: str) -> dict:
        pass

    def get_neighbor_recommendations(self, target_service: str, incident_type: str) -> list:
        pass

    def get_graph_data(self) -> dict:
        pass

    def archive_old_nodes(self, days: int):
        pass

    def run_raw_query(self, query: str, parameters: dict = None) -> list:
        return []

    def clear_all(self):
        pass


class MockGraphClient(BaseGraphClient):
    def __init__(self):
        # self.nodes: key is (label, identifier), value is properties dict
        self.nodes = {}
        # self.edges: list of dicts: {"from_label": str, "from_key": str, "to_label": str, "to_key": str, "rel_type": str, "properties": dict}
        self.edges = []
        log.info("graph_client.mock_initialized")

    def initialize_topology(self, topology: list):
        """Seed service nodes and DEPENDS_ON relationships from topology list: [{"service": str, "depends_on": list[str]}]"""
        for item in topology:
            svc = item["service"]
            self.create_or_update_node("Service", svc, {"name": svc, "status": "healthy"})
            for dep in item.get("depends_on", []):
                self.create_or_update_node("Service", dep, {"name": dep, "status": "healthy"})
                self.create_relationship("Service", svc, "Service", dep, "DEPENDS_ON")
        log.info("graph_client.mock_topology_seeded", services_count=len(topology))

    def create_or_update_node(self, label: str, identifier: str, properties: dict):
        key = (label.lower(), identifier)
        props = properties.copy()
        props["label"] = label
        props["id"] = identifier
        if "created_at" not in props:
            props["created_at"] = time.time()
        self.nodes[key] = props
        log.info("graph_client.mock_node_synced", label=label, id=identifier)

    def create_relationship(self, from_label: str, from_key: str, to_label: str, to_key: str, rel_type: str, properties: dict = None):
        # Check if relationship already exists
        exists = False
        for edge in self.edges:
            if (edge["from_label"].lower() == from_label.lower() and
                    edge["from_key"] == from_key and
                    edge["to_label"].lower() == to_label.lower() and
                    edge["to_key"] == to_key and
                    edge["rel_type"].upper() == rel_type.upper()):
                exists = True
                if properties:
                    edge["properties"].update(properties)
                break
        
        if not exists:
            self.edges.append({
                "from_label": from_label,
                "from_key": from_key,
                "to_label": to_label,
                "to_key": to_key,
                "rel_type": rel_type.upper(),
                "properties": properties or {}
            })
        log.info("graph_client.mock_relationship_created", from_key=from_key, to_key=to_key, rel=rel_type)

    def get_rca_root_cause(self, target_service: str) -> dict:
        """
        RCA Graph Traversal:
        Find downstream services via DEPENDS_ON chains.
        Return active incident nodes (OCCURRED_ON relationships) on those downstream services.
        """
        visited = set()
        to_visit = [target_service]
        dependents = []

        # Reachability via DEPENDS_ON path traversal
        while to_visit:
            curr = to_visit.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            if curr != target_service:
                dependents.append(curr)
            
            # Find all nodes curr depends on
            for edge in self.edges:
                if edge["from_label"].lower() == "service" and edge["from_key"] == curr and edge["rel_type"] == "DEPENDS_ON":
                    to_visit.append(edge["to_key"])

        # Check for open incidents occurred on dependents
        for dep_svc in dependents:
            # Check if there is an open incident occurred on dep_svc
            for node_key, node_props in self.nodes.items():
                if node_key[0] == "incident":
                    # Check OCCURRED_ON relation from incident to dep_svc
                    for edge in self.edges:
                        if (edge["from_label"].lower() == "incident" and edge["from_key"] == node_props["id"] and
                                edge["to_label"].lower() == "service" and edge["to_key"] == dep_svc and
                                edge["rel_type"] == "OCCURRED_ON"):
                            status = node_props.get("status", "open").lower()
                            if status not in ["remediated", "closed", "failed", "rejected"]:
                                log.info("graph_client.mock_rca_root_cause_found", target=target_service, root=dep_svc, incident_id=node_props["id"])
                                return {
                                    "root_cause_service": dep_svc,
                                    "incident_id": node_props["id"],
                                    "title": node_props.get("title", ""),
                                    "root_cause": node_props.get("root_cause", "")
                                }
        
        # Self root cause fallback
        log.info("graph_client.mock_rca_no_downstream_root", target=target_service)
        return {
            "root_cause_service": target_service,
            "incident_id": None,
            "title": "Self root cause",
            "root_cause": f"No downstream incident found. Root cause isolated to {target_service}."
        }

    def get_neighbor_recommendations(self, target_service: str, incident_type: str) -> list:
        """
        Recommendation Neighbor Discovery:
        Find services connected directly to target_service via DEPENDS_ON (either direction).
        Check historical incidents RESOLVED_BY playbooks on those neighbors.
        """
        neighbors = set()
        for edge in self.edges:
            if edge["rel_type"] == "DEPENDS_ON":
                if edge["from_key"] == target_service:
                    neighbors.add(edge["to_key"])
                elif edge["to_key"] == target_service:
                    neighbors.add(edge["from_key"])

        recommendations = []
        for neighbor in neighbors:
            # Query playbooks resolved on neighbor
            for edge in self.edges:
                if edge["rel_type"] == "OCCURRED_ON" and edge["to_key"] == neighbor:
                    inc_id = edge["from_key"]
                    # Find RESOLVED_BY playbook relationship
                    for r_edge in self.edges:
                        if r_edge["from_key"] == inc_id and r_edge["rel_type"] == "RESOLVED_BY":
                            playbook_name = r_edge["to_key"]
                            # Fetch playbook details if available
                            pb_props = self.nodes.get(("playbook", playbook_name), {})
                            recommendations.append({
                                "playbook": playbook_name,
                                "neighbor": neighbor,
                                "incident_type": incident_type,
                                "success_rate": pb_props.get("success_rate", 0.9)
                            })
        
        log.info("graph_client.mock_neighbor_recommendations_retrieved", target=target_service, count=len(recommendations))
        return recommendations

    def get_graph_data(self) -> dict:
        nodes_list = []
        for key, props in self.nodes.items():
            nodes_list.append({
                "data": {
                    "id": props["id"],
                    "label": props.get("name", props["id"]),
                    "type": props["label"],
                    "status": props.get("status", "healthy")
                }
            })
        
        edges_list = []
        for edge in self.edges:
            edges_list.append({
                "data": {
                    "source": edge["from_key"],
                    "target": edge["to_key"],
                    "label": edge["rel_type"]
                }
            })
            
        return {"nodes": nodes_list, "edges": edges_list}

    def archive_old_nodes(self, days: int):
        now = time.time()
        cutoff = now - (days * 86400)
        
        # Identify nodes to delete
        to_delete = []
        for key, props in self.nodes.items():
            if props["label"] in ["Incident", "Recommendation", "Approval"]:
                if props.get("created_at", now) < cutoff:
                    to_delete.append(key)

        for key in to_delete:
            label, identifier = key
            # Delete relationship edges
            self.edges = [e for e in self.edges if not (
                (e["from_label"].lower() == label and e["from_key"] == identifier) or
                (e["to_label"].lower() == label and e["to_key"] == identifier)
            )]
            del self.nodes[key]
            log.info("graph_client.mock_node_archived", label=label, id=identifier)

    def run_raw_query(self, query: str, parameters: dict = None) -> list:
        log.info("graph_client.mock_raw_query", query=query, params=parameters)
        return []

    def clear_all(self):
        self.nodes.clear()
        self.edges.clear()
        log.info("graph_client.mock_cleared")


class Neo4jGraphClient(BaseGraphClient):
    def __init__(self, uri, user, password):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Ensure driver works
        self.driver.verify_connectivity()
        log.info("graph_client.neo4j_connected", uri=uri)

    def close(self):
        self.driver.close()

    def initialize_topology(self, topology: list):
        with self.driver.session() as session:
            # Seed Service nodes and DEPENDS_ON relations
            for item in topology:
                svc = item["service"]
                session.run(
                    "MERGE (s:Service {name: $name}) ON CREATE SET s.status = 'healthy'",
                    name=svc
                )
                for dep in item.get("depends_on", []):
                    session.run(
                        "MERGE (s:Service {name: $name}) ON CREATE SET s.status = 'healthy'",
                        name=dep
                    )
                    session.run(
                        "MATCH (a:Service {name: $from_svc}), (b:Service {name: $to_svc}) "
                        "MERGE (a)-[:DEPENDS_ON]->(b)",
                        from_svc=svc, to_svc=dep
                    )
        log.info("graph_client.neo4j_topology_initialized")

    def create_or_update_node(self, label: str, identifier: str, properties: dict):
        # Cypher parameterized query
        cypher = f"MERGE (n:{label} {{id: $id}}) SET n += $properties"
        if label.lower() == "service":
            cypher = f"MERGE (n:{label} {{name: $id}}) SET n += $properties"
            
        props = properties.copy()
        if "created_at" not in props:
            props["created_at"] = time.time()
            
        with self.driver.session() as session:
            session.run(cypher, id=identifier, properties=props)

    def create_relationship(self, from_label: str, from_key: str, to_label: str, to_key: str, rel_type: str, properties: dict = None):
        from_id_field = "name" if from_label.lower() == "service" else "id"
        to_id_field = "name" if to_label.lower() == "service" else "id"
        
        cypher = (
            f"MATCH (a:{from_label} {{{from_id_field}: $from_key}}), (b:{to_label} {{{to_id_field}: $to_key}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += $properties"
        )
        with self.driver.session() as session:
            session.run(cypher, from_key=from_key, to_key=to_key, properties=properties or {})

    def get_rca_root_cause(self, target_service: str) -> dict:
        """
        RCA Cypher Traversal:
        Finds open incidents occurred downstream from target service.
        """
        cypher = (
            "MATCH (s:Service {name: $target})-[:DEPENDS_ON*1..3]->(dep:Service)<-[:OCCURRED_ON]-(i:Incident) "
            "WHERE NOT i.status IN ['remediated', 'closed', 'failed', 'rejected'] "
            "RETURN dep.name as root_cause_service, i.id as incident_id, i.title as title, i.root_cause as root_cause "
            "LIMIT 1"
        )
        with self.driver.session() as session:
            result = session.run(cypher, target=target_service)
            record = result.single()
            if record:
                return dict(record)
            
        return {
            "root_cause_service": target_service,
            "incident_id": None,
            "title": "Self root cause",
            "root_cause": f"No downstream incident found in Neo4j graph. Root cause isolated to {target_service}."
        }

    def get_neighbor_recommendations(self, target_service: str, incident_type: str) -> list:
        """
        Recommendation Neighbors Cypher query.
        """
        cypher = (
            "MATCH (s:Service {name: $target})-[:DEPENDS_ON]-(neighbor:Service)<-[:OCCURRED_ON]-(i:Incident)-[:RESOLVED_BY]->(pb:Playbook) "
            "RETURN pb.name as playbook, neighbor.name as neighbor, pb.success_rate as success_rate"
        )
        with self.driver.session() as session:
            result = session.run(cypher, target=target_service)
            recs = []
            for record in result:
                recs.append({
                    "playbook": record["playbook"],
                    "neighbor": record["neighbor"],
                    "incident_type": incident_type,
                    "success_rate": record.get("success_rate", 0.9)
                })
            return recs

    def get_graph_data(self) -> dict:
        nodes = []
        edges = []
        with self.driver.session() as session:
            # Query all nodes
            res_nodes = session.run("MATCH (n) RETURN n")
            for r in res_nodes:
                node = r["n"]
                label = list(node.labels)[0] if node.labels else "Unknown"
                identifier = node.get("name") if label.lower() == "service" else node.get("id")
                nodes.append({
                    "data": {
                        "id": identifier,
                        "label": node.get("name", node.get("id")),
                        "type": label,
                        "status": node.get("status", "healthy")
                    }
                })
            
            # Query all edges
            res_edges = session.run("MATCH (a)-[r]->(b) RETURN a, r, b")
            for r in res_edges:
                edge = r["r"]
                a = r["a"]
                b = r["b"]
                a_label = list(a.labels)[0] if a.labels else "Unknown"
                b_label = list(b.labels)[0] if b.labels else "Unknown"
                a_id = a.get("name") if a_label.lower() == "service" else a.get("id")
                b_id = b.get("name") if b_label.lower() == "service" else b.get("id")
                
                edges.append({
                    "data": {
                        "source": a_id,
                        "target": b_id,
                        "label": edge.type
                    }
                })
        return {"nodes": nodes, "edges": edges}

    def archive_old_nodes(self, days: int):
        cutoff_time = time.time() - (days * 86400)
        cypher = (
            "MATCH (n) "
            "WHERE (n:Incident OR n:Recommendation OR n:Approval) AND n.created_at < $cutoff "
            "DETACH DELETE n"
        )
        with self.driver.session() as session:
            session.run(cypher, cutoff=cutoff_time)
        log.info("graph_client.neo4j_nodes_archived", days=days)

    def run_raw_query(self, query: str, parameters: dict = None) -> list:
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(r) for r in result]

    def clear_all(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        log.info("graph_client.neo4j_cleared")
