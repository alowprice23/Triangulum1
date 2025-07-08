"""
Thought Chain Demonstration

This script demonstrates the Thought-Chaining Mechanism, showing how agents
can collaboratively build structured reasoning chains to solve problems.
"""

import logging
import time
import uuid
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path for importing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from triangulum_lx.agents.chain_node import ChainNode, ThoughtType, RelationshipType
from triangulum_lx.agents.thought_chain import ThoughtChain, TraversalOrder


def build_reasoning_chain() -> ThoughtChain:
    """
    Build a sample reasoning chain for a bug diagnosis scenario.
    
    This demonstrates how different agents can contribute to a collaborative
    reasoning process, building on each other's thoughts.
    
    Returns:
        ThoughtChain: A sample reasoning chain
    """
    # Create a new thought chain
    chain = ThoughtChain(
        name="Bug Diagnosis Chain",
        description="A reasoning chain for diagnosing a bug in the login system",
        metadata={"domain": "software_engineering", "priority": "high"}
    )
    
    # Create the initial observation (root node)
    observation = ChainNode(
        thought_type=ThoughtType.OBSERVATION,
        content={
            "observation": "Users are unable to log in to the system",
            "system": "Authentication Service",
            "reported_by": "Customer Support",
            "timestamp": "2025-07-01T15:30:00Z"
        },
        author_agent_id="observer_agent",
        confidence=0.95
    )
    
    # Add the observation to the chain
    chain.add_node(observation)
    
    # Add a question about the observation
    question = ChainNode(
        thought_type=ThoughtType.QUESTION,
        content={
            "question": "Are there any error messages in the authentication service logs?",
            "reasoning": "Log errors often provide clues about authentication failures"
        },
        author_agent_id="investigator_agent",
        confidence=0.8
    )
    
    # Connect the question to the observation
    chain.add_node(question, parent_id=observation.node_id, relationship=RelationshipType.QUESTIONS)
    
    # Add an answer to the question
    answer = ChainNode(
        thought_type=ThoughtType.ANSWER,
        content={
            "answer": "Yes, the logs show 'Database connection timeout' errors",
            "log_snippet": "ERROR [AuthService] Database connection timeout after 30s",
            "frequency": "Every login attempt"
        },
        author_agent_id="log_analyzer_agent",
        confidence=0.9
    )
    
    # Connect the answer to the question
    chain.add_node(answer, parent_id=question.node_id, relationship=RelationshipType.ANSWERS)
    
    # Add a hypothesis based on the answer
    hypothesis = ChainNode(
        thought_type=ThoughtType.HYPOTHESIS,
        content={
            "hypothesis": "The database connection pool is exhausted",
            "reasoning": "Connection timeouts often occur when all connections are in use and new ones can't be established"
        },
        author_agent_id="database_expert_agent",
        confidence=0.7
    )
    
    # Connect the hypothesis to the answer
    chain.add_node(hypothesis, parent_id=answer.node_id, relationship=RelationshipType.DERIVES_FROM)
    
    # Add evidence supporting the hypothesis
    evidence1 = ChainNode(
        thought_type=ThoughtType.EVIDENCE,
        content={
            "evidence": "Connection pool metrics show 100% utilization",
            "metric": "db_connection_pool_utilization",
            "value": "100%",
            "normal_range": "30-70%"
        },
        author_agent_id="metrics_agent",
        confidence=0.85
    )
    
    # Connect the evidence to the hypothesis
    chain.add_node(evidence1, parent_id=hypothesis.node_id, relationship=RelationshipType.SUPPORTS)
    
    # Add more evidence
    evidence2 = ChainNode(
        thought_type=ThoughtType.EVIDENCE,
        content={
            "evidence": "Recent code change increased session duration",
            "commit_id": "a1b2c3d4",
            "author": "dev.name@example.com",
            "description": "Increased session timeout from 1h to 24h"
        },
        author_agent_id="code_review_agent",
        confidence=0.8
    )
    
    # Connect the additional evidence
    chain.add_node(evidence2, parent_id=hypothesis.node_id, relationship=RelationshipType.SUPPORTS)
    
    # Add an inference based on the hypothesis and evidence
    inference = ChainNode(
        thought_type=ThoughtType.INFERENCE,
        content={
            "inference": "The increased session duration is causing connections to be held longer, exhausting the pool",
            "reasoning": "Longer sessions mean connections stay open longer, and if the pool size wasn't increased to compensate, it would explain the exhaustion"
        },
        author_agent_id="system_analyst_agent",
        confidence=0.9
    )
    
    # Connect the inference to both the hypothesis and evidence
    chain.add_node(inference, parent_id=hypothesis.node_id, relationship=RelationshipType.DERIVES_FROM)
    chain.add_relationship(source_id=evidence1.node_id, target_id=inference.node_id, relationship=RelationshipType.SUPPORTS)
    chain.add_relationship(source_id=evidence2.node_id, target_id=inference.node_id, relationship=RelationshipType.SUPPORTS)
    
    # Add a conclusion based on the inference
    conclusion = ChainNode(
        thought_type=ThoughtType.CONCLUSION,
        content={
            "conclusion": "The login failures are caused by database connection pool exhaustion due to the recent session duration increase",
            "confidence": "High",
            "impact": "All users are affected"
        },
        author_agent_id="lead_investigator_agent",
        confidence=0.95
    )
    
    # Connect the conclusion to the inference
    chain.add_node(conclusion, parent_id=inference.node_id, relationship=RelationshipType.DERIVES_FROM)
    
    # Add a suggested action based on the conclusion
    action = ChainNode(
        thought_type=ThoughtType.ACTION,
        content={
            "action": "Increase the database connection pool size to accommodate the longer sessions",
            "implementation": "Update db_config.yml to increase max_connections from 100 to 300",
            "estimated_effort": "Low",
            "estimated_impact": "Immediate resolution"
        },
        author_agent_id="solution_architect_agent",
        confidence=0.9
    )
    
    # Connect the action to the conclusion
    chain.add_node(action, parent_id=conclusion.node_id, relationship=RelationshipType.DERIVES_FROM)
    
    # Add an alternative action
    alternative_action = ChainNode(
        thought_type=ThoughtType.ACTION,
        content={
            "action": "Revert the session duration change and implement it with proper connection handling",
            "implementation": "Revert commit a1b2c3d4 and create a new implementation with connection release on inactivity",
            "estimated_effort": "Medium",
            "estimated_impact": "Immediate resolution with better long-term solution"
        },
        author_agent_id="senior_developer_agent",
        confidence=0.8
    )
    
    # Connect the alternative action to the conclusion as an alternative
    chain.add_node(alternative_action, parent_id=conclusion.node_id, relationship=RelationshipType.ALTERNATIVE_TO)
    
    # Add a reflection on the reasoning process
    reflection = ChainNode(
        thought_type=ThoughtType.REFLECTION,
        content={
            "reflection": "This investigation effectively traced from symptoms to root cause, but we should improve monitoring to catch such issues earlier",
            "lessons_learned": "1. Monitor connection pool utilization, 2. Add alerts for high utilization, 3. Review session management code changes more carefully"
        },
        author_agent_id="process_improvement_agent",
        confidence=0.9
    )
    
    # Connect the reflection to the conclusion
    chain.add_node(reflection, parent_id=conclusion.node_id, relationship=RelationshipType.EXTENDS)
    
    logger.info(f"Created reasoning chain with {len(chain)} nodes")
    return chain


