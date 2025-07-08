"""
Thought Chain Manager Demo - Demonstrates usage of the ThoughtChainManager.

This script shows how to use the ThoughtChainManager to create, manipulate, and query 
thought chains from multiple agents. It demonstrates the following features:
1. Creating thought chains
2. Adding thoughts from different agents
3. Building thought hierarchies
4. Searching for thoughts across chains
5. Finding related thoughts
6. Merging chains
7. Persisting and loading chains
"""

import logging
import os
import shutil
import time
from pathlib import Path

from triangulum_lx.agents.chain_node import ThoughtType, RelationshipType
from triangulum_lx.agents.thought_chain import TraversalOrder
from triangulum_lx.agents.thought_chain_manager import ThoughtChainManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def setup_storage():
    """Set up a temporary storage directory for the demo."""
    storage_dir = Path("./thought_chain_demo_storage")
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def demo_creating_chains(manager):
    """Demonstrate creating thought chains."""
    logger.info("\n=== DEMONSTRATING CHAIN CREATION ===")
    
    # Create a chain for a bug investigation
    bug_chain_id = manager.create_chain(
        name="Database Connection Bug",
        description="Investigation into database connection failures",
        metadata={"priority": "high", "issue_id": "DB-1234"},
        creator_agent_id="observer_agent"
    )
    
    # Create a chain for a feature design
    feature_chain_id = manager.create_chain(
        name="User Authentication Feature",
        description="Design and implementation of user authentication",
        metadata={"priority": "medium", "feature_id": "AUTH-456"},
        creator_agent_id="product_manager_agent"
    )
    
    # List all chains
    chains = manager.list_chains()
    logger.info(f"Created {len(chains)} chains:")
    for i, chain in enumerate(chains):
        logger.info(f"{i+1}. {chain['name']} ({chain['chain_id']})")
    
    return bug_chain_id, feature_chain_id


