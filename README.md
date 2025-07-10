# Triangulum Lx: Autonomous Self-Healing Software System

Triangulum Lx is an advanced autonomous system designed for debugging and repairing software with mathematical guarantees of success within a deterministic time frame. It leverages a unique three-agent (Observer, Analyst, Verifier) architecture and formal methods to achieve robust and efficient software maintenance.

## Overview

The Triangulum Lx system is built upon core principles of determinism, resource conservation, and information theory to provide a reliable solution for automated software repair. Its key features include:

- **Deterministic Operation**: Predictable behavior and state transitions.
- **Guaranteed Bug Resolution**: Aims to resolve bugs within a fixed operational cycle (60 ticks).
- **Agent-Based Architecture**: Utilizes specialized agents for observing, analyzing, and verifying software issues.
- **Self-Healing Capabilities**: Designed to recover from internal failures and maintain operational integrity.
- **Formal Verification**: Core components are specified and verified using TLA+.
- **Integrated Monitoring**: Comes with a dashboard for real-time visualization of system state and agent activity.

For a detailed understanding of the system's mathematical foundations and architecture, please refer to the [Triangulum System Files Guide](docs/TriangulumSystemFilesGuide.md).

## Getting Started

### Prerequisites

- Python 3.9+
- Docker & Docker Compose (for running services like the dashboard, Prometheus, Grafana)
- Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd triangulum-lx
    ```

2.  **Set up a Python virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up necessary API keys (if using LLM agents):**
    Set the `OPENAI_API_KEY` environment variable if you plan to use OpenAI models. Refer to `triangulum_lx/agents/llm_config.py` for more details.

### Running the System

The primary entry point for running the Triangulum Lx system is through its Command Line Interface (CLI).

-   **Run the engine with a default goal:**
    ```bash
    python -m triangulum_lx.scripts.cli run
    ```
    This will start the engine, which may also launch the Agentic Dashboard if configured.

-   **View available CLI options:**
    ```bash
    python -m triangulum_lx.scripts.cli --help
    ```

### Running with Docker (Recommended for full experience)

The system can be run using Docker Compose, which orchestrates the engine, dashboard, and monitoring services:

1.  **Ensure Docker Desktop is running.**
2.  **Build and start the services:**
    ```bash
    docker-compose up --build
    ```
    This will:
    - Build the Docker images for the engine and other services.
    - Start all services defined in `docker-compose.yml`.
    - The Agentic Dashboard should be accessible at `http://localhost:8080` (or the configured port if the `engine` service serves it).
    - Grafana dashboards (if configured) at `http://localhost:3000`.
    - Prometheus metrics at `http://localhost:9090`.

## Documentation

For more detailed information, please refer to the following documents:

-   **[Main System Guide](docs/TriangulumSystemFilesGuide.md)**: Comprehensive guide to system architecture, files, and mathematical foundations.
-   **[Agent Communication Protocol](docs/agent_communication_protocol.md)**: Details on how agents communicate.
-   **[Self-Healing Mechanisms](docs/self_healing.md)**: Explanation of the system's self-healing capabilities.
-   **[Agentic System Guide](docs/Triangulum_Agentic_System_Guide.md)**: Guide to the agentic components of the system.
-   **[Agentic System Testing Guide](docs/Triangulum_Agentic_Testing_Guide.md)**: How to test the agentic parts of the system.
-   **[Project Testing Plan](docs/Triangulum_Testing_Plan.md)**: Overall testing strategy for the project.

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to Triangulum Lx.

## License

This project is licensed under the [Specify License Here - e.g., MIT License].
