"""
tooling/repair.py
─────────────────
“DAG-aware” patch–orchestration module used by the Cascade-Aware Repair System.

What it does
────────────
1. **Dependency Graph Construction**  
   • Builds a directed graph G = (V,E) where each vertex is a source file and
     an edge *u → v* means  *v* `import`/`require`s *u*  (definition before use).

2. **Tarjan SCC Decomposition**  
   • Runs Tarjan’s linear-time algorithm to obtain *strongly connected
     components* (SCCs).  Each SCC becomes an **atomic repair unit** because
     any file inside the component can ripple to all others.

3. **Ripple-Score Heuristic**  
   • For every SCC `Cᵢ` compute  

        ripple(Cᵢ) = |Cᵢ|  +  Σ_{(Cᵢ→Cⱼ)}  |Cⱼ|
     
     i.e. direct size plus size of *downstream* dependents.  Sorting SCCs
     descending by that score yields a patch order that minimises cascades.

Public API
──────────
    graph = build_dep_graph(file_paths)
    sccs  = tarjan_scc(graph)                   # list[list[node]]
    order = ripple_sort(graph, sccs)            # list[list[node]] largest first
    apply_in_order(order, patch_callback)       # user-provided patcher

Implementation constraints
──────────────────────────
* **No external libraries** – pure std-lib.
* **O(V + E)** overall complexity.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from typing import Dict, List, Set, Callable

# Type aliases
Graph = Dict[str, Set[str]]
SCC = List[str]


# ──────────────────────────────────────────────────────────────────────────────
# 1.  Dependency Graph Construction
# ──────────────────────────────────────────────────────────────────────────────
def build_dep_graph(file_paths: List[str]) -> Graph:
    """
    Build a dependency graph from a list of Python source files.
    An edge u -> v means v depends on u.
    """
    graph: Graph = defaultdict(set)
    # Regex to find 'from .module import ...'
    import_re = re.compile(r"^\s*from\s+([.\w]+)\s+import\s+", re.MULTILINE)

    for path in file_paths:
        # Ensure node exists for every file
        if path not in graph:
            graph[path] = set()

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # AST-based import finding
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    # Simplistic resolver: assumes modules map to file names
                    # This would need to be much more robust for a real system
                    dep_path = f"{node.module.replace('.', '/')}.py"
                    if dep_path in file_paths:
                        graph[dep_path].add(path) # v depends on u
        except (SyntaxError, FileNotFoundError) as e:
            # Ignore files that can't be parsed; they might be data, etc.
            pass
            
    return graph


# ──────────────────────────────────────────────────────────────────────────────
# 2.  Tarjan's SCC Algorithm
# ──────────────────────────────────────────────────────────────────────────────
def tarjan_scc(graph: Graph) -> List[SCC]:
    """
    Find strongly connected components in a graph using Tarjan's algorithm.
    """
    n = len(graph)
    nodes = list(graph.keys())
    node_to_idx = {node: i for i, node in enumerate(nodes)}
    
    visited = [False] * n
    stack = []
    on_stack = [False] * n
    ids = [-1] * n
    low = [-1] * n
    at = 0
    sccs = []

    def dfs(i):
        nonlocal at
        stack.append(i)
        on_stack[i] = True
        ids[i] = low[i] = at
        at += 1

        for neighbor_node in graph[nodes[i]]:
            neighbor_idx = node_to_idx.get(neighbor_node)
            if neighbor_idx is None: continue

            if ids[neighbor_idx] == -1:
                dfs(neighbor_idx)
            if on_stack[neighbor_idx]:
                low[i] = min(low[i], low[neighbor_idx])

        if ids[i] == low[i]:
            scc = []
            while stack:
                node_idx = stack.pop()
                on_stack[node_idx] = False
                low[node_idx] = ids[i]
                scc.append(nodes[node_idx])
                if node_idx == i: break
            sccs.append(scc)

    for i in range(n):
        if ids[i] == -1:
            dfs(i)
            
    return sccs


# ──────────────────────────────────────────────────────────────────────────────
# 3.  Ripple-Score Heuristic
# ──────────────────────────────────────────────────────────────────────────────
def ripple_sort(graph: Graph, sccs: List[SCC]) -> List[SCC]:
    """
    Sort SCCs by "ripple score" to minimize downstream breaks.
    """
    scc_graph = _build_scc_graph(graph, sccs)
    
    memo = {}
    def get_downstream_size(scc_id: int) -> int:
        if scc_id in memo:
            return memo[scc_id]
        
        size = len(sccs[scc_id])
        for neighbor_id in scc_graph.get(scc_id, []):
            size += get_downstream_size(neighbor_id)
        
        memo[scc_id] = size
        return size

    scores = {i: get_downstream_size(i) for i in range(len(sccs))}
    
    sorted_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    
    return [sccs[i] for i in sorted_indices]


def _build_scc_graph(graph: Graph, sccs: List[SCC]) -> Dict[int, Set[int]]:
    """Condense the file graph into an SCC graph."""
    node_to_scc_id = {}
    for i, scc in enumerate(sccs):
        for node in scc:
            node_to_scc_id[node] = i
            
    scc_graph: Dict[int, Set[int]] = defaultdict(set)
    for u, neighbors in graph.items():
        u_id = node_to_scc_id[u]
        for v in neighbors:
            v_id = node_to_scc_id.get(v)
            if v_id is not None and u_id != v_id:
                scc_graph[u_id].add(v_id)
                
    return scc_graph


# ──────────────────────────────────────────────────────────────────────────────
# 4.  Orchestration
# ──────────────────────────────────────────────────────────────────────────────
def apply_in_order(
    sorted_sccs: List[SCC],
    patch_callback: Callable[[SCC], bool]
) -> bool:
    """
    Apply patches to SCCs in the given order.
    If any patch fails, stop and return False.
    """
    for scc in sorted_sccs:
        if not patch_callback(scc):
            print(f"Patch failed for SCC: {scc}. Aborting.")
            return False
    return True