def demonstrate_traversal(chain: ThoughtChain):
    """
    Demonstrate different ways to traverse a thought chain.
    
    Args:
        chain: The thought chain to traverse
    """
    logger.info("\n=== DEMONSTRATING CHAIN TRAVERSAL ===")
    
    # Depth-first traversal
    logger.info("\n--- Depth-First Traversal ---")
    for i, node in enumerate(chain.traverse(order=TraversalOrder.DEPTH_FIRST)):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: {list(node.content.keys())[0]}")
    
    # Breadth-first traversal
    logger.info("\n--- Breadth-First Traversal ---")
    for i, node in enumerate(chain.traverse(order=TraversalOrder.BREADTH_FIRST)):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: {list(node.content.keys())[0]}")
    
    # Chronological traversal
    logger.info("\n--- Chronological Traversal (oldest to newest) ---")
    for i, node in enumerate(chain.traverse(order=TraversalOrder.CHRONOLOGICAL)):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: {list(node.content.keys())[0]}")
    
    # Reverse chronological traversal
    logger.info("\n--- Reverse Chronological Traversal (newest to oldest) ---")
    for i, node in enumerate(chain.traverse(order=TraversalOrder.REVERSE_CHRONOLOGICAL)):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: {list(node.content.keys())[0]}")
    
    # Confidence-based traversal
    logger.info("\n--- Confidence-Based Traversal (highest confidence first) ---")
    for i, node in enumerate(chain.traverse(order=TraversalOrder.CONFIDENCE)):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: {list(node.content.keys())[0]} (confidence: {node.confidence})")


