# Agent Collaboration Protocol

This document outlines the protocol for how agents in the Triangulum platform communicate and collaborate with each other.

## 1. Message Bus

All inter-agent communication happens through the `EnhancedMessageBus`. This is a publish-subscribe system that allows agents to send and receive messages without having direct knowledge of each other.

## 2. Message Format

All messages on the bus are in JSON format. The basic message structure is as follows:

```json
{
  "message_id": "unique-message-id",
  "timestamp": "2024-07-25T12:00:00Z",
  "source_agent_id": "agent-id",
  "destination_agent_id": "agent-id",
  "message_type": "TaskAssignment",
  "payload": {
    // Message-specific data
  }
}
```

## 3. Core Message Types

### 3.1. `TaskAssignment`

- **Source:** `OrchestratorAgent`
- **Destination:** A specialized agent (e.g., `BugDetector`, `Strategy`, `Implementation`)
- **Payload:** Contains the details of the task to be performed.

### 3.2. `TaskResult`

- **Source:** A specialized agent
- **Destination:** `OrchestratorAgent`
- **Payload:** Contains the results of the completed task.

## 4. System Events

The `EnhancedMessageBus` also broadcasts system events, which can be used for monitoring and automation.

### 4.1. `AgentStarted`

- **Source:** `StartupManager`
- **Payload:** Contains the ID of the agent that has started.

### 4.2. `AgentStopped`

- **Source:** `StartupManager`
- **Payload:** Contains the ID of the agent that has stopped.

### 4.3. `DeadlockDetected`

- **Source:** `CLA`
- **Payload:** Contains the ID of the agent that is suspected of being deadlocked.

## 5. Agent Responsibilities

### 5.1. `OrchestratorAgent`

- Assigns tasks to specialized agents.
- Monitors the progress of tasks.
- Makes decisions based on the results of tasks.

### 5.2. Specialized Agents

- Consume tasks from the message bus.
- Execute the tasks.
- Post the results of the tasks back to the message bus.

### 5.3. `CLA`

- Monitors the health of the system.
- Detects deadlocks and other issues.
- Takes corrective actions, such as restarting agents or invoking the `triage` domain.

### 5.4. `StartupManager`

- Ensures that the system is properly configured and initialized before starting the agents.

### 5.5. `Monitor`

- Streams metrics to Prometheus and Grafana.
- Sends alerts when system thresholds are exceeded.
