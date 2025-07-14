# Orchestrator Redesign Plan

## 1. Principles

*   **Simplicity:** The new orchestrator will be much simpler than the old one. It will have fewer responsibilities and fewer dependencies.
*   **Testability:** The new orchestrator will be designed to be easily testable. It will have a clear and well-defined API, and it will not have any hidden dependencies.
*   **Asynchronous:** The new orchestrator will be fully asynchronous. This will make it much more scalable and responsive.

## 2. Key Components

*   **OrchestratorAgent:** The `OrchestratorAgent` will be responsible for managing the self-healing workflow. It will receive task requests from other agents, break them down into smaller steps, and assign them to specialized agents.
*   **Task:** A `Task` will represent a single unit of work that needs to be done. Each task will have a type, a priority, and a set of parameters.
*   **Workflow:** A `Workflow` will be a sequence of tasks that need to be executed in order.
*   **AgentProxy:** An `AgentProxy` will be a proxy for a specialized agent. It will be responsible for sending messages to the agent and receiving results back.

## 3. Workflow

1.  The `OrchestratorAgent` will receive a task request from another agent.
2.  The `OrchestratorAgent` will create a new `Workflow` for the task.
3.  The `OrchestratorAgent` will create a new `Task` for each step in the workflow.
4.  The `OrchestratorAgent` will assign each `Task` to an `AgentProxy`.
5.  The `AgentProxy` will send a message to the specialized agent.
6.  The specialized agent will process the message and send a result back to the `AgentProxy`.
7.  The `AgentProxy` will receive the result and notify the `OrchestratorAgent`.
8.  The `OrchestratorAgent` will update the status of the `Task` and the `Workflow`.
9.  When all the `Task`s in the `Workflow` are complete, the `OrchestratorAgent` will send a final result back to the original requester.