def demo_building_bug_investigation(manager, chain_id):
    """Demonstrate building a bug investigation thought chain."""
    logger.info("\n=== DEMONSTRATING BUG INVESTIGATION CHAIN ===")
    
    # Start with an observation
    observation_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.OBSERVATION,
        content={
            "observation": "Users are experiencing intermittent database connection failures",
            "time": "2025-07-01T10:15:00Z",
            "affected_users": 15,
            "environment": "production"
        },
        author_agent_id="observer_agent",
        confidence=0.95
    )
    
    # Add investigator's question
    question_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.QUESTION,
        content={
            "question": "What do the database logs show during these failures?"
        },
        author_agent_id="investigator_agent",
        parent_id=observation_id,
        relationship=RelationshipType.QUESTIONS,
        confidence=0.8
    )
    
    # Add log analyzer's answer
    answer_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.ANSWER,
        content={
            "answer": "Logs show 'Too many connections' errors and connection timeouts",
            "log_entries": [
                {"timestamp": "2025-07-01T10:14:30Z", "level": "ERROR", "message": "Too many connections"},
                {"timestamp": "2025-07-01T10:14:45Z", "level": "ERROR", "message": "Connection timeout"}
            ]
        },
        author_agent_id="log_analyzer_agent",
        parent_id=question_id,
        relationship=RelationshipType.ANSWERS,
        confidence=0.9
    )
    
    # Add database expert's hypothesis
    hypothesis_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.HYPOTHESIS,
        content={
            "hypothesis": "The connection pool is not releasing connections properly",
            "expected_behavior": "Connections should be released back to the pool after queries complete",
            "observed_behavior": "Connections are being held open until they timeout"
        },
        author_agent_id="database_expert_agent",
        parent_id=answer_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.7
    )
    
    # Add metrics evidence
    metrics_evidence_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.EVIDENCE,
        content={
            "evidence": "Connection pool metrics show 100% utilization",
            "metric_name": "db.connection_pool.utilization",
            "value": 100,
            "normal_range": "30-70",
            "time_period": "2025-07-01T10:00:00Z to 2025-07-01T10:30:00Z"
        },
        author_agent_id="metrics_agent",
        parent_id=hypothesis_id,
        relationship=RelationshipType.SUPPORTS,
        confidence=0.85
    )
    
    # Add code review evidence
    code_evidence_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.EVIDENCE,
        content={
            "evidence": "Recent code change increased session duration",
            "commit_id": "abc123",
            "author": "dev_user",
            "file": "src/database/connection.py",
            "change": "Session timeout increased from 30s to 300s"
        },
        author_agent_id="code_review_agent",
        parent_id=hypothesis_id,
        relationship=RelationshipType.SUPPORTS,
        confidence=0.8
    )
    
    # Add system analyst's inference
    inference_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.INFERENCE,
        content={
            "inference": "The increased session duration is causing connection pool exhaustion",
            "reasoning": "Longer sessions mean connections stay open longer, reducing availability for new requests"
        },
        author_agent_id="system_analyst_agent",
        parent_id=hypothesis_id,
        relationship=RelationshipType.SUPPORTS,
        confidence=0.9
    )
    
    # Add lead investigator's conclusion
    conclusion_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.CONCLUSION,
        content={
            "conclusion": "The database connection failures are caused by connection pool exhaustion due to increased session duration",
            "root_cause": "Code change that increased session timeout from 30s to 300s",
            "impact": "15 users affected during peak usage periods"
        },
        author_agent_id="lead_investigator_agent",
        parent_id=inference_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.95
    )
    
    # Add solution architect's action
    action1_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.ACTION,
        content={
            "action": "Revert session timeout to 30s",
            "priority": "high",
            "assignee": "dev_team",
            "estimated_time": "1 hour"
        },
        author_agent_id="solution_architect_agent",
        parent_id=conclusion_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.9
    )
    
    # Add senior developer's action
    action2_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.ACTION,
        content={
            "action": "Increase connection pool size from 50 to 100",
            "priority": "medium",
            "assignee": "ops_team",
            "estimated_time": "30 minutes"
        },
        author_agent_id="senior_developer_agent",
        parent_id=conclusion_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.8
    )
    
    # Add process improvement agent's reflection
    reflection_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.REFLECTION,
        content={
            "reflection": "We need better testing of connection pool behavior under load",
            "improvement": "Add load testing to CI/CD pipeline",
            "metric": "Connection pool utilization under simulated peak load"
        },
        author_agent_id="process_improvement_agent",
        parent_id=conclusion_id,
        relationship=RelationshipType.EXTENDS,
        confidence=0.9
    )
    
    # Get the chain
    chain = manager.get_chain(chain_id)
    logger.info(f"Built investigation chain with {len(chain)} thoughts")
    
    # Display the structure using depth-first traversal
    logger.info("\n--- Chain Structure (Depth-First) ---")
    nodes = list(chain.traverse(TraversalOrder.DEPTH_FIRST))
    for i, node in enumerate(nodes):
        parent_info = ""
        if node.parent_ids:
            parent_node = chain.get_node(next(iter(node.parent_ids)))
            if parent_node:
                rel = parent_node.get_relationship_to(node.node_id)
                parent_info = f" ← {rel.value} ← {parent_node.thought_type.value}"
        
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}{parent_info}")
    
    return {
        "observation_id": observation_id,
        "question_id": question_id,
        "answer_id": answer_id,
        "hypothesis_id": hypothesis_id,
        "metrics_evidence_id": metrics_evidence_id,
        "code_evidence_id": code_evidence_id,
        "inference_id": inference_id,
        "conclusion_id": conclusion_id,
        "action1_id": action1_id,
        "action2_id": action2_id,
        "reflection_id": reflection_id
    }


def demo_building_feature_design(manager, chain_id):
    """Demonstrate building a feature design thought chain."""
    logger.info("\n=== DEMONSTRATING FEATURE DESIGN CHAIN ===")
    
    # Start with a requirement
    requirement_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.OBSERVATION,
        content={
            "requirement": "Implement user authentication with multi-factor authentication support",
            "priority": "high",
            "requested_by": "security_team"
        },
        author_agent_id="product_manager_agent",
        confidence=0.9
    )
    
    # Add architect's design
    design_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.HYPOTHESIS,
        content={
            "design": "Use OAuth 2.0 with JWT tokens and TOTP for second factor",
            "components": [
                "Authentication server",
                "OAuth client libraries",
                "TOTP generator"
            ]
        },
        author_agent_id="architect_agent",
        parent_id=requirement_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.85
    )
    
    # Add security review
    security_review_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.EVIDENCE,
        content={
            "review": "Design meets security requirements with some recommendations",
            "recommendations": [
                "Use refresh tokens with short-lived access tokens",
                "Implement rate limiting for authentication attempts",
                "Add IP-based suspicious login detection"
            ]
        },
        author_agent_id="security_agent",
        parent_id=design_id,
        relationship=RelationshipType.SUPPORTS,
        confidence=0.9
    )
    
    # Add implementation plan
    plan_id = manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.ACTION,
        content={
            "plan": "Implementation plan for authentication feature",
            "phases": [
                {"name": "Backend OAuth implementation", "duration": "2 weeks"},
                {"name": "Frontend integration", "duration": "1 week"},
                {"name": "TOTP implementation", "duration": "1 week"},
                {"name": "Testing and security review", "duration": "1 week"}
            ]
        },
        author_agent_id="project_manager_agent",
        parent_id=design_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.8
    )
    
    # Get the chain
    chain = manager.get_chain(chain_id)
    logger.info(f"Built feature design chain with {len(chain)} thoughts")
    
    # Display the structure using depth-first traversal
    logger.info("\n--- Chain Structure (Depth-First) ---")
    nodes = list(chain.traverse(TraversalOrder.DEPTH_FIRST))
    for i, node in enumerate(nodes):
        parent_info = ""
        if node.parent_ids:
            parent_node = chain.get_node(next(iter(node.parent_ids)))
            if parent_node:
                rel = parent_node.get_relationship_to(node.node_id)
                parent_info = f" ← {rel.value} ← {parent_node.thought_type.value}"
        
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}{parent_info}")
    
    return {
        "requirement_id": requirement_id,
        "design_id": design_id,
        "security_review_id": security_review_id,
        "plan_id": plan_id
    }


