def test_compiled_workspace_graph_has_four_primary_nodes() -> None:
    from app.consilium.agents.graph import get_compiled_graph

    cg = get_compiled_graph()
    g = cg.get_graph()
    names = {str(n) for n in g.nodes if not str(n).startswith("__")}
    assert {"planning_merge", "monitoring_merge", "replan_merge", "notify"} <= names
