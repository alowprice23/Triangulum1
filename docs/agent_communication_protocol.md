# Triangulum Agent Communication Protocol

This document provides an overview of the Triangulum Agent Communication Protocol, a standardized system for communication between specialized agents in the Triangulum system.

## Overview

The Triangulum Agent Communication Protocol provides a robust foundation for inter-agent communication, enabling agents to exchange information, delegate tasks, and collaborate effectively. The protocol features:

- **Standardized Message Format**: A consistent structure for all agent messages.
- **Schema Validation**: Ensure message compliance with defined standards.
- **Topic-Based Routing**: Publish/subscribe messaging patterns for flexible communication.

## Message Structure

Messages in the Triangulum Agent Communication Protocol follow a standardized format defined in the `AgentMessage` class in `triangulum_lx/agents/message.py`.

## Message Bus

The `EnhancedMessageBus` in `triangulum_lx/agents/enhanced_message_bus.py` provides the central routing infrastructure for agent communication.