def demo_searching_thoughts(manager, bug_chain_id, feature_chain_id):
    """Demonstrate searching for thoughts across chains."""
    logger.info("\n=== DEMONSTRATING SEARCH CAPABILITIES ===")
    
    # Search for "authentication" across all chains
    auth_results = manager.search_thoughts(query="authentication")
    logger.info(f"\n--- Found {len(auth_results)} thoughts related to 'authentication' ---")
    for i, (chain_id, node) in enumerate(auth_results):
        chain = manager.get_chain(chain_id)
        logger.info(f"{i+1}. In chain '{chain.name}': [{node.thought_type.value}] by {node.author_agent_id}")
    
    # Search for "connection" in the bug chain
    conn_results = manager.search_thoughts(query="connection", chain_ids=[bug_chain_id])
    logger.info(f"\n--- Found {len(conn_results)} thoughts related to 'connection' in bug chain ---")
    for i, (chain_id, node) in enumerate(conn_results):
        chain = manager.get_chain(chain_id)
        logger.info(f"{i+1}. In chain '{chain.name}': [{node.thought_type.value}] by {node.author_agent_id}")
    
    # Search for high confidence thoughts
    high_conf_results = manager.search_thoughts(query="", min_confidence=0.9)
    logger.info(f"\n--- Found {len(high_conf_results)} thoughts with confidence >= 0.9 ---")
    for i, (chain_id, node) in enumerate(high_conf_results):
        chain = manager.get_chain(chain_id)
        logger.info(f"{i+1}. In chain '{chain.name}': [{node.thought_type.value}] by {node.author_agent_id} (confidence: {node.confidence})")
    
    # Search for thoughts by a specific agent
    agent_results = manager.search_thoughts(query="", author_agent_id="security_agent")
    logger.info(f"\n--- Found {len(agent_results)} thoughts by security_agent ---")
    for i, (chain_id, node) in enumerate(agent_results):
        chain = manager.get_chain(chain_id)
        logger.info(f"{i+1}. In chain '{chain.name}': [{node.thought_type.value}]: {list(node.content.keys())[0]}")
    
    # Search for evidence thoughts
    evidence_results = manager.search_thoughts(query="", thought_type=ThoughtType.EVIDENCE)
    logger.info(f"\n--- Found {len(evidence_results)} EVIDENCE thoughts ---")
    for i, (chain_id, node) in enumerate(evidence_results):
        chain = manager.get_chain(chain_id)
        logger.info(f"{i+1}. In chain '{chain.name}': by {node.author_agent_id}: {list(node.content.values())[0][:50]}...")
    
    return {
        "auth_results": len(auth_results),
        "conn_results": len(conn_results),
        "high_conf_results": len(high_conf_results),
        "agent_results": len(agent_results),
        "evidence_results": len(evidence_results)
    }


