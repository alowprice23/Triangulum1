import logging
import time
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
from triangulum_lx.monitoring.agentic_dashboard import AgenticDashboard

logger = logging.getLogger(__name__)

class MessageBusDashboardListener:
    """Connects the EnhancedMessageBus to the AgenticDashboard."""

    def __init__(self, message_bus: EnhancedMessageBus, dashboard: AgenticDashboard):
        self.message_bus = message_bus
        self.dashboard = dashboard
        self.message_bus.subscribe(
            agent_id="dashboard_listener",
            callback=self._handle_message,
            message_types=None
        )
        logger.info("Message bus listener initialized and subscribed to all message types.")

    def _handle_message(self, message):
        """Handle incoming messages and update dashboard accordingly."""
        try:
            self.dashboard.register_thought(
                agent_id=message.sender,
                chain_id=f"chain_{message.sender}",
                content=str(message.content),
                thought_type=message.message_type.value,
                metadata=message.metadata
            )

            if message.receiver:
                self.dashboard.register_message(
                    source_agent=message.sender,
                    target_agent=message.receiver,
                    message_type=message.message_type.value,
                    content=str(message.content),
                    metadata=message.metadata
                )
            
            # This is a placeholder for more detailed progress updates
            # In a real implementation, you would extract progress from the message
            if "progress" in message.metadata:
                 self.dashboard.update_agent_progress(
                    agent_id=message.sender,
                    percent_complete=message.metadata["progress"],
                    status="Active",
                    current_activity=f"Processed message {message.message_id}",
                )

        except Exception as e:
            logger.error(f"Error handling message in dashboard listener: {e}")

def is_triangulum_system_running():
    # Placeholder for a real health check
    return True

def monitor_backend_connection(dashboard: AgenticDashboard, message_bus: EnhancedMessageBus):
    """Monitor the connection to the backend and handle failures."""
    last_activity_time = time.time()

    while True:
        time.sleep(5)
        
        # This is a placeholder for a real activity check
        # In a real implementation, you would check the last message time from the bus
        latest_message_time = last_activity_time 

        if latest_message_time > last_activity_time:
            last_activity_time = latest_message_time
            continue

        if time.time() - last_activity_time > 30:
            logger.warning("No activity detected for 30 seconds, checking system status...")
            
            if not is_triangulum_system_running():
                logger.error("Triangulum system appears to be down")
                dashboard.update_global_progress(
                    dashboard.global_progress["percent_complete"],
                    "System Offline",
                    dashboard.global_progress["steps_completed"],
                    dashboard.global_progress["total_steps"]
                )
