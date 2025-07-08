# PH1-BF1.T1 - Fix Message Bus Register Handler

## Objective
Fix the MessageBus class to add proper register_handler method for OrchestratorAgent compatibility

## Files to touch / create
- triangulum_lx/agents/message_bus.py
- tests/unit/test_message_bus.py

## Definition-of-Done checklist
- [x] register_handler method implemented in MessageBus class
- [x] Proper type annotations for register_handler parameters
- [x] Logging added for handler registration events
- [x] Method documentation updated with clear description
- [x] Test case added to verify handler registration works correctly
- [x] Verified OrchestratorAgent can successfully register handlers

## Test strategy
- Unit test to verify MessageBus register_handler maps correctly to subscribe
- Integration test with OrchestratorAgent to confirm compatibility
- Verify proper logging when handlers are registered
- Test handler invocation for various message types

## Risk flags & dependencies
- Critical path component - all agent communication depends on MessageBus
- Regression risk if register_handler doesn't match subscribe functionality
- Dependent on MessageType enumeration and message schema