def demo_finding_related_thoughts(manager, bug_chain_id, bug_node_ids):
    """Demonstrate finding thoughts related to a specific thought."""
    logger.info("\n=== DEMONSTRATING RELATED THOUGHTS ===")
    
    # Find thoughts related to the hypothesis (evidence, inference)
    hypothesis_related = manager.find_related_thoughts(
        chain_id=bug_chain_id, 
        node_id=bug_node_ids["hypothesis_id"],
        max_distance=1
    )
    
    logger.info(f"\n--- Found {len(hypothesis_related)} thoughts directly related to the hypothesis ---")
    for i, node in enumerate(hypothesis_related):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: {list(node.content.values())[0][:50]}...")
    
    # Find all descendants of the observation (everything in the chain)
    observation_descendants = manager.find_related_thoughts(
        chain_id=bug_chain_id,
        node_id=bug_node_ids["observation_id"],
        include_ancestors=False,
        include_descendants=True
    )
    
    logger.info(f"\n--- Found {len(observation_descendants)} descendants of the initial observation ---")
    logger.info(f"This represents all thoughts that followed from the initial observation")
    
    # Find the path from evidence to action
    chain = manager.get_chain(bug_chain_id)
    paths = chain.find_paths(
        source_id=bug_node_ids["metrics_evidence_id"],
        target_id=bug_node_ids["action1_id"]
    )
    
    logger.info(f"\n--- Found {len(paths)} paths from evidence to action ---")
    if paths:
        logger.info(f"Path: {' -> '.join([node.thought_type.value for node in paths[0]])}")
    
    return {
        "hypothesis_related": len(hypothesis_related),
        "observation_descendants": len(observation_descendants),
        "evidence_to_action_paths": len(paths)
    }


def demo_merging_chains(manager):
    """Demonstrate merging two chains."""
    logger.info("\n=== DEMONSTRATING CHAIN MERGING ===")
    
    # Create a performance investigation chain
    perf_chain_id = manager.create_chain(
        name="Performance Investigation",
        description="Investigation into system performance issues",
        creator_agent_id="performance_agent"
    )
    
    # Add thoughts to the performance chain
    perf_observation_id = manager.add_thought(
        chain_id=perf_chain_id,
        thought_type=ThoughtType.OBSERVATION,
        content={"observation": "System response times increased by 200% during peak hours"},
        author_agent_id="performance_agent",
        confidence=0.95
    )
    
    perf_hypothesis_id = manager.add_thought(
        chain_id=perf_chain_id,
        thought_type=ThoughtType.HYPOTHESIS,
        content={"hypothesis": "Database queries are causing the slowdown"},
        author_agent_id="performance_agent",
        parent_id=perf_observation_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.8
    )
    
    # Create a database optimization chain
    db_chain_id = manager.create_chain(
        name="Database Optimization",
        description="Optimizing database performance",
        creator_agent_id="database_expert_agent"
    )
    
    # Add thoughts to the database chain
    db_observation_id = manager.add_thought(
        chain_id=db_chain_id,
        thought_type=ThoughtType.OBSERVATION,
        content={"observation": "Query execution times have increased significantly"},
        author_agent_id="database_expert_agent",
        confidence=0.9
    )
    
    db_evidence_id = manager.add_thought(
        chain_id=db_chain_id,
        thought_type=ThoughtType.EVIDENCE,
        content={"evidence": "Missing indexes on frequently queried columns"},
        author_agent_id="database_expert_agent",
        parent_id=db_observation_id,
        relationship=RelationshipType.SUPPORTS,
        confidence=0.85
    )
    
    db_action_id = manager.add_thought(
        chain_id=db_chain_id,
        thought_type=ThoughtType.ACTION,
        content={"action": "Add indexes to customer_id and order_date columns"},
        author_agent_id="database_expert_agent",
        parent_id=db_evidence_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.9
    )
    
    # Log the chains before merging
    perf_chain = manager.get_chain(perf_chain_id)
    db_chain = manager.get_chain(db_chain_id)
    logger.info(f"Performance chain has {len(perf_chain)} thoughts before merging")
    logger.info(f"Database chain has {len(db_chain)} thoughts before merging")
    
    # Merge the database chain into the performance chain
    success = manager.merge_chains(
        source_chain_id=db_chain_id,
        target_chain_id=perf_chain_id,
        connect_roots=True,
        root_relationship=RelationshipType.SUPPORTS
    )
    
    # Log the merged chain
    if success:
        merged_chain = manager.get_chain(perf_chain_id)
        logger.info(f"Successfully merged chains. Merged chain now has {len(merged_chain)} thoughts")
        
        # Verify relationships
        perf_hypothesis_node = merged_chain.get_node(perf_hypothesis_id)
        db_observation_node = merged_chain.get_node(db_observation_id)
        
        if db_observation_id in perf_hypothesis_node.child_ids:
            rel = perf_hypothesis_node.get_relationship_to(db_observation_id)
            logger.info(f"Relationship established: {perf_hypothesis_node.thought_type.value} -{rel.value}-> {db_observation_node.thought_type.value}")
        
        # Validate the merged chain
        is_valid, errors = merged_chain.validate()
        if is_valid:
            logger.info("Merged chain is valid")
        else:
            logger.warning(f"Merged chain has validation errors: {errors}")
    else:
        logger.error("Failed to merge chains")
    
    return perf_chain_id


