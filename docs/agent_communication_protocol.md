# Triangulum Agent Communication Protocol

This document provides an overview of the Triangulum Agent Communication Protocol, a standardized system for communication between specialized agents in the Triangulum system.

## Overview

The Triangulum Agent Communication Protocol provides a robust foundation for inter-agent communication, enabling agents to exchange information, delegate tasks, and collaborate effectively. The protocol features:

- **Standardized Message Format**: A consistent structure for all agent messages
- **Schema Validation**: Ensure message compliance with defined standards
- **Topic-Based Routing**: Publish/subscribe messaging patterns for flexible communication
- **Message Filtering**: Filter messages based on content or type
- **Delivery Guarantees**: Ensure reliable message delivery with retry mechanisms
- **Memory-Efficient Context**: Optimize token usage in multi-agent conversations
- **Thought Chain Integration**: Connect messages to reasoning chains

## Message Structure

Messages in the Triangulum Agent Communication Protocol follow a standardized format defined in the `AgentMessage` class:

### Core Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `message_type` | `MessageType` | Type of message (e.g., TASK_REQUEST, CODE_ANALYSIS) |
| `content` | `Dict[str, Any]` | Main content of the message |
| `sender` | `str` | ID of the agent sending the message |
| `message_id` | `str` | Unique identifier for the message (UUID) |
| `timestamp` | `float` | Unix timestamp when the message was created |
| `receiver` | `Optional[str]` | ID of the intended recipient (None for broadcasts) |
| `parent_id` | `Optional[str]` | ID of the parent message this is responding to |
| `conversation_id` | `str` | ID of the conversation this message belongs to |
| `confidence` | `Optional[float]` | Confidence level (0.0 to 1.0) |
| `metadata` | `Dict[str, Any]` | Additional metadata |
| `schema_version` | `str` | Version of the message schema |

### Enhanced Fields

| Field | Type | Description |
| ----- | ---- | ----------- |
| `problem_context` | `Dict[str, Any]` | Context about the problem being addressed |
| `analysis_results` | `Dict[str, Any]` | Results of analysis performed by agents |
| `suggested_actions` | `List[Dict[str, Any]]` | Actions suggested by agents |

## Message Types

The protocol defines several message types to represent different communication intents:

- **TASK_REQUEST**: Request an agent to perform a task
- **TASK_RESULT**: Response to a task request
- **QUERY**: Request information from an agent
- **QUERY_RESPONSE**: Response to a query
- **PROBLEM_ANALYSIS**: Analysis of a problem
- **CODE_ANALYSIS**: Analysis of code
- **RELATIONSHIP_ANALYSIS**: Analysis of code relationships
- **REPAIR_SUGGESTION**: Suggested repair action
- **VERIFICATION_RESULT**: Result of verification
- **ERROR**: Error message
- **STATUS**: Status update
- **LOG**: Log message

## Schema Validation

Messages are validated against a JSON schema defined in `message_schema.json` using the `MessageSchemaValidator` class:

```python
# Create a validator
validator = MessageSchemaValidator()

# Create a message
message = AgentMessage(
    message_type=MessageType.TASK_REQUEST,
    content={"task": "Analyze code"},
    sender="my_agent"
)

# Validate the message
is_valid, error = validator.validate_message(message)
if not is_valid:
    print(f"Invalid message: {error}")
```

## Message Bus

The `EnhancedMessageBus` provides the central routing infrastructure for agent communication:

### Basic Messaging

```python
# Create a message bus
message_bus = EnhancedMessageBus()

# Subscribe to messages
message_bus.subscribe(
    agent_id="my_agent",
    callback=handle_message,
    message_types=[MessageType.TASK_REQUEST]
)

# Publish a message
message_bus.publish(message)
```

### Topic-Based Routing

Topic-based routing enables more flexible communication patterns:

```python
# Subscribe to a topic
message_bus.subscribe_to_topic(
    agent_id="my_agent",
    topic="bug_reports",
    callback=handle_bug_report,
    message_types=[MessageType.PROBLEM_ANALYSIS]
)

# Publish to a topic
message_bus.publish_to_topic("bug_reports", message)
```

### Message Filtering

You can filter messages based on content using filter functions:

```python
# Define a filter function
def filter_high_priority(message):
    return message.content.get("priority") == "high"

# Subscribe with a filter
message_bus.subscribe_to_topic(
    agent_id="my_agent",
    topic="alerts",
    callback=handle_alert,
    message_types=[MessageType.STATUS],
    filter_func=filter_high_priority
)
```