def demonstrate_searching(chain: ThoughtChain):
    """
    Demonstrate how to search for nodes and paths in a thought chain.
    
    Args:
        chain: The thought chain to search
    """
    logger.info("\n=== DEMONSTRATING SEARCH CAPABILITIES ===")
    
    # Find nodes by thought type
    logger.info("\n--- Finding Nodes by Thought Type ---")
    evidence_nodes = chain.find_nodes(thought_type=ThoughtType.EVIDENCE)
    logger.info(f"Found {len(evidence_nodes)} evidence nodes:")
    for i, node in enumerate(evidence_nodes):
        logger.info(f"{i+1}. {node.content.get('evidence', '')}")
    
    # Find nodes by author
    logger.info("\n--- Finding Nodes by Author ---")
    analyst_nodes = chain.find_nodes(author_agent_id="system_analyst_agent")
    logger.info(f"Found {len(analyst_nodes)} nodes by system analyst:")
    for i, node in enumerate(analyst_nodes):
        logger.info(f"{i+1}. [{node.thought_type.value}] {list(node.content.values())[0][:50]}...")
    
    # Find nodes by confidence level
    logger.info("\n--- Finding Nodes by Confidence Level ---")
    high_confidence_nodes = chain.find_nodes(min_confidence=0.9)
    logger.info(f"Found {len(high_confidence_nodes)} nodes with confidence >= 0.9:")
    for i, node in enumerate(high_confidence_nodes):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}: confidence={node.confidence}")
    
    # Find nodes by keyword
    logger.info("\n--- Finding Nodes by Keyword ---")
    database_nodes = chain.find_nodes(keyword="database")
    logger.info(f"Found {len(database_nodes)} nodes containing 'database':")
    for i, node in enumerate(database_nodes):
        logger.info(f"{i+1}. [{node.thought_type.value}] {node.author_agent_id}")
    
    # Find paths between nodes
    logger.info("\n--- Finding Paths Between Nodes ---")
    # Find the observation and action nodes to trace a path between them
    observation_nodes = chain.find_nodes(thought_type=ThoughtType.OBSERVATION)
    action_nodes = chain.find_nodes(thought_type=ThoughtType.ACTION)
    
    if observation_nodes and action_nodes:
        observation = observation_nodes[0]
        action = action_nodes[0]
        
        paths = chain.find_paths(source_id=observation.node_id, target_id=action.node_id)
        logger.info(f"Found {len(paths)} paths from observation to action:")
        
        for i, path in enumerate(paths):
            path_str = " -> ".join([f"{node_id[:8]}" for node_id in path])
            logger.info(f"Path {i+1}: {path_str}")
            
            # Print the detailed path
            logger.info("Detailed path:")
            for j, node_id in enumerate(path):
                node = chain.get_node(node_id)
                logger.info(f"  {j+1}. [{node.thought_type.value}] {node.author_agent_id}")