def demo_persistence(storage_dir):
    """Demonstrate persistence of thought chains."""
    logger.info("\n=== DEMONSTRATING PERSISTENCE ===")
    
    # Create a manager with storage
    storage_manager = ThoughtChainManager(storage_dir=str(storage_dir))
    
    # Create a chain
    chain_id = storage_manager.create_chain(
        name="Persistent Chain",
        description="A chain that will be saved to disk",
        creator_agent_id="persistence_agent"
    )
    
    # Add some thoughts
    root_id = storage_manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.OBSERVATION,
        content={"observation": "This chain will be saved to disk"},
        author_agent_id="persistence_agent",
        confidence=0.9
    )
    
    child_id = storage_manager.add_thought(
        chain_id=chain_id,
        thought_type=ThoughtType.ACTION,
        content={"action": "Load the chain from disk"},
        author_agent_id="persistence_agent",
        parent_id=root_id,
        relationship=RelationshipType.DERIVES_FROM,
        confidence=0.9
    )
    
    # Check that the chain file exists
    chain_file = storage_dir / f"{chain_id}.json"
    if chain_file.exists():
        logger.info(f"Chain file created: {chain_file}")
        
        # Log file size
        file_size = chain_file.stat().st_size
        logger.info(f"Chain file size: {file_size} bytes")
        
        # Create a new manager and load the chains
        new_manager = ThoughtChainManager(storage_dir=str(storage_dir))
        count = new_manager.load_chains()
        
        # Verify the chain was loaded
        if count == 1:
            logger.info("Successfully loaded 1 chain from storage")
            
            # Get the loaded chain
            loaded_chain = new_manager.get_chain(chain_id)
            
            # Verify the chain contents
            if len(loaded_chain) == 2:
                logger.info(f"Loaded chain has 2 thoughts as expected")
                
                # Verify the relationship
                root_node = loaded_chain.get_node(root_id)
                child_node = loaded_chain.get_node(child_id)
                
                if child_id in root_node.child_ids and root_id in child_node.parent_ids:
                    rel = root_node.get_relationship_to(child_id)
                    logger.info(f"Relationship preserved: {root_node.thought_type.value} -{rel.value}-> {child_node.thought_type.value}")
            else:
                logger.error(f"Loaded chain has {len(loaded_chain)} thoughts, expected 2")
        else:
            logger.error(f"Loaded {count} chains, expected 1")
    else:
        logger.error(f"Chain file not created at {chain_file}")
    
    return chain_id


def main():
    """Run the Thought Chain Manager demonstration."""
    try:
        logger.info("Starting Thought Chain Manager Demonstration")
        
        # Set up storage
        storage_dir = setup_storage()
        
        # Create an in-memory manager for most demos
        manager = ThoughtChainManager()
        
        # Demo 1: Creating chains
        bug_chain_id, feature_chain_id = demo_creating_chains(manager)
        
        # Demo 2: Building a bug investigation chain
        bug_node_ids = demo_building_bug_investigation(manager, bug_chain_id)
        
        # Demo 3: Building a feature design chain
        feature_node_ids = demo_building_feature_design(manager, feature_chain_id)
        
        # Demo 4: Searching for thoughts across chains
        search_results = demo_searching_thoughts(manager, bug_chain_id, feature_chain_id)
        
        # Demo 5: Finding related thoughts
        related_results = demo_finding_related_thoughts(manager, bug_chain_id, bug_node_ids)
        
        # Demo 6: Merging chains
        merged_chain_id = demo_merging_chains(manager)
        
        # Demo 7: Persistence
        persistent_chain_id = demo_persistence(storage_dir)
        
        logger.info("\nThought Chain Manager Demonstration completed successfully")
        
    except Exception as e:
        logger.exception(f"Error in demonstration: {e}")
    finally:
        # Clean up
        if "storage_dir" in locals():
            pass  # Uncomment to clean up: shutil.rmtree(storage_dir)


if __name__ == "__main__":
    main()