### Delivery Guarantees

The `EnhancedMessageBus` provides delivery guarantees with retry mechanisms:

```python
# Enable delivery guarantees (enabled by default)
message_bus = EnhancedMessageBus(delivery_guarantee=True, retry_interval=5.0)

# Check delivery status
statuses = message_bus.get_delivery_status(message.message_id)

# Wait for delivery completion
statuses = message_bus.wait_for_delivery(message.message_id, timeout=30.0)
```

## Memory Management

The `MemoryManager` provides token-efficient context retrieval for agent communication:

```python
# Create a memory manager
memory_manager = MemoryManager(max_tokens=4000)

# Get context using various retrieval strategies
context = memory_manager.get_context(
    conversation,
    strategy=RetrievalStrategy.RECENCY,
    token_limit=1000
)
```

Available retrieval strategies:
- `RECENCY`: Most recent messages first
- `RELEVANCE`: Most relevant messages first
- `THREAD`: Messages in a specific thread
- `HYBRID`: Combination of recency and relevance
- `ROUND_ROBIN`: One message from each agent
- `TYPE_PRIORITIZED`: Prioritize specific message types

## Thought Chain Integration

The Agent Communication Protocol integrates with the Thought Chaining mechanism to connect messages with reasoning chains:

```python
# Create a thought chain manager
thought_chain_manager = ThoughtChainManager()

# Create a thought chain
chain_id = thought_chain_manager.create_chain(
    name="BugFixCoordination",
    description="Coordinates bug detection and fixing",
    creator_agent_id="coordinator_agent"
)

# Add a thought connected to a message
thought_chain_manager.add_thought(
    chain_id=chain_id,
    thought_type=ThoughtType.OBSERVATION,
    content={"observation": f"Bug detected", "source": message.message_id},
    author_agent_id="coordinator_agent"
)
```

## Complete Example

Here's a complete example of an agent using the protocol:

```python
from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
from triangulum_lx.agents.message_schema_validator import MessageSchemaValidator

class MyAgent:
    def __init__(self, agent_id, message_bus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.validator = MessageSchemaValidator()
        
        # Subscribe to messages
        self.message_bus.subscribe(
            agent_id=self.agent_id,
            callback=self.handle_message,
            message_types=[MessageType.TASK_REQUEST]
        )
        
        # Subscribe to a topic
        self.message_bus.subscribe_to_topic(
            agent_id=self.agent_id,
            topic="bug_reports",
            callback=self.handle_bug_report,
            message_types=[MessageType.PROBLEM_ANALYSIS]
        )
    
    def handle_message(self, message):
        print(f"Received message: {message.content}")
        
        # Send a response
        response = message.create_response(
            message_type=MessageType.TASK_RESULT,
            content={"result": "Task completed"}
        )
        
        self.message_bus.publish(response)
    
    def handle_bug_report(self, message):
        print(f"Received bug report: {message.content}")
```

## Best Practices

1. **Use Message Types Appropriately**: Choose the most specific message type for your intent.
2. **Validate Messages**: Always validate messages using the `MessageSchemaValidator` before sending.
3. **Use Topics for Broadcast Scenarios**: Use topic-based routing for one-to-many communication.
4. **Apply Filters Carefully**: Use message filtering to reduce processing overhead.
5. **Handle Errors Gracefully**: Implement error handling for message delivery failures.
6. **Optimize Context**: Use the memory manager to efficiently retrieve conversation context.
7. **Connect to Thought Chains**: Link messages to thought chains for traceable reasoning.
8. **Monitor Delivery Status**: Check delivery status for critical messages.
9. **Clean Up Resources**: Call `shutdown()` on the message bus when finished.
10. **Document Message Schemas**: Document the expected content structure for each message type.

## Reference Implementation

The Triangulum codebase provides a reference implementation of the Agent Communication Protocol in the following files:

- `triangulum_lx/agents/message.py`: Core message classes
- `triangulum_lx/agents/message_schema.json`: Message schema definition
- `triangulum_lx/agents/message_schema_validator.py`: Schema validation
- `triangulum_lx/agents/enhanced_message_bus.py`: Enhanced message bus with topic routing
- `triangulum_lx/agents/memory_manager.py`: Token-efficient context management

For a complete demonstration, see the `examples/enhanced_agent_communication_demo.py` file.
