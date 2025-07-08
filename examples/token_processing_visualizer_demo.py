#!/usr/bin/env python3
"""
Token Processing Visualizer Demo

This script demonstrates the token processing visualizer, which provides
detailed visualization of token-level processing during LLM operations.
This helps to make the internal LLM reasoning process more transparent.
"""

import os
import time
import random
import numpy as np
import argparse
import webbrowser
from triangulum_lx.monitoring.token_processing_visualizer import TokenProcessingVisualizer

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run Token Processing Visualizer Demo')
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./token_visualization_demo',
        help='Directory for visualization outputs'
    )
    
    parser.add_argument(
        '--auto-open',
        action='store_true',
        help='Automatically open visualizations in browser'
    )
    
    parser.add_argument(
        '--agents',
        type=int,
        default=5,
        help='Number of simulated agents'
    )
    
    return parser.parse_args()

def generate_attention_matrix(size: int = 10) -> list:
    """Generate a simulated attention matrix."""
    # Create a base attention matrix
    attention = np.zeros((size, size))
    
    # Add some diagonal attention (self-attention)
    for i in range(size):
        attention[i, i] = 0.5 + random.random() * 0.5
    
    # Add some attention to previous tokens (realistic for language models)
    for i in range(1, size):
        for j in range(i):
            attention[i, j] = random.random() * 0.7
    
    # Add some random attention spikes
    for _ in range(size // 2):
        i = random.randint(0, size - 1)
        j = random.randint(0, size - 1)
        attention[i, j] = 0.7 + random.random() * 0.3
    
    # Normalize rows
    for i in range(size):
        row_sum = attention[i, :].sum()
        if row_sum > 0:
            attention[i, :] = attention[i, :] / row_sum
    
    return attention.tolist()

def run_demo(output_dir: str, auto_open: bool = False, num_agents: int = 2):
    """
    Run the token processing visualizer demo.
    
    Args:
        output_dir: Directory for visualization outputs
        auto_open: Whether to automatically open visualizations in browser
        num_agents: Number of simulated agents
    """
    # Create the visualizer
    visualizer = TokenProcessingVisualizer(
        output_dir=output_dir,
        update_interval=0.2,  # Update visualizations more frequently for the demo
        max_tokens_per_chart=30,
        save_raw_data=True
    )
    
    # Create agent sessions
    agent_sessions = []
    for i in range(num_agents):
        agent_id = f"agent_{i+1}"
        description = f"Simulated processing by {agent_id}"
        session_id = visualizer.start_processing_session(agent_id, description)
        agent_sessions.append((agent_id, session_id))
        print(f"Started session {session_id} for {agent_id}")
    
    # Simulate token generation for each agent
    try:
        # Create some sample text for agents to process
        text_samples = [
            "The Triangulum system is designed to provide transparent LLM processing.",
            "By visualizing token-level confidence and attention patterns, we gain insights into the model's reasoning.",
            "This transparency helps users understand why the model makes certain decisions.",
            "Real-time feedback mechanisms allow for interactive adjustments during processing."
        ]
        
        print("\nGenerating tokens with varying confidence and processing times...")
        
        # For each sample text
        for text_idx, text in enumerate(text_samples):
            tokens = text.split()
            
            # Select a random agent to process this text
            agent_idx = text_idx % len(agent_sessions)
            agent_id, session_id = agent_sessions[agent_idx]
            
            print(f"\nAgent {agent_id} processing: '{text}'")
            
            # Generate tokens with varying confidence
            for i, token in enumerate(tokens):
                # Simulate different confidence patterns
                if text_idx == 0:
                    # First text: High confidence that gradually decreases
                    confidence = 95.0 - (i / len(tokens)) * 30.0
                elif text_idx == 1:
                    # Second text: Starting low and increasing confidence
                    confidence = 50.0 + (i / len(tokens)) * 45.0
                elif text_idx == 2:
                    # Third text: Fluctuating confidence
                    confidence = 70.0 + 25.0 * np.sin(i * np.pi / 4)
                else:
                    # Fourth text: Random confidence with a trend
                    confidence = 60.0 + (i / len(tokens)) * 30.0 + random.random() * 10.0 - 5.0
                
                # Ensure confidence is within bounds
                confidence = max(30.0, min(99.0, confidence))
                
                # Simulate processing time (harder tokens take longer)
                base_time = 50.0  # Base processing time in ms
                length_factor = len(token) * 2.0  # Longer tokens take more time
                complexity_factor = 10.0 if any(c in token for c in ".,!?;:") else 0.0  # Punctuation adds complexity
                randomness = random.random() * 20.0  # Random variation
                
                processing_time = base_time + length_factor + complexity_factor + randomness
                
                # Add the token
                visualizer.add_token(
                    session_id=session_id,
                    token=token,
                    confidence=confidence,
                    processing_time_ms=processing_time,
                    metadata={"position": i, "text_idx": text_idx}
                )
                
                # Simulate processing time
                time.sleep(0.1)
                
                # Occasionally add attention patterns
                if i > 0 and i % 8 == 0:
                    # Create attention matrix for tokens processed so far
                    attention_matrix = generate_attention_matrix(min(i + 1, 20))
                    
                    # Add attention pattern
                    visualizer.add_attention_pattern(
                        session_id=session_id,
                        attention_matrix=attention_matrix,
                        description=f"Attention after token {i}"
                    )
                    
                    print(f"  Added attention pattern after token {i}")
            
            # Pause between texts
            time.sleep(0.5)
        
        # End sessions
        for agent_id, session_id in agent_sessions:
            visualizer.end_processing_session(session_id)
            print(f"Ended session for {agent_id}")
        
        # Open visualizations in browser if requested
        if auto_open:
            visualization_url = f"file://{os.path.abspath(os.path.join(output_dir, 'token_processing.html'))}"
            print(f"\nOpening visualization in browser: {visualization_url}")
            webbrowser.open(visualization_url)
        
        print(f"\nToken processing visualization completed. Results saved to {output_dir}")
        print("To view visualizations, open the following file in a web browser:")
        print(f"  {os.path.abspath(os.path.join(output_dir, 'token_processing.html'))}")
    
    except KeyboardInterrupt:
        print("\nDemo interrupted. Cleaning up...")
        # End any active sessions
        for _, session_id in agent_sessions:
            visualizer.end_processing_session(session_id)

def main():
    """Run the token processing visualizer demo."""
    args = parse_arguments()
    
    print("=" * 80)
    print("TRIANGULUM TOKEN PROCESSING VISUALIZER DEMO".center(80))
    print("=" * 80)
    print("\nThis demo simulates LLM token processing and visualizes:")
    print("  - Token-level confidence scores")
    print("  - Processing time metrics")
    print("  - Attention patterns between tokens")
    print("  - Real-time updates of the processing state\n")
    
    run_demo(args.output_dir, args.auto_open, args.agents)

if __name__ == "__main__":
    main()
