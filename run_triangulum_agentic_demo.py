#!/usr/bin/env python3
"""
Run Triangulum Agentic System Demo

This script runs a comprehensive demonstration of Triangulum's agentic system capabilities,
showcasing the advanced agent communication, conflict resolution, and context preservation
features that enable the system to function as a truly agentic system with multiple
coordinated LLM agents.
"""

import os
import sys
import argparse
import logging
import time
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('triangulum_agentic_demo.log')
    ]
)

logger = logging.getLogger("triangulum_agentic_demo")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run Triangulum Agentic System Demo')
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./triangulum_demo_output',
        help='Directory for demo outputs'
    )
    
    parser.add_argument(
        '--demo-type',
        type=str,
        choices=['communication', 'conflict', 'context', 'token', 'all'],
        default='all',
        help='Type of demo to run'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()

def run_communication_demo(output_dir: str, verbose: bool = False) -> None:
    """
    Run the agentic communication demo.
    
    Args:
        output_dir: Directory for demo outputs
        verbose: Whether to enable verbose output
    """
    from examples.agentic_communication_demo import AgentSimulator
    
    logger.info("Running agentic communication demo...")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Configure verbosity
    if verbose:
        logging.getLogger("agentic_communication_demo").setLevel(logging.DEBUG)
    
    # Run demo
    simulator = AgentSimulator(output_dir=output_dir)
    simulator.run_demo_scenario()
    
    logger.info(f"Agentic communication demo completed. Outputs saved to {output_dir}")

def run_conflict_resolution_demo(output_dir: str, verbose: bool = False) -> None:
    """
    Run the conflict resolution demo.
    
    Args:
        output_dir: Directory for demo outputs
        verbose: Whether to enable verbose output
    """
    from triangulum_lx.agents.conflict_resolver import (
        ConflictResolver, ResolutionStrategy, ConflictStatus
    )
    
    logger.info("Running conflict resolution demo...")
    
    # Create output directory
    conflict_dir = os.path.join(output_dir, "conflict_resolution")
    os.makedirs(conflict_dir, exist_ok=True)
    
    # Create a conflict resolver
    resolver = ConflictResolver(orchestrator_id="orchestrator_agent")
    
    # Register agent expertise
    resolver.update_agent_expertise("bug_detector_agent", {
        "code_repair": 0.9,
        "bug_detection": 0.95,
        "test_generation": 0.7,
        "dependency_analysis": 0.6
    })
    
    resolver.update_agent_expertise("verification_agent", {
        "code_repair": 0.8,
        "bug_detection": 0.7,
        "test_generation": 0.9,
        "code_quality": 0.85
    })
    
    resolver.update_agent_expertise("relationship_analyst_agent", {
        "code_repair": 0.6,
        "dependency_analysis": 0.95,
        "code_structure": 0.9,
        "impact_analysis": 0.85
    })
    
    # Create competing decisions
    competing_decisions = [
        {
            "agent_id": "bug_detector_agent",
            "decision": {"fix_type": "add_null_check", "priority": "high"},
            "confidence": 0.85
        },
        {
            "agent_id": "verification_agent",
            "decision": {"fix_type": "add_type_check", "priority": "medium"},
            "confidence": 0.75
        },
        {
            "agent_id": "relationship_analyst_agent",
            "decision": {"fix_type": "refactor_login_flow", "priority": "medium"},
            "confidence": 0.65
        }
    ]
    
    # Register a conflict
    conflict_id = resolver.register_conflict(
        domain="code_repair",
        competing_decisions=competing_decisions,
        affected_agents=["bug_detector_agent", "verification_agent", "relationship_analyst_agent"],
        context={"file": "login.py", "line": 42, "function": "process_data"}
    )
    
    logger.info(f"Registered conflict {conflict_id} with {len(competing_decisions)} competing decisions")
    
    # Resolve the conflict using different strategies
    strategies = [
        ResolutionStrategy.CONSENSUS,
        ResolutionStrategy.CONFIDENCE,
        ResolutionStrategy.EXPERTISE,
        ResolutionStrategy.WEIGHTED_VOTE,
        ResolutionStrategy.HIERARCHICAL,
        ResolutionStrategy.HYBRID
    ]
    
    results = {}
    
    for strategy in strategies:
        logger.info(f"Resolving conflict using {strategy.name} strategy...")
        try:
            resolution = resolver.resolve_conflict(conflict_id, force_strategy=strategy)
            
            # Check if resolution was successful
            if resolution.get("status") == ConflictStatus.ESCALATED:
                results[strategy.name] = {
                    "status": "ESCALATED",
                    "reason": resolution.get("explanation", "Confidence below threshold"),
                    "confidence": resolution.get("confidence", 0.0)
                }
                logger.info(f"Strategy {strategy.name}: Escalated with reason: {resolution.get('explanation', 'Unknown')}")
            else:
                # Get result using either key name that might be present
                result_value = resolution.get("resolution_result", resolution.get("result", "Unknown"))
                
                results[strategy.name] = {
                    "status": "RESOLVED",
                    "result": result_value,
                    "confidence": resolution.get("confidence", 0.0),
                    "explanation": resolution.get("explanation", "No explanation provided")
                }
                
                logger.info(f"Strategy {strategy.name}: Selected {result_value} with confidence {resolution.get('confidence', 0.0):.2f}")
        
        except Exception as e:
            logger.error(f"Error in strategy {strategy.name}: {str(e)}")
            results[strategy.name] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    # Save results
    import json
    with open(os.path.join(conflict_dir, "conflict_resolution_results.json"), 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Conflict resolution demo completed. Results saved to {conflict_dir}")

def run_context_preservation_demo(output_dir: str, verbose: bool = False) -> None:
    """
    Run the context preservation demo.
    
    Args:
        output_dir: Directory for demo outputs
        verbose: Whether to enable verbose output
    """
    from triangulum_lx.agents.context_preserver import ContextPreserver, ContextRelevance
    
    logger.info("Running context preservation demo...")
    
    # Create output directory
    context_dir = os.path.join(output_dir, "context_preservation")
    os.makedirs(context_dir, exist_ok=True)
    
    # Create a context preserver
    preserver = ContextPreserver(
        max_context_size=10000,
        enable_semantic_chunking=True,
        enable_context_summarization=True
    )
    
    # Create a conversation context
    conversation_id = preserver.create_conversation_context(
        initiating_agent="orchestrator_agent",
        participating_agents=["bug_detector_agent", "verification_agent", "relationship_analyst_agent"],
        domain="code_repair",
        initial_context={
            "project": "example_project",
            "task": "Fix null pointer exception in login.py",
            "priority": "high"
        }
    )
    
    logger.info(f"Created conversation context {conversation_id}")
    
    # Add context elements representing a conversation between agents
    
    # Orchestrator agent assigns task to bug detector
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="orchestrator_agent",
        element_type="message",
        element_key="task_assignment",
        element_value="Analyze login.py for null pointer issues",
        relevance=ContextRelevance.HIGH
    )
    
    # Bug detector reports findings
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="bug_detector_agent",
        element_type="analysis_result",
        element_key="bug_detection",
        element_value={
            "file": "login.py",
            "line": 42,
            "issue": "Null pointer when user object is None",
            "severity": "high"
        },
        relevance=ContextRelevance.CRITICAL
    )
    
    # Orchestrator requests verification
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="orchestrator_agent",
        element_type="message",
        element_key="verification_request",
        element_value="Verify bug in login.py:42",
        relevance=ContextRelevance.MEDIUM
    )
    
    # Verification agent confirms bug
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="verification_agent",
        element_type="verification_result",
        element_key="bug_verification",
        element_value={
            "verified": True,
            "reproduction_steps": ["Login with null user ID", "Check error log"],
            "recommended_fix": "Add null check before accessing user properties"
        },
        relevance=ContextRelevance.HIGH
    )
    
    # Add low relevance elements to test pruning
    for i in range(10):
        preserver.add_context_element(
            conversation_id=conversation_id,
            source_agent="bug_detector_agent",
            element_type="debug_info",
            element_key=f"debug_{i}",
            element_value=f"Debug information {i}: This is less important context",
            relevance=ContextRelevance.LOW
        )
    
    # Orchestrator requests dependency analysis
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="orchestrator_agent",
        element_type="message",
        element_key="dependency_request",
        element_value="Analyze dependencies for login.py",
        relevance=ContextRelevance.MEDIUM
    )
    
    # Relationship analyst provides dependency information
    preserver.add_context_element(
        conversation_id=conversation_id,
        source_agent="relationship_analyst_agent",
        element_type="dependency_analysis",
        element_key="code_relationships",
        element_value={
            "dependencies": ["user.py", "session.py", "auth.py"],
            "impact": "Medium - affects login flow only",
            "affected_functions": ["validate_user", "create_session"]
        },
        relevance=ContextRelevance.HIGH
    )
    
    # Get context for each agent
    agents = ["orchestrator_agent", "bug_detector_agent", "verification_agent", "relationship_analyst_agent"]
    agent_contexts = {}
    
    for agent_id in agents:
        # Get context with different relevance levels
        context = preserver.get_conversation_context(
            conversation_id=conversation_id,
            agent_id=agent_id,
            min_relevance=ContextRelevance.MEDIUM,  # Only medium and higher relevance
            max_elements=20
        )
        
        agent_contexts[agent_id] = {
            "element_count": len(context["elements"]),
            "token_count": context["token_count"],
            "summary": context.get("summary")
        }
    
    # Generate a summary
    preserver._summarize_context(conversation_id)
    summary = preserver.conversation_contexts[conversation_id]["summary"]
    
    # Create a shared context
    shared_context_id = preserver.create_shared_context(
        agent_ids=agents,
        domain="system_configuration",
        context_data={
            "max_retry_count": 3,
            "timeout_seconds": 30,
            "verification_level": "high"
        },
        relevance=ContextRelevance.HIGH
    )
    
    # Save results
    import json
    with open(os.path.join(context_dir, "context_preservation_results.json"), 'w') as f:
        json.dump({
            "conversation_id": conversation_id,
            "agent_contexts": agent_contexts,
            "summary": summary,
            "shared_context_id": shared_context_id
        }, f, indent=2)
    
    logger.info(f"Context preservation demo completed. Results saved to {context_dir}")

