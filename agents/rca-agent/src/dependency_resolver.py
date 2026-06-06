import networkx as nx

class DependencyResolver:
    @staticmethod
    def load_graph(topology_cfg: dict) -> nx.DiGraph:
        """Constructs a directed dependency graph from configuration.
        A directed edge (u, v) means service 'u' depends on service 'v'.
        """
        graph = nx.DiGraph()
        if not topology_cfg:
            return graph
            
        services = topology_cfg.get("services", [])
        dependencies = topology_cfg.get("dependencies", [])
        
        # Add all service nodes
        for svc in services:
            graph.add_node(svc)
            
        # Add dependency edges (u -> v: u depends on v)
        for dep in dependencies:
            if len(dep) == 2:
                u, v = dep[0], dep[1]
                graph.add_edge(u, v)
                
        return graph

    @staticmethod
    def get_downstream_dependencies(graph: nx.DiGraph, service: str) -> list[str]:
        """Returns list of services that this service depends on (reachable downstream nodes)."""
        if service not in graph:
            return []
        # In a directed graph, if A -> B -> C, then B and C are reachable downstream nodes.
        # We can use networkxdfs_preorder_traversal or descendent retrieval.
        return list(nx.descendants(graph, service))

    @staticmethod
    def get_upstream_dependencies(graph: nx.DiGraph, service: str) -> list[str]:
        """Returns list of services that depend on this service (reachable upstream nodes)."""
        if service not in graph:
            return []
        # Upstream nodes are nodes that can reach this service node.
        # We can use networkx ancestors.
        return list(nx.ancestors(graph, service))
