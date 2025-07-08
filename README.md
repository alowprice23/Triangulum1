# Triangulum Dashboard Integration

This repository contains the integration between the Triangulum backend system and its dashboard visualization. It solves the issue where the dashboard was previously showing simulated data rather than real agent activity.

## Key Components

- **Dashboard Backend Connector**: Connects to the agent message bus and transforms messages into visualization events
- **Integrated Dashboard**: Displays real-time agent activity with fallback simulation mode
- **LLM Integration**: Demonstrates how LLM-powered agents work with the dashboard

## Usage

There are three main scripts to run the integration:

1. `python run_fixed_triangulum_dashboard.py [--simulation]` - Run just the dashboard
2. `python run_triangulum_with_live_dashboard.py` - Run both Triangulum system and dashboard
3. `python run_triangulum_llm_dashboard_integration.py` - Run LLM agents with dashboard

For more details, see [TRIANGULUM_DASHBOARD_INTEGRATION_SOLUTION.md](TRIANGULUM_DASHBOARD_INTEGRATION_SOLUTION.md)