def run_token_visualization_demo(output_dir: str, verbose: bool = False) -> None:
    """
    Run the token processing visualization demo.
    
    Args:
        output_dir: Directory for demo outputs
        verbose: Whether to enable verbose output
    """
    from triangulum_lx.monitoring.token_processing_visualizer import TokenProcessingVisualizer
    
    logger.info("Running token processing visualization demo...")
    
    # Create output directory
    token_dir = os.path.join(output_dir, "token_visualization")
    os.makedirs(token_dir, exist_ok=True)
    
    # Create token visualizer
    visualizer = TokenProcessingVisualizer(output_dir=token_dir)
    
    # Start a processing session
    session_id = visualizer.start_processing_session(
        agent_id="bug_detector_agent",
        description="Analyzing login.py for null pointer exceptions"
    )
    
    # Simulate token generation with varying confidence
    tokens = [
        "I", "will", "analyze", "the", "login.py", "file", "for", "null", "pointer", "exceptions", ".",
        "First", "I'll", "examine", "line", "42", "where", "the", "user", "object", "is", "accessed", ".",
        "I", "notice", "that", "there", "is", "no", "null", "check", "before", "accessing", "properties", ".",
        "This", "could", "cause", "a", "null", "pointer", "exception", "if", "user", "is", "None", ".",
        "I", "recommend", "adding", "a", "null", "check", "before", "accessing", "user", "properties", "."
    ]
    
    # Add tokens with varying confidence and processing times
    for i, token in enumerate(tokens):
        # Confidence pattern: starts medium, increases for important tokens, then stabilizes high
        confidence = 65.0  # Base confidence
        
        # Increase confidence for important tokens
        if token in ["null", "pointer", "exceptions", "no", "check", "None", "recommend"]:
            confidence += 15.0
        
        # General confidence increase as reasoning progresses
        confidence += min(20.0, i / len(tokens) * 25.0)
        
        # Fluctuating processing time
        processing_time = 50 + (i % 5) * 10  # Between 50-90ms
        
        # Add token to visualizer
        visualizer.add_token(
            session_id=session_id,
            token=token,
            confidence=confidence,
            processing_time_ms=processing_time
        )
        
        # Simulate processing time
        time.sleep(0.05)
    
    # End the session
    visualizer.end_processing_session(session_id)
    
    # Start another session
    session_id = visualizer.start_processing_session(
        agent_id="verification_agent",
        description="Verifying bug in login.py:42"
    )
    
    # Simulate token generation for verification
    tokens = [
        "I", "will", "verify", "the", "bug", "in", "login.py", "at", "line", "42", ".",
        "To", "reproduce", "the", "issue", "I", "need", "to", "create", "a", "test", "case", ".",
        "I'll", "create", "a", "scenario", "where", "user", "is", "None", "and", "attempt", "to", "access", "properties", ".",
        "The", "test", "confirms", "that", "a", "null", "pointer", "exception", "is", "raised", ".",
        "I", "concur", "with", "the", "recommended", "fix", "to", "add", "a", "null", "check", "."
    ]
    
    # Add tokens with a different confidence pattern
    for i, token in enumerate(tokens):
        # Confidence pattern: starts high, dips during analysis, then increases for conclusion
        confidence = 75.0  # Higher base confidence for verification
        
        # Decrease confidence during analysis phase
        if i > 15 and i < 35:
            confidence -= 15.0
        
        # Increase confidence for conclusion
        if i >= 35:
            confidence += 10.0
        
        # Add random variation
        confidence += (i % 3) * 5.0
        
        # More consistent processing time for verification agent
        processing_time = 60 + (i % 3) * 5  # Between 60-70ms
        
        # Add token to visualizer
        visualizer.add_token(
            session_id=session_id,
            token=token,
            confidence=confidence,
            processing_time_ms=processing_time
        )
        
        # Simulate processing time
        time.sleep(0.05)
    
    # End the session
    visualizer.end_processing_session(session_id)
    
    logger.info(f"Token visualization demo completed. Results saved to {token_dir}")

