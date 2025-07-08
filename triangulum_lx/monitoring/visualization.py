"""
Visualization components for Triangulum monitoring dashboard.

This module provides visualization tools for displaying Triangulum
metrics and system state in an interactive dashboard.
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import shutil
import os

from .metrics import MetricsCollector, TickMetrics
from ..core.state import Phase


def create_dashboard(engine, metrics, output_dir="dashboard"):
    """
    Create a dashboard visualization of the Triangulum system state.
    
    Args:
        engine: The TriangulationEngine instance
        metrics: MetricsCollector instance with recorded metrics
        output_dir: Directory to save the dashboard files
        
    Returns:
        str: Path to the dashboard index.html file
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Generate the visualizations
    _generate_system_state_plot(engine, output_path / "system_state.png")
    _generate_entropy_plot(metrics, output_path / "entropy.png")
    _generate_bug_flow_plot(metrics, output_path / "bug_flow.png")
    _generate_agent_performance_plot(metrics, output_path / "agent_performance.png")
    
    # Generate the HTML dashboard
    html_path = _generate_html_dashboard(
        engine, metrics, output_path, 
        ["system_state.png", "entropy.png", "bug_flow.png", "agent_performance.png"]
    )
    
    return html_path


def _generate_system_state_plot(engine, output_path):
    """Generate visualization of the current system state."""
    # Count bugs in each phase
    phase_counts = {phase.name: 0 for phase in Phase}
    for bug in engine.bugs:
        phase_counts[bug.phase.name] += 1
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    
    # Phase colors
    colors = {
        'WAIT': 'gray',
        'REPRO': 'blue',
        'PATCH': 'orange',
        'VERIFY': 'green',
        'DONE': 'darkgreen',
        'ESCALATE': 'red'
    }
    
    # Plot bars for each phase
    phases = list(phase_counts.keys())
    values = list(phase_counts.values())
    bar_colors = [colors.get(phase, 'gray') for phase in phases]
    
    bars = plt.bar(phases, values, color=bar_colors)
    
    # Add count labels on bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(
                bar.get_x() + bar.get_width()/2.,
                height + 0.1,
                str(int(height)),
                ha='center', va='bottom',
                fontweight='bold'
            )
    
    plt.title('Current Bug Distribution by Phase')
    plt.xlabel('Phase')
    plt.ylabel('Number of Bugs')
    plt.ylim(0, max(values) + 1 if max(values) > 0 else 5)
    
    # Add free agent indicator
    plt.text(
        0.02, 0.95, 
        f"Free Agents: {engine.free_agents}",
        transform=plt.gca().transAxes,
        fontsize=12,
        bbox=dict(facecolor='lightblue', alpha=0.5)
    )
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _generate_entropy_plot(metrics, output_path):
    """Generate entropy consumption over time visualization."""
    if not metrics.tick_metrics:
        # No data, create empty plot
        plt.figure(figsize=(10, 6))
        plt.title('Entropy Consumption (No Data)')
        plt.xlabel('Tick')
        plt.ylabel('Entropy (bits)')
        plt.grid(True)
        plt.savefig(output_path, dpi=150)
        plt.close()
        return
    
    # Extract data
    ticks = [m.tick_number for m in metrics.tick_metrics]
    entropy = [m.entropy_bits for m in metrics.tick_metrics]
    
    # Get entropy threshold if available
    threshold = None
    for m in metrics.tick_metrics:
        if hasattr(m, 'entropy_threshold'):
            threshold = m.entropy_threshold
            break
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    
    plt.plot(ticks, entropy, 'b-', marker='o', label='Consumed Entropy')
    
    # Add threshold line if available
    if threshold is not None:
        plt.axhline(y=threshold, color='r', linestyle='--', 
                   label=f'Threshold ({threshold:.2f} bits)')
    
    plt.title('Entropy Consumption Over Time')
    plt.xlabel('Tick')
    plt.ylabel('Entropy (bits)')
    plt.grid(True)
    plt.legend()
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _generate_bug_flow_plot(metrics, output_path):
    """Generate visualization of bug flow through phases over time."""
    if not metrics.tick_metrics:
        # No data, create empty plot
        plt.figure(figsize=(10, 6))
        plt.title('Bug Flow Through Phases (No Data)')
        plt.xlabel('Tick')
        plt.ylabel('Number of Bugs')
        plt.grid(True)
        plt.savefig(output_path, dpi=150)
        plt.close()
        return
    
    # Extract data
    ticks = [m.tick_number for m in metrics.tick_metrics]
    waiting = [m.bugs_waiting for m in metrics.tick_metrics]
    repro = [m.bugs_in_repro for m in metrics.tick_metrics]
    patch = [m.bugs_in_patch for m in metrics.tick_metrics]
    verify = [m.bugs_in_verify for m in metrics.tick_metrics]
    done = [m.bugs_done for m in metrics.tick_metrics]
    escalated = [m.bugs_escalated for m in metrics.tick_metrics]
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    
    plt.stackplot(
        ticks,
        waiting, repro, patch, verify, done, escalated,
        labels=['WAIT', 'REPRO', 'PATCH', 'VERIFY', 'DONE', 'ESCALATE'],
        colors=['gray', 'blue', 'orange', 'green', 'darkgreen', 'red'],
        alpha=0.8
    )
    
    plt.title('Bug Flow Through Phases')
    plt.xlabel('Tick')
    plt.ylabel('Number of Bugs')
    plt.grid(True)
    plt.legend(loc='upper left')
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _generate_agent_performance_plot(metrics, output_path):
    """Generate visualization of agent performance."""
    # If no agent metrics, create empty plot
    if not metrics.agent_metrics:
        plt.figure(figsize=(10, 6))
        plt.title('Agent Performance (No Data)')
        plt.xlabel('Agent')
        plt.ylabel('Metrics')
        plt.grid(True)
        plt.savefig(output_path, dpi=150)
        plt.close()
        return
    
    # Extract data
    agents = list(metrics.agent_metrics.keys())
    
    # Get the most recent metrics for each agent
    success_rates = []
    total_tokens = []
    processing_times = []
    
    for agent_id in agents:
        agent_metrics = metrics.agent_metrics[agent_id]
        if agent_metrics:
            latest_metric = agent_metrics[-1]
            success_rates.append(latest_metric.success_rate)
            
            # Sum tokens across all activities
            tokens_in = sum(m.tokens_in for m in agent_metrics)
            tokens_out = sum(m.tokens_out for m in agent_metrics)
            total_tokens.append(tokens_in + tokens_out)
            
            # Average processing time
            avg_time = sum(m.processing_time for m in agent_metrics) / len(agent_metrics)
            processing_times.append(avg_time)
        else:
            success_rates.append(0)
            total_tokens.append(0)
            processing_times.append(0)
    
    # Create figure with subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # Success rates
    ax1.bar(agents, success_rates, color='green')
    ax1.set_ylabel('Success Rate')
    ax1.set_title('Agent Performance Metrics')
    ax1.set_ylim(0, 1)
    
    # Token usage
    ax2.bar(agents, total_tokens, color='blue')
    ax2.set_ylabel('Total Tokens Used')
    
    # Processing time
    ax3.bar(agents, processing_times, color='orange')
    ax3.set_xlabel('Agent')
    ax3.set_ylabel('Avg Processing Time (s)')
    
    # Adjust layout
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def _generate_html_dashboard(engine, metrics, output_dir, image_paths):
    """Generate HTML dashboard that displays all visualizations."""
    html_path = output_dir / "index.html"
    
    # Get current time for dashboard title
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Summary statistics
    free_agents = engine.free_agents
    total_bugs = len(engine.bugs)
    bugs_done = sum(1 for bug in engine.bugs if bug.phase.name == "DONE")
    bugs_escalated = sum(1 for bug in engine.bugs if bug.phase.name == "ESCALATE")
    success_rate = bugs_done / total_bugs if total_bugs > 0 else 0
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Triangulum Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1, h2 {{
                color: #333;
            }}
            .header {{
                background-color: #4a6fa5;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .stats-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin-bottom: 20px;
            }}
            .stat-box {{
                flex: 1;
                min-width: 200px;
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .viz-container {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            .viz-box {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .viz-box img {{
                width: 100%;
                height: auto;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                color: #666;
                font-size: 0.8em;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Triangulum LX Dashboard</h1>
            <p>Generated: {now}</p>
        </div>
        
        <div class="stats-container">
            <div class="stat-box">
                <h3>System State</h3>
                <p>Free Agents: {free_agents}</p>
                <p>Tick: {engine.tick_no}</p>
                <p>Entropy: {getattr(engine.monitor, 'g_bits', 0):.2f} bits</p>
            </div>
            <div class="stat-box">
                <h3>Bug Statistics</h3>
                <p>Total Bugs: {total_bugs}</p>
                <p>Resolved: {bugs_done}</p>
                <p>Escalated: {bugs_escalated}</p>
                <p>Success Rate: {success_rate:.2f}</p>
            </div>
        </div>
        
        <div class="viz-container">
    """
    
    # Add each visualization image
    for img_path in image_paths:
        title = img_path.replace(".png", "").replace("_", " ").title()
        html_content += f"""
            <div class="viz-box">
                <h2>{title}</h2>
                <img src="{img_path}" alt="{title}" />
            </div>
        """
    
    # Close the HTML
    html_content += """
        </div>
        
        <div class="footer">
            <p>Triangulum LX - Agentic Debugging System</p>
        </div>
    </body>
    </html>
    """
    
    # Write HTML to file
    with open(html_path, "w") as f:
        f.write(html_content)
    
    return str(html_path)