def build_alternative_chain() -> ThoughtChain:
    """
    Build an alternative reasoning chain for the same problem.
    
    This demonstrates how different agents might reason about the same problem differently.
    
    Returns:
        ThoughtChain: An alternative reasoning chain
    """
    # Create a new thought chain
    chain = ThoughtChain(
        name="Alternative Bug Diagnosis",
        description="An alternative reasoning chain for the login system bug",
        metadata={"domain": "software_engineering", "perspective": "security"}
    )
    
    # Create the initial observation (root node)
    observation = ChainNode(
        thought_type=ThoughtType.OBSERVATION,
        content={
            "observation": "Users are unable to log in to the system",
            "system": "Authentication Service",
            "reported_by": "Security Team",
            "timestamp": "2025-07-01T15:35:00Z"
        },
        author_agent_id="security_observer_agent",
        confidence=0.95
    )
    
    # Add the observation to the chain
    chain.add_node(observation)
    
    # Add a hypothesis based on the observation
    hypothesis = ChainNode(
        thought_type=ThoughtType.HYPOTHESIS,
        content={
            "hypothesis": "The system might be under a denial of service attack",
            "reasoning": "Sudden authentication failures affecting all users can indicate a DoS attack"
        },
        author_agent_id="security_analyst_agent",
        confidence=0.6
    )
    
    # Connect the hypothesis to the observation
    chain.add_node(hypothesis, parent_id=observation.node_id, relationship=RelationshipType.DERIVES_FROM)
    
    # Add evidence contradicting the hypothesis
    evidence = ChainNode(
        thought_type=ThoughtType.EVIDENCE,
        content={
            "evidence": "Network traffic patterns are normal",
            "metric": "requests_per_second",
            "value": "within normal range",
            "analysis": "No indication of unusually high traffic volumes"
        },
        author_agent_id="network_monitor_agent",
        confidence=0.9
    )
    
    # Connect the evidence to the hypothesis
    chain.add_node(evidence, parent_id=hypothesis.node_id, relationship=RelationshipType.CONTRADICTS)
    
    # Add a new hypothesis based on the evidence
    new_hypothesis = ChainNode(
        thought_type=ThoughtType.HYPOTHESIS,
        content={
            "hypothesis": "The issue is likely internal rather than an attack",
            "reasoning": "Normal traffic patterns suggest an internal system failure"
        },
        author_agent_id="security_analyst_agent",
        confidence=0.8
    )
    
    # Connect the new hypothesis to the evidence
    chain.add_node(new_hypothesis, parent_id=evidence.node_id, relationship=RelationshipType.DERIVES_FROM)
    
    logger.info(f"Created alternative chain with {len(chain)} nodes")
    return chain


def demonstrate_chain_merging(main_chain: ThoughtChain, alternative_chain: ThoughtChain):
    """
    Demonstrate merging two thought chains.
    
    Args:
        main_chain: The main reasoning chain
        alternative_chain: An alternative reasoning chain to merge
    """
    logger.info("\n=== DEMONSTRATING CHAIN MERGING ===")
    
    # Count nodes before merging
    main_count_before = len(main_chain)
    alt_count = len(alternative_chain)
    
    logger.info(f"Main chain has {main_count_before} nodes before merging")
    logger.info(f"Alternative chain has {alt_count} nodes")
    
    # Find an appropriate node in the main chain to connect to
    # For this demo, we'll find the initial observation
    observation_nodes = main_chain.find_nodes(thought_type=ThoughtType.OBSERVATION)
    
    if observation_nodes:
        main_observation = observation_nodes[0]
        
        # Get the root node from the alternative chain
        alt_roots = [alternative_chain.get_node(node_id) for node_id in alternative_chain._root_node_ids]
        
        if alt_roots:
            alt_observation = alt_roots[0]
            
            # Create a context node to link the chains
            context_node = ChainNode(
                thought_type=ThoughtType.CONTEXT,
                content={
                    "context": "Incorporating security team's perspective",
                    "rationale": "Considering alternative explanations for the login issues"
                },
                author_agent_id="integration_agent",
                confidence=0.9
            )
            
            # Add the context node to the main chain, connected to the observation
            main_chain.add_node(context_node, parent_id=main_observation.node_id, relationship=RelationshipType.EXTENDS)
            
            # Merge the alternative chain into the main chain, connecting to the context node
            main_chain.merge(alternative_chain, connect_roots=True, root_relationship=RelationshipType.DERIVES_FROM)
            
            # Count nodes after merging
            main_count_after = len(main_chain)
            
            logger.info(f"Main chain has {main_count_after} nodes after merging")
            logger.info(f"Added {main_count_after - main_count_before} nodes from the alternative chain")
            
            # Validate the merged chain
            is_valid, errors = main_chain.validate()
            if is_valid:
                logger.info("Merged chain is valid")
            else:
                logger.warning(f"Merged chain has validation errors: {errors}")