def main():
    """Run the demo based on command-line arguments."""
    args = parse_arguments()
    
    # Create main output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Display welcome message
    print("\n" + "="*80)
    print("TRIANGULUM AGENTIC SYSTEM DEMONSTRATION".center(80))
    print("="*80 + "\n")
    print("This demo showcases the agentic capabilities of Triangulum, focusing on:")
    print("  - Advanced agent communication")
    print("  - Conflict resolution between competing agent decisions")
    print("  - Context preservation across long agent conversations")
    print("  - Token-level processing visibility")
    print("\nOutputs will be saved to:", args.output_dir)
    print("\n" + "="*80 + "\n")
    
    # Run selected demos
    if args.demo_type in ['communication', 'all']:
        communication_dir = os.path.join(args.output_dir, "communication_demo")
        run_communication_demo(communication_dir, args.verbose)
        print("\n✓ Communication demo completed\n")
    
    if args.demo_type in ['conflict', 'all']:
        run_conflict_resolution_demo(args.output_dir, args.verbose)
        print("\n✓ Conflict resolution demo completed\n")
    
    if args.demo_type in ['context', 'all']:
        run_context_preservation_demo(args.output_dir, args.verbose)
        print("\n✓ Context preservation demo completed\n")
    
    if args.demo_type in ['token', 'all']:
        run_token_visualization_demo(args.output_dir, args.verbose)
        print("\n✓ Token visualization demo completed\n")
    
    # Display completion message
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY".center(80))
    print("="*80 + "\n")
    print(f"All demo outputs have been saved to: {args.output_dir}")
    print("\nYou can review the demo results to understand Triangulum's agentic capabilities")
    print("and how they provide visibility into the internal operations of the system.")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