def demonstrate_chain_validation(chain: ThoughtChain):
    """
    Demonstrate chain validation capabilities.
    
    Args:
        chain: The thought chain to validate
    """
    logger.info("\n=== DEMONSTRATING CHAIN VALIDATION ===")
    
    # Validate the chain
    is_valid, errors = chain.validate()
    
    if is_valid:
        logger.info("Chain is valid")
    else:
        logger.warning(f"Chain has validation errors: {errors}")
    
    # Intentionally break the chain to demonstrate validation
    # We'll create a relationship that points to a non-existent node
    broken_chain = ThoughtChain.from_dict(chain.to_dict())  # Create a copy
    
    # Get a node from the chain
    nodes = list(broken_chain._nodes.values())
    if nodes:
        test_node = nodes[0]
        # Add a relationship to a non-existent node
        test_node.parent_ids.add("nonexistent_node_id")
        test_node.relationships["nonexistent_node_id"] = RelationshipType.DERIVES_FROM
        
        # Validate the broken chain
        is_valid, errors = broken_chain.validate()
        
        if is_valid:
            logger.info("Broken chain incorrectly validated as valid")
        else:
            logger.info(f"Broken chain correctly identified as invalid with errors: {errors}")


def demonstrate_serialization(chain: ThoughtChain):
    """
    Demonstrate serialization and deserialization of thought chains.
    
    Args:
        chain: The thought chain to serialize
    """
    logger.info("\n=== DEMONSTRATING SERIALIZATION ===")
    
    # Serialize the chain to JSON
    json_str = chain.to_json()
    
    # Get size of the serialized chain
    json_size = len(json_str)
    logger.info(f"Serialized chain to JSON ({json_size} bytes)")
    
    # Deserialize back to a chain
    deserialized_chain = ThoughtChain.from_json(json_str)
    
    # Verify the deserialization
    logger.info(f"Deserialized chain has {len(deserialized_chain)} nodes")
    
    # Check if the deserialized chain is valid
    is_valid, errors = deserialized_chain.validate()
    if is_valid:
        logger.info("Deserialized chain is valid")
    else:
        logger.warning(f"Deserialized chain has validation errors: {errors}")
    
    # Verify that the serialization-deserialization preserves all data
    original_dict = chain.to_dict()
    deserialized_dict = deserialized_chain.to_dict()
    
    # Check that the keys match
    original_keys = set(original_dict.keys())
    deserialized_keys = set(deserialized_dict.keys())
    
    if original_keys == deserialized_keys:
        logger.info("All top-level keys preserved in serialization")
    else:
        missing_keys = original_keys - deserialized_keys
        extra_keys = deserialized_keys - original_keys
        
        if missing_keys:
            logger.warning(f"Missing keys in deserialized chain: {missing_keys}")
        
        if extra_keys:
            logger.warning(f"Extra keys in deserialized chain: {extra_keys}")
    
    # Check that the node count matches
    if len(chain) == len(deserialized_chain):
        logger.info("Node count preserved in serialization")
    else:
        logger.warning(f"Node count mismatch: original={len(chain)}, deserialized={len(deserialized_chain)}")


def main():
    """Main function to run the demo."""
    logger.info("Starting Thought Chain Demonstration")
    
    # Build a sample reasoning chain
    chain = build_reasoning_chain()
    
    # Demonstrate different ways to traverse the chain
    demonstrate_traversal(chain)
    
    # Demonstrate search capabilities
    demonstrate_searching(chain)
    
    # Build an alternative chain
    alternative_chain = build_alternative_chain()
    
    # Demonstrate merging chains
    demonstrate_chain_merging(chain, alternative_chain)
    
    # Demonstrate chain validation
    demonstrate_chain_validation(chain)
    
    # Demonstrate serialization
    demonstrate_serialization(chain)
    
    logger.info("\nThought Chain Demonstration completed")


if __name__ == "__main__":
    main()
